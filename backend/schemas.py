from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    # Payload expected by POST /signin.
    username: str
    email: EmailStr
    password: str
    confirm_password: str

class UserLogin(BaseModel):
    # Kept for possible JSON login clients; the active /login route uses OAuth form data.
    email: EmailStr
    password: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    # Login still returns the token for API clients, but the browser uses the cookie.
    access_token: str
    token_type: str

class TokenData(BaseModel):
    # Minimal user identity stored after JWT verification.
    id: Optional[str] = None

class SummaryResponse(BaseModel):
    # Shared response shape for both page teaching and user questions.
    response : str
