"""SQLAlchemy ORM models for Library Management System."""

from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    isbn = Column(String(32), unique=True, index=True, nullable=False)
    title = Column(String(255), index=True, nullable=False)
    author = Column(String(255), index=True, nullable=False)
    category = Column(String(100), index=True, nullable=False)
    publisher = Column(String(255), nullable=True)
    publication_year = Column(Integer, nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    available_quantity = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transactions = relationship("Transaction", back_populates="book", cascade="all, delete-orphan")


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), index=True, nullable=False)
    roll_number = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    department = Column(String(100), nullable=False)
    registration_date = Column(Date, default=date.today, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transactions = relationship("Transaction", back_populates="member", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    issue_date = Column(Date, default=date.today, nullable=False)
    due_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    fine = Column(Float, default=0.0, nullable=False)
    status = Column(String(20), default="Issued", nullable=False)  # "Issued", "Returned", "Overdue"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    book = relationship("Book", back_populates="transactions")
    member = relationship("Member", back_populates="transactions")
