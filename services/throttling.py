"""Anti-Flood and Throttling Middleware to protect bot against button and message spam."""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from services.config import BotConfig


class ThrottlingMiddleware(BaseMiddleware):
    """Sliding window rate-limiter for messages and callbacks."""

    def __init__(self, config: BotConfig, burst_limit: int = 5, window_seconds: float = 2.0):
        self.config = config
        self.burst_limit = burst_limit
        self.window_seconds = window_seconds
        self._user_history: Dict[int, list[float]] = {}
        self._last_warned: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        uid = user.id

        # Admins are exempt from rate limiting
        if uid in self.config.admin_ids:
            return await handler(event, data)

        now = time.time()
        history = self._user_history.setdefault(uid, [])
        # Prune timestamps older than window
        self._user_history[uid] = [t for t in history if (now - t) < self.window_seconds]
        history = self._user_history[uid]

        if len(history) >= self.burst_limit:
            last_w = self._last_warned.get(uid, 0.0)
            if now - last_w > 2.0:
                self._last_warned[uid] = now
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer("⚠️ Iltimos, juda tez bosmang! Biroz kuting.", show_alert=False)
                    except Exception:
                        pass
                elif isinstance(event, Message):
                    try:
                        await event.answer("⚠️ Juda ko'p so'rov yuborildi. Iltimos, biroz kuting.")
                    except Exception:
                        pass
            return None

        history.append(now)
        return await handler(event, data)
