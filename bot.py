import os
import sqlite3

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, Update

TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
PUBLIC_URL = os.environ["RENDER_EXTERNAL_URL"]

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
        "⚡ TEST CHECKER\n\n"
        "👋 Bienvenido.\n\n"
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
        "⚠️ Este bot NO comprueba tarjetas reales."
    )


async def webhook(request):
    if request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token"
    ) != WEBHOOK_SECRET:
        return web.Response(status=403)

    data = await request.json()
    update = Update.model_validate(
        data,
        context={"bot": bot}
    )

    await dp.feed_update(bot, update)

    return web.Response(text="ok")


async def health(request):
    return web.Response(text="OK")


async def on_startup(app):
    await bot.set_webhook(
        url=f"{PUBLIC_URL}/telegram/{WEBHOOK_SECRET}",
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True
    )


async def on_cleanup(app):
    await bot.delete_webhook()
    await bot.session.close()


app = web.Application()

app.router.add_get("/", health)
app.router.add_post(
    f"/telegram/{WEBHOOK_SECRET}",
    webhook
)

app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

web.run_app(
    app,
    host="0.0.0.0",
    port=PORT
)
