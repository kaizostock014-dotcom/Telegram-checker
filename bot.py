import os
import time
import sqlite3
import threading
import requests
from flask import Flask

# ============================================================
# BILL CYPHER CHK — VERSION 2.0
# ============================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DIAMOND_ID = ADMIN_ID
PORT = int(os.environ.get("PORT", "10000"))

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DB = "bot.db"

app = Flask(__name__)


# ============================================================
# DATABASE
# ============================================================

def db():
    conn = sqlite3.connect(DB, check_same_thread=False)

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
            INSERT INTO users
            (id, username, credits, plan)
            VALUES (?, ?, 5, 'FREE')
            """,
            (user_id, username)
        )
        conn.commit()
    else:
        conn.execute(
            "UPDATE users SET username = ? WHERE id = ?",
            (username, user_id)
        )
        conn.commit()

    row = conn.execute(
        "SELECT id, username, credits, plan FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    conn.close()

    return row


# ============================================================
# TELEGRAM API
# ============================================================

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
        "text": text,
        "parse_mode": "HTML"
    }

    if keyboard:
        data["reply_markup"] = {
            "inline_keyboard": keyboard
        }

    return telegram("sendMessage", data)


def edit_message(chat_id, message_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }

    if keyboard:
        data["reply_markup"] = {
            "inline_keyboard": keyboard
        }

    return telegram("editMessageText", data)


def answer_callback(callback_id):
    telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )


# ============================================================
# MENUS
# ============================================================

def main_menu(user_id):

    buttons = [
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
        ],

        [
            {
                "text": "⚡ Command Panel",
                "callback_data": "cmds"
            }
        ]
    ]

    # SOLO EL PROPIETARIO VE DIAMOND
    if user_id == DIAMOND_ID and DIAMOND_ID != 0:

        buttons.append([
            {
                "text": "💎 Diamond",
                "callback_data": "diamond"
            }
        ])

    return buttons


def panel_menu(user_id):

    buttons = [
        [
            {
                "text": "🔎 Sandbox",
                "callback_data": "check"
            },
            {
                "text": "⚙️ Tools",
                "callback_data": "tools"
            }
        ],

        [
            {
                "text": "👤 Account",
                "callback_data": "account"
            },
            {
                "text": "💳 Credits",
                "callback_data": "credits"
            }
        ],

        [
            {
                "text": "⭐ Premium",
                "callback_data": "premium"
            }
        ]
    ]

    if user_id == DIAMOND_ID and DIAMOND_ID != 0:

        buttons.append([
            {
                "text": "💎 Diamond",
                "callback_data": "diamond"
            }
        ])

    buttons.append([
        {
            "text": "📚 References ↗",
            "callback_data": "references"
        },
        {
            "text": "‼️ Updates ↗",
            "callback_data": "updates"
        }
    ])

    buttons.append([
        {
            "text": "🏠 Inicio",
            "callback_data": "home"
        }
    ])

    return buttons


# ============================================================
# START / WELCOME
# ============================================================

def welcome(chat_id, user_id, username):

    get_user(user_id, username)

    name = username if username else "Usuario"

    text = (
        f"⚡ <b>Hello {name}</b>, Welcome to\n"
        f"<b>⚡ BILL CYPHER CHK ⚡</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "➤ Usa <b>/cmds</b> para abrir el\n"
        "panel de comandos interactivo ◀\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "☁️ <b>Bot Version: 2.0</b> ⚡\n\n"

        "🟢 API Status: <b>Online</b>\n\n"

        "ℹ️ Sistema de pruebas Sandbox.\n"
        "No se procesan tarjetas reales."
    )

    keyboard = [
        [
            {
                "text": "📚 References ↗",
                "callback_data": "references"
            },
            {
                "text": "‼️ Updates ↗",
                "callback_data": "updates"
            }
        ],

        [
            {
                "text": "⚡ Menú",
                "callback_data": "cmds"
            }
        ]
    ]

    send_message(
        chat_id,
        text,
        keyboard
    )


# ============================================================
# COMMAND PANEL
# ============================================================

def command_panel(chat_id, user_id):

    text = (
        "⚡ <b>BILL CYPHER CHK | COMMAND PANEL</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "➤ <b>Sandbox:</b> Online 🟢\n"
        "➤ <b>Tools:</b> 12\n"
        "➤ <b>API Status:</b> Online 🟢\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "☁️ <b>Bot Version: 2.0</b> ⚡"
    )

    send_message(
        chat_id,
        text,
        panel_menu(user_id)
    )


# ============================================================
# ACCOUNT
# ============================================================

def account(chat_id, user_id, username):

    user = get_user(
        user_id,
        username
    )

    plan = user[3]
    credits = user[2]

    text = (
        "👤 <b>MI CUENTA</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Usuario: @{username if username else 'sin_username'}\n"
        f"💳 Créditos: <b>{credits}</b>\n"
        f"⭐ Plan: <b>{plan}</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━"
    )

    send_message(
        chat_id,
        text,
        main_menu(user_id)
    )


# ============================================================
# CREDITS
# ============================================================

def credits(chat_id, user_id, username):

    user = get_user(
        user_id,
        username
    )

    text = (
        "💳 <b>TUS CRÉDITOS</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"💰 Disponibles: <b>{user[2]}</b>\n\n"

        "Los créditos se utilizan únicamente\n"
        "para funciones de Sandbox.\n\n"

        "━━━━━━━━━━━━━━━━━━━━"
    )

    send_message(
        chat_id,
        text,
        main_menu(user_id)
    )


# ============================================================
# PREMIUM
# ============================================================

def premium(chat_id, user_id):

    user = get_user(user_id)

    if user[3] == "PREMIUM":

        status = "✅ Premium está activo."

    else:

        status = "🔒 Premium no está activo."

    text = (
        "⭐ <b>BILL CYPHER PREMIUM</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "⚡ Interfaz Premium\n"
        "🚀 Funciones Sandbox adicionales\n"
        "💳 Sistema de créditos\n"
        "🎯 Acceso a herramientas Premium\n\n"

        f"{status}\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "ℹ️ Premium no procesa tarjetas reales."
    )

    send_message(
        chat_id,
        text,
        main_menu(user_id)
    )


# ============================================================
# DIAMOND — SOLO OWNER
# ============================================================

def diamond(chat_id, user_id):

    if user_id != DIAMOND_ID or DIAMOND_ID == 0:

        send_message(
            chat_id,
            "⛔ <b>ACCESS DENIED</b>\n\n"
            "Esta sección es exclusiva del propietario."
        )

        return

    text = (
        "💎 <b>BILL CYPHER — DIAMOND</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "👑 <b>OWNER ACCESS</b>\n\n"

        "💎 Diamond: <b>ACTIVADO</b>\n"
        "🛡 Owner: <b>VERIFIED</b>\n"
        "🟢 API: <b>ONLINE</b>\n"
        "🔎 Sandbox: <b>ACTIVE</b>\n"
        "🛠 Admin: <b>ACTIVE</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "🔐 Panel privado del propietario."
    )

    keyboard = [

        [
            {
                "text": "💳 + Créditos",
                "callback_data": "diamond_credit"
            },

            {
                "text": "⭐ Premium",
                "callback_data": "diamond_premium"
            }
        ],

        [
            {
                "text": "📊 Estadísticas",
                "callback_data": "diamond_stats"
            }
        ],

        [
            {
                "text": "⬅️ Volver",
                "callback_data": "cmds"
            }
        ]
    ]

    send_message(
        chat_id,
        text,
        keyboard
    )


# ============================================================
# SANDBOX ANIMATION
# ============================================================

def sandbox_check(chat_id, user_id, username):

    user = get_user(
        user_id,
        username
    )

    if user[2] <= 0:

        send_message(
            chat_id,

            "❌ <b>SIN CRÉDITOS</b>\n\n"
            "No tienes créditos disponibles.",

            main_menu(user_id)
        )

        return

    # CONSUMIR 1 CRÉDITO

    conn = db()

    conn.execute(
        """
        UPDATE users
        SET credits = credits - 1
        WHERE id = ?
        """,
        (user_id,)
    )

    conn.commit()
    conn.close()

    msg = send_message(
        chat_id,

        "🔎 <b>CHECK SANDBOX</b>\n\n"
        "⏳ <i>Iniciando...</i>"
    )

    message_id = msg.get(
        "result",
        {}
    ).get(
        "message_id"
    )

    if not message_id:
        return

    animations = [

        (
            "🔎 <b>CHECK SANDBOX</b>\n\n"
            "⏳ <i>Iniciando...</i>"
        ),

        (
            "🔎 <b>CHECK SANDBOX</b>\n\n"
            "⚡ <i>Cargando módulo...</i>"
        ),

        (
            "🔎 <b>CHECK SANDBOX</b>\n\n"
            "🔄 <i>Ejecutando simulación...</i>"
        ),

        (
            "🔎 <b>CHECK SANDBOX</b>\n\n"
            "⚡ <i>Analizando datos de prueba...</i>"
        ),

        (
            "🔎 <b>CHECK SANDBOX</b>\n\n"
            "🟢 <i>Finalizando...</i>"
        ),

        (
            "🔎 <b>CHECK SANDBOX</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ <b>SIMULACIÓN COMPLETADA</b>\n\n"
            "ℹ️ Resultado de prueba Sandbox.\n"
            "🛡️ No se procesó ninguna tarjeta real.\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
    ]

    for animation in animations:

        edit_message(
            chat_id,
            message_id,
            animation
        )

        time.sleep(0.8)

    edit_message(
        chat_id,
        message_id,
        animations[-1],
        main_menu(user_id)
    )


# ============================================================
# REFERENCES
# ============================================================

def references(chat_id, user_id):

    text = (
        "📚 <b>BILL CYPHER | REFERENCES</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "⚡ Información del proyecto\n"
        "📖 Referencias\n"
        "🛡️ Sandbox\n"
        "⚙️ Herramientas del bot\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "☁️ Version 2.0"
    )

    send_message(
        chat_id,
        text,
        main_menu(user_id)
    )


# ============================================================
# UPDATES
# ============================================================

def updates(chat_id, user_id):

    text = (
        "‼️ <b>BILL CYPHER | UPDATES</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "🆕 Version 2.0\n\n"

        "• ⚡ Nuevo Command Panel\n"
        "• 🔄 Animaciones\n"
        "• 🔎 Sandbox\n"
        "• ⭐ Premium\n"
        "• 💎 Diamond Owner\n"
        "• 💳 Sistema de créditos\n"
        "• 🛠 Panel administrativo\n\n"

        "━━━━━━━━━━━━━━━━━━━━"
    )

    send_message(
        chat_id,
        text,
        main_menu(user_id)
    )


# ============================================================
# TOOLS
# ============================================================

def tools(chat_id, user_id):

    text = (
        "⚙️ <b>TOOLS</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "🔎 Sandbox\n"
        "👤 Account\n"
        "💳 Credits\n"
        "⭐ Premium\n"
        "📊 Statistics\n\n"

        "🟢 Status: Online\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "ℹ️ Herramientas disponibles únicamente\n"
        "para funciones permitidas de prueba."
    )

    send_message(
        chat_id,
        text,
        main_menu(user_id)
    )


# ============================================================
# DIAMOND CREDIT TOOL
# ============================================================

def diamond_credit(chat_id, user_id):

    if user_id != DIAMOND_ID:

        send_message(
            chat_id,
            "⛔ Acceso restringido."
        )

        return

    send_message(
        chat_id,

        "💳 <b>DIAMOND | CREDIT MANAGER</b>\n\n"

        "Usa:\n\n"

        "<code>/addcredit ID CANTIDAD</code>\n\n"

        "Ejemplo:\n"

        "<code>/addcredit 123456789 100</code>",

        [
            [
                {
                    "text": "⬅️ Diamond",
                    "callback_data": "diamond"
                }
            ]
        ]
    )


# ============================================================
# DIAMOND PREMIUM TOOL
# ============================================================

def diamond_premium(chat_id, user_id):

    if user_id != DIAMOND_ID:

        send_message(
            chat_id,
            "⛔ Acceso restringido."
        )

        return

    send_message(
        chat_id,

        "⭐ <b>DIAMOND | PREMIUM MANAGER</b>\n\n"

        "Activar:\n"
        "<code>/premiumadd ID</code>\n\n"

        "Desactivar:\n"
        "<code>/premiumoff ID</code>",

        [
            [
                {
                    "text": "⬅️ Diamond",
                    "callback_data": "diamond"
                }
            ]
        ]
    )


# ============================================================
# DIAMOND STATISTICS
# ============================================================

def diamond_stats(chat_id, user_id):

    if user_id != DIAMOND_ID:

        send_message(
            chat_id,
            "⛔ Acceso restringido."
        )

        return

    conn = db()

    total_users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    premium_users = conn.execute(
        "SELECT COUNT(*) FROM users WHERE plan = 'PREMIUM'"
    ).fetchone()[0]

    total_credits = conn.execute(
        "SELECT COALESCE(SUM(credits), 0) FROM users"
    ).fetchone()[0]

    conn.close()

    text = (
        "📊 <b>DIAMOND STATISTICS</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"👥 Usuarios: <b>{total_users}</b>\n"
        f"⭐ Premium: <b>{premium_users}</b>\n"
        f"💳 Créditos: <b>{total_credits}</b>\n\n"

        "🟢 API: Online\n\n"

        "━━━━━━━━━━━━━━━━━━━━"
    )

    send_message(
        chat_id,
        text,

        [
            [
                {
                    "text": "⬅️ Diamond",
                    "callback_data": "diamond"
                }
            ]
        ]
    )


# ============================================================
# ADMIN — ADD CREDIT
# ============================================================

def admin_add_credit(chat_id, sender_id, text):

    if sender_id != ADMIN_ID:

        send_message(
            chat_id,
            "⛔ No tienes permiso."
        )

        return

    parts = text.split()

    if len(parts) != 3:

        send_message(
            chat_id,

            "❌ <b>Formato incorrecto</b>\n\n"
            "<code>/addcredit ID CANTIDAD</code>"
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
            "❌ ID y cantidad deben ser números positivos."
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

        "✅ <b>CRÉDITOS AGREGADOS</b>\n\n"

        f"🆔 Usuario: <code>{target_id}</code>\n"
        f"💳 Añadidos: <b>{amount}</b>"
    )


# ============================================================
# ADMIN — PREMIUM ON
# ============================================================

def admin_premium(chat_id, sender_id, text):

    if sender_id != ADMIN_ID:

        send_message(
            chat_id,
            "⛔ No tienes permiso."
        )

        return

    parts = text.split()

    if len(parts) != 2:

        send_message(
            chat_id,
            "❌ Usa:\n<code>/premiumadd ID</code>"
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

        "⭐ <b>PREMIUM ACTIVADO</b>\n\n"
        f"🆔 Usuario: <code>{target_id}</code>\n"
        "⭐ Plan: PREMIUM"
    )


# ============================================================
# ADMIN — PREMIUM OFF
# ============================================================

def admin_premium_off(chat_id, sender_id, text):

    if sender_id != ADMIN_ID:

        send_message(
            chat_id,
            "⛔ No tienes permiso."
        )

        return

    parts = text.split()

    if len(parts) != 2:

        send_message(
            chat_id,
            "❌ Usa:\n<code>/premiumoff ID</code>"
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

        "✅ <b>PREMIUM DESACTIVADO</b>\n\n"
        f"Usuario: <code>{target_id}</code>"
    )


# ============================================================
# ADMIN PANEL
# ============================================================

def admin_help(chat_id, sender_id):

    if sender_id != ADMIN_ID:

        send_message(
            chat_id,
            "⛔ No tienes permiso."
        )

        return

    text = (
        "💎 <b>OWNER / ADMIN PANEL</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "💳 <code>/addcredit ID CANTIDAD</code>\n"
        "⭐ <code>/premiumadd ID</code>\n"
        "🔴 <code>/premiumoff ID</code>\n\n"

        "💎 Diamond está protegido por tu ADMIN_ID.\n\n"

        "━━━━━━━━━━━━━━━━━━━━"
    )

    send_message(
        chat_id,
        text
    )


# ============================================================
# PROCESS CALLBACK
# ============================================================

def process_update(update):

    callback = update.get("callback_query")

    if callback:

        answer_callback(
            callback["id"]
        )

        data = callback.get(
            "data",
            ""
        )

        message = callback.get(
            "message",
            {}
        )

        chat_id = message.get(
            "chat",
            {}
        ).get(
            "id"
        )

        user = callback.get(
            "from",
            {}
        )

        user_id = user.get(
            "id",
            0
        )

        username = user.get(
            "username",
            ""
        )

        if data == "home":

            welcome(
                chat_id,
                user_id,
                username
            )

        elif data == "cmds":

            command_panel(
                chat_id,
                user_id
            )

        elif data == "check":

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

        elif data == "premium":

            premium(
                chat_id,
                user_id
            )

        elif data == "credits":

            credits(
                chat_id,
                user_id,
                username
            )

        elif data == "diamond":

            diamond(
                chat_id,
                user_id
            )

        elif data == "references":

            references(
                chat_id,
                user_id
            )

        elif data == "updates":

            updates(
                chat_id,
                user_id
            )

        elif data == "tools":

            tools(
                chat_id,
                user_id
            )

        elif data == "diamond_credit":

            diamond_credit(
                chat_id,
                user_id
            )

        elif data == "diamond_premium":

            diamond_premium(
                chat_id,
                user_id
            )

        elif data == "diamond_stats":

            diamond_stats(
                chat_id,
                user_id
            )

        return

    # ========================================================
    # NORMAL MESSAGE
    # ========================================================

    message = update.get("message")

    if not message:
        return

    chat_id = message.get(
        "chat",
        {}
    ).get(
        "id"
    )

    sender = message.get(
        "from",
        {}
    )

    sender_id = sender.get(
        "id",
        0
    )

    username = sender.get(
        "username",
        ""
    )

    text = message.get(
        "text",
        ""
    ).strip()

    if not text:
        return

    # ADMIN

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

    # START

    if text.startswith("/start"):

        welcome(
            chat_id,
            sender_id,
            username
        )

        return

    # COMMAND PANEL

    if text.startswith("/cmds"):

        command_panel(
            chat_id,
            sender_id
        )

        return

    # ACCOUNT

    if text.startswith("/me"):

        account(
            chat_id,
            sender_id,
            username
        )

        return

    # SANDBOX

    if text == "/check":

        sandbox_check(
            chat_id,
            sender_id,
            username
        )

        return

    # PREMIUM

    if text.startswith("/premium"):

        premium(
            chat_id,
            sender_id
        )

        return

    # CREDITS

    if text.startswith("/credits"):

        credits(
            chat_id,
            sender_id,
            username
        )

        return

    # DIAMOND

    if text.startswith("/diamond"):

        diamond(
            chat_id,
            sender_id
        )

        return

    # UNKNOWN

    send_message(
        chat_id,

        "⚡ Usa <b>/start</b> o <b>/cmds</b> "
        "para abrir el panel.",

        main_menu(sender_id)
    )


# ============================================================
# WEB SERVER
# ============================================================

@app.route("/")
def home():

    return "Bill Cypher Chk OK", 200


@app.route("/health")
def health():

    return "OK", 200


# ============================================================
# LONG POLLING
# ============================================================

def polling():

    print("⚡ Iniciando Bill Cypher Chk...")

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
                    "timeout": 30,

                    "allowed_updates": [
                        "message",
                        "callback_query"
                    ]
                }
            )

            updates = result.get(
                "result",
                []
            )

            for update in updates:

                offset = (
                    update["update_id"] + 1
                )

                try:

                    process_update(
                        update
                    )

                except Exception as e:

                    print(
                        "Error procesando update:",
                        e
                    )

        except Exception as e:

            print(
                "Error polling:",
                e
            )

            time.sleep(5)


# ============================================================
# START
# ============================================================

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
