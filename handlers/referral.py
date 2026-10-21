"""Referral system and gift claiming handler."""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import quote

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
)
from loguru import logger

from locales import t
from services.config import BotConfig
from services.db import Database
from services.subscription import check_subscription, build_sub_keyboard
from services.icons import ICONS, tg_icon
from services.ui import safe_answer, safe_edit_text

router = Router()


class ClaimGiftFlow(StatesGroup):
    waiting_recipient = State()


def _referral_kb(lang: str, bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
    share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={quote(t(lang, 'referral_share_text', ref_link=ref_link))}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_claim_gift"), callback_data="ref:claim_gift", icon_custom_emoji_id=ICONS["gift"])],
        [InlineKeyboardButton(text=t(lang, "btn_share_ref"), url=share_url, icon_custom_emoji_id=ICONS["users"])],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main", icon_custom_emoji_id=ICONS["back"])],
    ])


def _claim_recipient_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_myself"), callback_data="claim:myself", icon_custom_emoji_id=ICONS["user"], style="success")],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu:referral", icon_custom_emoji_id=ICONS["back"])],
    ])


_CACHED_BOT_USERNAME: Optional[str] = None

@router.callback_query(F.data == "menu:referral")
async def menu_referral(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_answer(callback)
    await state.clear()
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")

    global _CACHED_BOT_USERNAME
    if not _CACHED_BOT_USERNAME:
        bot_info = await callback.bot.get_me()
        _CACHED_BOT_USERNAME = bot_info.username or "bot"
    bot_username = _CACHED_BOT_USERNAME
    ref_link = f"https://t.me/{bot_username}?start=ref{user.id}"

    ref_count = int(db_user.get("referral_count") or 0)
    ref_stars = int(db_user.get("referral_stars") or 0)

    text = t(
        lang,
        "referral_info",
        ref_link=ref_link,
        ref_count=ref_count,
        ref_stars=ref_stars,
    )
    await safe_edit_text(
        callback.message,
        text,
        reply_markup=_referral_kb(lang, bot_username, user.id),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "ref:claim_gift")
async def claim_gift_start(callback: CallbackQuery, state: FSMContext) -> None:
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")
    ref_stars = int(db_user.get("referral_stars") or 0)

    # Minimal: 16 stars
    if ref_stars < 16:
        needed = 16 - ref_stars
        friends_needed = (needed + 1) // 2
        await callback.answer(
            t(lang, "claim_min_stars_error", current=ref_stars, needed=needed, friends_needed=friends_needed),
            show_alert=True,
        )
        return

    await state.set_state(ClaimGiftFlow.waiting_recipient)
    await callback.message.edit_text(
        t(lang, "claim_enter_recipient"),
        reply_markup=_claim_recipient_kb(lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "claim:myself", ClaimGiftFlow.waiting_recipient)
async def claim_myself(callback: CallbackQuery, state: FSMContext) -> None:
    user = callback.from_user
    if not user:
        return

    recipient = user.username or f"id{user.id}"
    await _finalize_gift_claim(callback.message, user.id, user.username, recipient, state)
    await callback.answer()


@router.message(ClaimGiftFlow.waiting_recipient)
async def claim_enter_username(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if not user:
        return

    config = BotConfig.load()
    db = Database(config.database_path)
    lang = await db.get_user_lang(user.id)

    raw = (message.text or "").strip().replace("https://t.me/", "").replace("t.me/", "").lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{4,32}", raw):
        await message.answer(t(lang, "username_invalid"), reply_markup=_claim_recipient_kb(lang), parse_mode="HTML")
        return

    await _finalize_gift_claim(message, user.id, user.username, raw, state)


async def _finalize_gift_claim(
    target: Message, user_id: int, username: Optional[str], recipient: str, state: FSMContext
) -> None:
    config = BotConfig.load()
    db = Database(config.database_path)
    db_user = await db.get_or_create_user(user_id, username)
    lang = db_user.get("lang", "uz")
    ref_stars = int(db_user.get("referral_stars") or 0)

    if ref_stars < 16:
        await target.answer(t(lang, "error_general"), parse_mode="HTML")
        await state.clear()
        return

    # Deduct 16 stars
    deducted = await db.deduct_referral_stars(user_id, 16)
    if not deducted:
        await target.answer(t(lang, "error_general"), parse_mode="HTML")
        await state.clear()
        return

    # Create gift request
    gift_name = "🧸 Ayiqcha (15⭐)"
    req_id = await db.create_gift_request(
        user_id=user_id,
        username=username,
        recipient_username=recipient,
        stars_spent=16,
        gift_name=gift_name,
    )

    remaining = ref_stars - 16
    await state.clear()

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu:referral")]
    ])
    text = t(lang, "claim_success", gift_name=gift_name, recipient=recipient, remaining=remaining)

    try:
        await target.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
    except Exception:
        await target.answer(text, reply_markup=back_kb, parse_mode="HTML")

    # Send notification to sender service / admin
    from services.gift_sender import dispatch_gift_request
    await dispatch_gift_request(target.bot, config, req_id, user_id, username, recipient, gift_name)


# ─── Verification of Channel Subscription ─────────────────────────────────────

@router.callback_query(F.data.startswith("sub_check:"))
async def handle_sub_check(callback: CallbackQuery, state: FSMContext) -> None:
    raw_ref = callback.data.split(":", 1)[1]
    ref_id = int(raw_ref) if (raw_ref.isdigit() and int(raw_ref) > 0) else None

    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username, ref_by=ref_id)
    lang = db_user.get("lang", "uz")

    is_subscribed, unsubscribed = await check_subscription(callback.bot, user.id, db, force=True)
    if not is_subscribed:
        await callback.answer(t(lang, "sub_not_completed"), show_alert=True)
        # Update keyboard with remaining channels
        try:
            await callback.message.edit_reply_markup(reply_markup=build_sub_keyboard(unsubscribed, lang, ref_id))
        except Exception:
            pass
        return

    # Rewarding referrer if this user joined via ref_id and was just verified
    stored_ref = db_user.get("ref_by") or ref_id
    if stored_ref and stored_ref != user.id:
        rewarded = await db.reward_referral(stored_ref, user.id, stars=2)
        if rewarded:
            # Clear ref_by so it only rewards once
            await db.clear_user_referrer(user.id)
            referrer_user = await db.get_user(stored_ref)
            tot_stars = int(referrer_user.get("referral_stars") or 2) if referrer_user else 2
            ref_lang = await db.get_user_lang(stored_ref)
            try:
                await callback.bot.send_message(
                    stored_ref,
                    t(ref_lang, "referral_reward_notice", total_stars=tot_stars),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning("Referal egasiga bildirishnoma yuborilmadi: {}", e)

    await callback.answer(t(lang, "sub_verified"))

    from handlers.start import _main_menu_keyboard
    from services.currency import format_balance
    db_user = await db.get_or_create_user(user.id, user.username)
    user_num = db_user.get("id", 1)
    bal_str = format_balance(float(db_user.get("balance_uzs") or 0.0), lang, config)
    name = f"@{user.username}" if user.username else (user.full_name or "Foydalanuvchi")

    await callback.message.edit_text(
        t(lang, "welcome", name=name, user_num=user_num, balance=bal_str),
        reply_markup=_main_menu_keyboard(lang),
        parse_mode="HTML",
    )
