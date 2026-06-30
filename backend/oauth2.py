import uuid
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from backend import schemas
from .config import settings

# auto_error=False lets us support both Authorization headers and httpOnly cookies.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
ACCESS_TOKEN_COOKIE_NAME = "access_token"

# Local in-memory logout list. For production, store revoked token ids in Redis/DB.
revoked_token_ids = set()


def create_access_token(data: dict):
    """Create a short-lived JWT with a unique id so logout can revoke it."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str, credentials_exception):
    """Decode the JWT and reject expired/revoked/invalid tokens."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id: str = payload.get("user_id")
        token_id: str = payload.get("jti")
        if id is None or token_id in revoked_token_ids:
            raise credentials_exception
        token_data = schemas.TokenData(id=id)
    except JWTError:
        raise credentials_exception
    return token_data


def get_token_from_request(request: Request, token: str | None = Depends(oauth2_scheme)):
    # API clients can send Authorization: Bearer <token>.
    if token:
        return token

    # Browser frontend uses the secure cookie set by /login.
    return request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)


def revoke_token(token: str):
    """Mark a token id as logged out for the life of this server process."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_id = payload.get("jti")
        if token_id:
            revoked_token_ids.add(token_id)
    except JWTError:
        # Logout should still clear the browser cookie even if the token is stale.
        return


def get_current_user(token: str | None = Depends(get_token_from_request)):
    """FastAPI dependency used by protected routes."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    return verify_access_token(token, credentials_exception)
