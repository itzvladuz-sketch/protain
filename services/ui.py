"""UI helpers: safe message edit and fast callback answering to eliminate button lag."""

from __future__ import annotations

from typing import Any, Optional
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from loguru import logger


async def safe_edit_text(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML",
    **kwargs: Any,
) -> Optional[Message]:
    """Edit message text safely, suppressing 'message is not modified' and 'message to edit not found'."""
    try:
        return await message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            **kwargs,
        )
    except TelegramBadRequest as exc:
        msg = str(exc).lower()
        if "message is not modified" in msg or "message to edit not found" in msg:
            return None
        logger.warning("TelegramBadRequest in safe_edit_text: {}", exc)
        return None
    except Exception as exc:
        logger.warning("Unexpected error in safe_edit_text: {}", exc)
        return None


async def safe_answer(
    callback: CallbackQuery,
    text: Optional[str] = None,
    show_alert: bool = False,
) -> None:
    """Answer callback query safely and immediately to remove loading spinner."""
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except Exception:
        pass
