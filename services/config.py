"""Small environment-based config for the Fragment Stars demo bot."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple

from loguru import logger


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("{}='{}' не int, использую {}", name, value, default)
        return default


def _float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value.replace(",", "."))
    except ValueError:
        logger.warning("{}='{}' не float, использую {}", name, value, default)
        return default


def _admin_ids() -> Tuple[int, ...]:
    raw = os.getenv("ADMIN_USER_ID", "")
    result: list[int] = []
    for chunk in raw.replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            result.append(int(chunk))
        except ValueError:
            logger.warning("ADMIN_USER_ID содержит некорректное значение '{}'", chunk)
    return tuple(result)


_CONFIG_CACHE: Optional["BotConfig"] = None


@dataclass(frozen=True)
class BotConfig:
    """Runtime settings intentionally kept boring and explicit."""

    bot_token: str
    database_path: str
    admin_user_ids: Tuple[int, ...]
    support_username: str

    fragment_api_key: Optional[str]
    fragment_wallet_mnemonic: str
    fragment_api_url: str
    fragment_api_mode: str
    fragment_payment_method: str
    fragment_cookies_base64: Optional[str]
    fragment_wallet_address: Optional[str]
    fragment_account_index: Optional[int]

    ton_wallet_address: str
    toncenter_api_key: Optional[str]

    min_stars_amount: int
    max_stars_amount: int
    order_timeout_minutes: int
    service_commission_percent: float
    usd_rub_rate: float

    enable_freekassa: bool
    freekassa_api_key: Optional[str]
    freekassa_shop_id: int
    freekassa_method: int
    freekassa_customer_ip: str

    humo_card_number: str
    humo_card_holder: str
    click_card_number: str
    click_card_holder: str
    tg_api_id: Optional[int]
    tg_api_hash: Optional[str]
    notification_bot_username: str
    usd_to_uzs_rate: float
    telethon_session_string: str

    version: str

    @classmethod
    def load(cls, force_reload: bool = False) -> "BotConfig":
        global _CONFIG_CACHE
        if _CONFIG_CACHE is not None and not force_reload:
            return _CONFIG_CACHE

        api_key = (os.getenv("FRAGMENT_API_KEY") or "").strip() or None
        required = ["BOT_TOKEN", "TON_WALLET_ADDRESS"]
        if not api_key:
            required.append("FRAGMENT_WALLET_MNEMONIC")

        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise ValueError(f"Отсутствуют переменные окружения: {', '.join(missing)}")

        api_mode = os.getenv("FRAGMENT_API_MODE", "kyc").strip().lower()
        if api_mode not in {"kyc", "no_kyc"}:
            logger.warning("FRAGMENT_API_MODE='{}' неизвестен, использую kyc", api_mode)
            api_mode = "kyc"

        payment_method = os.getenv("FRAGMENT_PAYMENT_METHOD", "ton").strip().lower()
        if payment_method not in {"ton", "usdt_ton"}:
            logger.warning("FRAGMENT_PAYMENT_METHOD='{}' неизвестен, использую ton", payment_method)
            payment_method = "ton"

        account_index_raw = os.getenv("FRAGMENT_ACCOUNT_INDEX", "").strip()
        account_index: Optional[int] = None
        if account_index_raw:
            try:
                account_index = int(account_index_raw)
                if account_index < 0 or account_index > 2_147_483_647:
                    raise ValueError
            except ValueError as exc:
                raise ValueError(
                    "FRAGMENT_ACCOUNT_INDEX должен быть целым числом от 0 до 2147483647"
                ) from exc

        config = cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            database_path=os.getenv("DATABASE_PATH", "stars_bot.db"),
            admin_user_ids=_admin_ids(),
            support_username=os.getenv("SUPPORT_USERNAME", "id_4448"),
            fragment_api_key=api_key,
            fragment_wallet_mnemonic=os.getenv("FRAGMENT_WALLET_MNEMONIC", ""),
            fragment_api_url=os.getenv("FRAGMENT_API_URL", "https://api.fragment-api.space"),
            fragment_api_mode=api_mode,
            fragment_payment_method=payment_method,
            fragment_cookies_base64=os.getenv("FRAGMENT_COOKIES_BASE64"),
            fragment_wallet_address=os.getenv("FRAGMENT_WALLET_ADDRESS") or None,
            fragment_account_index=account_index,
            ton_wallet_address=os.getenv("TON_WALLET_ADDRESS", ""),
            toncenter_api_key=os.getenv("TONCENTER_API_KEY") or os.getenv("TONAPI_KEY"),
            min_stars_amount=max(50, _int("MIN_STARS_AMOUNT", 50)),
            max_stars_amount=_int("MAX_STARS_AMOUNT", 50_000),
            order_timeout_minutes=_int("ORDER_TIMEOUT_MINUTES", 15),
            service_commission_percent=_float("SERVICE_COMMISSION_PERCENT", 3.0),
            usd_rub_rate=_float("USD_RUB_RATE", 100.0),
            enable_freekassa=_bool("ENABLE_FREEKASSA", False),
            freekassa_api_key=os.getenv("FREEKASSA_API_KEY"),
            freekassa_shop_id=_int("FREEKASSA_SHOP_ID", 0),
            freekassa_method=_int("FREEKASSA_METHOD", 44),
            freekassa_customer_ip=os.getenv("FREEKASSA_CUSTOMER_IP", "127.0.0.1"),
            humo_card_number=os.getenv("HUMO_CARD_NUMBER", "9860 3501 4730 5402").strip() or "9860 3501 4730 5402",
            humo_card_holder=os.getenv("HUMO_CARD_HOLDER", "HUMO CARD").strip() or "HUMO CARD",
            click_card_number=os.getenv("CLICK_CARD_NUMBER", "8801 9102 6669 7252").strip() or "8801 9102 6669 7252",
            click_card_holder=os.getenv("CLICK_CARD_HOLDER", "CLICK CARD").strip() or "CLICK CARD",
            tg_api_id=_int("TG_API_ID", 0) or None,
            tg_api_hash=os.getenv("TG_API_HASH") or None,
            notification_bot_username=os.getenv("NOTIFICATION_BOT_USERNAME", "@HUMOcardbot,@clickuz").strip() or "@HUMOcardbot,@clickuz",
            usd_to_uzs_rate=_float("USD_TO_UZS_RATE", 12900.0),
            telethon_session_string=os.getenv("TELETHON_SESSION_STRING", "").strip().strip("'\""),
            version=os.getenv("BOT_VERSION", "2.0-demo"),
        )
        config._warn_about_optional_settings()
        _CONFIG_CACHE = config
        return config

    def _warn_about_optional_settings(self) -> None:
        if self.fragment_api_mode == "kyc" and not self.fragment_cookies_base64:
            logger.warning(
                "FRAGMENT_API_MODE=kyc, но FRAGMENT_COOKIES_BASE64 пустой. "
                "KYC режим стабильнее, но ему нужны актуальные cookies Fragment."
            )
        if self.fragment_api_mode == "no_kyc":
            logger.warning(
                "no_kyc подходит для демо-запуска, но стабильность ниже. "
                "Основной рекомендуемый режим: FRAGMENT_API_MODE=kyc."
            )
        if self.fragment_payment_method == "usdt_ton":
            logger.warning(
                "FRAGMENT_PAYMENT_METHOD=usdt_ton: кошелек из FRAGMENT_WALLET_MNEMONIC должен иметь USDT on TON "
                "и небольшой TON баланс для газа/комиссии API."
            )
        if self.enable_freekassa and (not self.freekassa_api_key or not self.freekassa_shop_id):
            logger.warning(
                "ENABLE_FREEKASSA=true, но FREEKASSA_API_KEY/FREEKASSA_SHOP_ID не заполнены. "
                "Кнопка FreeKassa будет скрыта."
            )

    @property
    def freekassa_ready(self) -> bool:
        """True when the single acquiring provider can be shown to users."""
        return self.enable_freekassa and bool(self.freekassa_api_key) and self.freekassa_shop_id > 0
