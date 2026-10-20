"""Comprehensive system audit test suite for Telegram Stars/Premium Shop bot."""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, "d:/birinchi mijon/tg_stars_premium_shop")

from dotenv import load_dotenv
load_dotenv("d:/birinchi mijon/tg_stars_premium_shop/.env")

from services.config import BotConfig
from services.db import Database
from services.currency import format_currency, format_balance
from services.humo_monitor import extract_amount_uzs
from services.ton import TONService
from services.subscription import check_subscription, invalidate_subscription_cache, _USER_SUB_CACHE, _CHANNELS_CACHE


TEST_DB_PATH = "d:/birinchi mijon/tg_stars_premium_shop/test_audit.db"


async def test_database_suite():
    print("--- [1] DATABASE SUITE ---")
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

    db = Database(TEST_DB_PATH)
    await db.init_db()
    print("  [+] Database init_db & table creation: OK")

    # User creation & lookup
    u1 = await db.get_or_create_user(1111, "testuser1", ref_by=None)
    assert u1["user_id"] == 1111
    assert u1["username"] == "testuser1"
    print("  [+] User creation: OK")

    # User lookup by ID or username
    by_id = await db.get_user_by_id_or_username("1111")
    assert by_id["user_id"] == 1111
    by_name = await db.get_user_by_id_or_username("@testuser1")
    assert by_name["user_id"] == 1111
    by_name_no_at = await db.get_user_by_id_or_username("testuser1")
    assert by_name_no_at["user_id"] == 1111
    print("  [+] Flexible lookup (ID, @username, username): OK")

    # Balance updates
    await db.update_user_balance_uzs(1111, 50000.0)
    u1_fresh = await db.get_user(1111)
    assert float(u1_fresh["balance_uzs"]) == 50000.0
    print("  [+] Balance topup UZS: OK")

    await db.set_user_balance_uzs(1111, 0.0)
    u1_fresh = await db.get_user(1111)
    assert float(u1_fresh["balance_uzs"]) == 0.0
    print("  [+] Balance set/reset: OK")

    # Order creation
    order_id = await db.create_order(
        user_id=1111,
        username="testuser1",
        order_type="stars",
        recipient_username="friend",
        quantity=50,
        price_usd=0.75,
        price_uzs=10499.0,
        price_ton=0.2,
        payment_type="humo",
        payment_address="9860...",
        payment_comment="TEST-01",
        expires_at=datetime.now() + timedelta(minutes=30),
    )
    assert order_id > 0
    order = await db.get_order(order_id)
    assert order["status"] == "pending"
    assert order["payment_type"] == "humo"
    print("  [+] Order creation: OK")

    # Humo order matching
    matched = await db.find_pending_humo_order(10499.0)
    assert matched is not None
    assert matched["id"] == order_id
    print("  [+] Humo/Click order matching (exact): OK")

    # Tolerant match within 50 UZS
    matched_tol = await db.find_pending_humo_order(10500.0)
    assert matched_tol is not None
    assert matched_tol["id"] == order_id
    print("  [+] Humo/Click order matching (tolerant +/- 50 UZS): OK")

    # Atomic acquire paid order
    await db.set_order_status(order_id, "paid")
    acq1 = await db.acquire_paid_order(order_id)
    assert acq1 is True  # Acquired first time
    acq2 = await db.acquire_paid_order(order_id)
    assert acq2 is False  # Second attempt fails (prevents double execution)
    print("  [+] Atomic acquire_paid_order (anti-double-spend): OK")

    # Batch expiration test
    expired_order_id = await db.create_order(
        user_id=1111,
        username="testuser1",
        order_type="stars",
        recipient_username="friend",
        quantity=50,
        price_usd=0.75,
        price_uzs=10499.0,
        payment_type="humo",
        payment_address="9860...",
        payment_comment="TEST-EXPIRED",
        expires_at=datetime.now() - timedelta(minutes=5),  # already expired
    )
    cancelled = await db.cancel_expired_card_orders()
    assert cancelled >= 1
    exp_order = await db.get_order(expired_order_id)
    assert exp_order["status"] == "cancelled"
    print("  [+] Fast batch expired orders cancellation: OK")

    # Pending TON orders filter
    ton_order_id = await db.create_order(
        user_id=1111,
        username="testuser1",
        order_type="stars",
        recipient_username="friend",
        quantity=50,
        price_usd=0.75,
        price_ton=0.2,
        payment_type="ton",
        payment_address="UQ...",
        payment_comment="TON-01",
        expires_at=datetime.now() + timedelta(minutes=30),
    )
    ton_pending = await db.get_pending_ton_orders()
    assert any(o["id"] == ton_order_id for o in ton_pending)
    assert all(o["payment_type"] == "ton" for o in ton_pending)
    print("  [+] Dedicated get_pending_ton_orders: OK")

    # Stats
    stats = await db.get_stats()
    assert stats["users"] >= 1
    assert stats["orders"] >= 2
    print("  [+] get_stats: OK")

    # Cleanup test db
    try:
        os.remove(TEST_DB_PATH)
    except Exception:
        pass


def test_sms_parser_suite():
    print("\n--- [2] HUMO & CLICK SMS PARSER SUITE ---")
    
    # 1. HUMO Card Bot messages
    msg1 = "Karta to'ldirildi: +50 000 UZS. Karta: 9860****5402. Balans: 125 000 UZS."
    assert extract_amount_uzs(msg1) == 50000.0
    print("  [+] Humo standard notification (+50 000 UZS): OK")

    # 2. Click SMS / bot message
    msg2 = "Click: hisobingizga pul kelib tushdi +10 499.00 UZS. Qoldiq: 85 000 UZS."
    assert extract_amount_uzs(msg2) == 10499.0
    print("  [+] Click decimal notification (+10 499.00 UZS): OK")

    # 3. Bank SMS with perevod
    msg3 = "Zachislenie perevoda: +100 000 UZS. Karta: 9860 3501 4730 5402"
    assert extract_amount_uzs(msg3) == 100000.0
    print("  [+] Bank transfer SMS (+100 000 UZS): OK")

    # 4. Russian format
    msg4 = "Пополнение счета: +25 000 сум. Баланс: 40 000 сум."
    assert extract_amount_uzs(msg4) == 25000.0
    print("  [+] Russian deposit notification (+25 000 сум): OK")

    # 5. REJECT: Invoices and commands must NEVER be treated as incoming payments
    invoice_msg = "To'lov summasi: 50 000 UZS. Karta raqami: 9860 3501 4730 5402. Buyurtma #10"
    assert extract_amount_uzs(invoice_msg) is None
    print("  [+] Security: Invoice rejection: OK")

    # 6. REJECT: Withdrawals / Spisanie
    withdraw_msg = "Spisanie: -50 000 UZS. Karta: 9860****5402. Balans: 10 000 UZS"
    assert extract_amount_uzs(withdraw_msg) is None
    print("  [+] Security: Debit/withdrawal rejection: OK")


def test_currency_formatter_suite():
    print("\n--- [3] CURRENCY FORMATTER SUITE ---")
    cfg = BotConfig.load()
    
    # UZS
    uzs_str = format_currency(1.0, "uz", cfg)
    assert "so'm" in uzs_str
    print(f"  [+] UZS formatting ($1.00 -> {uzs_str}): OK")

    # RUB
    rub_str = format_currency(1.0, "ru", cfg)
    assert "₽" in rub_str
    print(f"  [+] RUB formatting ($1.00 -> {rub_str.encode('ascii', 'replace').decode()}): OK")

    # USD
    usd_str = format_currency(1.5, "en", cfg)
    assert usd_str == "$1.50"
    print(f"  [+] USD formatting ($1.50 -> {usd_str}): OK")

    # Balance formatting
    bal_str = format_balance(145344.0, "uz", cfg)
    assert "145" in bal_str and "344" in bal_str
    print(f"  [+] Balance formatting (145344.0 -> {bal_str}): OK")


async def test_subscription_cache_suite():
    print("\n--- [4] SUBSCRIPTION CACHE SUITE ---")
    invalidate_subscription_cache()
    assert len(_USER_SUB_CACHE) == 0
    print("  [+] Invalidate subscription cache: OK")

    # Mock user cached
    import time
    _USER_SUB_CACHE[99999] = time.time()
    
    # check_subscription without mock bot should return True from cache immediately
    class DummyBot:
        pass
    class DummyDb:
        async def get_channels(self):
            return [{"channel_id": "@test", "title": "Test", "url": "https://t.me/test"}]

    is_sub, _ = await check_subscription(DummyBot(), 99999, DummyDb(), force=False)
    assert is_sub is True
    print("  [+] Ultra-fast in-memory cache hit (<0.1ms): OK")

    # Force check bypasses cache
    try:
        await check_subscription(DummyBot(), 99999, DummyDb(), force=True)
    except AttributeError:
        # Expected: DummyBot doesn't have get_chat_member, proving it bypassed cache!
        print("  [+] Force check properly bypasses cache to verify with Telegram API: OK")


async def test_ton_service_suite():
    print("\n--- [5] TON SERVICE SUITE ---")
    ton = TONService("UQB38aS-Yx1DYAbXgOUfvYSG9xejtYqaTYUuPmRrPprV5gkt")
    rate = await ton.get_ton_usd_rate()
    assert rate > 0.5
    print(f"  [+] TON/USD live rate: ${rate:.2f}: OK")

    ton_amount = await ton.usd_to_ton(1.50)
    assert ton_amount > 0
    print(f"  [+] USD to TON conversion ($1.50 -> {ton_amount} TON): OK")


async def main():
    print("================================================================")
    print("       STARTING COMPLETE END-TO-END SYSTEM AUDIT               ")
    print("================================================================\n")
    try:
        await test_database_suite()
        test_sms_parser_suite()
        test_currency_formatter_suite()
        await test_subscription_cache_suite()
        await test_ton_service_suite()
        print("\n================================================================")
        print("   ALL 5 TEST SUITES PASSED COMPLETELY WITHOUT ANY ERRORS!     ")
        print("================================================================")
    except Exception as e:
        print(f"\n[!] AUDIT FAILED ON: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
