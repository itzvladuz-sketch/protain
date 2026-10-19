"""Uzbek localization dictionary - Short, clean and crisp."""

TEXTS: dict = {
    # Til tanlash
    "lang_select": "🌐 <b>Tilni tanlang | Выберите язык | Select language:</b>",

    # Asosiy menyu
    "welcome": (
        '<tg-emoji emoji-id="5994750571041525522">👋</tg-emoji> Assalomu alaykum, {name}\n'
        '<tg-emoji emoji-id="5771887475421090729">🆔</tg-emoji> User ID: {user_num}\n'
        '┗<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji> Balans: {balance}\n\n'
        "Quyidagi xizmatlardan birini tanlang:"
    ),
    "main_menu": (
        '<tg-emoji emoji-id="5994750571041525522">👋</tg-emoji> Assalomu alaykum, {name}\n'
        '<tg-emoji emoji-id="5771887475421090729">🆔</tg-emoji> User ID: {user_num}\n'
        '┗<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji> Balans: {balance}\n\n'
        "Quyidagi xizmatlardan birini tanlang:"
    ),

    # Tugmalar
    "btn_stars":    "Stars",
    "btn_premium":  "Premium",
    "btn_gift":     "Sovg'alar (Gifts)",
    "btn_balance":  "Balans",
    "btn_referral": "Referal (+2⭐)",
    "btn_orders":   "Buyurtmalarim",
    "btn_help":     "Yordam",
    "btn_language": "Tilni o'zgartirish",
    "btn_myself":   "O'zimga",
    "btn_back":     "Orqaga",
    "btn_cancel":   "Bekor qilish",
    "btn_pay_ton":  "TON bilan to'lash",
    "btn_pay_humo": "Humo (so'm)",
    "btn_check_payment": "Tekshirish",

    # Stars
    "stars_menu": (
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> <b>Telegram Stars</b>\n\n'
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> Kimga olamiz? Username kiriting yoki <b>«O\'zimga»</b> tugmasini bosing:'
    ),
    "enter_recipient": (
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> <b>Kimga olamiz?</b>\n'
        "Username kiriting yoki <b>«O'zimga»</b> bosing:"
    ),
    "enter_stars_amount": (
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> <b>Stars miqdorini kiriting:</b>\n'
        "Min: <b>{min}</b> | Max: <b>{max}</b>"
    ),
    "select_stars_amount": (
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> <b>Telegram Stars</b>\n\n'
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> Qabul qiluvchi: <b>@{recipient}</b>\n\n'
        "Kerakli miqdorni tanlang yoki <b>«Boshqa miqdor»</b> tugmasini bosing:"
    ),
    "no_username_set": "⚠️ Sizda @username yo'q. Qabul qiluvchi username'ini yozing:",
    "checking_username": "🔍 Tekshirilmoqda...",
    "username_invalid": "❌ Username topilmadi. Qayta kiriting:",

    # Buyurtma
    "order_summary_stars": (
        "📋 <b>Buyurtma:</b>\n\n"
        "⭐ <b>{amount} Stars</b> ➔ @{recipient}\n"
        "💰 Narxi: <b>{price}</b>\n"
        "👛 Balansingiz: <b>{balance}</b>\n"
        "{discount_line}"
    ),
    "order_summary_premium": (
        "📋 <b>Buyurtma:</b>\n\n"
        "👑 <b>Premium ({duration})</b> ➔ @{recipient}\n"
        "💰 Narxi: <b>{price}</b>\n"
        "👛 Balansingiz: <b>{balance}</b>\n"
        "{discount_line}"
    ),
    "order_summary_gift": (
        "📋 <b>Buyurtma:</b>\n\n"
        "🎁 <b>{gift_name} ({amount} Stars)</b> ➔ @{recipient}\n"
        "💰 Narxi: <b>{price}</b>\n"
        "👛 Balansingiz: <b>{balance}</b>\n"
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
        "⏱ To'lov muddati: <b>30 daqiqa</b>\n\n"
        "⚠️ <b>DIQQAT:</b> To'lov avtomatik tarzda 1-2 soniyada tasdiqlanishi uchun aynan <code>{amount:,}</code> so'm o'tkazing!"
    ),
    "click_payment_instructions": (
        "🔵 <b>Click (Uzcard) to'lov:</b>\n\n"
        "💳 Karta:\n<code>{card_number}</code>\n"
        "👤 Egasi: <b>{card_holder}</b>\n\n"
        "💰 To'lov summasi:\n<code>{amount:,}</code> so'm\n\n"
        "⏱ To'lov muddati: <b>30 daqiqa</b>\n\n"
        "⚠️ <b>DIQQAT:</b> To'lov avtomatik tarzda 1-2 soniyada tasdiqlanishi uchun aynan <code>{amount:,}</code> so'm o'tkazing!\n\n"
        "<i>To'lovni @clickuz boti yoki Click ilovasi orqali amalga oshirishingiz mumkin.</i>"
    ),
    "payment_not_found": "⏳ To'lov hali topilmadi. Pul o'tkazgan bo'lsangiz, 1-2 daqiqa kuting.",
    "payment_found": "✅ To'lov qabul qilindi!",
    "order_completed": (
        '<tg-emoji emoji-id="5994502837327892086">🎉</tg-emoji> <b>Bajarildi!</b>\n\n'
        '<tg-emoji emoji-id="5776375003280838798">✅</tg-emoji> <b>{amount}</b> ➔ @{recipient} ga yetkazildi.'
    ),
    "order_failed": "❌ Xatolik yuz berdi. @{support} ga murojaat qiling.",
    "order_expired": "⏱ Buyurtma #{id} muddati tugadi (to'lov qilinmadi).",

    # Balans
    "balance_info": (
        '<tg-emoji emoji-id="5771887475421090729">🆔</tg-emoji> User ID: {user_num}\n'
        '┗<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji> Balans: {balance}\n\n'
        "Balansni to'ldirish uchun quyidagi tugmani bosing:"
    ),
    "btn_topup": "To'ldirish",
    "btn_pay_humo": "Humo orqali to'lash",
    "btn_pay_click": "Click orqali to'lash",
    "btn_pay_balance": "Balansdan to'lash",
    "balance_topup_menu": '<tg-emoji emoji-id="5967548335542767952">💳</tg-emoji> <b>Balansni to\'ldirish (Humo / Click):</b>\n\nSummani tanlang yoki so\'mda yozing (masalan: 50000):',
    "balance_topup_min_error": "⚠️ Minimal summa: {min:,} so'm",
    "balance_topup_uzs_completed": (
        '<tg-emoji emoji-id="5994502837327892086">🎉</tg-emoji> <b>Balans to\'ldirildi!</b>\n\n'
        '+<b>{amount:,} so\'m</b> hisobingizga qo\'shildi.\n'
        "Joriy balans: <b>{new_balance:,} so'm</b>"
    ),
    "paid_from_balance": "✅ Balansdan to'landi! Buyurtma bajarilmoqda...",
    "insufficient_balance": "⚠️ Balansda mablag' yetarli emas.",

    # Yordam
    "help_text": (
        '<tg-emoji emoji-id="5873121512445187130">🆘</tg-emoji> <b>Yordam</b>\n\n'
        "👨‍💻 Aloqa: @{support}\n"
        '<tg-emoji emoji-id="5843553939672274145">⚡</tg-emoji> Xaridlar to\'lovdan so\'ng 1-3 daqiqada yetkaziladi.'
    ),

    # Buyurtmalar tarixi
    "my_orders": '<tg-emoji emoji-id="5886330010054168711">📋</tg-emoji> <b>Buyurtmalaringiz:</b>',
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
        '<tg-emoji emoji-id="5909201569898827582">🔔</tg-emoji> <b>Yangi Humo to\'lov buyurtmasi!</b>\n\n'
        '<tg-emoji emoji-id="5771887475421090729">🆔</tg-emoji> Buyurtma: #{order_id}\n'
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> Foydalanuvchi: @{username} (ID: <code>{user_id}</code>)\n'
        '<tg-emoji emoji-id="5924720918826848520">📦</tg-emoji> Turi: <b>{order_type}</b>\n'
        '<tg-emoji emoji-id="5811989245761426317">💰</tg-emoji> Summa: <b>{price_uzs:,} so\'m</b>\n'
        '<tg-emoji emoji-id="5778605968208170641">⏱</tg-emoji> Qabul qilish: 5 daqiqa ichida'
    ),
    "admin_order_approved": '<tg-emoji emoji-id="5776375003280838798">✅</tg-emoji> Buyurtma #{order_id} tasdiqlandi va yetkazildi!',
    "admin_order_already_processed": "⚠️ Buyurtma #{order_id} allaqachon bajarilgan yoki bekor bo'lgan.",

    # Referal & Bepul Sovg'a
    "referral_info": (
        '<tg-emoji emoji-id="5915556996215476302">👥</tg-emoji> <b>Referal dasturi</b>\n\n'
        "🔗 <b>Sizning taklif havolangiz:</b>\n"
        "<code>{ref_link}</code>\n\n"
        '<tg-emoji emoji-id="5915556996215476302">👥</tg-emoji> Taklif qilingan do\'stlar: <b>{ref_count}</b> ta\n'
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> To\'plangan Stars: <b>{ref_stars}</b> ⭐\n\n'
        'ℹ️ <i>Har bir taklif qilgan do\'stingiz uchun <b>+2 Stars</b> olasiz!</i>\n'
        '<tg-emoji emoji-id="6032937473162614352">🎁</tg-emoji> <i>Minimal <b>16 Stars</b> to\'plab, o\'zingizga bepul <b>Ayiqcha (15⭐)</b> sovg\'asini olishingiz mumkin!</i>'
    ),
    "btn_claim_gift": "Sovg'ani olish (Min: 16 ⭐)",
    "btn_share_ref": "Do'stlarga ulashish",
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
