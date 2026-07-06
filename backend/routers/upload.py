import hashlib
import logging
import fitz
from backend.config import settings
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, status
from sqlalchemy.orm import Session
from pathlib import Path
from backend import models, oauth2
from backend.database import get_db
from backend.ingestion_pipline import upload_books, extract_text_from_book
from backend.rate_limit import rate_limit

logger = logging.getLogger(__name__)
BOOKS_UPLOAD_PATH = settings.books_upload_path
MAX_PDF_SIZE_BYTES = 100 * 1024 * 1024

Path(BOOKS_UPLOAD_PATH).mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/upload", tags=["upload"])


def validate_pdf_upload(filename: str, content: bytes):
    """Reject bad uploads before the ingestion pipeline touches the file."""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF files are allowed."
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded PDF is empty."
        )
    if len(content) > MAX_PDF_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="PDF is too large. Maximum allowed size is 100 MB."
        )
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PDF file signature."
        )
    try:
        with fitz.open(stream=content, filetype="pdf") as pdf:
            if len(pdf) == 0:
                raise ValueError("PDF contains no pages.")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file could not be read as a valid PDF."
        ) from exc


@router.post("/books", dependencies=[Depends(rate_limit(5, 600))])
async def upload_book(
    file: UploadFile = File(...),
    current_user=Depends(oauth2.get_current_user),
    db: Session = Depends(get_db)
):
    if file.filename.lower().endswith(".pdf"):
        content = await file.read()
        validate_pdf_upload(file.filename, content)

        file_hash = hashlib.sha256(content).hexdigest()
        existing_book = db.query(models.Book).filter(
            models.Book.file_hash == file_hash,
            models.Book.user_id == current_user.id
        ).first()
        if existing_book:
            raise HTTPException(
                status_code=400,
                detail="Book already exists"
            )

        book_id = await upload_books(file.filename, file_hash, content, current_user, db)
        try:
            message = await extract_text_from_book(book_id, db)
        except Exception:
            logger.exception("Embedding failed after book upload.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Book uploaded, but indexing failed."
            )
        return message

    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type. Only PDF files are allowed.")
