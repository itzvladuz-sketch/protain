"""Full-featured SQLite database for Stars Shop bot.

Tables:
- users: bot users with lang, balance, ban status
- orders: all purchase orders (stars/premium/gift)
- prices: configurable prices per service
- settings: key-value admin settings
- broadcasts: broadcast history
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, Iterable, List, Optional

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
}


class Database:
    """Async SQLite wrapper for Stars Shop bot."""

    _prices_cache: Dict[str, Dict[str, Any]] = {}
    _prices_cache_time: float = 0.0

    def __init__(self, db_path: str):
        self.db_path = db_path

    # ─── Init ────────────────────────────────────────────────────────────────

    async def init_db(self) -> None:
        """Create all tables and seed default prices."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;
                PRAGMA cache_size=10000;
                PRAGMA temp_store=MEMORY;

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

                CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
                CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
                CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
                CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
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
        async with aiosqlite.connect(self.db_path) as db:
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
        async with aiosqlite.connect(self.db_path) as db:
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

    async def update_user_lang(self, user_id: int, lang: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
            await db.commit()

    async def update_user_balance(self, user_id: int, delta_ton: float) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET balance_ton = balance_ton + ? WHERE user_id = ?",
                (delta_ton, user_id),
            )
            await db.commit()

    async def update_user_balance_uzs(self, user_id: int, delta_uzs: float) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET balance_uzs = balance_uzs + ? WHERE user_id = ?",
                (delta_uzs, user_id),
            )
            await db.commit()

    async def ban_user(self, user_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    async def unban_user(self, user_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
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
        async with aiosqlite.connect(self.db_path) as db:
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
            WHERE payment_type = 'humo' AND status = 'pending'
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
            WHERE payment_type = 'humo' AND status = 'pending'
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
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE orders SET {set_clause} WHERE id = ?", values)
            await db.commit()
        logger.info("Order #{} -> {}", order_id, status)

    set_status = set_order_status

    async def acquire_paid_order(self, order_id: int) -> bool:
        """Atomically move paid order to processing. Returns True if acquired."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE orders SET status = 'processing' WHERE id = ? AND status = 'paid'",
                (order_id,),
            )
            await db.commit()
            return cursor.rowcount == 1

    async def get_stats(self) -> Dict[str, Any]:
        """Return aggregate stats for admin panel."""
        today = date.today().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
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
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE prices SET {set_clause} WHERE service = ?", values)
            await db.commit()
        Database._prices_cache.clear()
        logger.info("Price updated: {} -> {}", service, updates)

    # ─── Settings ────────────────────────────────────────────────────────────

    async def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        rows = await self._fetch("SELECT value FROM settings WHERE key = ?", (key,))
        return rows[0]["value"] if rows else default

    async def set_setting(self, key: str, value: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
            await db.commit()

    # ─── Broadcasts ──────────────────────────────────────────────────────────

    async def log_broadcast(self, admin_id: int, text: str, sent: int, failed: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO broadcasts (admin_id, message_text, sent_count, fail_count) VALUES (?, ?, ?, ?)",
                (admin_id, text, sent, failed),
            )
            await db.commit()

    # ─── Referral ────────────────────────────────────────────────────────────

    async def reward_referral(self, referrer_id: int, new_user_id: int, stars: int = 2) -> bool:
        """Reward referrer with stars when new user joins/subscribes."""
        async with aiosqlite.connect(self.db_path) as db:
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
        async with aiosqlite.connect(self.db_path) as db:
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
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET ref_by = NULL WHERE user_id = ?", (user_id,))
            await db.commit()

    # ─── Channels ────────────────────────────────────────────────────────────

    async def add_channel(self, channel_id: str, title: str, url: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
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
        async with aiosqlite.connect(self.db_path) as db:
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
        async with aiosqlite.connect(self.db_path) as db:
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
        async with aiosqlite.connect(self.db_path) as db:
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
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, tuple(params))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
