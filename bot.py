"""Minimal polling bot that demonstrates buying Telegram Stars via Fragment API."""

import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from loguru import logger

from handlers import admin, order, referral, start
from services.config import BotConfig
from services.db import Database
from services.fragment_api import FragmentAPIService
from services.logger import setup_logger
from services.payment_monitor import PaymentMonitor
from services.humo_monitor import HumoPaymentMonitor


async def notify_admins(bot: Bot, config: BotConfig, text: str) -> None:
    """Send a service message to every configured admin."""
    for admin_id in config.admin_user_ids:
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as exc:
            logger.warning("Не удалось отправить уведомление админу {}: {}", admin_id, exc)


async def check_fragment_api(config: BotConfig) -> None:
    """Check Fragment API once at startup and print a clear KYC recommendation."""
    fragment = FragmentAPIService(
        api_key=config.fragment_api_key,
        wallet_mnemonic=config.fragment_wallet_mnemonic,
        api_url=config.fragment_api_url,
        api_mode=config.fragment_api_mode,
        payment_method=config.fragment_payment_method,
        cookies_base64=config.fragment_cookies_base64,
        wallet_address=config.fragment_wallet_address,
        account_index=config.fragment_account_index,
    )
    health = await fragment.check_health()

    if health["ok"]:
        if health.get("provider") == "fragment-api.uz":
            logger.info(
                "Fragment-API.uz ulandi: loyiha='{}', hamyon='{}', balans={} TON, javob vaqti={}s",
                health.get("project"),
                health.get("wallet"),
                health.get("balance_ton"),
                health.get("response_time"),
            )
        else:
            logger.info(
                "Fragment API доступен: mode={}, payment_method={}, url={}, response={}s",
                config.fragment_api_mode,
                config.fragment_payment_method,
                config.fragment_api_url,
                health["response_time"],
            )
    else:
        logger.warning(
            "Fragment API не ответил при старте: {}. Бот запустится, но покупки могут падать.",
            health["error"],
        )

    if not config.fragment_api_key and config.fragment_api_mode != "kyc":
        logger.warning(
            "Режим no_kyc оставлен только для быстрого теста. Для стабильной работы используйте "
            "FRAGMENT_API_MODE=kyc и FRAGMENT_COOKIES_BASE64."
        )


async def main() -> None:
    """Load config, start the background monitor, and run aiogram polling."""
    load_dotenv()
    setup_logger()

    if not Path(".env").exists():
        logger.warning("Файл .env не найден. Скопируйте .env.example и заполните значения.")

    config = BotConfig.load()
    db = Database(config.database_path)
    await db.init_db()
    asyncio.create_task(check_fragment_api(config))

    bot = Bot(token=config.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin.router)
    dp.include_router(referral.router)
    dp.include_router(start.router)
    dp.include_router(order.router)

    monitor = PaymentMonitor(config)
    monitor.set_bot(bot)
    monitor_task = asyncio.create_task(monitor.start(), name="payment-monitor")

    humo_monitor = HumoPaymentMonitor(config, bot)
    humo_task = asyncio.create_task(humo_monitor.start(), name="humo-monitor")

    try:
        bot_info = await bot.get_me()
        logger.info("Бот запущен через polling: @{}", bot_info.username)
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception as e:
            logger.warning("delete_webhook xatosi (e'tiborsiz qoldiriladi): {}", e)

        while True:
            try:
                await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
                break
            except Exception as exc:
                logger.warning("Polling xatosi: {}. 5 soniyada qayta ulanadi...", exc)
                await asyncio.sleep(5)
    finally:
        await monitor.stop()
        await humo_monitor.stop()
        monitor_task.cancel()
        humo_task.cancel()
        await asyncio.gather(monitor_task, humo_task, return_exceptions=True)
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    import time
    while True:
        try:
            asyncio.run(main())
            break
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as err:
            logger.exception("Bot asosiy siklida xatolik: {}. 5 soniyada qayta ishga tushadi...", err)
            time.sleep(5)
