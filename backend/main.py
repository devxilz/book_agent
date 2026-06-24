from fastapi import FastAPI
from backend.routers import upload, login, singin, query_api
from . import models
from .database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Book Teacher")


#All the routers
app.include_router(upload.router)
app.include_router(login.router)
app.include_router(singin.router)
app.include_router(query_api.router)



