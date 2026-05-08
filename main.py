from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
import threading
import time
from datetime import datetime, timedelta, timezone

# 🔥 CONNECTION LOGIC: Inhe teeno files ko aaps mein jodne ke liye
from database import fetch_vehicle_data, sync_to_firebase, get_system_messages
from engine import GpsEngine

app = FastAPI()
stop_event = threading.Event()
stop_event.set()
lock = threading.Lock()

# 🏎️ Main Engine Initialize
engine = GpsEngine(stop_event, lock)

@app.get("/init")
async def init(v:str, i:str, lt:str, ln:str, t:str, background_tasks: BackgroundTasks):
    if stop_event.is_set():
        v_up, t_up = v.upper().strip(), t.upper().strip()
        try:
            # 🛑 NAN protection before firing
            lt_f, ln_f = float(lt), float(ln)
        except: return {"ok": False, "error": "Invalid Coords"}
        
        engine.total_sent = 0
        stop_event.clear()
        
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        payload = {
            "Vehicle_No": v_up, 
            "IMEI_No": str(i), 
            "Lat": f"{lt_f:.7f}", 
            "Lon": f"{ln_f:.7f}", 
            "Saved_Tag": t_up, 
            "Status": "Active", 
            "Time": now.strftime('%H:%M:%S')
        }
        
        # Firebase Sync (database.py function)
        background_tasks.add_task(sync_to_firebase, v_up, payload)
        
        # Start Engine (engine.py worker)
        threading.Thread(target=engine.handshake_worker, args=(t_up, i, v_up, lt_f, ln_f), daemon=True).start()
    return {"ok": True}

@app.get("/fetch_data")
async def fetch_api(vno: str):
    return await fetch_vehicle_data(vno)

@app.get("/status")
def status(): 
    return {"c": engine.total_sent, "f": not stop_event.is_set()}

@app.get("/stop")
def stop(): 
    stop_event.set()
    return {"ok": True}

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Ghop-Ghop GPS</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background:#000; color:#0f0; font-family:monospace; margin:0; display:flex; flex-direction:column; align-items:center; min-height:100vh; overflow-x:hidden; }
        .login-box, .dashboard { width:95%; max-width:440px; border:2px solid #0f0; padding:15px; background:rgba(0,10,0,0.95); border-radius:15px; box-shadow: 0 0 25px #0f0; margin-top:20px; box-sizing: border-box; }
        input, select { width:100%; background:#000; border:1px solid #333; color:#0f0; padding:12px; margin-top:10px; outline:none; text-transform:uppercase; font-size:16px; border-radius:5px; }
        .chk-group { display: flex; align-items: center; justify-content: flex-start; gap: 10px; margin-top: 15px; color: #fff; font-size: 14px; }
        .chk-group input { width: 22px; height: 22px; cursor: pointer; }
        button { width:100%; padding:14px; margin-top:10px; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; font-weight:bold; font-size:14px; border-radius:5px; }
        .audit-box { display:flex; justify-content:space-between; background:rgba(0,40,0,0.5); border:1px solid #0f0; padding:8px; margin-bottom:10px; border-radius:5px; font-size:10px; color:#fff; text-align:center; }
        .audit-box b { display:block; color:#0f0; font-size:14px; }
        .user-wall { background:#001a00; border:1px solid #0f0; padding:10px; margin-bottom:10px; font-size:13px; display:none; color:red; border-radius:5px; }
        #map { width:100%; height:200px; margin-top:15px; border:1px solid #0f0; border-radius:10px; }
    </style></head><body>

    <div class="login-box" id="loginScreen">
        <h1 style="text-align:center;font-size:24px;letter-spacing:5px;">Ghop-Ghop GPS</h1>
        <input type="text" id="m_num" placeholder="MOBILE NUMBER">
        <input type="password" id="m_pass" placeholder="PASSWORD">
        <button onclick="login()" style="background:#0f0;color:#000;border:none;margin-top:20px;">ACCESS SYSTEM</button>
    </div>

    <div class="dashboard" id="dashScreen" style="display:none;">
        <div class="audit-box">
            <div>OK<b id="a_ok">0</b></div>
            <div>FAIL<b id="a_fail">0</b></div>
            <div>ERROR<b id="a_err">0</b></div>
            <div>TOTAL<b id="a_total">0</b></div>
        </div>
        <div class="user-wall" id="u_wall"></div>
        <input type="text" id="v" onblur="smartFetch()" placeholder="VEHICLE NUMBER">
        <input type="text" id="i" placeholder="IMEI">
        <select id="tagSel"><option value="ALL">SEND ALL TAGS (DEFAULT)</option></select>
        <div class="chk-group"><input type="checkbox" id="useDef" checked> <label for="useDef">Use Default Location</label></div>
        <div style="display:flex;gap:5px;margin-top:10px;">
            <input type="text" id="lt" placeholder="LAT">
            <input type="text" id="ln" placeholder="LON">
        </div>
        <button onclick="st()" id="startBtn" style="background:#0f0;color:#000;font-size:18px;border:none;">START INJECTION</button>
        <button onclick="sp()" style="color:red;border-color:red;">ABORT</button>
        <div id="map"></div>
        <div style="display:flex;justify-content:space-between;margin-top:15px;font-size:14px;">
            <span>SENT: <b id="c">0</b></span>
            <span id="st_text" style="color:lime">IDLE</span>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const DB = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com";
        const DEFAULT_TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"];
        let map, marker, curUser = null, mon = null;

        function initMap() { 
            if (map) return; 
            map = L.map('map').setView([24.91, 83.79], 13); 
            L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png').addTo(map); 
            marker = L.marker([24.91, 83.79]).addTo(map); 
        }

        async function login() {
            let n = document.getElementById('m_num').value.trim();
            let p = document.getElementById('m_pass').value.trim();
            let res = await fetch(`${DB}/users/${n}.json`);
            let data = await res.json();
            if(data && data.password == p) { curUser = { ...data, mobile: n }; showDash(); }
            else alert("WRONG PASSWORD");
        }

        async function showDash() {
            document.getElementById('loginScreen').style.display='none';
            document.getElementById('dashScreen').style.display='block';
            initMap();
            
            // 🔥 Priority Messages Logic
            let wall = document.getElementById('u_wall');
            let bRes = await fetch(`${DB}/broadcast.json?t=${Date.now()}`);
            let bData = await bRes.json();
            if(bData && bData.text) {
                wall.innerHTML = `● <b>ADMIN:</b> ${bData.text}`;
                wall.style.display = 'block';
            }
            
            let sel = document.getElementById('tagSel');
            DEFAULT_TAGS.forEach(t => { 
                let o = document.createElement('option'); o.value = t; o.innerText = t; sel.appendChild(o); 
            });
        }

        async function smartFetch() {
            let v = document.getElementById('v').value.toUpperCase().trim();
            if(!v) return;
            let res = await fetch(`/fetch_data?vno=${v}&t=${Date.now()}`);
            let d = await res.json();
            if(d.IMEI_No){
                document.getElementById('i').value = d.IMEI_No;
                // 🛑 IRON-CLAD NAN FIX: Checking for Lon (Capital L)
                let lat = document.getElementById('useDef').checked ? curUser.lat : (d.Lat || d.lat || "24.9192");
                let lon = document.getElementById('useDef').checked ? (curUser.Lon || curUser.lon) : (d.Lon || d.lon || "83.7905");
                document.getElementById('lt').value = parseFloat(lat).toFixed(7);
                document.getElementById('ln').value = parseFloat(lon).toFixed(7);
            }
        }

        function st() {
            let v=document.getElementById('v').value, i=document.getElementById('i').value, lt=document.getElementById('lt').value, ln=document.getElementById('ln').value, t=document.getElementById('tagSel').value;
            fetch(`/init?v=${v}&i=${i}&lt=${lt}&ln=${ln}&t=${t}`);
            document.getElementById('st_text').innerText="FIRING";
            mon = setInterval(() => {
                fetch('/status').then(r=>r.json()).then(d=> {
                    document.getElementById('c').innerText = d.c;
                });
            }, 1000);
        }

        function sp() { fetch('/stop'); clearInterval(mon); document.getElementById('st_text').innerText="IDLE"; }
    </script></body></html>
    """
