from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models, oauth2
from backend.database import get_db


router = APIRouter(prefix="/library", tags=["Library"])


def clean_book_title(filename: str):
    # Keep the original filename in the database, but expose a nicer display name.
    title = filename.removesuffix(".pdf").removesuffix(".PDF")
    noisy_markers = ("z-library", "z-lib", "1lib", "libgen", "archive", ".sk", ".com", ".org")

    while "(" in title and ")" in title:
        start = title.rfind("(")
        end = title.find(")", start)
        if end == -1:
            break
        content = title[start:end + 1]
        if any(marker in content.lower() for marker in noisy_markers):
            title = f"{title[:start]}{title[end + 1:]}"
        else:
            break

    return " ".join(title.split())


def get_owned_book(book_id: str, user_id: str, db: Session):
    book = db.query(models.Book).filter(
        models.Book.book_id == book_id,
        models.Book.user_id == user_id
    ).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    return book


@router.get("/me")
def read_current_user(
    current_user=Depends(oauth2.get_current_user),
    db: Session = Depends(get_db)
):
    # The frontend uses this to restore the saved token session after refresh.
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email
    }


@router.get("/books")
def list_books(
    current_user=Depends(oauth2.get_current_user),
    db: Session = Depends(get_db)
):
    # This gives the frontend a practical library instead of manual book IDs.
    books = db.query(models.Book).filter(
        models.Book.user_id == current_user.id
    ).order_by(models.Book.book_name).all()

    response = []
    for book in books:
        page_count = db.query(func.count(models.Page.page_id)).filter(
            models.Page.book_id == book.book_id
        ).scalar()
        chapter_count = db.query(func.count(models.Chapter.chapter_id)).filter(
            models.Chapter.book_id == book.book_id
        ).scalar()
        max_page = db.query(func.max(models.Page.page_number)).filter(
            models.Page.book_id == book.book_id
        ).scalar()

        response.append({
            "book_id": book.book_id,
            "book_name": book.book_name,
            "display_name": clean_book_title(book.book_name),
            "page_count": page_count or 0,
            "chapter_count": chapter_count or 0,
            "max_page": max_page or 0
        })

    return {"books": response}


@router.get("/books/{book_id}/chapters")
def list_book_chapters(
    book_id: str,
    current_user=Depends(oauth2.get_current_user),
    db: Session = Depends(get_db)
):
    # The ownership check prevents users from browsing someone else's book.
    get_owned_book(book_id, current_user.id, db)

    chapters = db.query(models.Chapter).filter(
        models.Chapter.book_id == book_id
    ).order_by(models.Chapter.start_page).all()

    return {
        "chapters": [
            {
                "chapter_id": chapter.chapter_id,
                "title": chapter.title,
                "start_page": chapter.start_page,
                "end_page": chapter.end_page
            }
            for chapter in chapters
        ]
    }
