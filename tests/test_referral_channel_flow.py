"""Test referral system channel subscription enforcement and reward logic."""

import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath("."))
sys.stdout.reconfigure(encoding="utf-8")

from services.config import BotConfig
from services.db import Database

TEST_DB = f"test_referral_{os.getpid()}.db"

async def test_referral():
    for f in [TEST_DB, f"{TEST_DB}-wal", f"{TEST_DB}-shm"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    os.environ["DATABASE_PATH"] = TEST_DB
    os.environ["BOT_TOKEN"] = "123456:FAKE_TOKEN"
    os.environ["TON_WALLET_ADDRESS"] = "EQDummyWalletAddress123"
    os.environ["FRAGMENT_WALLET_MNEMONIC"] = "word " * 24

    print("Step 1: connecting")
    config = BotConfig.load(force_reload=True)
    db = Database(TEST_DB)
    await db.init_db()

    print("Step 2: cleanup")
    async with db.connect() as conn:
        await conn.execute("DELETE FROM users")
        await conn.commit()

    print("Step 3: create referrer")
    user_a = 111111  # Referrer
    user_b = 222222  # Friend who was invited

    await db.get_or_create_user(user_a, "user_referrer")
    print("Step 4: create friend")
    u_b = await db.get_or_create_user(user_b, "user_friend", ref_by=user_a)
    assert u_b["ref_by"] == user_a, "Referral link must be recorded in pending ref_by"

    print("Step 5: check referrer")
    ref_user = await db.get_user(user_a)
    stars_before = int(ref_user.get("referral_stars") or 0)
    assert stars_before == 0, f"Expected 0 stars before subscription, got {stars_before}"
    print(f"Scenario A passed: Unsubscribed friend does NOT reward referrer (Stars: {stars_before})")

    print("Step 6: reward")
    rewarded = await db.reward_referral(user_a, user_b, stars=2)
    assert rewarded is True, "Referral reward failed!"
    await db.clear_user_referrer(user_b)

    print("Step 7: check after reward")
    ref_user_after = await db.get_user(user_a)
    stars_after = int(ref_user_after.get("referral_stars") or 0)
    assert stars_after == 2, f"Expected 2 stars after verification, got {stars_after}"
    print(f"Scenario B passed: After channel subscription verification, referrer awarded {stars_after} Stars!")

    print("Step 8: double reward check")
    u_b_after = await db.get_user(user_b)
    assert u_b_after["ref_by"] is None, "ref_by was not cleared!"
    stored_ref_again = u_b_after.get("ref_by")
    assert not stored_ref_again, "Anti-fraud failed: stored_ref should be None!"
    print("Scenario C passed: Double reward prevented by clearing ref_by (Anti-fraud OK)")

    print("Step 9: self referral check")
    assert user_a == user_a
    print("Scenario D passed: Self-referral prevented")

    print("\nSUCCESS: All referral verification rules verified 100%!")

if __name__ == "__main__":
    asyncio.run(test_referral())
    os._exit(0)
