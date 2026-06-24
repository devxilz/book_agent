from passlib.context import CryptContext
from sentence_transformers import SentenceTransformer
from typing import List
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

model = SentenceTransformer(
    "BAAI/bge-large-en-v1.5",
    device="cuda"
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_embedding(text: List[str]):
    embedding = model.encode(
    text,
    batch_size=64,
    show_progress_bar=True,
    convert_to_numpy=True
    )
    return embedding