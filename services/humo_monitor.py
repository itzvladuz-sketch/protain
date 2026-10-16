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
    """Parse incoming bank payment sum from notification message.
    Strictly matches deposit messages (e.g. +50 000 UZS, Karta to'ldirildi: +50 000 UZS).
    Rejects invoices, bot commands, withdrawals, and debit messages.
    """
    cleaned = text.replace("\xa0", " ").strip()
    # Normalize apostrophes: ’, `, '
    cleaned = cleaned.replace("’", "'").replace("`", "'").replace("‘", "'")
    lower = cleaned.lower()
    normalized = cleaned.replace("\u2795", "+").replace("➕", "+")

    # Reject bot invoices, commands, or internal shop messages
    invoice_keywords = (
        "to'lov summasi", "to'lov muddati", "buyurtma #", "so'rov #",
        "admin panel", "karta raqami:", "qabul qiluvchi:", "balansdan to'lash",
        "humo to'lov:", "оплата через humo", "humo payment:", "spisanie",
        "yechildi", "chiqim", "oplata:", "oplata tovar", "karta blok",
        "komissiya", "avtomatik to'lov:", "yechib olindi",
    )
    if any(k in lower for k in invoice_keywords):
        return None

    deposit_markers = (
        "tushum", "kirim", "popolnenie", "prihod", "postuplenie",
        "to'ldirish", "toldirish", "to'ldirildi", "toldirildi",
        "hisobingiz to'ldirildi", "karta to'ldirildi", "kartangiz to'ldirildi",
        "kelib tushdi", "перевод на карту", "зачисление", "пополнение",
    )
    if not (any(m in lower for m in deposit_markers) or "+" in normalized):
        return None

    for line in normalized.splitlines():
        line = line.strip()
        # +10499 UZS, + 10.168,00 UZS, +15000 so'm, To'ldirish: 15000
        m = re.search(r"\+\s*([0-9]+(?:[.,\s][0-9]{3})*(?:[.,][0-9]{1,2})?|[0-9]+)", line)
        if not m:
            m = re.search(r"(?:to'?ldirish|tushum|kirim|popolnenie)[:\s]+\+?\s*([0-9]+(?:[.,\s][0-9]{3})*(?:[.,][0-9]{1,2})?|[0-9]+)", line, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(" ", "")
            if "." in raw and "," in raw:
                if raw.rfind(",") > raw.rfind("."):
                    raw = raw.replace(".", "").replace(",", ".")
                else:
                    raw = raw.replace(",", "")
            elif "." in raw:
                # Agar nuqtadan keyin 2 ta raqam bo'lsa (10168.00)
                parts = raw.split(".")
                if len(parts) == 2 and len(parts[1]) in (1, 2):
                    pass
                else:
                    raw = raw.replace(".", "")
            elif "," in raw:
                parts = raw.split(",")
                if len(parts) == 2 and len(parts[1]) in (1, 2):
                    raw = raw.replace(",", ".")
                else:
                    raw = raw.replace(",", "")
            try:
                amt = float(raw)
                if amt >= 1000:
                    return amt
            except ValueError:
                pass
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

            bot_me = await self.bot.get_me()
            my_bot_id = bot_me.id
            my_bot_username = (bot_me.username or "").lower()

            session = StringSession(self.config.telethon_session_string) if getattr(self.config, "telethon_session_string", "") else "humo_listener_session"
            self.client = TelegramClient(
                session,
                int(self.config.tg_api_id),
                str(self.config.tg_api_hash),
                device_model="Desktop",
                system_version="Windows 11",
                app_version="5.0.0",
                lang_code="uz",
                system_lang_code="uz-UZ",
            )

            await self.client.connect()
            if not await self.client.is_user_authorized():
                logger.warning("Telethon userbot tizimga kirmagan (avtorizatsiya talab qilinadi)")
                await self.client.disconnect()
                return

            logger.info("Telethon Humo to'lov tinglovchisi ishga tushdi (Bot @{} e'tiborsiz qoldiriladi)", my_bot_username)

            @self.client.on(events.NewMessage)
            async def handler(event):
                try:
                    # Ignore outgoing messages sent by the listener account
                    if getattr(event, "out", False):
                        return

                    sender = await event.get_sender()
                    if not sender:
                        return

                    sender_id = getattr(sender, "id", 0)
                    sender_username = (getattr(sender, "username", "") or "").lower()
                    sender_title = (getattr(sender, "title", "") or getattr(sender, "first_name", "") or "").lower()

                    # CRITICAL SECURITY: Never listen to our own shop bot!
                    if sender_id == my_bot_id or (my_bot_username and sender_username == my_bot_username):
                        return

                    target_bot = getattr(self.config, "notification_bot_username", "").lstrip("@").lower()

                    # Filter to genuine bank notification sources
                    is_match = False
                    if target_bot and (target_bot == sender_username or target_bot in sender_username or target_bot in sender_title):
                        is_match = True
                    elif any(bank_tag in sender_username or bank_tag in sender_title for bank_tag in ("humo", "humocard", "payme", "click", "bank", "sms", "pay")):
                        is_match = True

                    if not is_match:
                        return

                    msg_text = event.raw_text or ""
                    logger.info("Bank/Humo xabari keldi (@{} / {}): {}", sender_username, sender_title, msg_text[:80].replace('\n', ' '))
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
        username = str(order.get("username") or "")
        lang = await self.db.get_user_lang(user_id)
        price_uzs = float(order.get("price_uzs") or amount_uzs)

        logger.info("Humo to'lov tasdiqlandi: Order #{} ({} so'm)", order_id, amount_uzs)

        if order_type == "topup":
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

            # Admin notice
            for adm_id in self.config.admin_user_ids:
                try:
                    await self.bot.send_message(
                        adm_id,
                        f"💰 <b>Humo to'lov tasdiqlandi!</b>\n\n"
                        f"🆔 Buyurtma: #{order_id}\n"
                        f"👤 Foydalanuvchi: <code>{user_id}</code> (@{username})\n"
                        f"💵 Summa: <b>{int(price_uzs):,} so'm</b>\n"
                        f"✅ Balansga muvaffaqiyatli o'tkazildi!",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            return True

        # Gift orders are dispatched via gift sender / admin confirmation
        if order_type == "gift":
            from services.gift_sender import dispatch_order_gift
            desc = f"Gift ({quantity} Stars)"
            await self.db.set_order_status(order_id, "processing")
            await dispatch_order_gift(
                self.bot,
                self.config,
                order_id,
                user_id,
                username,
                recipient,
                desc,
                price_uzs,
            )
            try:
                await self.bot.send_message(
                    user_id,
                    f"🎉 <b>Sovg'a to'lovingiz qabul qilindi!</b>\n\n"
                    f"🧸 <b>{desc}</b> sovg'asi tez orada @{recipient} ga yetkazib beriladi!\n"
                    f"💰 To'landi: <b>{int(price_uzs):,} so'm</b>",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning("Foydalanuvchiga xabar yuborilmadi: {}", e)
            return True

        # Regular service order (stars, premium)
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

            # Admin notice
            for adm_id in self.config.admin_user_ids:
                try:
                    await self.bot.send_message(
                        adm_id,
                        f"✅ <b>Humo buyurtma muvaffaqiyatli bajarildi!</b>\n\n"
                        f"🆔 Buyurtma: #{order_id}\n"
                        f"👤 Qabul qiluvchi: @{recipient}\n"
                        f"📦 Mahsulot: <b>{desc}</b>\n"
                        f"💵 Summa: <b>{int(price_uzs):,} so'm</b>",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
        except Exception as exc:
            logger.exception("Fragment fulfillment failed for order #{}: {}", order_id, exc)
            # Automatic safety refund directly to user's bot balance
            await self.db.update_user_balance_uzs(user_id, price_uzs)
            await self.db.set_order_status(order_id, "failed", error_message=f"Fragment xatosi, balansga o'tkazildi: {exc}")
            user_row = await self.db.get_user(user_id)
            new_bal_uzs = float(user_row.get("balance_uzs") or 0.0) if user_row else price_uzs
            try:
                await self.bot.send_message(
                    user_id,
                    f"⚠️ <b>Buyurtmani avtomatik yetkazishda xatolik yuz berdi.</b>\n\n"
                    f"To'lovingiz (<b>{int(price_uzs):,} so'm</b>) xavfsiz ravishda <b>bot balansingizga</b> o'tkazildi!\n"
                    f"Joriy balansingiz: <b>{int(new_bal_uzs):,} so'm</b>\n\n"
                    f"<i>Siz balansingiz orqali qayta xarid qilishingiz mumkin.</i>",
                    parse_mode="HTML",
                )
            except Exception:
                pass

            # Notify admin
            for adm_id in self.config.admin_user_ids:
                try:
                    await self.bot.send_message(
                        adm_id,
                        f"⚠️ <b>Humo buyurtma #{order_id} Fragment xatosi!</b>\n\n"
                        f"To'lov ({int(price_uzs):,} so'm) xavfsiz ravishda foydalanuvchi <code>{user_id}</code> balansiga o'tkazildi.\n"
                        f"Xatolik: <code>{exc}</code>",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

        return True

    async def _check_expired_humo_orders(self) -> None:
        """Cancel Humo orders that passed the timeout silently."""
        now = datetime.now().isoformat(timespec="seconds")
        pending = await self.db._fetch(
            "SELECT * FROM orders WHERE payment_type = 'humo' AND status = 'pending' AND expires_at < ?",
            (now,),
        )
        for order in pending:
            order_id = int(order["id"])
            await self.db.set_order_status(order_id, "cancelled")
            logger.info("Humo buyurtma #{} muddati o'tib bekor qilindi", order_id)

    async def _sleep(self, seconds: int) -> None:
        if not self._stop_event:
            await asyncio.sleep(seconds)
            return
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass
