import os,re,time,random,sqlite3,threading,logging
from datetime import datetime,timezone
import requests
from flask import Flask,jsonify

# BILL CYPHER CHK 3.0 - SANDBOX EDITION
# No real card/CVV/bank/payment authorization is performed.
TOKEN=os.getenv('BOT_TOKEN','').strip(); ADMIN_ID=os.getenv('ADMIN_ID','').strip()
PORT=int(os.getenv('PORT','10000')); DB=os.getenv('DB_FILE','bill_cypher.db')
GIF=os.getenv('ANIMATION_FILE_ID','').strip(); API=f'https://api.telegram.org/bot{TOKEN}'
app=Flask(__name__); S=requests.Session(); LOCK=threading.Lock(); logging.basicConfig(level=logging.INFO,format='%(asctime)s | %(levelname)s | %(message)s')

def con():
    x=sqlite3.connect(DB,timeout=20); x.row_factory=sqlite3.Row; return x

def init():
    with LOCK:
        x=con(); x.execute('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT,first_name TEXT,credits INTEGER DEFAULT 5,premium_until INTEGER DEFAULT 0,created_at INTEGER,updated_at INTEGER)'''); x.execute('''CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,action TEXT,created_at INTEGER)'''); x.commit(); x.close()

def user(u):
    uid=int(u['id']); now=int(time.time()); un=u.get('username') or ''; fn=u.get('first_name') or 'User'
    with LOCK:
        x=con(); x.execute('''INSERT INTO users(id,username,first_name,credits,premium_until,created_at,updated_at) VALUES(?,?,?,5,0,?,?) ON CONFLICT(id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name,updated_at=excluded.updated_at''',(uid,un,fn,now,now)); x.commit(); x.close()

def get(uid):
    with LOCK:
        x=con(); r=x.execute('SELECT * FROM users WHERE id=?',(int(uid),)).fetchone(); x.close(); return r

def find(t):
    t=str(t).lstrip('@').strip()
    with LOCK:
        x=con(); r=x.execute('SELECT * FROM users WHERE '+('id=?' if t.isdigit() else 'lower(username)=lower(?)')+' LIMIT 1',(int(t) if t.isdigit() else t,)).fetchone(); x.close(); return r

def log(uid,a):
    with LOCK:
        x=con(); x.execute('INSERT INTO logs(user_id,action,created_at) VALUES(?,?,?)',(uid,a,int(time.time()))); x.commit(); x.close()

def credits(uid):
    with LOCK:
        x=con(); r=x.execute('SELECT credits FROM users WHERE id=?',(uid,)).fetchone(); x.close()
    return int(r['credits']) if r else 0

def take(uid):
    with LOCK:
        x=con(); r=x.execute('SELECT credits FROM users WHERE id=?',(uid,)).fetchone()
        if not r or r['credits']<1: x.close(); return False
        x.execute('UPDATE users SET credits=credits-1,updated_at=? WHERE id=?',(int(time.time()),uid)); x.commit(); x.close(); return True

def add(uid,n):
    with LOCK:
        x=con(); x.execute('UPDATE users SET credits=credits+?,updated_at=? WHERE id=?',(n,int(time.time()),uid)); x.commit(); x.close()

def premium(uid,until):
    with LOCK:
        x=con(); x.execute('UPDATE users SET premium_until=?,updated_at=? WHERE id=?',(until,int(time.time()),uid)); x.commit(); x.close()

def isp(r): return bool(r and int(r['premium_until'] or 0)>int(time.time()))
def owner(uid): return bool(ADMIN_ID and str(uid)==ADMIN_ID)
def esc(v): return str(v).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def pexpiry(r):
    if not isp(r): return 'FREE'
    return datetime.fromtimestamp(int(r['premium_until']),timezone.utc).astimezone().strftime('%d %b %Y • %H:%M')

def tg(m,p=None,t=35):
    if not TOKEN: return {'ok':False,'description':'BOT_TOKEN missing'}
    try:
        r=S.post(f'{API}/{m}',json=p or {},timeout=t); d=r.json()
        if not d.get('ok'): logging.error('Telegram %s: %s',m,d)
        return d
    except Exception as e: logging.error('Telegram %s exception: %s',m,e); return {'ok':False,'description':str(e)}

def send(cid,text,k=None):
    p={'chat_id':cid,'text':text,'parse_mode':'HTML','disable_web_page_preview':True}
    if k:p['reply_markup']=k
    return tg('sendMessage',p)

def edit(cid,mid,text,k=None):
    p={'chat_id':cid,'message_id':mid,'text':text,'parse_mode':'HTML','disable_web_page_preview':True}
    if k:p['reply_markup']=k
    return tg('editMessageText',p)

def cb(cid,text='',alert=False): return tg('answerCallbackQuery',{'callback_query_id':cid,'text':text,'show_alert':alert})

def anim(cid,text,k=None):
    if not GIF:return send(cid,text,k)
    p={'chat_id':cid,'animation':GIF,'caption':text,'parse_mode':'HTML'}
    if k:p['reply_markup']=k
    r=tg('sendAnimation',p)
    return r if r.get('ok') else send(cid,text,k)

def kb(rows): return {'inline_keyboard':rows}
def btn(t,d): return {'text':t,'callback_data':d}
def back(): return kb([[btn('↩️ HOME','home')]])

def home(u):
    r=get(u['id']); plan='DIAMOND 💠' if owner(u['id']) else ('PREMIUM 💎' if isp(r) else 'FREE')
    return f'''╭━━━━━━━━━━━━━━━━━━━━╮\n       ⚡ <b>BILL CYPHER</b>\n             <b>CHK</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\nHello <b>{esc(u.get("first_name") or "SpaceBoy")}</b> 👋\nWelcome to the control center.\n\n┌─ <b>SYSTEM</b> ──────────┐\n│ 🟢 API       <b>ONLINE</b>\n│ 🧪 ENGINE    <b>READY</b>\n│ 🤖 VERSION   <b>3.0</b>\n│ 💳 PLAN      <b>{plan}</b>\n│ 💰 CREDITS   <b>{credits(u["id"])}</b>\n└─────────────────────┘\n\nSelect a module below.'''

def home_k(uid):
    r=[[btn('⚡ CHECK SANDBOX','check'),btn('👤 ACCOUNT','account')],[btn('💎 PREMIUM','premium'),btn('💰 CREDITS','credits')],[btn('🛠 TOOLS','tools'),btn('📊 STATUS','status')],[btn('📚 REFERENCES','refs'),btn('📢 UPDATES','updates')],[btn('⚙️ COMMANDS','cmds')]]
    if owner(uid):r.append([btn('💠 DIAMOND','diamond')])
    return kb(r)

def panel(): return '''╭━━━━━━━━━━━━━━━━━━━━╮\n      ⚡ <b>BILL CYPHER PANEL</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n📡 <b>SYSTEM OVERVIEW</b>\n━━━━━━━━━━━━━━━━━━━━\n⚡ Modules    <b>08</b>\n🛠 Tools      <b>12</b>\n🟢 API        <b>ONLINE</b>\n🧪 Sandbox    <b>READY</b>\n🤖 Version    <b>3.0</b>\n━━━━━━━━━━━━━━━━━━━━\n\nChoose a module.'''

def panel_k(): return kb([[btn('⚡ CHECK','check'),btn('👤 ACCOUNT','account')],[btn('💎 PREMIUM','premium'),btn('💰 CREDITS','credits')],[btn('🛠 TOOLS','tools'),btn('📊 STATUS','status')],[btn('↩️ HOME','home')]])

def pages(name,uid):
    r=get(uid)
    if name=='account': return f'''╭━━━━━━━━━━━━━━━━━━━━╮\n        👤 <b>ACCOUNT</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n👤 Username: <b>@{esc(r["username"] or "not_set")}</b>\n🆔 ID: <code>{uid}</code>\n💳 Plan: <b>{"PREMIUM 💎" if isp(r) else "FREE"}</b>\n💰 Credits: <b>{r["credits"]}</b>\n⏳ Premium: <b>{esc(pexpiry(r))}</b>'''
    if name=='premium': return '''╭━━━━━━━━━━━━━━━━━━━━╮\n          💎 <b>PREMIUM</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\nPremium uses an exact expiration time.\n\nOwner examples:\n<code>/premiumadd FRED 2d</code>\n<code>/premiumadd FRED 1w</code>\n<code>/premiumadd FRED 1m</code>\n<code>/premiumadd FRED 2m</code>\n<code>/premiumoff FRED</code>\n\nUnits: h • d • w • m • y'''
    if name=='credits': return f'''╭━━━━━━━━━━━━━━━━━━━━╮\n          💰 <b>CREDITS</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\nAvailable: <b>{credits(uid)}</b>\n\nEach Sandbox check consumes 1 credit.'''
    if name=='tools': return '''╭━━━━━━━━━━━━━━━━━━━━╮\n           🛠 <b>TOOLS</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n⚡ Sandbox Engine\n👤 Account Inspector\n💎 Premium Manager\n💰 Credit Manager\n📊 System Status\n\nAll checks in this edition are <b>Sandbox only</b>.'''
    if name=='status': return '''╭━━━━━━━━━━━━━━━━━━━━╮\n          📊 <b>STATUS</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n🟢 Telegram API  ONLINE\n🟢 Polling       ACTIVE\n🟢 Database      READY\n🟢 Sandbox       READY\n🤖 Version       3.0\n\nNo real payment-card or banking authorization is performed.'''
    if name=='refs': return '''╭━━━━━━━━━━━━━━━━━━━━╮\n        📚 <b>REFERENCES</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n/start — Home\n/cmds — Command panel\n/check — Sandbox\n/me — Account\n/premium — Premium\n/credits — Credits\n/status — Status'''
    if name=='updates': return '''╭━━━━━━━━━━━━━━━━━━━━╮\n          📢 <b>UPDATES</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n<b>v3.0</b>\n• New interface\n• Premium expiration\n• Automatic webhook cleanup\n• Polling diagnostics\n• Animated Sandbox workflow'''
    if name=='diamond': return '''╭━━━━━━━━━━━━━━━━━━━━╮\n          💠 <b>DIAMOND</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n<code>/premiumadd FRED 2d</code>\n<code>/premiumoff FRED</code>\n<code>/addcredit FRED 25</code>\n<code>/userinfo FRED</code>'''

def duration(s):
    m=re.fullmatch(r'(\d+)\s*([hdwmy])',s.lower())
    if not m:return None
    n=int(m.group(1)); u=m.group(2)
    return n*{'h':3600,'d':86400,'w':604800,'m':2592000,'y':31536000}[u] if n>0 else None

def sandbox(cid,mid,uid):
    stages=[('⚡','Initializing Sandbox Engine',15),('🔎','Analyzing synthetic request',32),('🛰️','Connecting to test gateway',52),('🧪','Running simulation',72),('📡','Reading simulated response',90),('✅','Finalizing result',100)]
    for icon,label,pct in stages:
        bar='█'*(pct//10)+'░'*(10-pct//10)
        edit(cid,mid,f'''╭━━━━━━━━━━━━━━━━━━━━╮\n       ⚡ <b>BILL CYPHER</b>\n          <b>SANDBOX</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n{icon} <b>{label}</b>\n\n<code>[{bar}] {pct}%</code>\n\n🧪 Mode: <b>SIMULATION</b>'''); time.sleep(.55)
    status=random.choice(['APPROVED','DECLINED','REVIEW'])
    edit(cid,mid,f'''╭━━━━━━━━━━━━━━━━━━━━╮\n          ⚡ <b>RESULT</b>\n╰━━━━━━━━━━━━━━━━━━━━╯\n\n🧪 Status: <b>{status}</b>\n📡 Response: <b>Synthetic gateway response</b>\n🔒 Mode: <b>SANDBOX</b>\n\nThis result is synthetic and does not contact a bank, payment processor, or real card network.''',back()); log(uid,'sandbox:'+status)

def command(msg):
    text=(msg.get('text') or '').strip(); u=msg.get('from') or {}; cid=msg.get('chat',{}).get('id')
    if not text.startswith('/'):return
    user(u); p=text.split(); c=p[0].split('@')[0].lower(); a=p[1:]; uid=int(u['id'])
    if c in ('/start','/home'): anim(cid,home(u),home_k(uid)); return
    if c in ('/cmds','/commands','/panel'): send(cid,panel(),panel_k()); return
    if c in ('/me','/account'): send(cid,pages('account',uid),back()); return
    if c=='/premium': send(cid,pages('premium',uid),back()); return
    if c=='/credits': send(cid,pages('credits',uid),back()); return
    if c=='/status': send(cid,pages('status',uid),back()); return
    if c=='/tools': send(cid,pages('tools',uid),back()); return
    if c=='/refs': send(cid,pages('refs',uid),back()); return
    if c=='/updates': send(cid,pages('updates',uid),back()); return
    if c=='/diamond': send(cid,pages('diamond',uid),back()) if owner(uid) else send(cid,'⛔ Owner only.'); return
    if c=='/check':
        if not take(uid): send(cid,'❌ <b>Not enough credits.</b>',back()); return
        r=send(cid,'⚡ <b>Starting Sandbox...</b>\n\n<code>[░░░░░░░░░░] 0%</code>')
        if r.get('ok'):
            threading.Thread(target=sandbox,args=(cid,r['result']['message_id'],uid),daemon=True).start()
        else:add(uid,1)
        return
    if c=='/addcredit':
        if not owner(uid):send(cid,'⛔ Owner only.');return
        if len(a)!=2 or not a[1].isdigit() or int(a[1])<=0:send(cid,'Usage: <code>/addcredit FRED 10</code>');return
        r=find(a[0]);
        if not r:send(cid,'❌ User not found. They must press /start first.');return
        add(r['id'],int(a[1]));send(cid,f'✅ Added <b>{a[1]}</b> credits to <b>{esc(a[0])}</b>.');return
    if c=='/premiumadd':
        if not owner(uid):send(cid,'⛔ Owner only.');return
        if len(a)!=2:send(cid,'Usage: <code>/premiumadd FRED 2d</code>');return
        sec=duration(a[1]); r=find(a[0])
        if not sec:send(cid,'❌ Duration invalid. Use 2h, 2d, 1w, 1m, 2m or 1y.');return
        if not r:send(cid,'❌ User not found. They must press /start first.');return
        until=max(int(time.time()),int(r['premium_until'] or 0))+sec; premium(r['id'],until)
        dt=datetime.fromtimestamp(until,timezone.utc).astimezone().strftime('%d %b %Y • %H:%M')
        send(cid,f'💎 <b>PREMIUM ACTIVATED</b>\n\nUser: <b>{esc(a[0])}</b>\nAdded: <b>{esc(a[1])}</b>\nExpires: <b>{dt}</b>');return
    if c=='/premiumoff':
        if not owner(uid):send(cid,'⛔ Owner only.');return
        if len(a)!=1:send(cid,'Usage: <code>/premiumoff FRED</code>');return
        r=find(a[0]);
        if not r:send(cid,'❌ User not found.');return
        premium(r['id'],0);send(cid,f'🛑 Premium removed from <b>{esc(a[0])}</b>.');return
    if c=='/userinfo':
        if not owner(uid):send(cid,'⛔ Owner only.');return
        if len(a)!=1:send(cid,'Usage: <code>/userinfo FRED</code>');return
        r=find(a[0]);
        if not r:send(cid,'❌ User not found.');return
        send(cid,f'''👤 <b>USER INFO</b>\n\nUsername: <b>@{esc(r['username'] or 'not_set')}</b>\nID: <code>{r['id']}</code>\nCredits: <b>{r['credits']}</b>\nPlan: <b>{'PREMIUM 💎' if isp(r) else 'FREE'}</b>\nPremium: <b>{esc(pexpiry(r))}</b>''');return
    send(cid,'❓ Unknown command. Use <code>/cmds</code>.')

def callback(q):
    cid=q.get('id'); d=q.get('data',''); m=q.get('message') or {}; chat=m.get('chat',{}).get('id'); mid=m.get('message_id'); u=q.get('from') or {}; uid=int(u['id']); user(u); cb(cid)
    if d=='home':edit(chat,mid,home(u),home_k(uid))
    elif d=='cmds':edit(chat,mid,panel(),panel_k())
    elif d in ('account','premium','credits','tools','status','refs','updates','diamond'):
        if d=='diamond' and not owner(uid):cb(cid,'Owner only.',True);return
        edit(chat,mid,pages(d,uid),back())
    elif d=='check':
        if not take(uid):cb(cid,'Not enough credits.',True);return
        edit(chat,mid,'⚡ <b>Starting Sandbox...</b>\n\n<code>[░░░░░░░░░░] 0%</code>')
        threading.Thread(target=sandbox,args=(chat,mid,uid),daemon=True).start()

def startup():
    if not TOKEN:logging.error('FATAL: BOT_TOKEN is missing in Render Environment.');return False
    logging.info('Webhook before cleanup: %s',tg('getWebhookInfo',t=15)); logging.info('deleteWebhook: %s',tg('deleteWebhook',{'drop_pending_updates':False},15))
    me=tg('getMe',t=15)
    if not me.get('ok'):logging.error('FATAL: getMe failed. BOT_TOKEN is invalid or revoked.');return False
    logging.info('Connected as @%s (id=%s)',me['result'].get('username'),me['result'].get('id')); return True

def poll():
    if not startup():return
    off=None;logging.info('Polling started.')
    while True:
        p={'timeout':25,'allowed_updates':['message','callback_query']}
        if off is not None:p['offset']=off
        r=tg('getUpdates',p,35)
        if not r.get('ok'):time.sleep(5);continue
        for up in r.get('result',[]):
            off=up['update_id']+1
            try:
                if 'message' in up:command(up['message'])
                elif 'callback_query' in up:callback(up['callback_query'])
            except Exception:logging.exception('Update error')

@app.get('/')
def root():return jsonify(bot='Bill Cypher Chk',version='3.0',status='online',engine='sandbox')
@app.get('/health')
def health():return jsonify(status='ok')
@app.get('/ping')
def ping():return 'pong'

if __name__=='__main__':
    init(); threading.Thread(target=poll,daemon=True,name='telegram-polling').start(); logging.info('Starting Bill Cypher Chk on port %s',PORT); app.run(host='0.0.0.0',port=PORT,debug=False,use_reloader=False)
