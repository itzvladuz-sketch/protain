"""English localization dictionary - Short, clean and crisp."""

TEXTS: dict = {
    # Language select
    "lang_select": "🌐 <b>Tilni tanlang | Выберите язык | Select language:</b>",

    # Main menu
    "welcome": (
        "👋 Hello, <b>{name}</b>!\n\n"
        "Please select a service:"
    ),
    "main_menu": (
        "👋 <b>Main Menu</b>\n\n"
        "Please select a service:"
    ),

    # Buttons
    "btn_stars":    "⭐ Stars",
    "btn_premium":  "💎 Premium",
    "btn_gift":     "🎁 Gifts Catalog",
    "btn_balance":  "💰 Balance",
    "btn_referral": "👥 Referrals (+2⭐)",
    "btn_orders":   "📋 My Orders",
    "btn_help":     "Help",
    "btn_language": "🌐 Change Language",
    "btn_myself":   "👤 For myself",
    "btn_back":     "◀️ Back",
    "btn_cancel":   "❌ Cancel",
    "btn_pay_ton":  "💎 Pay TON",
    "btn_pay_humo": "💳 Humo (UZS)",
    "btn_check_payment": "🔍 Check",

    # Stars
    "stars_menu": (
        "⭐ <b>Telegram Stars</b>\n\n"
        "👤 Who is this for? Enter username or tap <b>«For myself»</b>:"
    ),
    "enter_recipient": (
        "👤 <b>Who is this for?</b>\n"
        "Enter username or tap <b>«For myself»</b>:"
    ),
    "enter_stars_amount": (
        "⭐ <b>Stars amount:</b>\n"
        "Min: <b>{min}</b> | Max: <b>{max}</b>"
    ),
    "select_stars_amount": (
        "⭐ <b>Telegram Stars</b>\n\n"
        "👤 Recipient: <b>@{recipient}</b>\n\n"
        "Choose Stars amount or tap <b>«✏️ Custom amount»</b>:"
    ),
    "no_username_set": "⚠️ You don't have a @username. Enter recipient's username:",
    "checking_username": "🔍 Checking...",
    "username_invalid": "❌ User not found. Try again:",

    # Order
    "order_summary_stars": (
        "📋 <b>Order:</b>\n\n"
        "⭐ <b>{amount} Stars</b> ➔ @{recipient}\n"
        "💰 Price: <b>{price}</b>\n"
        "{discount_line}"
    ),
    "order_summary_premium": (
        "📋 <b>Order:</b>\n\n"
        "👑 <b>Premium ({duration})</b> ➔ @{recipient}\n"
        "💰 Price: <b>{price}</b>\n"
        "{discount_line}"
    ),
    "order_summary_gift": (
        "📋 <b>Order:</b>\n\n"
        "🎁 <b>{gift_name} ({amount} Stars)</b> ➔ @{recipient}\n"
        "💰 Price: <b>{price}</b>\n"
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
        "⏱ Payment window: <b>10 minutes</b>\n\n"
        "⚠️ <b>NOTE:</b> For automatic instant verification, please transfer exactly <code>{amount:,}</code> UZS!"
    ),
    "payment_not_found": "⏳ Payment not found yet. If you transferred, please wait 1-2 minutes.",
    "payment_found": "✅ Payment received!",
    "order_completed": (
        "🎉 <b>Completed!</b>\n\n"
        "✅ <b>{amount}</b> ➔ sent to @{recipient}."
    ),
    "order_failed": "❌ Failed. Contact @{support}.",
    "order_expired": "⏱ Order #{id} expired (payment not received).",

    # Balance
    "balance_info": (
        "💰 <b>Your balance:</b> <b>{balance}</b>\n\n"
        "To top up your balance, click the button below:"
    ),
    "btn_topup": "➕ Top Up",
    "btn_pay_humo": "💳 Pay with Humo",
    "btn_pay_balance": "💰 Pay from balance",
    "balance_topup_menu": "💳 <b>Top up balance (Humo):</b>\n\nChoose an amount or enter in UZS (e.g. 50000):",
    "balance_topup_min_error": "⚠️ Minimum amount: {min:,} UZS",
    "balance_topup_uzs_completed": (
        "🎉 <b>Balance topped up!</b>\n\n"
        "+<b>{amount:,} UZS</b> credited to your balance.\n"
        "Current balance: <b>{new_balance:,} UZS</b>"
    ),
    "paid_from_balance": "✅ Paid from balance! Order is being processed...",
    "insufficient_balance": "⚠️ Insufficient balance.",

    # Help
    "help_text": (
        "🆘 <b>Help</b>\n\n"
        "👨‍💻 Support: @{support}\n"
        "⚡️ Delivered in 1-3 minutes after payment."
    ),

    # Orders history
    "my_orders": "📋 <b>Your orders:</b>",
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
        "🔔 <b>New Humo order!</b>\n\n"
        "🆔 Order: #{order_id}\n"
        "👤 User: @{username} (ID: <code>{user_id}</code>)\n"
        "📦 Type: <b>{order_type}</b>\n"
        "💰 Amount: <b>{price_uzs:,} UZS</b>\n"
        "⏱ Awaiting payment: 5 minutes"
    ),
    "admin_order_approved": "✅ Order #{order_id} approved and fulfilled!",
    "admin_order_already_processed": "⚠️ Order #{order_id} has already been processed or cancelled.",

    # Referrals & Gifts
    "referral_info": (
        "👥 <b>Referral Program</b>\n\n"
        "🔗 <b>Your invite link:</b>\n"
        "<code>{ref_link}</code>\n\n"
        "👥 Friends invited: <b>{ref_count}</b>\n"
        "⭐ Earned Stars: <b>{ref_stars}</b> ⭐\n\n"
        "ℹ️ <i>For every friend invited, you receive <b>+2 Stars</b>!</i>\n"
        "🎁 <i>Collect <b>16 Stars</b> or more to claim a free <b>Teddy (15⭐)</b> gift!</i>"
    ),
    "btn_claim_gift": "🎁 Claim Gift (Min: 16 ⭐)",
    "btn_share_ref": "📤 Share with friends",
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
