"""Order and balance flow handler: Stars, Premium, Gift, and Balance Topup."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
)
from dotenv import load_dotenv
from loguru import logger

from locales import t
from services.config import BotConfig
from services.db import Database
from services.fragment_api import FragmentAPIService
from services.currency import format_currency, format_balance
from services.ton import TONService
from services.icons import ICONS, tg_icon

load_dotenv()
router = Router()

GIFTS_CATALOG = [
    # (svc_key, stars_amount, emoji, {"uz": "...", "ru": "...", "en": "..."})
    ("gift_15",        15,  "🧸", {"uz": "Ayiqcha",   "ru": "Мишка",    "en": "Teddy"}),
    ("gift_25",        25,  "💖", {"uz": "Yurakcha",  "ru": "Сердечко", "en": "Heart"}),
    ("gift_rose",      25,  "🌹", {"uz": "Atirgul",   "ru": "Роза",     "en": "Rose"}),
    ("gift_cake",      50,  "🎂", {"uz": "Tort",      "ru": "Торт",     "en": "Cake"}),
    ("gift_rocket",    50,  "🚀", {"uz": "Raketa",    "ru": "Ракета",   "en": "Rocket"}),
    ("gift_diamond",   50,  "💎", {"uz": "Olmos",     "ru": "Алмаз",    "en": "Diamond"}),
    ("gift_champagne", 75,  "🍾", {"uz": "Shampan",   "ru": "Шампанское", "en": "Champagne"}),
    ("gift_box",       100, "🎁", {"uz": "Sovg'a",    "ru": "Подарок",  "en": "Gift Box"}),
    ("gift_trophy",    100, "🏆", {"uz": "Kubok",     "ru": "Кубок",    "en": "Trophy"}),
]


# ─── FSM States ───────────────────────────────────────────────────────────────

class OrderFlow(StatesGroup):
    enter_recipient = State()
    enter_quantity  = State()
    confirm_order   = State()
    waiting_payment = State()


class TopupFlow(StatesGroup):
    waiting_amount = State()


# ─── Keyboards ────────────────────────────────────────────────────────────────

def _back_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main", icon_custom_emoji_id=ICONS["back"])]
    ])


def _cancel_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="back:main", icon_custom_emoji_id=ICONS["cancel"])]
    ])


def _recipient_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_myself"), callback_data="recipient:self", icon_custom_emoji_id=ICONS["user"], style="success")],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="back:main", icon_custom_emoji_id=ICONS["cancel"])],
    ])


def _payment_kb(lang: str, order_id: int, payment_type: str = "humo") -> InlineKeyboardMarkup:
    buttons = []
    if payment_type == "click":
        buttons.append([InlineKeyboardButton(
            text=f"📲 Click (@clickuz) da to'lash",
            url="https://t.me/clickuz",
            icon_custom_emoji_id=ICONS["card"],
        )])
    buttons.append([InlineKeyboardButton(text=t(lang, "btn_check_payment"), callback_data=f"check:{order_id}", icon_custom_emoji_id=ICONS["check"])])
    buttons.append([InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="back:main", icon_custom_emoji_id=ICONS["cancel"])])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _order_confirm_kb(
    lang: str,
    user_balance_uzs: float = 0.0,
    price_uzs: float = 0.0,
    price_formatted: str = "",
    config: Optional[BotConfig] = None,
    **kwargs,
) -> InlineKeyboardMarkup:
    if not config:
        config = BotConfig.load()
    bal_str = format_balance(user_balance_uzs, lang, config)
    bal_label = f"{t(lang, 'btn_pay_balance')} ({bal_str})"
    buttons = [
        [InlineKeyboardButton(text=bal_label, callback_data="pay:balance", icon_custom_emoji_id=ICONS["wallet"])],
        [
            InlineKeyboardButton(text=t(lang, "btn_pay_humo"), callback_data="pay:humo", icon_custom_emoji_id=ICONS["card"]),
            InlineKeyboardButton(text=t(lang, "btn_pay_click"), callback_data="pay:click", icon_custom_emoji_id=ICONS["card"]),
        ],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="back:main", icon_custom_emoji_id=ICONS["cancel"])],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _topup_presets_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="10 000 so'm", callback_data="topup_amt:10000", icon_custom_emoji_id=ICONS["money"]),
            InlineKeyboardButton(text="25 000 so'm", callback_data="topup_amt:25000", icon_custom_emoji_id=ICONS["money"]),
        ],
        [
            InlineKeyboardButton(text="50 000 so'm", callback_data="topup_amt:50000", icon_custom_emoji_id=ICONS["money"]),
            InlineKeyboardButton(text="100 000 so'm", callback_data="topup_amt:100000", icon_custom_emoji_id=ICONS["money"]),
        ],
        [
            InlineKeyboardButton(text="200 000 so'm", callback_data="topup_amt:200000", icon_custom_emoji_id=ICONS["money"]),
            InlineKeyboardButton(text="500 000 so'm", callback_data="topup_amt:500000", icon_custom_emoji_id=ICONS["money"]),
        ],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu:balance", icon_custom_emoji_id=ICONS["back"])],
    ])


async def _stars_presets_kb(lang: str, config: BotConfig, db: Database) -> InlineKeyboardMarkup:
    price_row = await db.get_price("stars")
    base_usd = float(price_row["base_price_usd"]) if price_row else 0.015
    commission = float(price_row["commission_percent"]) / 100 if price_row else 0.05
    discount = float(price_row.get("discount_percent", 0)) if price_row else 0.0

    presets = [50, 75, 100, 200, 350, 400, 500]
    buttons = []
    for qty in presets:
        total_usd = base_usd * qty * (1 + commission)
        if discount > 0:
            total_usd = total_usd * (1 - discount / 100)
        price_str = format_currency(total_usd, lang, config)
        buttons.append(InlineKeyboardButton(text=f"{qty} — {price_str}", callback_data=f"stars_qty:{qty}", icon_custom_emoji_id=ICONS["star"]))

    custom_text = {
        "uz": "Boshqa miqdor",
        "ru": "Другое",
        "en": "Custom",
    }.get(lang, "Boshqa miqdor")
    buttons.append(InlineKeyboardButton(text=custom_text, callback_data="stars_qty:custom", icon_custom_emoji_id=ICONS["pencil"]))

    keyboard = []
    row = []
    for btn in buttons:
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main", icon_custom_emoji_id=ICONS["back"])])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ─── Utility ──────────────────────────────────────────────────────────────────

def _normalize_username(raw: str) -> str:
    u = raw.strip().replace("https://t.me/", "").replace("t.me/", "").lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{4,32}", u):
        raise ValueError("invalid")
    return u


async def _calc_price(config: BotConfig, service: str, quantity: int = 1) -> dict:
    """Return {price_usd, price_ton, discount_percent}."""
    db = Database(config.database_path)
    price_row = await db.get_price(service)
    if not price_row:
        raise ValueError(f"Price not found for {service}")

    base_usd = float(price_row["base_price_usd"])
    commission = float(price_row["commission_percent"]) / 100
    discount = float(price_row["discount_percent"])

    if service == "stars":
        total_usd = base_usd * quantity * (1 + commission)
    else:
        total_usd = base_usd * (1 + commission)

    if discount > 0:
        total_usd = total_usd * (1 - discount / 100)

    total_usd = round(total_usd, 4)

    try:
        ton_service = TONService(config.ton_wallet_address, config.toncenter_api_key)
        rate = await ton_service.get_ton_usd_rate()
        price_ton = round(total_usd / rate, 6)
    except Exception:
        price_ton = round(total_usd / 3.5, 6)

    return {"price_usd": total_usd, "price_ton": price_ton, "discount_percent": discount}


# ─── Balance Top Up Flow ──────────────────────────────────────────────────────

async def _notify_admin_new_order(
    bot,
    config: BotConfig,
    order_id: int,
    user_id: int,
    username: str,
    order_type: str,
    price_uzs: float,
) -> None:
    db = Database(config.database_path)
    order = await db.get_order(order_id)
    payment_type = (order.get("payment_type") if order else "") or "humo"
    recipient = (order.get("recipient_username") or "") if order else ""
    qty = int(order.get("quantity") or 1) if order else 1

    if order_type == "stars":
        desc = f"{qty} Stars"
    elif order_type == "premium":
        desc = f"{qty} oy Premium"
    elif order_type == "topup":
        desc = "Balans to'ldirish"
    else:
        desc = f"{qty} Stars Gift"

    rec_line = f"👤 Qabul qiluvchi: @{recipient}\n" if recipient and recipient != "self" else ""

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ #{order_id} Tasdiqlash va yuborish", callback_data=f"admin_confirm:{order_id}", icon_custom_emoji_id=ICONS["check"])],
        [InlineKeyboardButton(text=f"❌ #{order_id} Bekor qilish", callback_data=f"admin_cancel:{order_id}", icon_custom_emoji_id=ICONS["cancel"])],
    ])

    if payment_type == "click":
        card_type_title = "Click (Uzcard)"
        card_num = config.click_card_number or "8801 9102 6669 7252"
    else:
        card_type_title = "Humo"
        card_num = config.humo_card_number or "9860 3501 4730 5402"

    caption = (
        f"{tg_icon('bell', '🔔')} <b>Yangi {card_type_title} to'lov kutilmoqda!</b>\n\n"
        f"{tg_icon('orders', '🆔')} Buyurtma: #{order_id}\n"
        f"{tg_icon('user', '👤')} Foydalanuvchi: <code>{user_id}</code> (@{username or 'yoq'})\n"
        f"{rec_line}"
        f"{tg_icon('box', '📦')} Mahsulot: <b>{desc}</b>\n"
        f"{tg_icon('dollar', '💵')} Summa: <b>{int(price_uzs):,} so'm</b>\n"
        f"{tg_icon('card', '💳')} Karta ({card_type_title}): <code>{card_num}</code>\n\n"
        f"<i>To'lov kelgach, pastdagi tugmani bosib darhol tasdiqlashingiz mumkin:</i>"
    )

    for adm_id in config.admin_user_ids:
        try:
            await bot.send_message(adm_id, caption, reply_markup=admin_kb, parse_mode="HTML")
            logger.info("Adminga (#{}: {}) to'lov bildirishnomasi yuborildi", adm_id, order_id)
        except Exception as e:
            logger.warning("Adminga bildirishnoma yuborilmadi: {}", e)


@router.callback_query(F.data == "balance:topup")
async def balance_topup(callback: CallbackQuery, state: FSMContext) -> None:
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")

    await state.set_state(TopupFlow.waiting_amount)
    await callback.message.edit_text(
        t(lang, "balance_topup_menu"),
        reply_markup=_topup_presets_kb(lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("topup_amt:"), TopupFlow.waiting_amount)
async def topup_preset_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    raw = callback.data.split(":", 1)[1]
    try:
        amt = float(raw)
    except ValueError:
        return
    await _show_topup_method_choice(callback.message, callback.from_user, amt, state)
    await callback.answer()


@router.message(TopupFlow.waiting_amount)
async def topup_manual_amount(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    db = Database(config.database_path)
    user = message.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")

    raw = (message.text or "").strip().replace(" ", "").replace(",", "")
    try:
        amt = float(raw)
        if amt < 5000 or amt > 50_000_000:
            raise ValueError
    except ValueError:
        await message.answer(t(lang, "balance_topup_min_error", min=5000), reply_markup=_topup_presets_kb(lang), parse_mode="HTML")
        return

    await _show_topup_method_choice(message, user, amt, state)


def _topup_method_kb(lang: str, amt: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Humo orqali to'lash", callback_data=f"topup_pay:humo:{amt}", icon_custom_emoji_id=ICONS["card"])],
        [InlineKeyboardButton(text="🔵 Click orqali to'lash", callback_data=f"topup_pay:click:{amt}", icon_custom_emoji_id=ICONS["card"])],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="balance:topup", icon_custom_emoji_id=ICONS["back"])],
    ])


async def _show_topup_method_choice(target: Message, user, amt: float, state: FSMContext) -> None:
    config = BotConfig.load()
    db = Database(config.database_path)
    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")

    int_amt = int(amt)
    text = (
        f"{tg_icon('card', '💳')} <b>Balansni to'ldirish summasi: {int_amt:,} so'm</b>\n\n"
        f"To'lov turini tanlang:"
    )
    kb = _topup_method_kb(lang, int_amt)
    try:
        await target.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("topup_pay:"))
async def topup_pay_selected(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    pay_type = parts[1]
    amt = float(parts[2])
    await _create_card_topup_order(callback.message, callback.from_user, amt, pay_type, state)
    await callback.answer()


async def _create_card_topup_order(target: Message, user, amt: float, pay_type: str, state: FSMContext) -> None:
    config = BotConfig.load()
    db = Database(config.database_path)
    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")

    rate = getattr(config, "usd_to_uzs_rate", 12900.0)
    final_amt = float(int(amt))
    expires_at = datetime.now() + timedelta(minutes=30)

    if pay_type == "click":
        card_num = config.click_card_number or "8801 9102 6669 7252"
        card_holder = config.click_card_holder or "CLICK CARD"
        instr_key = "click_payment_instructions"
    else:
        card_num = config.humo_card_number or "9860 3501 4730 5402"
        card_holder = config.humo_card_holder or "HUMO CARD"
        instr_key = "humo_payment_instructions"

    order_id = await db.create_order(
        user_id=user.id,
        username=user.username,
        order_type="topup",
        recipient_username=user.username or "self",
        quantity=1,
        price_usd=round(final_amt / rate, 2),
        price_ton=0.0,
        price_uzs=final_amt,
        discount_percent=0.0,
        payment_type=pay_type,
        payment_address=card_num,
        payment_comment=f"{pay_type.upper()}-{user.id}",
        expires_at=expires_at,
    )

    await state.update_data(order_id=order_id)
    await state.set_state(OrderFlow.waiting_payment)
    text = t(lang, instr_key,
             card_number=card_num,
             card_holder=card_holder,
             amount=int(final_amt))
    try:
        await target.edit_text(text, reply_markup=_payment_kb(lang, order_id, payment_type=pay_type), parse_mode="HTML")
    except Exception:
        await target.answer(text, reply_markup=_payment_kb(lang, order_id, payment_type=pay_type), parse_mode="HTML")

    # Notify admin
    await _notify_admin_new_order(target.bot, config, order_id, user.id, user.username or "", "topup", final_amt)


# ─── Stars flow ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:stars")
async def stars_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")
    price_row = await db.get_price("stars")

    if not price_row or not price_row.get("is_active"):
        await callback.message.edit_text(t(lang, "error_general"), reply_markup=_back_kb(lang), parse_mode="HTML")
        await callback.answer()
        return

    await state.update_data(service="stars")
    await state.set_state(OrderFlow.enter_recipient)

    await callback.message.edit_text(
        t(lang, "stars_menu"),
        reply_markup=_recipient_kb(lang),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Premium flow ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:premium")
async def premium_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")

    services = ["premium_1m", "premium_3m", "premium_6m", "premium_12m"]
    durations = {
        "uz": {"premium_1m": "1 oy", "premium_3m": "3 oy", "premium_6m": "6 oy", "premium_12m": "12 oy"},
        "ru": {"premium_1m": "1 мес", "premium_3m": "3 мес", "premium_6m": "6 мес", "premium_12m": "12 мес"},
        "en": {"premium_1m": "1 mo", "premium_3m": "3 mo", "premium_6m": "6 mo", "premium_12m": "12 mo"},
    }
    buttons = []
    for svc in services:
        p = await db.get_price(svc)
        if p and p.get("is_active"):
            usd = float(p["base_price_usd"]) * (1 + float(p["commission_percent"]) / 100)
            disc = float(p.get("discount_percent", 0))
            if disc:
                usd = usd * (1 - disc / 100)
            price_str = format_currency(usd, lang, config)
            dur = durations.get(lang, durations["uz"])[svc]
            disc_badge = f" (-{disc:.0f}%)" if disc else ""
            buttons.append([InlineKeyboardButton(
                text=f"{dur} — {price_str}{disc_badge}",
                callback_data=f"premium:{svc}",
                icon_custom_emoji_id=ICONS["diamond"],
            )])

    buttons.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main", icon_custom_emoji_id=ICONS["back"])])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        t(lang, "premium_menu"),
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("premium:"))
async def premium_selected(callback: CallbackQuery, state: FSMContext) -> None:
    svc = callback.data.split(":", 1)[1]
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")

    dur_months = {"premium_1m": 1, "premium_3m": 3, "premium_6m": 6, "premium_12m": 12}.get(svc, 1)
    await state.update_data(service=svc, quantity=dur_months)
    await state.set_state(OrderFlow.enter_recipient)

    await callback.message.edit_text(
        t(lang, "enter_recipient"),
        reply_markup=_recipient_kb(lang),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Gift flow (2 ta ustun, 100 Stars gacha) ──────────────────────────────────

@router.callback_query(F.data == "menu:gift")
async def gift_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")

    buttons = []
    for svc, stars_cnt, emoji, names in GIFTS_CATALOG:
        p = await db.get_price(svc)
        if not p or not p.get("is_active"):
            # Fallback calculate if not yet in db
            usd = round(stars_cnt * 0.015 * 1.05, 4)
        else:
            usd = float(p["base_price_usd"]) * (1 + float(p["commission_percent"]) / 100)
            disc = float(p.get("discount_percent", 0))
            if disc:
                usd = usd * (1 - disc / 100)
        price_str = format_currency(usd, lang, config)
        name = names.get(lang, names["uz"])
        btn_text = f"{emoji} {name} — {price_str}"
        buttons.append(InlineKeyboardButton(text=btn_text, callback_data=f"gift:{svc}", icon_custom_emoji_id=ICONS["gift"]))

    # 2 ta ustun (2 columns) qilib joylash
    keyboard = []
    row = []
    for btn in buttons:
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main", icon_custom_emoji_id=ICONS["back"])])
    kb = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback.message.edit_text(
        t(lang, "gift_menu"),
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("gift:"))
async def gift_selected(callback: CallbackQuery, state: FSMContext) -> None:
    svc = callback.data.split(":", 1)[1]
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")

    gift_item = next((g for g in GIFTS_CATALOG if g[0] == svc), None)
    if gift_item:
        amt = gift_item[1]
        name = f"{gift_item[2]} {gift_item[3].get(lang, gift_item[3]['uz'])}"
    else:
        amt = 50
        name = "Gift"

    await state.update_data(service=svc, quantity=amt, gift_name=name)
    await state.set_state(OrderFlow.enter_recipient)

    await callback.message.edit_text(
        t(lang, "enter_recipient"),
        reply_markup=_recipient_kb(lang),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Recipient self (O'zimga) ─────────────────────────────────────────────────

@router.callback_query(F.data == "recipient:self", OrderFlow.enter_recipient)
async def recipient_self(callback: CallbackQuery, state: FSMContext) -> None:
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")

    if not user.username:
        await callback.answer(t(lang, "no_username_set"), show_alert=True)
        return

    username = user.username
    await state.update_data(recipient=username)

    data = await state.get_data()
    service = data.get("service", "stars")

    if service == "stars":
        price_row = await db.get_price("stars")
        min_q = price_row["min_qty"] if price_row else 50
        max_q = price_row["max_qty"] if price_row else 50000
        await state.update_data(min_qty=min_q, max_qty=max_q)
        await state.set_state(OrderFlow.enter_quantity)
        kb = await _stars_presets_kb(lang, config, db)
        await callback.message.edit_text(
            t(lang, "select_stars_amount", recipient=username),
            reply_markup=kb,
            parse_mode="HTML",
        )
    else:
        await _show_order_summary(callback.message, state, lang, config, user_id=user.id)

    await callback.answer()


# ─── Recipient manual text entry ──────────────────────────────────────────────

@router.message(OrderFlow.enter_recipient)
async def enter_recipient(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    db = Database(config.database_path)
    user = message.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")

    try:
        username = _normalize_username(message.text or "")
    except ValueError:
        await message.answer(t(lang, "username_invalid"), reply_markup=_recipient_kb(lang), parse_mode="HTML")
        return

    await state.update_data(recipient=username)
    data = await state.get_data()
    service = data.get("service", "stars")

    if service == "stars":
        price_row = await db.get_price("stars")
        min_q = price_row["min_qty"] if price_row else 50
        max_q = price_row["max_qty"] if price_row else 50000
        await state.update_data(min_qty=min_q, max_qty=max_q)
        await state.set_state(OrderFlow.enter_quantity)
        kb = await _stars_presets_kb(lang, config, db)
        await message.answer(
            t(lang, "select_stars_amount", recipient=username),
            reply_markup=kb,
            parse_mode="HTML",
        )
    else:
        await _show_order_summary(message, state, lang, config, user_id=user.id)


# ─── Quantity entry (Stars only) ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("stars_qty:"), OrderFlow.enter_quantity)
async def stars_qty_selected(callback: CallbackQuery, state: FSMContext) -> None:
    val = callback.data.split(":", 1)[1]
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return
    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")

    if val == "custom":
        data = await state.get_data()
        min_q = data.get("min_qty", 50)
        max_q = data.get("max_qty", 50000)
        await callback.message.edit_text(
            t(lang, "enter_stars_amount", min=min_q, max=max_q),
            reply_markup=_cancel_kb(lang),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    qty = int(val)
    await state.update_data(quantity=qty)
    await state.set_state(OrderFlow.confirm_order)
    await _show_order_summary(callback.message, state, lang, config, user_id=user.id)
    await callback.answer()

@router.message(OrderFlow.enter_quantity)
async def enter_quantity(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    db = Database(config.database_path)
    user = message.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")
    data = await state.get_data()
    min_q = data.get("min_qty", 50)
    max_q = data.get("max_qty", 50000)

    raw = (message.text or "").strip().replace(" ", "").replace(",", "")
    if not raw.isdigit():
        await message.answer(t(lang, "error_try_again"), parse_mode="HTML")
        return

    qty = int(raw)
    if qty < min_q or qty > max_q:
        await message.answer(
            t(lang, "enter_stars_amount", min=min_q, max=max_q),
            reply_markup=_cancel_kb(lang),
            parse_mode="HTML",
        )
        return

    await state.update_data(quantity=qty)
    await state.set_state(OrderFlow.confirm_order)
    await _show_order_summary(message, state, lang, config, user_id=user.id)


async def _show_order_summary(
    target: Message, state: FSMContext, lang: str, config: BotConfig, user_id: int
) -> None:
    """Calculate price and show order confirmation with balance payment option."""
    data = await state.get_data()
    service = data.get("service", "stars")
    qty = data.get("quantity", 1)
    recipient = data.get("recipient", "?")
    gift_name = data.get("gift_name", "")

    try:
        prices = await _calc_price(config, service, qty)
    except Exception:
        logger.exception("Price calculation failed")
        await target.answer(t(lang, "error_general"), parse_mode="HTML")
        return

    await state.update_data(**prices)

    db = Database(config.database_path)
    user_row = await db.get_user(user_id)
    user_balance_uzs = float(user_row.get("balance_uzs") or 0.0) if user_row else 0.0
    rate = getattr(config, "usd_to_uzs_rate", 12900.0)
    price_uzs = round(prices["price_usd"] * rate)

    price_formatted = format_currency(prices["price_usd"], lang, config)

    bal_str = format_balance(user_balance_uzs, lang, config)
    disc = prices["discount_percent"]
    disc_line = t(lang, "discount_line", discount=f"{disc:.0f}") if disc > 0 else ""

    if service == "stars":
        summary = t(lang, "order_summary_stars",
                    amount=qty, recipient=recipient,
                    price=price_formatted,
                    balance=bal_str,
                    discount_line=disc_line)
    elif service.startswith("premium"):
        dur_map = {
            "uz": {"premium_1m": "1 oy", "premium_3m": "3 oy", "premium_6m": "6 oy", "premium_12m": "12 oy"},
            "ru": {"premium_1m": "1 мес", "premium_3m": "3 мес", "premium_6m": "6 мес", "premium_12m": "12 мес"},
            "en": {"premium_1m": "1 mo", "premium_3m": "3 mo", "premium_6m": "6 mo", "premium_12m": "12 mo"},
        }
        duration = dur_map.get(lang, dur_map["uz"]).get(service, service)
        summary = t(lang, "order_summary_premium",
                    duration=duration, recipient=recipient,
                    price=price_formatted,
                    balance=bal_str,
                    discount_line=disc_line)
    else:  # gift
        amt = qty
        if not gift_name:
            for g_svc, g_qty, g_emoji, g_names in GIFTS_CATALOG:
                if g_svc == service:
                    gift_name = f"{g_emoji} {g_names.get(lang, g_names['uz'])}"
                    amt = g_qty
                    break
            if not gift_name:
                gift_name = "Gift"
        summary = t(lang, "order_summary_gift",
                    gift_name=gift_name,
                    amount=amt, recipient=recipient,
                    price=price_formatted,
                    balance=bal_str,
                    discount_line=disc_line)

    await state.set_state(OrderFlow.confirm_order)
    kb = _order_confirm_kb(
        lang,
        user_balance_uzs=user_balance_uzs,
        price_uzs=float(price_uzs),
        price_formatted=price_formatted,
    )
    try:
        await target.edit_text(summary, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await target.answer(summary, reply_markup=kb, parse_mode="HTML")


# ─── Payment from Balance ─────────────────────────────────────────────────────

@router.callback_query(F.data == "pay:balance", OrderFlow.confirm_order)
async def pay_balance(callback: CallbackQuery, state: FSMContext) -> None:
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")
    user_balance_ton = float(db_user.get("balance_ton") or 0.0)
    user_balance_uzs = float(db_user.get("balance_uzs") or 0.0)
    data = await state.get_data()

    service   = data.get("service", "stars")
    qty       = data.get("quantity", 1)
    recipient = data.get("recipient", "?")
    gift_name = data.get("gift_name", "")
    price_usd = float(data.get("price_usd", 0))
    price_ton = float(data.get("price_ton", 0))
    discount  = float(data.get("discount_percent", 0))
    rate      = getattr(config, "usd_to_uzs_rate", 12900.0)
    price_uzs = round(price_usd * rate)

    # Prioritize UZS if sufficient, else TON
    if user_balance_uzs >= price_uzs and price_uzs > 0:
        await db.update_user_balance_uzs(user.id, -price_uzs)
    elif user_balance_ton >= price_ton and price_ton > 0:
        await db.update_user_balance(user.id, -price_ton)
    else:
        bal_str = format_balance(user_balance_uzs, lang, config)
        price_str = format_currency(price_usd, lang, config)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_topup"), callback_data="balance:topup", icon_custom_emoji_id=ICONS["wallet"])],
            [
                InlineKeyboardButton(text=t(lang, "btn_pay_humo"), callback_data="pay:humo", icon_custom_emoji_id=ICONS["card"]),
                InlineKeyboardButton(text=t(lang, "btn_pay_click"), callback_data="pay:click", icon_custom_emoji_id=ICONS["card"]),
            ],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back:main", icon_custom_emoji_id=ICONS["back"])],
        ])
        await callback.message.edit_text(
            f"{tg_icon('cancel', '⚠️')} <b>Balansingizda yetarli mablag' yo'q!</b>\n\n"
            f"{tg_icon('wallet', '💰')} Sizning balansingiz: <b>{bal_str}</b>\n"
            f"{tg_icon('card', '💳')} To'lov summasi: <b>{price_str}</b>\n\n"
            f"<i>Xarid qilish uchun avval balansni to'ldiring yoki Humo / Click orqali to'lang:</i>",
            reply_markup=kb,
            parse_mode="HTML",
        )
        await callback.answer()
        return

    order_type = "stars" if service == "stars" else ("premium" if service.startswith("premium") else "gift")
    order_id = await db.create_order(
        user_id=user.id,
        username=user.username,
        order_type=order_type,
        recipient_username=recipient,
        quantity=qty,
        price_usd=price_usd,
        price_ton=price_ton,
        price_uzs=float(price_uzs),
        discount_percent=discount,
        payment_type="balance",
        payment_address="balance",
        payment_comment=f"BAL-{user.id}",
        expires_at=datetime.now() + timedelta(minutes=10),
    )
    await db.set_order_status(order_id, "paid")
    await state.clear()

    await callback.message.edit_text(t(lang, "paid_from_balance"), parse_mode="HTML")
    await callback.answer()

    # Instant fulfillment via Fragment API
    fragment = FragmentAPIService(
        api_key=config.fragment_api_key,
        wallet_mnemonic=config.fragment_wallet_mnemonic,
        api_url=config.fragment_api_url,
        api_mode=config.fragment_api_mode,
        payment_method=config.fragment_payment_method,
        cookies_base64=config.fragment_cookies_base64,
        wallet_address=config.fragment_wallet_address,
        account_index=config.fragment_account_index,
    )

    try:
        if order_type == "gift":
            from services.gift_sender import dispatch_order_gift
            desc = f"{gift_name} ({qty} Stars)" if gift_name else f"{qty} Stars Gift"
            await db.set_order_status(order_id, "processing")
            await dispatch_order_gift(callback.bot, config, order_id, user.id, user.username, recipient, desc, price_uzs)
            await callback.message.edit_text(
                f"🎉 <b>Sovg'a buyurtmangiz qabul qilindi!</b>\n\n"
                f"🧸 <b>{desc}</b> sovg'asi tez orada @{recipient} ga yetkazib beriladi!\n"
                f"💰 To'landi: <b>{int(price_uzs):,} so'm</b>",
                reply_markup=_back_kb(lang),
                parse_mode="HTML",
            )
            return

        if order_type == "premium":
            tx = await fragment.buy_premium(recipient, qty)
            desc = f"{qty} oy Premium"
        else:
            tx = await fragment.buy_stars(recipient, qty)
            desc = f"{qty} Stars"

        await db.set_order_status(order_id, "completed", fragment_tx_hash=tx)
        await callback.message.edit_text(
            t(lang, "order_completed", amount=desc, recipient=recipient),
            reply_markup=_back_kb(lang),
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.exception("Fragment instant fulfillment error: {}", exc)
        if price_uzs > 0:
            await db.update_user_balance_uzs(user.id, price_uzs)
        elif price_ton > 0:
            await db.update_user_balance(user.id, price_ton)
        await db.set_order_status(order_id, "failed", error_message=str(exc))
        await callback.message.edit_text(
            f"❌ <b>Xatolik yuz berdi:</b>\n{exc}\n\n<i>Mablag' balansingizga qaytarildi.</i>",
            reply_markup=_back_kb(lang),
            parse_mode="HTML",
        )


# ─── Payment via Humo & Click ────────────────────────────────────────────────

@router.callback_query(F.data == "pay:humo", OrderFlow.confirm_order)
async def pay_humo(callback: CallbackQuery, state: FSMContext) -> None:
    await _create_service_card_order(callback, state, "humo")


@router.callback_query(F.data == "pay:click", OrderFlow.confirm_order)
async def pay_click(callback: CallbackQuery, state: FSMContext) -> None:
    await _create_service_card_order(callback, state, "click")


async def _create_service_card_order(callback: CallbackQuery, state: FSMContext, pay_type: str) -> None:
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")
    data = await state.get_data()

    service   = data.get("service", "stars")
    qty       = data.get("quantity", 1)
    recipient = data.get("recipient", "?")
    price_usd = float(data.get("price_usd", 0))
    discount  = float(data.get("discount_percent", 0))

    rate = getattr(config, "usd_to_uzs_rate", 12900.0)
    price_uzs = float(round(price_usd * rate))

    # 30 minutes expiry
    expires_at = datetime.now() + timedelta(minutes=30)

    if service == "stars":
        order_type = "stars"
    elif service.startswith("premium"):
        order_type = "premium"
    else:
        order_type = "gift"

    if pay_type == "click":
        card_num = config.click_card_number or "8801 9102 6669 7252"
        card_holder = config.click_card_holder or "CLICK CARD"
        instr_key = "click_payment_instructions"
    else:
        card_num = config.humo_card_number or "9860 3501 4730 5402"
        card_holder = config.humo_card_holder or "HUMO CARD"
        instr_key = "humo_payment_instructions"

    order_id = await db.create_order(
        user_id=user.id,
        username=user.username,
        order_type=order_type,
        recipient_username=recipient,
        quantity=qty,
        price_usd=price_usd,
        price_ton=0.0,
        price_uzs=float(price_uzs),
        discount_percent=discount,
        payment_type=pay_type,
        payment_address=card_num,
        payment_comment=f"{pay_type.upper()}-{user.id}",
        expires_at=expires_at,
    )

    await state.update_data(order_id=order_id)
    await state.set_state(OrderFlow.waiting_payment)

    await callback.message.edit_text(
        t(lang, instr_key,
          card_number=card_num,
          card_holder=card_holder,
          amount=int(price_uzs)),
        reply_markup=_payment_kb(lang, order_id, payment_type=pay_type),
        parse_mode="HTML",
    )
    await callback.answer()

    # Notify admin with 1-click confirmation button
    await _notify_admin_new_order(callback.bot, config, order_id, user.id, user.username or "", order_type, price_uzs)


# ─── Check payment (User) ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("check:"))
async def check_payment(callback: CallbackQuery, state: FSMContext) -> None:
    order_id = int(callback.data.split(":", 1)[1])
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    db_user = await db.get_or_create_user(user.id, user.username)
    lang = db_user.get("lang", "uz")

    order = await db.get_order(order_id)
    if not order or order["user_id"] != user.id:
        await callback.answer(t(lang, "error_general"), show_alert=True)
        return

    if order["status"] == "completed":
        if order.get("order_type") == "topup":
            user_row = await db.get_user(user.id)
            amount_val = int(float(order.get("price_uzs") or 0.0))
            new_bal = int(float(user_row.get("balance_uzs") or 0.0)) if user_row else amount_val
            await callback.message.edit_text(
                t(lang, "balance_topup_uzs_completed", amount=amount_val, new_balance=new_bal),
                reply_markup=_back_kb(lang),
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                t(lang, "order_completed",
                  amount=f"{order['quantity']} {order.get('order_type', '')}",
                  recipient=order["recipient_username"]),
                reply_markup=_back_kb(lang),
                parse_mode="HTML",
            )
        await callback.answer()
        return

    if order["status"] == "failed":
        await callback.message.edit_text(
            t(lang, "order_failed", support=config.support_username or "admin"),
            reply_markup=_back_kb(lang),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Pending
    order_type_desc = f"{order.get('quantity')} Stars" if order.get('order_type') == 'stars' else f"{order.get('quantity')} {order.get('order_type')}"
    rec_desc = f" (@{order.get('recipient_username')})" if order.get('recipient_username') and order.get('recipient_username') != 'self' else ""
    check_amt = int(float(order.get("price_uzs") or 0))

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ #{order_id} Tasdiqlash", callback_data=f"admin_confirm:{order_id}", icon_custom_emoji_id=ICONS["check"])],
        [InlineKeyboardButton(text=f"❌ #{order_id} Bekor qilish", callback_data=f"admin_cancel:{order_id}", icon_custom_emoji_id=ICONS["cancel"])],
    ])
    for adm_id in config.admin_user_ids:
        try:
            await callback.bot.send_message(
                adm_id,
                f"{tg_icon('bell', '🔔')} <b>Foydalanuvchi to'lovni tekshirdi!</b>\n\n"
                f"{tg_icon('orders', '🆔')} Buyurtma: #{order_id}\n"
                f"{tg_icon('user', '👤')} Foydalanuvchi: <code>{user.id}</code> (@{user.username or 'yoq'})\n"
                f"{tg_icon('box', '📦')} Mahsulot: <b>{order_type_desc}</b>{rec_desc}\n"
                f"{tg_icon('dollar', '💵')} Summa: <b>{check_amt:,} so'm</b>\n\n"
                f"<i>Agar pul kartangizga tushgan bo'lsa, quyidagi tugmani bosib tasdiqlang:</i>",
                reply_markup=admin_kb,
                parse_mode="HTML",
            )
        except Exception:
            pass

    if user.id in config.admin_user_ids:
        test_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡️ Hoziroq tasdiqlash va Stars yuborish", callback_data=f"admin_confirm:{order_id}", icon_custom_emoji_id=ICONS["lightning"])],
            [InlineKeyboardButton(text="🔄 Qayta tekshirish", callback_data=f"check:{order_id}", icon_custom_emoji_id=ICONS["check"])],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admin_cancel:{order_id}", icon_custom_emoji_id=ICONS["cancel"])],
        ])
        await callback.message.edit_text(
            f"{tg_icon('crown', '👑')} <b>Admin sinov rejimi:</b>\n\n"
            f"{tg_icon('orders', '🆔')} Buyurtma: #{order_id}\n"
            f"{tg_icon('box', '📦')} Mahsulot: <b>{order_type_desc}</b>{rec_desc}\n"
            f"{tg_icon('dollar', '💵')} Summa: <b>{check_amt:,} so'm</b>\n\n"
            f"<i>Bank SMS xabarini kutmasdan, buyurtmani darhol bajarish uchun tugmani bosing:</i>",
            reply_markup=test_kb,
            parse_mode="HTML",
        )
        await callback.answer("👑 Admin rejimi: darhol tasdiqlashingiz mumkin!")
        return

    alert_text = (
        "⏳ To'lov tekshirilmoqda.\n\n"
        "To'lov kartaga tushishi bilan tizim avtomatik tasdiqlaydi. "
        "Yoki to'lov chekini (skrinshotini) shu chatga rasm qilib yuboring!"
    )
    await callback.answer(alert_text, show_alert=True)


@router.message(OrderFlow.waiting_payment)
async def process_user_payment_sms(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    db = Database(config.database_path)
    user = message.from_user
    if not user:
        return

    data = await state.get_data()
    order_id = data.get("order_id")
    order = await db.get_order(order_id) if order_id else None
    if not order or order["status"] != "pending":
        await state.clear()
        return

    expected_uzs = float(order.get("price_uzs") or 0.0)

    # Forward receipt to admins for manual review if user sends check screenshot/text
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ #{order_id} Tasdiqlash", callback_data=f"admin_confirm:{order_id}", icon_custom_emoji_id=ICONS["check"])],
        [InlineKeyboardButton(text=f"❌ #{order_id} Bekor qilish", callback_data=f"admin_cancel:{order_id}", icon_custom_emoji_id=ICONS["cancel"])],
    ])

    admin_caption = (
        f"{tg_icon('bell', '📸')} <b>Foydalanuvchi to'lov cheki yubordi:</b>\n\n"
        f"{tg_icon('orders', '🆔')} Buyurtma: #{order_id}\n"
        f"{tg_icon('user', '👤')} Foydalanuvchi: <code>{user.id}</code> (@{user.username or 'yoq'})\n"
        f"{tg_icon('money', '💰')} Summa: <b>{int(expected_uzs):,} so'm</b>\n"
        f"{tg_icon('box', '📦')} Turi: {order.get('order_type')}"
    )

    for admin_id in config.admin_user_ids:
        try:
            if message.photo:
                await message.bot.send_photo(
                    admin_id,
                    message.photo[-1].file_id,
                    caption=admin_caption,
                    reply_markup=admin_kb,
                    parse_mode="HTML",
                )
            elif message.document:
                await message.bot.send_document(
                    admin_id,
                    message.document.file_id,
                    caption=admin_caption,
                    reply_markup=admin_kb,
                    parse_mode="HTML",
                )
            else:
                user_text = message.text or ""
                await message.bot.send_message(
                    admin_id,
                    f"{admin_caption}\n\n💬 Xabar: <i>{user_text}</i>",
                    reply_markup=admin_kb,
                    parse_mode="HTML",
                )
        except Exception:
            pass

    await message.answer(
        "📩 <b>To'lov chekingiz adminga yuborildi.</b>\n\n"
        "To'lov kartaga tushishi bilan tizim avtomatik tarzda (yoki admin tomonidan) tasdiqlaydi. "
        "Iltimos, kuting.",
        parse_mode="HTML",
    )


# ─── Admin 1-Click Order Confirmation ─────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_confirm:"))
async def admin_confirm_payment(callback: CallbackQuery) -> None:
    config = BotConfig.load()
    user = callback.from_user
    if not user or user.id not in config.admin_user_ids:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    order_id = int(callback.data.split(":", 1)[1])
    db = Database(config.database_path)
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi!", show_alert=True)
        return

    if order["status"] in ("completed", "paid", "cancelled"):
        await callback.answer(f"Buyurtma #{order_id} allaqachon {order['status']} bo'lgan!", show_alert=True)
        return

    user_id = int(order["user_id"])
    order_type = str(order.get("order_type") or "stars")
    price_uzs = float(order.get("price_uzs") or 0.0)
    quantity = int(order.get("quantity") or 1)
    recipient = str(order.get("recipient_username") or "")
    lang = await db.get_user_lang(user_id)

    if order_type == "topup":
        await db.update_user_balance_uzs(user_id, price_uzs)
        await db.set_order_status(order_id, "completed")
        user_row = await db.get_user(user_id)
        new_bal = float(user_row.get("balance_uzs") or 0.0) if user_row else price_uzs
        try:
            await callback.bot.send_message(
                user_id,
                t(lang, "balance_topup_uzs_completed", amount=int(price_uzs), new_balance=int(new_bal)),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Foydalanuvchiga xabar yuborilmadi: {}", e)

        await callback.message.edit_text(
            f"✅ <b>Buyurtma #{order_id} admin tomonidan tasdiqlandi!</b>\n\n"
            f"👤 Foydalanuvchi: <code>{user_id}</code>\n"
            f"💰 Balansga qo'shildi: <b>{int(price_uzs):,} so'm</b>",
            parse_mode="HTML",
        )
        await callback.answer("✅ Balans to'ldirildi!")
        return

    # If order is gift, admin confirm directly marks it completed
    if order_type == "gift":
        desc = f"Gift ({quantity} Stars)"
        await db.set_order_status(order_id, "completed")
        try:
            await callback.bot.send_message(
                user_id,
                t(lang, "order_completed", amount=desc, recipient=recipient),
                parse_mode="HTML",
            )
        except Exception:
            pass

        await callback.message.edit_text(
            f"✅ <b>Sovg'a buyurtmasi #{order_id} tasdiqlandi va bajarildi!</b>\n\n"
            f"👤 Qabul qiluvchi: @{recipient}\n"
            f"🎁 Sovg'a: <b>{desc}</b>\n"
            f"💰 Summa: <b>{int(price_uzs):,} so'm</b>",
            parse_mode="HTML",
        )
        await callback.answer("✅ Sovg'a yetkazildi deb belgilandi!")
        return

    # Regular service order (stars, premium)
    await db.set_order_status(order_id, "paid")
    fragment = FragmentAPIService(
        api_key=config.fragment_api_key,
        wallet_mnemonic=config.fragment_wallet_mnemonic,
        api_url=config.fragment_api_url,
        api_mode=config.fragment_api_mode,
        payment_method=config.fragment_payment_method,
        cookies_base64=config.fragment_cookies_base64,
        wallet_address=config.fragment_wallet_address,
        account_index=config.fragment_account_index,
    )

    try:
        if order_type == "premium":
            tx = await fragment.buy_premium(recipient, quantity)
            desc = f"{quantity} oy Premium"
        else:
            tx = await fragment.buy_stars(recipient, quantity)
            desc = f"{quantity} Stars"

        await db.set_order_status(order_id, "completed", fragment_tx_hash=tx)
        try:
            await callback.bot.send_message(
                user_id,
                t(lang, "order_completed", amount=desc, recipient=recipient),
                parse_mode="HTML",
            )
        except Exception:
            pass

        await callback.message.edit_text(
            f"✅ <b>Buyurtma #{order_id} muvaffaqiyatli bajarildi!</b>\n\n"
            f"👤 Qabul qiluvchi: @{recipient}\n"
            f"📦 Mahsulot: <b>{desc}</b>\n"
            f"💰 Summa: <b>{int(price_uzs):,} so'm</b>",
            parse_mode="HTML",
        )
        await callback.answer("✅ Bajarildi!")
    except Exception as exc:
        logger.exception("Fragment error on admin confirm: {}", exc)
        await db.set_order_status(order_id, "failed", error_message=str(exc))
        await callback.answer(f"Fragment xatosi: {exc}", show_alert=True)


@router.callback_query(F.data.startswith("admin_cancel:"))
async def admin_cancel_order(callback: CallbackQuery) -> None:
    config = BotConfig.load()
    user = callback.from_user
    if not user or user.id not in config.admin_user_ids:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    order_id = int(callback.data.split(":", 1)[1])
    db = Database(config.database_path)
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi!", show_alert=True)
        return

    if order["status"] not in ("pending", "processing"):
        await callback.answer(f"Buyurtma #{order_id} allaqachon {order['status']}!", show_alert=True)
        return

    old_status = order["status"]
    payment_type = order.get("payment_type") or ""
    price_uzs = float(order.get("price_uzs") or 0.0)
    user_id = int(order["user_id"])

    # If money was already paid/deducted, refund safely to user balance
    refunded = False
    if old_status == "processing" or payment_type in ("balance", "humo", "click"):
        if price_uzs > 0:
            await db.update_user_balance_uzs(user_id, price_uzs)
            refunded = True

    await db.set_order_status(order_id, "cancelled")
    lang = await db.get_user_lang(user_id)
    refund_note = f"\n\n💰 <b>{int(price_uzs):,} so'm</b> balansingizga qaytarildi." if refunded else ""
    try:
        await callback.bot.send_message(
            user_id,
            f"❌ <b>Sizning #{order_id}-raqamli buyurtmangiz bekor qilindi.</b>{refund_note}\n\n"
            f"Savollar bo'lsa @{config.support_username or 'admin'} ga murojaat qiling.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    admin_refund_note = f" (Foydalanuvchi balansiga {int(price_uzs):,} so'm qaytarildi)" if refunded else ""
    await callback.message.edit_text(
        f"❌ <b>Buyurtma #{order_id} bekor qilindi.</b>{admin_refund_note}",
        parse_mode="HTML",
    )
    await callback.answer("Bekor qilindi!")


@router.callback_query(F.data.startswith("order_gift_done:"))
async def admin_gift_done(callback: CallbackQuery) -> None:
    config = BotConfig.load()
    user = callback.from_user
    if not user or user.id not in config.admin_user_ids:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    order_id = int(callback.data.split(":", 1)[1])
    db = Database(config.database_path)
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi!", show_alert=True)
        return

    if order["status"] == "completed":
        await callback.answer("Bu buyurtma allaqachon bajarilgan!", show_alert=True)
        return

    await db.set_order_status(order_id, "completed")
    user_id = int(order["user_id"])
    recipient = order.get("recipient_username") or ""
    qty = order.get("quantity") or 0
    price_uzs = float(order.get("price_uzs") or 0.0)
    lang = await db.get_user_lang(user_id)
    desc = f"Gift ({qty} Stars)"

    try:
        await callback.bot.send_message(
            user_id,
            t(lang, "order_completed", amount=desc, recipient=recipient),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Foydalanuvchiga xabar yuborilmadi: {}", e)

    await callback.message.edit_text(
        f"✅ <b>Sovg'a buyurtmasi #{order_id} yetkazildi va tasdiqlandi!</b>\n\n"
        f"👤 Qabul qiluvchi: @{recipient}\n"
        f"🎁 Sovg'a: <b>{desc}</b>\n"
        f"💰 Summa: <b>{int(price_uzs):,} so'm</b>",
        parse_mode="HTML",
    )
    await callback.answer("✅ Sovg'a yetkazildi deb tasdiqlandi!")

