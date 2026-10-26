"""Start handler: language selection, main menu, balance, help, orders history."""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
)
from dotenv import load_dotenv

from locales import t
from services.config import BotConfig
from services.db import STATUS_EMOJIS, Database
from services.icons import ICONS, tg_icon
from services.ui import safe_answer, safe_edit_text

load_dotenv()
router = Router()


class LangSelect(StatesGroup):
    selecting = State()


# ─── Keyboards ────────────────────────────────────────────────────────────────

def _lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek",    callback_data="set_lang:uz"),
            InlineKeyboardButton(text="🇷🇺 Русский",   callback_data="set_lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English",   callback_data="set_lang:en"),
        ]
    ])


def _main_menu_keyboard(lang: str, is_vip: bool = False) -> InlineKeyboardMarkup:
    vip_btn_text = "👑 VIP Tarif: Faol (0%)" if is_vip else "👑 VIP Optom Tarif (0%)"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=vip_btn_text, callback_data="menu:vip", icon_custom_emoji_id=ICONS["crown"]),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_stars"),   callback_data="menu:stars",    icon_custom_emoji_id=ICONS["star"]),
            InlineKeyboardButton(text=t(lang, "btn_premium"), callback_data="menu:premium",  icon_custom_emoji_id=ICONS["diamond"]),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_gift"),    callback_data="menu:gift",     icon_custom_emoji_id=ICONS["gift"]),
            InlineKeyboardButton(text=t(lang, "btn_balance"), callback_data="menu:balance",  icon_custom_emoji_id=ICONS["wallet"], style="success"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_referral"), callback_data="menu:referral", icon_custom_emoji_id=ICONS["users"]),
            InlineKeyboardButton(text=t(lang, "btn_orders"),  callback_data="menu:orders",   icon_custom_emoji_id=ICONS["orders"]),
        ],
        [
            InlineKeyboardButton(text=t(lang, "btn_help"),    callback_data="menu:help",     icon_custom_emoji_id=ICONS["help"], style="danger"),
            InlineKeyboardButton(text=t(lang, "btn_language"), callback_data="menu:language", icon_custom_emoji_id=ICONS["globe"]),
        ],
    ])


# ─── /start ──────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    config = BotConfig.load()
    db = Database(config.database_path)
    user = message.from_user
    if not user:
        return

    # Check start referral payload: /start ref12345 or /start ref_12345
    ref_id = None
    args = (message.text or "").split(maxsplit=1)
    if len(args) > 1:
        param = args[1].strip()
        if param.startswith("ref_"):
            val = param[4:]
            if val.isdigit():
                ref_id = int(val)
        elif param.startswith("ref") and param[3:].isdigit():
            ref_id = int(param[3:])

    existing = await db.get_or_create_user(user.id, user.username, ref_by=ref_id)
    lang = existing.get("lang") or "uz"

    # Mandatory channel subscription check
    from services.subscription import check_subscription, build_sub_keyboard
    is_subscribed, unsubscribed = await check_subscription(message.bot, user.id, db)
    if not is_subscribed:
        await message.answer(
            t(lang, "sub_required_title"),
            reply_markup=build_sub_keyboard(unsubscribed, lang, ref_id),
            parse_mode="HTML",
        )
        return

    # If user joined via referral and is subscribed, reward referrer
    stored_ref = existing.get("ref_by") or ref_id
    if stored_ref and stored_ref != user.id:
        rewarded = await db.reward_referral(stored_ref, user.id, stars=2)
        if rewarded:
            await db.clear_user_referrer(user.id)
            referrer_user = await db.get_user(stored_ref)
            tot_stars = int(referrer_user.get("referral_stars") or 2) if referrer_user else 2
            ref_lang = await db.get_user_lang(stored_ref)
            try:
                await message.bot.send_message(
                    stored_ref,
                    t(ref_lang, "referral_reward_notice", total_stars=tot_stars),
                    parse_mode="HTML",
                )
            except Exception:
                pass

    if existing.get("lang"):
        name = f"@{user.username}" if user.username else (user.full_name or "Foydalanuvchi")
        if existing.get("is_banned"):
            await message.answer(t(lang, "error_banned", support=config.support_username))
            return
        from services.currency import format_balance
        # Fresh balans uchun get_user
        fresh_user = await db.get_user(user.id) or existing
        user_num = fresh_user.get("id", 1)
        bal_str = format_balance(float(fresh_user.get("balance_uzs") or 0.0), lang, config)
        await message.answer(
            t(lang, "welcome", name=name, user_num=user_num, balance=bal_str),
            reply_markup=_main_menu_keyboard(lang, is_vip=await db.is_user_vip(user.id)),
            parse_mode="HTML",
        )
        return

    await state.set_state(LangSelect.selecting)
    await message.answer(
        t("uz", "lang_select"),
        reply_markup=_lang_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("set_lang:"))
async def set_lang(callback: CallbackQuery, state: FSMContext) -> None:
    lang = callback.data.split(":", 1)[1]
    if lang not in ("uz", "ru", "en"):
        await callback.answer()
        return

    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    await db.update_user_lang(user.id, lang)

    from services.currency import format_balance
    user_num = db_user.get("id", 1)
    bal_str = format_balance(float(db_user.get("balance_uzs") or 0.0), lang, config)

    name = f"@{user.username}" if user.username else (user.full_name or "Foydalanuvchi")
    await callback.message.edit_text(
        t(lang, "welcome", name=name, user_num=user_num, balance=bal_str),
        reply_markup=_main_menu_keyboard(lang, is_vip=await db.is_user_vip(user.id)),
        parse_mode="HTML",
    )
    await state.clear()
    await callback.answer(t(lang, "language_changed"))


# ─── Main menu callbacks ──────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:language")
async def menu_language(callback: CallbackQuery) -> None:
    await safe_answer(callback)
    await safe_edit_text(
        callback.message,
        t("uz", "lang_select"),
        reply_markup=_lang_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "menu:balance")
async def menu_balance(callback: CallbackQuery) -> None:
    await safe_answer(callback)
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_user(user.id)
    if not db_user:
        db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")
    balance_uzs = float(db_user.get("balance_uzs") or 0.0)

    from services.currency import format_balance
    formatted_bal = format_balance(balance_uzs, lang, config)

    balance_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ " + t(lang, "btn_topup"), callback_data="balance:topup", icon_custom_emoji_id=ICONS["plus"]),
            InlineKeyboardButton(text="💸 Pul yechish", callback_data="balance:withdraw", icon_custom_emoji_id=ICONS["money"]),
        ],
        [
            InlineKeyboardButton(text="📜 Tranzaksiyalar tarixi", callback_data="balance:history", icon_custom_emoji_id=ICONS["orders"]),
        ],
        [InlineKeyboardButton(text=t(lang, "btn_back"),  callback_data="back:main", icon_custom_emoji_id=ICONS["back"])],
    ])
    user_num = db_user.get("id", 1)
    await safe_edit_text(
        callback.message,
        t(lang, "balance_info", balance=formatted_bal, balance_uzs=int(balance_uzs), user_num=user_num),
        reply_markup=balance_kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data == "menu:help")
async def menu_help(callback: CallbackQuery) -> None:
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")
    sup_user = (config.support_username or "id_4448").lstrip("@")

    help_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_support"), url=f"https://t.me/{sup_user}", icon_custom_emoji_id=ICONS["user"])],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main", icon_custom_emoji_id=ICONS["back"])],
    ])
    try:
        await callback.message.edit_text(
            t(lang, "help_text", support=sup_user),
            reply_markup=help_kb,
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "menu:orders")
async def menu_orders(callback: CallbackQuery) -> None:
    await callback.answer()
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")
    orders = await db.get_user_orders(user.id, limit=10)

    order_nav_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_refresh"), callback_data="menu:orders", icon_custom_emoji_id=ICONS["sparkle"])],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main", icon_custom_emoji_id=ICONS["back"])],
    ])

    if not orders:
        try:
            await callback.message.edit_text(
                t(lang, "no_orders"),
                reply_markup=order_nav_kb,
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    lines = [f"{t(lang, 'my_orders')}\n"]
    for o in orders:
        order_id = o["id"]
        status = o.get("status") or "pending"
        status_key = f"status_{status}"
        order_type = o.get("order_type") or "stars"
        type_key = f"type_{order_type}"
        emoji = STATUS_EMOJIS.get(status, "•")
        status_text = t(lang, status_key)
        type_text = t(lang, type_key)

        price_uzs = float(o.get("price_uzs") or 0.0)
        price_ton = float(o.get("price_ton") or 0.0)
        if price_uzs > 0:
            price_disp = f"{int(price_uzs):,} so'm"
        elif price_ton > 0:
            price_disp = f"{price_ton:.4f} TON"
        else:
            price_disp = f"${float(o.get('price_usd') or 0):.2f}"

        raw_rec = o.get("recipient_username")
        if not raw_rec or raw_rec == "self":
            rec_disp = "Hisobga"
        else:
            rec_disp = f"@{html.escape(raw_rec.lstrip('@'))}"

        qty = o.get("quantity", 1)
        if order_type == "stars":
            item_desc = f"{qty} dona"
        elif order_type == "premium":
            item_desc = f"{qty} oy"
        elif order_type == "gift":
            item_desc = f"{qty} Sovg'a"
        else:
            item_desc = f"{price_disp}"

        date_str = str(o.get("created_at", ""))[:16].replace("T", " ")

        lines.append(
            f"<b>#{order_id}</b> | {type_text} ({item_desc})\n"
            f"   {tg_icon('pin', '📌')} Kimga: <code>{rec_disp}</code>\n"
            f"   {tg_icon('card', '💳')} Narx: <b>{price_disp}</b>\n"
            f"   {emoji} Holat: <b>{status_text}</b>"
            + (f" | <i>{date_str}</i>" if date_str else "")
        )

    text = "\n\n".join(lines)
    if len(text) > 4000:
        text = text[:3950] + "\n\n<i>... (qisqartirildi)</i>"

    try:
        await callback.message.edit_text(
            text,
            reply_markup=order_nav_kb,
            parse_mode="HTML",
        )
    except Exception:
        pass




@router.callback_query(F.data == "back:main")
async def back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_answer(callback)
    data = await state.get_data()
    order_id = data.get("order_id")
    await state.clear()
    config = BotConfig.load()
    db = Database(config.database_path)
    if order_id:
        try:
            order = await db.get_order(int(order_id))
            if order and order.get("status") == "pending" and order.get("order_type") != "topup":
                await db.set_order_status(int(order_id), "cancelled")
        except Exception:
            pass
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_user(user.id)
    if not db_user:
        db_user = await db.get_or_create_user(user.id, user.username)
    else:
        if user.username:
            await db.get_or_create_user(user.id, user.username)

    lang = db_user.get("lang", "uz")
    from services.currency import format_balance
    user_num = db_user.get("id", 1)
    bal_str = format_balance(float(db_user.get("balance_uzs") or 0.0), lang, config)
    name = f"@{user.username}" if user.username else (user.full_name or "Foydalanuvchi")

    await safe_edit_text(
        callback.message,
        t(lang, "main_menu", name=name, user_num=user_num, balance=bal_str),
        reply_markup=_main_menu_keyboard(lang, is_vip=await db.is_user_vip(user.id)),
        parse_mode="HTML",
    )
