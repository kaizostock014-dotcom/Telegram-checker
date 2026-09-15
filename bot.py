import asyncio
import os
import sqlite3

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(TOKEN)
dp = Dispatcher()

db = sqlite3.connect("users.db")
db.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    credits INTEGER DEFAULT 10,
    plan TEXT DEFAULT 'FREE',
    status TEXT DEFAULT 'ACTIVE'
)
""")
db.commit()


def add_user(user_id, username):
    db.execute(
        "INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)",
        (user_id, username)
    )
    db.commit()


def get_user(user_id):
    return db.execute(
        "SELECT id, username, credits, plan, status FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()


@dp.message(Command("start"))
async def start(message: Message):
    add_user(
        message.from_user.id,
        message.from_user.username or ""
    )

    await message.answer(
        "⚡ Kaori Test Checker\n\n"
        "👋 Bienvenido\n\n"
        "Usa /me para ver tu información.\n"
        "Usa /check para realizar una prueba en sandbox."
    )


@dp.message(Command("me"))
async def me(message: Message):
    add_user(
        message.from_user.id,
        message.from_user.username or ""
    )

    user = get_user(message.from_user.id)

    await message.answer(
        "⚡ USER INFO\n\n"
        f"👤 User: @{user[1] or 'sin_username'}\n"
        f"🆔 ID: {user[0]}\n"
        f"💎 Plan: {user[3]}\n"
        f"🟢 Status: {user[4]}\n"
        f"💳 Credits: {user[2]}"
    )


@dp.message(Command("check"))
async def check(message: Message):
    add_user(
        message.from_user.id,
        message.from_user.username or ""
    )

    user = get_user(message.from_user.id)

    if user[2] <= 0:
        await message.answer("❌ No tienes créditos.")
        return

    db.execute(
        "UPDATE users SET credits = credits - 1 WHERE id = ?",
        (message.from_user.id,)
    )
    db.commit()

    await message.answer(
        "🧪 TEST CHECK\n\n"
        "✅ Prueba procesada en modo sandbox.\n"
        "💳 Se utilizó 1 crédito.\n\n"
        "⚠️ Este bot no comprueba tarjetas reales."
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
