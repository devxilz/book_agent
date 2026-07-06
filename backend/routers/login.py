from fastapi import APIRouter, HTTPException, Request, Response, Depends, status
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.config import settings
from backend.database import get_db
from backend import models, schemas, utils, oauth2
from backend.rate_limit import rate_limit

router = APIRouter(tags=['Authentication'])

@router.post('/login', response_model=schemas.Token, dependencies=[Depends(rate_limit(10, 60))])
def login(
    response: Response,
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # OAuth2PasswordRequestForm calls the login email field "username".
    user = db.query(models.User).filter(
        models.User.email == user_credentials.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid Credential.")

    if not utils.verify(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid Credential.")

    access_token = oauth2.create_access_token(data={"user_id": user.id})

    # Store the token in an httpOnly cookie so frontend JavaScript cannot read it.
    response.set_cookie(
        key=oauth2.ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=oauth2.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.post('/logout')
def logout(request: Request, response: Response):
    # Revoke the current cookie token before clearing it from the browser.
    token = request.cookies.get(oauth2.ACCESS_TOKEN_COOKIE_NAME)
    if token:
        oauth2.revoke_token(token)
    response.delete_cookie(
        key=oauth2.ACCESS_TOKEN_COOKIE_NAME,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax"
    )
    return {"message": "Logged out"}
