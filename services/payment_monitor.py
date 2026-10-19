"""Polling payment monitor for TON orders with multilingual notifications."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from aiogram import Bot
from loguru import logger

from locales import t
from services.config import BotConfig
from services.db import Database
from services.fragment_api import FragmentAPIService
from services.ton import TONService


def _parse_dt(value: Any) -> datetime:
    """Parse SQLite/Python datetime strings."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


class PaymentMonitor:
    """Checks payments and fulfills paid orders through Fragment API."""

    def __init__(self, config: BotConfig):
        self.config = config
        self.db = Database(config.database_path)
        self.ton = TONService(config.ton_wallet_address, config.toncenter_api_key)
        self.fragment = FragmentAPIService(
            api_key=config.fragment_api_key,
            wallet_mnemonic=config.fragment_wallet_mnemonic,
            api_url=config.fragment_api_url,
            api_mode=config.fragment_api_mode,
            payment_method=config.fragment_payment_method,
            cookies_base64=config.fragment_cookies_base64,
            wallet_address=config.fragment_wallet_address,
            account_index=config.fragment_account_index,
        )
        self.bot: Optional[Bot] = None
        self._running = False
        self._stop_event: Optional[asyncio.Event] = None

    def set_bot(self, bot: Bot) -> None:
        """Attach aiogram Bot so the monitor can notify users."""
        self.bot = bot

    async def start(self) -> None:
        """Run payment checks until `stop()` is called."""
        if self._running:
            return
        self._running = True
        self._stop_event = asyncio.Event()
        logger.info("Payment monitor started")
        try:
            while self._running:
                await self.tick()
                await self._sleep(25)
        finally:
            self._running = False
            self._stop_event = None
            logger.info("Payment monitor stopped")

    async def stop(self) -> None:
        """Stop the monitor loop."""
        self._running = False
        if self._stop_event:
            self._stop_event.set()

    async def tick(self) -> None:
        """One full monitor pass: check pending payments, then fulfill paid orders."""
        try:
            for order in await self.db.get_pending_ton_orders():
                try:
                    await self.check_payment(order)
                except Exception as exc:
                    logger.warning("Error checking TON order #{}: {}", order.get("id"), exc)

            for order in await self.db.get_paid_orders():
                try:
                    await self.fulfill_paid_order(order)
                except Exception as exc:
                    logger.warning("Error fulfilling paid order #{}: {}", order.get("id"), exc)
        except Exception as err:
            logger.exception("Unexpected error in PaymentMonitor tick: {}", err)

    async def check_payment(self, order: Dict[str, Any]) -> None:
        """Check a pending TON order."""
        order_id = int(order["id"])
        expires_at = _parse_dt(order["expires_at"])
        user_id = int(order["user_id"])
        lang = await self.db.get_user_lang(user_id)

        if datetime.now() > expires_at:
            await self.db.set_order_status(order_id, "expired")
            return

        payment_type = order.get("payment_type") or "ton"
        if payment_type == "ton":
            await self._check_ton(order)

    async def _check_ton(self, order: Dict[str, Any]) -> None:
        order_id = int(order["id"])
        price_ton = float(order.get("price_ton") or order.get("total_ton") or 0.0)
        user_id = int(order["user_id"])
        lang = await self.db.get_user_lang(user_id)

        created_ts = int(_parse_dt(order["created_at"]).timestamp()) if order.get("created_at") else 0
        tx = await self.ton.check_transaction(
            comment=order["payment_comment"],
            min_amount=price_ton,
            since_timestamp=created_ts,
        )
        if not tx:
            return

        await self.db.set_order_status(order_id, "paid", fragment_tx_hash=tx.get("hash"))
        await self._notify(user_id, t(lang, "payment_found"))

    async def fulfill_paid_order(self, order: Dict[str, Any]) -> None:
        """Deliver Stars, Premium or Gift through Fragment API."""
        order_id = int(order["id"])
        if not await self.db.acquire_paid_order(order_id):
            return

        recipient = str(order.get("recipient_username") or order.get("username") or "")
        order_type = str(order.get("order_type") or "stars")
        quantity = int(order.get("quantity") or order.get("stars") or 1)
        user_id = int(order["user_id"])
        lang = await self.db.get_user_lang(user_id)

        try:
            if order_type == "topup":
                price_ton = float(order.get("price_ton") or 0.0)
                await self.db.update_user_balance(user_id, price_ton)
                user_row = await self.db.get_user(user_id)
                new_bal = float(user_row.get("balance_ton") or 0.0) if user_row else price_ton
                await self.db.set_order_status(order_id, "completed")
                await self._notify(
                    user_id,
                    t(lang, "balance_topup_completed", amount=f"{price_ton:.4f}", new_balance=f"{new_bal:.4f}"),
                )
                return

            if order_type == "premium":
                tx_hash = await self.fragment.buy_premium(recipient, quantity)
                amount_desc = f"{quantity} oy Telegram Premium"
            elif order_type == "gift":
                tx_hash = await self.fragment.buy_stars(recipient, quantity)
                amount_desc = f"{quantity} Stars Gift"
            else:
                # stars
                tx_hash = await self.fragment.buy_stars(recipient, quantity)
                amount_desc = f"{quantity} Stars"

            await self.db.set_order_status(order_id, "completed", fragment_tx_hash=tx_hash)
            await self._notify(
                user_id,
                t(lang, "order_completed", amount=amount_desc, recipient=recipient),
            )
        except Exception as exc:
            logger.exception("Fragment fulfillment failed for order #{}", order_id)
            await self.db.set_order_status(order_id, "failed", error_message=str(exc))
            await self._notify(
                user_id,
                t(lang, "order_failed", error=str(exc), support=self.config.support_username),
            )

    async def _notify(self, user_id: int, text: str) -> None:
        if not self.bot:
            return
        try:
            await self.bot.send_message(user_id, text, parse_mode="HTML")
        except Exception as exc:
            logger.warning("Failed to notify user {}: {}", user_id, exc)

    async def _sleep(self, seconds: int) -> None:
        if not self._stop_event:
            await asyncio.sleep(seconds)
            return
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass
