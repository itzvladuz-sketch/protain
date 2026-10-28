"""Test exact 5432 UZS custom amount payment scenario."""

import asyncio
import os
import sys

BASE_DIR = "d:/birinchi mijon/tg_stars_premium_shop"
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv()

from services.config import BotConfig
from services.db import Database
from services.humo_monitor import HumoPaymentMonitor, extract_amount_uzs
from unittest.mock import AsyncMock, MagicMock

async def test_5432_flow():
    print("=" * 60)
    print("  TESTING EXACT 5432 UZS USER PAYMENT")
    print("=" * 60)

    test_db = os.path.join(BASE_DIR, "test_5432.db")
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except Exception:
            pass

    db = Database(test_db)
    await db.init_db()

    cfg = BotConfig.load()
    bot = MagicMock()
    bot.send_message = AsyncMock()

    # 1. User with ID 999111 starts with 0 UZS
    uid = 999111
    user = await db.get_or_create_user(uid, "test_payer_5432")
    assert user["balance_uzs"] == 0.0
    print("  [+] User created with 0 UZS balance: OK")

    # 2. User inputs custom topup: 5432 UZS
    from datetime import datetime, timedelta
    amt_uzs = 5432.0
    order_id = await db.create_order(
        user_id=uid,
        username="test_payer_5432",
        order_type="topup",
        recipient_username="test_payer_5432",
        quantity=int(amt_uzs),
        price_usd=round(amt_uzs / 12900, 2),
        price_ton=0.0,
        price_uzs=amt_uzs,
        discount_percent=0.0,
        payment_type="humo",
        payment_address="9860 3501 4730 5402",
        payment_comment=f"HUMO-{uid}",
        expires_at=datetime.now() + timedelta(minutes=15),
    )
    assert order_id > 0
    print(f"  [+] Pending topup order #{order_id} created for {int(amt_uzs)} so'm: OK")

    # 3. Bank sends notification about +5432 UZS
    sms = "Karta to'ldirildi: +5 432 UZS. Karta: 9860****5402. Balans: 100 000 UZS"
    parsed_amt = extract_amount_uzs(sms)
    assert parsed_amt == 5432.0
    print(f"  [+] SMS parsed amount: {parsed_amt} so'm: OK")

    # 4. Humo monitor processes incoming payment
    monitor = HumoPaymentMonitor(cfg, bot)
    monitor.db = db
    confirmed = await monitor.process_incoming_humo_payment(parsed_amt, sms)
    assert confirmed is True
    print("  [+] Automatic payment confirmation: OK")

    # 5. Check user balance updated to 5432 UZS
    user_after = await db.get_user(uid)
    assert user_after["balance_uzs"] == 5432.0
    print(f"  [+] User new balance in DB: {user_after['balance_uzs']} so'm: OK")

    # 6. Check order status is completed
    order = await db.get_order(order_id)
    assert order["status"] == "completed"
    print("  [+] Order status is 'completed': OK")

    # 7. Check user received notification
    assert bot.send_message.called
    print("  [+] User & Admin notifications delivered: OK")

    try:
        if os.path.exists(test_db):
            os.remove(test_db)
    except Exception:
        pass

    print("=" * 60)
    print("  5432 UZS TEST COMPLETED WITH 100% SUCCESS!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_5432_flow())
    os._exit(0)
