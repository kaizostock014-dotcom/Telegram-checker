import os
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
PUBLIC_URL = os.environ["RENDER_EXTERNAL_URL"]

# En Render crea esta variable:
# ADMIN_ID = tu número de usuario de Telegram
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(TOKEN)
dp = Dispatcher()

# =========================================================
# BASE DE DATOS
# =========================================================

db = sqlite3.connect("users.db", check_same_thread=False)

db.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT DEFAULT '',
    credits INTEGER DEFAULT 10,
    plan TEXT DEFAULT 'FREE',
    premium_until TEXT DEFAULT NULL,
    status TEXT DEFAULT 'ACTIVE'
)
""")

db.commit()


def add_user(user_id, username):
    db.execute(
        """
        INSERT OR IGNORE INTO users
        (id, username, credits, plan, status)
        VALUES (?, ?, 10, 'FREE', 'ACTIVE')
        """,
        (user_id, username)
    )
    db.commit()


def get_user(user_id):
    return db.execute(
        """
        SELECT id, username, credits, plan,
               premium_until, status
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()


def update_credits(user_id, amount):
    db.execute(
        "UPDATE users SET credits = credits + ? WHERE id = ?",
        (amount, user_id)
    )
    db.commit()


def activate_premium(user_id, days):
    user = get_user(user_id)

    now = datetime.now(timezone.utc)

    if user and user[4]:
        try:
            current_until = datetime.fromisoformat(user[4])

            if current_until > now:
                start = current_until
            else:
                start = now
        except ValueError:
            start = now
    else:
        start = now

    expiration = start + timedelta(days=days)

    db.execute(
        """
        UPDATE users
        SET plan = 'PREMIUM',
            premium_until = ?
        WHERE id = ?
        """,
        (expiration.isoformat(), user_id)
    )

    db.commit()


def premium_active(user):
    if not user:
        return False

    if user[3] != "PREMIUM":
        return False

    if not user[4]:
        return False

    try:
        expiration = datetime.fromisoformat(user[4])
        return expiration > datetime.now(timezone.utc)
    except ValueError:
        return False


def clean_expired_premium(user_id):
    user = get_user(user_id)

    if not user:
        return

    if user[3] == "PREMIUM" and user[4]:
        try:
            expiration = datetime.fromisoformat(user[4])

            if expiration <= datetime.now(timezone.utc):
                db.execute(
                    """
                    UPDATE users
                    SET plan = 'FREE',
                        premium_until = NULL
                    WHERE id = ?
                    """,
                    (user_id,)
                )
                db.commit()

        except ValueError:
            pass


# =========================================================
# TECLADO PRINCIPAL
# =========================================================

def main_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💎 PREMIUM",
                    callback_data="premium"
                ),
                InlineKeyboardButton(
                    text="💳 CRÉDITOS",
                    callback_data="credits"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 MI CUENTA",
                    callback_data="account"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧪 CHECK SANDBOX",
                    callback_data="check"
                )
            ]
        ]
    )


def admin_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 USUARIOS",
                    callback_data="admin_users"
                )
            ]
        ]
    )


# =========================================================
# START
# =========================================================

@dp.message(Command("start"))
async def start(message: Message):

    user_id = message.from_user.id
    username = message.from_user.username or ""

    add_user(user_id, username)

    await message.answer(
        "⚡ <b>BILL CYPHER CHK</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "👋 Bienvenido.\n\n"
        "💎 Premium disponible\n"
        "💳 Sistema de créditos\n"
        "🧪 Checker en modo sandbox\n\n"
        "Selecciona una opción:",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# =========================================================
# MI CUENTA
# =========================================================

@dp.message(Command("me"))
async def me(message: Message):

    user_id = message.from_user.id

    add_user(
        user_id,
        message.from_user.username or ""
    )

    clean_expired_premium(user_id)

    user = get_user(user_id)

    plan = user[3]

    if premium_active(user):
        plan_text = "💎 PREMIUM"
        expiration = datetime.fromisoformat(
            user[4]
        ).strftime("%d/%m/%Y %H:%M UTC")
    else:
        plan_text = "🆓 FREE"
        expiration = "No activo"

    await message.answer(
        "👤 <b>MI CUENTA</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Usuario: @{user[1] or 'sin_username'}\n"
        f"🆔 ID: <code>{user[0]}</code>\n"
        f"💎 Plan: {plan_text}\n"
        f"💳 Créditos: <b>{user[2]}</b>\n"
        f"📅 Expira: {expiration}\n"
        f"🟢 Estado: {user[5]}",
        parse_mode="HTML"
    )


# =========================================================
# CHECK SANDBOX
# =========================================================

async def run_check_animation(message: Message):

    frames = [
        (
            "⚡ <b>BILL CYPHER CHK</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "🔎 <b>Checking...</b>\n"
            "━━━━━━━━━━━━░░░░░\n"
            "⏳ 20%"
        ),
        (
            "⚡ <b>BILL CYPHER CHK</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "🔎 <b>Checking...</b>\n"
            "━━━━━━━━━━━━━━━━░░\n"
            "⏳ 45%"
        ),
        (
            "⚡ <b>BILL CYPHER CHK</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "🔄 <b>Processing...</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⏳ 70%"
        ),
        (
            "⚡ <b>BILL CYPHER CHK</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "⚙️ <b>Finishing...</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⏳ 90%"
        ),
    ]

    for frame in frames:

        try:
            await message.edit_text(
                frame,
                parse_mode="HTML"
            )
        except Exception:
            pass

        await asyncio.sleep(0.8)


@dp.message(Command("check"))
async def check(message: Message):

    user_id = message.from_user.id

    add_user(
        user_id,
        message.from_user.username or ""
    )

    clean_expired_premium(user_id)

    user = get_user(user_id)

    if user[2] <= 0:

        await message.answer(
            "❌ <b>Sin créditos</b>\n\n"
            "No tienes créditos disponibles.",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

        return

    # Descontar crédito
    db.execute(
        """
        UPDATE users
        SET credits = credits - 1
        WHERE id = ?
        """,
        (user_id,)
    )

    db.commit()

    # Mensaje inicial
    sent = await message.answer(
        "⚡ <b>BILL CYPHER CHK</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🔎 <b>Starting...</b>",
        parse_mode="HTML"
    )

    # Animación
    await run_check_animation(sent)

    await asyncio.sleep(0.5)

    await sent.edit_text(
        "⚡ <b>BILL CYPHER CHK</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🧪 <b>SANDBOX RESULT</b>\n\n"
        "✅ Test processed\n"
        "🟢 Simulation completed\n\n"
        "💳 Crédito utilizado: <b>1</b>\n\n"
        "⚠️ Este bot funciona únicamente "
        "con datos de prueba/sandbox.\n"
        "No verifica tarjetas reales.",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# =========================================================
# PREMIUM
# =========================================================

@dp.message(Command("premium"))
async def premium(message: Message):

    await message.answer(
        "💎 <b>PREMIUM</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⭐ Beneficios:\n\n"
        "⚡ Mayor cantidad de créditos\n"
        "🚀 Acceso prioritario\n"
        "🎨 Interfaz Premium\n"
        "📅 Plan con vencimiento\n\n"
        "Selecciona una opción:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💎 PREMIUM 30 DÍAS",
                        callback_data="premium_30"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 VOLVER",
                        callback_data="home"
                    )
                ]
            ]
        )
    )


# =========================================================
# CRÉDITOS
# =========================================================

@dp.message(Command("credits"))
async def credits(message: Message):

    await message.answer(
        "💳 <b>CRÉDITOS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Los créditos se utilizan para las "
        "pruebas del checker sandbox.\n\n"
        "📦 Paquetes disponibles próximamente.\n\n"
        "⚠️ Los créditos no habilitan validación "
        "de tarjetas reales.",
        parse_mode="HTML"
    )


# =========================================================
# CALLBACKS
# =========================================================

@dp.callback_query(F.data == "home")
async def callback_home(callback: CallbackQuery):

    await callback.message.edit_text(
        "⚡ <b>BILL CYPHER CHK</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Selecciona una opción:",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

    await callback.answer()


@dp.callback_query(F.data == "account")
async def callback_account(callback: CallbackQuery):

    user_id = callback.from_user.id

    add_user(
        user_id,
        callback.from_user.username or ""
    )

    clean_expired_premium(user_id)

    user = get_user(user_id)

    if premium_active(user):

        expiration = datetime.fromisoformat(
            user[4]
        ).strftime("%d/%m/%Y %H:%M UTC")

        plan = "💎 PREMIUM"

    else:

        expiration = "No activo"
        plan = "🆓 FREE"

    await callback.message.edit_text(
        "👤 <b>MI CUENTA</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 @{user[1] or 'sin_username'}\n"
        f"🆔 <code>{user[0]}</code>\n"
        f"💎 Plan: {plan}\n"
        f"💳 Créditos: <b>{user[2]}</b>\n"
        f"📅 Expira: {expiration}\n"
        f"🟢 Estado: {user[5]}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 VOLVER",
                        callback_data="home"
                    )
                ]
            ]
        )
    )

    await callback.answer()


@dp.callback_query(F.data == "premium")
async def callback_premium(callback: CallbackQuery):

    await callback.message.edit_text(
        "💎 <b>PREMIUM</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⭐ Premium incluye:\n\n"
        "⚡ Más créditos\n"
        "🚀 Prioridad\n"
        "🎨 Funciones Premium\n"
        "📅 30 días de duración\n\n"
        "Elige tu plan:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💎 PREMIUM 30 DÍAS",
                        callback_data="premium_30"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 VOLVER",
                        callback_data="home"
                    )
                ]
            ]
        )
    )

    await callback.answer()


@dp.callback_query(F.data == "credits")
async def callback_credits(callback: CallbackQuery):

    await callback.message.edit_text(
        "💳 <b>CRÉDITOS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Cada prueba sandbox utiliza 1 crédito.\n\n"
        "📦 Los paquetes de créditos se pueden "
        "activar desde el panel de administración.\n\n"
        "⚠️ Uso exclusivamente sandbox.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 VOLVER",
                        callback_data="home"
                    )
                ]
            ]
        )
    )

    await callback.answer()


@dp.callback_query(F.data == "check")
async def callback_check(callback: CallbackQuery):

    user_id = callback.from_user.id

    add_user(
        user_id,
        callback.from_user.username or ""
    )

    clean_expired_premium(user_id)

    user = get_user(user_id)

    if user[2] <= 0:

        await callback.answer(
            "❌ No tienes créditos.",
            show_alert=True
        )

        return

    # Descontar crédito
    db.execute(
        """
        UPDATE users
        SET credits = credits - 1
        WHERE id = ?
        """,
        (user_id,)
    )

    db.commit()

    await callback.answer()

    sent = await callback.message.answer(
        "⚡ <b>BILL CYPHER CHK</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🔎 <b>Starting...</b>",
        parse_mode="HTML"
    )

    await run_check_animation(sent)

    await asyncio.sleep(0.5)

    await sent.edit_text(
        "⚡ <b>BILL CYPHER CHK</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🧪 <b>SANDBOX RESULT</b>\n\n"
        "✅ Test processed\n"
        "🟢 Simulation completed\n\n"
        "💳 Crédito utilizado: <b>1</b>\n\n"
        "⚠️ No se procesan ni validan "
        "tarjetas reales.",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


@dp.callback_query(F.data == "premium_30")
async def callback_premium_30(callback: CallbackQuery):

    await callback.answer(
        "💎 El pago Premium se puede conectar con Telegram Stars.",
        show_alert=True
    )


# =========================================================
# ADMIN
# =========================================================

def is_admin(user_id):

    return ADMIN_ID != 0 and user_id == ADMIN_ID


@dp.message(Command("admin"))
async def admin(message: Message):

    if not is_admin(message.from_user.id):

        await message.answer("❌ No autorizado.")
        return

    await message.answer(
        "👑 <b>ADMIN PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Comandos disponibles:\n\n"
        "<code>/addcredit ID CANTIDAD</code>\n"
        "<code>/premiumadd ID DIAS</code>\n"
        "<code>/users</code>",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


@dp.message(Command("addcredit"))
async def addcredit(message: Message):

    if not is_admin(message.from_user.id):

        await message.answer("❌ No autorizado.")
        return

    parts = message.text.split()

    if len(parts) != 3:

        await message.answer(
            "Uso:\n"
            "<code>/addcredit ID CANTIDAD</code>",
            parse_mode="HTML"
        )

        return

    try:

        user_id = int(parts[1])
        amount = int(parts[2])

    except ValueError:

        await message.answer(
            "❌ ID o cantidad inválida."
        )

        return

    user = get_user(user_id)

    if not user:

        await message.answer(
            "❌ Usuario no encontrado."
        )

        return

    update_credits(user_id, amount)

    await message.answer(
        "✅ <b>Créditos añadidos</b>\n\n"
        f"👤 ID: <code>{user_id}</code>\n"
        f"💳 Cantidad: <b>+{amount}</b>",
        parse_mode="HTML"
    )


@dp.message(Command("premiumadd"))
async def premiumadd(message: Message):

    if not is_admin(message.from_user.id):

        await message.answer("❌ No autorizado.")
        return

    parts = message.text.split()

    if len(parts) != 3:

        await message.answer(
            "Uso:\n"
            "<code>/premiumadd ID DIAS</code>",
            parse_mode="HTML"
        )

        return

    try:

        user_id = int(parts[1])
        days = int(parts[2])

    except ValueError:

        await message.answer(
            "❌ ID o días inválidos."
        )

        return

    user = get_user(user_id)

    if not user:

        await message.answer(
            "❌ Usuario no encontrado."
        )

        return

    activate_premium(user_id, days)

    # Premium también recibe créditos
    update_credits(user_id, 50)

    await message.answer(
        "💎 <b>PREMIUM ACTIVADO</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 ID: <code>{user_id}</code>\n"
        f"📅 Duración: <b>{days} días</b>\n"
        "💳 Bono: <b>+50 créditos</b>",
        parse_mode="HTML"
    )


@dp.message(Command("users"))
async def users(message: Message):

    if not is_admin(message.from_user.id):

        await message.answer("❌ No autorizado.")
        return

    total = db.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    premium = db.execute(
        "SELECT COUNT(*) FROM users WHERE plan = 'PREMIUM'"
    ).fetchone()[0]

    await message.answer(
        "👑 <b>ESTADÍSTICAS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Usuarios: <b>{total}</b>\n"
        f"💎 Premium: <b>{premium}</b>",
        parse_mode="HTML"
    )


# =========================================================
# HEALTH CHECK
# =========================================================

async def health(request):

    return web.Response(text="OK")


# =========================================================
# WEBHOOK
# =========================================================

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

    await dp.feed_update(
        bot,
        update
    )

    return web.Response(text="ok")


async def on_startup(app):

    await bot.set_webhook(
        url=f"{PUBLIC_URL}/telegram/{WEBHOOK_SECRET}",
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True
    )


async def on_cleanup(app):

    await bot.delete_webhook()

    await bot.session.close()


# =========================================================
# APP
# =========================================================

app = web.Application()

app.router.add_get(
    "/",
    health
)

app.router.add_post(
    f"/telegram/{WEBHOOK_SECRET}",
    webhook
)

app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)


if __name__ == "__main__":

    web.run_app(
        app,
        host="0.0.0.0",
        port=PORT
    )
