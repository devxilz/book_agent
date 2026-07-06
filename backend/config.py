from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Required settings already used by your backend.
    books_upload_path: str
    sqlalchemy_database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    llm_model_name: str
    vlm_model_name: str
    cookie_secure: bool = False # change it when in production to true.
    openai_api_key: str | None = None
    openai_model: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
