import logging

from fastapi import HTTPException, status
from ollama import chat
from sqlalchemy.orm import Session

from backend import models
from backend.config import settings
from backend.prompts.system import SYSTEM_PROMPT


logger = logging.getLogger(__name__)


def query(text: str, system_prompt: str | None = None):
    """Send a prompt to the local Ollama model and return its response."""
    model_name = settings.llm_model_name
    try:
        if system_prompt:
            return chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            )

        return chat(model=model_name, messages=[{"role": "user", "content": text}])
    except Exception as exc:
        logger.exception("Ollama failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The local AI model is not available. Please make sure Ollama is running.",
        ) from exc


async def page_call(book_id: str, page: int, db: Session):
    """Teach one exact SQL page. Retrieval is intentionally not used here."""
    page_obj = db.query(models.Page).filter(
        models.Page.book_id == book_id,
        models.Page.page_number == page,
    ).first()
    if not page_obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{page} not found.")

    text = page_obj.content
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page {page} has no extractable text to teach.",
        )

    user_prompt = f"""Teach the following page.

                Your task is NOT to summarize it.

                Your task is to act like an experienced teacher explaining the page to a complete beginner.

                Requirements:

                - Use provided page as your primary source of knowledge.
                - Only use outside knowledge when it is absolutely necessary to understand a term or grammar that the page assumes the reader already knows. Any outside information must be minimal and must not introduce new facts, examples, or ideas beyond what is necessary to understand the page.
                - Do not add examples, facts, definitions, or explanations that are not supported by the page.
                - Do not skip any sentence.
                - Explain every idea thoroughly.
                - Explain the reasoning behind every important statement.
                - Explain how each paragraph connects to the previous one. If there is genuinely no connection to make, do not try to make one.
                - For every cause-effect relationship in the page, write it out explicitly using an A -> B -> C chain, filled in only with what the page states. If a paragraph has no cause-effect relationship, do not try to make one.
                - Explain important concepts using only information available in the page. If the page uses a term without ever explaining what it means, explain it only if you know what it means.
                - Do not explain by swapping words for easier synonyms. Explain the underlying mechanism or relationship instead; your explanation should not look like the original sentence with a few words changed.
                - For any sentence that bundles multiple ideas, requirements, or consequences together, break it into separate short steps instead of one dense explanation.
                - Keep the same order as the original page.
                - If the page ends abruptly or is incomplete, simply state the last sentence exactly as it appears on the page. Do not speculate, summarize, explain why it is incomplete, or add any additional comments.

                The goal is that after reading your explanation, someone who has never seen the page can understand every idea the author intended to communicate without missing any information.

                <Page_Context>
                {text}
                </Page_Context>"""
    return query(user_prompt, SYSTEM_PROMPT)
