"""Gift sender service for referral rewards (via sender userbot or admin)."""

from __future__ import annotations

import os
from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger

from services.config import BotConfig
from services.db import Database


async def dispatch_gift_request(
    bot: Bot,
    config: BotConfig,
    request_id: int,
    user_id: int,
    username: Optional[str],
    recipient: str,
    gift_name: str = "🧸 Ayiqcha (15⭐)",
) -> None:
    """Notify admin / sender account about a new referral gift reward request."""
    # Check if userbot is configured
    userbot_session = os.getenv("GIFT_SENDER_SESSION", "").strip()
    userbot_api_id = os.getenv("GIFT_SENDER_API_ID", "").strip()
    userbot_api_hash = os.getenv("GIFT_SENDER_API_HASH", "").strip()

    attempted_auto = False
    if userbot_session and userbot_api_id and userbot_api_hash:
        try:
            logger.info("Attempting auto gift dispatch via userbot...")
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            client = TelegramClient(StringSession(userbot_session), int(userbot_api_id), userbot_api_hash)
            await client.connect()
            if await client.is_user_authorized():
                logger.info("Sender userbot faol, sovg'a yuborish tayyor")
                attempted_auto = True
            await client.disconnect()
        except Exception as err:
            logger.warning("Sender userbot orqali yuborishda xatolik: {}", err)

    # Notify admins with 1-click confirmation button
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yuborildi deb tasdiqlash", callback_data=f"gift_done:{request_id}")],
    ])

    admin_text = (
        f"🎁 <b>Yangi Referal Sovg'a so'rovi!</b> #{request_id}\n\n"
        f"👤 Foydalanuvchi: @{username or 'yoq'} (ID: <code>{user_id}</code>)\n"
        f"🎯 Qabul qiluvchi: <b>@{recipient}</b>\n"
        f"🧸 Sovg'a: <b>{gift_name}</b> (16 Stars yechildi)\n\n"
        f"ℹ️ <i>Ushbu sovg'ani sovg'a yuboruvchi akkaunt orqali @{recipient} ga yuboring va quyidagi tugmani bosing.</i>"
    )

    for admin_id in config.admin_user_ids:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=admin_kb, parse_mode="HTML")
        except Exception as exc:
            logger.warning("Adminga sovg'a xabari yuborilmadi {}: {}", admin_id, exc)


async def dispatch_order_gift(
    bot: Bot,
    config: BotConfig,
    order_id: int,
    user_id: int,
    username: Optional[str],
    recipient: str,
    gift_name: str,
    price_uzs: float,
) -> bool:
    """Handle paid gift order: attempt userbot dispatch or notify admin with 1-click confirmation."""
    userbot_session = os.getenv("GIFT_SENDER_SESSION", "").strip()
    userbot_api_id = os.getenv("GIFT_SENDER_API_ID", "").strip()
    userbot_api_hash = os.getenv("GIFT_SENDER_API_HASH", "").strip()

    auto_success = False
    if userbot_session and userbot_api_id and userbot_api_hash:
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            client = TelegramClient(StringSession(userbot_session), int(userbot_api_id), userbot_api_hash)
            await client.connect()
            if await client.is_user_authorized():
                # Akkaunt orqali yetkazish
                logger.info("Sovg'a yuboruvchi akkaunt orqali @{} ga {} yuborilmoqda", recipient, gift_name)
                # Kelajakda Telethon Star Gift RPC qo'shilganda to'g'ridan-to'g'ri chaqiriladi
                auto_success = False
            await client.disconnect()
        except Exception as err:
            logger.warning("Gift sender akkauntida xatolik: {}", err)

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ #{order_id} Sovg'ani yubordim (Tasdiqlash)", callback_data=f"order_gift_done:{order_id}")],
        [InlineKeyboardButton(text=f"❌ #{order_id} Bekor qilish", callback_data=f"admin_cancel:{order_id}")],
    ])

    admin_text = (
        f"🎁 <b>Yangi Sovg'a (Gift) buyurtmasi!</b> #{order_id}\n\n"
        f"👤 Buyurtmachi: @{username or 'yoq'} (ID: <code>{user_id}</code>)\n"
        f"🎯 Qabul qiluvchi: <b>@{recipient}</b>\n"
        f"🧸 Sovg'a: <b>{gift_name}</b>\n"
        f"💰 To'langan: <b>{int(price_uzs):,} so'm</b>\n\n"
        f"ℹ️ <i>Sovg'a yuboruvchi akkauntingizdan @{recipient} profiliga <b>{gift_name}</b> sovg'asini yuboring va pastdagi tugmani bosing:</i>"
    )

    for admin_id in config.admin_user_ids:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=admin_kb, parse_mode="HTML")
        except Exception as exc:
            logger.warning("Adminga sovg'a buyurtmasi xabari yuborilmadi {}: {}", admin_id, exc)

    return True
