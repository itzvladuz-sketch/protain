"""Full-featured SQLite database for Stars Shop bot.

Tables:
- users: bot users with lang, balance, ban status
- orders: all purchase orders (stars/premium/gift)
- prices: configurable prices per service
- settings: key-value admin settings
- broadcasts: broadcast history
"""

from __future__ import annotations

import asyncio

from contextlib import asynccontextmanager
from datetime import datetime, date, timedelta
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional

import aiosqlite
from loguru import logger


# ─────────────────────────────────────────────────────────────────────────────
# Default prices seeded at startup
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_PRICES = [
    # (service_key, base_price_usd, commission_percent, discount_percent, min_qty, max_qty)
    ("stars",        0.015,  8.5168, 0.0,    50,    50000),
    ("premium_1m",   3.99,   0.0, 0.0,    1,     1),
    ("premium_3m",   9.99,   0.0, 0.0,    1,     1),
    ("premium_6m",   17.99,  0.0, 0.0,    1,     1),
    ("premium_12m",  34.99,  0.0, 0.0,    1,     1),
    ("gift_15",      0.225,  0.0, 0.0,    15,    15),
    ("gift_25",      0.375,  0.0, 0.0,    25,    25),
    ("gift_rose",    0.375,  0.0, 0.0,    25,    25),
    ("gift_cake",    0.75,   0.0, 0.0,    50,    50),
    ("gift_rocket",  0.75,   0.0, 0.0,    50,    50),
    ("gift_diamond", 0.75,   0.0, 0.0,    50,    50),
    ("gift_champagne", 1.125, 0.0, 0.0,   75,    75),
    ("gift_box",     1.50,   0.0, 0.0,    100,   100),
    ("gift_trophy",  1.50,   0.0, 0.0,    100,   100),
]

STATUS_EMOJIS = {
    "pending":    "⏳",
    "paid":       "✅",
    "processing": "⚙️",
    "completed":  "🎉",
    "failed":     "❌",
    "cancelled":  "🚫",
    "expired":    "⏱️",
}


class Database:
    """Async SQLite wrapper for Stars Shop bot."""

    _prices_cache: Dict[str, Dict[str, Any]] = {}
    _prices_cache_time: float = 0.0

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._shared_conn: Optional[aiosqlite.Connection] = None
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        """Provide persistent SQLite connection with asyncio lock, WAL mode, and zero connection overhead."""
        lock = self._get_lock()
        async with lock:
            if self._shared_conn is None:
                self._shared_conn = await aiosqlite.connect(self.db_path, timeout=60.0)
                await self._shared_conn.execute("PRAGMA busy_timeout = 60000;")
                await self._shared_conn.execute("PRAGMA journal_mode = WAL;")
                await self._shared_conn.execute("PRAGMA synchronous = NORMAL;")
                await self._shared_conn.execute("PRAGMA cache_size = 10000;")
                await self._shared_conn.execute("PRAGMA temp_store = MEMORY;")
            yield self._shared_conn

    async def close(self) -> None:
        """Close persistent SQLite connection."""
        lock = self._get_lock()
        async with lock:
            if self._shared_conn is not None:
                try:
                    await self._shared_conn.close()
                except Exception:
                    pass
                self._shared_conn = None

    # ─── Init ────────────────────────────────────────────────────────────────

    async def init_db(self) -> None:
        """Create all tables and seed default prices."""
        async with self.connect() as db:
            await db.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;
                PRAGMA cache_size=10000;
                PRAGMA temp_store=MEMORY;
                PRAGMA busy_timeout=30000;

                CREATE TABLE IF NOT EXISTS users (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id         INTEGER NOT NULL UNIQUE,
                    username        TEXT,
                    lang            TEXT NOT NULL DEFAULT 'uz',
                    balance_ton     REAL NOT NULL DEFAULT 0.0,
                    balance_uzs     REAL NOT NULL DEFAULT 0.0,
                    ref_by          INTEGER DEFAULT NULL,
                    referral_stars  INTEGER NOT NULL DEFAULT 0,
                    referral_count  INTEGER NOT NULL DEFAULT 0,
                    is_banned       INTEGER NOT NULL DEFAULT 0,
                    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id             INTEGER NOT NULL,
                    username            TEXT,
                    order_type          TEXT NOT NULL DEFAULT 'stars',
                    recipient_username  TEXT,
                    stars               INTEGER NOT NULL DEFAULT 0,
                    quantity            INTEGER NOT NULL DEFAULT 0,
                    price_usd           REAL NOT NULL DEFAULT 0,
                    price_ton           REAL NOT NULL DEFAULT 0,
                    price_uzs           REAL NOT NULL DEFAULT 0,
                    discount_percent    REAL NOT NULL DEFAULT 0,
                    status              TEXT NOT NULL DEFAULT 'pending',
                    payment_type        TEXT NOT NULL DEFAULT 'ton',
                    payment_address     TEXT,
                    payment_comment     TEXT,
                    fragment_tx_hash    TEXT,
                    error_message       TEXT,
                    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at          TEXT NOT NULL,
                    paid_at             TEXT,
                    completed_at        TEXT
                );

                CREATE TABLE IF NOT EXISTS prices (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    service             TEXT NOT NULL UNIQUE,
                    base_price_usd      REAL NOT NULL DEFAULT 0.015,
                    commission_percent  REAL NOT NULL DEFAULT 5.0,
                    discount_percent    REAL NOT NULL DEFAULT 0.0,
                    min_qty             INTEGER NOT NULL DEFAULT 1,
                    max_qty             INTEGER NOT NULL DEFAULT 50000,
                    is_active           INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE TABLE IF NOT EXISTS broadcasts (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id     INTEGER NOT NULL,
                    message_text TEXT NOT NULL,
                    sent_count   INTEGER NOT NULL DEFAULT 0,
                    fail_count   INTEGER NOT NULL DEFAULT 0,
                    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS channels (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id  TEXT NOT NULL UNIQUE,
                    title       TEXT NOT NULL,
                    url         TEXT NOT NULL,
                    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS gift_requests (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id             INTEGER NOT NULL,
                    username            TEXT,
                    recipient_username  TEXT NOT NULL,
                    stars_spent         INTEGER NOT NULL DEFAULT 16,
                    gift_name           TEXT NOT NULL,
                    status              TEXT NOT NULL DEFAULT 'pending',
                    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at        TEXT,
                    error_message       TEXT
                );

                CREATE TABLE IF NOT EXISTS balance_transactions (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id             INTEGER NOT NULL,
                    admin_id            INTEGER DEFAULT NULL,
                    tx_type             TEXT NOT NULL,
                    amount_uzs          REAL NOT NULL DEFAULT 0.0,
                    amount_ton          REAL NOT NULL DEFAULT 0.0,
                    old_balance_uzs     REAL NOT NULL DEFAULT 0.0,
                    new_balance_uzs     REAL NOT NULL DEFAULT 0.0,
                    order_id            INTEGER DEFAULT NULL,
                    comment             TEXT,
                    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS withdraw_requests (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id         INTEGER NOT NULL,
                    username        TEXT,
                    card_number     TEXT NOT NULL,
                    card_holder     TEXT DEFAULT NULL,
                    amount_uzs      REAL NOT NULL,
                    status          TEXT NOT NULL DEFAULT 'pending',
                    admin_id        INTEGER DEFAULT NULL,
                    admin_note      TEXT DEFAULT NULL,
                    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    processed_at    TEXT DEFAULT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
                CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
                CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
                CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders(payment_type, status);
                CREATE INDEX IF NOT EXISTS idx_orders_expires ON orders(expires_at);
                CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
                CREATE INDEX IF NOT EXISTS idx_gift_requests_status ON gift_requests(status);
                CREATE INDEX IF NOT EXISTS idx_bt_user ON balance_transactions(user_id);
                CREATE INDEX IF NOT EXISTS idx_bt_type ON balance_transactions(tx_type);
                CREATE INDEX IF NOT EXISTS idx_bt_created ON balance_transactions(created_at);
                CREATE INDEX IF NOT EXISTS idx_wr_status ON withdraw_requests(status);
                CREATE INDEX IF NOT EXISTS idx_wr_user ON withdraw_requests(user_id);
            """)
            await db.commit()
            await self._ensure_orders_columns(db)
            await self._ensure_users_columns(db)

        await self.init_default_prices()
        logger.info("Database ready: {}", self.db_path)

    async def _ensure_users_columns(self, db: aiosqlite.Connection) -> None:
        """Add missing columns to users table if table already existed."""
        cursor = await db.execute("PRAGMA table_info(users)")
        existing = {row[1] for row in await cursor.fetchall()}
        columns = {
            "balance_uzs": "REAL NOT NULL DEFAULT 0.0",
            "ref_by": "INTEGER DEFAULT NULL",
            "referral_stars": "INTEGER NOT NULL DEFAULT 0",
            "referral_count": "INTEGER NOT NULL DEFAULT 0",
            "vip_until": "TEXT DEFAULT NULL",
        }
        for name, col_type in columns.items():
            if name not in existing:
                await db.execute(f"ALTER TABLE users ADD COLUMN {name} {col_type}")
                logger.info("users jadvaliga ustun qo'shildi: {}", name)
        await db.commit()

    async def _ensure_orders_columns(self, db: aiosqlite.Connection) -> None:
        """Add missing columns to orders table if table already existed."""
        cursor = await db.execute("PRAGMA table_info(orders)")
        existing = {row[1] for row in await cursor.fetchall()}
        columns = {
            "order_type": "TEXT NOT NULL DEFAULT 'stars'",
            "stars": "INTEGER NOT NULL DEFAULT 0",
            "quantity": "INTEGER NOT NULL DEFAULT 0",
            "discount_percent": "REAL NOT NULL DEFAULT 0.0",
            "price_uzs": "REAL NOT NULL DEFAULT 0.0",
        }
        for name, col_type in columns.items():
            if name not in existing:
                await db.execute(f"ALTER TABLE orders ADD COLUMN {name} {col_type}")
                logger.info("orders jadvaliga ustun qo'shildi: {}", name)
        if "stars" in existing:
            await db.execute("UPDATE orders SET quantity = stars WHERE (quantity = 0 OR quantity IS NULL) AND stars > 0")
        await db.commit()

    async def init_default_prices(self) -> None:
        """Insert default prices if they don't exist yet and lower legacy 5.0% commission."""
        async with self.connect() as db:
            for service, base_usd, comm, disc, min_q, max_q in DEFAULT_PRICES:
                await db.execute(
                    """
                    INSERT OR IGNORE INTO prices
                        (service, base_price_usd, commission_percent, discount_percent, min_qty, max_qty)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (service, base_usd, comm, disc, min_q, max_q),
                )
            # Faqat stars uchun 8.5168% (50 Stars = 10,499 so'm), qolgan barcha xizmatlarga 0% komissiya
            await db.execute("UPDATE prices SET commission_percent = 8.5168 WHERE service = 'stars'")
            await db.execute("UPDATE prices SET commission_percent = 0.0 WHERE service != 'stars'")
            await db.commit()
            Database._prices_cache.clear()

    # ─── Users ───────────────────────────────────────────────────────────────

    async def get_or_create_user(
        self, user_id: int, username: Optional[str], ref_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get existing user or create a new one with optional referrer."""
        async with self.connect() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row:
                ref = int(ref_by) if (ref_by and int(ref_by) != user_id) else None
                await db.execute(
                    """
                    INSERT INTO users (user_id, username, ref_by)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, username, ref),
                )
                await db.commit()
                cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = await cursor.fetchone()
                return dict(row) if row else {}

            if username and row["username"] != username:
                await db.execute(
                    "UPDATE users SET username = ? WHERE user_id = ?",
                    (username, user_id),
                )
                await db.commit()
            return dict(row)

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        rows = await self._fetch("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return rows[0] if rows else None

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        clean = username.lstrip("@").strip()
        rows = await self._fetch("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (clean,))
        return rows[0] if rows else None

    async def get_user_by_id_or_username(self, identifier: str) -> Optional[Dict[str, Any]]:
        clean = str(identifier).strip().lstrip("@")
        if clean.isdigit():
            user = await self.get_user(int(clean))
            if user:
                return user
        return await self.get_user_by_username(clean)

    async def set_user_balance_uzs(self, user_id: int, new_balance: float) -> None:
        async with self.connect() as db:
            await db.execute(
                "UPDATE users SET balance_uzs = ? WHERE user_id = ?",
                (max(0.0, float(new_balance)), user_id),
            )
            await db.commit()

    async def reset_all_balances_except(self, keep_user_id: int) -> int:
        async with self.connect() as db:
            cursor = await db.execute(
                "UPDATE users SET balance_uzs = 0.0, balance_ton = 0.0 WHERE user_id != ?",
                (keep_user_id,),
            )
            await db.commit()
            return cursor.rowcount

    async def update_user_lang(self, user_id: int, lang: str) -> None:
        async with self.connect() as db:
            await db.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
            await db.commit()

    async def update_user_balance(self, user_id: int, delta_ton: float) -> None:
        async with self.connect() as db:
            await db.execute(
                "UPDATE users SET balance_ton = COALESCE(balance_ton, 0.0) + ? WHERE user_id = ?",
                (delta_ton, user_id),
            )
            await db.commit()

    async def update_user_balance_uzs(self, user_id: int, delta_uzs: float) -> None:
        async with self.connect() as db:
            await db.execute(
                "UPDATE users SET balance_uzs = MAX(0.0, COALESCE(balance_uzs, 0.0) + ?) WHERE user_id = ?",
                (delta_uzs, user_id),
            )
            await db.commit()

    async def deduct_user_balance_uzs(self, user_id: int, amount_uzs: float) -> bool:
        """Atomically deduct balance_uzs only if balance >= amount_uzs. Returns True if deducted."""
        if amount_uzs <= 0:
            return False
        async with self.connect() as db:
            cursor = await db.execute(
                """
                UPDATE users
                SET balance_uzs = balance_uzs - ?
                WHERE user_id = ? AND balance_uzs >= ?
                """,
                (amount_uzs, user_id, amount_uzs),
            )
            await db.commit()
            return cursor.rowcount == 1

    async def deduct_user_balance_ton(self, user_id: int, amount_ton: float) -> bool:
        """Atomically deduct balance_ton only if balance >= amount_ton. Returns True if deducted."""
        if amount_ton <= 0:
            return False
        async with self.connect() as db:
            cursor = await db.execute(
                """
                UPDATE users
                SET balance_ton = balance_ton - ?
                WHERE user_id = ? AND balance_ton >= ?
                """,
                (amount_ton, user_id, amount_ton),
            )
            await db.commit()
            return cursor.rowcount == 1

    async def get_users_with_balance(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return users with positive balance (UZS or TON), highest balance first."""
        return await self._fetch(
            "SELECT * FROM users WHERE balance_uzs > 0 OR balance_ton > 0 ORDER BY balance_uzs DESC, id DESC LIMIT ?",
            (limit,),
        )

    async def get_all_users_ordered(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return all users ordered by balance DESC, then newest."""
        return await self._fetch(
            "SELECT * FROM users ORDER BY balance_uzs DESC, id DESC LIMIT ?",
            (limit,),
        )

    async def ban_user(self, user_id: int) -> None:
        async with self.connect() as db:
            await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    async def unban_user(self, user_id: int) -> None:
        async with self.connect() as db:
            await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
            await db.commit()

    async def get_all_users(self) -> List[Dict[str, Any]]:
        return await self._fetch("SELECT * FROM users WHERE is_banned = 0 ORDER BY id DESC")

    async def get_user_count(self) -> int:
        rows = await self._fetch("SELECT COUNT(*) as cnt FROM users")
        return rows[0]["cnt"] if rows else 0

    async def get_user_lang(self, user_id: int) -> str:
        rows = await self._fetch("SELECT lang FROM users WHERE user_id = ?", (user_id,))
        return rows[0]["lang"] if rows else "uz"

    # ─── Orders ──────────────────────────────────────────────────────────────

    async def create_order(
        self,
        *,
        user_id: int,
        username: Optional[str],
        order_type: str,
        recipient_username: str,
        quantity: int,
        price_usd: float,
        price_ton: float = 0.0,
        price_uzs: float = 0.0,
        discount_percent: float = 0.0,
        payment_type: str = "ton",
        payment_address: str,
        payment_comment: str,
        expires_at: datetime,
    ) -> int:
        """Create a new order and return its ID."""
        async with self.connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO orders (
                    user_id, username, order_type, recipient_username,
                    stars, quantity, price_usd, price_ton, price_uzs, discount_percent,
                    payment_type, payment_address, payment_comment, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id, username, order_type, recipient_username,
                    quantity, quantity, price_usd, price_ton, price_uzs, discount_percent,
                    payment_type, payment_address, payment_comment,
                    expires_at.isoformat(timespec="seconds"),
                ),
            )
            await db.commit()
            order_id = int(cursor.lastrowid)
        logger.info("Order #{} created: {} {} for @{}", order_id, quantity, order_type, recipient_username)
        return order_id

    async def find_pending_humo_order(self, amount_uzs: float) -> Optional[Dict[str, Any]]:
        """Find pending Humo order matching incoming amount (exact or within small tolerance)."""
        now = datetime.now().isoformat(timespec="seconds")
        # 1. Exact match
        rows = await self._fetch(
            """
            SELECT * FROM orders
            WHERE payment_type IN ('humo', 'click') AND status = 'pending'
            AND ABS(price_uzs - ?) < 1
            AND expires_at >= ?
            ORDER BY id ASC LIMIT 1
            """,
            (amount_uzs, now),
        )
        if rows:
            return rows[0]

        # 2. Tolerant match (within 50 UZS) if user sent flat amount without delta (e.g. 10499 vs 10500)
        rows = await self._fetch(
            """
            SELECT * FROM orders
            WHERE payment_type IN ('humo', 'click') AND status = 'pending'
            AND ABS(price_uzs - ?) <= 50
            AND expires_at >= ?
            ORDER BY id ASC LIMIT 1
            """,
            (amount_uzs, now),
        )
        return rows[0] if rows else None

    async def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        rows = await self._fetch("SELECT * FROM orders WHERE id = ?", (order_id,))
        return rows[0] if rows else None

    async def get_user_orders(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        return await self._fetch(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )

    async def get_all_orders(self, limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if status:
            return await self._fetch(
                "SELECT * FROM orders WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit),
            )
        return await self._fetch("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))

    async def get_pending_orders(self) -> List[Dict[str, Any]]:
        return await self._fetch(
            "SELECT * FROM orders WHERE status = 'pending' ORDER BY id"
        )

    async def get_paid_orders(self) -> List[Dict[str, Any]]:
        return await self._fetch(
            "SELECT * FROM orders WHERE status = 'paid' ORDER BY id"
        )

    async def get_pending_ton_orders(self) -> List[Dict[str, Any]]:
        """Return only pending TON orders for payment monitor."""
        return await self._fetch(
            "SELECT * FROM orders WHERE payment_type = 'ton' AND status = 'pending' ORDER BY id"
        )

    async def cancel_expired_card_orders(self) -> int:
        """Cancel all expired Humo/Click orders in a single fast query."""
        now = datetime.now().isoformat(timespec="seconds")
        async with self.connect() as db:
            cursor = await db.execute(
                """
                UPDATE orders
                SET status = 'cancelled'
                WHERE payment_type IN ('humo', 'click')
                  AND status = 'pending'
                  AND expires_at < ?
                """,
                (now,),
            )
            await db.commit()
            return cursor.rowcount

    async def set_order_status(self, order_id: int, status: str, **extra: Any) -> None:
        """Update order status and any additional fields."""
        now = datetime.now().isoformat(timespec="seconds")
        allowed = {
            "status", "fragment_tx_hash", "error_message",
            "paid_at", "completed_at", "price_ton",
        }
        fields: Dict[str, Any] = {"status": status}
        if status == "paid":
            fields.setdefault("paid_at", now)
        if status in ("completed", "failed"):
            fields.setdefault("completed_at", now)
        for k, v in extra.items():
            if k in allowed:
                fields[k] = v

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [order_id]
        async with self.connect() as db:
            await db.execute(f"UPDATE orders SET {set_clause} WHERE id = ?", values)
            await db.commit()
        logger.info("Order #{} -> {}", order_id, status)

    set_status = set_order_status

    async def acquire_pending_order(self, order_id: int) -> bool:
        """Atomically move pending order to processing. Returns True if acquired first (prevents race conditions)."""
        async with self.connect() as db:
            cursor = await db.execute(
                "UPDATE orders SET status = 'processing' WHERE id = ? AND status = 'pending'",
                (order_id,),
            )
            await db.commit()
            return cursor.rowcount == 1

    async def acquire_paid_order(self, order_id: int) -> bool:
        """Atomically move paid order to processing. Returns True if acquired."""
        async with self.connect() as db:
            cursor = await db.execute(
                "UPDATE orders SET status = 'processing' WHERE id = ? AND status = 'paid'",
                (order_id,),
            )
            await db.commit()
            return cursor.rowcount == 1

    async def get_stats(self) -> Dict[str, Any]:
        """Return aggregate stats for admin panel."""
        today = date.today().isoformat()
        async with self.connect() as db:
            db.row_factory = aiosqlite.Row

            total_users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
            total_orders = (await (await db.execute("SELECT COUNT(*) FROM orders")).fetchone())[0]
            completed = (await (await db.execute(
                "SELECT COUNT(*) FROM orders WHERE status='completed'")).fetchone())[0]
            failed = (await (await db.execute(
                "SELECT COUNT(*) FROM orders WHERE status='failed'")).fetchone())[0]
            pending = (await (await db.execute(
                "SELECT COUNT(*) FROM orders WHERE status IN ('pending','paid','processing')")).fetchone())[0]

            today_orders_row = await (await db.execute(
                "SELECT COUNT(*) FROM orders WHERE created_at >= ?", (today,))).fetchone()
            today_orders = today_orders_row[0] if today_orders_row else 0

            rev_row = await (await db.execute(
                "SELECT COALESCE(SUM(price_usd), 0) FROM orders WHERE status='completed'")).fetchone()
            total_revenue = float(rev_row[0]) if rev_row else 0.0

            today_rev_row = await (await db.execute(
                "SELECT COALESCE(SUM(price_usd), 0) FROM orders WHERE status='completed' AND created_at >= ?",
                (today,))).fetchone()
            today_revenue = float(today_rev_row[0]) if today_rev_row else 0.0

        return {
            "users": total_users,
            "orders": total_orders,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "today_orders": today_orders,
            "today_revenue": today_revenue,
            "total_revenue": total_revenue,
        }

    # ─── Prices ──────────────────────────────────────────────────────────────

    async def get_price(self, service: str) -> Optional[Dict[str, Any]]:
        now = datetime.now().timestamp()
        if Database._prices_cache and (now - Database._prices_cache_time) < 300:
            if service in Database._prices_cache:
                return Database._prices_cache[service]

        rows = await self._fetch("SELECT * FROM prices WHERE service = ?", (service,))
        if rows:
            Database._prices_cache[service] = rows[0]
            Database._prices_cache_time = now
            return rows[0]
        return None

    async def get_all_prices(self) -> List[Dict[str, Any]]:
        return await self._fetch("SELECT * FROM prices ORDER BY id")

    async def get_active_prices(self) -> List[Dict[str, Any]]:
        return await self._fetch("SELECT * FROM prices WHERE is_active = 1 ORDER BY id")

    async def set_price(
        self,
        service: str,
        *,
        base_price_usd: Optional[float] = None,
        commission_percent: Optional[float] = None,
        discount_percent: Optional[float] = None,
        min_qty: Optional[int] = None,
        max_qty: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> None:
        updates = {}
        if base_price_usd is not None:
            updates["base_price_usd"] = base_price_usd
        if commission_percent is not None:
            updates["commission_percent"] = commission_percent
        if discount_percent is not None:
            updates["discount_percent"] = discount_percent
        if min_qty is not None:
            updates["min_qty"] = min_qty
        if max_qty is not None:
            updates["max_qty"] = max_qty
        if is_active is not None:
            updates["is_active"] = 1 if is_active else 0
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [service]
        async with self.connect() as db:
            await db.execute(f"UPDATE prices SET {set_clause} WHERE service = ?", values)
            await db.commit()
        Database._prices_cache.clear()
        logger.info("Price updated: {} -> {}", service, updates)

    # ─── Settings ────────────────────────────────────────────────────────────

    async def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        rows = await self._fetch("SELECT value FROM settings WHERE key = ?", (key,))
        return rows[0]["value"] if rows else default

    async def set_setting(self, key: str, value: str) -> None:
        async with self.connect() as db:
            await db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
            await db.commit()

    async def get_order_timeout_minutes(self, default: int = 5) -> int:
        val = await self.get_setting("order_timeout_minutes", str(default))
        try:
            return max(1, int(val or default))
        except (ValueError, TypeError):
            return default

    async def set_order_timeout_minutes(self, minutes: int) -> None:
        await self.set_setting("order_timeout_minutes", str(max(1, minutes)))

    # ─── Broadcasts ──────────────────────────────────────────────────────────

    async def log_broadcast(self, admin_id: int, text: str, sent: int, failed: int) -> None:
        async with self.connect() as db:
            await db.execute(
                "INSERT INTO broadcasts (admin_id, message_text, sent_count, fail_count) VALUES (?, ?, ?, ?)",
                (admin_id, text, sent, failed),
            )
            await db.commit()

    # ─── Referral ────────────────────────────────────────────────────────────

    async def reward_referral(self, referrer_id: int, new_user_id: int, stars: int = 2) -> bool:
        """Reward referrer with stars when new user joins/subscribes."""
        async with self.connect() as db:
            cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,))
            if not await cursor.fetchone():
                return False

            await db.execute(
                """
                UPDATE users
                SET referral_stars = referral_stars + ?,
                    referral_count = referral_count + 1
                WHERE user_id = ?
                """,
                (stars, referrer_id),
            )
            await db.commit()
            logger.info("Referral reward: user {} +{} stars from {}", referrer_id, stars, new_user_id)
            return True

    async def deduct_referral_stars(self, user_id: int, stars: int) -> bool:
        """Deduct referral stars when claiming a gift."""
        async with self.connect() as db:
            cursor = await db.execute(
                "SELECT referral_stars FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            if not row or (row[0] or 0) < stars:
                return False
            await db.execute(
                "UPDATE users SET referral_stars = referral_stars - ? WHERE user_id = ?",
                (stars, user_id),
            )
            await db.commit()
            return True

    async def clear_user_referrer(self, user_id: int) -> None:
        """Clear ref_by once referral reward has been processed."""
        async with self.connect() as db:
            await db.execute("UPDATE users SET ref_by = NULL WHERE user_id = ?", (user_id,))
            await db.commit()

    # ─── Channels ────────────────────────────────────────────────────────────

    async def add_channel(self, channel_id: str, title: str, url: str) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO channels (channel_id, title, url)
                VALUES (?, ?, ?)
                """,
                (str(channel_id).strip(), title.strip(), url.strip()),
            )
            await db.commit()
            logger.info("Channel added: {} ({})", title, channel_id)

    async def delete_channel(self, channel_id: str) -> None:
        async with self.connect() as db:
            await db.execute("DELETE FROM channels WHERE channel_id = ?", (str(channel_id).strip(),))
            await db.commit()
            logger.info("Channel deleted: {}", channel_id)

    async def get_channels(self) -> List[Dict[str, Any]]:
        return await self._fetch("SELECT * FROM channels ORDER BY id")

    async def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        rows = await self._fetch("SELECT * FROM channels WHERE channel_id = ?", (str(channel_id).strip(),))
        return rows[0] if rows else None

    # ─── Gift Requests ───────────────────────────────────────────────────────

    async def create_gift_request(
        self,
        user_id: int,
        username: Optional[str],
        recipient_username: str,
        stars_spent: int = 16,
        gift_name: str = "🧸 Ayiqcha",
    ) -> int:
        async with self.connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO gift_requests (user_id, username, recipient_username, stars_spent, gift_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, username, recipient_username.lstrip("@"), stars_spent, gift_name),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_gift_requests(self, limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if status:
            return await self._fetch(
                "SELECT * FROM gift_requests WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit),
            )
        return await self._fetch(
            "SELECT * FROM gift_requests ORDER BY id DESC LIMIT ?", (limit,)
        )

    async def get_gift_request(self, request_id: int) -> Optional[Dict[str, Any]]:
        rows = await self._fetch("SELECT * FROM gift_requests WHERE id = ?", (request_id,))
        return rows[0] if rows else None

    async def set_gift_request_status(
        self, request_id: int, status: str, error_message: Optional[str] = None
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        async with self.connect() as db:
            await db.execute(
                """
                UPDATE gift_requests
                SET status = ?, completed_at = ?, error_message = ?
                WHERE id = ?
                """,
                (status, now if status == "completed" else None, error_message, request_id),
            )
            await db.commit()

    # ─── Internal ────────────────────────────────────────────────────────────

    async def _fetch(self, query: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
        async with self.connect() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, tuple(params))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


    # ─── Transactions & Ledger ───────────────────────────────────────────────

    async def record_transaction(
        self,
        user_id: int,
        tx_type: str,
        amount_uzs: float = 0.0,
        old_balance_uzs: float = 0.0,
        new_balance_uzs: float = 0.0,
        admin_id: Optional[int] = None,
        order_id: Optional[int] = None,
        comment: Optional[str] = None,
        amount_ton: float = 0.0,
    ) -> int:
        """Record an immutable transaction entry into balance_transactions."""
        async with self.connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO balance_transactions (
                    user_id, admin_id, tx_type, amount_uzs, amount_ton,
                    old_balance_uzs, new_balance_uzs, order_id, comment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id, admin_id, tx_type, amount_uzs, amount_ton,
                    old_balance_uzs, new_balance_uzs, order_id, comment
                ),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_user_transactions(self, user_id: int, limit: int = 15) -> List[Dict[str, Any]]:
        """Return transaction history for a single user."""
        return await self._fetch(
            """
            SELECT * FROM balance_transactions
            WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        )

    async def get_withdrawals_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Return list of deductions/withdrawals made by admin or approved for users."""
        return await self._fetch(
            """
            SELECT bt.*, u.username
            FROM balance_transactions bt
            LEFT JOIN users u ON u.user_id = bt.user_id
            WHERE bt.tx_type IN ('admin_withdraw', 'admin_zero', 'user_withdraw_approved')
            ORDER BY bt.id DESC LIMIT ?
            """,
            (limit,),
        )

    async def get_all_transactions(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Return latest transactions across all types."""
        return await self._fetch(
            """
            SELECT bt.*, u.username
            FROM balance_transactions bt
            LEFT JOIN users u ON u.user_id = bt.user_id
            ORDER BY bt.id DESC LIMIT ?
            """,
            (limit,),
        )

    async def get_financial_stats(self) -> Dict[str, Any]:
        """Aggregate total deposits, withdrawals, purchases and current user balances."""
        today = date.today().isoformat()
        async with self.connect() as db:
            # 1. Total topups (card & ton & manual admin topups)
            c1 = await db.execute(
                "SELECT COALESCE(SUM(amount_uzs), 0) FROM balance_transactions WHERE tx_type IN ('card_topup', 'ton_topup', 'admin_deposit')"
            )
            total_deposited = float((await c1.fetchone())[0])

            # 2. Total admin withdrawals & user withdrawals
            c2 = await db.execute(
                "SELECT COALESCE(SUM(amount_uzs), 0) FROM balance_transactions WHERE tx_type IN ('admin_withdraw', 'admin_zero')"
            )
            total_admin_withdrawn = float((await c2.fetchone())[0])

            c3 = await db.execute(
                "SELECT COALESCE(SUM(amount_uzs), 0) FROM balance_transactions WHERE tx_type = 'user_withdraw_approved'"
            )
            total_user_withdrawn = float((await c3.fetchone())[0])

            # 3. Purchases from balance
            c4 = await db.execute(
                "SELECT COALESCE(SUM(amount_uzs), 0) FROM balance_transactions WHERE tx_type = 'purchase'"
            )
            total_purchases = float((await c4.fetchone())[0])

            # 4. Today's stats
            c5 = await db.execute(
                "SELECT COALESCE(SUM(amount_uzs), 0) FROM balance_transactions WHERE tx_type IN ('card_topup', 'ton_topup', 'admin_deposit') AND created_at >= ?",
                (today,),
            )
            today_deposited = float((await c5.fetchone())[0])

            c6 = await db.execute(
                "SELECT COALESCE(SUM(amount_uzs), 0) FROM balance_transactions WHERE tx_type IN ('admin_withdraw', 'admin_zero', 'user_withdraw_approved') AND created_at >= ?",
                (today,),
            )
            today_withdrawn = float((await c6.fetchone())[0])

            # 5. Current balance sum in users table
            c7 = await db.execute("SELECT COALESCE(SUM(balance_uzs), 0) FROM users")
            current_user_balances = float((await c7.fetchone())[0])

            # 6. Pending withdraw requests count
            c8 = await db.execute("SELECT COUNT(*) FROM withdraw_requests WHERE status = 'pending'")
            pending_withdraw_count = int((await c8.fetchone())[0])

        return {
            "total_deposited": total_deposited,
            "total_admin_withdrawn": total_admin_withdrawn,
            "total_user_withdrawn": total_user_withdrawn,
            "total_withdrawn_overall": total_admin_withdrawn + total_user_withdrawn,
            "total_purchases": total_purchases,
            "today_deposited": today_deposited,
            "today_withdrawn": today_withdrawn,
            "current_user_balances": current_user_balances,
            "pending_withdraw_count": pending_withdraw_count,
        }

    async def get_user_financial_profile(self, user_id: int) -> Dict[str, Any]:
        """Aggregate deposit, withdrawal, and purchase totals for a specific user."""
        async with self.connect() as db:
            c1 = await db.execute(
                "SELECT COALESCE(SUM(amount_uzs), 0) FROM balance_transactions WHERE user_id = ? AND tx_type IN ('card_topup', 'ton_topup', 'admin_deposit')",
                (user_id,),
            )
            deposited = float((await c1.fetchone())[0])

            c2 = await db.execute(
                "SELECT COALESCE(SUM(amount_uzs), 0) FROM balance_transactions WHERE user_id = ? AND tx_type IN ('admin_withdraw', 'admin_zero', 'user_withdraw_approved')",
                (user_id,),
            )
            withdrawn = float((await c2.fetchone())[0])

            c3 = await db.execute(
                "SELECT COALESCE(SUM(amount_uzs), 0) FROM balance_transactions WHERE user_id = ? AND tx_type = 'purchase'",
                (user_id,),
            )
            purchased = float((await c3.fetchone())[0])

        return {
            "total_deposited": deposited,
            "total_withdrawn": withdrawn,
            "total_purchased": purchased,
        }

    # ─── Withdraw Requests (User to Card) ────────────────────────────────────

    async def create_withdraw_request(
        self,
        user_id: int,
        username: Optional[str],
        card_number: str,
        card_holder: Optional[str],
        amount_uzs: float,
    ) -> int:
        """Create a new user withdrawal request."""
        async with self.connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO withdraw_requests (user_id, username, card_number, card_holder, amount_uzs, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
                """,
                (user_id, username, card_number, card_holder, amount_uzs),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_withdraw_request(self, req_id: int) -> Optional[Dict[str, Any]]:
        rows = await self._fetch("SELECT * FROM withdraw_requests WHERE id = ?", (req_id,))
        return rows[0] if rows else None

    async def get_pending_withdraw_requests(self, limit: int = 20) -> List[Dict[str, Any]]:
        return await self._fetch(
            "SELECT * FROM withdraw_requests WHERE status = 'pending' ORDER BY id ASC LIMIT ?",
            (limit,),
        )

    async def get_pending_withdraw_count(self) -> int:
        rows = await self._fetch("SELECT COUNT(*) as cnt FROM withdraw_requests WHERE status = 'pending'")
        return int(rows[0]["cnt"]) if rows else 0

    async def set_withdraw_request_status(
        self, req_id: int, status: str, admin_id: Optional[int] = None, admin_note: Optional[str] = None
    ) -> bool:
        now = datetime.now().isoformat(timespec="seconds")
        async with self.connect() as db:
            cursor = await db.execute(
                """
                UPDATE withdraw_requests
                SET status = ?, admin_id = ?, admin_note = ?, processed_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (status, admin_id, admin_note, now, req_id),
            )
            await db.commit()
            return cursor.rowcount == 1


    # ─── VIP Membership ──────────────────────────────────────────────────────

    async def is_user_vip(self, user_id: int) -> bool:
        """Check if user has an active VIP membership."""
        user = await self.get_user(user_id)
        if not user or not user.get("vip_until"):
            return False
        try:
            exp = datetime.fromisoformat(str(user["vip_until"]))
            return exp > datetime.now()
        except Exception:
            return False

    async def get_user_vip_info(self, user_id: int) -> Dict[str, Any]:
        """Return detailed VIP information for user."""
        user = await self.get_user(user_id)
        if not user or not user.get("vip_until"):
            return {"is_vip": False, "vip_until": None, "days_left": 0, "hours_left": 0}

        try:
            exp = datetime.fromisoformat(str(user["vip_until"]))
            now = datetime.now()
            if exp <= now:
                return {"is_vip": False, "vip_until": str(user["vip_until"]), "days_left": 0, "hours_left": 0}

            diff = exp - now
            days_left = diff.days
            hours_left = int(diff.seconds // 3600)
            return {
                "is_vip": True,
                "vip_until": exp.strftime("%d.%m.%Y %H:%M"),
                "days_left": days_left,
                "hours_left": hours_left,
            }
        except Exception:
            return {"is_vip": False, "vip_until": None, "days_left": 0, "hours_left": 0}

    async def set_user_vip(self, user_id: int, days: int) -> str:
        """Grant or extend VIP membership for user by `days` days. Returns new expiry iso string."""
        user = await self.get_user(user_id)
        now = datetime.now()
        base_time = now

        if user and user.get("vip_until"):
            try:
                curr_exp = datetime.fromisoformat(str(user["vip_until"]))
                if curr_exp > now:
                    base_time = curr_exp
            except Exception:
                pass

        new_exp = base_time + timedelta(days=days)
        new_exp_iso = new_exp.isoformat(timespec="seconds")

        async with self.connect() as db:
            await db.execute(
                "UPDATE users SET vip_until = ? WHERE user_id = ?",
                (new_exp_iso, user_id),
            )
            await db.commit()

        logger.info("User {} ga {} kunlik VIP berildi. Tugash vaqti: {}", user_id, days, new_exp_iso)
        return new_exp_iso

    async def cancel_user_vip(self, user_id: int) -> bool:
        """Cancel VIP membership for user."""
        async with self.connect() as db:
            cursor = await db.execute(
                "UPDATE users SET vip_until = NULL WHERE user_id = ?",
                (user_id,),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_vip_plans(self) -> Dict[str, Dict[str, Any]]:
        """Return configured VIP tariff plans with pricing."""
        p1 = await self.get_setting("vip_price_1d")
        p7 = await self.get_setting("vip_price_7d")
        p15 = await self.get_setting("vip_price_15d")

        p1_val = float(p1) if p1 else 9900.0
        p7_val = float(p7) if p7 else 25000.0
        p15_val = float(p15) if p15 else 45000.0

        return {
            "vip_1d": {
                "key": "vip_1d",
                "name": "⚡ 1 Kunlik VIP Pass",
                "days": 1,
                "price_uzs": p1_val,
                "price_usd": round(p1_val / 12900, 2),
                "badge": "Tezkor xarid",
                "benefit": "500-1,000 Stars xaridida o'zini to'liq oqlaydi!",
            },
            "vip_7d": {
                "key": "vip_7d",
                "name": "📅 7 Kunlik VIP Pass",
                "days": 7,
                "price_uzs": p7_val,
                "price_usd": round(p7_val / 12900, 2),
                "badge": "65% Chegirma",
                "benefit": "Resellerlar va faol xaridorlar tanlovi!",
            },
            "vip_15d": {
                "key": "vip_15d",
                "name": "⭐ 15 Kunlik Premium Pass",
                "days": 15,
                "price_uzs": p15_val,
                "price_usd": round(p15_val / 12900, 2),
                "badge": "70% Super Chegirma",
                "benefit": "Eng arzon tannarx — xohlagancha stars oling!",
            },
        }

    async def get_active_vip_users(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return users with active VIP status."""
        now = datetime.now().isoformat(timespec="seconds")
        return await self._fetch(
            """
            SELECT user_id, username, vip_until, balance_uzs
            FROM users
            WHERE vip_until IS NOT NULL AND vip_until > ?
            ORDER BY vip_until ASC LIMIT ?
            """,
            (now, limit),
        )

    async def get_vip_stats(self) -> Dict[str, Any]:
        """Return VIP membership statistics."""
        now = datetime.now().isoformat(timespec="seconds")
        async with self.connect() as db:
            c1 = await db.execute("SELECT COUNT(*) FROM users WHERE vip_until IS NOT NULL AND vip_until > ?", (now,))
            active_count = (await c1.fetchone())[0]

            c2 = await db.execute(
                "SELECT COALESCE(SUM(price_uzs), 0), COUNT(*) FROM orders WHERE order_type LIKE 'vip_%' AND status = 'completed'"
            )
            row2 = await c2.fetchone()
            total_revenue = float(row2[0]) if row2 else 0.0
            total_sold = int(row2[1]) if row2 else 0

        return {
            "active_vip_count": active_count,
            "total_vip_revenue": total_revenue,
            "total_vip_sold": total_sold,
        }
