"""Admin panel handler: stats, prices, users, orders, broadcast."""

from __future__ import annotations

import asyncio
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
)
from dotenv import load_dotenv
from loguru import logger

from locales import t
from services.config import BotConfig
from services.db import Database, STATUS_EMOJIS
from services.icons import ICONS, tg_icon

load_dotenv()
router = Router()

# Map service keys to translation keys
SERVICE_NAME_KEYS = {
    "stars":        "admin_service_name_stars",
    "premium_1m":   "admin_service_name_premium_1m",
    "premium_3m":   "admin_service_name_premium_3m",
    "premium_6m":   "admin_service_name_premium_6m",
    "premium_12m":  "admin_service_name_premium_12m",
    "gift_50":      "admin_service_name_gift_50",
    "gift_100":     "admin_service_name_gift_100",
    "gift_150":     "admin_service_name_gift_150",
    "gift_250":     "admin_service_name_gift_250",
    "gift_500":     "admin_service_name_gift_500",
    "gift_1000":    "admin_service_name_gift_1000",
}


class AdminStates(StatesGroup):
    waiting_broadcast_text    = State()
    confirm_broadcast         = State()
    waiting_user_id           = State()
    waiting_new_price         = State()
    waiting_new_commission    = State()
    waiting_new_discount      = State()
    waiting_channel_id        = State()
    waiting_channel_title     = State()
    waiting_channel_url       = State()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Statistika",   callback_data="adm:stats", icon_custom_emoji_id=ICONS["chart"]),
            InlineKeyboardButton(text="Buyurtmalar",  callback_data="adm:orders", icon_custom_emoji_id=ICONS["orders"]),
        ],
        [
            InlineKeyboardButton(text="Narxlar",      callback_data="adm:prices", icon_custom_emoji_id=ICONS["money"]),
            InlineKeyboardButton(text="Foydalanuvchilar", callback_data="adm:users", icon_custom_emoji_id=ICONS["users"]),
        ],
        [
            InlineKeyboardButton(text="Majburiy kanallar", callback_data="adm:channels", icon_custom_emoji_id=ICONS["megaphone"]),
            InlineKeyboardButton(text="Sovg'a so'rovlari", callback_data="adm:gift_requests", icon_custom_emoji_id=ICONS["gift"]),
        ],
        [
            InlineKeyboardButton(text="Xabar yuborish", callback_data="adm:broadcast", icon_custom_emoji_id=ICONS["send"]),
        ],
    ])


def _admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])]
    ])


async def _is_admin(user_id: int, config: Optional[BotConfig] = None) -> bool:
    if not config:
        config = BotConfig.load()
    if user_id in config.admin_user_ids:
        return True
    db = Database(config.database_path)
    db_admin = await db.get_setting("admin_id")
    if db_admin and str(user_id) == str(db_admin):
        return True
    if not config.admin_user_ids and not db_admin:
        await db.set_setting("admin_id", str(user_id))
        logger.info("Admin aniqlanmagan edi. User {} birinchi admin sifatida belgilandi.", user_id)
        return True
    return False


async def show_admin_panel(target: Message, config: Optional[BotConfig] = None) -> None:
    """Show main admin panel. Can be called from /admin command or callback."""
    if not config:
        config = BotConfig.load()
    await target.answer(
        f'{tg_icon("crown", "👑")} <b>Admin Panel</b>\n\nXizmat turini tanlang:',
        reply_markup=_admin_main_kb(),
        parse_mode="HTML",
    )


# ─── /admin command ───────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return
    await show_admin_panel(message, config)


# ─── Main panel callback ──────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:main")
async def admin_main(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return
    await callback.message.edit_text(
        f'{tg_icon("crown", "👑")} <b>Admin Panel</b>\n\nXizmat turini tanlang:',
        reply_markup=_admin_main_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Stats ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:stats")
async def admin_stats(callback: CallbackQuery) -> None:
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    stats = await db.get_stats()

    text = (
        f'{tg_icon("chart", "📊")} <b>Statistika</b>\n\n'
        f'{tg_icon("users", "👥")} Jami foydalanuvchilar: <b>{stats["users"]}</b>\n'
        f'{tg_icon("orders", "📋")} Jami buyurtmalar: <b>{stats["orders"]}</b>\n'
        f'{tg_icon("check", "✅")} Bajarilgan: <b>{stats["completed"]}</b>\n'
        f'{tg_icon("cancel", "❌")} Xatolik: <b>{stats["failed"]}</b>\n'
        f'{tg_icon("clock", "⏳")} Kutilmoqda: <b>{stats["pending"]}</b>\n\n'
        f'{tg_icon("calendar", "📅")} <b>Bugun:</b>\n'
        f'  • Buyurtmalar: <b>{stats["today_orders"]}</b>\n'
        f'  • Daromad: <b>${stats["today_revenue"]:.2f}</b>\n\n'
        f'{tg_icon("money", "💰")} <b>Jami daromad: ${stats["total_revenue"]:.2f}</b>'
    )
    await callback.message.edit_text(text, reply_markup=_admin_back_kb(), parse_mode="HTML")
    await callback.answer()


# ─── Orders ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:orders")
async def admin_orders(callback: CallbackQuery) -> None:
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    orders = await db.get_all_orders(limit=20)

    if not orders:
        await callback.message.edit_text(
            f"{tg_icon('orders', '📋')} <b>Buyurtmalar yo'q</b>",
            reply_markup=_admin_back_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    lines = [f"{tg_icon('orders', '📋')} <b>So'nggi {len(orders)} ta buyurtma:</b>\n"]
    for o in orders:
        emoji = STATUS_EMOJIS.get(o["status"], "•")
        date_str = str(o.get("created_at", ""))[:16].replace("T", " ")
        lines.append(
            f"{tg_icon('pin', '🔖')} <b>#{o['id']}</b> {emoji} | {o.get('order_type','?').upper()}\n"
            f"   {tg_icon('user', '👤')} @{o.get('username','?')} → @{o.get('recipient_username','?')}\n"
            f"   {tg_icon('diamond', '💎')} {float(o.get('price_ton',0)):.4f} TON | {tg_icon('calendar', '📅')} {date_str}"
        )
        if len(lines) > 30:  # Telegram message limit safety
            break

    # Add filter buttons
    filter_buttons = [
        [
            InlineKeyboardButton(text="Kutilmoqda", callback_data="adm:orders:pending", icon_custom_emoji_id=ICONS["clock"]),
            InlineKeyboardButton(text="Bajarilgan", callback_data="adm:orders:completed", icon_custom_emoji_id=ICONS["check"]),
        ],
        [
            InlineKeyboardButton(text="Xatolik", callback_data="adm:orders:failed", icon_custom_emoji_id=ICONS["cancel"]),
            InlineKeyboardButton(text="Hammasi", callback_data="adm:orders", icon_custom_emoji_id=ICONS["orders"]),
        ],
        [InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=filter_buttons)

    text = "\n\n".join(lines)
    if len(text) > 4000:
        text = text[:3950] + "\n\n<i>... (qisqartirildi)</i>"

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("adm:orders:"))
async def admin_orders_filtered(callback: CallbackQuery) -> None:
    status = callback.data.split(":", 2)[2]
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    orders = await db.get_all_orders(limit=15, status=status)
    status_labels = {"pending": "Kutilmoqda", "completed": "Bajarilgan", "failed": "Xatolik"}
    label = status_labels.get(status, status)

    if not orders:
        await callback.message.edit_text(
            f"{tg_icon('orders', '📋')} <b>{label}</b> — buyurtmalar yo'q",
            reply_markup=_admin_back_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    lines = [f"{tg_icon('orders', '📋')} <b>{label}</b> ({len(orders)} ta):\n"]
    for o in orders:
        emoji = STATUS_EMOJIS.get(o["status"], "•")
        date_str = str(o.get("created_at", ""))[:16].replace("T", " ")
        lines.append(
            f"{tg_icon('pin', '🔖')} <b>#{o['id']}</b> {emoji} | {o.get('order_type','?').upper()}\n"
            f"   {tg_icon('user', '👤')} @{o.get('username','?')} → @{o.get('recipient_username','?')}\n"
            f"   {tg_icon('diamond', '💎')} {float(o.get('price_ton',0)):.4f} TON | {tg_icon('calendar', '📅')} {date_str}"
        )

    text = "\n\n".join(lines)
    if len(text) > 4000:
        text = text[:3950] + "\n\n<i>... (qisqartirildi)</i>"
    await callback.message.edit_text(text, reply_markup=_admin_back_kb(), parse_mode="HTML")
    await callback.answer()


# ─── Prices ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:prices")
async def admin_prices(callback: CallbackQuery) -> None:
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    prices = await db.get_all_prices()

    buttons = []
    for p in prices:
        svc = p["service"]
        name_key = SERVICE_NAME_KEYS.get(svc, svc)
        name = t("uz", name_key)
        icon_id = ICONS["star"] if "star" in svc else (ICONS["diamond"] if "premium" in svc else ICONS["gift"])
        disc = f" (-{p['discount_percent']:.0f}%)" if float(p.get("discount_percent", 0)) > 0 else ""
        state_prefix = "" if p["is_active"] else "[O'chirilgan] "
        buttons.append([InlineKeyboardButton(
            text=f"{state_prefix}{name} — ${p['base_price_usd']}{disc}",
            callback_data=f"adm:price:{svc}",
            icon_custom_emoji_id=icon_id,
        )])

    buttons.append([InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        f'{tg_icon("money", "💰")} <b>Narxlarni boshqarish</b>\n\nO\'zgartirish uchun xizmatni tanlang:',
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:price:"))
async def admin_price_detail(callback: CallbackQuery) -> None:
    svc = callback.data.split(":", 2)[2]
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    p = await db.get_price(svc)
    if not p:
        await callback.answer("Topilmadi")
        return

    name_key = SERVICE_NAME_KEYS.get(svc, svc)
    name = t("uz", name_key)
    active_str = "Ha" if p["is_active"] else "Yo'q"
    disc = float(p.get("discount_percent", 0))
    disc_str = f"{disc:.1f}%" if disc > 0 else "Yo'q"

    text = (
        f'{tg_icon("pin", "📌")} <b>{name}</b>\n\n'
        f'{tg_icon("dollar", "💵")} Asosiy narx: <b>${p["base_price_usd"]}</b>\n'
        f'{tg_icon("chart", "📊")} Komissiya: <b>{p["commission_percent"]}%</b>\n'
        f'{tg_icon("party", "🎉")} Chegirma: <b>{disc_str}</b>\n'
        f'{tg_icon("check", "✅")} Faol: <b>{active_str}</b>'
    )

    toggle_label = "O'chirish" if p["is_active"] else "Yoqish"
    toggle_icon = ICONS["cancel"] if p["is_active"] else ICONS["check"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Narx", callback_data=f"adm:editprice:{svc}", icon_custom_emoji_id=ICONS["dollar"]),
            InlineKeyboardButton(text="Komissiya", callback_data=f"adm:editcomm:{svc}", icon_custom_emoji_id=ICONS["chart"]),
        ],
        [
            InlineKeyboardButton(text="Chegirma", callback_data=f"adm:editdisc:{svc}", icon_custom_emoji_id=ICONS["party"]),
            InlineKeyboardButton(text=toggle_label, callback_data=f"adm:toggle:{svc}", icon_custom_emoji_id=toggle_icon),
        ],
        [InlineKeyboardButton(text="Narxlar", callback_data="adm:prices", icon_custom_emoji_id=ICONS["back"])],
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("adm:toggle:"))
async def admin_toggle_price(callback: CallbackQuery) -> None:
    svc = callback.data.split(":", 2)[2]
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    p = await db.get_price(svc)
    if not p:
        await callback.answer("Topilmadi")
        return

    new_state = not bool(p["is_active"])
    await db.set_price(svc, is_active=new_state)
    status = "✅ Yoqildi" if new_state else "❌ O'chirildi"
    await callback.answer(status)
    # Refresh
    await admin_price_detail(callback)


@router.callback_query(F.data.startswith("adm:editprice:"))
async def admin_edit_price_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    svc = callback.data.split(":", 2)[2]
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    p = await db.get_price(svc)
    name = t("uz", SERVICE_NAME_KEYS.get(svc, svc))

    await state.update_data(edit_service=svc, edit_field="base_price_usd")
    await state.set_state(AdminStates.waiting_new_price)
    await callback.message.edit_text(
        f'{tg_icon("dollar", "💵")} <b>{name}</b> uchun yangi narxni kiriting:\n\n'
        f'Joriy narx: <b>${p["base_price_usd"]}</b>\n\n'
        f'<i>Misol: 0.015</i>',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Bekor", callback_data=f"adm:price:{svc}", icon_custom_emoji_id=ICONS["cancel"])]
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_new_price)
async def admin_set_price(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    data = await state.get_data()
    svc = data.get("edit_service")
    if not svc:
        return

    try:
        val = float((message.text or "").replace(",", "."))
        if val <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri qiymat. Raqam kiriting:", parse_mode="HTML")
        return

    db = Database(config.database_path)
    await db.set_price(svc, base_price_usd=val)
    await state.clear()
    name = t("uz", SERVICE_NAME_KEYS.get(svc, svc))
    await message.answer(f"{tg_icon('check', '✅')} <b>{name}</b> narxi <b>${val}</b> ga o'zgartirildi!", parse_mode="HTML",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text="Narxlar", callback_data="adm:prices", icon_custom_emoji_id=ICONS["back"])]
                         ]))


@router.callback_query(F.data.startswith("adm:editcomm:"))
async def admin_edit_commission_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    svc = callback.data.split(":", 2)[2]
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    p = await db.get_price(svc)
    name = t("uz", SERVICE_NAME_KEYS.get(svc, svc))

    await state.update_data(edit_service=svc)
    await state.set_state(AdminStates.waiting_new_commission)
    await callback.message.edit_text(
        f'{tg_icon("chart", "📊")} <b>{name}</b> uchun komissiyani kiriting (%):\n\n'
        f'Joriy: <b>{p["commission_percent"]}%</b>\n\n<i>Misol: 5</i>',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Bekor", callback_data=f"adm:price:{svc}", icon_custom_emoji_id=ICONS["cancel"])]
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_new_commission)
async def admin_set_commission(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    data = await state.get_data()
    svc = data.get("edit_service")

    try:
        val = float((message.text or "").replace(",", "."))
        if val < 0 or val > 100:
            raise ValueError
    except ValueError:
        await message.answer("❌ 0-100 orasida raqam kiriting:")
        return

    db = Database(config.database_path)
    await db.set_price(svc, commission_percent=val)
    await state.clear()
    name = t("uz", SERVICE_NAME_KEYS.get(svc, svc))
    await message.answer(f"{tg_icon('check', '✅')} <b>{name}</b> komissiyasi <b>{val}%</b> ga o'zgartirildi!", parse_mode="HTML",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text="Narxlar", callback_data="adm:prices", icon_custom_emoji_id=ICONS["back"])]
                         ]))


@router.callback_query(F.data.startswith("adm:editdisc:"))
async def admin_edit_discount_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    svc = callback.data.split(":", 2)[2]
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    p = await db.get_price(svc)
    name = t("uz", SERVICE_NAME_KEYS.get(svc, svc))

    await state.update_data(edit_service=svc)
    await state.set_state(AdminStates.waiting_new_discount)
    await callback.message.edit_text(
        f'{tg_icon("party", "🎉")} <b>{name}</b> uchun chegirmani kiriting (%):\n\n'
        f'Joriy: <b>{p["discount_percent"]}%</b>\n\n<i>0 = chegirma yo\'q</i>',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Bekor", callback_data=f"adm:price:{svc}", icon_custom_emoji_id=ICONS["cancel"])]
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_new_discount)
async def admin_set_discount(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    data = await state.get_data()
    svc = data.get("edit_service")

    try:
        val = float((message.text or "").replace(",", "."))
        if val < 0 or val > 100:
            raise ValueError
    except ValueError:
        await message.answer("❌ 0-100 orasida raqam kiriting:")
        return

    db = Database(config.database_path)
    await db.set_price(svc, discount_percent=val)
    await state.clear()
    name = t("uz", SERVICE_NAME_KEYS.get(svc, svc))
    disc_str = f"{val}%" if val > 0 else "yo'q"
    await message.answer(f"{tg_icon('check', '✅')} <b>{name}</b> chegirmasi <b>{disc_str}</b> ga o'zgartirildi!", parse_mode="HTML",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text="Narxlar", callback_data="adm:prices", icon_custom_emoji_id=ICONS["back"])]
                         ]))


# ─── Users ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:users")
async def admin_users(callback: CallbackQuery, state: FSMContext) -> None:
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    count = await db.get_user_count()

    await state.set_state(AdminStates.waiting_user_id)
    await callback.message.edit_text(
        f'{tg_icon("users", "👥")} <b>Foydalanuvchilar</b>\n\nJami: <b>{count}</b> ta\n\n'
        f"Foydalanuvchi <b>Telegram ID</b>sini kiriting:",
        reply_markup=_admin_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_user_id)
async def admin_user_lookup(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    raw = (message.text or "").strip()
    try:
        user_id = int(raw)
    except ValueError:
        await message.answer("❌ Raqam kiriting (foydalanuvchi ID si):")
        return

    db = Database(config.database_path)
    user = await db.get_user(user_id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi.", parse_mode="HTML")
        return

    orders = await db.get_user_orders(user_id, limit=100)
    orders_count = len(orders)
    date_str = str(user.get("created_at", ""))[:10]
    banned = "Ha" if user.get("is_banned") else "Yo'q"
    lang = user.get("lang", "uz")
    lang_names = {"uz": "🇺🇿 O'zbek", "ru": "🇷🇺 Rus", "en": "🇬🇧 Ingliz"}

    text = (
        f'{tg_icon("user", "👤")} <b>Foydalanuvchi #{user_id}</b>\n\n'
        f'{tg_icon("user", "🆔")} ID: <code>{user_id}</code>\n'
        f'{tg_icon("user", "👤")} Username: @{user.get("username", "-")}\n'
        f'{tg_icon("globe", "🌐")} Til: {lang_names.get(lang, lang)}\n'
        f'{tg_icon("diamond", "💎")} Balans: {float(user.get("balance_ton", 0)):.4f} TON\n'
        f'{tg_icon("ban", "🚫")} Bloklangan: {banned}\n'
        f'{tg_icon("calendar", "📅")} Ro\'yxatdan: {date_str}\n'
        f'{tg_icon("orders", "📋")} Buyurtmalar: {orders_count} ta'
    )

    ban_btn = (
        InlineKeyboardButton(text="Blokdan chiqarish", callback_data=f"adm:unban:{user_id}", icon_custom_emoji_id=ICONS["check"])
        if user.get("is_banned")
        else InlineKeyboardButton(text="Bloklash", callback_data=f"adm:ban:{user_id}", icon_custom_emoji_id=ICONS["ban"])
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [ban_btn],
        [InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])],
    ])

    await state.clear()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm:ban:"))
async def admin_ban_user(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split(":", 2)[2])
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    await db.ban_user(user_id)
    await callback.answer("🚫 Foydalanuvchi bloklandi.")
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Blokdan chiqarish", callback_data=f"adm:unban:{user_id}", icon_custom_emoji_id=ICONS["check"])],
            [InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])],
        ])
    )


@router.callback_query(F.data.startswith("adm:unban:"))
async def admin_unban_user(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split(":", 2)[2])
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    await db.unban_user(user_id)
    await callback.answer("✅ Blokdan chiqarildi.")
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Bloklash", callback_data=f"adm:ban:{user_id}", icon_custom_emoji_id=ICONS["ban"])],
            [InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])],
        ])
    )


# ─── Broadcast ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    count = await db.get_user_count()

    await state.set_state(AdminStates.waiting_broadcast_text)
    await callback.message.edit_text(
        f'{tg_icon("megaphone", "📢")} <b>Xabar yuborish</b>\n\n'
        f"Barcha <b>{count}</b> ta foydalanuvchiga yuboriladigan xabarni yozing:\n\n"
        f"<i>HTML formatlash qo'llab-quvvatlanadi:\n"
        f"&lt;b&gt;qalin&lt;/b&gt;, &lt;i&gt;kursiv&lt;/i&gt;, &lt;code&gt;kod&lt;/code&gt;</i>",
        reply_markup=_admin_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_text)
async def admin_broadcast_text(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    broadcast_text = message.text or message.caption or ""
    if not broadcast_text:
        await message.answer("❌ Xabar matni bo'sh. Qayta kiriting:")
        return

    db = Database(config.database_path)
    count = await db.get_user_count()

    await state.update_data(broadcast_text=broadcast_text)
    await state.set_state(AdminStates.confirm_broadcast)

    preview = broadcast_text[:200] + ("..." if len(broadcast_text) > 200 else "")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Yuborish", callback_data="adm:broadcast:confirm", icon_custom_emoji_id=ICONS["send"]),
            InlineKeyboardButton(text="Bekor", callback_data="adm:main", icon_custom_emoji_id=ICONS["cancel"]),
        ]
    ])
    await message.answer(
        f'{tg_icon("megaphone", "📢")} <b>Xabarni tasdiqlang</b>\n\n'
        f"<b>{count}</b> ta foydalanuvchiga yuboriladi:\n\n"
        f"━━━━━━━━━━━━━\n{preview}\n━━━━━━━━━━━━━",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm:broadcast:confirm", AdminStates.confirm_broadcast)
async def admin_broadcast_send(callback: CallbackQuery, state: FSMContext) -> None:
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")
    if not broadcast_text:
        await callback.answer("❌ Xabar yo'q")
        return

    await state.clear()
    db = Database(config.database_path)
    users = await db.get_all_users()

    await callback.message.edit_text(
        f'{tg_icon("clock", "⏳")} <b>Yuborilmoqda...</b>\n0 / {len(users)}',
        parse_mode="HTML",
    )

    success = 0
    fail = 0
    bot = callback.bot

    for i, user in enumerate(users):
        try:
            await bot.send_message(
                user["user_id"],
                broadcast_text,
                parse_mode="HTML",
            )
            success += 1
        except Exception:
            fail += 1

        # Update progress every 20 messages
        if (i + 1) % 20 == 0 or i + 1 == len(users):
            try:
                await callback.message.edit_text(
                    f'{tg_icon("clock", "⏳")} <b>Yuborilmoqda...</b>\n{i+1} / {len(users)}',
                    parse_mode="HTML",
                )
            except Exception:
                pass
        await asyncio.sleep(0.05)  # avoid flood

    await db.log_broadcast(callback.from_user.id, broadcast_text, success, fail)

    await callback.message.edit_text(
        f'{tg_icon("check", "✅")} <b>Xabar yuborildi!</b>\n\n'
        f'{tg_icon("send", "📤")} Muvaffaqiyatli: <b>{success}</b>\n'
        f'{tg_icon("cancel", "❌")} Xatolik: <b>{fail}</b>',
        reply_markup=_admin_back_kb(),
        parse_mode="HTML",
    )


# ─── Channels Management ──────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:channels")
async def adm_channels_list(callback: CallbackQuery) -> None:
    config = BotConfig.load()
    if not await _is_admin(callback.from_user.id, config):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    db = Database(config.database_path)
    channels = await db.get_channels()

    buttons = []
    if not channels:
        text = f"{tg_icon('megaphone', '📢')} <b>Majburiy kanallar yo'q.</b>\n\nFoydalanuvchilar to'g'ridan-to'g'ri botdan foydalanishmoqda."
    else:
        text = f"{tg_icon('megaphone', '📢')} <b>Majburiy kanallar ro'yxati ({len(channels)} ta):</b>\n\n"
        for i, ch in enumerate(channels, 1):
            text += f"{i}. <b>{ch['title']}</b> (<code>{ch['channel_id']}</code>)\n🔗 {ch['url']}\n\n"
            buttons.append([
                InlineKeyboardButton(text=f"{ch['title']} ni o'chirish", callback_data=f"del_ch:{ch['channel_id']}", icon_custom_emoji_id=ICONS["trash"])
            ])

    buttons.append([InlineKeyboardButton(text="Kanal qo'shish", callback_data="adm:add_channel", icon_custom_emoji_id=ICONS["plus"])])
    buttons.append([InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "adm:add_channel")
async def adm_add_channel_start(callback: CallbackQuery, state: FSMContext) -> None:
    config = BotConfig.load()
    if not await _is_admin(callback.from_user.id, config):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_channel_id)
    await callback.message.edit_text(
        f"{tg_icon('megaphone', '📢')} <b>Kanal ID yoki @username'ini kiriting:</b>\n\n"
        "Masalan: <code>@meningkanalim</code> yoki <code>-1001234567890</code>\n\n"
        "<i>Eslatma: Bot ushbu kanalda ADMIN bo'lishi kerak!</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Bekor qilish", callback_data="adm:channels", icon_custom_emoji_id=ICONS["cancel"])]
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_channel_id)
async def adm_process_channel_id(message: Message, state: FSMContext) -> None:
    ch_id = (message.text or "").strip()
    if not ch_id:
        return
    await state.update_data(channel_id=ch_id)
    await state.set_state(AdminStates.waiting_channel_title)
    await message.answer(
        f"{tg_icon('memo', '📝')} <b>Kanal nomini kiriting:</b>\n\nMasalan: <code>Rasmiy Kanal</code>",
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_channel_title)
async def adm_process_channel_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        return
    await state.update_data(title=title)
    await state.set_state(AdminStates.waiting_channel_url)
    await message.answer(
        f"{tg_icon('link', '🔗')} <b>Kanal havolasini (link) kiriting:</b>\n\nMasalan: <code>https://t.me/meningkanalim</code>",
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_channel_url)
async def adm_process_channel_url(message: Message, state: FSMContext) -> None:
    url = (message.text or "").strip()
    data = await state.get_data()
    ch_id = data.get("channel_id")
    title = data.get("title")
    await state.clear()

    config = BotConfig.load()
    db = Database(config.database_path)
    await db.add_channel(ch_id, title, url)

    await message.answer(
        f"{tg_icon('check', '✅')} <b>Kanal muvaffaqiyatli qo'shildi!</b>\n\n"
        f"{tg_icon('megaphone', '📢')} Nomi: <b>{title}</b>\n"
        f"{tg_icon('user', '🆔')} ID: <code>{ch_id}</code>\n"
        f"{tg_icon('link', '🔗')} Havola: {url}",
        reply_markup=_admin_back_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("del_ch:"))
async def adm_delete_channel(callback: CallbackQuery) -> None:
    ch_id = callback.data.split(":", 1)[1]
    config = BotConfig.load()
    if not await _is_admin(callback.from_user.id, config):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    db = Database(config.database_path)
    await db.delete_channel(ch_id)
    await callback.answer("✅ Kanal o'chirildi!", show_alert=True)
    await adm_channels_list(callback)


# ─── Gift Requests Management ─────────────────────────────────────────────────

@router.callback_query(F.data == "adm:gift_requests")
async def adm_gift_requests(callback: CallbackQuery) -> None:
    config = BotConfig.load()
    if not await _is_admin(callback.from_user.id, config):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    db = Database(config.database_path)
    requests = await db.get_gift_requests(limit=10)

    if not requests:
        text = f"{tg_icon('gift', '🎁')} <b>Sovg'a so'rovlari hozircha yo'q.</b>"
        kb = _admin_back_kb()
    else:
        text = f"{tg_icon('gift', '🎁')} <b>So'nggi sovg'a so'rovlari ({len(requests)} ta):</b>\n\n"
        buttons = []
        for req in requests:
            status_emoji = "⏳" if req["status"] == "pending" else "✅"
            text += (
                f"#{req['id']} {status_emoji} <b>@{req['recipient_username']}</b>\n"
                f"👤 Foydalanuvchi: <code>{req['user_id']}</code> (@{req.get('username') or 'yoq'})\n"
                f"🧸 Sovg'a: <b>{req['gift_name']}</b> ({req['stars_spent']}⭐)\n"
                f"📅 Sana: {req['created_at']}\n\n"
            )
            if req["status"] == "pending":
                buttons.append([
                    InlineKeyboardButton(
                        text=f"#{req['id']} - Yuborildi deb tasdiqlash",
                        callback_data=f"gift_done:{req['id']}",
                        icon_custom_emoji_id=ICONS["check"]
                    )
                ])
        buttons.append([InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("gift_done:"))
async def adm_gift_mark_done(callback: CallbackQuery) -> None:
    req_id = int(callback.data.split(":", 1)[1])
    config = BotConfig.load()
    if not await _is_admin(callback.from_user.id, config):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    db = Database(config.database_path)
    req = await db.get_gift_request(req_id)
    if not req:
        await callback.answer("So'rov topilmadi!", show_alert=True)
        return

    await db.set_gift_request_status(req_id, "completed")
    user_id = int(req["user_id"])
    recipient = req["recipient_username"]
    gift_name = req["gift_name"]

    try:
        await callback.bot.send_message(
            user_id,
            f"{tg_icon('party', '🎉')} <b>Sovg'angiz yetkazib berildi!</b>\n\n"
            f"@{recipient} akkauntiga <b>{gift_name}</b> muvaffaqiyatli topshirildi!\n"
            f"Biz bilan qolganingiz uchun rahmat! {tg_icon('star', '⭐')}",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Foydalanuvchiga xabar yuborilmadi: {}", e)

    await callback.message.edit_text(
        f"{tg_icon('check', '✅')} <b>Sovg'a so'rovi #{req_id} muvaffaqiyatli bajarildi!</b>\n\n"
        f"🎯 Qabul qiluvchi: @{recipient}\n"
        f"🧸 Sovg'a: {gift_name}",
        reply_markup=_admin_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer("✅ Bajarildi!")

