"""Test simulating the user clicking the '100 stars' button in the bot."""

import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath("."))
sys.stdout.reconfigure(encoding="utf-8")
import aiosqlite
from unittest.mock import AsyncMock, MagicMock
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage, StorageKey
from aiogram.types import CallbackQuery, Message, User, Chat

from services.config import BotConfig
from services.db import Database
from handlers.order import stars_qty_selected, OrderFlow

TEST_DB = "test_stars_100.db"

async def run_test():
    for f in [TEST_DB, f"{TEST_DB}-wal", f"{TEST_DB}-shm"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    os.environ["DATABASE_PATH"] = TEST_DB
    os.environ["BOT_TOKEN"] = "123456:FAKE_TOKEN"
    os.environ["TON_WALLET_ADDRESS"] = "EQDummyWalletAddress123"
    os.environ["FRAGMENT_WALLET_MNEMONIC"] = "word " * 24

    config = BotConfig.load(force_reload=True)
    db = Database(config.database_path)
    await db.init_db()

    # Create test user
    user_id = 8534196478
    username = "test_stars_buyer"
    await db.get_or_create_user(user_id, username)

    # Setup FSMContext
    storage = MemoryStorage()
    key = StorageKey(bot_id=123456, chat_id=user_id, user_id=user_id)
    state = FSMContext(storage=storage, key=key)
    await state.set_state(OrderFlow.enter_quantity)
    await state.update_data(service="stars", recipient=username)

    # Setup Mock CallbackQuery for "stars_qty:100"
    user_obj = User(id=user_id, is_bot=False, first_name="Test", username=username)
    chat_obj = Chat(id=user_id, type="private")
    message_obj = MagicMock(spec=Message)
    message_obj.edit_text = AsyncMock()
    message_obj.answer = AsyncMock()

    callback = MagicMock(spec=CallbackQuery)
    callback.data = "stars_qty:100"
    callback.from_user = user_obj
    callback.message = message_obj
    callback.answer = AsyncMock()

    print("Executing stars_qty_selected for 100 stars...")
    await stars_qty_selected(callback, state)

    # Verify state and output
    current_state = await state.get_state()
    data = await state.get_data()
    print(f"Current State: {current_state}")
    print(f"Stored Quantity: {data.get('quantity')}")
    print(f"Calculated Price USD: {data.get('price_usd')}")

    assert current_state == OrderFlow.confirm_order, f"Expected confirm_order, got {current_state}"
    assert data.get("quantity") == 100, f"Expected quantity 100, got {data.get('quantity')}"
    assert data.get("price_usd") > 0, "Price USD must be > 0"
    assert message_obj.edit_text.called or message_obj.answer.called, "Order summary was not displayed!"

    call_args = message_obj.edit_text.call_args or message_obj.answer.call_args
    summary_text = call_args[0][0]
    print("\n--- Displayed Order Summary ---")
    print(summary_text)
    print("--------------------------------")
    print("\nSUCCESS: 100 Stars button works flawlessly with 0 errors!")

if __name__ == "__main__":
    asyncio.run(run_test())
    os._exit(0)
