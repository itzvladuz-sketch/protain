"""Test suite for /start flow and ThrottlingMiddleware."""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

BASE_DIR = "d:/birinchi mijon/tg_stars_premium_shop"
sys.path.insert(0, BASE_DIR)

from aiogram.types import Chat, Message, User
from services.config import BotConfig
from services.db import Database
from services.throttling import ThrottlingMiddleware
from handlers.start import cmd_start

async def run_tests():
    print("=" * 60)
    print("  TESTING /START AND THROTTLING MIDDLEWARE")
    print("=" * 60)

    # 1. Config admin_ids property
    cfg = BotConfig.load()
    assert hasattr(cfg, "admin_ids")
    assert hasattr(cfg, "admin_user_ids")
    assert cfg.admin_ids == cfg.admin_user_ids
    print("  [+] BotConfig admin_ids & admin_user_ids: OK")

    # 2. ThrottlingMiddleware execution
    throttle = ThrottlingMiddleware(cfg)
    handler = AsyncMock(return_value="handled")

    user = User(id=12345678, is_bot=False, first_name="Test", username="testuser")
    msg = MagicMock(spec=Message)
    msg.from_user = user
    data = {"event_from_user": user}

    # First call should succeed
    res = await throttle(handler, msg, data)
    assert res == "handled"
    print("  [+] ThrottlingMiddleware normal pass: OK")

    # Multiple calls under limit (1 + 4 = 5 calls)
    for _ in range(4):
        res = await throttle(handler, msg, data)
        assert res == "handled"
    print("  [+] ThrottlingMiddleware allows burst up to limit: OK")

    # 6th call exceeds burst limit (5) -> throttled
    throttled_res = await throttle(handler, msg, data)
    assert throttled_res is None
    print("  [+] ThrottlingMiddleware throttles excessive burst: OK")

    # 3. Test cmd_start
    test_db_path = os.path.join(BASE_DIR, "test_start.db")
    try:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    except Exception:
        pass

    db = Database(test_db_path)
    await db.init_db()

    real_msg = MagicMock(spec=Message)
    real_msg.from_user = user
    real_msg.text = "/start"
    real_msg.answer = AsyncMock()
    real_msg.bot = MagicMock()

    state = MagicMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()

    # Create user in db with language set
    await db.get_or_create_user(user.id, user.username)
    await db.update_user_lang(user.id, "uz")

    # Call cmd_start with patched db
    import handlers.start as start_module
    from unittest.mock import patch

    with patch("services.config.BotConfig.load", return_value=cfg):
        with patch("handlers.start.Database", return_value=db):
            await cmd_start(real_msg, state)

    assert real_msg.answer.called
    call_args = real_msg.answer.call_args
    assert "Assalomu alaykum" in call_args[0][0]
    print("  [+] cmd_start successfully sends welcome menu: OK")

    try:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    except Exception:
        pass

    print("=" * 60)
    print("  ALL START & THROTTLING TESTS PASSED 100%!")
    print("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(run_tests())
    os._exit(0)
