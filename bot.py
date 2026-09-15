import os
import time
import sqlite3
import threading
import requests
from flask import Flask

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
PORT = int(os.environ.get("PORT", "10000"))
DB = "bot.db"
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

def db():
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT DEFAULT '',
        first_name TEXT DEFAULT '',
        credits INTEGER DEFAULT 5,
        plan TEXT DEFAULT 'FREE',
        checks INTEGER DEFAULT 0
    )""")
    con.commit()
    con.close()

def ensure_user(u):
    con = db()
    row = con.execute("SELECT id FROM users WHERE id=?", (u["id"],)).fetchone()
    if row is None:
        con.execute(
            "INSERT INTO users(id,username,first_name,credits,plan,checks) VALUES(?,?,?,?,?,?)",
            (u["id"], u.get("username",""), u.get("first_name","User"), 5, "FREE", 0)
        )
    else:
        con.execute(
            "UPDATE users SET username=?,first_name=? WHERE id=?",
            (u.get("username",""), u.get("first_name","User"), u["id"])
        )
    con.commit()
    con.close()

def get_user(uid):
    con = db()
    r = con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    con.close()
    return r

def api(method, data=None):
    try:
        return requests.post(f"{API}/{method}", data=data or {}, timeout=35).json()
    except Exception as e:
        print("API error:", e)
        return {"ok": False}

def send(chat_id, text, keyboard=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = keyboard
    return api("sendMessage", data)

def edit(chat_id, message_id, text, keyboard=None):
    data = {"chat_id": chat_id, "message_id": message_id,
            "text": text, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = keyboard
    return api("editMessageText", data)

def answer(qid):
    api("answerCallbackQuery", {"callback_query_id": qid})

def kb(rows):
    return {"inline_keyboard": rows}

def home_kb(uid):
    rows = [
        [{"text":"🔎 CHECK SANDBOX","callback_data":"check"},
         {"text":"👤 MI CUENTA","callback_data":"account"}],
        [{"text":"⭐ PREMIUM","callback_data":"premium"},
         {"text":"💳 CRÉDITOS","callback_data":"credits"}],
        [{"text":"⚡ COMMAND CENTER","callback_data":"cmds"}],
        [{"text":"📚 REFERENCES","callback_data":"refs"},
         {"text":"🟢 UPDATES","callback_data":"updates"}]
    ]
    if uid == ADMIN_ID:
        rows.append([{"text":"💎 DIAMOND OWNER","callback_data":"diamond"}])
    return kb(rows)

def back_kb():
    return kb([[{"text":"⬅️ BACK","callback_data":"cmds"}],
               [{"text":"🏠 HOME","callback_data":"home"}]])

def cmds_kb():
    return kb([
        [{"text":"⚡ GATEWAYS","callback_data":"gateways"},
         {"text":"⚙ TOOLS","callback_data":"tools"}],
        [{"text":"🔎 SANDBOX","callback_data":"check"},
         {"text":"👤 ACCOUNT","callback_data":"account"}],
        [{"text":"📚 REFERENCES","callback_data":"refs"},
         {"text":"🟢 UPDATES","callback_data":"updates"}],
        [{"text":"🏠 HOME","callback_data":"home"}]
    ])

def diamond_kb():
    return kb([
        [{"text":"➕ ADD CREDITS","callback_data":"dcredits"},
         {"text":"⭐ PREMIUM","callback_data":"dpremium"}],
        [{"text":"📊 STATISTICS","callback_data":"dstats"},
         {"text":"🧪 SANDBOX","callback_data":"check"}],
        [{"text":"🏠 HOME","callback_data":"home"}]
    ])

def welcome(uid, name):
    u = get_user(uid)
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "♯ <b>BILL CYPHER CHK</b> 𐓏\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 Hello <b>{name}</b>\n"
        "Welcome to the control center.\n\n"
        "🔴 <b>Mode:</b> SANDBOX\n"
        "🟢 <b>API Status:</b> ONLINE\n"
        "⚡ <b>Version:</b> 2.0\n"
        f"💳 <b>Credits:</b> {u['credits']}\n"
        f"⭐ <b>Plan:</b> {u['plan']}\n\n"
        "Use /cmds to open the command panel.\n"
        "All checker activity is simulated test data only.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

def commands():
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ <b>BILL CYPHER — COMMAND CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📡 <b>Gateways:</b> 12 sandbox modules\n"
        "⚙ <b>Tools:</b> 8 utility modules\n"
        "🟢 <b>API:</b> ONLINE\n"
        "🧪 <b>Engine:</b> SANDBOX\n"
        "🔢 <b>Version:</b> 2.0\n\n"
        "Choose a section below.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

def account(uid):
    u = get_user(uid)
    user = "@"+u["username"] if u["username"] else "Sin username"
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👤 <b>MY ACCOUNT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"👤 User: {user}\n"
        f"⭐ Plan: <b>{u['plan']}</b>\n"
        f"💳 Credits: <b>{u['credits']}</b>\n"
        f"🔎 Sandbox runs: <b>{u['checks']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

def consume(uid):
    con = db()
    r = con.execute("SELECT credits FROM users WHERE id=?", (uid,)).fetchone()
    if not r or r["credits"] <= 0:
        con.close()
        return False
    con.execute("UPDATE users SET credits=credits-1,checks=checks+1 WHERE id=?", (uid,))
    con.commit()
    con.close()
    return True

def sandbox(chat_id, uid):
    if not consume(uid):
        send(chat_id, "❌ <b>Sin créditos.</b>\n\nUsa /credits o pide créditos al propietario.",
             home_kb(uid))
        return

    r = send(chat_id,
             "🧪 <b>SANDBOX ANALYZER</b>\n━━━━━━━━━━━━━━━━━━━━\n⏳ Initializing...\n━━━━━━━━━━━━━━━━━━━━")
    mid = r.get("result", {}).get("message_id")
    if not mid:
        return

    steps = [
        "⏳ Initializing sandbox...",
        "⚡ Loading test modules...",
        "🔄 Running synthetic analysis...",
        "🧩 Evaluating simulated response...",
        "📊 Building report...",
        "🟢 Analysis complete."
    ]
    for s in steps:
        edit(chat_id, mid,
             "🧪 <b>SANDBOX ANALYZER</b>\n━━━━━━━━━━━━━━━━━━━━\n"+s+
             "\n━━━━━━━━━━━━━━━━━━━━")
        time.sleep(0.65)

    edit(chat_id, mid,
         "━━━━━━━━━━━━━━━━━━━━\n"
         "🧪 <b>SANDBOX RESULT</b>\n"
         "━━━━━━━━━━━━━━━━━━━━\n\n"
         "🆔 Test: <code>TEST-AUTO</code>\n"
         "📡 Engine: <b>Sandbox</b>\n"
         "📊 Status: <b>TEST COMPLETE</b>\n"
         "🔐 Real card data: <b>NONE</b>\n"
         "💳 Real authorization: <b>NO</b>\n\n"
         "Resultado generado automáticamente con datos sintéticos.\n"
         "━━━━━━━━━━━━━━━━━━━━",
         kb([[{"text":"🔄 RUN AGAIN","callback_data":"check"},
              {"text":"👤 ACCOUNT","callback_data":"account"}],
             [{"text":"⚡ COMMAND CENTER","callback_data":"cmds"},
              {"text":"🏠 HOME","callback_data":"home"}]]))

def callback(q):
    answer(q["id"])
    m = q.get("message", {})
    uid = q["from"]["id"]
    chat = m["chat"]["id"]
    ensure_user(q["from"])
    d = q.get("data")

    if d == "home":
        send(chat, welcome(uid, q["from"].get("first_name","User")), home_kb(uid))
    elif d == "cmds":
        send(chat, commands(), cmds_kb())
    elif d == "check":
        sandbox(chat, uid)
    elif d == "account":
        send(chat, account(uid), back_kb())
    elif d == "credits":
        u = get_user(uid)
        send(chat, f"💳 <b>CREDITS</b>\n\nDisponibles: <b>{u['credits']}</b>\n\n1 Sandbox = 1 crédito.", back_kb())
    elif d == "premium":
        send(chat, "⭐ <b>PREMIUM</b>\n\nPremium es un plan del bot para funciones de interfaz y sandbox.", back_kb())
    elif d == "refs":
        send(chat, "📚 <b>REFERENCES</b>\n\nTelegram Bot API\nFlask\nSQLite\nSandbox Engine", back_kb())
    elif d == "updates":
        send(chat, "🟢 <b>UPDATES</b>\n\nv2.0 — Command Center, Sandbox automático, Diamond, créditos y cuentas.", back_kb())
    elif d == "gateways":
        send(chat, "⚡ <b>SANDBOX GATEWAYS</b>\n\n🟢 Alpha — ONLINE\n🟢 Beta — ONLINE\n🟢 Gamma — ONLINE\n🟡 Delta — TESTING\n\nSon módulos simulados; no conectan con procesadores reales.", back_kb())
    elif d == "tools":
        send(chat, "⚙ <b>TOOLS</b>\n\n🔎 Sandbox Analyzer\n📊 Statistics\n🧪 Test Generator\n⏱ Latency Simulator\n📝 Response Formatter", back_kb())
    elif d == "diamond":
        if uid == ADMIN_ID:
            send(chat, "━━━━━━━━━━━━━━━━━━━━\n💎 <b>BILL CYPHER — DIAMOND</b>\n━━━━━━━━━━━━━━━━━━━━\n\n👑 OWNER ACCESS\n💎 Diamond: <b>ACTIVATED</b>\n🟢 API: <b>ONLINE</b>\n🧪 Sandbox: <b>ACTIVE</b>\n🛡 Admin: <b>ACTIVE</b>\n\nPrivate owner console.", diamond_kb())
        else:
            send(chat, "⛔ Owner access only.")
    elif d in ("dcredits","dpremium","dstats"):
        if uid != ADMIN_ID:
            send(chat, "⛔ Owner access only.")
            return
        if d == "dcredits":
            send(chat, "➕ <b>ADD CREDITS</b>\n\n<code>/addcredit USER_ID AMOUNT</code>", diamond_kb())
        elif d == "dpremium":
            send(chat, "⭐ <b>PREMIUM CONTROL</b>\n\n<code>/premiumadd USER_ID</code>\n<code>/premiumoff USER_ID</code>", diamond_kb())
        else:
            con = db()
            users = con.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
            checks = con.execute("SELECT COALESCE(SUM(checks),0) n FROM users").fetchone()["n"]
            con.close()
            send(chat, f"📊 <b>STATISTICS</b>\n\n👥 Users: <b>{users}</b>\n🔎 Sandbox runs: <b>{checks}</b>\n🟢 API: ONLINE", diamond_kb())

def message(m):
    u = m.get("from", {})
    chat = m.get("chat", {}).get("id")
    if not u or not chat:
        return
    ensure_user(u)
    uid = u["id"]
    text = (m.get("text") or "").strip()
    if not text:
        return
    cmd = text.split()[0].split("@")[0].lower()
    p = text.split()

    if cmd == "/start":
        send(chat, welcome(uid, u.get("first_name","User")), home_kb(uid))
    elif cmd in ("/cmds","/help"):
        send(chat, commands(), cmds_kb())
    elif cmd in ("/me","/account"):
        send(chat, account(uid), back_kb())
    elif cmd == "/credits":
        send(chat, f"💳 <b>CREDITS</b>\n\nDisponibles: <b>{get_user(uid)['credits']}</b>", back_kb())
    elif cmd == "/premium":
        send(chat, "⭐ <b>PREMIUM</b>\n\nPlan premium del bot.", back_kb())
    elif cmd == "/check":
        sandbox(chat, uid)
    elif cmd == "/diamond":
        callback({"id":"0","from":u,"message":{"chat":{"id":chat}},"data":"diamond"})
    elif cmd == "/addcredit":
        if uid != ADMIN_ID:
            send(chat, "⛔ Admin only.")
        elif len(p) == 3:
            try:
                target, amount = int(p[1]), int(p[2])
                con = db()
                con.execute("UPDATE users SET credits=credits+? WHERE id=?", (amount,target))
                con.commit()
                con.close()
                send(chat, f"✅ Añadidos <b>{amount}</b> créditos a <code>{target}</code>.")
            except:
                send(chat, "Uso: /addcredit USER_ID AMOUNT")
        else:
            send(chat, "Uso: /addcredit USER_ID AMOUNT")
    elif cmd == "/premiumadd":
        if uid == ADMIN_ID and len(p) == 2:
            con=db(); con.execute("UPDATE users SET plan='PREMIUM' WHERE id=?", (int(p[1]),)); con.commit(); con.close()
            send(chat, "⭐ Premium activado.")
        else:
            send(chat, "⛔ Admin only.")
    elif cmd == "/premiumoff":
        if uid == ADMIN_ID and len(p) == 2:
            con=db(); con.execute("UPDATE users SET plan='FREE' WHERE id=?", (int(p[1]),)); con.commit(); con.close()
            send(chat, "⭐ Premium desactivado.")
        else:
            send(chat, "⛔ Admin only.")
    else:
        send(chat, "Usa /start o /cmds.", home_kb(uid))

def poll():
    init_db()
    api("deleteWebhook", {"drop_pending_updates": True})
    offset = 0
    print("Bill Cypher Chk started")
    while True:
        try:
            r = api("getUpdates", {
                "offset": offset,
                "timeout": 25,
                "allowed_updates": '["message","callback_query"]'
            })
            if not r.get("ok"):
                time.sleep(3)
                continue
            for update in r.get("result", []):
                offset = update["update_id"] + 1
                if "callback_query" in update:
                    callback(update["callback_query"])
                elif "message" in update:
                    message(update["message"])
        except Exception as e:
            print("Polling error:", repr(e))
            time.sleep(3)

@app.get("/")
def health():
    return "Bill Cypher Chk ONLINE", 200

@app.get("/health")
def health2():
    return {"status":"online","mode":"sandbox"}, 200

if __name__ == "__main__":
    threading.Thread(target=poll, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)
