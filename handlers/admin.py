"""Admin panel handler: stats, prices, users, orders, broadcast."""

from __future__ import annotations

import html

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
from services.ui import safe_answer, safe_edit_text

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
    waiting_give_balance_target = State()
    waiting_give_balance_amount = State()
    waiting_take_balance_target = State()
    waiting_take_balance_amount = State()
    waiting_timeout_minutes = State()


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
            InlineKeyboardButton(text="Balanslar ro'yxati", callback_data="adm:balance_list", icon_custom_emoji_id=ICONS["wallet"]),
            InlineKeyboardButton(text="Balans to'ldirish", callback_data="adm:give_balance", icon_custom_emoji_id=ICONS["money"]),
        ],
        [
            InlineKeyboardButton(text="Sovg'a so'rovlari", callback_data="adm:gift_requests", icon_custom_emoji_id=ICONS["gift"]),
            InlineKeyboardButton(text="Majburiy kanallar", callback_data="adm:channels", icon_custom_emoji_id=ICONS["megaphone"]),
        ],
        [
            InlineKeyboardButton(text="⏱ Kutish vaqti", callback_data="adm:timeout", icon_custom_emoji_id=ICONS["clock"]),
            InlineKeyboardButton(text="Xabar yuborish", callback_data="adm:broadcast", icon_custom_emoji_id=ICONS["send"]),
        ],
    ])


def _user_card_kb(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    ban_btn = (
        InlineKeyboardButton(text="Blokdan chiqarish", callback_data=f"adm:unban:{user_id}", icon_custom_emoji_id=ICONS["check"])
        if is_banned
        else InlineKeyboardButton(text="Bloklash", callback_data=f"adm:ban:{user_id}", icon_custom_emoji_id=ICONS["ban"])
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Pul qo'shish", callback_data=f"adm:add_bal:{user_id}", icon_custom_emoji_id=ICONS["wallet"]),
            InlineKeyboardButton(text="➖ Pul ayirish", callback_data=f"adm:take_bal:{user_id}", icon_custom_emoji_id=ICONS["money"]),
        ],
        [
            InlineKeyboardButton(text="🔄 Balansni 0 qilish", callback_data=f"adm:zero_bal:{user_id}", icon_custom_emoji_id=ICONS["trash"]),
            ban_btn,
        ],
        [
            InlineKeyboardButton(text="💰 Balanslar ro'yxati", callback_data="adm:balance_list", icon_custom_emoji_id=ICONS["wallet"]),
            InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"]),
        ],
    ])


def _render_user_card(user: dict, orders_count: int) -> str:
    user_id = int(user["user_id"])
    date_str = str(user.get("created_at", ""))[:10]
    banned = "Ha 🚫" if user.get("is_banned") else "Yo'q ✅"
    lang = user.get("lang", "uz")
    lang_names = {"uz": "🇺🇿 O'zbek", "ru": "🇷🇺 Rus", "en": "🇬🇧 Ingliz"}
    bal_uzs = int(user.get("balance_uzs") or 0)
    bal_ton = float(user.get("balance_ton") or 0.0)

    return (
        f'{tg_icon("user", "👤")} <b>Foydalanuvchi #{user_id}</b>\n\n'
        f'{tg_icon("user", "🆔")} ID: <code>{user_id}</code>\n'
        f'{tg_icon("user", "👤")} Username: @{user.get("username", "-")}\n'
        f'{tg_icon("globe", "🌐")} Til: {lang_names.get(lang, lang)}\n'
        f'{tg_icon("wallet", "💰")} Balans: <b>{bal_uzs:,} so\'m</b>\n'
        f'{tg_icon("diamond", "💎")} TON Balans: {bal_ton:.4f} TON\n'
        f'{tg_icon("ban", "🚫")} Bloklangan: {banned}\n'
        f'{tg_icon("calendar", "📅")} Ro\'yxatdan: {date_str}\n'
        f'{tg_icon("orders", "📋")} Buyurtmalar: {orders_count} ta'
    )


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


@router.message(Command("addmoney", "pay", "give", "balans"))
async def cmd_addmoney(message: Message) -> None:
    """Admin buyrug'i:
    /pay 50000 -> admin o'ziga
    /pay 8534196478 50000 -> ID bo'yicha
    /pay @Bash_maq 50000 -> username bo'yicha
    /give, /addmoney, /balans ham ishlaydi
    """
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    parts = (message.text or "").split()
    db = Database(config.database_path)

    if len(parts) == 2:
        # Format 1: /pay 50000 (o'ziga)
        try:
            amount = float(parts[1].replace(",", "").replace(" ", ""))
            if amount <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Noto'g'ri summa: <code>/pay 50000</code>", parse_mode="HTML")
            return
        target_user = await db.get_user(message.from_user.id)
        if not target_user:
            target_user = await db.get_or_create_user(message.from_user.id, message.from_user.username)
        target_user_id = message.from_user.id
    elif len(parts) >= 3:
        # Format 2: /pay @username 50000 yoki /pay 8534196478 50000
        target_raw = parts[1]
        try:
            amount = float(parts[2].replace(",", "").replace(" ", ""))
            if amount <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Noto'g'ri summa: <code>/pay @username 50000</code>", parse_mode="HTML")
            return

        target_user = await db.get_user_by_id_or_username(target_raw)
        if not target_user:
            await message.answer(
                f"❌ Foydalanuvchi topilmadi: <code>{target_raw}</code>\n"
                f"Foydalanuvchi botga kamida bir marta kirib /start bosgan bo'lishi kerak.",
                parse_mode="HTML",
            )
            return
        target_user_id = target_user["user_id"]
    else:
        await message.answer(
            f"ℹ️ <b>Balans to'ldirish buyruqlari:</b>\n\n"
            f"<code>/pay 50000</code> — o'zingizga pul qo'shish\n"
            f"<code>/pay @username 50000</code> — username bo'yicha pul o'tkazish\n"
            f"<code>/pay 8534196478 50000</code> — ID bo'yicha pul o'tkazish\n\n"
            f"<i>Shuningdek /give, /addmoney buyruqlari ham ishlaydi.</i>",
            parse_mode="HTML",
        )
        return

    await db.update_user_balance_uzs(target_user_id, amount)
    updated_user = await db.get_user(target_user_id)
    new_bal = int(updated_user.get("balance_uzs") or 0)

    # Foydalanuvchiga bildirishnoma yuborish (agar o'ziga tashlamayotgan bo'lsa)
    if target_user_id != message.from_user.id:
        try:
            await message.bot.send_message(
                target_user_id,
                f"{tg_icon('party', '🎉')} <b>Balansingiz to'ldirildi!</b>\n\n"
                f"Admin tomonidan hisobingizga pul o'tkazildi.\n"
                f"➕ Qo'shildi: <b>+{int(amount):,} so'm</b>\n"
                f"{tg_icon('wallet', '💰')} Yangi balansingiz: <b>{new_bal:,} so'm</b>\n\n"
                f"Xaridlaringiz uchun rahmat!",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Foydalanuvchiga bildirishnoma yuborilmadi (ID {}): {}", target_user_id, e)

    await message.answer(
        f"✅ <b>Balans muvaffaqiyatli to'ldirildi!</b>\n\n"
        f"👤 Foydalanuvchi: <code>{target_user_id}</code> (@{updated_user.get('username') or 'yoq'})\n"
        f"➕ Qo'shildi: <b>+{int(amount):,} so'm</b>\n"
        f"💰 Yangi balans: <b>{new_bal:,} so'm</b>",
        parse_mode="HTML",
    )


@router.message(Command("take", "minus", "ayir", "sub", "yech"))
async def cmd_takemoney(message: Message) -> None:
    """Admin buyrug'i:
    /take @username 20000 -> username bo'yicha pul ayirish
    /take 8534196478 20000 -> ID bo'yicha pul ayirish
    /minus, /ayir, /sub, /yech ham ishlaydi
    """
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    parts = (message.text or "").split()
    db = Database(config.database_path)

    if len(parts) < 3:
        await message.answer(
            f"ℹ️ <b>Balansdan pul ayirish buyrug'i:</b>\n\n"
            f"<code>/take @username 20000</code> — username bo'yicha ayirish\n"
            f"<code>/take 8534196478 20000</code> — ID bo'yicha ayirish\n\n"
            f"<i>Shuningdek /minus, /ayir, /yech buyruqlari ham ishlaydi.</i>",
            parse_mode="HTML",
        )
        return

    target_raw = parts[1]
    try:
        amount = float(parts[2].replace(",", "").replace(" ", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri summa: <code>/take @username 20000</code>", parse_mode="HTML")
        return

    target_user = await db.get_user_by_id_or_username(target_raw)
    if not target_user:
        await message.answer(
            f"❌ Foydalanuvchi topilmadi: <code>{target_raw}</code>\n"
            f"Foydalanuvchi botga kamida bir marta kirgan bo'lishi kerak.",
            parse_mode="HTML",
        )
        return

    target_user_id = target_user["user_id"]
    old_bal = int(target_user.get("balance_uzs") or 0)
    await db.update_user_balance_uzs(target_user_id, -amount)
    updated_user = await db.get_user(target_user_id)
    new_bal = int(updated_user.get("balance_uzs") or 0)
    actual_deducted = max(0, old_bal - new_bal)

    # Foydalanuvchiga bildirishnoma yuborish
    try:
        await message.bot.send_message(
            target_user_id,
            f"ℹ️ <b>Balansingiz o'zgartirildi</b>\n\n"
            f"Admin tomonidan balansingizdan mablag' yechildi:\n"
            f"➖ Ayirildi: <b>-{actual_deducted:,} so'm</b>\n"
            f"{tg_icon('wallet', '💰')} Yangi balansingiz: <b>{new_bal:,} so'm</b>",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Foydalanuvchiga bildirishnoma yuborilmadi (ID {}): {}", target_user_id, e)

    await message.answer(
        f"✅ <b>Balansdan pul muvaffaqiyatli ayirildi!</b>\n\n"
        f"👤 Foydalanuvchi: <code>{target_user_id}</code> (@{updated_user.get('username') or 'yoq'})\n"
        f"➖ Ayirildi: <b>-{actual_deducted:,} so'm</b>\n"
        f"💰 Avvalgi balans: <b>{old_bal:,} so'm</b>\n"
        f"💰 Yangi balans: <b>{new_bal:,} so'm</b>",
        parse_mode="HTML",
    )


@router.message(Command("zero", "clear", "nol"))
async def cmd_zeromoney(message: Message) -> None:
    """Admin buyrug'i:
    /zero @username -> bitta user balansini 0 qilish
    /zero 8534196478 -> ID bo'yicha 0 qilish
    """
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    parts = (message.text or "").split()
    db = Database(config.database_path)

    if len(parts) < 2:
        await message.answer(
            f"ℹ️ <b>Balansni 0 qilish buyrug'i:</b>\n\n"
            f"<code>/zero @username</code> — username bo'yicha 0 qilish\n"
            f"<code>/zero 8534196478</code> — ID bo'yicha 0 qilish\n\n"
            f"<i>Barcha userlarni 0 qilish uchun: <code>/resetall</code></i>",
            parse_mode="HTML",
        )
        return

    target_raw = parts[1]
    target_user = await db.get_user_by_id_or_username(target_raw)
    if not target_user:
        await message.answer(
            f"❌ Foydalanuvchi topilmadi: <code>{target_raw}</code>",
            parse_mode="HTML",
        )
        return

    target_user_id = target_user["user_id"]
    old_bal = int(target_user.get("balance_uzs") or 0)
    await db.set_user_balance_uzs(target_user_id, 0.0)

    try:
        await message.bot.send_message(
            target_user_id,
            f"ℹ️ <b>Balansingiz 0 ga tenglashtirildi.</b>\n"
            f"{tg_icon('wallet', '💰')} Yangi balansingiz: <b>0 so'm</b>",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Foydalanuvchiga bildirishnoma yuborilmadi: {}", e)

    await message.answer(
        f"✅ <b>Foydalanuvchi balansi 0 qilindi!</b>\n\n"
        f"👤 User: <code>{target_user_id}</code> (@{target_user.get('username') or 'yoq'})\n"
        f"💰 Avvalgi balans: <b>{old_bal:,} so'm</b>\n"
        f"💰 Yangi balans: <b>0 so'm</b>",
        parse_mode="HTML",
    )


@router.message(Command("resetall", "zeroall"))
async def cmd_resetall(message: Message) -> None:
    """Admin buyrug'i: Admindan boshqa barcha foydalanuvchilar balansini 0 qilish."""
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    db = Database(config.database_path)
    count = await db.reset_all_balances_except(message.from_user.id)
    await message.answer(
        f"✅ <b>Barcha foydalanuvchilar balansi 0 qilindi!</b>\n\n"
        f"🔄 Nollangan foydalanuvchilar soni: <b>{count} ta</b>\n"
        f"👑 Asosiy admin (<code>{message.from_user.id}</code>) balansi o'zgarishsiz qoldirildi.",
        parse_mode="HTML",
    )


@router.message(Command("balances", "balanslar", "users"))
async def cmd_list_balances(message: Message) -> None:
    """Admin buyrug'i: barcha foydalanuvchilar balanslarini ro'yxat ko'rinishida chiqarish."""
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    db = Database(config.database_path)
    users = await db.get_users_with_balance(limit=30)
    if not users:
        await message.answer(
            "💰 <b>Balanslar:</b>\n\nHozircha balansi mavjud bo'lgan foydalanuvchilar yo'q.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👥 Barcha userlar", callback_data="adm:balance_list_all")],
                [InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])],
            ]),
            parse_mode="HTML",
        )
        return

    total_uzs = sum(float(u.get("balance_uzs") or 0.0) for u in users)
    lines = ["💰 <b>Foydalanuvchilar balanslari:</b>\n"]
    inline_keyboard = []

    for idx, u in enumerate(users[:20], 1):
        uid = int(u["user_id"])
        uname = f"@{u['username']}" if u.get("username") else f"ID:{uid}"
        bal = int(u.get("balance_uzs") or 0)
        lines.append(f"{idx}. <b>{uname}</b> (<code>{uid}</code>) — <b>{bal:,} so'm</b>")
        btn_text = f"{idx}. {uname} — {bal:,} so'm"
        inline_keyboard.append([
            InlineKeyboardButton(text=btn_text[:35], callback_data=f"adm:view_user:{uid}")
        ])

    lines.append(f"\n📊 Ko'rsatilganlar jami: <b>{int(total_uzs):,} so'm</b> ({len(users)} ta user)")
    lines.append("\n<i>User ustiga bosib pul qo'shish, ayirish yoki 0 qilish mumkin.</i>")

    inline_keyboard.append([
        InlineKeyboardButton(text="👥 Barcha foydalanuvchilar", callback_data="adm:balance_list_all"),
    ])
    inline_keyboard.append([
        InlineKeyboardButton(text="➕ Balans to'ldirish", callback_data="adm:give_balance", icon_custom_emoji_id=ICONS["wallet"]),
        InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"]),
    ])

    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard), parse_mode="HTML")


@router.message(Command("user", "lookup"))
async def cmd_user_lookup(message: Message) -> None:
    """Admin buyrug'i: foydalanuvchi kartasini ochish."""
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("ℹ️ Misol: <code>/user @username</code> yoki <code>/user 8534196478</code>", parse_mode="HTML")
        return

    target_raw = parts[1]
    db = Database(config.database_path)
    user = await db.get_user_by_id_or_username(target_raw)
    if not user:
        await message.answer(f"❌ Foydalanuvchi topilmadi: <code>{target_raw}</code>", parse_mode="HTML")
        return

    user_id = int(user["user_id"])
    orders = await db.get_user_orders(user_id, limit=100)
    text = _render_user_card(user, len(orders))
    kb = _user_card_kb(user_id, bool(user.get("is_banned")))
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ─── Main panel callback ──────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:main")
async def admin_main(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_answer(callback)
    await state.clear()
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
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
    await safe_answer(callback)
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
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
    await safe_answer(callback)
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
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
        emoji = STATUS_EMOJIS.get(o.get("status"), "•")
        date_str = str(o.get("created_at", ""))[:16].replace("T", " ")
        price_uzs = float(o.get("price_uzs") or 0.0)
        price_disp = f"{int(price_uzs):,} so'm" if price_uzs > 0 else f"{float(o.get('price_ton',0)):.4f} TON"
        u_name = html.escape(str(o.get("username") or o.get("user_id") or "?")).lstrip("@")
        raw_rec = o.get("recipient_username")
        rec_disp = "Hisobga" if (not raw_rec or raw_rec == "self") else f"@{html.escape(raw_rec.lstrip('@'))}"
        order_type = html.escape(str(o.get("order_type") or "?").upper())
        qty = o.get("quantity", 1)
        lines.append(
            f"{tg_icon('pin', '🔖')} <b>#{o['id']}</b> {emoji} | {order_type} ({qty})\n"
            f"   {tg_icon('user', '👤')} @{u_name} → {rec_disp}\n"
            f"   💰 {price_disp} | {tg_icon('calendar', '📅')} {date_str}"
        )
        if len(lines) > 30:
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
    await safe_answer(callback)
    status = callback.data.split(":", 2)[2]
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
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
        emoji = STATUS_EMOJIS.get(o.get("status"), "•")
        date_str = str(o.get("created_at", ""))[:16].replace("T", " ")
        price_uzs = float(o.get("price_uzs") or 0.0)
        price_disp = f"{int(price_uzs):,} so'm" if price_uzs > 0 else f"{float(o.get('price_ton',0)):.4f} TON"
        u_name = html.escape(str(o.get("username") or o.get("user_id") or "?")).lstrip("@")
        raw_rec = o.get("recipient_username")
        rec_disp = "Hisobga" if (not raw_rec or raw_rec == "self") else f"@{html.escape(raw_rec.lstrip('@'))}"
        order_type = html.escape(str(o.get("order_type") or "?").upper())
        qty = o.get("quantity", 1)
        lines.append(
            f"{tg_icon('pin', '🔖')} <b>#{o['id']}</b> {emoji} | {order_type} ({qty})\n"
            f"   {tg_icon('user', '👤')} @{u_name} → {rec_disp}\n"
            f"   💰 {price_disp} | {tg_icon('calendar', '📅')} {date_str}"
        )

    text = "\n\n".join(lines)
    if len(text) > 4000:
        text = text[:3950] + "\n\n<i>... (qisqartirildi)</i>"
    await callback.message.edit_text(text, reply_markup=_admin_back_kb(), parse_mode="HTML")
    await callback.answer()


# ─── Prices ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:prices")
async def admin_prices(callback: CallbackQuery) -> None:
    await safe_answer(callback)
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Balanslar ro'yxati", callback_data="adm:balance_list", icon_custom_emoji_id=ICONS["wallet"])],
        [InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])],
    ])
    await callback.message.edit_text(
        f'{tg_icon("users", "👥")} <b>Foydalanuvchilar</b>\n\nJami: <b>{count}</b> ta\n\n'
        f"Foydalanuvchining <b>Telegram ID</b> yoki <b>@username</b>ini kiriting:\n\n"
        f"<i>Misol: <code>8534196478</code> yoki <code>@sxkmvv</code></i>",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_user_id)
async def admin_user_lookup(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    raw = (message.text or "").strip()
    db = Database(config.database_path)
    user = await db.get_user_by_id_or_username(raw)
    if not user:
        await message.answer(
            f"❌ Foydalanuvchi topilmadi: <code>{raw}</code>\n"
            f"Foydalanuvchi botdan ro'yxatdan o'tgan bo'lishi kerak. Qaytadan kiriting:",
            reply_markup=_admin_back_kb(),
            parse_mode="HTML",
        )
        return

    user_id = int(user["user_id"])
    orders = await db.get_user_orders(user_id, limit=100)
    text = _render_user_card(user, len(orders))
    kb = _user_card_kb(user_id, bool(user.get("is_banned")))

    await state.clear()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm:view_user:"))
async def admin_view_user(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    user_id = int(callback.data.split(":", 2)[2])
    db = Database(config.database_path)
    user = await db.get_user(user_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    orders = await db.get_user_orders(user_id, limit=100)
    text = _render_user_card(user, len(orders))
    kb = _user_card_kb(user_id, bool(user.get("is_banned")))
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


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
    await callback.message.edit_reply_markup(reply_markup=_user_card_kb(user_id, is_banned=True))


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
    await callback.message.edit_reply_markup(reply_markup=_user_card_kb(user_id, is_banned=False))


# ─── Balance Management (List / Give / Take / Zero) ───────────────────────────

@router.callback_query(F.data.in_({"adm:balance_list", "adm:balance_list_all"}))
async def admin_balance_list(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    db = Database(config.database_path)
    show_all = callback.data == "adm:balance_list_all"

    if show_all:
        users = await db.get_all_users_ordered(limit=30)
        title = "👥 <b>Barcha foydalanuvchilar (balans tartibida):</b>\n\n"
    else:
        users = await db.get_users_with_balance(limit=30)
        title = "💰 <b>Balansida mablag' bor foydalanuvchilar:</b>\n\n"

    if not users:
        text = title + "<i>Hozircha balansi mavjud bo'lgan foydalanuvchilar yo'q.</i>"
        toggle_btn = (
            InlineKeyboardButton(text="💰 Faqat balansi borlar", callback_data="adm:balance_list")
            if show_all
            else InlineKeyboardButton(text="👥 Barcha foydalanuvchilar", callback_data="adm:balance_list_all")
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [toggle_btn],
            [InlineKeyboardButton(text="➕ Balans to'ldirish", callback_data="adm:give_balance", icon_custom_emoji_id=ICONS["wallet"])],
            [InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])],
        ])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        return

    total_uzs = sum(float(u.get("balance_uzs") or 0.0) for u in users)
    lines = [title]
    inline_keyboard = []

    for idx, u in enumerate(users[:20], 1):
        uid = int(u["user_id"])
        uname = f"@{u['username']}" if u.get("username") else f"ID:{uid}"
        bal = int(u.get("balance_uzs") or 0)
        lines.append(f"{idx}. <b>{uname}</b> (<code>{uid}</code>) — <b>{bal:,} so'm</b>")
        btn_text = f"{idx}. {uname} — {bal:,} so'm"
        inline_keyboard.append([
            InlineKeyboardButton(text=btn_text[:35], callback_data=f"adm:view_user:{uid}")
        ])

    lines.append(f"\n📊 Ko'rsatilganlar jami: <b>{int(total_uzs):,} so'm</b> ({len(users)} ta user)")
    lines.append("\n<i>Foydalanuvchi ustiga bosib pul qo'shish, ayirish yoki 0 qilish mumkin.</i>")

    toggle_btn = (
        InlineKeyboardButton(text="💰 Faqat balansi borlar", callback_data="adm:balance_list")
        if show_all
        else InlineKeyboardButton(text="👥 Barcha foydalanuvchilar", callback_data="adm:balance_list_all")
    )
    inline_keyboard.append([toggle_btn])
    inline_keyboard.append([
        InlineKeyboardButton(text="➕ Balans to'ldirish", callback_data="adm:give_balance", icon_custom_emoji_id=ICONS["wallet"]),
        InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"]),
    ])

    await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "adm:give_balance")
async def admin_give_balance_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    await state.set_state(AdminStates.waiting_give_balance_target)
    await callback.message.edit_text(
        f'{tg_icon("wallet", "💳")} <b>Foydalanuvchi balansini to\'ldirish</b>\n\n'
        f"Foydalanuvchining <b>Telegram ID</b> yoki <b>@username</b>ini kiriting:\n\n"
        f"<i>Misol: <code>8534196478</code> yoki <code>@sxkmvv</code></i>",
        reply_markup=_admin_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_give_balance_target)
async def admin_process_give_balance_target(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    raw = (message.text or "").strip()
    db = Database(config.database_path)
    user = await db.get_user_by_id_or_username(raw)
    if not user:
        await message.answer(
            f"❌ Foydalanuvchi topilmadi: <code>{raw}</code>\n"
            f"Foydalanuvchi botga kamida bir marta kirgan bo'lishi kerak. Qaytadan ID yoki @username kiriting:",
            reply_markup=_admin_back_kb(),
            parse_mode="HTML",
        )
        return

    user_id = int(user["user_id"])
    await state.update_data(target_user_id=user_id, target_username=user.get("username"))
    await state.set_state(AdminStates.waiting_give_balance_amount)
    bal_uzs = int(user.get("balance_uzs") or 0)
    await message.answer(
        f'{tg_icon("user", "👤")} Foydalanuvchi: <b>@{user.get("username") or "yo\'q"}</b> (<code>{user_id}</code>)\n'
        f'{tg_icon("wallet", "💰")} Hozirgi balansi: <b>{bal_uzs:,} so\'m</b>\n\n'
        f'Qo\'shmoqchi bo\'lgan <b>summani (so\'mda)</b> kiriting:\n'
        f'<i>Misol: <code>50000</code> yoki <code>100000</code></i>',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Bekor qilish", callback_data="adm:main", icon_custom_emoji_id=ICONS["cancel"])]
        ]),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm:add_bal:"))
async def admin_add_balance_btn(callback: CallbackQuery, state: FSMContext) -> None:
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    user_id = int(callback.data.split(":", 2)[2])
    db = Database(config.database_path)
    user = await db.get_user(user_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    await state.update_data(target_user_id=user_id, target_username=user.get("username"))
    await state.set_state(AdminStates.waiting_give_balance_amount)
    bal_uzs = int(user.get("balance_uzs") or 0)
    await callback.message.edit_text(
        f'{tg_icon("wallet", "💰")} <b>Balans to\'ldirish</b>\n\n'
        f'👤 Foydalanuvchi: <b>@{user.get("username") or "yo\'q"}</b> (<code>{user_id}</code>)\n'
        f'💰 Hozirgi balans: <b>{bal_uzs:,} so\'m</b>\n\n'
        f'Qo\'shiladigan <b>summani (so\'mda)</b> kiriting:\n'
        f'<i>Masalan: <code>50000</code> yoki <code>100000</code></i>',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Bekor qilish", callback_data=f"adm:view_user:{user_id}", icon_custom_emoji_id=ICONS["cancel"])]
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_give_balance_amount)
async def admin_process_give_balance_amount(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    raw = (message.text or "").strip().replace(" ", "").replace(",", "")
    try:
        amount = float(raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri summa! Musbat raqam kiriting (masalan: <code>50000</code>):", parse_mode="HTML")
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        await state.clear()
        await message.answer("❌ Foydalanuvchi topilmadi. Qaytadan urinib ko'ring.", reply_markup=_admin_back_kb())
        return

    db = Database(config.database_path)
    await db.update_user_balance_uzs(target_user_id, amount)
    user = await db.get_user(target_user_id)
    new_bal = int(user.get("balance_uzs") or 0)
    await state.clear()

    # Foydalanuvchiga xabar yuborish
    try:
        await message.bot.send_message(
            target_user_id,
            f"{tg_icon('party', '🎉')} <b>Balansingiz to'ldirildi!</b>\n\n"
            f"Admin tomonidan hisobingizga pul o'tkazildi.\n"
            f"➕ Qo'shildi: <b>+{int(amount):,} so'm</b>\n"
            f"{tg_icon('wallet', '💰')} Yangi balansingiz: <b>{new_bal:,} so'm</b>\n\n"
            f"Xaridlaringiz uchun rahmat!",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Foydalanuvchiga bildirishnoma yuborilmadi (ID {}): {}", target_user_id, e)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 User kartasi", callback_data=f"adm:view_user:{target_user_id}")],
        [InlineKeyboardButton(text="💰 Balanslar ro'yxati", callback_data="adm:balance_list")],
        [InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])],
    ])
    await message.answer(
        f"{tg_icon('check', '✅')} <b>Balans muvaffaqiyatli to'ldirildi!</b>\n\n"
        f"👤 Foydalanuvchi: <code>{target_user_id}</code> (@{user.get('username') or 'yoq'})\n"
        f"➕ Qo'shildi: <b>+{int(amount):,} so'm</b>\n"
        f"💰 Yangi balans: <b>{new_bal:,} so'm</b>",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm:take_bal:"))
async def admin_take_balance_btn(callback: CallbackQuery, state: FSMContext) -> None:
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    user_id = int(callback.data.split(":", 2)[2])
    db = Database(config.database_path)
    user = await db.get_user(user_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    await state.update_data(target_user_id=user_id, target_username=user.get("username"))
    await state.set_state(AdminStates.waiting_take_balance_amount)
    bal_uzs = int(user.get("balance_uzs") or 0)
    await callback.message.edit_text(
        f'{tg_icon("money", "💸")} <b>Balansdan pul ayirish (yechish)</b>\n\n'
        f'👤 Foydalanuvchi: <b>@{user.get("username") or "yo\'q"}</b> (<code>{user_id}</code>)\n'
        f'💰 Hozirgi balans: <b>{bal_uzs:,} so\'m</b>\n\n'
        f'Ayirmoqchi bo\'lgan <b>summani (so\'mda)</b> kiriting:\n'
        f'<i>Masalan: <code>20000</code> yoki <code>50000</code></i>',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Bekor qilish", callback_data=f"adm:view_user:{user_id}", icon_custom_emoji_id=ICONS["cancel"])]
        ]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_take_balance_amount)
async def admin_process_take_balance_amount(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    raw = (message.text or "").strip().replace(" ", "").replace(",", "")
    try:
        amount = float(raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri summa! Musbat raqam kiriting (masalan: <code>20000</code>):", parse_mode="HTML")
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        await state.clear()
        await message.answer("❌ Foydalanuvchi topilmadi. Qaytadan urinib ko'ring.", reply_markup=_admin_back_kb())
        return

    db = Database(config.database_path)
    old_user = await db.get_user(target_user_id)
    old_bal = int(old_user.get("balance_uzs") or 0) if old_user else 0

    await db.update_user_balance_uzs(target_user_id, -amount)
    user = await db.get_user(target_user_id)
    new_bal = int(user.get("balance_uzs") or 0) if user else 0
    actual_deducted = max(0, old_bal - new_bal)
    await state.clear()

    # Foydalanuvchiga xabar yuborish
    try:
        await message.bot.send_message(
            target_user_id,
            f"ℹ️ <b>Balansingiz o'zgartirildi</b>\n\n"
            f"Admin tomonidan balansingizdan mablag' yechildi:\n"
            f"➖ Ayirildi: <b>-{actual_deducted:,} so'm</b>\n"
            f"{tg_icon('wallet', '💰')} Yangi balansingiz: <b>{new_bal:,} so'm</b>",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Foydalanuvchiga bildirishnoma yuborilmadi (ID {}): {}", target_user_id, e)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 User kartasi", callback_data=f"adm:view_user:{target_user_id}")],
        [InlineKeyboardButton(text="💰 Balanslar ro'yxati", callback_data="adm:balance_list")],
        [InlineKeyboardButton(text="Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])],
    ])
    await message.answer(
        f"{tg_icon('check', '✅')} <b>Balansdan pul muvaffaqiyatli ayirildi!</b>\n\n"
        f"👤 Foydalanuvchi: <code>{target_user_id}</code> (@{user.get('username') or 'yoq'})\n"
        f"➖ Yechildi: <b>-{actual_deducted:,} so'm</b>\n"
        f"💰 Avvalgi balans: <b>{old_bal:,} so'm</b>\n"
        f"💰 Yangi balans: <b>{new_bal:,} so'm</b>",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm:zero_bal:"))
async def admin_zero_balance_btn(callback: CallbackQuery) -> None:
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await callback.answer()
        return

    user_id = int(callback.data.split(":", 2)[2])
    db = Database(config.database_path)
    old_user = await db.get_user(user_id)
    old_bal = int(old_user.get("balance_uzs") or 0) if old_user else 0

    await db.set_user_balance_uzs(user_id, 0.0)
    await callback.answer("✅ Foydalanuvchi balansi 0 qilindi!", show_alert=True)

    # Foydalanuvchiga bildirishnoma yuborish
    try:
        await callback.bot.send_message(
            user_id,
            f"ℹ️ <b>Balansingiz 0 ga tenglashtirildi.</b>\n"
            f"{tg_icon('wallet', '💰')} Yangi balansingiz: <b>0 so'm</b>",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Foydalanuvchiga bildirishnoma yuborilmadi: {}", e)

    user = await db.get_user(user_id)
    if not user:
        return
    orders = await db.get_user_orders(user_id, limit=100)
    text = _render_user_card(user, len(orders))
    kb = _user_card_kb(user_id, bool(user.get("is_banned")))
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


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
    try:
        from services.subscription import invalidate_subscription_cache
        invalidate_subscription_cache()
    except Exception:
        pass

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
    try:
        from services.subscription import invalidate_subscription_cache
        invalidate_subscription_cache()
    except Exception:
        pass
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

# ─── Order timeout setting ───────────────────────────────────────────────────

@router.callback_query(F.data == "adm:timeout")
async def admin_timeout_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_answer(callback)
    await state.clear()
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        return

    db = Database(config.database_path)
    cur_timeout = await db.get_order_timeout_minutes(default=5)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏱ 3 daqiqa", callback_data="adm:set_timeout:3"),
            InlineKeyboardButton(text="⏱ 5 daqiqa (standart)", callback_data="adm:set_timeout:5"),
        ],
        [
            InlineKeyboardButton(text="⏱ 10 daqiqa", callback_data="adm:set_timeout:10"),
            InlineKeyboardButton(text="⏱ 15 daqiqa", callback_data="adm:set_timeout:15"),
        ],
        [
            InlineKeyboardButton(text="⏱ 30 daqiqa", callback_data="adm:set_timeout:30"),
            InlineKeyboardButton(text="✏️ Boshqa vaqt", callback_data="adm:set_timeout:custom"),
        ],
        [InlineKeyboardButton(text="◀️ Admin Panel", callback_data="adm:main", icon_custom_emoji_id=ICONS["back"])],
    ])

    await safe_edit_text(
        callback.message,
        f"{tg_icon('clock', '⏱')} <b>To'lov kutish vaqti (taymaut)</b>\n\n"
        f"Mijoz karta orqali to'lov qilish uchun beriladigan vaqt.\n"
        f"Ushbu vaqt o'tgach, to'lanmagan buyurtma avtomatik bekor bo'ladi.\n\n"
        f"⚙️ Hozirgi kutish vaqti: <b>{cur_timeout} daqiqa</b>\n\n"
        f"<i>O'zgartirish uchun quyidagi tugmalardan birini tanlang yoki o'zingiz kiriting:</i>",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm:set_timeout:"))
async def admin_set_timeout(callback: CallbackQuery, state: FSMContext) -> None:
    val = callback.data.split(":", 2)[2]
    config = BotConfig.load()
    if not callback.from_user or not await _is_admin(callback.from_user.id, config):
        await safe_answer(callback)
        return

    db = Database(config.database_path)

    if val == "custom":
        await safe_answer(callback)
        await state.set_state(AdminStates.waiting_timeout_minutes)
        await safe_edit_text(
            callback.message,
            f"{tg_icon('pencil', '✏️')} Yangi kutish vaqtini <b>daqiqalarda</b> yozib yuboring (masalan: <code>7</code> yoki <code>20</code>):\n\n"
            f"<i>Bekor qilish uchun /cancel deb yozing.</i>",
            reply_markup=_admin_back_kb(),
            parse_mode="HTML",
        )
        return

    try:
        minutes = int(val)
    except ValueError:
        await safe_answer(callback, "Noto'g'ri qiymat!", show_alert=True)
        return

    await db.set_order_timeout_minutes(minutes)
    await safe_answer(callback, f"✅ Kutish vaqti {minutes} daqiqaga o'rnatildi!", show_alert=True)
    await admin_timeout_menu(callback, state)


@router.message(AdminStates.waiting_timeout_minutes)
async def admin_save_custom_timeout(message: Message, state: FSMContext) -> None:
    config = BotConfig.load()
    if not message.from_user or not await _is_admin(message.from_user.id, config):
        return

    text = (message.text or "").strip()
    if text.startswith("/cancel"):
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=_admin_main_kb())
        return

    try:
        minutes = int(text)
        if minutes < 1 or minutes > 1440:
            raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri son! Iltimos, 1 dan 1440 gacha butun son kiriting:")
        return

    db = Database(config.database_path)
    await db.set_order_timeout_minutes(minutes)
    await state.clear()
    await message.answer(
        f"✅ <b>To'lov kutish vaqti muvaffaqiyatli saqlandi:</b> {minutes} daqiqa!",
        reply_markup=_admin_main_kb(),
        parse_mode="HTML",
    )

