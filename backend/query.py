from ollama import chat
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend import models
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

 

'''context for the model to understand the task and provide relevant responses.'''
def query(text: str):
    model_name = settings.llm_model_name
    try:
        response = chat(model=model_name, messages=[{"role": "user", "content": text}])
    except:
          logger.error("Ollama failed")
    return response

async def page_call(book_id: str, page: int, db:Session):
        page_obj = db.query(models.Page).filter(
        models.Page.book_id == book_id,models.Page.page_number == page).first()
        if not page_obj:
              raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{page} not found.")
        text = page_obj.content
        response = query(text)
        return response



