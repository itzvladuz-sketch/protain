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
    """Parse incoming bank payment sum from notification message (Humo, Click, Bank SMS).
    Strictly matches deposit messages (e.g. +50 000 UZS, Karta to'ldirildi: +50 000 UZS, Click: Summa 15 000 UZS).
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
        "humo to'lov:", "click to'lov:", "оплата через humo", "оплата через click",
        "humo payment:", "click payment:", "spisanie", "yechildi", "chiqim",
        "oplata:", "oplata tovar", "karta blok", "komissiya",
        "avtomatik to'lov:", "yechib olindi", "snyatie", "списание",
    )
    if any(k in lower for k in invoice_keywords):
        return None

    deposit_markers = (
        "tushum", "kirim", "popolnenie", "prihod", "postuplenie",
        "to'ldirish", "toldirish", "to'ldirildi", "toldirildi",
        "hisobingiz to'ldirildi", "karta to'ldirildi", "kartangiz to'ldirildi",
        "kelib tushdi", "перевод на карту", "зачисление", "пополнение",
        "vhodjaschij", "vhod", "o'tkazma", "перевод", "postupili",
        "zachislenie", "perevod",
    )
    if not (any(m in lower for m in deposit_markers) or "+" in normalized):
        return None

    for raw_line in normalized.splitlines():
        # Split by comma, semicolon, or sentence-ending period (. followed by whitespace)
        chunks = re.split(r"[,;]|\.\s+", raw_line)
        for line in chunks:
            line = line.strip()
            line_lower = line.lower()
            if not line:
                continue
            # Skip balance chunks so we never confuse total balance with incoming amount
            if any(b in line_lower for b in ("balans:", "баланс:", "qoldiq:", "остаток:", "balance:")):
                continue
            # Skip card number chunks
            if re.search(r"^(?:karta|карта|card|pan|schet|счет)[:\s]+[0-9* ]{8,}", line_lower):
                continue

            # Try matching with +
            m = re.search(r"\+\s*([0-9]+(?:[.,\s][0-9]{3})*(?:[.,][0-9]{1,2})?|[0-9]+)", line)
            if not m:
                # Try matching with keywords like Summa, to'ldirish, etc.
                m = re.search(
                    r"(?:to'?ldirish|tushum|kirim|popolnenie|summa|сумма|зачисление|zachislenie|perevod|o'?tkazma)[:\s]+\+?\s*([0-9]+(?:[.,\s][0-9]{3})*(?:[.,][0-9]{1,2})?|[0-9]+)",
                    line,
                    re.IGNORECASE,
                )
            if not m and any(m in lower for m in deposit_markers):
                # Try matching amount followed by currency: 15 000 UZS
                m = re.search(
                    r"(?:^|[\s:+])([0-9]+(?:[.,\s][0-9]{3})*(?:[.,][0-9]{1,2})?|[0-9]+)\s*(?:uzs|so'?m|sum|сум)",
                    line,
                    re.IGNORECASE,
                )

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
        """Connect Telethon client and listen for incoming messages.

        Session strategy — uses StringSession from .env as primary:
        1. Load TELETHON_SESSION_STRING from .env
        2. Connect and verify authorization
        3. After successful connection, save the (potentially updated) session
           string back to .env so it stays fresh across restarts
        4. On disconnect/reconnect, the updated string is always available
        """
        try:
            from telethon import TelegramClient, events
            from telethon.sessions import StringSession
            import dotenv

            bot_me = await self.bot.get_me()
            my_bot_id = bot_me.id
            my_bot_username = (bot_me.username or "").lower()

            clean_session = (getattr(self.config, "telethon_session_string", "") or "").strip().strip("'\"")

            if not clean_session:
                logger.warning(
                    "TELETHON_SESSION_STRING .env faylida topilmadi. "
                    "Avval 'python telethon_auth.py' orqali sessiya yarating."
                )
                return

            # Connect using StringSession
            self.client = TelegramClient(
                StringSession(clean_session),
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
                logger.warning(
                    "Telethon sessiyasi eskirgan yoki yaroqsiz. "
                    "Qayta avtorizatsiya qiling: python telethon_auth.py"
                )
                await self.client.disconnect()
                self.client = None
                return

            # Save the (potentially refreshed) session back to .env
            try:
                updated_str = StringSession.save(self.client.session)
                if updated_str and updated_str != clean_session:
                    dotenv.set_key(".env", "TELETHON_SESSION_STRING", updated_str)
                    logger.info("Telethon session string .env ga yangilandi")
            except Exception as save_err:
                logger.debug("Session stringni .env ga saqlashda xatolik (kritik emas): {}", save_err)

            logger.info("Telethon Humo to\'lov tinglovchisi ishga tushdi (Bot @{} e\'tiborsiz qoldiriladi)", my_bot_username)

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

                    raw_targets = getattr(self.config, "notification_bot_username", "")
                    target_bots = [b.strip().lstrip("@").lower() for b in raw_targets.replace(";", ",").split(",") if b.strip()]

                    # Filter to genuine bank notification sources (Humo, Click, Bank SMS)
                    is_match = False
                    if target_bots and any(tb == sender_username or tb in sender_username or tb in sender_title for tb in target_bots):
                        is_match = True
                    elif any(bank_tag in sender_username or bank_tag in sender_title for bank_tag in (
                        "humo", "humocard", "payme", "click", "clickuz", "bank", "sms", "pay",
                        "uzum", "anor", "tbc", "infin", "kapital", "agro", "xalq", "hamkor",
                        "ipak", "ipoteka", "davr", "trust", "milliy", "nbu", "sqb", "asakabank", "paynet"
                    )):
                        is_match = True

                    msg_text = event.raw_text or ""
                    amt = extract_amount_uzs(msg_text)
                    # If it's a known bank bot OR if message is unambiguously a deposit notification with amount
                    if amt and (is_match or any(k in msg_text.lower() for k in ("tushum", "kirim", "to'ldirildi", "toldirildi", "karta to'ldirildi", "hisobingiz to'ldirildi", "зачисление", "пополнение", "kelib tushdi"))):
                        logger.info("To'lov xabari aniqlandi: {} so'm (yuboruvchi: @{} / {})", amt, sender_username, sender_title)
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
            logger.info("Mos keluvchi Humo/Click buyurtma topilmadi (summa: {} so'm)", amount_uzs)
            for adm_id in self.config.admin_user_ids:
                try:
                    await self.bot.send_message(
                        adm_id,
                        f"🔔 <b>Kartaga to'lov kelib tushdi!</b>\n\n"
                        f"💰 Summa: <b>{int(amount_uzs):,} so'm</b>\n\n"
                        f"ℹ️ <i>Mos keluvchi faol buyurtma topilmadi. Agar biror foydalanuvchi adashib o'tkazgan bo'lsa, <code>/pay @username {int(amount_uzs)}</code> orqali hisobiga qo'shishingiz mumkin.</i>",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            return False

        order_id = int(order["id"])
        # ATOMIC ACQUIRE: prevent duplicate/concurrent fulfillment of same order
        if not await self.db.acquire_pending_order(order_id):
            logger.info("Buyurtma #{} allaqachon boshqa vazifa tomonidan qabul qilingan", order_id)
            return False

        user_id = int(order["user_id"])
        order_type = str(order.get("order_type") or "stars")
        quantity = int(order.get("quantity") or 1)
        recipient = str(order.get("recipient_username") or "")
        username = str(order.get("username") or "")
        lang = await self.db.get_user_lang(user_id)
        price_uzs = float(order.get("price_uzs") or amount_uzs)

        logger.info("Humo/Click to'lov tasdiqlandi: Order #{} ({} so'm)", order_id, amount_uzs)

        if order_type == "topup":
            u_before = await self.db.get_user(user_id)
            old_bal_u = float(u_before.get("balance_uzs") or 0.0) if u_before else 0.0
            await self.db.update_user_balance_uzs(user_id, price_uzs)
            await self.db.set_order_status(order_id, "completed")
            user_row = await self.db.get_user(user_id)
            new_bal_uzs = float(user_row.get("balance_uzs") or 0.0) if user_row else price_uzs
            try:
                await self.db.record_transaction(
                    user_id=user_id,
                    tx_type="card_topup",
                    amount_uzs=price_uzs,
                    old_balance_uzs=old_bal_u,
                    new_balance_uzs=new_bal_uzs,
                    order_id=order_id,
                    comment="Karta (Humo/Click) orqali avtomatik to'ldirildi",
                )
            except Exception as _e:
                logger.warning("Tranzaksiya qaydida xatolik: {}", _e)
            try:
                await self.bot.send_message(
                    user_id,
                    t(lang, "balance_topup_uzs_completed", amount=int(price_uzs), new_balance=int(new_bal_uzs)),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning("Foydalanuvchiga bildirishnoma yuborilmadi: {}", e)

            # Admin notice: Faqat axborot (tasdiqlash tugmalari talab qilinmaydi)
            for adm_id in self.config.admin_user_ids:
                try:
                    await self.bot.send_message(
                        adm_id,
                        f"💰 <b>To'lov avtomatik qabul qilindi!</b>\n\n"
                        f"🆔 Buyurtma: #{order_id} (Balans to'ldirish)\n"
                        f"👤 Foydalanuvchi: <code>{user_id}</code> (@{username or 'yoq'})\n"
                        f"💵 Summa: <b>{int(price_uzs):,} so'm</b>\n"
                        f"✅ Foydalanuvchi balansiga avtomatik o'tkazildi!\n"
                        f"👛 Yangi balansi: <b>{int(new_bal_uzs):,} so'm</b>",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            return True

        # VIP Membership activation
        if order_type.startswith("vip_"):
            days = 1 if order_type == "vip_1d" else (7 if order_type == "vip_7d" else 15)
            vip_exp = await self.db.set_user_vip(user_id, days)
            await self.db.set_order_status(order_id, "completed")
            u_row = await self.db.get_user(user_id)
            cur_bal = float(u_row.get("balance_uzs") or 0.0) if u_row else 0.0
            try:
                await self.db.record_transaction(
                    user_id=user_id,
                    tx_type="vip_purchase",
                    amount_uzs=price_uzs,
                    old_balance_uzs=cur_bal,
                    new_balance_uzs=cur_bal,
                    order_id=order_id,
                    comment=f"{days} kunlik VIP Pass (Karta orqali)",
                )
            except Exception:
                pass

            try:
                await self.bot.send_message(
                    user_id,
                    f"🎉 <b>Premium Optom Tarif muvaffaqiyatli faollashtirildi!</b>\n\n"
                    f"⭐ Tarif: <b>{days} kunlik VIP Pass</b>\n"
                    f"📅 Amal qilish muddati: <b>{vip_exp[:16]}</b> gacha\n"
                    f"💰 To'landi: <b>{int(price_uzs):,} so'm</b>\n\n"
                    f"🌟 <i>Endi botdagi barcha Stars va xizmatlar siz uchun 0% komissiyada (o'z tannarxida) taqdim etiladi!</i>",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning("Foydalanuvchiga VIP bildirishnomasi bormadi: {}", e)

            for adm_id in self.config.admin_user_ids:
                try:
                    await self.bot.send_message(
                        adm_id,
                        f"⭐ <b>Yangi Premium obuna xarid qilindi!</b>\n\n"
                        f"👤 Foydalanuvchi: <code>{user_id}</code> (@{username or 'yoq'})\n"
                        f"⚡ Tarif: <b>{days} kunlik VIP</b>\n"
                        f"💵 Summa: <b>{int(price_uzs):,} so'm</b>\n"
                        f"📅 Tugash vaqti: <b>{vip_exp[:16]}</b>",
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

            for adm_id in self.config.admin_user_ids:
                try:
                    await self.bot.send_message(
                        adm_id,
                        f"🎁 <b>Sovg'a to'lovi avtomatik qabul qilindi!</b>\n\n"
                        f"🆔 Buyurtma: #{order_id}\n"
                        f"👤 Foydalanuvchi: <code>{user_id}</code> (@{username or 'yoq'})\n"
                        f"👤 Qabul qiluvchi: @{recipient}\n"
                        f"🧸 Sovg'a: <b>{desc}</b>\n"
                        f"💵 Summa: <b>{int(price_uzs):,} so'm</b>\n"
                        f"✅ To'lov qabul qilindi va yetkazish navbatiga qo'yildi!",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
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

            is_vip_user = await self.db.is_user_vip(user_id)
            saved_uzs = 0.0
            if is_vip_user and order_type == "stars":
                price_row = await self.db.get_price("stars")
                comm = float(price_row.get("commission_percent", 8.5168)) / 100
                rate = getattr(self.config, "usd_to_uzs_rate", 12900.0)
                base_usd = float(price_row.get("base_price_usd", 0.015))
                regular_cost = round(base_usd * quantity * (1 + comm) * rate)
                saved_uzs = max(0.0, float(regular_cost - price_uzs))
                if saved_uzs > 0:
                    await self.db.add_vip_savings(user_id, saved_uzs)

            from services.receipt import format_order_receipt
            receipt_text = format_order_receipt(
                order_id=order_id,
                order_type=order_type,
                desc=desc,
                recipient=recipient,
                price_uzs=float(price_uzs),
                payment_method="Humo / Click",
                lang=lang,
                is_vip=is_vip_user,
                saved_uzs=saved_uzs,
                tx_hash=tx,
            )

            await self.bot.send_message(
                user_id,
                receipt_text,
                parse_mode="HTML",
            )

            # Admin notice: Faqat axborot (hech qanday qo'lda tasdiqlash talab qilinmaydi)
            for adm_id in self.config.admin_user_ids:
                try:
                    await self.bot.send_message(
                        adm_id,
                        f"🎉 <b>To'lov kelib tushdi va avtomatik yetkazildi!</b>\n\n"
                        f"🆔 Buyurtma: #{order_id}\n"
                        f"👤 Foydalanuvchi: <code>{user_id}</code> (@{username or 'yoq'})\n"
                        f"👤 Qabul qiluvchi: @{recipient}\n"
                        f"📦 Mahsulot: <b>{desc}</b>\n"
                        f"💵 Summa: <b>{int(price_uzs):,} so'm</b>\n\n"
                        f"⚡️ <i>Fragment orqali avtomatik muvaffaqiyatli yetkazildi!</i>",
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
        """Cancel Humo orders that passed the timeout silently in one fast batch query."""
        try:
            cancelled_count = await self.db.cancel_expired_card_orders()
            if cancelled_count > 0:
                logger.info("Muddati o'tgan {} ta Humo/Click buyurtma bekor qilindi", cancelled_count)
        except Exception as err:
            logger.warning("Muddati o'tgan buyurtmalarni tekshirishda xatolik: {}", err)

    async def _sleep(self, seconds: int) -> None:
        if not self._stop_event:
            await asyncio.sleep(seconds)
            return
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass
