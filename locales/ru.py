"""Russian localization dictionary - Short, clean and crisp."""

TEXTS: dict = {
    # Выбор языка
    "lang_select": "🌐 <b>Tilni tanlang | Выберите язык | Select language:</b>",

    # Главное меню
    "welcome": (
        '<tg-emoji emoji-id="5994750571041525522">👋</tg-emoji> Здравствуйте, {name}\n'
        '<tg-emoji emoji-id="5771887475421090729">🆔</tg-emoji> User ID: {user_num}\n'
        '┗<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji> Баланс: {balance}\n\n'
        "Выберите услугу:"
    ),
    "main_menu": (
        '<tg-emoji emoji-id="5994750571041525522">👋</tg-emoji> Здравствуйте, {name}\n'
        '<tg-emoji emoji-id="5771887475421090729">🆔</tg-emoji> User ID: {user_num}\n'
        '┗<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji> Баланс: {balance}\n\n'
        "Выберите услугу:"
    ),

    # Кнопки
    "btn_stars":    "Stars",
    "btn_premium":  "Premium",
    "btn_gift":     "Подарки (Gifts)",
    "btn_balance":  "Баланс",
    "btn_referral": "Рефералы (+2⭐)",
    "btn_orders":   "Мои заказы",
    "btn_help":     "Помощь",
    "btn_language": "Сменить язык",
    "btn_support": "Поддержка",
    "btn_refresh": "Обновить",
    "btn_myself":   "Себе",
    "btn_back":     "Назад",
    "btn_cancel":   "Отмена",
    "btn_pay_ton":  "Оплатить TON",
    "btn_pay_humo": "Humo (сум)",
    "btn_check_payment": "Проверить",

    # Stars
    "stars_menu": (
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> <b>Telegram Stars</b>\n\n'
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> Кому покупаем? Введите username или нажмите <b>«Себе»</b>:'
    ),
    "enter_recipient": (
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> <b>Кому покупаем?</b>\n'
        "Введите username или нажмите <b>«Себе»</b>:"
    ),
    "enter_stars_amount": (
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> <b>Количество Stars:</b>\n'
        "Мин: <b>{min}</b> | Макс: <b>{max}</b>"
    ),
    "select_stars_amount": (
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> <b>Telegram Stars</b>\n\n'
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> Получатель: <b>@{recipient}</b>\n\n'
        "Выберите количество Stars или нажмите <b>«Другое количество»</b>:"
    ),
    "no_username_set": '<tg-emoji emoji-id="5872829476143894491">🚫</tg-emoji> У вас нет @username. Введите username получателя:',
    "checking_username": '<tg-emoji emoji-id="5879618294845584992">🔍</tg-emoji> Проверяю...',
    "username_invalid": '<tg-emoji emoji-id="5778527486270770928">❌</tg-emoji> Username не найден. Попробуйте снова:',

    # Заказ
    "order_summary_stars": (
        '<tg-emoji emoji-id="5886330010054168711">📋</tg-emoji> <b>Заказ:</b>\n\n'
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> <b>{amount} Stars</b> ➔ @{recipient}\n'
        '<tg-emoji emoji-id="5811989245761426317">💰</tg-emoji> Стоимость: <b>{price}</b>\n'
        '<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji> Ваш баланс: <b>{balance}</b>\n'
        "{discount_line}"
    ),
    "order_summary_premium": (
        '<tg-emoji emoji-id="5886330010054168711">📋</tg-emoji> <b>Заказ:</b>\n\n'
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> <b>Premium ({duration})</b> ➔ @{recipient}\n'
        '<tg-emoji emoji-id="5811989245761426317">💰</tg-emoji> Стоимость: <b>{price}</b>\n'
        '<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji> Ваш баланс: <b>{balance}</b>\n'
        "{discount_line}"
    ),
    "order_summary_gift": (
        '<tg-emoji emoji-id="5886330010054168711">📋</tg-emoji> <b>Заказ:</b>\n\n'
        '<tg-emoji emoji-id="6032937473162614352">🎁</tg-emoji> <b>{gift_name} ({amount} Stars)</b> ➔ @{recipient}\n'
        '<tg-emoji emoji-id="5811989245761426317">💰</tg-emoji> Стоимость: <b>{price}</b>\n'
        '<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji> Ваш баланс: <b>{balance}</b>\n'
        "{discount_line}"
    ),
    "discount_line": '<tg-emoji emoji-id="5994502837327892086">🎉</tg-emoji> Скидка: <b>-{discount}%</b>\n',

    # Premium
    "premium_menu": (
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> <b>Telegram Premium</b>\n\n'
        "Выберите период:"
    ),

    # Gift
    "gift_menu": (
        '<tg-emoji emoji-id="6032937473162614352">🎁</tg-emoji> <b>Telegram Gift</b>\n\n'
        "Выберите подарок:"
    ),

    # Оплата
    "humo_payment_instructions": (
        '<tg-emoji emoji-id="5967548335542767952">💳</tg-emoji> <b>Оплата через Humo:</b>\n\n'
        '<tg-emoji emoji-id="5967548335542767952">💳</tg-emoji> Карта:\n<code>{card_number}</code>\n'
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> Владелец: <b>{card_holder}</b>\n\n'
        '<tg-emoji emoji-id="5811989245761426317">💰</tg-emoji> Сумма к оплате:\n<code>{amount:,}</code> сум\n\n'
        '<tg-emoji emoji-id="5778605968208170641">⏱</tg-emoji> Срок оплаты: <b>{timeout} минут</b>\n\n'
        '<tg-emoji emoji-id="5908961403917570106">📌</tg-emoji> <b>ВНИМАНИЕ:</b> Для автоматического зачисления переводите именно <code>{amount:,}</code> сум!'
    ),
    "click_payment_instructions": (
        '<tg-emoji emoji-id="5967548335542767952">💳</tg-emoji> <b>Оплата через Click (Uzcard):</b>\n\n'
        '<tg-emoji emoji-id="5967548335542767952">💳</tg-emoji> Карта:\n<code>{card_number}</code>\n'
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> Владелец: <b>{card_holder}</b>\n\n'
        '<tg-emoji emoji-id="5811989245761426317">💰</tg-emoji> Сумма к оплате:\n<code>{amount:,}</code> сум\n\n'
        '<tg-emoji emoji-id="5778605968208170641">⏱</tg-emoji> Срок оплаты: <b>{timeout} минут</b>\n\n'
        '<tg-emoji emoji-id="5908961403917570106">📌</tg-emoji> <b>ВНИМАНИЕ:</b> Для автоматического зачисления переводите именно <code>{amount:,}</code> сум!\n\n'
        "<i>Оплатить можно через бота @clickuz или приложение Click Up.</i>"
    ),
    "payment_not_found": '<tg-emoji emoji-id="5778605968208170641">⏳</tg-emoji> Оплата пока не найдена. Если вы перевели, подождите 1-2 минуты.',
    "payment_found": '<tg-emoji emoji-id="5776375003280838798">✅</tg-emoji> Оплата принята!',
    "order_completed": (
        '<tg-emoji emoji-id="5994502837327892086">🎉</tg-emoji> <b>Выполнено!</b>\n\n'
        '<tg-emoji emoji-id="5776375003280838798">✅</tg-emoji> <b>{amount}</b> ➔ отправлено @{recipient}.'
    ),
    "order_failed": '<tg-emoji emoji-id="5778527486270770928">❌</tg-emoji> Ошибка. Обратитесь к @{support}.',
    "order_expired": '<tg-emoji emoji-id="5778605968208170641">⏱</tg-emoji> Срок заказа #{id} истёк (оплата не поступила).',

    # Баланс
    "balance_info": (
        '<tg-emoji emoji-id="5771887475421090729">🆔</tg-emoji> User ID: {user_num}\n'
        '┗<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji> Баланс: {balance}\n\n'
        "Для пополнения баланса нажмите кнопку ниже:"
    ),
    "btn_topup": "Пополнить",
    "btn_pay_humo": "Humo",
    "btn_pay_click": "Click (Uzcard)",
    "btn_pay_balance": "Оплатить с баланса",
    "balance_topup_menu": '<tg-emoji emoji-id="5967548335542767952">💳</tg-emoji> <b>Пополнение баланса (Humo / Click):</b>\n\nВыберите сумму или введите в сумах (например: 50000):',
    "balance_topup_min_error": '<tg-emoji emoji-id="5872829476143894491">🚫</tg-emoji> Минимальная сумма: {min:,} сум',
    "balance_topup_uzs_completed": (
        '<tg-emoji emoji-id="5994502837327892086">🎉</tg-emoji> <b>Баланс пополнен!</b>\n\n'
        '+<b>{amount:,} сум</b> зачислено на баланс.\n'
        "Текущий баланс: <b>{new_balance:,} сум</b>"
    ),
    "paid_from_balance": '<tg-emoji emoji-id="5776375003280838798">✅</tg-emoji> Оплачено с баланса! Заказ выполняется...',
    "insufficient_balance": '<tg-emoji emoji-id="5872829476143894491">🚫</tg-emoji> На балансе недостаточно средств.',

    # Помощь
    "help_text": (
        '<tg-emoji emoji-id="5873121512445187130">🆘</tg-emoji> <b>Помощь</b>\n\n'
        "👨‍💻 Поддержка: @{support}\n"
        '<tg-emoji emoji-id="5843553939672274145">⚡</tg-emoji> Доставка Stars в течение 1-3 минут после оплаты.'
    ),

    # Мои заказы
    "my_orders": '<tg-emoji emoji-id="5886330010054168711">📋</tg-emoji> <b>Ваши заказы:</b>',
    "no_orders": '<tg-emoji emoji-id="5924720918826848520">📦</tg-emoji> Заказов пока нет.',
    "order_item": "#{id} | {type} ➔ @{recipient} | {amount} | {status_emoji} {status}",

    "status_pending":    "Ожидает",
    "status_paid":       "Оплачен",
    "status_processing": "Выполняется",
    "status_completed":  "Выполнен",
    "status_failed":     "Ошибка",
    "status_cancelled":  "Отменен",
    "status_expired":    "Истек",

    "type_stars":   '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> Stars',
    "type_premium": '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> Premium',
    "type_gift":    '<tg-emoji emoji-id="6032937473162614352">🎁</tg-emoji> Gift',
    "type_topup":   '<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji> Баланс',

    "language_changed": '<tg-emoji emoji-id="5776375003280838798">✅</tg-emoji> Язык изменён!',
    "error_general": '<tg-emoji emoji-id="5778527486270770928">❌</tg-emoji> Ошибка. Попробуйте снова.',
    "error_try_again": '<tg-emoji emoji-id="5778527486270770928">❌</tg-emoji> Попробуйте снова.',
    "error_banned": '<tg-emoji emoji-id="5872829476143894491">🚫</tg-emoji> Вы заблокированы. @{support}',

    # Admin panel
    "admin_service_name_stars":      "⭐ Stars ($ / шт)",
    "admin_service_name_premium_1m": "⭐ Premium 1 мес",
    "admin_service_name_premium_3m": "⭐ Premium 3 мес",
    "admin_service_name_premium_6m": "⭐ Premium 6 мес",
    "admin_service_name_premium_12m":"⭐ Premium 12 мес",
    "admin_service_name_gift_50":    "🎁 Gift 50 Stars",
    "admin_service_name_gift_100":   "🎁 Gift 100 Stars",
    "admin_service_name_gift_150":   "🎁 Gift 150 Stars",
    "admin_service_name_gift_250":   "🎁 Gift 250 Stars",
    "admin_service_name_gift_1000":  "🎁 Gift 1000 Stars",

    "admin_new_humo_order": (
        '<tg-emoji emoji-id="5909201569898827582">🔔</tg-emoji> <b>Новый заказ через Humo!</b>\n\n'
        '<tg-emoji emoji-id="5771887475421090729">🆔</tg-emoji> Заказ: #{order_id}\n'
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> Пользователь: @{username} (ID: <code>{user_id}</code>)\n'
        '<tg-emoji emoji-id="5924720918826848520">📦</tg-emoji> Тип: <b>{order_type}</b>\n'
        '<tg-emoji emoji-id="5811989245761426317">💰</tg-emoji> Сумма: <b>{price_uzs:,} сум</b>\n'
        '<tg-emoji emoji-id="5778605968208170641">⏱</tg-emoji> Ожидание оплаты: 5 минут'
    ),
    "admin_order_approved": '<tg-emoji emoji-id="5776375003280838798">✅</tg-emoji> Заказ #{order_id} подтверждён и выполнен!',
    "admin_order_already_processed": '<tg-emoji emoji-id="5872829476143894491">🚫</tg-emoji> Заказ #{order_id} уже обработан или отменён.',

    # Рефералы и подарки
    "referral_info": (
        '<tg-emoji emoji-id="5915556996215476302">👥</tg-emoji> <b>Реферальная программа</b>\n\n'
        '<tg-emoji emoji-id="5877465816030515018">🔗</tg-emoji> <b>Ваша реферальная ссылка:</b>\n'
        "<code>{ref_link}</code>\n\n"
        '<tg-emoji emoji-id="5915556996215476302">👥</tg-emoji> Приглашено друзей: <b>{ref_count}</b>\n'
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> Заработано Stars: <b>{ref_stars}</b> ⭐\n\n'
        "ℹ️ <i>За каждого приглашённого друга вы получаете <b>+2 Stars</b>!</i>\n"
        '<tg-emoji emoji-id="6032937473162614352">🎁</tg-emoji> <i>Накопив от <b>16 Stars</b>, вы можете бесплатно забрать подарок <b>Мишка (15⭐)</b>!</i>'
    ),
    "btn_claim_gift": "Забрать подарок (Мин: 16 ⭐)",
    "btn_share_ref": "Поделиться с друзьями",
    "referral_share_text": "⭐ Самый удобный бот для покупки Telegram Stars, Premium и подарков! Переходи по ссылке:\n{ref_link}",
    "referral_reward_notice": '<tg-emoji emoji-id="5994502837327892086">🎉</tg-emoji> <b>Новый реферал!</b>\nПо вашей ссылке зарегистрировался новый друг. Вам начислено <b>+2 Stars</b>! <tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji>\n\nВсего Stars: <b>{total_stars}</b> <tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji>',
    "claim_min_stars_error": '<tg-emoji emoji-id="5872829476143894491">🚫</tg-emoji> <b>Недостаточно Stars!</b>\nДля получения подарка необходимо минимум <b>16 Stars</b>.\n\nУ вас: <b>{current} Stars</b> (нужно ещё <b>{needed} Stars</b> / {friends_needed} друзей).',
    "claim_enter_recipient": '<tg-emoji emoji-id="6032937473162614352">🎁</tg-emoji> <b>Получатель подарка:</b>\nВведите Telegram username или нажмите <b>«Себе»</b>:',
    "claim_success": '<tg-emoji emoji-id="5994502837327892086">🎉</tg-emoji> <b>Заявка на подарок принята!</b>\n\n<tg-emoji emoji-id="6032937473162614352">🎁</tg-emoji> Подарок <b>{gift_name}</b> будет отправлен на @{recipient}!\n\n<i>Остаток Stars: {remaining} ⭐</i>',

    # Обязательная подписка
    "sub_required_title": '<tg-emoji emoji-id="5771695636411847302">📢</tg-emoji> <b>Для использования бота подпишитесь на наши каналы:</b>\n\nПосле подписки нажмите кнопку «Проверить»:',
    "btn_sub_check": "Проверить",
    "sub_not_completed": '<tg-emoji emoji-id="5778527486270770928">❌</tg-emoji> Вы ещё не подписались на все каналы. Пожалуйста, подпишитесь и проверьте снова!',
    "sub_verified": '<tg-emoji emoji-id="5776375003280838798">✅</tg-emoji> Подписка подтверждена! Добро пожаловать!',
}
