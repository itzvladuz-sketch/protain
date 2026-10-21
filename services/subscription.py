"""Mandatory channel subscription checker service and middleware."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, TelegramObject
from loguru import logger

from locales import t
from services.config import BotConfig
from services.db import Database


import time

_CHANNELS_CACHE: Optional[List[Dict[str, Any]]] = None
_CHANNELS_CACHE_TIME: float = 0.0
_USER_SUB_CACHE: Dict[int, float] = {}  # user_id -> timestamp when confirmed subscribed
SUB_CACHE_TTL = 900.0  # 15 minutes cache for confirmed subscriptions (prevents button lag)
CHANNELS_CACHE_TTL = 300.0  # 5 minutes cache for mandatory channel list


def invalidate_subscription_cache(user_id: Optional[int] = None) -> None:
    """Invalidate channel cache or a specific user's subscription cache."""
    global _CHANNELS_CACHE, _CHANNELS_CACHE_TIME
    if user_id:
        _USER_SUB_CACHE.pop(user_id, None)
    else:
        _CHANNELS_CACHE = None
        _CHANNELS_CACHE_TIME = 0.0
        _USER_SUB_CACHE.clear()


async def check_subscription(
    bot: Bot,
    user_id: int,
    db: Database,
    force: bool = False,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Check whether user is subscribed to all mandatory channels.

    Returns (is_subscribed_to_all, unsubscribed_channels_list).
    """
    global _CHANNELS_CACHE, _CHANNELS_CACHE_TIME
    now = time.time()

    # Fast cache check: If user was confirmed subscribed recently, return immediately (< 1ms)
    if not force and user_id in _USER_SUB_CACHE:
        if (now - _USER_SUB_CACHE[user_id]) < SUB_CACHE_TTL:
            return True, []

    # Get cached channels or query DB
    if _CHANNELS_CACHE is not None and (now - _CHANNELS_CACHE_TIME) < CHANNELS_CACHE_TTL:
        channels = _CHANNELS_CACHE
    else:
        channels = await db.get_channels()
        _CHANNELS_CACHE = channels
        _CHANNELS_CACHE_TIME = now

    if not channels:
        _USER_SUB_CACHE[user_id] = now
        return True, []

    unsubscribed = []
    for ch in channels:
        ch_id = str(ch.get("channel_id") or "").strip()
        if not ch_id:
            continue

        try:
            chat_id: Any = int(ch_id) if (ch_id.startswith("-") and ch_id[1:].isdigit()) else ch_id
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status not in ("creator", "administrator", "member", "restricted"):
                unsubscribed.append(ch)
        except TelegramBadRequest as bad_req:
            err_msg = str(bad_req).lower()
            if any(k in err_msg for k in ("participant_id_invalid", "user_not_participant", "user not found", "member not found")):
                unsubscribed.append(ch)
            else:
                logger.warning("Kanal obunasi tekshiruvida TelegramBadRequest {}: {}", ch_id, bad_req)
        except Exception as err:
            err_msg = str(err).lower()
            if any(k in err_msg for k in ("participant_id_invalid", "user_not_participant", "user not found")):
                unsubscribed.append(ch)
            else:
                logger.warning("Kanal obunasini tekshirishda kutilmagan xatolik {}: {}", ch_id, err)

    if not unsubscribed:
        _USER_SUB_CACHE[user_id] = now
        return True, []
    else:
        _USER_SUB_CACHE.pop(user_id, None)
        return False, unsubscribed


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


class SubscriptionMiddleware(BaseMiddleware):
    """Aiogram middleware that enforces mandatory channel subscription for all non-admin users."""

    def __init__(self, db: Database, config: BotConfig):
        super().__init__()
        self.db = db
        self.config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user or user.is_bot:
            return await handler(event, data)

        # Admins always bypass channel subscription checks
        if user.id in self.config.admin_user_ids:
            return await handler(event, data)

        # Allow certain messages and callbacks
        if isinstance(event, Message):
            text = (event.text or "").strip()
            # Allow /start so start handler can parse referral params and show prompt
            if text.startswith("/start"):
                return await handler(event, data)
        elif isinstance(event, CallbackQuery):
            data_val = event.data or ""
            # Allow checking subscription, changing language, or admin callbacks
            if (
                data_val.startswith("sub_check:")
                or data_val.startswith("set_lang:")
                or data_val.startswith("adm:")
                or data_val.startswith("del_ch:")
                or data_val.startswith("back:main")
            ):
                return await handler(event, data)

        bot: Bot = data.get("bot") or getattr(event, "bot", None)
        if not bot:
            return await handler(event, data)

        is_sub, unsub = await check_subscription(bot, user.id, self.db)
        if not is_sub:
            db_user = await self.db.get_user(user.id)
            lang = (db_user.get("lang") if db_user else None) or "uz"

            if isinstance(event, CallbackQuery):
                await event.answer(t(lang, "sub_not_completed"), show_alert=True)
                try:
                    await event.message.edit_text(
                        t(lang, "sub_required_title"),
                        reply_markup=build_sub_keyboard(unsub, lang),
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
                return
            elif isinstance(event, Message):
                await event.answer(
                    t(lang, "sub_required_title"),
                    reply_markup=build_sub_keyboard(unsub, lang),
                    parse_mode="HTML",
                )
                return

        return await handler(event, data)
