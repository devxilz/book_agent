from passlib.context import CryptContext
from sentence_transformers import SentenceTransformer
from typing import List
import torch


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Use GPU when available, but let the app run on CPU-only machines too.
embedding_device = "cuda" if torch.cuda.is_available() else "cpu"

model = SentenceTransformer(
    "BAAI/bge-large-en-v1.5",
    device=embedding_device
)


def hash_password(password: str) -> str:
    """Hash passwords before storing them in the database."""
    return pwd_context.hash(password)


def verify(plain_password: str, hashed_password: str) -> bool:
    """Check a login password against the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_embedding(text: List[str]):
    """Create vector embeddings for Chroma retrieval."""
    embedding = model.encode(
        text,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    return embedding
