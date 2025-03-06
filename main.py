import string
import uuid
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional
import random

# create a FastAPI instance
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# configure the database
SQLALCHEMY_DATABASE_URL = "sqlite:///./library.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# create a database model
class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String)
    coverUrl = Column(String)
    language = Column(String)
    publisher = Column(String)
    published_date = Column(String)
    isbn = Column(String, unique=True, index=True)
    description = Column(String)
    available = Column(Integer, default=1)  # 1 for available, 0 for borrowed
    created_at = Column(DateTime, default=datetime.now)

# create the database tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class BookBase(BaseModel):
    title: str
    author: str
    coverUrl: Optional[str] = "https://via"
    language: Optional[str] = "English"
    publisher: Optional[str] = "Unknown"
    published_date: Optional[str]= "1900-01-01"
    isbn: Optional[str] = "9780000000000"
    description: Optional[str] = "No description available"

class BookCreate(BookBase):
    pass

class BookResponse(BookBase):
    id: int
    available: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Home route
@app.get("/")
def home():
    return {"message": "Welcome to the Bookshell API"}

# random sample data, query: random?isbn=9780062315007, generate a random book with this ISBN
@app.get("/random")
def random_book(isbn: str):
    # generate a random book with isbn
    random.seed(isbn)
    # genera a uuid for the book
    r_uuid = uuid.uuid4()
    return {
        "title": ''.join(random.choices(string.ascii_letters + string.digits, k=10)),
        "author":   ''.join(random.choices(string.ascii_letters + string.digits, k=5)),
        "coverUrl": "https://via.placeholder.com/150",
        "language": "English",
        "publisher": "HarperCollins",
        "published_date": "1988-01-01",
        "isbn": isbn,
        "description": r_uuid,
        "available": 1
    }


# API endpoints
@app.post("/books/", response_model=BookResponse)
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    db_book = Book(**book.model_dump())
    db.add(db_book)
    try:
        db.commit()
        db.refresh(db_book)
        return db_book
    except:
        db.rollback()
        raise HTTPException(status_code=400, detail="ISBN already exists")

@app.get("/books/", response_model=List[BookResponse])
def list_books(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    books = db.query(Book).offset(skip).limit(limit).all()
    return books

@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(book_id: int, book: BookCreate, db: Session = Depends(get_db)):
    db_book = db.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    for key, value in book.model_dump().items():
        setattr(db_book, key, value)
    
    try:
        db.commit()
        db.refresh(db_book)
        return db_book
    except:
        db.rollback()
        raise HTTPException(status_code=400, detail="Update failed")

@app.delete("/books/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)):
    db_book = db.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db.delete(db_book)
    db.commit()
    return {"message": "Book deleted successfully"}

@app.put("/books/{book_id}/borrow")
def borrow_book(book_id: int, db: Session = Depends(get_db)):
    db_book = db.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if db_book.available == 0:
        raise HTTPException(status_code=400, detail="Book is not available")
    
    db_book.available = 0
    db.commit()
    return {"message": "Book borrowed successfully"}

@app.put("/books/{book_id}/return")
def return_book(book_id: int, db: Session = Depends(get_db)):
    db_book = db.query(Book).filter(Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if db_book.available == 1:
        raise HTTPException(status_code=400, detail="Book is already returned")
    
    db_book.available = 1
    db.commit()
    return {"message": "Book returned successfully"}

@app.get("/books/search/")
def search_books(query: str, db: Session = Depends(get_db)):
    books = db.query(Book).filter(
        (Book.title.ilike(f"%{query}%")) |
        (Book.author.ilike(f"%{query}%")) |
        (Book.isbn.ilike(f"%{query}%"))
    ).all()
    return books
