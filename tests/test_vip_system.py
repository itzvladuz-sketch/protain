"""Comprehensive Test Suite for VIP Optom Tarif System."""

import asyncio
import os
import sys
from datetime import datetime, timedelta

BASE_DIR = "d:/birinchi mijon/tg_stars_premium_shop"
sys.path.insert(0, BASE_DIR)

from services.config import BotConfig
from services.db import Database
from handlers.order import _calc_price
from services.humo_monitor import HumoPaymentMonitor

TEST_DB = os.path.join(BASE_DIR, "test_vip.db")

class DummyBot:
    async def send_message(self, *args, **kwargs):
        return True

async def test_vip():
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass

    from dataclasses import replace
    config = BotConfig.load()
    config = replace(config, database_path=TEST_DB)
    db = Database(TEST_DB)
    await db.init_db()

    print("=" * 65)
    print("  TESTING VIP OPTOM TARIF SYSTEM")
    print("=" * 65)

    uid = 555888
    u = await db.get_or_create_user(uid, "vip_customer")
    assert u["user_id"] == uid

    # 1. Check initial VIP status
    is_vip = await db.is_user_vip(uid)
    assert is_vip is False
    print("  [+] Initial non-VIP status verified: OK")

    # 2. Check regular price (must have commission)
    reg_price = await _calc_price(config, "stars", 100, user_id=uid)
    assert reg_price["is_vip"] is False
    # base is 0.015 * 100 = 1.5 USD; with commission: 1.5 * 1.085168 = 1.6278
    assert reg_price["price_usd"] > 1.50
    print(f"  [+] Regular price for 100 stars: ${reg_price['price_usd']} (with commission): OK")

    # 3. Grant 1-day VIP
    exp_iso = await db.set_user_vip(uid, 1)
    is_vip_now = await db.is_user_vip(uid)
    assert is_vip_now is True
    vip_info = await db.get_user_vip_info(uid)
    assert vip_info["is_vip"] is True
    print(f"  [+] 1-day VIP granted (Expires: {vip_info['vip_until']}): OK")

    # 4. Check VIP price for 100 stars (must be 0% commission / wholesale)
    vip_price = await _calc_price(config, "stars", 100, user_id=uid)
    assert vip_price["is_vip"] is True
    assert vip_price["price_usd"] == 1.50  # Exactly raw cost: 100 * 0.015
    savings_usd = reg_price["price_usd"] - vip_price["price_usd"]
    savings_uzs = round(savings_usd * 12900)
    print(f"  [+] VIP wholesale price for 100 stars: ${vip_price['price_usd']} (Savings: {savings_uzs} so'm): OK")

    # 5. Extend VIP by 7 days
    exp_extended = await db.set_user_vip(uid, 7)
    exp_dt = datetime.fromisoformat(exp_extended)
    assert exp_dt > datetime.now() + timedelta(days=7)
    info_ext = await db.get_user_vip_info(uid)
    assert info_ext["days_left"] >= 7
    print(f"  [+] VIP extended by 7 days (Total days left: {info_ext['days_left']}): OK")

    # 6. Test VIP plans pricing
    plans = await db.get_vip_plans()
    assert "vip_1d" in plans
    assert plans["vip_1d"]["price_uzs"] == 9900.0
    assert plans["vip_7d"]["price_uzs"] == 25000.0
    assert plans["vip_15d"]["price_uzs"] == 45000.0
    print("  [+] VIP plans retrieved (9,900 / 25,000 / 45,000 so'm): OK")

    # 7. Test active VIP users listing
    active_vips = await db.get_active_vip_users()
    assert len(active_vips) == 1
    assert active_vips[0]["user_id"] == uid
    print("  [+] Active VIP users list retrieval: OK")

    # 8. Test Humo/Click card payment for VIP order
    uid2 = 666999
    await db.get_or_create_user(uid2, "humo_vip_user")
    order_id = await db.create_order(
        user_id=uid2,
        username="humo_vip_user",
        order_type="vip_1d",
        recipient_username="humo_vip_user",
        quantity=1,
        price_usd=0.77,
        price_ton=0.0,
        price_uzs=9900.0,
        payment_type="humo",
        payment_address="9860350147305402",
        payment_comment=f"VIP-1D-{uid2}",
        expires_at=datetime.now() + timedelta(minutes=5),
    )

    monitor = HumoPaymentMonitor(config, DummyBot())
    monitor.db = db
    # Process incoming payment of 9,900 UZS
    res = await monitor.process_incoming_humo_payment(9900.0, "Karta to'ldirildi: +9900 UZS")
    assert res is True
    # Verify uid2 is now VIP
    assert await db.is_user_vip(uid2) is True
    ord_db = await db.get_order(order_id)
    assert ord_db["status"] == "completed"
    print("  [+] Automatic Humo/Click payment activation of VIP: OK")

    # 9. Cancel VIP
    cancelled = await db.cancel_user_vip(uid)
    assert cancelled is True
    assert await db.is_user_vip(uid) is False
    print("  [+] Admin cancellation of VIP: OK")

    await db.close()

    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass

    print("=" * 65)
    print("   ALL VIP OPTOM TARIF TESTS PASSED 100% SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(test_vip())
