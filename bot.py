import os
import time
import sqlite3
import threading
import requests
from flask import Flask, request

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
PORT = int(os.environ.get("PORT", "10000"))
PUBLIC_URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "billcypher_webhook_2026")
DB = "bot.db"
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

# ---------------- DATABASE ----------------

def db():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT DEFAULT '',
        first_name TEXT DEFAULT '',
        credits INTEGER DEFAULT 5,
        plan TEXT DEFAULT 'FREE',
        checks INTEGER DEFAULT 0
    )""")
    c.commit()
    c.close()

def ensure_user(u):
    c = db()
    r = c.execute("SELECT id FROM users WHERE id=?", (u["id"],)).fetchone()
    if r is None:
        c.execute(
            "INSERT INTO users(id,username,first_name,credits,plan,checks) VALUES(?,?,?,?,?,?)",
            (u["id"], u.get("username",""), u.get("first_name","User"), 5, "FREE", 0)
        )
    else:
        c.execute(
            "UPDATE users SET username=?, first_name=? WHERE id=?",
            (u.get("username",""), u.get("first_name","User"), u["id"])
        )
    c.commit()
    c.close()

def get_user(uid):
    c = db()
    r = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    c.close()
    return r

def change_credits(uid, amount):
    c = db()
    c.execute("UPDATE users SET credits=credits+? WHERE id=?", (amount, uid))
    c.commit()
    c.close()

def consume(uid):
    c = db()
    r = c.execute("SELECT credits FROM users WHERE id=?", (uid,)).fetchone()
    if not r or r["credits"] < 1:
        c.close()
        return False
    c.execute("UPDATE users SET credits=credits-1,checks=checks+1 WHERE id=?", (uid,))
    c.commit()
    c.close()
    return True

# ---------------- TELEGRAM ----------------

def tg(method, data=None):
    try:
        r = requests.post(f"{API}/{method}", data=data or {}, timeout=30)
        result = r.json()
        print(method, "OK" if result.get("ok") else result, flush=True)
        return result
    except Exception as e:
        print(method, "ERROR:", repr(e), flush=True)
        return {"ok": False}

def send(chat, text, keyboard=None):
    d = {"chat_id": chat, "text": text, "parse_mode": "HTML"}
    if keyboard:
        d["reply_markup"] = keyboard
    return tg("sendMessage", d)

def edit(chat, mid, text, keyboard=None):
    d = {"chat_id": chat, "message_id": mid, "text": text, "parse_mode": "HTML"}
    if keyboard:
        d["reply_markup"] = keyboard
    return tg("editMessageText", d)

def answer(qid):
    tg("answerCallbackQuery", {"callback_query_id": qid})

def K(rows):
    return {"inline_keyboard": rows}

# ---------------- MENUS ----------------

def home(uid):
    rows = [
        [{"text":"🔎 CHECK SANDBOX","callback_data":"check"},
         {"text":"👤 MI CUENTA","callback_data":"account"}],
        [{"text":"⭐ PREMIUM","callback_data":"premium"},
         {"text":"💳 CRÉDITOS","callback_data":"credits"}],
        [{"text":"⚡ COMMAND CENTER","callback_data":"cmds"}],
        [{"text":"📚 REFERENCES","callback_data":"refs"},
         {"text":"🟢 UPDATES","callback_data":"updates"}],
    ]
    if uid == ADMIN_ID:
        rows.append([{"text":"💎 DIAMOND OWNER","callback_data":"diamond"}])
    return K(rows)

def back():
    return K([[{"text":"⬅️ BACK","callback_data":"cmds"}],
              [{"text":"🏠 HOME","callback_data":"home"}]])

def cmds():
    return K([
        [{"text":"⚡ GATEWAYS","callback_data":"gateways"},
         {"text":"⚙ TOOLS","callback_data":"tools"}],
        [{"text":"🔎 SANDBOX","callback_data":"check"},
         {"text":"👤 ACCOUNT","callback_data":"account"}],
        [{"text":"📚 REFERENCES","callback_data":"refs"},
         {"text":"🟢 UPDATES","callback_data":"updates"}],
        [{"text":"🏠 HOME","callback_data":"home"}]
    ])

def diamond():
    return K([
        [{"text":"➕ ADD CREDITS","callback_data":"dcredits"},
         {"text":"⭐ PREMIUM","callback_data":"dpremium"}],
        [{"text":"📊 STATISTICS","callback_data":"dstats"},
         {"text":"🧪 SANDBOX","callback_data":"check"}],
        [{"text":"🏠 HOME","callback_data":"home"}]
    ])

# ---------------- PAGES ----------------

def welcome(uid, name):
    u = get_user(uid)
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "♯ <b>BILL CYPHER CHK</b> 𐓏\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 Hello <b>{name}</b>\n"
        "Welcome to the control center.\n\n"
        "🔴 Mode: <b>SANDBOX</b>\n"
        "🟢 API Status: <b>ONLINE</b>\n"
        "⚡ Bot Version: <b>2.1</b>\n"
        f"💳 Credits: <b>{u['credits']}</b>\n"
        f"⭐ Plan: <b>{u['plan']}</b>\n\n"
        "Use /cmds to open the interactive command panel.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

def command_page():
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ <b>BILL CYPHER — COMMAND PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📡 Gateways: <b>12</b> sandbox modules\n"
        "⚙ Tools: <b>8</b> utilities\n"
        "🟢 API Status: <b>ONLINE</b>\n"
        "🧪 Engine: <b>SANDBOX</b>\n"
        "⚡ Version: <b>2.1</b>\n\n"
        "Selecciona una categoría.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

def run_check(chat, uid):
    if not consume(uid):
        send(chat, "❌ <b>Sin créditos.</b>\n\nUsa /credits o pide créditos al propietario.", home(uid))
        return

    r = send(chat, "🧪 <b>SANDBOX ANALYZER</b>\n━━━━━━━━━━━━━━━━━━━━\n⏳ Starting...\n━━━━━━━━━━━━━━━━━━━━")
    mid = r.get("result", {}).get("message_id")
    if not mid:
        return

    for s in [
        "⏳ Starting sandbox engine...",
        "⚡ Loading modules...",
        "🔄 Running automatic test...",
        "🧩 Processing synthetic data...",
        "📊 Preparing report...",
        "🟢 Complete!"
    ]:
        edit(chat, mid, "🧪 <b>SANDBOX ANALYZER</b>\n━━━━━━━━━━━━━━━━━━━━\n"+s+"\n━━━━━━━━━━━━━━━━━━━━")
        time.sleep(.55)

    edit(chat, mid,
         "━━━━━━━━━━━━━━━━━━━━\n"
         "🧪 <b>SANDBOX RESULT</b>\n"
         "━━━━━━━━━━━━━━━━━━━━\n\n"
         "🆔 Test: <code>AUTO-TEST</code>\n"
         "📡 Engine: <b>Sandbox</b>\n"
         "📊 Status: <b>TEST COMPLETE</b>\n"
         "🔐 Real card data: <b>NONE</b>\n"
         "💳 Real authorization: <b>NO</b>\n\n"
         "Análisis automático realizado con datos sintéticos.\n"
         "━━━━━━━━━━━━━━━━━━━━",
         K([[{"text":"🔄 RUN AGAIN","callback_data":"check"},
             {"text":"👤 ACCOUNT","callback_data":"account"}],
            [{"text":"⚡ COMMAND CENTER","callback_data":"cmds"},
             {"text":"🏠 HOME","callback_data":"home"}]]))

# ---------------- UPDATE HANDLER ----------------

def handle_update(u):
    if "callback_query" in u:
        q = u["callback_query"]
        answer(q["id"])
        user = q["from"]
        ensure_user(user)
        uid = user["id"]
        chat = q["message"]["chat"]["id"]
        d = q.get("data","")

        if d == "home":
            send(chat, welcome(uid, user.get("first_name","User")), home(uid))
        elif d == "cmds":
            send(chat, command_page(), cmds())
        elif d == "check":
            run_check(chat, uid)
        elif d == "account":
            x = get_user(uid)
            send(chat, f"👤 <b>MY ACCOUNT</b>\n━━━━━━━━━━━━━━━━━━━━\n🆔 <code>{uid}</code>\n👤 @{x['username'] if x['username'] else 'none'}\n⭐ Plan: <b>{x['plan']}</b>\n💳 Credits: <b>{x['credits']}</b>\n🔎 Sandbox runs: <b>{x['checks']}</b>", back())
        elif d == "credits":
            send(chat, f"💳 <b>CREDITS</b>\n\nDisponibles: <b>{get_user(uid)['credits']}</b>\n\n1 sandbox = 1 crédito.", back())
        elif d == "premium":
            send(chat, "⭐ <b>PREMIUM</b>\n\nPlan para funciones de interfaz y sandbox.", back())
        elif d == "refs":
            send(chat, "📚 <b>REFERENCES</b>\n\nTelegram Bot API\nFlask\nSQLite\nSandbox Engine", back())
        elif d == "updates":
            send(chat, "🟢 <b>UPDATES</b>\n\nv2.1 — Webhook estable, Command Panel, Sandbox automático y Diamond.", back())
        elif d == "gateways":
            send(chat, "⚡ <b>SANDBOX GATEWAYS</b>\n\n🟢 Alpha — ONLINE\n🟢 Beta — ONLINE\n🟢 Gamma — ONLINE\n🟡 Delta — TESTING\n\nMódulos simulados; no conectan con procesadores reales.", back())
        elif d == "tools":
            send(chat, "⚙ <b>TOOLS</b>\n\n🔎 Sandbox Analyzer\n📊 Statistics\n🧪 Test Generator\n⏱ Latency Simulator\n📝 Response Formatter", back())
        elif d == "diamond":
            if uid == ADMIN_ID:
                send(chat, "━━━━━━━━━━━━━━━━━━━━\n💎 <b>BILL CYPHER — DIAMOND</b>\n━━━━━━━━━━━━━━━━━━━━\n\n👑 OWNER ACCESS\n💎 Diamond: <b>ACTIVATED</b>\n🟢 API: <b>ONLINE</b>\n🧪 Sandbox: <b>ACTIVE</b>\n🛡 Admin: <b>ACTIVE</b>\n\nPrivate owner console.", diamond())
            else:
                send(chat, "⛔ Owner access only.")
        elif d == "dcredits":
            send(chat, "➕ <b>ADD CREDITS</b>\n\n<code>/addcredit USER_ID AMOUNT</code>", diamond())
        elif d == "dpremium":
            send(chat, "⭐ <b>PREMIUM CONTROL</b>\n\n<code>/premiumadd USER_ID</code>\n<code>/premiumoff USER_ID</code>", diamond())
        elif d == "dstats":
            c=db()
            a=c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
            b=c.execute("SELECT COALESCE(SUM(checks),0) n FROM users").fetchone()["n"]
            c.close()
            send(chat, f"📊 <b>STATISTICS</b>\n\n👥 Users: <b>{a}</b>\n🔎 Sandbox runs: <b>{b}</b>\n🟢 API: ONLINE", diamond())
        return

    if "message" not in u:
        return
    m = u["message"]
    user = m.get("from", {})
    chat = m.get("chat", {}).get("id")
    if not user or not chat:
        return
    ensure_user(user)
    text = (m.get("text") or "").strip()
    if not text:
        return

    parts = text.split()
    cmd = parts[0].split("@")[0].lower()
    uid = user["id"]

    if cmd == "/start":
        send(chat, welcome(uid, user.get("first_name","User")), home(uid))
    elif cmd in ("/cmds","/help"):
        send(chat, command_page(), cmds())
    elif cmd in ("/me","/account"):
        x=get_user(uid)
        send(chat, f"👤 <b>MY ACCOUNT</b>\n\n🆔 <code>{uid}</code>\n💳 Credits: <b>{x['credits']}</b>\n⭐ Plan: <b>{x['plan']}</b>\n🔎 Sandbox runs: <b>{x['checks']}</b>", back())
    elif cmd == "/credits":
        send(chat, f"💳 <b>CREDITS</b>\n\nDisponibles: <b>{get_user(uid)['credits']}</b>", back())
    elif cmd == "/premium":
        send(chat, "⭐ <b>PREMIUM</b>\n\nPlan para funciones de interfaz y sandbox.", back())
    elif cmd == "/check":
        run_check(chat, uid)
    elif cmd == "/diamond":
        if uid == ADMIN_ID:
            send(chat, "💎 <b>BILL CYPHER — DIAMOND</b>\n\n👑 OWNER ACCESS\n🟢 API ONLINE\n🧪 SANDBOX ACTIVE\n🛡 ADMIN ACTIVE", diamond())
        else:
            send(chat, "⛔ Owner access only.")
    elif cmd == "/addcredit" and uid == ADMIN_ID and len(parts)==3:
        try:
            target=int(parts[1]); amount=int(parts[2])
            change_credits(target, amount)
            send(chat, f"✅ Añadidos <b>{amount}</b> créditos a <code>{target}</code>.")
        except:
            send(chat, "Uso: /addcredit USER_ID AMOUNT")
    elif cmd == "/premiumadd" and uid == ADMIN_ID and len(parts)==2:
        try:
            target=int(parts[1]); c=db(); c.execute("UPDATE users SET plan='PREMIUM' WHERE id=?",(target,)); c.commit(); c.close()
            send(chat, "⭐ Premium activado.")
        except:
            send(chat, "❌ USER_ID inválido.")
    elif cmd == "/premiumoff" and uid == ADMIN_ID and len(parts)==2:
        try:
            target=int(parts[1]); c=db(); c.execute("UPDATE users SET plan='FREE' WHERE id=?",(target,)); c.commit(); c.close()
            send(chat, "⭐ Premium desactivado.")
        except:
            send(chat, "❌ USER_ID inválido.")
    else:
        send(chat, "Usa /start o /cmds.", home(uid))

# ---------------- WEBHOOK ----------------

@app.get("/")
def root():
    return "Bill Cypher Chk ONLINE", 200

@app.get("/health")
def health():
    return {"status":"online","telegram":"webhook","sandbox":True}, 200

@app.post("/telegram/" + WEBHOOK_SECRET)
def telegram_webhook():
    update = request.get_json(silent=True)
    if update:
        try:
            handle_update(update)
        except Exception as e:
            print("UPDATE ERROR:", repr(e), flush=True)
    return "OK", 200

def configure_webhook():
    init_db()
    if not PUBLIC_URL:
        print("ERROR: RENDER_EXTERNAL_URL is missing.", flush=True)
        return
    url = f"{PUBLIC_URL}/telegram/{WEBHOOK_SECRET}"
    result = tg("setWebhook", {
        "url": url,
        "drop_pending_updates": "true",
        "allowed_updates": '["message","callback_query"]'
    })
    print("WEBHOOK URL:", url, flush=True)
    print("WEBHOOK CONFIG:", result, flush=True)

if __name__ == "__main__":
    init_db()
    threading.Thread(target=configure_webhook, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)
