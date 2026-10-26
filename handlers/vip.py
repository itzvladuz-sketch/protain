"""VIP Optom Tarif (Club/Reseller Pass) handlers.
Allows users to buy 1-day, 7-day, and 15-day VIP subscriptions for 0% commission wholesale pricing.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from locales import t
from services.config import BotConfig
from services.db import Database
from services.icons import ICONS, tg_icon
from services.ui import safe_answer, safe_edit_text

router = Router()


def _vip_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu:vip", icon_custom_emoji_id=ICONS["back"])]
    ])


@router.callback_query(F.data == "menu:vip")
async def vip_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_answer(callback)
    await state.clear()
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    if not user:
        return

    vip_info = await db.get_user_vip_info(user.id)
    plans = await db.get_vip_plans()

    if vip_info["is_vip"]:
        # User is already active VIP
        text = (
            f"{tg_icon('star', '⭐')} <b>Sizning VIP Optom Tarifingiz FAOL!</b>\n\n"
            f"📅 <b>Amal qilish muddati:</b> <code>{vip_info['vip_until']}</code> gacha\n"
            f"⏱ <b>Qolgan vaqt:</b> <b>{vip_info['days_left']} kun, {vip_info['hours_left']} soat</b>\n\n"
            f"🌟 <b>Sizning VIP imtiyozlaringiz:</b>\n"
            f"• Barcha Telegram Stars <b>0% komissiyada (o'z tannarxida)</b>!\n"
            f"• Reseller narxlari — xohlagancha hajmda arzon xarid qiling!\n"
            f"• Har bir xaridingizda <b>toza foyda</b> ko'rasiz.\n\n"
            f"<i>Obunani muddatidan oldin uzaytirishingiz ham mumkin (kunlar qo'shiladi).</i>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Stars xarid qilish (0%)", callback_data="menu:stars", icon_custom_emoji_id=ICONS["star"])],
            [InlineKeyboardButton(text="🔄 Obunani uzaytirish", callback_data="vip:extend", icon_custom_emoji_id=ICONS["star"])],
            [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back:main", icon_custom_emoji_id=ICONS["back"])],
        ])
        await safe_edit_text(callback.message, text, reply_markup=kb, parse_mode="HTML")
        return

    # User is not VIP
    await _show_vip_plans(callback.message, plans)


@router.callback_query(F.data == "vip:extend")
async def vip_extend(callback: CallbackQuery) -> None:
    await safe_answer(callback)
    config = BotConfig.load()
    db = Database(config.database_path)
    plans = await db.get_vip_plans()
    await _show_vip_plans(callback.message, plans, is_extend=True)


async def _show_vip_plans(target: Message, plans: dict, is_extend: bool = False) -> None:
    p1 = plans["vip_1d"]
    p7 = plans["vip_7d"]
    p15 = plans["vip_15d"]

    title = "🔄 <b>VIP Obunani Uzaytirish</b>" if is_extend else f"{tg_icon('star', '⭐')} <b>VIP Optom Tarif — Starsni Tannarxida Oling!</b>"

    text = (
        f"{title}\n\n"
        f"VIP tarif orqali Telegram Stars va boshqa xizmatlarni <b>0% komissiya bilan</b>, rasmiy Fragment tannarxida olasiz!\n\n"
        f"📊 <b>Narxlar solishtiruvi:</b>\n"
        f"• Oddiy foydalanuvchiga: <code>50 Stars = 10,499 so'm</code>\n"
        f"• ⭐ Premium a'zolariga: <b>50 Stars = 9,675 so'm</b> (~193.5 so'mdan)\n\n"
        f"💡 <i>Atigi 600-1000 ta Stars olganingizdayoq VIP pass puli o'zini to'liq oqlaydi va siz toza foydadasiz!</i>\n\n"
        f"Quyidagi qulay tariflardan birini tanlang:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"⚡ 1 kunlik — {int(p1['price_uzs']):,} so'm",
            callback_data="vip_plan:vip_1d",
            icon_custom_emoji_id=ICONS["star"]
        )],
        [InlineKeyboardButton(
            text=f"📅 7 kunlik — {int(p7['price_uzs']):,} so'm (65% chegirma)",
            callback_data="vip_plan:vip_7d",
            icon_custom_emoji_id=ICONS["diamond"]
        )],
        [InlineKeyboardButton(
            text=f"⭐ 15 kunlik — {int(p15['price_uzs']):,} so'm (70% super)",
            callback_data="vip_plan:vip_15d",
            icon_custom_emoji_id=ICONS["star"]
        )],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back:main", icon_custom_emoji_id=ICONS["back"])],
    ])

    await safe_edit_text(target, text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("vip_plan:"))
async def vip_plan_selected(callback: CallbackQuery) -> None:
    await safe_answer(callback)
    plan_key = callback.data.split(":", 1)[1]
    config = BotConfig.load()
    db = Database(config.database_path)
    plans = await db.get_vip_plans()
    plan = plans.get(plan_key)
    if not plan:
        await callback.answer("Tarif topilmadi!", show_alert=True)
        return

    user = callback.from_user
    db_user = await db.get_user(user.id)
    user_bal_uzs = float(db_user.get("balance_uzs") or 0.0) if db_user else 0.0
    price_uzs = plan["price_uzs"]

    text = (
        f"{tg_icon('star', '⭐')} <b>{plan['name']}</b>\n\n"
        f"💰 <b>Tarif narxi:</b> <code>{int(price_uzs):,} so'm</code>\n"
        f"⏱ <b>Amal qilish muddati:</b> <b>{plan['days']} kun</b> ({plan['badge']})\n"
        f"🎁 <b>Imtiyoz:</b> Barcha Telegram Stars 0% komissiyada (tannarxida)!\n"
        f"📝 <i>{plan['benefit']}</i>\n\n"
        f"💳 Sizning bot balansingiz: <b>{int(user_bal_uzs):,} so'm</b>\n\n"
        f"To'lov turini tanlang:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"👛 Balansdan to'lash ({int(price_uzs):,} so'm)",
            callback_data=f"vip_pay:balance:{plan_key}",
            icon_custom_emoji_id=ICONS["wallet"]
        )],
        [InlineKeyboardButton(
            text="💳 Humo orqali to'lash",
            callback_data=f"vip_pay:humo:{plan_key}",
            icon_custom_emoji_id=ICONS["card"]
        )],
        [InlineKeyboardButton(
            text="📲 Click orqali to'lash",
            callback_data=f"vip_pay:click:{plan_key}",
            icon_custom_emoji_id=ICONS["card"]
        )],
        [InlineKeyboardButton(text="🔙 Tariflarga qaytish", callback_data="menu:vip", icon_custom_emoji_id=ICONS["back"])],
    ])

    await safe_edit_text(callback.message, text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("vip_pay:balance:"))
async def vip_pay_from_balance(callback: CallbackQuery) -> None:
    await safe_answer(callback)
    plan_key = callback.data.split(":", 2)[2]
    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    plans = await db.get_vip_plans()
    plan = plans.get(plan_key)
    if not plan:
        await callback.answer("Tarif topilmadi!", show_alert=True)
        return

    price_uzs = plan["price_uzs"]
    user_db = await db.get_user(user.id)
    cur_bal = float(user_db.get("balance_uzs") or 0.0) if user_db else 0.0

    if cur_bal < price_uzs:
        await safe_edit_text(
            callback.message,
            f"{tg_icon('cancel', '⚠️')} <b>Balansingizda yetarli mablag' mavjud emas!</b>\n\n"
            f"💰 Sizning balansingiz: <b>{int(cur_bal):,} so'm</b>\n"
            f"📌 Tarif narxi: <b>{int(price_uzs):,} so'm</b>\n\n"
            f"Iltimos, avval balansingizni to'ldiring yoki to'g'ridan-to'g'ri karta orqali to'lang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Balansni to'ldirish", callback_data="balance:topup", icon_custom_emoji_id=ICONS["plus"])],
                [InlineKeyboardButton(text="💳 Humo orqali to'lash", callback_data=f"vip_pay:humo:{plan_key}", icon_custom_emoji_id=ICONS["card"])],
                [InlineKeyboardButton(text="📲 Click orqali to'lash", callback_data=f"vip_pay:click:{plan_key}", icon_custom_emoji_id=ICONS["card"])],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu:vip", icon_custom_emoji_id=ICONS["back"])],
            ]),
            parse_mode="HTML",
        )
        return

    # Atomic deduction
    deducted = await db.deduct_user_balance_uzs(user.id, price_uzs)
    if not deducted:
        await callback.answer("Balansingizda yetarli mablag' qolmagan!", show_alert=True)
        return

    # Activate VIP
    days = plan["days"]
    vip_exp = await db.set_user_vip(user.id, days)

    # Record completed order & transaction
    order_id = await db.create_order(
        user_id=user.id,
        username=user.username,
        order_type=plan_key,
        recipient_username=user.username or "self",
        quantity=days,
        price_usd=plan["price_usd"],
        price_uzs=price_uzs,
        price_ton=0.0,
        payment_type="balance",
        payment_address="balance",
        payment_comment=f"VIP-{plan_key}-{user.id}",
        expires_at=datetime.now() + timedelta(days=days),
    )
    await db.set_order_status(order_id, "completed")

    await db.record_transaction(
        user_id=user.id,
        tx_type="vip_purchase",
        amount_uzs=price_uzs,
        old_balance_uzs=cur_bal,
        new_balance_uzs=cur_bal - price_uzs,
        order_id=order_id,
        comment=f"{plan['name']} faollashtirildi (Balansdan)",
    )

    text = (
        f"🎉 <b>TABRIKLAYMIZ! VIP Optom Tarif FAOL!</b>\n\n"
        f"⭐ Tarif: <b>{plan['name']}</b>\n"
        f"📅 Amal qilish muddati: <b>{vip_exp[:16]}</b> gacha\n"
        f"💰 Yechildi: <b>{int(price_uzs):,} so'm</b>\n\n"
        f"🌟 <i>Endi botdagi barcha Stars siz uchun 0% komissiyada (o'z tannarxida) beriladi. Hoziroq xarid qilib foydani his eting!</i>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Stars xarid qilish (0%)", callback_data="menu:stars", icon_custom_emoji_id=ICONS["star"])],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back:main", icon_custom_emoji_id=ICONS["back"])],
    ])

    await safe_edit_text(callback.message, text, reply_markup=kb, parse_mode="HTML")

    # Notify admins
    for adm_id in config.admin_user_ids:
        try:
            await callback.bot.send_message(
                adm_id,
                f"👑 <b>Yangi VIP obuna xarid qilindi!</b>\n\n"
                f"👤 Foydalanuvchi: @{user.username or 'yoq'} (<code>{user.id}</code>)\n"
                f"⚡ Tarif: <b>{plan['name']}</b>\n"
                f"💵 Summa: <b>{int(price_uzs):,} so'm</b> (Balansdan)\n"
                f"📅 Tugash vaqti: <b>{vip_exp[:16]}</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("vip_pay:humo:") | F.data.startswith("vip_pay:click:"))
async def vip_pay_card(callback: CallbackQuery) -> None:
    await safe_answer(callback)
    parts = callback.data.split(":")
    pay_type = parts[1]
    plan_key = parts[2]

    config = BotConfig.load()
    db = Database(config.database_path)
    user = callback.from_user
    plans = await db.get_vip_plans()
    plan = plans.get(plan_key)
    if not plan:
        await callback.answer("Tarif topilmadi!", show_alert=True)
        return

    price_uzs = plan["price_uzs"]
    timeout_min = await db.get_order_timeout_minutes()
    expires_at = datetime.now() + timedelta(minutes=timeout_min)

    card_num = getattr(config, f"{pay_type}_card_number", "") or "9860350147305402"
    card_holder = getattr(config, f"{pay_type}_card_holder", "") or "Stars Shop"

    order_id = await db.create_order(
        user_id=user.id,
        username=user.username,
        order_type=plan_key,
        recipient_username=user.username or "self",
        quantity=plan["days"],
        price_usd=plan["price_usd"],
        price_ton=0.0,
        price_uzs=price_uzs,
        discount_percent=0.0,
        payment_type=pay_type,
        payment_address=card_num,
        payment_comment=f"VIP-{plan_key}-{user.id}",
        expires_at=expires_at,
    )

    pay_name = "Humo" if pay_type == "humo" else "Click"
    text = (
        f"{tg_icon('card', '💳')} <b>{pay_name} orqali to'lov</b>\n\n"
        f"⭐ Tarif: <b>{plan['name']}</b> ({plan['days']} kun)\n"
        f"💰 To'lov summasi: <b>{int(price_uzs):,} so'm</b>\n\n"
        f"💳 Karta raqami: <code>{card_num}</code>\n"
        f"👤 Karta egasi: <b>{card_holder}</b>\n\n"
        f"⏱ <b>To'lovni amalga oshirish vaqti: {timeout_min} daqiqa</b>\n\n"
        f"<i>To'lov amalga oshirilgach, tizim avtomatik ravishda VIP obunangizni faollashtiradi!</i>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"order_cancel:{order_id}", icon_custom_emoji_id=ICONS["cancel"])]
    ])

    await safe_edit_text(callback.message, text, reply_markup=kb, parse_mode="HTML")
