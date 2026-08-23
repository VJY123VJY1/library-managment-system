"""FastAPI Application for Library Management System."""

import os
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import engine, Base, get_db, SessionLocal
from models import Book, Member, Transaction
import schemas
import crud
from seed_data import seed_database




# Create tables on startup
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context to initialize database tables and seed sample data."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield






app = FastAPI(
    title="College Library Management System",
    description="A comprehensive RESTful API and management system for college libraries.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for cross-origin frontend support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_index():
    return FileResponse("../frontend/index.html")

app.mount("/css", StaticFiles(directory="../frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="../frontend/js"), name="js")

# ==========================================
# DASHBOARD ENDPOINTS
# ==========================================
@app.get("/api/dashboard/stats", response_model=schemas.DashboardStats, tags=["Dashboard"])
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Retrieve comprehensive real-time statistics for the library dashboard."""
    return crud.get_dashboard_stats(db)


# ==========================================
# BOOK ENDPOINTS
# ==========================================
@app.get("/api/books", response_model=List[schemas.BookResponse], tags=["Books"])
def read_books(
    search: Optional[str] = Query(None, description="Search by title, author, ISBN, or publisher"),
    category: Optional[str] = Query(None, description="Filter by book category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Retrieve all books with optional search query and category filters."""
    return crud.get_books(db, skip=skip, limit=limit, search=search, category=category)


@app.get("/api/books/{book_id}", response_model=schemas.BookResponse, tags=["Books"])
def read_book(book_id: int, db: Session = Depends(get_db)):
    """Retrieve details of a specific book by ID."""
    db_book = crud.get_book(db, book_id)
    if not db_book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return db_book


@app.post("/api/books", response_model=schemas.BookResponse, status_code=status.HTTP_201_CREATED, tags=["Books"])
def create_book(book: schemas.BookCreate, db: Session = Depends(get_db)):
    """Register a new book in the library catalog."""
    existing = crud.get_book_by_isbn(db, book.isbn)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A book with ISBN '{book.isbn}' is already registered."
        )
    return crud.create_book(db, book)


@app.put("/api/books/{book_id}", response_model=schemas.BookResponse, tags=["Books"])
def update_book(book_id: int, book_update: schemas.BookUpdate, db: Session = Depends(get_db)):
    """Update details or quantity of an existing book."""
    try:
        return crud.update_book(db, book_id, book_update)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.delete("/api/books/{book_id}", response_model=schemas.BookResponse, tags=["Books"])
def delete_book(book_id: int, db: Session = Depends(get_db)):
    """Delete a book from the library catalog (only if no active copies are issued)."""
    try:
        return crud.delete_book(db, book_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==========================================
# MEMBER ENDPOINTS
# ==========================================
@app.get("/api/members", response_model=List[schemas.MemberResponse], tags=["Members"])
def read_members(
    search: Optional[str] = Query(None, description="Search by name, roll number, email, or department"),
    department: Optional[str] = Query(None, description="Filter by department"),
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Retrieve all library members with search and department filtering."""
    return crud.get_members(db, skip=skip, limit=limit, search=search, department=department)


@app.get("/api/members/{member_id}", response_model=schemas.MemberDetailResponse, tags=["Members"])
def read_member(member_id: int, db: Session = Depends(get_db)):
    """Retrieve detailed member profile including all loan history."""
    try:
        return crud.get_member_detail(db, member_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.post("/api/members", response_model=schemas.MemberResponse, status_code=status.HTTP_201_CREATED, tags=["Members"])
def create_member(member: schemas.MemberCreate, db: Session = Depends(get_db)):
    """Register a new student or faculty member."""
    try:
        return crud.create_member(db, member)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.put("/api/members/{member_id}", response_model=schemas.MemberResponse, tags=["Members"])
def update_member(member_id: int, member_update: schemas.MemberUpdate, db: Session = Depends(get_db)):
    """Update member profile details."""
    try:
        return crud.update_member(db, member_id, member_update)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.delete("/api/members/{member_id}", response_model=schemas.MemberResponse, tags=["Members"])
def delete_member(member_id: int, db: Session = Depends(get_db)):
    """Remove a member (only if they have no active unreturned books)."""
    try:
        return crud.delete_member(db, member_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==========================================
# TRANSACTION ENDPOINTS
# ==========================================
@app.get("/api/transactions", response_model=List[schemas.TransactionResponse], tags=["Transactions"])
def read_transactions(
    status: Optional[str] = Query(None, description="Filter by status: 'Issued', 'Returned', 'Overdue'"),
    search: Optional[str] = Query(None, description="Search by book title, ISBN, member name, or roll number"),
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Retrieve all transactions with status and search filters."""
    return crud.get_transactions(db, skip=skip, limit=limit, status=status, search=search)


@app.post("/api/transactions/issue", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED, tags=["Transactions"])
def issue_book_endpoint(tx_in: schemas.TransactionCreate, db: Session = Depends(get_db)):
    """Issue a book copy to a registered member."""
    try:
        return crud.issue_book(
            db=db,
            book_id=tx_in.book_id,
            member_id=tx_in.member_id,
            issue_date=tx_in.issue_date,
            due_date=tx_in.due_date
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.put("/api/transactions/{transaction_id}/return", response_model=schemas.TransactionResponse, tags=["Transactions"])
def return_book_endpoint(
    transaction_id: int,
    tx_return: schemas.TransactionReturn = schemas.TransactionReturn(),
    db: Session = Depends(get_db)
):
    """Process a book return and calculate any applicable overdue fines."""
    try:
        return crud.return_book(
            db=db,
            transaction_id=transaction_id,
            return_date=tx_return.return_date
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==========================================
# FRONTEND STATIC FILES & SPA SERVING
# ==========================================
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_dashboard():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/{page_name}.html")
    def serve_page(page_name: str):
        page_path = os.path.join(frontend_dir, f"{page_name}.html")
        if os.path.isfile(page_path):
            return FileResponse(page_path)
        raise HTTPException(status_code=404, detail="Page not found")
