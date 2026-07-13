import logging
import re
from fastapi import HTTPException, status
from ollama import chat
from sqlalchemy.orm import Session
from openai import OpenAI
from backend import models
from backend.config import settings
from backend.prompts.system import SYSTEM_PROMPT

client = OpenAI(api_key=settings.openai_api_key,base_url="https://api.groq.com/openai/v1",)
logger = logging.getLogger(__name__)


PERSONAL_INFO_PATTERNS = (
    re.compile(r"^\s*name\s*[:\-].*$", re.IGNORECASE),
    re.compile(r"^\s*student\s*name\s*[:\-].*$", re.IGNORECASE),
    re.compile(r"^\s*roll\s*(?:no|number)?\s*[:\-].*$", re.IGNORECASE),
    re.compile(r"^\s*class\s*[:\-].*$", re.IGNORECASE),
    re.compile(r"^\s*section\s*[:\-].*$", re.IGNORECASE),
    re.compile(r"^\s*sec\s*[:\-].*$", re.IGNORECASE),
    re.compile(r"^\s*submitted\s+by\s*[:\-].*$", re.IGNORECASE),
    re.compile(r"^\s*prepared\s+by\s*[:\-].*$", re.IGNORECASE),
    re.compile(r"^\s*written\s+by\s*[:\-].*$", re.IGNORECASE),
    re.compile(r"^\s*author\s*[:\-].*$", re.IGNORECASE),
)

PERSONAL_INFO_PREFIXES = (
    "name",
    "studentname",
    "writername",
    "authorname",
    "rollno",
    "rollnumber",
    "rolno",
    "roino",
    "class",
    "section",
    "sec",
    "submittedby",
    "preparedby",
    "writtenby",
    "author",
    "signature",
    "schoolname",
)


def strip_note_owner_metadata(text: str) -> str:
    """Remove common note-owner labels so the model does not teach them."""
    cleaned_lines = []
    for line in text.splitlines():
        if is_owner_metadata_line(line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def normalize_line_for_label_check(line: str) -> str:

    return re.sub(r"[^a-z0-9]+", "", line.lower())


def is_owner_metadata_line(line: str) -> bool:

    if any(pattern.match(line) for pattern in PERSONAL_INFO_PATTERNS):
        return True

    normalized = normalize_line_for_label_check(line)
    if not normalized:
        return False

    has_separator = any(sep in line for sep in (":", "=", "-", "|"))
    short_line = len(line.strip()) <= 50

    for prefix in PERSONAL_INFO_PREFIXES:
        if normalized.startswith(prefix) and (has_separator or short_line):
            return True

    return False


def query(text: str, system_prompt: str | None = None):
    """Send a prompt to the local Ollama model and return its response."""
    model_name = settings.llm_model_name
    try:
        if system_prompt:
            response = chat(
                    model=settings.llm_model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},{"role": "user", "content": text}],
                )
            return response

        return chat(
                    model=settings.llm_model_name,
                    messages=[{"role": "user", "content": text}],
                )
    except Exception as exc:
        logger.exception("Ollama failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The local AI model is not available. Please make sure Ollama is running.",
        ) from exc


async def page_call(book_id: str, page: int, db: Session):
    """Teach one exact SQL page."""
    page_obj = db.query(models.Page).filter(
        models.Page.book_id == book_id,
        models.Page.page_number == page,
    ).first()
    if not page_obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{page} not found.")

    text = strip_note_owner_metadata(page_obj.content)
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page {page} has no teachable text after filtering note metadata.",
        )

    user_prompt = f"""Teach the following page.
    Teach the content of the provided page to a complete beginner.

        Behavior Rules

        - Use the provided page as your primary source.
        - Only use outside knowledge when absolutely necessary to explain a term or grammar assumed by the page.
        - Do not introduce new facts, examples, or ideas beyond what is necessary.
        - Do not omit any information from the page.
        - Preserve the original order of ideas.
        - Explain every important idea thoroughly.
        - Explain the reasoning behind important statements.
        - Explain how each paragraph relates to the previous one when a genuine connection exists.
        - Make all cause-effect relationships explicit using only information from the page.
        - If a sentence contains multiple ideas, explain those ideas separately.
        - If the page ends abruptly, stop after reproducing the last sentence exactly as it appears.

        Output Style
        - write headings or subheading in big and bold letters.
        - Write naturally, as if teaching a student.
        - Organize the explanation into paragraphs and section headings when helpful.
        - Do NOT quote every sentence before explaining it.
        - Do NOT label content as "Sentence 1", "Sentence 2", or use sentence numbers.
        - Do NOT produce a sentence-by-sentence transcript.
        - Integrate explanations into a continuous narrative while preserving the original order of ideas.
        
        <Page_Context>
            {text}
        </Page_Context>"""

    return query(user_prompt, SYSTEM_PROMPT)
