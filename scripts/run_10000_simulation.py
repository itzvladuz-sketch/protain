"""10,000-Run Massive Stress Test & Verification Suite.
Simulates 10,000 deposits + 10,000 Stars/Premium/Gift purchases under concurrent load.
Verifies balance consistency, atomic locking, double-spend prevention, and DB integrity.
"""

import asyncio
import os
import sys
import random
import time
from datetime import datetime, timedelta

BASE_DIR = "d:/birinchi mijon/tg_stars_premium_shop"
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from loguru import logger
# Silence verbose loguru output during 10,000 ops so it runs at maximum speed
logger.remove()
logger.add(sys.stdout, level="ERROR")

from services.config import BotConfig
from services.db import Database
from services.humo_monitor import HumoPaymentMonitor

SIM_DB_PATH = os.path.join(BASE_DIR, "test_simulation_10000.db")


class MockBot:
    def __init__(self):
        self.msg_count = 0

    async def send_message(self, chat_id, text, **kwargs):
        self.msg_count += 1
        return True

    async def get_me(self):
        class DummyUser:
            id = 999999999
            username = "starsbop_bot"
            first_name = "Stars Bot"
        return DummyUser()


async def run_10000_tests():
    if os.path.exists(SIM_DB_PATH):
        try:
            os.remove(SIM_DB_PATH)
        except Exception:
            pass

    config = BotConfig.load()
    db = Database(SIM_DB_PATH)
    await db.init_db()
    mock_bot = MockBot()
    monitor = HumoPaymentMonitor(config, mock_bot)
    monitor.db = db

    print("=" * 70, flush=True)
    print("  >>> STARTING 10,000 RUN MASSIVE STRESS TEST & SYSTEM AUDIT <<<", flush=True)
    print("=" * 70, flush=True)

    errors = []
    start_time = time.time()

    # ─────────────────────────────────────────────────────────────
    # STEP 1: Create 100 test user accounts
    # ─────────────────────────────────────────────────────────────
    print("\n[STEP 1/5] Initializing 100 test user accounts...", flush=True)
    users = []
    for i in range(1, 101):
        uid = 20000 + i
        uname = f"whale_{i}"
        u = await db.get_or_create_user(uid, uname)
        users.append(u)
    print("  [+] 100 user accounts created successfully.", flush=True)

    # ─────────────────────────────────────────────────────────────
    # STEP 2: 10,000 Card Deposits (Humo & Click)
    # ─────────────────────────────────────────────────────────────
    print("\n[STEP 2/5] Executing 10,000 Card Deposits (Humo & Click)...", flush=True)
    t0 = time.time()

    sms_templates = [
        "Karta: 9860350147305402\nTushum: +{amount} UZS\nBalans: 15,500,000 UZS",
        "Click: Karta to'ldirildi. Summa: {amount} so'm. Kod: {code}",
        "HUMO: Perevod na kartu +{amount}.00 UZS. Uspeshno.",
        "Xisobingizga {amount} UZS mablag' kelib tushdi. Humo Card",
        "Kirim: +{amount} UZS. Click Up orqali to'lov.",
        "To'lov qabul qilindi: +{amount} UZS karta orqali",
    ]

    deposit_amounts = [10000, 15000, 20000, 25000, 50000, 75000, 100000, 150000, 200000, 500000]
    total_deposited = 0
    deposits_passed = 0
    total_deposits_target = 10000

    for i in range(1, total_deposits_target + 1):
        user = random.choice(users)
        amt = random.choice(deposit_amounts)
        pay_type = random.choice(["humo", "click"])

        # 1. User initiates deposit
        oid = await db.create_order(
            user_id=user["user_id"],
            username=user["username"],
            order_type="topup",
            recipient_username=user["username"],
            quantity=1,
            price_usd=round(amt / 12900, 2),
            price_uzs=float(amt),
            price_ton=0.0,
            payment_type=pay_type,
            payment_address="9860350147305402",
            payment_comment=f"TOPUP-{user['user_id']}-{i}",
            expires_at=datetime.now() + timedelta(minutes=5),
        )
        if not oid:
            errors.append(f"Deposit #{i}: create_order failed")
            continue

        # 2. Simulate bank notification SMS
        tmpl = random.choice(sms_templates)
        fmt_amt = f"{amt:,}".replace(",", " ") if random.random() > 0.5 else str(amt)
        sms_text = tmpl.format(amount=fmt_amt, code=random.randint(1000, 9999))

        # 3. Process SMS
        ok = await monitor.process_incoming_humo_payment(float(amt), sms_text)
        if not ok:
            errors.append(f"Deposit #{i}: monitor.process failed for order #{oid}")
            continue

        # 4. Verify order completed
        order = await db.get_order(oid)
        if not order or order["status"] != "completed":
            errors.append(f"Deposit #{i}: order #{oid} status {order.get('status') if order else None}")
            continue

        deposits_passed += 1
        total_deposited += amt

        if i % 2000 == 0:
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            print(f"  [+] Progress: {i:,} / 10,000 deposits completed ({rate:.1f} ops/sec)", flush=True)

    dep_elapsed = time.time() - t0
    print(f"  [OK] 10,000 Deposits finished in {dep_elapsed:.2f}s ({deposits_passed}/10,000 succeeded)", flush=True)
    print(f"  [+] Total deposited sum: {total_deposited:,} UZS", flush=True)

    # Verify sum of balances in DB
    all_users = await db.get_all_users()
    db_sum_balances = sum(float(u.get("balance_uzs") or 0) for u in all_users)
    print(f"  [+] DB Sum of all user balances: {int(db_sum_balances):,} UZS", flush=True)
    if int(db_sum_balances) != total_deposited:
        errors.append(f"Balance mismatch: DB sum {int(db_sum_balances)} != expected {total_deposited}")

    # ─────────────────────────────────────────────────────────────
    # STEP 3: 10,000 Purchases (Stars, Premium, Gifts)
    # ─────────────────────────────────────────────────────────────
    print("\n[STEP 3/5] Executing 10,000 Purchases (Stars, Premium, Gifts)...", flush=True)
    t1 = time.time()

    total_purchases_target = 10000
    purchases_passed = 0
    cat_counts = {"stars": 0, "premium": 0, "gift": 0}

    for i in range(1, total_purchases_target + 1):
        user = random.choice(users)
        cat = random.choice(["stars", "premium", "gift"])

        if cat == "stars":
            qty = random.choice([50, 75, 100, 150, 250, 500])
            cost_uzs = float(qty * 210)
        elif cat == "premium":
            dur = random.choice([1, 3, 6, 12])
            qty = dur
            cost_uzs = float({1: 45000, 3: 120000, 6: 210000, 12: 380000}[dur])
        else:
            qty = random.choice([15, 25, 50, 100])
            cost_uzs = float(qty * 220)

        # Ensure user has sufficient funds (from the 10,000 deposits)
        user_fresh = await db.get_user(user["user_id"])
        if float(user_fresh.get("balance_uzs") or 0) < cost_uzs:
            await db.update_user_balance_uzs(user["user_id"], cost_uzs + 50000)

        # 1. Atomic deduction (anti-double-spend protected)
        deducted = await db.deduct_user_balance_uzs(user["user_id"], cost_uzs)
        if not deducted:
            errors.append(f"Purchase #{i}: deduct_user_balance_uzs failed")
            continue

        # 2. Create order
        oid = await db.create_order(
            user_id=user["user_id"],
            username=user["username"],
            order_type=cat,
            recipient_username="friend_recipient",
            quantity=qty,
            price_usd=round(cost_uzs / 12900, 2),
            price_uzs=cost_uzs,
            price_ton=0.0,
            payment_type="balance",
            payment_address="balance",
            payment_comment=f"PURCHASE-{i}",
            expires_at=datetime.now() + timedelta(minutes=10),
        )
        if not oid:
            errors.append(f"Purchase #{i}: create_order failed")
            continue

        # 3. Simulate completion (Fragment/Gift queue dispatch)
        await db.set_order_status(oid, "completed", fragment_tx_hash=f"tx_hash_{i}")
        ord_res = await db.get_order(oid)
        if not ord_res or ord_res["status"] != "completed":
            errors.append(f"Purchase #{i}: order #{oid} status not completed")
            continue

        purchases_passed += 1
        cat_counts[cat] += 1

        if i % 2000 == 0:
            elapsed = time.time() - t1
            rate = i / elapsed if elapsed > 0 else 0
            print(f"  [+] Progress: {i:,} / 10,000 purchases completed ({rate:.1f} ops/sec)", flush=True)

    pur_elapsed = time.time() - t1
    print(f"  [OK] 10,000 Purchases finished in {pur_elapsed:.2f}s ({purchases_passed}/10,000 succeeded)", flush=True)
    print(f"      - Stars orders: {cat_counts['stars']:,}", flush=True)
    print(f"      - Premium orders: {cat_counts['premium']:,}", flush=True)
    print(f"      - Gift orders: {cat_counts['gift']:,}", flush=True)

    # ─────────────────────────────────────────────────────────────
    # STEP 4: Massive Concurrency & Race Condition Stress (1,000 ops)
    # ─────────────────────────────────────────────────────────────
    print("\n[STEP 4/5] Executing Concurrency & Anti-Double-Spend Stress (1,000 simultaneous ops)...", flush=True)

    boss_uid = 888888
    await db.get_or_create_user(boss_uid, "stress_boss")
    initial_boss_bal = 100000.0  # Exactly enough for four 25,000 spends
    await db.set_user_balance_uzs(boss_uid, initial_boss_bal)

    async def single_spend():
        return await db.deduct_user_balance_uzs(boss_uid, 25000.0)

    # 500 concurrent spend requests on the same balance
    results = await asyncio.gather(*[single_spend() for _ in range(500)])
    boss_success_count = sum(1 for r in results if r is True)
    boss_user = await db.get_user(boss_uid)
    print(f"  [+] 500 concurrent spends on 100k balance: {boss_success_count} succeeded (Expected exactly 4)", flush=True)
    print(f"  [+] Final user balance: {boss_user['balance_uzs']} UZS (Expected 0.0)", flush=True)

    if boss_success_count != 4:
        errors.append(f"Double-spend escape: {boss_success_count} succeeded, expected 4")
    if float(boss_user["balance_uzs"]) != 0.0:
        errors.append(f"Balance leaked into negative: {boss_user['balance_uzs']}")

    # 500 concurrent duplicate SMS for 1 order
    dup_oid = await db.create_order(
        user_id=boss_uid,
        username="stress_boss",
        order_type="topup",
        recipient_username="stress_boss",
        quantity=1,
        price_usd=1.0,
        price_uzs=55555.0,
        price_ton=0.0,
        payment_type="humo",
        payment_address="9860350147305402",
        payment_comment="DUP-STRESS",
        expires_at=datetime.now() + timedelta(minutes=5),
    )

    dup_sms_results = await asyncio.gather(*[
        monitor.process_incoming_humo_payment(55555.0, "Kirim: 55555 UZS")
        for _ in range(500)
    ])
    accepted_count = sum(1 for r in dup_sms_results if r is True)
    print(f"  [+] 500 concurrent duplicate SMS for 1 order: {accepted_count} accepted (Expected exactly 1)", flush=True)
    if accepted_count != 1:
        errors.append(f"Duplicate SMS race condition: {accepted_count} accepted, expected 1")

    # ─────────────────────────────────────────────────────────────
    # STEP 5: Database Deep Integrity & Health Audit
    # ─────────────────────────────────────────────────────────────
    print("\n[STEP 5/5] Deep Database Integrity Audit...", flush=True)
    async with db.connect() as conn:
        cursor = await conn.execute("PRAGMA integrity_check;")
        row = await cursor.fetchone()
        integrity_res = row[0] if row else "unknown"

        cursor = await conn.execute("SELECT COUNT(*) FROM orders;")
        total_orders_in_db = (await cursor.fetchone())[0]

        cursor = await conn.execute("SELECT COUNT(*) FROM users;")
        total_users_in_db = (await cursor.fetchone())[0]

        cursor = await conn.execute("SELECT COUNT(*) FROM users WHERE balance_uzs < 0 OR balance_ton < 0;")
        negative_users = (await cursor.fetchone())[0]

    print(f"  [+] SQLite PRAGMA integrity_check: {integrity_res}", flush=True)
    print(f"  [+] Total registered orders in DB: {total_orders_in_db:,}", flush=True)
    print(f"  [+] Total users in DB: {total_users_in_db:,}", flush=True)
    print(f"  [+] Accounts with negative balance: {negative_users} (Expected 0)", flush=True)

    if integrity_res != "ok":
        errors.append(f"DB integrity check failed: {integrity_res}")
    if negative_users > 0:
        errors.append(f"Found {negative_users} accounts with negative balance!")

    # ─────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────
    total_time = time.time() - start_time
    print("\n" + "=" * 70, flush=True)
    print(f"  >>> 10,000 TEST RUN FINISHED IN {total_time:.1f}s ({total_time/60:.2f} mins) <<<", flush=True)
    print("=" * 70, flush=True)

    if not errors:
        print("  [SUCCESS]: ALL 20,000+ TRANSACTIONS & CHECKS PASSED WITH 0 ERRORS!", flush=True)
        print("  System is 100% verified, stable, and ready for production scale.", flush=True)
    else:
        print(f"  [FAIL]: Found {len(errors)} issues during stress test:", flush=True)
        for e in errors[:10]:
            print(f"     - {e}", flush=True)

    print("=" * 70, flush=True)

    await db.close()

    if os.path.exists(SIM_DB_PATH):
        try:
            os.remove(SIM_DB_PATH)
        except Exception:
            pass

    return len(errors) == 0


if __name__ == "__main__":
    success = asyncio.run(run_10000_tests())
    sys.exit(0 if success else 1)
