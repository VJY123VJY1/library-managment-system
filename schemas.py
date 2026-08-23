"""Pydantic schemas for data validation and API request/response serialization."""

from datetime import date, datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# BOOK SCHEMAS
# ==========================================
class BookBase(BaseModel):
    isbn: str = Field(..., min_length=1, max_length=32, description="Unique ISBN code")
    title: str = Field(..., min_length=1, max_length=255, description="Book title")
    author: str = Field(..., min_length=1, max_length=255, description="Author name")
    category: str = Field(..., min_length=1, max_length=100, description="Book category/genre")
    publisher: Optional[str] = Field(None, max_length=255)
    publication_year: Optional[int] = Field(None, ge=1000, le=2100)
    quantity: int = Field(..., ge=1, description="Total physical copies in library")


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    isbn: Optional[str] = Field(None, min_length=1, max_length=32)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    author: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    publisher: Optional[str] = Field(None, max_length=255)
    publication_year: Optional[int] = Field(None, ge=1000, le=2100)
    quantity: Optional[int] = Field(None, ge=1)


class BookResponse(BookBase):
    id: int
    available_quantity: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# MEMBER SCHEMAS
# ==========================================
class MemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Full name")
    roll_number: str = Field(..., min_length=1, max_length=50, description="Unique Student/Staff ID")
    email: str = Field(..., min_length=3, max_length=255, description="Email address")
    phone: Optional[str] = Field(None, max_length=20)
    department: str = Field(..., min_length=1, max_length=100, description="Academic department")
    registration_date: Optional[date] = None


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    roll_number: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = Field(None, min_length=3, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, min_length=1, max_length=100)


class MemberResponse(MemberBase):
    id: int
    registration_date: date
    created_at: Optional[datetime] = None
    active_loans_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# TRANSACTION SCHEMAS
# ==========================================
class TransactionCreate(BaseModel):
    book_id: int
    member_id: int
    issue_date: Optional[date] = None
    due_date: Optional[date] = None


class TransactionReturn(BaseModel):
    return_date: Optional[date] = None


class TransactionResponse(BaseModel):
    id: int
    book_id: int
    member_id: int
    book_title: Optional[str] = None
    book_isbn: Optional[str] = None
    member_name: Optional[str] = None
    member_roll_number: Optional[str] = None
    issue_date: date
    due_date: date
    return_date: Optional[date] = None
    fine: float = 0.0
    overdue_days: int = 0
    status: str  # "Issued", "Returned", "Overdue"
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MemberDetailResponse(MemberResponse):
    transactions: List[TransactionResponse] = []


# ==========================================
# DASHBOARD SCHEMAS
# ==========================================
class DashboardStats(BaseModel):
    total_books: int
    total_copies: int
    available_books: int
    issued_books: int
    total_members: int
    overdue_books: int
    total_fine: float
    category_distribution: Dict[str, int] = {}
    recent_transactions: List[TransactionResponse] = []
