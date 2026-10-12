"""Uzbek localization dictionary - Short, clean and crisp."""

TEXTS: dict = {
    # Til tanlash
    "lang_select": "🌐 <b>Tilni tanlang | Выберите язык | Select language:</b>",

    # Asosiy menyu
    "welcome": (
        "👋 Assalomu alaykum, <b>{name}</b>!\n\n"
        "Quyidagi xizmatlardan birini tanlang:"
    ),
    "main_menu": (
        "👋 <b>Asosiy menyu</b>\n\n"
        "Quyidagi xizmatlardan birini tanlang:"
    ),

    # Tugmalar
    "btn_stars":    "⭐ Stars",
    "btn_premium":  "💎 Premium",
    "btn_gift":     "🎁 Sovg'alar (Gifts)",
    "btn_balance":  "💰 Balans",
    "btn_referral": "👥 Referal (+2⭐)",
    "btn_orders":   "📋 Buyurtmalarim",
    "btn_help":     "Yordam",
    "btn_language": "🌐 Tilni o'zgartirish",
    "btn_myself":   "🟢 O'zimga",
    "btn_back":     "◀️ Orqaga",
    "btn_cancel":   "❌ Bekor qilish",
    "btn_pay_ton":  "💎 TON bilan to'lash",
    "btn_pay_humo": "💳 Humo (so'm)",
    "btn_check_payment": "🔍 Tekshirish",

    # Stars
    "stars_menu": (
        "⭐ <b>Telegram Stars</b>\n\n"
        "👤 Kimga olamiz? Username kiriting yoki <b>«O'zimga»</b> tugmasini bosing:"
    ),
    "enter_recipient": (
        "👤 <b>Kimga olamiz?</b>\n"
        "Username kiriting yoki <b>«O'zimga»</b> bosing:"
    ),
    "enter_stars_amount": (
        "⭐ <b>Stars miqdorini kiriting:</b>\n"
        "Min: <b>{min}</b> | Max: <b>{max}</b>"
    ),
    "select_stars_amount": (
        "⭐ <b>Telegram Stars</b>\n\n"
        "👤 Qabul qiluvchi: <b>@{recipient}</b>\n\n"
        "Kerakli miqdorni tanlang yoki <b>«✏️ Boshqa miqdor»</b> tugmasini bosing:"
    ),
    "no_username_set": "⚠️ Sizda @username yo'q. Qabul qiluvchi username'ini yozing:",
    "checking_username": "🔍 Tekshirilmoqda...",
    "username_invalid": "❌ Username topilmadi. Qayta kiriting:",

    # Buyurtma
    "order_summary_stars": (
        "📋 <b>Buyurtma:</b>\n\n"
        "⭐ <b>{amount} Stars</b> ➔ @{recipient}\n"
        "💰 Narxi: <b>{price}</b>\n"
        "{discount_line}"
    ),
    "order_summary_premium": (
        "📋 <b>Buyurtma:</b>\n\n"
        "👑 <b>Premium ({duration})</b> ➔ @{recipient}\n"
        "💰 Narxi: <b>{price}</b>\n"
        "{discount_line}"
    ),
    "order_summary_gift": (
        "📋 <b>Buyurtma:</b>\n\n"
        "🎁 <b>{gift_name} ({amount} Stars)</b> ➔ @{recipient}\n"
        "💰 Narxi: <b>{price}</b>\n"
        "{discount_line}"
    ),
    "discount_line": "🎉 Chegirma: <b>-{discount}%</b>\n",

    # Premium
    "premium_menu": (
        "👑 <b>Telegram Premium</b>\n\n"
        "Muddati tanlang:"
    ),

    # Gift
    "gift_menu": (
        "🎁 <b>Telegram Gift</b>\n\n"
        "Sovg'ani tanlang:"
    ),

    # To'lov
    "humo_payment_instructions": (
        "💳 <b>Humo to'lov:</b>\n\n"
        "💳 Karta:\n<code>{card_number}</code>\n"
        "👤 Egasi: <b>{card_holder}</b>\n\n"
        "💰 To'lov summasi:\n<code>{amount:,}</code> so'm\n\n"
        "⏱ To'lov muddati: <b>5 daqiqa</b>\n\n"
        "⚠️ <b>DIQQAT:</b> To'lov avtomatik tarzda 1-2 soniyada tasdiqlanishi uchun aynan <code>{amount:,}</code> so'm o'tkazing!"
    ),
    "payment_not_found": "⏳ To'lov hali topilmadi. Pul o'tkazgan bo'lsangiz, 1-2 daqiqa kuting.",
    "payment_found": "✅ To'lov qabul qilindi!",
    "order_completed": (
        "🎉 <b>Bajarildi!</b>\n\n"
        "✅ <b>{amount}</b> ➔ @{recipient} ga yetkazildi."
    ),
    "order_failed": "❌ Xatolik yuz berdi. @{support} ga murojaat qiling.",
    "order_expired": "⏱ Buyurtma #{id} muddati tugadi (to'lov qilinmadi).",

    # Balans
    "balance_info": (
        "💰 <b>Sizning balansingiz:</b> <b>{balance}</b>\n\n"
        "Balansni to'ldirish uchun quyidagi tugmani bosing:"
    ),
    "btn_topup": "➕ To'ldirish",
    "btn_pay_humo": "💳 Humo orqali to'lash",
    "btn_pay_balance": "💰 Balansdan to'lash",
    "balance_topup_menu": "💳 <b>Balansni to'ldirish (Humo):</b>\n\nSummani tanlang yoki so'mda yozing (masalan: 50000):",
    "balance_topup_min_error": "⚠️ Minimal summa: {min:,} so'm",
    "balance_topup_uzs_completed": (
        "🎉 <b>Balans to'ldirildi!</b>\n\n"
        "+<b>{amount:,} so'm</b> hisobingizga qo'shildi.\n"
        "Joriy balans: <b>{new_balance:,} so'm</b>"
    ),
    "paid_from_balance": "✅ Balansdan to'landi! Buyurtma bajarilmoqda...",
    "insufficient_balance": "⚠️ Balansda mablag' yetarli emas.",
    "paid_from_balance": "✅ Balansdan to'landi! Buyurtma bajarilmoqda...",
    "insufficient_balance": "⚠️ Balansda mablag' yetarli emas.",

    # Yordam
    "help_text": (
        "🆘 <b>Yordam</b>\n\n"
        "👨‍💻 Aloqa: @{support}\n"
        "⚡️ Xaridlar to'lovdan so'ng 1-3 daqiqada yetkaziladi."
    ),

    # Buyurtmalar tarixi
    "my_orders": "📋 <b>Buyurtmalaringiz:</b>",
    "no_orders": "📭 Buyurtmalar yo'q.",
    "order_item": "#{id} | {type} ➔ @{recipient} | {amount} | {status_emoji} {status}",

    "status_pending":    "Kutilmoqda",
    "status_paid":       "To'langan",
    "status_processing": "Bajarilmoqda",
    "status_completed":  "Bajarildi",
    "status_failed":     "Xatolik",
    "status_cancelled":  "Bekor",

    "type_stars":   "⭐ Stars",
    "type_premium": "👑 Premium",
    "type_gift":    "🎁 Gift",

    "language_changed": "✅ Til o'zgartirildi!",
    "error_general": "❌ Xatolik. Qaytadan urinib ko'ring.",
    "error_try_again": "❌ Qayta urinib ko'ring.",
    "error_banned": "🚫 Siz bloklangansiz. @{support}",

    # Admin panel
    "admin_service_name_stars":      "⭐ Stars ($ / dona)",
    "admin_service_name_premium_1m": "👑 Premium 1 oy",
    "admin_service_name_premium_3m": "👑 Premium 3 oy",
    "admin_service_name_premium_6m": "👑 Premium 6 oy",
    "admin_service_name_premium_12m":"👑 Premium 12 oy",
    "admin_service_name_gift_50":    "🎁 Gift 50 Stars",
    "admin_service_name_gift_100":   "🎁 Gift 100 Stars",
    "admin_service_name_gift_150":   "🎁 Gift 150 Stars",
    "admin_service_name_gift_250":   "🎁 Gift 250 Stars",
    "admin_service_name_gift_1000":  "🎁 Gift 1000 Stars",

    "admin_new_humo_order": (
        "🔔 <b>Yangi Humo to'lov buyurtmasi!</b>\n\n"
        "🆔 Buyurtma: #{order_id}\n"
        "👤 Foydalanuvchi: @{username} (ID: <code>{user_id}</code>)\n"
        "📦 Turi: <b>{order_type}</b>\n"
        "💰 Summa: <b>{price_uzs:,} so'm</b>\n"
        "⏱ Qabul qilish: 5 daqiqa ichida"
    ),
    "admin_order_approved": "✅ Buyurtma #{order_id} tasdiqlandi va yetkazildi!",
    "admin_order_already_processed": "⚠️ Buyurtma #{order_id} allaqachon bajarilgan yoki bekor bo'lgan.",

    # Referal & Bepul Sovg'a
    "referral_info": (
        "👥 <b>Referal dasturi</b>\n\n"
        "🔗 <b>Sizning taklif havolangiz:</b>\n"
        "<code>{ref_link}</code>\n\n"
        "👥 Taklif qilingan do'stlar: <b>{ref_count}</b> ta\n"
        "⭐ To'plangan Stars: <b>{ref_stars}</b> ⭐\n\n"
        "ℹ️ <i>Har bir taklif qilgan do'stingiz uchun <b>+2 Stars</b> olasiz!</i>\n"
        "🎁 <i>Minimal <b>16 Stars</b> to'plab, o'zingizga bepul <b>Ayiqcha (15⭐)</b> sovg'asini olishingiz mumkin!</i>"
    ),
    "btn_claim_gift": "🎁 Sovg'ani olish (Min: 16 ⭐)",
    "btn_share_ref": "📤 Do'stlarga ulashish",
    "referral_share_text": "⭐ Telegram Stars, Premium va Sovg'alar xarid qilish uchun eng qulay bot! Ushbu havola orqali kiring:\n{ref_link}",
    "referral_reward_notice": "🎉 <b>Yangi do'st qo'shildi!</b>\nSizning taklif havolangiz orqali yangi do'stingiz botga kirdi. Sizga <b>+2 Stars</b> berildi! ⭐\n\nJami Stars: <b>{total_stars} ⭐</b>",
    "claim_min_stars_error": "⚠️ <b>Stars yetarli emas!</b>\nSovg'a olish uchun kamida <b>16 Stars</b> to'plashingiz kerak.\n\nSizda: <b>{current} Stars</b> bor (yana <b>{needed} Stars</b> / {friends_needed} ta do'st kerak).",
    "claim_enter_recipient": "🎁 <b>Sovg'ani qabul qiluvchi:</b>\nTelegram username'ingizni yozing yoki <b>«O'zimga»</b> tugmasini bosing:",
    "claim_success": "🎉 <b>Sovg'a so'rovingiz qabul qilindi!</b>\n\n🧸 <b>{gift_name}</b> sovg'asi tez orada @{recipient} ga yetkazib beriladi!\n\n<i>Qolgan Stars balansingiz: {remaining} ⭐</i>",

    # Majburiy obuna
    "sub_required_title": "📢 <b>Botdan to'liq foydalanish uchun quyidagi kanallarga a'zo bo'ling:</b>\n\nObuna bo'lgach, «✅ Tekshirish» tugmasini bosing:",
    "btn_sub_check": "✅ Tekshirish",
    "sub_not_completed": "❌ Siz hali barcha kanallarga a'zo bo'lmadingiz. Iltimos, barcha kanallarga obuna bo'lib qayta tekshiring!",
    "sub_verified": "✅ Obuna tasdiqlandi! Botdan to'liq foydalanishingiz mumkin.",
}
