import os
import time
import sqlite3
import threading
import requests
from flask import Flask, request

# =========================
# CONFIGURACIÓN
# =========================

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

PORT = int(os.environ.get("PORT", "10000"))

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

DB = "bot.db"

app = Flask(__name__)


# =========================
# BASE DE DATOS
# =========================

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


def get_user(user_id, username=""):
    conn = db()

    row = conn.execute(
        "SELECT id, username, credits, plan FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if not row:
        conn.execute(
            """
            INSERT INTO users (id, username, credits, plan)
            VALUES (?, ?, 5, 'FREE')
            """,
            (user_id, username)
        )
        conn.commit()

        row = conn.execute(
            "SELECT id, username, credits, plan FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

    conn.close()
    return row


# =========================
# TELEGRAM
# =========================

def telegram(method, data=None):
    try:
        response = requests.post(
            f"{API}/{method}",
            json=data or {},
            timeout=40
        )
        return response.json()
    except Exception as e:
        print("Telegram error:", e)
        return {}


def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = {
            "inline_keyboard": keyboard
        }

    return telegram("sendMessage", data)


def edit_message(chat_id, message_id, text):
    return telegram(
        "editMessageText",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        }
    )


def answer_callback(callback_id):
    telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )


# =========================
# MENÚ
# =========================

def menu():
    return [
        [
            {
                "text": "🔎 Check Sandbox",
                "callback_data": "check"
            },
            {
                "text": "👤 Mi cuenta",
                "callback_data": "account"
            }
        ],
        [
            {
                "text": "⭐ Premium",
                "callback_data": "premium"
            },
            {
                "text": "💳 Créditos",
                "callback_data": "credits"
            }
        ]
    ]


# =========================
# CUENTA
# =========================

def account(chat_id, user_id, username):
    user = get_user(user_id, username)

    plan = user[3]
    credits = user[2]

    send_message(
        chat_id,
        "👤 MI CUENTA\n\n"
        f"🆔 ID: {user_id}\n"
        f"👤 Usuario: @{username if username else 'sin_username'}\n"
        f"💳 Créditos: {credits}\n"
        f"⭐ Plan: {plan}",
        menu()
    )


# =========================
# CRÉDITOS
# =========================

def credits(chat_id, user_id, username):
    user = get_user(user_id, username)

    send_message(
        chat_id,
        "💳 TUS CRÉDITOS\n\n"
        f"💰 Disponibles: {user[2]}\n\n"
        "Los créditos se utilizan únicamente "
        "para las funciones de Sandbox.",
        menu()
    )


# =========================
# PREMIUM
# =========================

def premium(chat_id):
    send_message(
        chat_id,
        "⭐ PREMIUM\n\n"
        "🔥 Más créditos\n"
        "⚡ Interfaz Premium\n"
        "🎯 Funciones Sandbox adicionales\n\n"
        "Esta versión no procesa ni valida tarjetas reales.",
        menu()
    )


# =========================
# CHECK SANDBOX
# =========================

def sandbox_check(chat_id, user_id, username):
    user = get_user(user_id, username)

    if user[2] <= 0:
        send_message(
            chat_id,
            "❌ No tienes créditos disponibles.\n\n"
            "Usa la opción 💳 Créditos.",
            menu()
        )
        return

    conn = db()

    conn.execute(
        "UPDATE users SET credits = credits - 1 WHERE id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()

    msg = send_message(
        chat_id,
        "🔎 CHECK SANDBOX\n\n"
        "⏳ Iniciando prueba..."
    )

    message_id = msg.get("result", {}).get("message_id")

    if not message_id:
        return

    time.sleep(1)

    edit_message(
        chat_id,
        message_id,
        "🔎 CHECK SANDBOX\n\n"
        "⏳ Ejecutando simulación..."
    )

    time.sleep(1)

    edit_message(
        chat_id,
        message_id,
        "🔎 CHECK SANDBOX\n\n"
        "✅ Simulación completada.\n\n"
        "ℹ️ Resultado de prueba Sandbox.\n"
        "No se procesó ninguna tarjeta real."
    )


# =========================
# COMANDOS ADMIN
# =========================

def admin_add_credit(chat_id, sender_id, text):

    if sender_id != ADMIN_ID:
        send_message(
            chat_id,
            "⛔ No tienes permiso para usar este comando."
        )
        return

    parts = text.split()

    if len(parts) != 3:
        send_message(
            chat_id,
            "❌ Formato incorrecto.\n\n"
            "Usa:\n"
            "/addcredit ID CANTIDAD\n\n"
            "Ejemplo:\n"
            "/addcredit 5320997298 100"
        )
        return

    try:
        target_id = int(parts[1])
        amount = int(parts[2])

        if amount <= 0:
            raise ValueError

    except ValueError:
        send_message(
            chat_id,
            "❌ El ID y la cantidad deben ser números positivos."
        )
        return

    conn = db()

    conn.execute(
        """
        INSERT OR IGNORE INTO users
        (id, username, credits, plan)
        VALUES (?, '', 0, 'FREE')
        """,
        (target_id,)
    )

    conn.execute(
        """
        UPDATE users
        SET credits = credits + ?
        WHERE id = ?
        """,
        (amount, target_id)
    )

    conn.commit()
    conn.close()

    send_message(
        chat_id,
        "✅ CRÉDITOS AGREGADOS\n\n"
        f"🆔 Usuario: {target_id}\n"
        f"💳 Créditos añadidos: {amount}"
    )


def admin_premium(chat_id, sender_id, text):

    if sender_id != ADMIN_ID:
        send_message(
            chat_id,
            "⛔ No tienes permiso para usar este comando."
        )
        return

    parts = text.split()

    if len(parts) != 2:
        send_message(
            chat_id,
            "❌ Usa:\n\n"
            "/premiumadd ID"
        )
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        send_message(
            chat_id,
            "❌ El ID debe ser numérico."
        )
        return

    conn = db()

    conn.execute(
        """
        INSERT OR IGNORE INTO users
        (id, username, credits, plan)
        VALUES (?, '', 0, 'FREE')
        """,
        (target_id,)
    )

    conn.execute(
        """
        UPDATE users
        SET plan = 'PREMIUM'
        WHERE id = ?
        """,
        (target_id,)
    )

    conn.commit()
    conn.close()

    send_message(
        chat_id,
        "⭐ PREMIUM ACTIVADO\n\n"
        f"🆔 Usuario: {target_id}\n"
        "⭐ Plan: PREMIUM"
    )


def admin_premium_off(chat_id, sender_id, text):

    if sender_id != ADMIN_ID:
        send_message(
            chat_id,
            "⛔ No tienes permiso para usar este comando."
        )
        return

    parts = text.split()

    if len(parts) != 2:
        send_message(
            chat_id,
            "❌ Usa:\n\n"
            "/premiumoff ID"
        )
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        send_message(
            chat_id,
            "❌ El ID debe ser numérico."
        )
        return

    conn = db()

    conn.execute(
        """
        UPDATE users
        SET plan = 'FREE'
        WHERE id = ?
        """,
        (target_id,)
    )

    conn.commit()
    conn.close()

    send_message(
        chat_id,
        f"✅ Premium desactivado para {target_id}."
    )


def admin_help(chat_id, sender_id):

    if sender_id != ADMIN_ID:
        send_message(
            chat_id,
            "⛔ No tienes permiso."
        )
        return

    send_message(
        chat_id,
        "🛠 ADMIN\n\n"
        "/addcredit ID CANTIDAD\n"
        "/premiumadd ID\n"
        "/premiumoff ID\n\n"
        "Ejemplos:\n\n"
        "/addcredit 5320997298 100\n"
        "/premiumadd 5320997298"
    )


# =========================
# PROCESAR MENSAJES
# =========================

def process_update(update):

    # =====================
    # BOTONES
    # =====================

    callback = update.get("callback_query")

    if callback:

        answer_callback(callback["id"])

        data = callback.get("data", "")
        message = callback.get("message", {})

        chat_id = message.get("chat", {}).get("id")
        user = callback.get("from", {})

        user_id = user.get("id")
        username = user.get("username", "")

        if data == "check":
            sandbox_check(
                chat_id,
                user_id,
                username
            )

        elif data == "account":
            account(
                chat_id,
                user_id,
                username
            )

        elif data == "credits":
            credits(
                chat_id,
                user_id,
                username
            )

        elif data == "premium":
            premium(chat_id)

        return

    # =====================
    # MENSAJE
    # =====================

    message = update.get("message")

    if not message:
        return

    chat_id = message.get("chat", {}).get("id")

    sender = message.get("from", {})

    sender_id = sender.get("id", 0)
    username = sender.get("username", "")

    text = message.get("text", "").strip()

    if not text:
        return

    # =====================
    # ADMIN
    # =====================

    if text.startswith("/addcredit"):
        admin_add_credit(
            chat_id,
            sender_id,
            text
        )
        return

    if text.startswith("/premiumadd"):
        admin_premium(
            chat_id,
            sender_id,
            text
        )
        return

    if text.startswith("/premiumoff"):
        admin_premium_off(
            chat_id,
            sender_id,
            text
        )
        return

    if text.startswith("/admin"):
        admin_help(
            chat_id,
            sender_id
        )
        return

    # =====================
    # START
    # =====================

    if text.startswith("/start"):

        get_user(
            sender_id,
            username
        )

        send_message(
            chat_id,
            "🤖 BILL CYPHER CHK\n\n"
            "Bienvenido.\n\n"
            "Selecciona una opción:",
            menu()
        )

        return

    # =====================
    # ME
    # =====================

    if text.startswith("/me"):

        account(
            chat_id,
            sender_id,
            username
        )

        return

    # =====================
    # CHECK
    # =====================

    if text == "/check":

        sandbox_check(
            chat_id,
            sender_id,
            username
        )

        return

    # =====================
    # PREMIUM
    # =====================

    if text.startswith("/premium"):

        premium(chat_id)

        return

    # =====================
    # CRÉDITOS
    # =====================

    if text.startswith("/credits"):

        credits(
            chat_id,
            sender_id,
            username
        )

        return

    # =====================
    # MENSAJE DESCONOCIDO
    # =====================

    send_message(
        chat_id,
        "🤖 Usa /start para abrir el menú."
    )


# =========================
# WEB
# =========================

@app.route("/")
def home():
    return "Bill Cypher Chk OK", 200


@app.route("/health")
def health():
    return "OK", 200


# =========================
# POLLING
# =========================

def polling():

    print("Iniciando bot...")

    # Elimina cualquier webhook anterior
    telegram(
        "deleteWebhook",
        {
            "drop_pending_updates": True
        }
    )

    offset = 0

    while True:

        try:

            result = telegram(
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": 30
                }
            )

            updates = result.get("result", [])

            for update in updates:

                offset = update["update_id"] + 1

                try:
                    process_update(update)
                except Exception as e:
                    print("Error procesando update:", e)

        except Exception as e:

            print("Error polling:", e)
            time.sleep(5)


# =========================
# INICIO
# =========================

if __name__ == "__main__":

    thread = threading.Thread(
        target=polling,
        daemon=True
    )

    thread.start()

    app.run(
        host="0.0.0.0",
        port=PORT
    )
