"""Multi-currency formatter according to user language:
uz -> Uzbek so'm (UZS)
ru -> Russian ruble (RUB)
en -> US Dollar (USD)
"""

from services.config import BotConfig


def format_currency(usd_amount: float, lang: str, config: BotConfig) -> str:
    """Format USD amount into user's language currency."""
    if lang == "uz":
        rate = getattr(config, "usd_to_uzs_rate", 12900.0)
        uzs = round(usd_amount * rate)
        return f"{uzs:,} so'm".replace(",", " ")
    elif lang == "ru":
        rate = getattr(config, "usd_rub_rate", 100.0)
        rub = round(usd_amount * rate, 1)
        if rub.is_integer():
            return f"{int(rub):,} ₽".replace(",", " ")
        return f"{rub:,.1f} ₽".replace(",", " ")
    else:  # en
        return f"${usd_amount:,.2f}"


def format_balance(balance_uzs: float, lang: str, config: BotConfig) -> str:
    """Format balance (stored in UZS) according to user language currency."""
    if lang == "uz":
        return f"{int(balance_uzs):,} so'm".replace(",", " ")
    rate_uzs = getattr(config, "usd_to_uzs_rate", 12900.0) or 12900.0
    usd = balance_uzs / rate_uzs
    if lang == "ru":
        rate_rub = getattr(config, "usd_rub_rate", 100.0) or 100.0
        rub = round(usd * rate_rub, 1)
        if rub.is_integer():
            return f"{int(rub):,} ₽".replace(",", " ")
        return f"{rub:,.1f} ₽".replace(",", " ")
    else:  # en
        return f"${usd:,.2f}"
