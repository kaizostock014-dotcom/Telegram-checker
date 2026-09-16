import os
import time
import sqlite3
import threading
import requests
from flask import Flask, request

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
PORT = int(os.environ.get("PORT", "10000"))
PUBLIC_URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
DB = "bot.db"
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

def db():
    c=sqlite3.connect(DB, check_same_thread=False)
    c.row_factory=sqlite3.Row
    return c

def init_db():
    c=db()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT DEFAULT '',
        first_name TEXT DEFAULT '',
        credits INTEGER DEFAULT 5,
        plan TEXT DEFAULT 'FREE',
        checks INTEGER DEFAULT 0)""")
    c.commit(); c.close()

def ensure_user(u):
    c=db()
    r=c.execute("SELECT id FROM users WHERE id=?",(u["id"],)).fetchone()
    if r is None:
        c.execute("INSERT INTO users VALUES(?,?,?,?,?,?)",
                  (u["id"],u.get("username",""),u.get("first_name","User"),5,"FREE",0))
    else:
        c.execute("UPDATE users SET username=?,first_name=? WHERE id=?",
                  (u.get("username",""),u.get("first_name","User"),u["id"]))
    c.commit(); c.close()

def get_user(uid):
    c=db(); r=c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone(); c.close(); return r

def tg(method,data=None):
    try:
        r=requests.post(f"{API}/{method}",data=data or {},timeout=25)
        j=r.json()
        print(f"[TG] {method}: {j}",flush=True)
        return j
    except Exception as e:
        print(f"[TG] {method} ERROR: {e}",flush=True)
        return {"ok":False}

def send(chat,text,k=None):
    d={"chat_id":chat,"text":text,"parse_mode":"HTML"}
    if k:d["reply_markup"]=k
    return tg("sendMessage",d)

def edit(chat,mid,text,k=None):
    d={"chat_id":chat,"message_id":mid,"text":text,"parse_mode":"HTML"}
    if k:d["reply_markup"]=k
    return tg("editMessageText",d)

def K(rows): return {"inline_keyboard":rows}

def home(uid):
    rows=[
      [{"text":"🔎 CHECK SANDBOX","callback_data":"check"},{"text":"👤 MI CUENTA","callback_data":"account"}],
      [{"text":"⭐ PREMIUM","callback_data":"premium"},{"text":"💳 CRÉDITOS","callback_data":"credits"}],
      [{"text":"⚡ COMMAND CENTER","callback_data":"cmds"}],
      [{"text":"📚 REFERENCES","callback_data":"refs"},{"text":"🟢 UPDATES","callback_data":"updates"}]]
    if uid==ADMIN_ID: rows.append([{"text":"💎 DIAMOND OWNER","callback_data":"diamond"}])
    return K(rows)

def back(): return K([[{"text":"⬅️ BACK","callback_data":"cmds"}],[{"text":"🏠 HOME","callback_data":"home"}]])

def cmds(): return K([
    [{"text":"⚡ GATEWAYS","callback_data":"gateways"},{"text":"⚙ TOOLS","callback_data":"tools"}],
    [{"text":"🔎 SANDBOX","callback_data":"check"},{"text":"👤 ACCOUNT","callback_data":"account"}],
    [{"text":"📚 REFERENCES","callback_data":"refs"},{"text":"🟢 UPDATES","callback_data":"updates"}],
    [{"text":"🏠 HOME","callback_data":"home"}]])

def diamond(): return K([
    [{"text":"➕ ADD CREDITS","callback_data":"dcredits"},{"text":"⭐ PREMIUM","callback_data":"dpremium"}],
    [{"text":"📊 STATISTICS","callback_data":"dstats"},{"text":"🧪 SANDBOX","callback_data":"check"}],
    [{"text":"🏠 HOME","callback_data":"home"}]])

def welcome(uid,name):
    u=get_user(uid)
    return (f"━━━━━━━━━━━━━━━━━━━━\n♯ <b>BILL CYPHER CHK</b> 𐓏\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n👋 Hello <b>{name}</b>\n"
            f"🔴 Mode: <b>SANDBOX</b>\n🟢 API Status: <b>ONLINE</b>\n"
            f"⚡ Version: <b>2.1</b>\n💳 Credits: <b>{u['credits']}</b>\n"
            f"⭐ Plan: <b>{u['plan']}</b>\n\n"
            "Use /cmds to open the command panel.\n"
            "━━━━━━━━━━━━━━━━━━━━")

def command_page():
    return ("━━━━━━━━━━━━━━━━━━━━\n⚡ <b>BILL CYPHER — COMMAND PANEL</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n📡 Gateways: <b>12</b>\n"
            "⚙ Tools: <b>8</b>\n🟢 API Status: <b>ONLINE</b>\n"
            "🧪 Engine: <b>SANDBOX</b>\n⚡ Version: <b>2.1</b>\n"
            "━━━━━━━━━━━━━━━━━━━━")

def run_check(chat,uid):
    c=db(); r=c.execute("SELECT credits FROM users WHERE id=?",(uid,)).fetchone()
    if not r or r["credits"]<1:
        c.close(); send(chat,"❌ <b>Sin créditos.</b>",home(uid)); return
    c.execute("UPDATE users SET credits=credits-1,checks=checks+1 WHERE id=?",(uid,))
    c.commit(); c.close()
    x=send(chat,"🧪 <b>SANDBOX ANALYZER</b>\n━━━━━━━━━━━━━━━━━━━━\n⏳ Starting...\n━━━━━━━━━━━━━━━━━━━━")
    mid=x.get("result",{}).get("message_id")
    if not mid:return
    for s in ["⏳ Starting engine...","⚡ Loading modules...","🔄 Running automatic test...","📊 Building report...","🟢 Complete!"]:
        edit(chat,mid,"🧪 <b>SANDBOX ANALYZER</b>\n━━━━━━━━━━━━━━━━━━━━\n"+s+"\n━━━━━━━━━━━━━━━━━━━━")
        time.sleep(.5)
    edit(chat,mid,"━━━━━━━━━━━━━━━━━━━━\n🧪 <b>SANDBOX RESULT</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "🆔 Test: <code>AUTO-TEST</code>\n📡 Engine: <b>Sandbox</b>\n"
         "📊 Status: <b>TEST COMPLETE</b>\n🔐 Real card data: <b>NONE</b>\n"
         "💳 Real authorization: <b>NO</b>\n\n"
         "Análisis automático con datos sintéticos.\n━━━━━━━━━━━━━━━━━━━━",
         K([[{"text":"🔄 RUN AGAIN","callback_data":"check"},{"text":"👤 ACCOUNT","callback_data":"account"}],
            [{"text":"⚡ COMMAND CENTER","callback_data":"cmds"},{"text":"🏠 HOME","callback_data":"home"}]]))

def handle(u):
    if "callback_query" in u:
        q=u["callback_query"]; tg("answerCallbackQuery",{"callback_query_id":q["id"]})
        user=q["from"]; ensure_user(user); uid=user["id"]; chat=q["message"]["chat"]["id"]; d=q.get("data","")
        if d=="home":send(chat,welcome(uid,user.get("first_name","User")),home(uid))
        elif d=="cmds":send(chat,command_page(),cmds())
        elif d=="check":run_check(chat,uid)
        elif d=="account":
            x=get_user(uid); send(chat,f"👤 <b>MY ACCOUNT</b>\n\n🆔 <code>{uid}</code>\n💳 Credits: <b>{x['credits']}</b>\n⭐ Plan: <b>{x['plan']}</b>\n🔎 Runs: <b>{x['checks']}</b>",back())
        elif d=="credits":send(chat,f"💳 <b>CREDITS</b>\n\nDisponibles: <b>{get_user(uid)['credits']}</b>",back())
        elif d=="premium":send(chat,"⭐ <b>PREMIUM</b>\n\nPlan premium para funciones del bot.",back())
        elif d=="refs":send(chat,"📚 <b>REFERENCES</b>\n\nTelegram Bot API\nFlask\nSQLite\nSandbox Engine",back())
        elif d=="updates":send(chat,"🟢 <b>UPDATES</b>\n\nv2.1 — Webhook + Command Panel + Sandbox.",back())
        elif d=="gateways":send(chat,"⚡ <b>SANDBOX GATEWAYS</b>\n\n🟢 Alpha — ONLINE\n🟢 Beta — ONLINE\n🟡 Delta — TESTING\n\nMódulos simulados.",back())
        elif d=="tools":send(chat,"⚙ <b>TOOLS</b>\n\n🔎 Sandbox Analyzer\n📊 Statistics\n🧪 Test Generator\n⏱ Latency Simulator",back())
        elif d=="diamond" and uid==ADMIN_ID:
            send(chat,"━━━━━━━━━━━━━━━━━━━━\n💎 <b>DIAMOND OWNER</b>\n━━━━━━━━━━━━━━━━━━━━\n\n👑 OWNER ACCESS\n🟢 API ONLINE\n🧪 SANDBOX ACTIVE\n🛡 ADMIN ACTIVE",diamond())
        elif d=="dcredits" and uid==ADMIN_ID:send(chat,"➕ <b>ADD CREDITS</b>\n\n<code>/addcredit USER_ID AMOUNT</code>",diamond())
        elif d=="dpremium" and uid==ADMIN_ID:send(chat,"⭐ <b>PREMIUM CONTROL</b>\n\n<code>/premiumadd USER_ID</code>\n<code>/premiumoff USER_ID</code>",diamond())
        elif d=="dstats" and uid==ADMIN_ID:
            c=db(); a=c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]; b=c.execute("SELECT COALESCE(SUM(checks),0) n FROM users").fetchone()["n"]; c.close()
            send(chat,f"📊 <b>STATISTICS</b>\n\n👥 Users: <b>{a}</b>\n🔎 Runs: <b>{b}</b>",diamond())
        return
    m=u.get("message")
    if not m:return
    user=m.get("from",{}); chat=m.get("chat",{}).get("id")
    if not user or not chat:return
    ensure_user(user); uid=user["id"]; text=(m.get("text") or "").strip()
    if not text:return
    p=text.split(); cmd=p[0].split("@")[0].lower()
    if cmd=="/start":send(chat,welcome(uid,user.get("first_name","User")),home(uid))
    elif cmd in ("/cmds","/help"):send(chat,command_page(),cmds())
    elif cmd in ("/me","/account"):
        x=get_user(uid);send(chat,f"👤 <b>MY ACCOUNT</b>\n\n🆔 <code>{uid}</code>\n💳 Credits: <b>{x['credits']}</b>\n⭐ Plan: <b>{x['plan']}</b>\n🔎 Runs: <b>{x['checks']}</b>",back())
    elif cmd=="/credits":send(chat,f"💳 <b>CREDITS</b>\n\nDisponibles: <b>{get_user(uid)['credits']}</b>",back())
    elif cmd=="/premium":send(chat,"⭐ <b>PREMIUM</b>\n\nPlan premium para funciones del bot.",back())
    elif cmd=="/check":run_check(chat,uid)
    elif cmd=="/diamond":
        if uid==ADMIN_ID: send(chat,"💎 <b>DIAMOND OWNER</b>\n\n👑 OWNER ACCESS\n🟢 API ONLINE\n🧪 SANDBOX ACTIVE",diamond())
        else:send(chat,"⛔ Owner access only.")
    elif cmd=="/addcredit" and uid==ADMIN_ID and len(p)==3:
        try:
            target=int(p[1]); amount=int(p[2]); c=db(); c.execute("UPDATE users SET credits=credits+? WHERE id=?",(amount,target)); c.commit(); c.close(); send(chat,"✅ Créditos añadidos.")
        except:send(chat,"Uso: /addcredit USER_ID AMOUNT")
    elif cmd=="/premiumadd" and uid==ADMIN_ID and len(p)==2:
        try:
            target=int(p[1]);c=db();c.execute("UPDATE users SET plan='PREMIUM' WHERE id=?",(target,));c.commit();c.close();send(chat,"⭐ Premium activado.")
        except:send(chat,"❌ USER_ID inválido.")
    elif cmd=="/premiumoff" and uid==ADMIN_ID and len(p)==2:
        try:
            target=int(p[1]);c=db();c.execute("UPDATE users SET plan='FREE' WHERE id=?",(target,));c.commit();c.close();send(chat,"⭐ Premium desactivado.")
        except:send(chat,"❌ USER_ID inválido.")
    else:send(chat,"Usa /start o /cmds.",home(uid))

@app.get("/")
def root(): return "Bill Cypher Chk ONLINE",200

@app.get("/health")
def health(): return {"status":"online","telegram":"webhook","sandbox":True},200

@app.post("/telegram")
def telegram():
    u=request.get_json(silent=True)
    print("[WEBHOOK] received:",bool(u),flush=True)
    if u:
        try: handle(u)
        except Exception as e: print("[UPDATE ERROR]",repr(e),flush=True)
    return "OK",200

def setup():
    init_db()
    if not BOT_TOKEN:
        print("FATAL: BOT_TOKEN is empty",flush=True); return
    me=tg("getMe")
    if not me.get("ok"):
        print("FATAL: Telegram rejected BOT_TOKEN",flush=True); return
    print("BOT:",me["result"].get("username"),flush=True)
    if not PUBLIC_URL:
        print("FATAL: RENDER_EXTERNAL_URL is empty",flush=True); return
    url=PUBLIC_URL+"/telegram"
    result=tg("setWebhook",{"url":url,"drop_pending_updates":"true","allowed_updates":'["message","callback_query"]'})
    print("WEBHOOK:",url,flush=True)
    print("WEBHOOK SET:",result,flush=True)
    info=tg("getWebhookInfo")
    print("WEBHOOK INFO:",info,flush=True)

if __name__=="__main__":
    setup()
    app.run(host="0.0.0.0",port=PORT)
