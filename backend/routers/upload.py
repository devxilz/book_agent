import hashlib
from backend.config import settings
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, status
from sqlalchemy.orm import Session
from pathlib import Path
from backend import models, oauth2
from backend.database import get_db
from backend.ingestion_pipline import upload_books, extract_text_from_book

BOOKS_UPLOAD_PATH = settings.books_upload_path

Path(BOOKS_UPLOAD_PATH).mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/books")
async def upload_book(file: UploadFile = File(...), current_user: int = Depends(oauth2.get_current_user), db: Session = Depends(get_db)):
        if file.filename.lower().endswith(".pdf"):
    
            content = await file.read()
    
            file_hash = hashlib.sha256(content).hexdigest()
            existing_book = db.query(models.Book).filter(
                models.Book.file_hash == file_hash,
                models.Book.user_id == current_user.id
            ).first()
            if existing_book:
                raise HTTPException(
                            status_code=400,
                            detail="Book already exists")
            book_id = await upload_books(file.filename, file_hash, content, current_user, db)
            message = await extract_text_from_book(book_id, db)
            return message

        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type. Only PDF files are allowed.")