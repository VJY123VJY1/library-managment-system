"""Comprehensive End-to-End Test Suite for Library Management System."""

import sys
import os
from datetime import date, timedelta
from fastapi.testclient import TestClient

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from main import app
from database import engine, Base, SessionLocal
from seed_data import seed_database


def test_full_system():
    print("\n" + "=" * 60)
    print("🚀 RUNNING LIBRARY MANAGEMENT SYSTEM AUTOMATED TEST SUITE")
    print("=" * 60)

    with TestClient(app) as client:
        # 1. Test Static Files & Frontend Pages
        print("\n[1/7] Testing Frontend Page Serving...")
        pages = ["/", "/books.html", "/members.html", "/issue.html", "/return.html", "/transactions.html"]
        for page in pages:
            res = client.get(page)
            assert res.status_code == 200, f"Page {page} failed with status {res.status_code}"
            print(f"  ✓ GET {page} -> 200 OK (Serving HTML)")

        res_css = client.get("/static/css/style.css")
        assert res_css.status_code == 200, f"CSS failed: {res_css.status_code}"
        print("  ✓ GET /static/css/style.css -> 200 OK")

        # 2. Test Dashboard Stats
        print("\n[2/7] Testing Dashboard Stats API...")
        res = client.get("/api/dashboard/stats")
        assert res.status_code == 200
        stats = res.json()
        assert "total_books" in stats and stats["total_books"] > 0
        assert "available_books" in stats
        assert "issued_books" in stats
        assert "total_members" in stats and stats["total_members"] > 0
        assert "overdue_books" in stats
        assert "total_fine" in stats
        print(f"  ✓ Dashboard Stats: Total Books={stats['total_books']}, Available={stats['available_books']}, Issued={stats['issued_books']}, Members={stats['total_members']}, Overdue={stats['overdue_books']}, Fine=₹{stats['total_fine']}")

        # 3. Test Book Operations
        print("\n[3/7] Testing Book Management APIs...")
        res = client.get("/api/books")
        assert res.status_code == 200

        # Create Book
        test_isbn = f"978-TEST-{int(date.today().strftime('%Y%m%d'))}99"
        new_book_payload = {
            "isbn": test_isbn,
            "title": "Automated Testing in Python",
            "author": "Test Author",
            "category": "Programming",
            "publisher": "Test Publishing",
            "publication_year": 2024,
            "quantity": 3
        }
        res = client.post("/api/books", json=new_book_payload)
        assert res.status_code == 201, f"Create book failed: {res.text}"
        created_book = res.json()
        book_id = created_book["id"]
        assert created_book["available_quantity"] == 3
        print(f"  ✓ POST /api/books -> Created Book ID {book_id} (Available: {created_book['available_quantity']}/{created_book['quantity']})")

        # Duplicate ISBN rejection
        res_dup = client.post("/api/books", json=new_book_payload)
        assert res_dup.status_code == 400
        print("  ✓ Duplicate ISBN validation blocked duplicate creation (400 Bad Request)")

        # Update Book
        update_payload = {"title": "Automated Testing in Python (Updated Edition)", "quantity": 4}
        res = client.put(f"/api/books/{book_id}", json=update_payload)
        assert res.status_code == 200
        assert res.json()["title"] == "Automated Testing in Python (Updated Edition)"
        assert res.json()["available_quantity"] == 4
        print("  ✓ PUT /api/books/{id} -> Book updated successfully")

        # 4. Test Member Operations
        print("\n[4/7] Testing Member Management APIs...")
        test_roll = f"TEST-ROLL-{int(date.today().strftime('%m%d'))}01"
        new_member_payload = {
            "name": "Kavita Nair",
            "roll_number": test_roll,
            "email": "kavita.nair@college.edu",
            "phone": "+91 99999 11111",
            "department": "Computer Science"
        }
        res = client.post("/api/members", json=new_member_payload)
        assert res.status_code == 201, f"Create member failed: {res.text}"
        created_member = res.json()
        member_id = created_member["id"]
        print(f"  ✓ POST /api/members -> Registered Member ID {member_id} ({created_member['name']})")

        # Duplicate Roll Number rejection
        res_dup_member = client.post("/api/members", json=new_member_payload)
        assert res_dup_member.status_code == 400
        print("  ✓ Duplicate Roll Number validation blocked duplicate member registration (400 Bad Request)")

        # 5. Test Book Checkout / Issue Workflow & Inventory Decrement
        print("\n[5/7] Testing Issue Workflow & Inventory Logic...")
        issue_payload = {
            "book_id": book_id,
            "member_id": member_id,
            "issue_date": str(date.today()),
            "due_date": str(date.today() + timedelta(days=14))
        }
        res = client.post("/api/transactions/issue", json=issue_payload)
        assert res.status_code == 201, f"Issue failed: {res.text}"
        tx = res.json()
        tx_id = tx["id"]
        assert tx["status"] == "Issued"
        print(f"  ✓ POST /api/transactions/issue -> Issued Transaction #{tx_id}")

        # Verify book available quantity decreased
        res_book = client.get(f"/api/books/{book_id}")
        assert res_book.json()["available_quantity"] == 3  # was 4, now 3
        print(f"  ✓ Available stock verified: 4 -> {res_book.json()['available_quantity']}")

        # Verify active member loans count
        res_member = client.get(f"/api/members/{member_id}")
        assert res_member.json()["active_loans_count"] == 1
        print(f"  ✓ Member active loans verified: {res_member.json()['active_loans_count']}")

        # 6. Test Safety Constraints (Blocking Deletions with Active Loans)
        print("\n[6/7] Testing Business Safety Constraints...")
        # Attempt to delete book with active issued copy
        res_del_book = client.delete(f"/api/books/{book_id}")
        assert res_del_book.status_code == 400
        print("  ✓ Deleting book with active issued copies correctly blocked (400 Bad Request)")

        # Attempt to delete member with active borrowed book
        res_del_member = client.delete(f"/api/members/{member_id}")
        assert res_del_member.status_code == 400
        print("  ✓ Deleting member with active borrowed books correctly blocked (400 Bad Request)")

        # 7. Test Return Workflow & Dynamic Fine Calculation
        print("\n[7/7] Testing Return Workflow & Fine Assessment...")
        # Simulate return with 5 days overdue
        overdue_return_date = date.today() + timedelta(days=19)  # 19 days after issue (due in 14) -> 5 days late
        return_payload = {"return_date": str(overdue_return_date)}
        res_return = client.put(f"/api/transactions/{tx_id}/return", json=return_payload)
        assert res_return.status_code == 200, f"Return failed: {res_return.text}"
        returned_tx = res_return.json()
        assert returned_tx["status"] == "Returned"
        assert returned_tx["overdue_days"] == 5
        assert returned_tx["fine"] == 25.0  # 5 days * ₹5 = ₹25.0
        print(f"  ✓ PUT /api/transactions/{tx_id}/return -> Successfully returned! Overdue: {returned_tx['overdue_days']} days, Fine: ₹{returned_tx['fine']}")

        # Verify inventory was restored
        res_book_restored = client.get(f"/api/books/{book_id}")
        assert res_book_restored.json()["available_quantity"] == 4
        print(f"  ✓ Inventory restored after return: available={res_book_restored.json()['available_quantity']}/{res_book_restored.json()['quantity']}")

        # Verify double return is rejected
        res_double_return = client.put(f"/api/transactions/{tx_id}/return", json=return_payload)
        assert res_double_return.status_code == 400
        print("  ✓ Re-returning an already closed transaction correctly blocked (400 Bad Request)")

        # Clean up test entities
        client.delete(f"/api/books/{book_id}")
        client.delete(f"/api/members/{member_id}")
        print("  ✓ Test records successfully cleaned up after loan completion")

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED SUCCESSFULLY! (100% PASS RATE)")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    test_full_system()
