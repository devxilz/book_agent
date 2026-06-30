import os
import re
import uuid
import fitz
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend import models, utils, chroma_db
from .chunking import split_text
from .config import settings


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

    # Store the physical PDF under a UUID so user filenames cannot affect paths.
    with open(file_location, "wb") as buffer:
        buffer.write(content)

    db.add(new_book)
    chapter_pattern = re.compile(r"^(chapter|ch\.?)\s*\d+", re.IGNORECASE)
    chapters = []

    # Extract every page into SQL so page_summary can teach a chosen page exactly.
    with fitz.open(file_location) as pdf:
        toc = pdf.get_toc()
        total_pages = len(pdf)
        for page_num in range(total_pages):
            page = models.Page(
                page_id=str(uuid.uuid4()),
                book_id=book_id,
                page_number=page_num + 1,
                content=pdf[page_num].get_text()
            )
            db.add(page)

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    file_location = os.path.join(settings.books_upload_path, f"{book_id}.pdf")
    if not os.path.exists(file_location):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book file not found"
        )
    chapters = db.query(models.Chapter).filter(models.Chapter.book_id == book_id).all()
    if not chapters:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No chapters found for this book"
        )

    for chapter in chapters:
        extracted_text = extract_text_from_chapter(book_id, chapter.chapter_id, db)
        chunks = split_text(extracted_text)
        embeddings = utils.get_embedding(chunks)
        chroma_db.collection.add(
            ids=[str(uuid.uuid4()) for _ in chunks],
            embeddings=embeddings,
            documents=chunks,
            metadatas=[
                {
                    "book_id": book_id,
                    "chapter_id": chapter.chapter_id,
                    "chapter_title": chapter.title,
                    "chunk_index": idx
                }
                for idx in range(len(chunks))
            ]
        )
    return {"message": "book is successfully embedded and stored in the database"}


def extract_text_from_chapter(book_id: str, chapter_id: str, db: Session):
    """Read only the pages that belong to one chapter from the saved PDF."""
    chapter = db.query(models.Chapter).filter(
        models.Chapter.chapter_id == chapter_id,
        models.Chapter.book_id == book_id
    ).first()
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chapter not found"
        )
    file_location = os.path.join(settings.books_upload_path, f"{book_id}.pdf")
    with fitz.open(file_location) as pdf:
        text = ""
        for page_num in range(chapter.start_page - 1, chapter.end_page):
            page = pdf.load_page(page_num)
            text += page.get_text()
    return text
