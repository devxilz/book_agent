from .database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, nullable=False, index=True)
    username = Column(String, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False, index=True)
    books = relationship("Book", back_populates="owner", cascade="all, delete-orphan")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True, server_default=text("now()"))
    
class Book(Base):
    __tablename__ = "books"

    book_id = Column(String, primary_key=True)
    book_name = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, index=True)
    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE")
    )

    owner = relationship("User", back_populates="books")
    chapters = relationship(
        "Chapter",
        back_populates="book",
        cascade="all, delete-orphan"
    )
    pages = relationship(
        "Page",
        back_populates="book",
        cascade="all, delete-orphan"
    )

class Chapter(Base):
    __tablename__ = "chapters"

    chapter_id = Column(String, primary_key=True)

    book_id = Column(
        String,
        ForeignKey("books.book_id", ondelete="CASCADE")
    )

    title = Column(String, nullable=False)
    start_page = Column(Integer, nullable=False)
    end_page = Column(Integer, nullable=False)

    book = relationship("Book", back_populates="chapters")

class Page(Base):
    __tablename__ = "pages"

    page_id = Column(String, primary_key=True)

    book_id = Column(
        String,
        ForeignKey("books.book_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    page_number = Column(Integer, nullable=False, index=True)

    content = Column(String, nullable=False)
    
    book = relationship("Book", back_populates="pages")

class UserQuery(Base):
    __tablename__ = "user_queries"

    query_id = Column(String, primary_key=True)
    user_id = Column(
        String, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
        )
    book_id = Column(
        String, 
        ForeignKey("books.book_id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
        )
    page_number = Column(Integer, nullable=False)
    query_text = Column(String, nullable=False)
    response_text = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
