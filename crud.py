"""CRUD operations and business logic for Library Management System."""

from datetime import date, timedelta, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from models import Book, Member, Transaction
from schemas import (
    BookCreate, BookUpdate,
    MemberCreate, MemberUpdate,
    TransactionCreate, TransactionReturn
)

FINE_RATE_PER_DAY = 5.0  # ₹5 per overdue day


def compute_overdue_and_fine(issue_date: date, due_date: date, return_date: Optional[date] = None) -> tuple[int, float, str]:
    """Calculate overdue days, fine amount, and current status for a transaction."""
    reference_date = return_date if return_date else date.today()
    if reference_date > due_date:
        overdue_days = (reference_date - due_date).days
        fine = round(overdue_days * FINE_RATE_PER_DAY, 2)
        status = "Returned" if return_date else "Overdue"
    else:
        overdue_days = 0
        fine = 0.0
        status = "Returned" if return_date else "Issued"
    return overdue_days, fine, status


def format_transaction_dict(tx: Transaction) -> Dict[str, Any]:
    """Helper to convert Transaction ORM model into schema-compatible dict with computed fields."""
    overdue_days, dynamic_fine, dynamic_status = compute_overdue_and_fine(
        tx.issue_date, tx.due_date, tx.return_date
    )
    
    # If the transaction is already returned, respect the saved fine and status
    fine_val = tx.fine if tx.return_date is not None else dynamic_fine
    status_val = "Returned" if tx.return_date is not None else dynamic_status

    return {
        "id": tx.id,
        "book_id": tx.book_id,
        "member_id": tx.member_id,
        "book_title": tx.book.title if tx.book else "Unknown Book",
        "book_isbn": tx.book.isbn if tx.book else "N/A",
        "member_name": tx.member.name if tx.member else "Unknown Member",
        "member_roll_number": tx.member.roll_number if tx.member else "N/A",
        "issue_date": tx.issue_date,
        "due_date": tx.due_date,
        "return_date": tx.return_date,
        "fine": fine_val,
        "overdue_days": overdue_days,
        "status": status_val,
        "created_at": tx.created_at,
    }


# ==========================================
# BOOK OPERATIONS
# ==========================================
def get_books(
    db: Session,
    skip: int = 0,
    limit: int = 1000,
    search: Optional[str] = None,
    category: Optional[str] = None
) -> List[Book]:
    """Retrieve books with optional filtering by search query and category."""
    query = db.query(Book)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Book.title.ilike(search_term),
                Book.author.ilike(search_term),
                Book.isbn.ilike(search_term),
                Book.publisher.ilike(search_term),
                Book.category.ilike(search_term)
            )
        )
    if category and category.lower() != "all":
        query = query.filter(Book.category.ilike(category.strip()))
    
    return query.order_by(Book.title.asc()).offset(skip).limit(limit).all()


def get_book(db: Session, book_id: int) -> Optional[Book]:
    return db.query(Book).filter(Book.id == book_id).first()


def get_book_by_isbn(db: Session, isbn: str) -> Optional[Book]:
    return db.query(Book).filter(Book.isbn == isbn.strip()).first()


def create_book(db: Session, book: BookCreate) -> Book:
    # Initialize available_quantity equal to initial total quantity
    db_book = Book(
        isbn=book.isbn.strip(),
        title=book.title.strip(),
        author=book.author.strip(),
        category=book.category.strip(),
        publisher=book.publisher.strip() if book.publisher else None,
        publication_year=book.publication_year,
        quantity=book.quantity,
        available_quantity=book.quantity
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


def update_book(db: Session, book_id: int, book_update: BookUpdate) -> Book:
    db_book = get_book(db, book_id)
    if not db_book:
        raise ValueError("Book not found")

    update_data = book_update.model_dump(exclude_unset=True)

    # Check ISBN uniqueness if changed
    if "isbn" in update_data and update_data["isbn"]:
        new_isbn = update_data["isbn"].strip()
        existing = get_book_by_isbn(db, new_isbn)
        if existing and existing.id != book_id:
            raise ValueError(f"Book with ISBN '{new_isbn}' already exists")
        update_data["isbn"] = new_isbn

    # Quantity change handling
    if "quantity" in update_data and update_data["quantity"] is not None:
        new_quantity = update_data["quantity"]
        issued_count = db_book.quantity - db_book.available_quantity
        if new_quantity < issued_count:
            raise ValueError(
                f"Cannot reduce quantity to {new_quantity}. There are currently {issued_count} copies issued to members."
            )
        # Update available quantity proportionally
        db_book.available_quantity = new_quantity - issued_count
        db_book.quantity = new_quantity

    for key, value in update_data.items():
        if key != "quantity" and value is not None:
            setattr(db_book, key, value.strip() if isinstance(value, str) else value)

    db.commit()
    db.refresh(db_book)
    return db_book


def delete_book(db: Session, book_id: int) -> Book:
    db_book = get_book(db, book_id)
    if not db_book:
        raise ValueError("Book not found")

    # Check if there are active issued transactions
    active_loans = db.query(Transaction).filter(
        Transaction.book_id == book_id,
        Transaction.return_date == None
    ).count()

    if active_loans > 0:
        raise ValueError(
            f"Cannot delete book '{db_book.title}'. It currently has {active_loans} active issued copy/copies."
        )

    db.delete(db_book)
    db.commit()
    return db_book


# ==========================================
# MEMBER OPERATIONS
# ==========================================
def get_members(
    db: Session,
    skip: int = 0,
    limit: int = 1000,
    search: Optional[str] = None,
    department: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve members with search and department filtering, including active loans count."""
    query = db.query(Member)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Member.name.ilike(search_term),
                Member.roll_number.ilike(search_term),
                Member.email.ilike(search_term),
                Member.department.ilike(search_term),
                Member.phone.ilike(search_term)
            )
        )
    if department and department.lower() != "all":
        query = query.filter(Member.department.ilike(department.strip()))

    members = query.order_by(Member.name.asc()).offset(skip).limit(limit).all()

    result = []
    for m in members:
        active_loans = db.query(Transaction).filter(
            Transaction.member_id == m.id,
            Transaction.return_date == None
        ).count()
        m_dict = {
            "id": m.id,
            "name": m.name,
            "roll_number": m.roll_number,
            "email": m.email,
            "phone": m.phone,
            "department": m.department,
            "registration_date": m.registration_date,
            "created_at": m.created_at,
            "active_loans_count": active_loans
        }
        result.append(m_dict)
    return result


def get_member(db: Session, member_id: int) -> Optional[Member]:
    return db.query(Member).filter(Member.id == member_id).first()


def get_member_by_roll_number(db: Session, roll_number: str) -> Optional[Member]:
    return db.query(Member).filter(Member.roll_number == roll_number.strip()).first()


def create_member(db: Session, member: MemberCreate) -> Member:
    roll = member.roll_number.strip()
    if get_member_by_roll_number(db, roll):
        raise ValueError(f"Member with Roll Number / ID '{roll}' already exists")

    db_member = Member(
        name=member.name.strip(),
        roll_number=roll,
        email=member.email.strip(),
        phone=member.phone.strip() if member.phone else None,
        department=member.department.strip(),
        registration_date=member.registration_date or date.today()
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member


def update_member(db: Session, member_id: int, member_update: MemberUpdate) -> Member:
    db_member = get_member(db, member_id)
    if not db_member:
        raise ValueError("Member not found")

    update_data = member_update.model_dump(exclude_unset=True)

    if "roll_number" in update_data and update_data["roll_number"]:
        new_roll = update_data["roll_number"].strip()
        existing = get_member_by_roll_number(db, new_roll)
        if existing and existing.id != member_id:
            raise ValueError(f"Member with Roll Number '{new_roll}' already exists")
        update_data["roll_number"] = new_roll

    for key, value in update_data.items():
        if value is not None:
            setattr(db_member, key, value.strip() if isinstance(value, str) else value)

    db.commit()
    db.refresh(db_member)
    return db_member


def delete_member(db: Session, member_id: int) -> Member:
    db_member = get_member(db, member_id)
    if not db_member:
        raise ValueError("Member not found")

    active_loans = db.query(Transaction).filter(
        Transaction.member_id == member_id,
        Transaction.return_date == None
    ).count()

    if active_loans > 0:
        raise ValueError(
            f"Cannot delete member '{db_member.name}'. They currently have {active_loans} borrowed book(s)."
        )

    db.delete(db_member)
    db.commit()
    return db_member


def get_member_detail(db: Session, member_id: int) -> Dict[str, Any]:
    db_member = get_member(db, member_id)
    if not db_member:
        raise ValueError("Member not found")

    tx_records = db.query(Transaction).filter(
        Transaction.member_id == member_id
    ).order_by(Transaction.id.desc()).all()

    formatted_txs = [format_transaction_dict(tx) for tx in tx_records]
    active_loans = sum(1 for tx in formatted_txs if tx["return_date"] is None)

    return {
        "id": db_member.id,
        "name": db_member.name,
        "roll_number": db_member.roll_number,
        "email": db_member.email,
        "phone": db_member.phone,
        "department": db_member.department,
        "registration_date": db_member.registration_date,
        "created_at": db_member.created_at,
        "active_loans_count": active_loans,
        "transactions": formatted_txs
    }


# ==========================================
# TRANSACTION OPERATIONS
# ==========================================
def get_transactions(
    db: Session,
    skip: int = 0,
    limit: int = 1000,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve all transactions with dynamic search and status filtering."""
    query = db.query(Transaction).join(Book).join(Member)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Book.title.ilike(search_term),
                Book.isbn.ilike(search_term),
                Member.name.ilike(search_term),
                Member.roll_number.ilike(search_term)
            )
        )

    txs = query.order_by(Transaction.id.desc()).all()
    formatted = [format_transaction_dict(tx) for tx in txs]

    if status and status.lower() != "all":
        target_status = status.strip().capitalize()
        formatted = [tx for tx in formatted if tx["status"].capitalize() == target_status]

    return formatted[skip: skip + limit]


def get_transaction(db: Session, tx_id: int) -> Optional[Transaction]:
    return db.query(Transaction).filter(Transaction.id == tx_id).first()


def issue_book(
    db: Session,
    book_id: int,
    member_id: int,
    issue_date: Optional[date] = None,
    due_date: Optional[date] = None
) -> Dict[str, Any]:
    """Issue a book copy to a member with inventory decrement and validation."""
    book = get_book(db, book_id)
    if not book:
        raise ValueError("Book not found")

    member = get_member(db, member_id)
    if not member:
        raise ValueError("Member not found")

    if book.available_quantity <= 0:
        raise ValueError(f"Book '{book.title}' is currently out of stock (0 available copies).")

    # Set default dates
    i_date = issue_date or date.today()
    d_date = due_date or (i_date + timedelta(days=14))

    if d_date < i_date:
        raise ValueError("Due date cannot be earlier than the issue date")

    # Decrement available quantity
    book.available_quantity -= 1

    tx = Transaction(
        book_id=book.id,
        member_id=member.id,
        issue_date=i_date,
        due_date=d_date,
        return_date=None,
        fine=0.0,
        status="Issued"
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    return format_transaction_dict(tx)


def return_book(
    db: Session,
    transaction_id: int,
    return_date: Optional[date] = None
) -> Dict[str, Any]:
    """Return an issued book, calculate overdue fine, and increment inventory."""
    tx = get_transaction(db, transaction_id)
    if not tx:
        raise ValueError("Transaction not found")

    if tx.return_date is not None:
        raise ValueError("This book has already been returned")

    r_date = return_date or date.today()
    if r_date < tx.issue_date:
        raise ValueError("Return date cannot be earlier than the issue date")

    # Calculate fine
    overdue_days, fine, _ = compute_overdue_and_fine(tx.issue_date, tx.due_date, r_date)

    tx.return_date = r_date
    tx.fine = fine
    tx.status = "Returned"

    # Restore inventory
    if tx.book:
        tx.book.available_quantity = min(tx.book.quantity, tx.book.available_quantity + 1)

    db.commit()
    db.refresh(tx)

    return format_transaction_dict(tx)


# ==========================================
# DASHBOARD STATS
# ==========================================
def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    """Compute live library dashboard statistics."""
    total_books = db.query(Book).count()
    total_copies = db.query(func.sum(Book.quantity)).scalar() or 0
    available_books = db.query(func.sum(Book.available_quantity)).scalar() or 0
    total_members = db.query(Member).count()

    # Active loans
    active_loans = db.query(Transaction).filter(Transaction.return_date == None).all()
    issued_books = len(active_loans)

    # Overdue count and pending fines
    today = date.today()
    overdue_count = 0
    pending_fines = 0.0

    for loan in active_loans:
        if loan.due_date < today:
            overdue_count += 1
            days = (today - loan.due_date).days
            pending_fines += days * FINE_RATE_PER_DAY

    # Collected fines from completed transactions
    collected_fines = db.query(func.sum(Transaction.fine)).filter(Transaction.return_date != None).scalar() or 0.0
    total_fine = round(collected_fines + pending_fines, 2)

    # Category distribution
    categories = db.query(Book.category, func.sum(Book.quantity)).group_by(Book.category).all()
    category_distribution = {cat: (count or 0) for cat, count in categories}

    # Recent transactions (top 7)
    recent_txs_raw = db.query(Transaction).order_by(Transaction.id.desc()).limit(7).all()
    recent_transactions = [format_transaction_dict(tx) for tx in recent_txs_raw]

    return {
        "total_books": total_books,
        "total_copies": total_copies,
        "available_books": available_books,
        "issued_books": issued_books,
        "total_members": total_members,
        "overdue_books": overdue_count,
        "total_fine": total_fine,
        "category_distribution": category_distribution,
        "recent_transactions": recent_transactions
    }
