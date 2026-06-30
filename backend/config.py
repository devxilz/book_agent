from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Required settings already used by your backend.
    books_upload_path: str
    sqlalchemy_database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    llm_model_name: str

    # Local development uses HTTP, so this defaults to False.
    # In production behind HTTPS, set COOKIE_SECURE=true in .env.
    cookie_secure: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
