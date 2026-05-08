from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
import threading
import time
from datetime import datetime, timedelta, timezone

# 🔗 Module Connections
from database import fetch_vehicle_data, sync_to_firebase, get_system_messages
from engine import GpsEngine

app = FastAPI()
stop_event = threading.Event()
stop_event.set()
lock = threading.Lock()
engine = GpsEngine(stop_event, lock)

@app.get("/init")
async def init(v:str, i:str, lt:str, ln:str, t:str, background_tasks: BackgroundTasks):
    if stop_event.is_set():
        v_up, t_up = v.upper().strip(), t.upper().strip()
        try: lt_f, ln_f = float(lt), float(ln)
        except: return {"ok": False}
        
        engine.total_sent = 0
        stop_event.clear()
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        payload = {"Vehicle_No": v_up, "IMEI_No": str(i), "Lat": f"{lt_f:.7f}", "Lon": f"{ln_f:.7f}", "Saved_Tag": t_up, "Status": "Active", "Time": now.strftime('%H:%M:%S')}
        background_tasks.add_task(sync_to_firebase, v_up, payload)
        threading.Thread(target=engine.handshake_worker, args=(t_up, i, v_up, lt_f, ln_f), daemon=True).start()
    return {"ok": True}

@app.get("/status")
def status(): return {"c": engine.total_sent, "f": not stop_event.is_set()}

@app.get("/stop")
def stop(): stop_event.set(); return {"ok": True}

@app.get("/fetch_data")
async def fetch_api(vno: str): return await fetch_vehicle_data(vno)

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
        .chk-group { display: flex; align-items: center; justify-content: flex-start; gap: 10px; margin-top: 15px; color: #fff; font-size: 14px; padding-left: 5px; }
        button { width:100%; padding:14px; margin-top:10px; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; font-weight:bold; border-radius:5px; transition: 0.3s; }
        button:active { transform: scale(0.95); }
        .audit-box { display:flex; justify-content:space-between; background:rgba(0,40,0,0.5); border:1px solid #0f0; padding:8px; margin-top:10px; border-radius:5px; font-size:10px; text-align:center; }
        .audit-box b { display:block; color:#0f0; font-size:14px; }
        .progress-container { width: 100%; background: #111; border: 1px solid #333; height: 12px; margin-top: 15px; border-radius: 10px; overflow: hidden; }
        .progress-bar { width: 0%; height: 100%; background: linear-gradient(90deg, #0f0, #00ffaa); box-shadow: 0 0 15px #0f0; transition: width 0.4s; }
        #map { width:100%; height:250px; margin-top:15px; border:1px solid #0f0; border-radius:10px; }
        .nav { width:95%; max-width:440px; display:flex; justify-content:space-between; font-size:12px; margin-top:15px; color:#fff; }
        .user-wall { background:#001a00; border:1px solid #0f0; padding:10px; margin-top:10px; font-size:13px; display:none; color:red; border-radius:5px; width:100%; }
    </style></head><body>

    <div class="login-box" id="loginScreen">
        <h1 style="text-align:center;font-size:24px;letter-spacing:5px;">Ghop-Ghop GPS</h1>
        <input type="text" id="m_num" placeholder="MOBILE NUMBER">
        <input type="password" id="m_pass" placeholder="PASSWORD">
        <div class="chk-group"><input type="checkbox" id="rem" checked> <label for="rem">Remember Me</label></div>
        <button onclick="login()" style="background:#0f0;color:#000;border:none;margin-top:20px;">ACCESS SYSTEM</button>
    </div>

    <div class="nav" id="dashNav" style="display:none;"><span>USER: <b id="u_name" style="color:#0f0"></b></span><span onclick="logout()" style="color:red;cursor:pointer;font-weight:bold;">[ LOGOUT ]</span></div>
    
    <div class="dashboard" id="dashScreen" style="display:none;">
        <div class="audit-box"><div>OK<b id="a_ok">0</b></div><div>FAIL<b id="a_fail">0</b></div><div>ERROR<b id="a_err">0</b></div><div>TOTAL<b id="a_total">0</b></div></div>
        <div class="user-wall" id="u_wall"></div>
        <input type="text" id="v" onblur="smartFetch()" placeholder="VEHICLE NUMBER">
        <input type="text" id="i" placeholder="IMEI">
        <select id="tagSel" onchange="chkMan()"><option value="MARK">MARK (DEFAULT)</option><option value="MANUAL">+ ADD NEW TAG</option></select>
        <input type="text" id="manTag" placeholder="ENTER NEW TAG" style="display:none;border-color:yellow;">
        <div class="chk-group"><input type="checkbox" id="useDef" checked> <label for="useDef">Use Default Location</label></div>
        <div style="display:flex;gap:5px;margin-top:10px;"><input type="text" id="lt" placeholder="LAT"><input type="text" id="ln" placeholder="LON"></div>
        <button onclick="st()" id="startBtn" style="background:#0f0;color:#000;font-size:18px;">START INJECTION</button>
        <button onclick="sp()" style="color:red;border-color:red;">ABORT</button>
        <button onclick="location.reload()" style="color:yellow;border-color:yellow;font-size:11px;">RESET SYSTEM</button>
        <div class="progress-container"><div class="progress-bar" id="pBar"></div></div>
        <div id="map"></div>
        <div style="display:flex;justify-content:space-between;margin-top:15px;font-size:14px;"><span>SENT: <b id="c">0</b></span><span id="st_text" style="color:lime">IDLE</span></div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const DB = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com";
        const TAGS = ["RA18", "WTEX", "ASPL", "LOCT14A", "ACT1", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"];
        let map, marker, curUser = null, mon = null;

        function initMap() { if (map) return; map = L.map('map').setView([24.91, 83.79], 13); L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png').addTo(map); marker = L.marker([24.91, 83.79]).addTo(map); }
        async function login() {
            let n = document.getElementById('m_num').value.trim(), p = document.getElementById('m_pass').value.trim();
            let res = await fetch(`${DB}/users/${n}.json`);
            let data = await res.json();
            if(data && data.password == p) { 
                curUser = { ...data, mobile: n }; 
                if(document.getElementById('rem').checked) localStorage.setItem('nitro_user', JSON.stringify(curUser));
                showDash(); 
            } else alert("WRONG PASSWORD");
        }
        window.onload = () => { let s = localStorage.getItem('nitro_user'); if(s){ curUser = JSON.parse(s); showDash(); } }
        async function showDash() {
            document.getElementById('loginScreen').style.display='none';
            document.getElementById('dashScreen').style.display='block';
            document.getElementById('dashNav').style.display='flex';
            document.getElementById('u_name').innerText = curUser.mobile;
            let sel = document.getElementById('tagSel');
            TAGS.forEach(t => { let o = document.createElement('option'); o.value = t; o.innerText = t; sel.appendChild(o); });
            initMap();
        }
        function chkMan() { document.getElementById('manTag').style.display = (document.getElementById('tagSel').value == "MANUAL") ? 'block' : 'none'; }
        async function smartFetch() {
            let v = document.getElementById('v').value.toUpperCase().trim();
            if(!v) return;
            let res = await fetch(`/fetch_data?vno=${v}`);
            let d = await res.json();
            if(d.IMEI_No){
                document.getElementById('i').value = d.IMEI_No;
                let lat = document.getElementById('useDef').checked ? (curUser.lat || "24.9189") : (d.Lat || "24.9192");
                let lon = document.getElementById('useDef').checked ? (curUser.Lon || "83.7905") : (d.Lon || "83.7905");
                document.getElementById('lt').value = parseFloat(lat).toFixed(7);
                document.getElementById('ln').value = parseFloat(lon).toFixed(7);
                map.setView([lat, lon], 15); marker.setLatLng([lat, lon]);
            }
        }
        function st() {
            let v=document.getElementById('v').value, i=document.getElementById('i').value, lt=document.getElementById('lt').value, ln=document.getElementById('ln').value, t=document.getElementById('tagSel').value;
            if(t=="MANUAL") t = document.getElementById('manTag').value;
            fetch(`/init?v=${v}&i=${i}&lt=${lt}&ln=${ln}&t=${t}`);
            document.getElementById('st_text').innerText="FIRING";
            mon = setInterval(() => {
                fetch('/status').then(r=>r.json()).then(d=> {
                    document.getElementById('c').innerText = d.c;
                    document.getElementById('a_total').innerText = d.c;
                    document.getElementById('a_ok').innerText = d.c;
                    document.getElementById('pBar').style.width = (d.c % 101) + "%";
                });
            }, 1000);
        }
        function sp() { fetch('/stop'); clearInterval(mon); document.getElementById('st_text').innerText="IDLE"; }
        function logout() { localStorage.removeItem('nitro_user'); location.reload(); }
    </script></body></html>
    """
