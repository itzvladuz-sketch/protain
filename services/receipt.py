"""Digital Receipt and Transaction Formatter for completed orders."""

from __future__ import annotations

from datetime import datetime
from typing import Optional


def format_order_receipt(
    order_id: int,
    order_type: str,
    desc: str,
    recipient: str,
    price_uzs: float,
    payment_method: str = "Bot Balansi",
    lang: str = "uz",
    is_vip: bool = False,
    saved_uzs: float = 0.0,
    tx_hash: Optional[str] = None,
) -> str:
    """Return a luxury, copyable digital receipt for delivered products."""
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    if lang == "ru":
        title = "🎉 <b>ЗАКАЗ УСПЕШНО ДОСТАВЛЕН!</b>"
        rcpt = f"🧾 <b>Электронный чек #ORD-{order_id}</b>"
        p_label = "📦 <b>Услуга:</b>"
        r_label = "👤 <b>Получатель:</b>"
        pr_label = "💰 <b>Оплачено:</b>"
        pm_label = "💳 <b>Метод оплаты:</b>"
        d_label = "⚡️ <b>Доставка:</b> Мгновенно (Fragment API)"
        t_label = "📅 <b>Время:</b>"
        foot = "🌟 <i>Спасибо за покупку! При возникновении вопросов обращайтесь в поддержку.</i>"
        vip_line = f"\n⭐ <b>VIP Выгода:</b> 0% комиссии (-{int(saved_uzs):,} сум сэкономлено)" if (is_vip and saved_uzs > 0) else ""
        tx_line = f"\n🔗 <b>Транзакция:</b> <code>{tx_hash[:16]}...</code>" if tx_hash else ""
    elif lang == "en":
        title = "🎉 <b>ORDER SUCCESSFULLY DELIVERED!</b>"
        rcpt = f"🧾 <b>Digital Receipt #ORD-{order_id}</b>"
        p_label = "📦 <b>Service:</b>"
        r_label = "👤 <b>Recipient:</b>"
        pr_label = "💰 <b>Paid amount:</b>"
        pm_label = "💳 <b>Payment method:</b>"
        d_label = "⚡️ <b>Delivery:</b> Instant (Fragment API)"
        t_label = "📅 <b>Time:</b>"
        foot = "🌟 <i>Thank you for your purchase! Contact support for any inquiries.</i>"
        vip_line = f"\n⭐ <b>VIP Benefit:</b> 0% markup (-{int(saved_uzs):,} UZS saved)" if (is_vip and saved_uzs > 0) else ""
        tx_line = f"\n🔗 <b>Transaction:</b> <code>{tx_hash[:16]}...</code>" if tx_hash else ""
    else:  # uz
        title = "🎉 <b>BUYURTMA MUVAFFAQIYATLI YETKAZILDI!</b>"
        rcpt = f"🧾 <b>Elektron Chek #ORD-{order_id}</b>"
        p_label = "📦 <b>Xizmat:</b>"
        r_label = "👤 <b>Qabul qiluvchi:</b>"
        pr_label = "💰 <b>To'langan summa:</b>"
        pm_label = "💳 <b>To'lov usuli:</b>"
        d_label = "⚡️ <b>Yetkazish:</b> Avtomatik (Fragment API)"
        t_label = "📅 <b>Vaqt:</b>"
        foot = "🌟 <i>Xaridingiz uchun tashakkur! Savollar bo'lsa, qo'llab-quvvatlashga yozing.</i>"
        vip_line = f"\n⭐ <b>VIP Imtiyoz:</b> 0% komissiya (-{int(saved_uzs):,} so'm tejaldi)" if (is_vip and saved_uzs > 0) else ""
        tx_line = f"\n🔗 <b>Tranzaksiya:</b> <code>{tx_hash[:16]}...</code>" if tx_hash else ""

    lines = [
        title,
        "",
        rcpt,
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"{p_label} <b>{desc}</b>",
        f"{r_label} <b>@{recipient}</b>",
        f"{pr_label} <b>{int(price_uzs):,} so'm</b>",
        f"{pm_label} <b>{payment_method}</b>" + vip_line,
        d_label + tx_line,
        f"{t_label} <code>{now_str}</code>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        foot,
    ]
    return "\n".join(lines)
