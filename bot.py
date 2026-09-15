import os
import time
import sqlite3
import requests
from flask import Flask, request

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "telegram-secret")
PUBLIC_URL = os.environ["RENDER_EXTERNAL_URL"]

app = Flask(__name__)

DB = "bot.db"


def db():
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            credits INTEGER DEFAULT 5,
            plan TEXT DEFAULT 'FREE'
        )
    """)
    conn.commit()
    return conn


def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    if keyboard:
        data["reply_markup"] = {
            "inline_keyboard": keyboard
        }

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json=data,
        timeout=15
    )


def edit_message(chat_id, message_id, text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
        json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        },
        timeout=15
    )


def answer_callback(callback_id):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
        json={"callback_query_id": callback_id},
        timeout=15
    )


def get_user(user):
    conn = db()
    row = conn.execute(
        "SELECT id, username, credits, plan FROM users WHERE id=?",
        (user["id"],)
    ).fetchone()

    if not row:
        conn.execute(
            "INSERT INTO users (id, username) VALUES (?, ?)",
            (user["id"], user.get("username", ""))
        )
        conn.commit()
        row = (
            user["id"],
            user.get("username", ""),
            5,
            "FREE"
        )

    conn.close()
    return row


def main_menu():
    return [
        [
            {"text": "🔎 Check Sandbox", "callback_data": "check"},
            {"text": "👤 Mi cuenta", "callback_data": "account"}
        ],
        [
            {"text": "⭐ Premium", "callback_data": "premium"},
            {"text": "💳 Créditos", "callback_data": "credits"}
        ]
    ]


def process_update(update):
    if "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        message_id = cb["message"]["message_id"]
        data = cb["data"]

        answer_callback(cb["id"])

        user = get_user(cb["from"])

        if data == "account":
            send_message(
                chat_id,
                f"""👤 <b>MI CUENTA</b>

🆔 ID: <code>{user[0]}</code>
👤 Usuario: @{user[1] or 'sin_username'}
💎 Plan: <b>{user[3]}</b>
💰 Créditos: <b>{user[2]}</b>""",
                main_menu()
            )

        elif data == "credits":
            send_message(
                chat_id,
                f"""💳 <b>TUS CRÉDITOS</b>

💰 Disponibles: <b>{user[2]}</b>

Los créditos se utilizan únicamente
para las funciones de <b>Sandbox</b>.""",
                main_menu()
            )

        elif data == "premium":
            send_message(
                chat_id,
                """⭐ <b>PREMIUM</b>

🔥 Más créditos
⚡ Interfaz Premium
🎯 Funciones Sandbox adicionales

Esta versión no procesa ni valida
tarjetas reales.""",
                main_menu()
            )

        elif data == "check":
            if user[2] <= 0:
                send_message(
                    chat_id,
                    "❌ No tienes créditos disponibles.",
                    main_menu()
                )
                return

            conn = db()
            conn.execute(
                "UPDATE users SET credits = credits - 1 WHERE id=?",
                (user[0],)
            )
            conn.commit()
            conn.close()

            msg = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "🔎 <b>Iniciando análisis Sandbox...</b>",
                    "parse_mode": "HTML"
                },
                timeout=15
            ).json()

            mid = msg["result"]["message_id"]

            steps = [
                "🔎 <b>Iniciando análisis Sandbox...</b>",
                "🔄 <b>Consultando datos de prueba...</b>",
                "📡 <b>Procesando información Sandbox...</b>",
                "🧩 <b>Analizando resultado...</b>",
                "✅ <b>ANÁLISIS SANDBOX COMPLETADO</b>\n\n"
                "🟢 Resultado: <b>TEST</b>\n"
                "🧪 Modo: <b>Sandbox</b>\n\n"
                "⚠️ No se procesó ninguna tarjeta real."
            ]

            for step in steps:
                edit_message(chat_id, mid, step)
                time.sleep(1)

            send_message(chat_id, "🏠 Menú principal:", main_menu())

        return

    if "message" not in update:
        return

    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    user = get_user(message["from"])
if text.startswith("/addcredit"):
    if sender_id != ADMIN_ID:
        send_message(chat_id, "⛔ No tienes permiso.")
        return

    partes = text.split()

    if len(partes) != 3:
        send_message(chat_id, "❌ Usa: /addcredit ID CANTIDAD")
        return

    try:
        usuario_id = int(partes[1])
        cantidad = int(partes[2])
    except ValueError:
        send_message(chat_id, "❌ ID y cantidad deben ser números.")
        return

    conn = db()

    conn.execute(
        "INSERT OR IGNORE INTO users (id, username, credits, plan) VALUES (?, '', 0, 'FREE')",
        (usuario_id,)
    )

    conn.execute(
        "UPDATE users SET credits = credits + ? WHERE id = ?",
        (cantidad, usuario_id)
    )

    conn.commit()
    conn.close()

    send_message(
        chat_id,
        f"✅ Se agregaron {cantidad} créditos a {usuario_id}."
    )
    return
    if text.startswith("/start"):
        send_message(
            chat_id,
            f"""<b>⚡ BILL CYPHER CHK ⚡</b>

👋 Bienvenido, @{user[1] or 'usuario'}

💎 Plan: <b>{user[3]}</b>
💰 Créditos: <b>{user[2]}</b>

🔐 Sistema de pruebas Sandbox

Selecciona una opción:""",
            main_menu()
        )

    elif text == "/me":
        send_message(
            chat_id,
            f"""👤 <b>MI CUENTA</b>

🆔 ID: <code>{user[0]}</code>
👤 Usuario: @{user[1] or 'sin_username'}
💎 Plan: <b>{user[3]}</b>
💰 Créditos: <b>{user[2]}</b>""",
            main_menu()
        )

    elif text == "/check":
        send_message(
            chat_id,
            "👇 Pulsa <b>Check Sandbox</b> para iniciar.",
            main_menu()
        )

    else:
        send_message(
            chat_id,
            "🤖 Usa /start para abrir el menú.",
            main_menu()
        )


@app.route("/")
def home():
    return "OK", 200


@app.route("/telegram/<secret>", methods=["POST"])
def telegram_webhook(secret):
    if secret != WEBHOOK_SECRET:
        return "Unauthorized", 401

    update = request.get_json(silent=True)

    if update:
        process_update(update)

    return "OK", 200


def set_webhook():
    url = f"{PUBLIC_URL}/telegram/{WEBHOOK_SECRET}"

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": url},
        timeout=15
    )


if __name__ == "__main__":
    set_webhook()

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
