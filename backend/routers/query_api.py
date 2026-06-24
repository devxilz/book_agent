from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.query import page_call, query
from backend import schemas, models

router = APIRouter(
    tags=['Chat'],
    prefix='/chat'
    )

@router.post('/page_summary', response_model=schemas.SummaryResponse)
async def page_summary(book_id: str, page: int, db: Session = Depends(get_db)):
        response = await page_call(book_id,page,db)
        return schemas.SummaryResponse(response=response.message.content)

@router.post('/next_page_summary', response_model=schemas.SummaryResponse)
async def next_page_summary(book_id: str, page: int, db: Session = Depends(get_db)):
        page_obj = db.query(models.Page).filter(
        models.Page.book_id == book_id,
        models.Page.page_number == page + 1
        ).first()

        if not page_obj:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail=f"Page {page} not found"
            )
        response = query(page_obj.content)
        return schemas.SummaryResponse(response=response.message.content)

@router.post('/user_query', response_model=schemas.SummaryResponse)
async def user_query(text: str):
       response = query(text)
       return schemas.SummaryResponse(response=response)
