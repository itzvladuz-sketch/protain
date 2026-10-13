"""English localization dictionary - Short, clean and crisp."""

TEXTS: dict = {
    # Language select
    "lang_select": "🌐 <b>Tilni tanlang | Выберите язык | Select language:</b>",

    # Main menu
    "welcome": (
        '<tg-emoji emoji-id="5994750571041525522">👋</tg-emoji> Hello, {name}\n'
        '<tg-emoji emoji-id="5771887475421090729">🆔</tg-emoji> User ID: {user_num}\n'
        '┗<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji> Balance: {balance}\n\n'
        "Please select a service:"
    ),
    "main_menu": (
        '<tg-emoji emoji-id="5994750571041525522">👋</tg-emoji> Hello, {name}\n'
        '<tg-emoji emoji-id="5771887475421090729">🆔</tg-emoji> User ID: {user_num}\n'
        '┗<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji> Balance: {balance}\n\n'
        "Please select a service:"
    ),

    # Buttons
    "btn_stars":    "Stars",
    "btn_premium":  "Premium",
    "btn_gift":     "Gifts",
    "btn_balance":  "Balance",
    "btn_referral": "Referrals (+2⭐)",
    "btn_orders":   "My Orders",
    "btn_help":     "Help",
    "btn_language": "Change Language",
    "btn_myself":   "For myself",
    "btn_back":     "Back",
    "btn_cancel":   "Cancel",
    "btn_pay_ton":  "Pay TON",
    "btn_pay_humo": "Humo",
    "btn_check_payment": "Check",

    # Stars
    "stars_menu": (
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> <b>Telegram Stars</b>\n\n'
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> Who is this for? Enter username or tap <b>«For myself»</b>:'
    ),
    "enter_recipient": (
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> <b>Who is this for?</b>\n'
        "Enter username or tap <b>«For myself»</b>:"
    ),
    "enter_stars_amount": (
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> <b>Stars amount:</b>\n'
        "Min: <b>{min}</b> | Max: <b>{max}</b>"
    ),
    "select_stars_amount": (
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> <b>Telegram Stars</b>\n\n'
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> Recipient: <b>@{recipient}</b>\n\n'
        "Choose Stars amount or tap <b>«Custom amount»</b>:"
    ),
    "no_username_set": "⚠️ You don't have a @username. Enter recipient's username:",
    "checking_username": "🔍 Checking...",
    "username_invalid": "❌ User not found. Try again:",

    # Order
    "order_summary_stars": (
        "📋 <b>Order:</b>\n\n"
        "⭐ <b>{amount} Stars</b> ➔ @{recipient}\n"
        "💰 Price: <b>{price}</b>\n"
        "👛 Your balance: <b>{balance}</b>\n"
        "{discount_line}"
    ),
    "order_summary_premium": (
        "📋 <b>Order:</b>\n\n"
        "👑 <b>Premium ({duration})</b> ➔ @{recipient}\n"
        "💰 Price: <b>{price}</b>\n"
        "👛 Your balance: <b>{balance}</b>\n"
        "{discount_line}"
    ),
    "order_summary_gift": (
        "📋 <b>Order:</b>\n\n"
        "🎁 <b>{gift_name} ({amount} Stars)</b> ➔ @{recipient}\n"
        "💰 Price: <b>{price}</b>\n"
        "👛 Your balance: <b>{balance}</b>\n"
        "{discount_line}"
    ),
    "discount_line": "🎉 Discount: <b>-{discount}%</b>\n",

    # Premium
    "premium_menu": (
        "👑 <b>Telegram Premium</b>\n\n"
        "Select duration:"
    ),

    # Gift
    "gift_menu": (
        "🎁 <b>Telegram Gift</b>\n\n"
        "Select gift:"
    ),

    # Payment
    "humo_payment_instructions": (
        "💳 <b>Humo Payment:</b>\n\n"
        "💳 Card:\n<code>{card_number}</code>\n"
        "👤 Cardholder: <b>{card_holder}</b>\n\n"
        "💰 Payment Amount:\n<code>{amount:,}</code> UZS\n\n"
        "⏱ Payment window: <b>5 minutes</b>\n\n"
        "⚠️ <b>NOTE:</b> For automatic instant verification, please transfer exactly <code>{amount:,}</code> UZS!"
    ),
    "payment_not_found": "⏳ Payment not found yet. If you transferred, please wait 1-2 minutes.",
    "payment_found": "✅ Payment received!",
    "order_completed": (
        '<tg-emoji emoji-id="5994502837327892086">🎉</tg-emoji> <b>Completed!</b>\n\n'
        '<tg-emoji emoji-id="5776375003280838798">✅</tg-emoji> <b>{amount}</b> ➔ sent to @{recipient}.'
    ),
    "order_failed": "❌ Failed. Contact @{support}.",
    "order_expired": "⏱ Order #{id} expired (payment not received).",

    # Balance
    "balance_info": (
        '<tg-emoji emoji-id="5771887475421090729">🆔</tg-emoji> User ID: {user_num}\n'
        '┗<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji> Balance: {balance}\n\n'
        "To top up your balance, click the button below:"
    ),
    "btn_topup": "Top Up",
    "btn_pay_humo": "Humo",
    "btn_pay_balance": "Pay from balance",
    "balance_topup_menu": '<tg-emoji emoji-id="5967548335542767952">💳</tg-emoji> <b>Top up balance (Humo):</b>\n\nChoose an amount or enter in UZS (e.g. 50000):',
    "balance_topup_min_error": "⚠️ Minimum amount: {min:,} UZS",
    "balance_topup_uzs_completed": (
        '<tg-emoji emoji-id="5994502837327892086">🎉</tg-emoji> <b>Balance topped up!</b>\n\n'
        "+<b>{amount:,} UZS</b> credited to your balance.\n"
        "Current balance: <b>{new_balance:,} UZS</b>"
    ),
    "paid_from_balance": "✅ Paid from balance! Order is being processed...",
    "insufficient_balance": "⚠️ Insufficient balance.",

    # Help
    "help_text": (
        '<tg-emoji emoji-id="5873121512445187130">🆘</tg-emoji> <b>Help</b>\n\n'
        "👨‍💻 Support: @{support}\n"
        '<tg-emoji emoji-id="5843553939672274145">⚡</tg-emoji> Delivered in 1-3 minutes after payment.'
    ),

    # Orders history
    "my_orders": '<tg-emoji emoji-id="5886330010054168711">📋</tg-emoji> <b>Your orders:</b>',
    "no_orders": "📭 No orders yet.",
    "order_item": "#{id} | {type} ➔ @{recipient} | {amount} | {status_emoji} {status}",

    "status_pending":    "Pending",
    "status_paid":       "Paid",
    "status_processing": "Processing",
    "status_completed":  "Completed",
    "status_failed":     "Failed",
    "status_cancelled":  "Cancelled",

    "type_stars":   "⭐ Stars",
    "type_premium": "👑 Premium",
    "type_gift":    "🎁 Gift",

    "language_changed": "✅ Language changed!",
    "error_general": "❌ Error. Please try again.",
    "error_try_again": "❌ Please try again.",
    "error_banned": "🚫 You are banned. @{support}",

    # Admin panel
    "admin_service_name_stars":      "⭐ Stars ($ / pc)",
    "admin_service_name_premium_1m": "👑 Premium 1 mo",
    "admin_service_name_premium_3m": "👑 Premium 3 mo",
    "admin_service_name_premium_6m": "👑 Premium 6 mo",
    "admin_service_name_premium_12m":"👑 Premium 12 mo",
    "admin_service_name_gift_50":    "🎁 Gift 50 Stars",
    "admin_service_name_gift_100":   "🎁 Gift 100 Stars",
    "admin_service_name_gift_150":   "🎁 Gift 150 Stars",
    "admin_service_name_gift_250":   "🎁 Gift 250 Stars",
    "admin_service_name_gift_1000":  "🎁 Gift 1000 Stars",

    "admin_new_humo_order": (
        '<tg-emoji emoji-id="5909201569898827582">🔔</tg-emoji> <b>New Humo order!</b>\n\n'
        '<tg-emoji emoji-id="5771887475421090729">🆔</tg-emoji> Order: #{order_id}\n'
        '<tg-emoji emoji-id="5771887475421090729">👤</tg-emoji> User: @{username} (ID: <code>{user_id}</code>)\n'
        '<tg-emoji emoji-id="5924720918826848520">📦</tg-emoji> Type: <b>{order_type}</b>\n'
        '<tg-emoji emoji-id="5811989245761426317">💰</tg-emoji> Amount: <b>{price_uzs:,} UZS</b>\n'
        '<tg-emoji emoji-id="5778605968208170641">⏱</tg-emoji> Awaiting payment: 5 minutes'
    ),
    "admin_order_approved": '<tg-emoji emoji-id="5776375003280838798">✅</tg-emoji> Order #{order_id} approved and fulfilled!',
    "admin_order_already_processed": "⚠️ Order #{order_id} has already been processed or cancelled.",

    # Referrals & Gifts
    "referral_info": (
        '<tg-emoji emoji-id="5915556996215476302">👥</tg-emoji> <b>Referral Program</b>\n\n'
        "🔗 <b>Your invite link:</b>\n"
        "<code>{ref_link}</code>\n\n"
        '<tg-emoji emoji-id="5915556996215476302">👥</tg-emoji> Friends invited: <b>{ref_count}</b>\n'
        '<tg-emoji emoji-id="5958376256788502078">⭐</tg-emoji> Earned Stars: <b>{ref_stars}</b> ⭐\n\n'
        "ℹ️ <i>For every friend invited, you receive <b>+2 Stars</b>!</i>\n"
        '<tg-emoji emoji-id="6032937473162614352">🎁</tg-emoji> <i>Collect <b>16 Stars</b> or more to claim a free <b>Teddy (15⭐)</b> gift!</i>'
    ),
    "btn_claim_gift": "Claim Gift (Min: 16 ⭐)",
    "btn_share_ref": "Share with friends",
    "referral_share_text": "⭐ The easiest bot to buy Telegram Stars, Premium and Gifts! Join via this link:\n{ref_link}",
    "referral_reward_notice": "🎉 <b>New referral!</b>\nA new user joined via your link. You earned <b>+2 Stars</b>! ⭐\n\nTotal Stars: <b>{total_stars} ⭐</b>",
    "claim_min_stars_error": "⚠️ <b>Not enough Stars!</b>\nYou need at least <b>16 Stars</b> to claim a gift.\n\nYou have: <b>{current} Stars</b> (need <b>{needed} Stars</b> / {friends_needed} friends more).",
    "claim_enter_recipient": "🎁 <b>Gift recipient:</b>\nEnter Telegram username or tap <b>«For myself»</b>:",
    "claim_success": "🎉 <b>Gift request submitted!</b>\n\n🧸 <b>{gift_name}</b> will be delivered to @{recipient} shortly!\n\n<i>Remaining Stars: {remaining} ⭐</i>",

    # Mandatory subscription
    "sub_required_title": "📢 <b>To use the bot, please subscribe to our channels:</b>\n\nOnce subscribed, tap «✅ Check»:",
    "btn_sub_check": "✅ Check",
    "sub_not_completed": "❌ You haven't subscribed to all channels yet. Please subscribe and try again!",
    "sub_verified": "✅ Subscription verified! Welcome!",
}
