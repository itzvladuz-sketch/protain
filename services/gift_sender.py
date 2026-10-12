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
    """Notify admin / sender account about a new gift reward request."""
    db = Database(config.database_path)

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
