import uuid
from fastapi import APIRouter, HTTPException , Depends, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, utils
from backend.schemas import UserCreate 

router = APIRouter(tags=['Sign In'])

@router.post('/signin')
def signin(user_info: UserCreate, db: Session = Depends(get_db)):
    # Check if the passwords match
    if user_info.password != user_info.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match.")
    user_id = str(uuid.uuid4())
    hashed_password = utils.hash_password(user_info.password)
    new_user = models.User(
        id=user_id,
        username=user_info.username,
        email=user_info.email,
        hashed_password=hashed_password 
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
    