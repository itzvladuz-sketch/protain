"""Telethon-based payment listener for Humo card bank/bot notifications."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Optional

from aiogram import Bot
from loguru import logger

from locales import t
from services.config import BotConfig
from services.db import Database
from services.fragment_api import FragmentAPIService


def extract_amount_uzs(text: str) -> Optional[float]:
    """Parse payment sum from notification message.
    Matches formats like:
    +50 000 UZS, +50000 so'm, 50 000.00 UZS, To'lov: 50000, Tushum: 50000, +50000, etc.
    """
    cleaned = text.replace("\xa0", " ").strip()
    patterns = [
        r"\+\s*([0-9]{1,3}(?:[ ,][0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)",
        r"(?:tushum|kirim|popolnenie|prihod|to'?lov|postuplenie|perevod|summa|sum|qiymat)[:\s]+\+?\s*([0-9]{1,3}(?:[ ,][0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)",
        r"([0-9]{1,3}(?:[ ,][0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)\s*(?:uzs|so'?m|сум)",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            num_str = match.group(1).replace(" ", "").replace(",", "")
            try:
                amt = float(num_str)
                if amt >= 1000:
                    return amt
            except ValueError:
                continue
    return None


class HumoPaymentMonitor:
    """Listens to bank/notification bot messages via Telethon userbot."""

    def __init__(self, config: BotConfig, bot: Bot):
        self.config = config
        self.bot = bot
        self.db = Database(config.database_path)
        self.client = None
        self._running = False
        self._stop_event: Optional[asyncio.Event] = None

    async def start(self) -> None:
        """Start the auto-expiry check loop and userbot listener if configured."""
        self._running = True
        self._stop_event = asyncio.Event()

        # Start userbot if API_ID and API_HASH are provided
        userbot_task = None
        if getattr(self.config, "tg_api_id", None) and getattr(self.config, "tg_api_hash", None):
            userbot_task = asyncio.create_task(self._run_userbot(), name="humo-telethon-userbot")

        try:
            while self._running:
                await self._check_expired_humo_orders()
                await self._sleep(20)
        finally:
            self._running = False
            if userbot_task:
                userbot_task.cancel()
            if self.client:
                try:
                    await self.client.disconnect()
                except Exception:
                    pass

    async def stop(self) -> None:
        self._running = False
        if self._stop_event:
            self._stop_event.set()

    async def _run_userbot(self) -> None:
        """Connect Telethon client and listen for incoming messages."""
        try:
            from telethon import TelegramClient, events
            from telethon.sessions import StringSession
            session = StringSession(self.config.telethon_session_string) if getattr(self.config, "telethon_session_string", "") else "humo_listener_session"
            self.client = TelegramClient(
                session,
                int(self.config.tg_api_id),
                str(self.config.tg_api_hash),
            )

            await self.client.connect()
            if not await self.client.is_user_authorized():
                logger.warning("Telethon userbot tizimga kirmagan (avtorizatsiya talab qilinadi)")
                await self.client.disconnect()
                return

            logger.info("Telethon Humo to'lov tinglovchisi ishga tushdi")

            @self.client.on(events.NewMessage)
            async def handler(event):
                try:
                    sender = await event.get_sender()
                    sender_username = (getattr(sender, "username", "") or "").lower()
                    sender_title = (getattr(sender, "title", "") or getattr(sender, "first_name", "") or "").lower()
                    target_bot = getattr(self.config, "notification_bot_username", "").lstrip("@").lower()
                    is_bot = bool(getattr(sender, "bot", False))

                    # Filter by target bot, bank keywords, or any bot message
                    is_match = False
                    if target_bot and (target_bot in sender_username or target_bot in sender_title):
                        is_match = True
                    elif any(kw in sender_username or kw in sender_title for kw in ("humo", "bank", "karta", "card", "click", "payme", "uzum", "pay")):
                        is_match = True
                    elif is_bot:
                        is_match = True
                    elif not target_bot:
                        is_match = True

                    if not is_match:
                        return

                    msg_text = event.raw_text or ""
                    amt = extract_amount_uzs(msg_text)
                    if amt:
                        logger.info("Humo to'lov xabari aniqlandi: {} so'm (yuboruvchi: @{} / {})", amt, sender_username, sender_title)
                        await self.process_incoming_humo_payment(amt, msg_text)
                except Exception as err:
                    logger.warning("Xabarni tahlil qilishda xatolik: {}", err)

            await self.client.run_until_disconnected()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception("Telethon Humo monitorida xatolik: {}", exc)

    async def process_incoming_humo_payment(self, amount_uzs: float, raw_text: str = "") -> bool:
        """Match incoming payment with a pending order and fulfill."""
        order = await self.db.find_pending_humo_order(amount_uzs)
        if not order:
            logger.info("Mos keluvchi Humo buyurtma topilmadi (summa: {} so'm)", amount_uzs)
            return False

        order_id = int(order["id"])
        user_id = int(order["user_id"])
        order_type = str(order.get("order_type") or "stars")
        quantity = int(order.get("quantity") or 1)
        recipient = str(order.get("recipient_username") or "")
        lang = await self.db.get_user_lang(user_id)

        logger.info("Humo to'lov tasdiqlandi: Order #{} ({} so'm)", order_id, amount_uzs)

        if order_type == "topup":
            price_uzs = float(order.get("price_uzs") or amount_uzs)
            await self.db.update_user_balance_uzs(user_id, price_uzs)
            await self.db.set_order_status(order_id, "completed")
            user_row = await self.db.get_user(user_id)
            new_bal_uzs = float(user_row.get("balance_uzs") or 0.0) if user_row else price_uzs
            try:
                await self.bot.send_message(
                    user_id,
                    t(lang, "balance_topup_uzs_completed", amount=int(price_uzs), new_balance=int(new_bal_uzs)),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning("Foydalanuvchiga bildirishnoma yuborilmadi: {}", e)
            return True

        # Regular service order (stars, premium, gift)
        await self.db.set_order_status(order_id, "paid")
        fragment = FragmentAPIService(
            api_key=self.config.fragment_api_key,
            wallet_mnemonic=self.config.fragment_wallet_mnemonic,
            api_url=self.config.fragment_api_url,
            api_mode=self.config.fragment_api_mode,
            payment_method=self.config.fragment_payment_method,
            cookies_base64=self.config.fragment_cookies_base64,
            wallet_address=self.config.fragment_wallet_address,
            account_index=self.config.fragment_account_index,
        )

        try:
            if order_type == "premium":
                tx = await fragment.buy_premium(recipient, quantity)
                desc = f"{quantity} oy Premium"
            else:
                tx = await fragment.buy_stars(recipient, quantity)
                desc = f"{quantity} Stars"

            await self.db.set_order_status(order_id, "completed", fragment_tx_hash=tx)
            await self.bot.send_message(
                user_id,
                t(lang, "order_completed", amount=desc, recipient=recipient),
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.exception("Fragment fulfillment failed for order #{}: {}", order_id, exc)
            await self.db.set_order_status(order_id, "failed", error_message=str(exc))
            await self.bot.send_message(
                user_id,
                t(lang, "order_failed", support=self.config.support_username or "admin"),
                parse_mode="HTML",
            )

        return True

    async def _check_expired_humo_orders(self) -> None:
        """Cancel Humo orders that passed the 5-minute timeout silently."""
        now = datetime.now().isoformat(timespec="seconds")
        pending = await self.db._fetch(
            "SELECT * FROM orders WHERE payment_type = 'humo' AND status = 'pending' AND expires_at < ?",
            (now,),
        )
        for order in pending:
            order_id = int(order["id"])
            await self.db.set_order_status(order_id, "cancelled")
            logger.info("Humo buyurtma #{} muddati o'tib bekor qilindi (5 daqiqa)", order_id)

    async def _sleep(self, seconds: int) -> None:
        if not self._stop_event:
            await asyncio.sleep(seconds)
            return
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass
