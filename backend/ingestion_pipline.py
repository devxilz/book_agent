import os
import re
import uuid
import fitz
import ollama
import logging
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend import models, utils, chroma_db
from .chunking import split_text
from .config import settings

logger = logging.getLogger(__name__)
temp_dir = "temp"

if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

async def upload_books(filename: str, file_hash: str, content: bytes, current_user, db: Session):
    """Save the PDF and create Book/Page/Chapter records."""
    book_id = str(uuid.uuid4())
    file_location = os.path.join(settings.books_upload_path, f"{book_id}.pdf")

    new_book = models.Book(
        book_id=book_id,
        book_name=filename,
        file_hash=file_hash,
        user_id=current_user.id
    )

    # Store the physical PDF under a UUID 
    with open(file_location, "wb") as buffer:
        buffer.write(content)

    db.add(new_book)
    chapter_pattern = re.compile(r"^(chapter|ch\.?)\s*\d+", re.IGNORECASE)
    chapters = []


    with fitz.open(file_location) as pdf:
        toc = pdf.get_toc()
        total_pages = len(pdf)
        for page_num in range(total_pages):
            page = pdf.load_page(page_num)

            page_content = await extract_page_text(page, page_num)

            page_record = models.Page(
                page_id=str(uuid.uuid4()),
                book_id=book_id,
                page_number=page_num + 1,
                content=page_content,
            )

            db.add(page_record)

    # Use table-of-contents chapter entries when the PDF provides them.
    for _, title, page in toc:
        if chapter_pattern.match(title):
            chapters.append((title, page))

    # If the PDF has no usable chapter entries, store one fallback chapter.
    if not chapters:
        chapter = models.Chapter(
            chapter_id=str(uuid.uuid4()),
            book_id=book_id,
            title="Full Book",
            start_page=1,
            end_page=total_pages
        )
        db.add(chapter)

    for index, (title, start_page) in enumerate(chapters):
        if index < len(chapters) - 1:
            end_page = chapters[index + 1][1] - 1
        else:
            end_page = total_pages

        chapter = models.Chapter(
            chapter_id=str(uuid.uuid4()),
            book_id=book_id,
            title=title,
            start_page=start_page,
            end_page=end_page
        )
        db.add(chapter)

    db.commit()
    db.refresh(new_book)
    return new_book.book_id


async def extract_text_from_book(book_id: str, db: Session):
    """Split chapter text and store vector embeddings in Chroma."""
    book = db.query(models.Book).filter(models.Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Book not found.")
    else:
        file_location = os.path.join(settings.books_upload_path, f"{book_id}.pdf")
        if not os.path.exists(file_location):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="PDF file not found.")
        pages = db.query(models.Page).filter(models.Page.book_id == book_id).order_by(models.Page.page_number).all()
        all_chunks = []
        all_metadata = []

        for page in pages:
            split_chunks = split_text(page.content)

            for i, chunk in enumerate(split_chunks):
                all_chunks.append(chunk)
                all_metadata.append({
                    "book_id": book_id,
                    "page_number": page.page_number,
                    "chunk_index": i,
                })
        embeddings = utils.get_embedding(all_chunks)
        BATCH_SIZE = 500

        for start in range(0, len(all_chunks), BATCH_SIZE):
            end = start + BATCH_SIZE
            batch_docs = all_chunks[start:end]
            batch_embeddings = embeddings[start:end]
            batch_metadata = all_metadata[start:end]
            chroma_db.collection.add(
                ids=[str(uuid.uuid4()) for _ in batch_docs],
                documents=batch_docs,
                embeddings=batch_embeddings.tolist(),
                metadatas=batch_metadata,
            )
    return {"message": "book is successfully embedded and stored in the database"}

def is_scanned_image_page(page) -> bool:
    images = page.get_images(full=True)
    if not images:
        return False
    page_area = page.rect.width * page.rect.height
    for img in images:
        xref = img[0]
        rects = page.get_image_rects(xref)
        for r in rects:
            if (r.width * r.height) / page_area > 0.8:
                return True
    return False

async def text_from_image(page, page_num: int):
    pix = page.get_pixmap(dpi=150)
    image_path = os.path.join(temp_dir, f"page_{page_num}.png")
    pix.save(image_path)
    try:
        response = ollama.chat(
                model=settings.vlm_model_name,
                messages=[
                    {
                        "role": "user",
                        "content": """
            Extract every handwritten word from this notebook page.

            Return plain text only.

            Do not summarize.
            Do not interpret.
            Keep line breaks exactly as seen.
            If something is unreadable, write [UNCLEAR].
            """,
                        "images": [image_path],
                    }
                ],
            )
    except Exception as exc:
        logger.exception("Ollama VLM failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The local VLM model is not available. Please make sure Ollama is running.",
        ) from exc
    print(response["message"]["content"])   
    return response["message"]["content"]

async def extract_page_text(page, page_num: int):
    if is_scanned_image_page(page):
        return await text_from_image(page, page_num + 1)
    else:
        return page.get_text()
