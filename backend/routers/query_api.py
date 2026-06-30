from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend import chroma_db, models, oauth2, schemas
from backend.database import get_db
from backend.prompts.user import USER_QUERY_PROMPT
from backend.query import page_call, query
from backend.rate_limit import rate_limit
from backend.utils import get_embedding


router = APIRouter(tags=["Chat"], prefix="/chat")


@router.post(
    "/page_summary",
    response_model=schemas.SummaryResponse,
    dependencies=[Depends(rate_limit(30, 60))],
)
async def page_summary(
    book_id: str,
    page: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    """Teach one selected page from a book owned by the logged-in user."""
    book = db.query(models.Book).filter(
        models.Book.book_id == book_id,
        models.Book.user_id == current_user.id,
    ).first()
    if not book:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    page_obj = db.query(models.Page).filter(
        models.Page.book_id == book_id,
        models.Page.page_number == page,
    ).first()
    if not page_obj:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Page {page} not found",
        )

    response = await page_call(book_id, page, db)
    return schemas.SummaryResponse(response=response.message.content)


@router.post(
    "/user_query",
    response_model=schemas.SummaryResponse,
    dependencies=[Depends(rate_limit(40, 60))],
)
async def user_query(
    text: str,
    book_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    """Answer user questions using retrieved chunks from the selected book."""
    book = db.query(models.Book).filter(
        models.Book.book_id == book_id,
        models.Book.user_id == current_user.id,
    ).first()
    if not book:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    query_embedding = get_embedding([text])
    results = chroma_db.collection.query(
        query_embeddings=query_embedding,
        n_results=5,
        where={"book_id": book_id},
    )
    documents = results["documents"][0] if results["documents"] else []
    if not documents:
        return schemas.SummaryResponse(
            response="I could not find enough relevant text in this book to answer that question."
        )

    context = "\n\n".join(documents)
    prompt = f"""
            Context:

            {context}

            ----------------------------------------

            Question:

            {text}

            ----------------------------------------

            Instructions:

            Answer the question using the provided context.

            Requirements:
            - Maximum 8 lines.
            - Minimum 1 line.
            - Use simple language.
            - Be accurate and direct.
            - If the context does not contain enough information, state that clearly in one or two lines and briefly explain what is missing.
            """
    response = query(prompt, USER_QUERY_PROMPT)
    return schemas.SummaryResponse(response=response.message.content)
