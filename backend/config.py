from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    books_upload_path:str
    sqlalchemy_database_url:str
    secret_key:str
    algorithm:str
    access_token_expire_minutes:int
    llm_model_name:str
    class Config:
        env_file = ".env"


settings = Settings()