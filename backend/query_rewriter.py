from sqlalchemy.orm import Session
from backend import models

def query_rewrite(text:str, book_id:str, user:str, page:int, db: Session ):
    conversations = db.query(models.UserQuery).filter(
        models.UserQuery.user_id == user,
        models.UserQuery.book_id == book_id,
        models.UserQuery.page_number == page,
    ).order_by((models.UserQuery.created_at.desc())).limit(5).all()
    if conversations:
        history = ""
        for conversation in conversations:
            history += f"User Previous Query: {conversation.query_text}\n"
            history += f"Assistant: {conversation.response_text}\n\n"
        history += f"User Current Query: {text}\n"
        pass# complete it
    else:
        return text

