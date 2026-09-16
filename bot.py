import os
import time
import random
import sqlite3
import threading
import requests
from flask import Flask, jsonify

# ============================================================
# BILL CYPHER CHK — KAORI-STYLE SAFE SANDBOX BOT
# Visual animations + animated loading + inline menus.
# No real card/CVV/funds/authorization processing.
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
PORT = int(os.getenv("PORT", "10000"))
DB_PATH = os.getenv("DB_PATH", "bot.db")
ANIMATION_URL = os.getenv("ANIMATION_URL", "").strip()
VERSION = "1.3"
GATEWAYS = 73
TOOLS = 12

app = Flask(__name__)
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DB_LOCK = threading.Lock()


def db():
    c = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with DB_LOCK:
        c = db()
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY, username TEXT DEFAULT '', first_name TEXT DEFAULT '',
            credits INTEGER DEFAULT 5, plan TEXT DEFAULT 'FREE', checks INTEGER DEFAULT 0,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP, last_check TEXT DEFAULT ''
        )""")
        c.commit(); c.close()


def tg(method, data=None):
    try:
        r = requests.post(f"{API}/{method}", json=data or {}, timeout=35)
        out = r.json()
        if not out.get("ok"): print("[TG ERROR]", method, out)
        return out
    except Exception as e:
        print("[TG EXCEPTION]", method, e)
        return None


def ensure_user(u):
    with DB_LOCK:
        c = db()
        row = c.execute("SELECT id FROM users WHERE id=?", (u["id"],)).fetchone()
        if row:
            c.execute("UPDATE users SET username=?, first_name=? WHERE id=?",
                      (u.get("username", "") or "", u.get("first_name", "") or "", u["id"]))
        else:
            c.execute("INSERT INTO users(id,username,first_name) VALUES(?,?,?)",
                      (u["id"], u.get("username", "") or "", u.get("first_name", "") or ""))
        c.commit(); c.close()


def get_user(uid):
    with DB_LOCK:
        c = db(); r = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone(); c.close(); return r


def send(chat_id, text, kb=None):
    d = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb: d["reply_markup"] = kb
    return tg("sendMessage", d)


def edit(chat_id, mid, text, kb=None):
    d = {"chat_id": chat_id, "message_id": mid, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb: d["reply_markup"] = kb
    return tg("editMessageText", d)


def animation(chat_id, caption, kb=None):
    if not ANIMATION_URL:
        return send(chat_id, caption, kb)
    d = {"chat_id": chat_id, "animation": ANIMATION_URL, "caption": caption, "parse_mode": "HTML"}
    if kb: d["reply_markup"] = kb
    return tg("sendAnimation", d)


def callback(cid):
    tg("answerCallbackQuery", {"callback_query_id": cid})


def home_kb(uid):
    rows = [
        [{"text":"⚡ Check Sandbox","callback_data":"check"},{"text":"👤 Account","callback_data":"account"}],
        [{"text":"💎 Premium","callback_data":"premium"},{"text":"💰 Credits","callback_data":"credits"}],
        [{"text":"⚙ Command Panel","callback_data":"panel"}],
        [{"text":"📚 References","callback_data":"refs"},{"text":"📢 Updates","callback_data":"updates"}]
    ]
    if uid == ADMIN_ID: rows.append([{"text":"💠 Diamond","callback_data":"diamond"}])
    return {"inline_keyboard": rows}


def panel_kb():
    return {"inline_keyboard":[
        [{"text":"⚡ Gateways","callback_data":"gateways"},{"text":"⚙ Tools","callback_data":"tools"}],
        [{"text":"👤 Account","callback_data":"account"},{"text":"💰 Credits","callback_data":"credits"}],
        [{"text":"💎 Premium","callback_data":"premium"},{"text":"💠 Diamond","callback_data":"diamond"}],
        [{"text":"🔙 Back","callback_data":"home"}]
    ]}


def back_kb(): return {"inline_keyboard":[[{"text":"🔙 Back","callback_data":"home"}]]}


def home_text(u):
    name = (u.get("first_name") or u.get("username") or "SpaceBoy").replace("<","&lt;").replace(">","&gt;")
    return ("🔴━━━━━━━━━━━━━━━━━━🔴\n"
            "♯ <b>Bill Cypher Chk</b> 𐓏\n"
            "🔴━━━━━━━━━━━━━━━━━━🔴\n\n"
            f"Hello <b>{name}</b>, Welcome to <b>Bill Cypher Chk</b>\n\n"
            "🔴━━━━━━━━━━━━━━━━━━🔴\n\n"
            "Use <code>/cmds</code> to open the interactive command panel.\n\n"
            f"Bot Version: <b>{VERSION}</b>\n"
            "Api Status: <b>Online 🟢</b>\n\n"
            "🧪 Sandbox Engine: <b>Ready</b>\n"
            "🔴━━━━━━━━━━━━━━━━━━🔴")


def panel_text():
    return ("🔴━━━━━━━━━━━━━━━━━━🔴\n"
            "♯ <b>Bill Cypher Chk | Command Panel</b>\n"
            "🔴━━━━━━━━━━━━━━━━━━🔴\n\n"
            f"Gateways: <b>{GATEWAYS}</b> | Tools: <b>{TOOLS}</b>\n"
            "Api Status: <b>Online 🟢</b>\n"
            f"Bot Version: <b>{VERSION}</b>\n\n"
            "Select an option below.")


def animated_check(chat_id, uid):
    row = get_user(uid)
    if not row: return
    if row["plan"] != "PREMIUM" and row["credits"] <= 0:
        send(chat_id, "❌ <b>Sin créditos</b>\n\nUsa /premium para consultar los planes.", back_kb()); return
    with DB_LOCK:
        c = db()
        if row["plan"] != "PREMIUM":
            c.execute("UPDATE users SET credits=credits-1, checks=checks+1, last_check=datetime('now') WHERE id=?", (uid,))
        else:
            c.execute("UPDATE users SET checks=checks+1, last_check=datetime('now') WHERE id=?", (uid,))
        c.commit(); c.close()

    msg = send(chat_id, "⚡ <b>Bill Cypher Chk</b>\n\n▰▱▱▱▱ 20%\n🔄 Initializing sandbox...")
    if not msg or not msg.get("ok"): return
    mid = msg["result"]["message_id"]
    frames = [
        "⚡ <b>Bill Cypher Chk</b>\n\n▰▱▱▱▱ 20%\n🔄 Initializing sandbox...",
        "⚡ <b>Bill Cypher Chk</b>\n\n▰▰▰▱▱ 50%\n🔎 Analyzing simulation...",
        "⚡ <b>Bill Cypher Chk</b>\n\n▰▰▰▰▱ 80%\n📊 Generating response...",
        "⚡ <b>Bill Cypher Chk</b>\n\n▰▰▰▰▰ 100%\n🟢 Test complete!"
    ]
    for f in frames:
        time.sleep(.75)
        edit(chat_id, mid, f)
    latency = random.randint(120,420)
    result = random.choice(["APPROVED (SIMULATED)","DECLINED (SIMULATED)","TEST COMPLETE"])
    edit(chat_id, mid,
         "⚡ <b>Bill Cypher Chk | Sandbox</b>\n"
         "━━━━━━━━━━━━━━━━━━━━\n\n"
         "🟢 <b>TEST COMPLETE</b>\n\n"
         "Gateway: <b>SANDBOX</b>\n"
         "Mode: <b>SIMULATION</b>\n"
         f"Response: <b>{result}</b>\n"
         f"Latency: <b>{latency}ms</b>\n\n"
         "━━━━━━━━━━━━━━━━━━━━\n"
         "⚠️ No real card was processed.\n"
         "⚠️ No CVV, funds or bank authorization was performed.", back_kb())


def account(chat_id, uid):
    r=get_user(uid)
    send(chat_id, f"👤 <b>ACCOUNT</b>\n━━━━━━━━━━━━━━━━━━━━\n\nID: <code>{r['id']}</code>\nUsername: @{r['username'] or 'none'}\nPlan: <b>{r['plan']}</b>\nCredits: <b>{r['credits']}</b>\nChecks: <b>{r['checks']}</b>", back_kb())


def handle_command(chat_id, u, text):
    ensure_user(u); p=text.split(); cmd=p[0].split('@')[0].lower(); args=p[1:]
    if cmd=="/start": animation(chat_id,home_text(u),home_kb(u["id"]))
    elif cmd in ("/cmds","/commands"): send(chat_id,panel_text(),panel_kb())
    elif cmd in ("/check","/chk"): animated_check(chat_id,u["id"])
    elif cmd in ("/me","/account"): account(chat_id,u["id"])
    elif cmd=="/credits":
        r=get_user(u["id"]); send(chat_id,f"💰 <b>CREDITS</b>\n\nAvailable: <b>{r['credits']}</b>\nPlan: <b>{r['plan']}</b>\n\n1 Sandbox Test = 1 credit.",back_kb())
    elif cmd=="/premium": send(chat_id,"💎 <b>PREMIUM</b>\n\n⚡ Sandbox ilimitado\n🚀 Prioridad\n📊 Estadísticas avanzadas\n\nContacta al owner para activación.",back_kb())
    elif cmd=="/gateways": send(chat_id,f"⚡ <b>GATEWAYS</b>\n\nAvailable: <b>{GATEWAYS}</b>\nStatus: 🟢 Online\nMode: Sandbox",back_kb())
    elif cmd=="/tools": send(chat_id,f"⚙ <b>TOOLS</b>\n\nAvailable: <b>{TOOLS}</b>\n🧪 Sandbox Analyzer\n📊 Statistics\n👤 Account\n💰 Credits\n💎 Premium",back_kb())
    elif cmd=="/refs": send(chat_id,"📚 <b>REFERENCES</b>\n\nBill Cypher Chk\nTelegram Bot API\nSandbox Documentation",back_kb())
    elif cmd=="/updates": send(chat_id,f"📢 <b>UPDATES</b>\n\nVersion: <b>{VERSION}</b>\n🟢 Core\n🟢 Sandbox\n🟢 Credits\n🟢 Premium",back_kb())
    elif cmd=="/diamond": diamond(chat_id,u["id"])
    elif cmd=="/stats": stats(chat_id,u["id"])
    elif cmd=="/addcredit": addcredit(chat_id,u["id"],args)
    elif cmd=="/premiumadd": prem(chat_id,u["id"],args,True)
    elif cmd=="/premiumoff": prem(chat_id,u["id"],args,False)
    else: send(chat_id,"❓ Comando no reconocido. Usa /cmds.",panel_kb())


def diamond(chat_id,uid):
    if uid!=ADMIN_ID: send(chat_id,"⛔ Access denied.",back_kb()); return
    send(chat_id,"💠 <b>DIAMOND OWNER PANEL</b>\n━━━━━━━━━━━━━━━━━━━━\n\n👑 Owner: <b>ACTIVE</b>\n🟢 Bot: <b>ONLINE</b>\n🧪 Sandbox: <b>ONLINE</b>\n\nUse /stats, /addcredit, /premiumadd or /premiumoff.",back_kb())


def stats(chat_id,uid):
    if uid!=ADMIN_ID: send(chat_id,"⛔ Access denied."); return
    with DB_LOCK:
        c=db(); users=c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]; premn=c.execute("SELECT COUNT(*) n FROM users WHERE plan='PREMIUM'").fetchone()["n"]; checks=c.execute("SELECT COALESCE(SUM(checks),0) n FROM users").fetchone()["n"]; c.close()
    send(chat_id,f"📊 <b>STATISTICS</b>\n\n👥 Users: <b>{users}</b>\n💎 Premium: <b>{premn}</b>\n🧪 Checks: <b>{checks}</b>\n⚡ Gateways: <b>{GATEWAYS}</b>\n⚙ Tools: <b>{TOOLS}</b>",back_kb())


def addcredit(chat_id,uid,args):
    if uid!=ADMIN_ID: send(chat_id,"⛔ Access denied."); return
    if len(args)!=2: send(chat_id,"Uso: <code>/addcredit ID CANTIDAD</code>"); return
    try: target,amount=int(args[0]),int(args[1])
    except: send(chat_id,"❌ Datos inválidos."); return
    with DB_LOCK:
        c=db(); c.execute("UPDATE users SET credits=credits+? WHERE id=?",(amount,target)); c.commit(); c.close()
    send(chat_id,f"✅ Added <b>{amount}</b> credits to <code>{target}</code>.")


def prem(chat_id,uid,args,on):
    if uid!=ADMIN_ID: send(chat_id,"⛔ Access denied."); return
    if len(args)!=1: send(chat_id,"Uso: <code>/premiumadd ID</code>" if on else "Uso: <code>/premiumoff ID</code>"); return
    try: target=int(args[0])
    except: send(chat_id,"❌ ID inválido."); return
    with DB_LOCK:
        c=db(); c.execute("UPDATE users SET plan=? WHERE id=?",("PREMIUM" if on else "FREE",target)); c.commit(); c.close()
    send(chat_id,"💎 Premium activated." if on else "✅ Premium disabled.")


def callbacks(q):
    callback(q["id"]); m=q.get("message",{}); chat=m.get("chat",{}); u=q.get("from",{}); cid=chat.get("id"); uid=u.get("id"); data=q.get("data")
    if not cid or not uid:return
    ensure_user(u)
    if data=="home": edit(cid,m["message_id"],home_text(u),home_kb(uid))
    elif data=="panel": edit(cid,m["message_id"],panel_text(),panel_kb())
    elif data=="check": animated_check(cid,uid)
    elif data=="account": account(cid,uid)
    elif data=="credits":
        r=get_user(uid); edit(cid,m["message_id"],f"💰 <b>CREDITS</b>\n\nAvailable: <b>{r['credits']}</b>\nPlan: <b>{r['plan']}</b>\n\n1 Sandbox Test = 1 credit.",back_kb())
    elif data=="premium": edit(cid,m["message_id"],"💎 <b>PREMIUM</b>\n\n⚡ Sandbox ilimitado\n🚀 Prioridad\n📊 Estadísticas avanzadas\n\nContacta al owner para activación.",back_kb())
    elif data=="gateways": edit(cid,m["message_id"],f"⚡ <b>GATEWAYS</b>\n\nAvailable: <b>{GATEWAYS}</b>\nStatus: 🟢 Online\nMode: Sandbox",back_kb())
    elif data=="tools": edit(cid,m["message_id"],f"⚙ <b>TOOLS</b>\n\nAvailable: <b>{TOOLS}</b>\n🧪 Sandbox Analyzer\n📊 Statistics\n👤 Account\n💰 Credits",back_kb())
    elif data=="refs": edit(cid,m["message_id"],"📚 <b>REFERENCES</b>\n\nTelegram Bot API\nSandbox Documentation",back_kb())
    elif data=="updates": edit(cid,m["message_id"],f"📢 <b>UPDATES</b>\n\nVersion: <b>{VERSION}</b>\n🟢 Core\n🟢 Sandbox\n🟢 Credits",back_kb())
    elif data=="diamond": diamond(cid,uid)
    elif data=="stats": stats(cid,uid)


def process(update):
    try:
        if "message" in update:
            m=update["message"]; u=m.get("from"); text=m.get("text","") or ""
            if u and text.startswith("/"): handle_command(m["chat"]["id"],u,text)
            elif u and text.lower() in ("menu","panel","cmds"): send(m["chat"]["id"],panel_text(),panel_kb())
        elif "callback_query" in update: callbacks(update["callback_query"])
    except Exception as e: print("[UPDATE ERROR]",e)


def poll():
    if not BOT_TOKEN: print("[FATAL] BOT_TOKEN missing"); return
    me=tg("getMe")
    if not me or not me.get("ok"): print("[FATAL] Telegram token/API error"); return
    print("[TG] Connected:","@"+me["result"].get("username","unknown"))
    tg("deleteWebhook",{"drop_pending_updates":False})
    print("[TG] Webhook cleared. Polling active.")
    offset=None
    while True:
        try:
            d={"timeout":25,"limit":100,"allowed_updates":["message","callback_query"]}
            if offset is not None:d["offset"]=offset
            r=tg("getUpdates",d)
            if not r or not r.get("ok"): time.sleep(4); continue
            for u in r.get("result",[]):
                offset=u["update_id"]+1; process(u)
        except Exception as e: print("[POLL ERROR]",e); time.sleep(5)


@app.get("/")
def root(): return jsonify({"bot":"Bill Cypher Chk","version":VERSION,"status":"online","engine":"sandbox"})

@app.get("/health")
def health(): return jsonify({"status":"ok"})


def main():
    init_db()
    threading.Thread(target=poll,daemon=True).start()
    app.run(host="0.0.0.0",port=PORT,debug=False,use_reloader=False)

if __name__=="__main__": main()
