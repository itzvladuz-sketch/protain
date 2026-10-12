"""Telethon sessiyasini yangilash va .env fayliga saqlash skripti.
Ishga tushirish uchun konsolda quyidagi buyruqni bering:
    python login_telethon.py
"""

import asyncio
import os
import dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

dotenv.load_dotenv(".env")

API_ID = int(os.getenv("TG_API_ID", 33727665))
API_HASH = os.getenv("TG_API_HASH", "92bd14dc73af062fbc506248e72bae1b")


async def main():
    print("=" * 60)
    print(" HUMO / BANK BOT XABARLARINI AVTOMATIK O'QISH UCHUN TIZIM")
    print("=" * 60)
    print("Karta to'lovlari haqida SMS keladigan Telegram akkauntingiz")
    print("telefon raqamini xalqaro formatda kiriting (masalan: +998901234567)\n")

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start()

    session_str = client.session.save()
    me = await client.get_me()

    print("\n" + "=" * 60)
    print(f"✅ MUVAFFAQIYATLI KIRILDI!")
    print(f"👤 Ism: {me.first_name}")
    print(f"🆔 Username: @{me.username or 'yoq'}")
    print(f"📞 Telefon: {me.phone}")
    print("=" * 60)

    # Save to .env
    dotenv.set_key(".env", "TELETHON_SESSION_STRING", session_str)
    print("\n💾 Yangi sessiya .env fayliga avtomatik saqlandi!")
    print("Endi bot Humo SMS botidan xabarlarni to'liq avtomatik o'qiydi.")
    print("Botni qayta ishga tushirishingiz mumkin: python main.py")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
