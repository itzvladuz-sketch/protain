"""Interactive Telethon session authorizer for Humo auto-payment listener."""

import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()


async def main():
    api_id_raw = os.getenv("TG_API_ID")
    api_hash = os.getenv("TG_API_HASH")

    if not api_id_raw or not api_hash:
        print("XATO: .env faylida TG_API_ID yoki TG_API_HASH ko'rsatilmagan.")
        return

    api_id = int(api_id_raw)
    session_name = "humo_listener_session"

    print(f"Telethon ulanmoqda (API_ID: {api_id})...")
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()

    me = await client.get_me()
    print(f"\n✅ Muvaffaqiyatli ulandi!")
    print(f"👤 Foydalanuvchi: {me.first_name} (@{me.username or me.phone})")
    print("Sessiya 'humo_listener_session.session' fayliga saqlandi. Endi bot avtomatik ishlaydi.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
