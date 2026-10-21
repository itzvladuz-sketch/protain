"""End-to-End Test Suite for Financial Ledger, Withdrawal Tracking & User Withdraw Requests."""

import asyncio
import os
import sys
from datetime import datetime

BASE_DIR = "d:/birinchi mijon/tg_stars_premium_shop"
sys.path.insert(0, BASE_DIR)

from services.config import BotConfig
from services.db import Database

TEST_DB_PATH = os.path.join(BASE_DIR, "test_finances.db")

async def test_finances_system():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

    db = Database(TEST_DB_PATH)
    await db.init_db()

    print("=" * 65)
    print("  TESTING FINANCIAL LEDGER & WITHDRAWAL SYSTEM")
    print("=" * 65)

    # 1. Create test user
    uid = 777123
    u = await db.get_or_create_user(uid, "test_finance_user")
    assert u["user_id"] == uid
    print("  [+] Test user created: OK")

    # 2. Deposit 100,000 UZS via card topup
    await db.update_user_balance_uzs(uid, 100000.0)
    tx1 = await db.record_transaction(
        user_id=uid,
        tx_type="card_topup",
        amount_uzs=100000.0,
        old_balance_uzs=0.0,
        new_balance_uzs=100000.0,
        comment="Test card topup",
    )
    assert tx1 > 0
    print(f"  [+] Card deposit transaction recorded (ID #{tx1}): OK")

    # 3. User buys Stars (30,000 UZS)
    deducted = await db.deduct_user_balance_uzs(uid, 30000.0)
    assert deducted is True
    tx2 = await db.record_transaction(
        user_id=uid,
        tx_type="purchase",
        amount_uzs=30000.0,
        old_balance_uzs=100000.0,
        new_balance_uzs=70000.0,
        comment="Xarid: 100 stars",
    )
    assert tx2 > 0
    print(f"  [+] Purchase transaction recorded (ID #{tx2}): OK")

    # 4. Admin withdraws/deducts 20,000 UZS
    deducted = await db.deduct_user_balance_uzs(uid, 20000.0)
    assert deducted is True
    tx3 = await db.record_transaction(
        user_id=uid,
        admin_id=999000,
        tx_type="admin_withdraw",
        amount_uzs=20000.0,
        old_balance_uzs=70000.0,
        new_balance_uzs=50000.0,
        comment="Admin yechib oldi",
    )
    assert tx3 > 0
    print(f"  [+] Admin withdrawal transaction recorded (ID #{tx3}): OK")

    # 5. User submits card withdrawal request for 25,000 UZS
    deducted = await db.deduct_user_balance_uzs(uid, 25000.0)
    assert deducted is True
    req_id = await db.create_withdraw_request(
        user_id=uid,
        username="test_finance_user",
        card_number="8600 1234 5678 9999",
        card_holder="Test User",
        amount_uzs=25000.0,
    )
    assert req_id > 0
    tx4 = await db.record_transaction(
        user_id=uid,
        tx_type="user_withdraw_pending",
        amount_uzs=25000.0,
        old_balance_uzs=50000.0,
        new_balance_uzs=25000.0,
        comment=f"Kartaga yechish so'rovi #{req_id}",
    )
    print(f"  [+] User card withdrawal request created (Req #{req_id}, TX #{tx4}): OK")

    # 6. Verify pending requests count
    pending_count = await db.get_pending_withdraw_count()
    assert pending_count == 1
    pending_reqs = await db.get_pending_withdraw_requests()
    assert len(pending_reqs) == 1
    assert pending_reqs[0]["amount_uzs"] == 25000.0
    print("  [+] Pending withdrawal requests retrieval: OK")

    # 7. Admin approves withdrawal request
    approved = await db.set_withdraw_request_status(req_id, "approved", admin_id=999000)
    assert approved is True
    tx5 = await db.record_transaction(
        user_id=uid,
        admin_id=999000,
        tx_type="user_withdraw_approved",
        amount_uzs=25000.0,
        old_balance_uzs=25000.0,
        new_balance_uzs=25000.0,
        comment=f"Admin #{999000} to'lab berdi",
    )
    print("  [+] Admin approval of withdrawal request: OK")

    # 8. Check financial statistics
    stats = await db.get_financial_stats()
    print("  [+] Financial Statistics:", stats)
    assert stats["total_deposited"] == 100000.0
    assert stats["total_admin_withdrawn"] == 20000.0
    assert stats["total_user_withdrawn"] == 25000.0
    assert stats["total_purchases"] == 30000.0
    assert stats["current_user_balances"] == 25000.0
    assert stats["pending_withdraw_count"] == 0
    print("  [+] Financial stats aggregation accuracy: 100% OK")

    # 9. Check per-user financial profile
    prof = await db.get_user_financial_profile(uid)
    print("  [+] User Financial Profile:", prof)
    assert prof["total_deposited"] == 100000.0
    assert prof["total_withdrawn"] == 45000.0  # 20,000 admin + 25,000 user
    assert prof["total_purchased"] == 30000.0
    print("  [+] User profile financial audit: 100% OK")

    # 10. Check withdrawal history feed
    wd_history = await db.get_withdrawals_history()
    assert len(wd_history) == 2  # 1 admin_withdraw + 1 user_withdraw_approved
    print("  [+] Withdrawal history feed: 2 records found: OK")

    # 11. Test Rejection & Refund Flow for second withdrawal
    req2_id = await db.create_withdraw_request(
        user_id=uid,
        username="test_finance_user",
        card_number="8600 0000 0000 1111",
        card_holder="Test User",
        amount_uzs=10000.0,
    )
    # Deduct 10,000
    await db.deduct_user_balance_uzs(uid, 10000.0)
    # Admin rejects
    rejected = await db.set_withdraw_request_status(req2_id, "rejected", admin_id=999000, admin_note="Karta bloklangan")
    assert rejected is True
    # Refund 10,000 back
    await db.update_user_balance_uzs(uid, 10000.0)
    tx_ref = await db.record_transaction(
        user_id=uid,
        admin_id=999000,
        tx_type="user_withdraw_refunded",
        amount_uzs=10000.0,
        old_balance_uzs=15000.0,
        new_balance_uzs=25000.0,
        comment="Rad etildi va qaytarildi",
    )
    u_final = await db.get_user(uid)
    assert u_final["balance_uzs"] == 25000.0
    print("  [+] Withdrawal rejection and balance refund: 100% OK")

    await db.close()

    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

    print("=" * 65)
    print("   ALL FINANCIAL & WITHDRAWAL TESTS PASSED FLAWLESSLY!")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(test_finances_system())
