"""Sample seed data for the Library Management System."""

from datetime import date, timedelta
from sqlalchemy.orm import Session
from models import Book, Member, Transaction
from crud import FINE_RATE_PER_DAY


def seed_database(db: Session):
    """Seed the database with realistic sample records if it is empty."""
    # Check if database already has data
    if db.query(Book).count() > 0 or db.query(Member).count() > 0:
        return

    today = date.today()

    # 1. Sample Books
    sample_books = [
        Book(
            isbn="978-0132350884",
            title="Clean Code: A Handbook of Agile Software Craftsmanship",
            author="Robert C. Martin",
            category="Programming",
            publisher="Prentice Hall",
            publication_year=2008,
            quantity=5,
            available_quantity=3  # 2 active loans
        ),
        Book(
            isbn="978-0262033848",
            title="Introduction to Algorithms (4th Edition)",
            author="Thomas H. Cormen, Charles E. Leiserson",
            category="Computer Science",
            publisher="MIT Press",
            publication_year=2022,
            quantity=4,
            available_quantity=3  # 1 active loan
        ),
        Book(
            isbn="978-0131103627",
            title="The C Programming Language",
            author="Brian W. Kernighan, Dennis M. Ritchie",
            category="Programming",
            publisher="Prentice Hall",
            publication_year=1988,
            quantity=3,
            available_quantity=2  # 1 active loan
        ),
        Book(
            isbn="978-0596007126",
            title="Head First Design Patterns",
            author="Eric Freeman, Elisabeth Robson",
            category="Computer Science",
            publisher="O'Reilly Media",
            publication_year=2004,
            quantity=4,
            available_quantity=3  # 1 active loan
        ),
        Book(
            isbn="978-0134685991",
            title="Effective Java (3rd Edition)",
            author="Joshua Bloch",
            category="Programming",
            publisher="Addison-Wesley",
            publication_year=2018,
            quantity=3,
            available_quantity=3
        ),
        Book(
            isbn="978-0486600888",
            title="The Principles of Quantum Mechanics",
            author="Paul Dirac",
            category="Physics",
            publisher="Oxford University Press",
            publication_year=1981,
            quantity=2,
            available_quantity=2
        ),
        Book(
            isbn="978-0387900742",
            title="Linear Algebra Done Right",
            author="Sheldon Axler",
            category="Mathematics",
            publisher="Springer",
            publication_year=2015,
            quantity=3,
            available_quantity=3
        ),
        Book(
            isbn="978-0062316097",
            title="Sapiens: A Brief History of Humankind",
            author="Yuval Noah Harari",
            category="History",
            publisher="Harper",
            publication_year=2014,
            quantity=4,
            available_quantity=4
        ),
        Book(
            isbn="978-0141439518",
            title="Pride and Prejudice",
            author="Jane Austen",
            category="Literature",
            publisher="Penguin Classics",
            publication_year=2002,
            quantity=3,
            available_quantity=3
        ),
    ]

    db.add_all(sample_books)
    db.commit()

    for book in sample_books:
        db.refresh(book)

    # 2. Sample Members
    sample_members = [
        Member(
            name="Aarav Sharma",
            roll_number="CS2023001",
            email="aarav.sharma@college.edu",
            phone="+91 98765 43210",
            department="Computer Science",
            registration_date=today - timedelta(days=120)
        ),
        Member(
            name="Priya Patel",
            roll_number="IT2023014",
            email="priya.patel@college.edu",
            phone="+91 98123 45678",
            department="Information Technology",
            registration_date=today - timedelta(days=90)
        ),
        Member(
            name="Rohan Verma",
            roll_number="EC2023045",
            email="rohan.verma@college.edu",
            phone="+91 97234 56789",
            department="Electronics & Communication",
            registration_date=today - timedelta(days=60)
        ),
        Member(
            name="Ananya Iyer",
            roll_number="ME2023012",
            email="ananya.iyer@college.edu",
            phone="+91 99345 67890",
            department="Mechanical Engineering",
            registration_date=today - timedelta(days=45)
        ),
        Member(
            name="Vikram Singh",
            roll_number="MT2023008",
            email="vikram.singh@college.edu",
            phone="+91 98456 78901",
            department="Mathematics",
            registration_date=today - timedelta(days=30)
        ),
    ]

    db.add_all(sample_members)
    db.commit()

    for member in sample_members:
        db.refresh(member)

    # 3. Sample Transactions
    # tx1: Returned past transaction with fine
    issue_date_1 = today - timedelta(days=40)
    due_date_1 = today - timedelta(days=26)
    return_date_1 = today - timedelta(days=20)  # Overdue by 6 days -> 6 * 5 = 30 fine
    tx1 = Transaction(
        book_id=sample_books[0].id,
        member_id=sample_members[0].id,
        issue_date=issue_date_1,
        due_date=due_date_1,
        return_date=return_date_1,
        fine=30.0,
        status="Returned"
    )

    # tx2: Returned past transaction on time (no fine)
    issue_date_2 = today - timedelta(days=25)
    due_date_2 = today - timedelta(days=11)
    return_date_2 = today - timedelta(days=13)  # On time
    tx2 = Transaction(
        book_id=sample_books[1].id,
        member_id=sample_members[1].id,
        issue_date=issue_date_2,
        due_date=due_date_2,
        return_date=return_date_2,
        fine=0.0,
        status="Returned"
    )

    # tx3: Active loan within due date
    issue_date_3 = today - timedelta(days=5)
    due_date_3 = today + timedelta(days=9)
    tx3 = Transaction(
        book_id=sample_books[0].id,
        member_id=sample_members[1].id,
        issue_date=issue_date_3,
        due_date=due_date_3,
        return_date=None,
        fine=0.0,
        status="Issued"
    )

    # tx4: Active loan within due date
    issue_date_4 = today - timedelta(days=3)
    due_date_4 = today + timedelta(days=11)
    tx4 = Transaction(
        book_id=sample_books[1].id,
        member_id=sample_members[2].id,
        issue_date=issue_date_4,
        due_date=due_date_4,
        return_date=None,
        fine=0.0,
        status="Issued"
    )

    # tx5: Active loan that is OVERDUE (due 7 days ago -> 7 * 5 = 35 fine)
    issue_date_5 = today - timedelta(days=21)
    due_date_5 = today - timedelta(days=7)
    tx5 = Transaction(
        book_id=sample_books[0].id,
        member_id=sample_members[2].id,
        issue_date=issue_date_5,
        due_date=due_date_5,
        return_date=None,
        fine=35.0,
        status="Overdue"
    )

    # tx6: Active loan that is OVERDUE (due 4 days ago -> 4 * 5 = 20 fine)
    issue_date_6 = today - timedelta(days=18)
    due_date_6 = today - timedelta(days=4)
    tx6 = Transaction(
        book_id=sample_books[2].id,
        member_id=sample_members[0].id,
        issue_date=issue_date_6,
        due_date=due_date_6,
        return_date=None,
        fine=20.0,
        status="Overdue"
    )

    # tx7: Active loan within due date
    issue_date_7 = today - timedelta(days=2)
    due_date_7 = today + timedelta(days=12)
    tx7 = Transaction(
        book_id=sample_books[3].id,
        member_id=sample_members[3].id,
        issue_date=issue_date_7,
        due_date=due_date_7,
        return_date=None,
        fine=0.0,
        status="Issued"
    )

    db.add_all([tx1, tx2, tx3, tx4, tx5, tx6, tx7])
    db.commit()
