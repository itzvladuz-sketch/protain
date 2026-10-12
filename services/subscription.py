"""Mandatory channel subscription checker service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger

from locales import t
from services.db import Database


async def check_subscription(bot: Bot, user_id: int, db: Database) -> Tuple[bool, List[Dict[str, Any]]]:
    """Check whether user is subscribed to all mandatory channels.
    
    Returns (is_subscribed_to_all, unsubscribed_channels_list).
    """
    channels = await db.get_channels()
    if not channels:
        return True, []

    unsubscribed = []
    for ch in channels:
        ch_id = ch["channel_id"]
        try:
            # Try chat member check
            chat_id = int(ch_id) if (ch_id.startswith("-") and ch_id[1:].isdigit()) else ch_id
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ("left", "kicked"):
                unsubscribed.append(ch)
        except Exception as err:
            logger.warning("Kanal obunasini tekshirishda xatolik {}: {}", ch_id, err)
            # If bot is not admin in channel, let's treat user as subscribed or log warning
            pass

    return len(unsubscribed) == 0, unsubscribed


def build_sub_keyboard(
    unsubscribed: List[Dict[str, Any]], lang: str = "uz", ref_id: Optional[int] = None
) -> InlineKeyboardMarkup:
    """Build keyboard with subscription links and a verify button."""
    buttons = []
    for i, ch in enumerate(unsubscribed, 1):
        btn_text = f"📢 {i}. {ch['title']}"
        buttons.append([InlineKeyboardButton(text=btn_text, url=ch["url"])])

    check_cb = f"sub_check:{ref_id}" if ref_id else "sub_check:0"
    buttons.append([
        InlineKeyboardButton(text=t(lang, "btn_sub_check"), callback_data=check_cb)
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
