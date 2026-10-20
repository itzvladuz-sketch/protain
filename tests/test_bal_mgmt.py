import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db import Database

async def main():
    db_path = "test_bal.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    db = Database(db_path)
    await db.init_db()

    await db.get_or_create_user(1001, "user1")
    await db.get_or_create_user(1002, "user2")
    await db.get_or_create_user(1003, "user3")

    await db.update_user_balance_uzs(1001, 50000)
    await db.update_user_balance_uzs(1002, 120000)
    await db.update_user_balance_uzs(1003, 0)

    with_bal = await db.get_users_with_balance(10)
    assert len(with_bal) == 2, f"Expected 2, got {len(with_bal)}"
    assert with_bal[0]["user_id"] == 1002, "User 1002 should be first"

    # Deduction
    await db.update_user_balance_uzs(1001, -20000)
    u1 = await db.get_user(1001)
    assert int(u1["balance_uzs"]) == 30000, f"Expected 30000, got {u1['balance_uzs']}"

    # Floor at 0
    await db.update_user_balance_uzs(1001, -50000)
    u1 = await db.get_user(1001)
    assert u1["balance_uzs"] == 0.0, f"Expected 0.0, got {u1['balance_uzs']}"

    # Reset all balances except admin
    await db.update_user_balance_uzs(1001, 25000)
    await db.update_user_balance_uzs(1003, 75000)
    reset_cnt = await db.reset_all_balances_except(1002)
    assert reset_cnt >= 2, f"Expected >= 2, got {reset_cnt}"
    u1_f = await db.get_user(1001)
    u2_f = await db.get_user(1002)
    u3_f = await db.get_user(1003)
    assert u1_f["balance_uzs"] == 0.0
    assert u2_f["balance_uzs"] == 120000.0
    assert u3_f["balance_uzs"] == 0.0

    if os.path.exists(db_path):
        os.remove(db_path)
    print("ALL BALANCE UNIT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
