"""TgAndroidIcons custom emoji IDs and helper functions for Telegram Premium UI."""

ICONS: dict[str, str] = {
    "wave":    "5994750571041525522",  # 👋
    "user":    "5771887475421090729",  # 👤 / 🆔
    "wallet":  "5769403330761593044",  # 👛
    "money":   "5811989245761426317",  # 💰
    "star":    "5958376256788502078",  # ⭐
    "diamond": "5963312935148195483",  # 💎
    "gift":    "6032937473162614352",  # 🎁
    "users":   "5915556996215476302",  # 👥
    "orders":  "5886330010054168711",  # 📝
    "help":    "5873121512445187130",  # 🆘 / ❓
    "globe":   "5879585266426973039",  # 🌐
    "card":    "5967548335542767952",  # 💳
    "check":   "5776375003280838798",  # ✅
    "back":    "5877629862306385808",  # ◀️
    "cancel":  "5778527486270770928",  # ❌
    "sparkle": "5931621672846103580",  # 💫
    "fire":    "6008118472066732010",  # 🔥
    "party":   "5994502837327892086",  # 🎉
    "plus":    "5877219383691972108",  # ➕
    "pencil":  "5879841310902324730",  # ✏️
    "crown":   "5807868868886009920",  # 👑
}


def tg_icon(name: str, fallback: str = "") -> str:
    """Return <tg-emoji> tag for HTML formatting with fallback standard emoji."""
    emoji_id = ICONS.get(name)
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback
