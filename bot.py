import os
import time
import html
import random
import sqlite3
import threading
import requests

from flask import Flask, jsonify

# ============================================================
# BILL CYPHER CHK — PREMIUM UI / SANDBOX EDITION
# Single-file Telegram bot for Render
#
# SAFE MODE:
# - /check runs a synthetic sandbox simulation only.
# - It does NOT process real cards, CVV, balances, or bank
#   authorizations.
#
# Environment variables:
#   BOT_TOKEN       = BotFather token
#   ADMIN_ID        = your Telegram numeric ID
#   ANIMATION_FILE_ID = optional Telegram GIF/animation file_id
#   PORT            = Render port (normally 10000)
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
ANIMATION_FILE_ID = os.getenv("ANIMATION_FILE_ID", "").strip()
PORT = int(os.getenv("PORT", "10000"))
DB_PATH = os.getenv("DB_PATH", "bill_cypher.db")

VERSION = "2.0"
GATEWAYS = 73
TOOLS = 12

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
app = Flask(__name__)
DB_LOCK = threading.Lock()


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with DB_LOCK:
        conn = get_db()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                credits INTEGER DEFAULT 5,
                plan TEXT DEFAULT 'FREE',
                checks INTEGER DEFAULT 0,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_check TEXT DEFAULT ''
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()


def ensure_user(user):
    uid = int(user["id"])
    username = user.get("username", "") or ""
    first_name = user.get("first_name", "") or ""

    with DB_LOCK:
        conn = get_db()
        exists = conn.execute(
            "SELECT id FROM users WHERE id = ?",
            (uid,)
        ).fetchone()

        if exists:
            conn.execute("""
                UPDATE users
                SET username = ?, first_name = ?
                WHERE id = ?
            """, (username, first_name, uid))
        else:
            conn.execute("""
                INSERT INTO users
                (id, username, first_name, credits, plan)
                VALUES (?, ?, ?, 5, 'FREE')
            """, (uid, username, first_name))

        conn.commit()
        conn.close()


def user_row(uid):
    with DB_LOCK:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (uid,)
        ).fetchone()
        conn.close()
    return row


def log_action(uid, action):
    with DB_LOCK:
        conn = get_db()
        conn.execute(
            "INSERT INTO logs(user_id, action) VALUES (?, ?)",
            (uid, action)
        )
        conn.commit()
        conn.close()


# ============================================================
# TELEGRAM API
# ============================================================

def tg(method, payload=None):
    if not BOT_TOKEN:
        print("[FATAL] BOT_TOKEN is missing.")
        return None

    try:
        r = requests.post(
            f"{API}/{method}",
            json=payload or {},
            timeout=35
        )
        data = r.json()

        if not data.get("ok"):
            print(f"[TG ERROR] {method}: {data}")

        return data
    except Exception as exc:
        print(f"[TG EXCEPTION] {method}: {exc}")
        return None


def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if keyboard:
        payload["reply_markup"] = keyboard
    return tg("sendMessage", payload)


def edit_message(chat_id, message_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if keyboard:
        payload["reply_markup"] = keyboard

    result = tg("editMessageText", payload)

    # Telegram returns MESSAGE_NOT_MODIFIED if the same text is sent.
    return result


def answer_callback(callback_id):
    return tg(
        "answerCallbackQuery",
        {"callback_query_id": callback_id}
    )


def send_animation(chat_id, caption, keyboard=None):
    """
    Uses ANIMATION_FILE_ID if configured.
    Telegram file_id is the most reliable option because the
    animation is already stored on Telegram.
    """
    if not ANIMATION_FILE_ID:
        return send_message(chat_id, caption, keyboard)

    payload = {
        "chat_id": chat_id,
        "animation": ANIMATION_FILE_ID,
        "caption": caption,
        "parse_mode": "HTML"
    }

    if keyboard:
        payload["reply_markup"] = keyboard

    return tg("sendAnimation", payload)


# ============================================================
# UI HELPERS
# ============================================================

def safe_name(user):
    return html.escape(
        user.get("first_name")
        or user.get("username")
        or "SpaceBoy"
    )


def status_dot(ok=True):
    return "🟢" if ok else "🔴"


def progress_bar(percent, width=12):
    filled = round(width * percent / 100)
    return "▰" * filled + "▱" * (width - filled)


def main_keyboard(uid):
    rows = [
        [
            {"text": "⚡  CHECK SANDBOX", "callback_data": "check"},
        ],
        [
            {"text": "👤  ACCOUNT", "callback_data": "account"},
            {"text": "💰  CREDITS", "callback_data": "credits"},
        ],
        [
            {"text": "💎  PREMIUM", "callback_data": "premium"},
            {"text": "⚙️  COMMANDS", "callback_data": "panel"},
        ],
        [
            {"text": "📚  REFERENCES", "callback_data": "refs"},
            {"text": "📢  UPDATES", "callback_data": "updates"},
        ],
    ]

    if uid == ADMIN_ID:
        rows.append([
            {"text": "💠  DIAMOND OWNER", "callback_data": "diamond"}
        ])

    return {"inline_keyboard": rows}


def panel_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "⚡ GATEWAYS", "callback_data": "gateways"},
                {"text": "⚙️ TOOLS", "callback_data": "tools"},
            ],
            [
                {"text": "👤 ACCOUNT", "callback_data": "account"},
                {"text": "💰 CREDITS", "callback_data": "credits"},
            ],
            [
                {"text": "💎 PREMIUM", "callback_data": "premium"},
                {"text": "📊 STATUS", "callback_data": "status"},
            ],
            [
                {"text": "🔙 HOME", "callback_data": "home"}
            ]
        ]
    }


def back_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🔙  BACK TO HOME", "callback_data": "home"}]
        ]
    }


def diamond_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "📊 STATISTICS", "callback_data": "stats"},
                {"text": "💎 PREMIUM USERS", "callback_data": "premium_users"},
            ],
            [
                {"text": "➕ CREDIT HELP", "callback_data": "credit_help"}
            ],
            [
                {"text": "🔙 HOME", "callback_data": "home"}
            ]
        ]
    }


# ============================================================
# SCREENS
# ============================================================

def home_screen(user):
    name = safe_name(user)

    return (
        "🔴━━━━━━━━━━━━━━━━━━━━━━━━🔴\n"
        "        <b>♯ BILL CYPHER CHK</b>\n"
        "🔴━━━━━━━━━━━━━━━━━━━━━━━━🔴\n\n"
        f"👋 Hello <b>{name}</b>\n"
        "Welcome to your private testing panel.\n\n"
        "╭────────────────────────╮\n"
        "│  ⚡ <b>ENGINE STATUS</b>          │\n"
        f"│  API       {status_dot()} <b>ONLINE</b>       │\n"
        "│  ENGINE    🧪 <b>READY</b>        │\n"
        f"│  VERSION   <b>{VERSION}</b>             │\n"
        "╰────────────────────────╯\n\n"
        "🔹 <b>Sandbox Analyzer</b>\n"
        "Synthetic test environment • no real payment data\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Use <code>/cmds</code> for the command panel."
    )


def panel_screen():
    return (
        "╔════════════════════════════╗\n"
        "║   ⚡ <b>BILL CYPHER PANEL</b>   ║\n"
        "╚════════════════════════════╝\n\n"
        "📡 <b>SYSTEM OVERVIEW</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ Gateways     <b>{GATEWAYS}</b>\n"
        f"⚙️ Tools        <b>{TOOLS}</b>\n"
        "🟢 API          <b>ONLINE</b>\n"
        "🧪 Sandbox      <b>READY</b>\n"
        f"🤖 Version      <b>{VERSION}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select a module below."
    )


def account_screen(row):
    username = html.escape(row["username"] or "none")
    plan = html.escape(row["plan"])

    return (
        "╭━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "│       👤 <b>ACCOUNT</b>       │\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        f"🆔 ID: <code>{row['id']}</code>\n"
        f"👤 Username: @{username}\n"
        f"💎 Plan: <b>{plan}</b>\n"
        f"💰 Credits: <b>{row['credits']}</b>\n"
        f"🧪 Tests: <b>{row['checks']}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔐 Account status: 🟢 ACTIVE"
    )


def credits_screen(row):
    return (
        "💰 <b>CREDIT CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Available credits: <b>{row['credits']}</b>\n"
        f"Current plan: <b>{html.escape(row['plan'])}</b>\n\n"
        "🧪 Sandbox test: <b>1 credit</b>\n"
        "💎 Premium: <b>unlimited sandbox</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Contact the owner for credit management."
    )


def premium_screen():
    return (
        "💎 <b>BILL CYPHER PREMIUM</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🚀 Premium features\n\n"
        "⚡ Unlimited Sandbox tests\n"
        "📊 Advanced statistics\n"
        "🔔 Priority processing\n"
        "💠 Premium account badge\n"
        "🧪 Full simulation dashboard\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Contact the owner to activate Premium."
    )


def status_screen():
    return (
        "📡 <b>SYSTEM STATUS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "API             🟢 ONLINE\n"
        "Telegram        🟢 CONNECTED\n"
        "Database        🟢 READY\n"
        "Sandbox         🟢 READY\n"
        "UI Engine       🟢 READY\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Version         <b>{VERSION}</b>"
    )


# ============================================================
# SANDBOX ANIMATION
# ============================================================

def sandbox_result():
    # Synthetic-only result. No card/payment information is used.
    result = random.choice([
        "APPROVED (SIMULATED)",
        "DECLINED (SIMULATED)",
        "TEST COMPLETE"
    ])
    latency = random.randint(118, 420)
    return result, latency


def run_sandbox(chat_id, uid):
    row = user_row(uid)

    if not row:
        return

    # Premium does not consume credits.
    if row["plan"] != "PREMIUM":
        if row["credits"] <= 0:
            send_message(
                chat_id,
                "🚫 <b>NO CREDITS</b>\n\n"
                "You have no Sandbox credits left.",
                back_keyboard()
            )
            return

        with DB_LOCK:
            conn = get_db()
            conn.execute("""
                UPDATE users
                SET credits = credits - 1,
                    checks = checks + 1,
                    last_check = datetime('now')
                WHERE id = ?
            """, (uid,))
            conn.commit()
            conn.close()
    else:
        with DB_LOCK:
            conn = get_db()
            conn.execute("""
                UPDATE users
                SET checks = checks + 1,
                    last_check = datetime('now')
                WHERE id = ?
            """, (uid,))
            conn.commit()
            conn.close()

    log_action(uid, "sandbox_check")

    # Initial card-like dashboard animation, but explicitly sandbox.
    first = send_message(
        chat_id,
        "╔════════════════════════════╗\n"
        "║     🧪 <b>SANDBOX ENGINE</b>     ║\n"
        "╚════════════════════════════╝\n\n"
        "⚡ <b>Initializing...</b>\n"
        "▱▱▱▱▱▱▱▱▱▱▱▱   0%\n\n"
        "Environment: <b>SAFE SIMULATION</b>"
    )

    if not first or not first.get("ok"):
        return

    mid = first["result"]["message_id"]

    frames = [
        (
            "⚡ <b>Initializing engine</b>",
            15,
            "Booting simulation core..."
        ),
        (
            "📡 <b>Connecting to sandbox</b>",
            30,
            "Secure test channel established..."
        ),
        (
            "🔎 <b>Running synthetic analysis</b>",
            50,
            "Analyzing generated test data..."
        ),
        (
            "🧠 <b>Evaluating response</b>",
            70,
            "Calculating simulated gateway response..."
        ),
        (
            "📊 <b>Building report</b>",
            88,
            "Preparing result dashboard..."
        ),
        (
            "🟢 <b>Finalizing</b>",
            100,
            "Sandbox test complete."
        ),
    ]

    for title, percent, detail in frames:
        time.sleep(0.65)

        bar = progress_bar(percent)

        text = (
            "╔════════════════════════════╗\n"
            "║     🧪 <b>SANDBOX ENGINE</b>     ║\n"
            "╚════════════════════════════╝\n\n"
            f"{title}\n"
            f"<code>{bar}</code> <b>{percent}%</b>\n\n"
            f"↳ {detail}\n\n"
            "Environment: <b>SAFE SIMULATION</b>"
        )

        edit_message(chat_id, mid, text)

    result, latency = sandbox_result()

    time.sleep(0.7)

    final = (
        "╔════════════════════════════╗\n"
        "║       🧪 <b>RESULT</b>          ║\n"
        "╚════════════════════════════╝\n\n"
        "🟢 <b>TEST COMPLETE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ Engine: <b>SANDBOX</b>\n"
        "📡 Gateway: <b>SIMULATOR</b>\n"
        f"📊 Response: <b>{result}</b>\n"
        f"⏱ Latency: <b>{latency} ms</b>\n"
        "🧪 Mode: <b>SYNTHETIC</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ No real card was processed.\n"
        "⚠️ No CVV, balance or bank authorization was checked."
    )

    edit_message(
        chat_id,
        mid,
        final,
        back_keyboard()
    )


# ============================================================
# COMMANDS
# ============================================================

def cmd_start(chat_id, user):
    ensure_user(user)

    # If an animation file_id is configured, it appears as the
    # visual banner above the welcome caption.
    send_animation(
        chat_id,
        home_screen(user),
        main_keyboard(user["id"])
    )


def cmd_cmds(chat_id):
    send_message(
        chat_id,
        panel_screen(),
        panel_keyboard()
    )


def cmd_account(chat_id, uid):
    row = user_row(uid)
    send_message(
        chat_id,
        account_screen(row),
        back_keyboard()
    )


def cmd_credits(chat_id, uid):
    row = user_row(uid)
    send_message(
        chat_id,
        credits_screen(row),
        back_keyboard()
    )


def cmd_premium(chat_id):
    send_message(
        chat_id,
        premium_screen(),
        back_keyboard()
    )


def cmd_gateways(chat_id):
    send_message(
        chat_id,
        "⚡ <b>GATEWAY CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Configured modules: <b>{GATEWAYS}</b>\n\n"
        "🧪 Sandbox Simulator     🟢 ONLINE\n"
        "📊 Synthetic Analyzer    🟢 ONLINE\n\n"
        "These are simulated modules only; "
        "no live payment authorization is performed.",
        back_keyboard()
    )


def cmd_tools(chat_id):
    send_message(
        chat_id,
        "⚙️ <b>TOOLS CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Tools loaded: <b>{TOOLS}</b>\n\n"
        "01 • 🧪 Sandbox Analyzer\n"
        "02 • 📊 Statistics\n"
        "03 • 👤 Account\n"
        "04 • 💰 Credit Center\n"
        "05 • 💎 Premium\n"
        "06 • 📡 API Monitor\n"
        "07 • 🟢 Health Monitor\n"
        "08 • 🧠 Synthetic Engine\n\n"
        "More UI modules can be added later.",
        back_keyboard()
    )


def cmd_refs(chat_id):
    send_message(
        chat_id,
        "📚 <b>REFERENCES</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "♯ Bill Cypher Chk\n"
        "⚡ Private testing interface\n"
        "🧪 Sandbox simulation engine\n\n"
        "This project is independent and is not affiliated "
        "with Kaori.",
        back_keyboard()
    )


def cmd_updates(chat_id):
    send_message(
        chat_id,
        "📢 <b>UPDATES</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Current release: <b>{VERSION}</b>\n\n"
        "🟢 Premium UI\n"
        "🟢 Animated Sandbox\n"
        "🟢 Account system\n"
        "🟢 Credit system\n"
        "🟢 Diamond owner panel\n"
        "🟢 Statistics\n"
        "🟢 Render polling engine",
        back_keyboard()
    )


def cmd_stats(chat_id, uid):
    if uid != ADMIN_ID:
        send_message(chat_id, "⛔ <b>Owner only.</b>")
        return

    with DB_LOCK:
        conn = get_db()
        users = conn.execute(
            "SELECT COUNT(*) n FROM users"
        ).fetchone()["n"]
        premium = conn.execute(
            "SELECT COUNT(*) n FROM users WHERE plan='PREMIUM'"
        ).fetchone()["n"]
        checks = conn.execute(
            "SELECT COALESCE(SUM(checks),0) n FROM users"
        ).fetchone()["n"]
        conn.close()

    send_message(
        chat_id,
        "📊 <b>DIAMOND STATISTICS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Users: <b>{users}</b>\n"
        f"💎 Premium: <b>{premium}</b>\n"
        f"🧪 Sandbox tests: <b>{checks}</b>\n"
        f"⚡ Gateways: <b>{GATEWAYS}</b>\n"
        f"⚙️ Tools: <b>{TOOLS}</b>\n"
        f"🤖 Version: <b>{VERSION}</b>",
        back_keyboard()
    )


def cmd_addcredit(chat_id, uid, args):
    if uid != ADMIN_ID:
        send_message(chat_id, "⛔ <b>Owner only.</b>")
        return

    if len(args) != 2:
        send_message(
            chat_id,
            "Usage:\n<code>/addcredit USER_ID AMOUNT</code>"
        )
        return

    try:
        target = int(args[0])
        amount = int(args[1])
    except ValueError:
        send_message(chat_id, "❌ Invalid ID or amount.")
        return

    if amount <= 0:
        send_message(chat_id, "❌ Amount must be greater than zero.")
        return

    with DB_LOCK:
        conn = get_db()
        exists = conn.execute(
            "SELECT id FROM users WHERE id=?",
            (target,)
        ).fetchone()

        if not exists:
            conn.close()
            send_message(
                chat_id,
                "❌ User must start the bot first."
            )
            return

        conn.execute(
            "UPDATE users SET credits = credits + ? WHERE id=?",
            (amount, target)
        )
        conn.commit()
        conn.close()

    send_message(
        chat_id,
        "✅ <b>CREDITS UPDATED</b>\n\n"
        f"User: <code>{target}</code>\n"
        f"Added: <b>+{amount}</b>"
    )


def cmd_premiumadd(chat_id, uid, args):
    if uid != ADMIN_ID:
        send_message(chat_id, "⛔ <b>Owner only.</b>")
        return

    if len(args) != 1:
        send_message(
            chat_id,
            "Usage:\n<code>/premiumadd USER_ID</code>"
        )
        return

    try:
        target = int(args[0])
    except ValueError:
        send_message(chat_id, "❌ Invalid ID.")
        return

    with DB_LOCK:
        conn = get_db()
        conn.execute(
            "UPDATE users SET plan='PREMIUM' WHERE id=?",
            (target,)
        )
        conn.commit()
        conn.close()

    send_message(
        chat_id,
        "💎 <b>PREMIUM ACTIVATED</b>\n\n"
        f"User: <code>{target}</code>"
    )


def cmd_premiumoff(chat_id, uid, args):
    if uid != ADMIN_ID:
        send_message(chat_id, "⛔ <b>Owner only.</b>")
        return

    if len(args) != 1:
        send_message(
            chat_id,
            "Usage:\n<code>/premiumoff USER_ID</code>"
        )
        return

    try:
        target = int(args[0])
    except ValueError:
        send_message(chat_id, "❌ Invalid ID.")
        return

    with DB_LOCK:
        conn = get_db()
        conn.execute(
            "UPDATE users SET plan='FREE' WHERE id=?",
            (target,)
        )
        conn.commit()
        conn.close()

    send_message(
        chat_id,
        "✅ Premium disabled."
    )


def cmd_diamond(chat_id, uid):
    if uid != ADMIN_ID:
        send_message(
            chat_id,
            "⛔ <b>DIAMOND ACCESS DENIED</b>"
        )
        return

    send_message(
        chat_id,
        "💠 <b>DIAMOND OWNER CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👑 Access: <b>OWNER</b>\n"
        "📡 API: 🟢 ONLINE\n"
        "🧪 Engine: 🟢 READY\n"
        "💎 Premium system: 🟢 READY\n\n"
        "Choose an owner tool.",
        diamond_keyboard()
    )


# ============================================================
# CALLBACK HANDLER
# ============================================================

def handle_callback(query):
    answer_callback(query["id"])

    data = query.get("data", "")
    message = query.get("message", {})
    chat = message.get("chat", {})
    user = query.get("from", {})

    chat_id = chat.get("id")
    uid = user.get("id")
    message_id = message.get("message_id")

    if not chat_id or not uid:
        return

    ensure_user(user)

    if data == "home":
        edit_message(
            chat_id,
            message_id,
            home_screen(user),
            main_keyboard(uid)
        )

    elif data == "panel":
        edit_message(
            chat_id,
            message_id,
            panel_screen(),
            panel_keyboard()
        )

    elif data == "check":
        # Send the animated simulation as a separate live message.
        run_sandbox(chat_id, uid)

    elif data == "account":
        edit_message(
            chat_id,
            message_id,
            account_screen(user_row(uid)),
            back_keyboard()
        )

    elif data == "credits":
        edit_message(
            chat_id,
            message_id,
            credits_screen(user_row(uid)),
            back_keyboard()
        )

    elif data == "premium":
        edit_message(
            chat_id,
            message_id,
            premium_screen(),
            back_keyboard()
        )

    elif data == "gateways":
        edit_message(
            chat_id,
            message_id,
            "⚡ <b>GATEWAYS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Modules: <b>{GATEWAYS}</b>\n"
            "Sandbox Simulator: 🟢 ONLINE\n"
            "Live authorization: ⚪ DISABLED\n\n"
            "Only synthetic tests are performed.",
            back_keyboard()
        )

    elif data == "tools":
        edit_message(
            chat_id,
            message_id,
            "⚙️ <b>TOOLS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Loaded tools: <b>{TOOLS}</b>\n\n"
            "🧪 Sandbox Analyzer\n"
            "📊 Statistics\n"
            "👤 Account\n"
            "💰 Credits\n"
            "💎 Premium\n"
            "📡 API Monitor\n"
            "🧠 Synthetic Engine",
            back_keyboard()
        )

    elif data == "refs":
        edit_message(
            chat_id,
            message_id,
            "📚 <b>REFERENCES</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Bill Cypher Chk\n"
            "Sandbox Engine\n"
            "Telegram Bot API\n\n"
            "Independent project.",
            back_keyboard()
        )

    elif data == "updates":
        edit_message(
            chat_id,
            message_id,
            "📢 <b>UPDATES</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Version <b>{VERSION}</b>\n\n"
            "🟢 Premium UI\n"
            "🟢 Animated Sandbox\n"
            "🟢 Credits\n"
            "🟢 Diamond\n"
            "🟢 Statistics",
            back_keyboard()
        )

    elif data == "status":
        edit_message(
            chat_id,
            message_id,
            status_screen(),
            back_keyboard()
        )

    elif data == "diamond":
        cmd_diamond(chat_id, uid)

    elif data == "stats":
        cmd_stats(chat_id, uid)

    elif data == "premium_users":
        if uid != ADMIN_ID:
            send_message(chat_id, "⛔ Owner only.")
            return

        with DB_LOCK:
            conn = get_db()
            rows = conn.execute("""
                SELECT id, username
                FROM users
                WHERE plan='PREMIUM'
                ORDER BY id DESC
                LIMIT 30
            """).fetchall()
            conn.close()

        if not rows:
            text = "💎 <b>PREMIUM USERS</b>\n\nNo Premium users."
        else:
            lines = []
            for row in rows:
                name = html.escape(row["username"] or "no_username")
                lines.append(
                    f"• <code>{row['id']}</code> @{name}"
                )
            text = (
                "💎 <b>PREMIUM USERS</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                + "\n".join(lines)
            )

        send_message(chat_id, text, back_keyboard())

    elif data == "credit_help":
        if uid != ADMIN_ID:
            send_message(chat_id, "⛔ Owner only.")
            return

        send_message(
            chat_id,
            "💠 <b>OWNER COMMANDS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<code>/addcredit USER_ID AMOUNT</code>\n"
            "<code>/premiumadd USER_ID</code>\n"
            "<code>/premiumoff USER_ID</code>\n"
            "<code>/stats</code>"
        )


# ============================================================
# UPDATE ROUTER
# ============================================================

def process_update(update):
    try:
        if "callback_query" in update:
            handle_callback(update["callback_query"])
            return

        message = update.get("message")
        if not message:
            return

        user = message.get("from")
        chat_id = message.get("chat", {}).get("id")

        if not user or not chat_id:
            return

        ensure_user(user)

        text = (message.get("text") or "").strip()

        if not text:
            return

        if not text.startswith("/"):
            lowered = text.lower()

            if lowered in ("menu", "menú", "panel"):
                cmd_cmds(chat_id)
            elif lowered in ("check", "chk"):
                run_sandbox(chat_id, user["id"])
            else:
                send_message(
                    chat_id,
                    "♯ <b>Bill Cypher Chk</b>\n\n"
                    "Use <code>/cmds</code> to open the panel."
                )
            return

        parts = text.split()
        command = parts[0].split("@")[0].lower()
        args = parts[1:]

        if command == "/start":
            cmd_start(chat_id, user)

        elif command in ("/cmds", "/commands"):
            cmd_cmds(chat_id)

        elif command in ("/check", "/chk"):
            run_sandbox(chat_id, user["id"])

        elif command in ("/account", "/me"):
            cmd_account(chat_id, user["id"])

        elif command == "/credits":
            cmd_credits(chat_id, user["id"])

        elif command == "/premium":
            cmd_premium(chat_id)

        elif command == "/gateways":
            cmd_gateways(chat_id)

        elif command == "/tools":
            cmd_tools(chat_id)

        elif command in ("/refs", "/references"):
            cmd_refs(chat_id)

        elif command == "/updates":
            cmd_updates(chat_id)

        elif command == "/status":
            send_message(
                chat_id,
                status_screen(),
                back_keyboard()
            )

        elif command == "/diamond":
            cmd_diamond(chat_id, user["id"])

        elif command == "/stats":
            cmd_stats(chat_id, user["id"])

        elif command == "/addcredit":
            cmd_addcredit(chat_id, user["id"], args)

        elif command == "/premiumadd":
            cmd_premiumadd(chat_id, user["id"], args)

        elif command == "/premiumoff":
            cmd_premiumoff(chat_id, user["id"], args)

        else:
            send_message(
                chat_id,
                "❓ Unknown command.\n\n"
                "Use <code>/cmds</code>.",
                panel_keyboard()
            )

    except Exception as exc:
        print(f"[UPDATE ERROR] {exc}")


# ============================================================
# TELEGRAM POLLING
# ============================================================

def polling_loop():
    print("========================================")
    print(" BILL CYPHER CHK v" + VERSION)
    print(" Telegram polling engine starting...")
    print("========================================")

    if not BOT_TOKEN:
        print("[FATAL] BOT_TOKEN is missing.")
        return

    me = tg("getMe")

    if not me or not me.get("ok"):
        print("[FATAL] Telegram getMe failed.")
        return

    bot = me["result"]
    print(
        "[TG] Connected as @" +
        str(bot.get("username", "unknown"))
    )

    # Prevent webhook/polling conflicts.
    deleted = tg(
        "deleteWebhook",
        {"drop_pending_updates": False}
    )
    print(
        "[TG] deleteWebhook:",
        bool(deleted and deleted.get("ok"))
    )

    offset = None

    while True:
        try:
            payload = {
                "timeout": 25,
                "limit": 100,
                "allowed_updates": [
                    "message",
                    "callback_query"
                ]
            }

            if offset is not None:
                payload["offset"] = offset

            result = tg("getUpdates", payload)

            if not result:
                time.sleep(2)
                continue

            if not result.get("ok"):
                time.sleep(5)
                continue

            updates = result.get("result", [])

            for update in updates:
                update_id = update.get("update_id")

                if update_id is not None:
                    offset = update_id + 1

                process_update(update)

        except requests.exceptions.RequestException as exc:
            print("[NETWORK]", exc)
            time.sleep(5)

        except Exception as exc:
            print("[POLLING]", exc)
            time.sleep(5)


# ============================================================
# FLASK HEALTH SERVER
# ============================================================

@app.route("/")
def root():
    return jsonify({
        "bot": "Bill Cypher Chk",
        "version": VERSION,
        "status": "online",
        "engine": "sandbox",
        "transport": "long-polling"
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "version": VERSION
    })


@app.route("/ping")
def ping():
    return "pong", 200


# ============================================================
# MAIN
# ============================================================

def main():
    init_db()

    thread = threading.Thread(
        target=polling_loop,
        daemon=True
    )
    thread.start()

    print(f"[WEB] Flask listening on 0.0.0.0:{PORT}")

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False
    )


if __name__ == "__main__":
    main()
