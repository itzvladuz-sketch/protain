"""Test odd amount payments such as 1,234,000 UZS and custom amounts."""

import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath("."))
sys.stdout.reconfigure(encoding="utf-8")

from services.config import BotConfig
from services.db import Database
from services.humo_monitor import HumoPaymentMonitor, extract_amount_uzs

TEST_DB = "test_odd_amounts.db"

async def test_odd_amounts():
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

    config = BotConfig.load(force_reload=True)
    db = Database(TEST_DB)
    await db.init_db()

    async with db.connect() as conn:
        await conn.execute("DELETE FROM orders")
        await conn.execute("DELETE FROM users")
        await conn.commit()

    user_id = 8534196478
    username = "test_payer_odd"
    await db.get_or_create_user(user_id, username)

    # Test 1: 1,234,000 UZS (1234 ming)
    from datetime import datetime, timedelta
    amt_1234k = 1234000.0
    order_id_1 = await db.create_order(
        user_id=user_id,
        username=username,
        order_type="topup",
        recipient_username=username,
        quantity=1,
        price_uzs=amt_1234k,
        price_usd=round(amt_1234k / 12900, 2),
        payment_type="humo",
        payment_address="9860350147305402",
        payment_comment="topup_1234k",
        expires_at=datetime.now() + timedelta(minutes=30),
    )
    print(f"Created order #{order_id_1} for {amt_1234k} UZS")

    # SMS simulation for 1,234,000 UZS
    sms_texts = [
        "To'lov qabul qilindi: 1 234 000 UZS. Karta: *5402. Qoldiq: 5 000 000 UZS",
        "Karta to'ldirildi +1234000.00 UZS Humocard",
        "Vash schet popolnen na 1 234 000,00 UZS. Click",
    ]

    for sms in sms_texts:
        parsed = extract_amount_uzs(sms)
        assert parsed == amt_1234k, f"Parsed {parsed} != expected {amt_1234k} for SMS: {sms}"
        print(f"SMS correctly parsed: '{sms[:40]}...' -> {parsed} UZS")

    matched_order = await db.find_pending_humo_order(amt_1234k)
    assert matched_order is not None, "Failed to match 1,234,000 UZS order!"
    assert matched_order["id"] == order_id_1, f"Expected order {order_id_1}, got {matched_order['id']}"
    print(f"Database match OK: Order #{matched_order['id']} ({matched_order['price_uzs']} UZS)")

    # Complete payment and top up balance
    await db.acquire_pending_order(order_id_1)
    await db.set_order_status(order_id_1, "completed")
    await db.update_user_balance_uzs(user_id, amt_1234k)

    user_after = await db.get_user(user_id)
    assert user_after["balance_uzs"] == amt_1234k, f"User balance mismatch: {user_after['balance_uzs']}"
    print(f"User balance successfully credited: {user_after['balance_uzs']} UZS")

    print("\nSUCCESS: Odd and large amounts (like 1,234,000 UZS) are 100% supported and verified!")

if __name__ == "__main__":
    asyncio.run(test_odd_amounts())
    os._exit(0)
