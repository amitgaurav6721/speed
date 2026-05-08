from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
import threading
import time
from datetime import datetime, timedelta, timezone

# 🔗 Connections
from database import fetch_vehicle_data, sync_to_firebase
from engine import GpsEngine

app = FastAPI()
stop_event = threading.Event()
stop_event.set()
lock = threading.Lock()
engine = GpsEngine(stop_event, lock)

TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"]

@app.get("/init")
async def init(v:str, i:str, lt:str, ln:str, t:str, background_tasks: BackgroundTasks):
    if stop_event.is_set():
        v_up, t_up = v.upper().strip(), t.upper().strip()
        engine.total_sent = 0
        stop_event.clear()
        
        # Fire ALL tags if selected, else fire single
        target_tags = TAGS if t_up == "ALL" else [t_up]
        for tag in target_tags:
            threading.Thread(target=engine.handshake_worker, args=(tag, i, v_up, lt, ln), daemon=True).start()
    return {"ok": True}

@app.get("/status")
def status(): 
    return {"c": engine.total_sent, "f": not stop_event.is_set()}

@app.get("/stop")
def stop(): 
    stop_event.set()
    return {"ok": True}

@app.get("/fetch_data")
async def fetch_api(vno: str):
    # 🔥 Database Fetch Hard Fix: Formatting response for frontend
    data = await fetch_vehicle_data(vno)
    if data:
        return {
            "found": True, 
            "imei": data.get('IMEI_No'), 
            "lat": data.get('Lat'), 
            "lon": data.get('Lon')
        }
    return {"found": False}

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
        .login-box, .dashboard { width:95%; max-width:440px; border:2px solid #0f0; padding:20px; background:rgba(0,10,0,0.95); border-radius:15px; box-shadow: 0 0 25px #0f0; margin-top:20px; }
        .conn-box { display: flex; justify-content: space-around; background: #111; padding: 8px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #333; font-size: 10px; }
        .dot { height: 8px; width: 8px; background-color: #333; border-radius: 50%; display: inline-block; margin-right: 4px; }
        .online { background-color: #0f0; box-shadow: 0 0 8px #0f0; }
        input, select { width:100%; background:#000; border:1px solid #333; color:#0f0; padding:12px; margin-top:10px; outline:none; text-transform:uppercase; font-size:16px; border-radius:5px; }
        .chk-group { display: flex; align-items: center; gap: 12px; margin-top: 15px; margin-bottom: 10px; color: #fff; font-size: 13px; cursor: pointer; }
        .chk-group input { width: 18px; height: 18px; accent-color: #0f0; cursor: pointer; margin: 0; }
        button { width:100%; padding:14px; margin-top:10px; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; font-weight:bold; border-radius:5px; }
        .audit-box { display:flex; justify-content:space-between; background:rgba(0,40,0,0.5); border:1px solid #0f0; padding:8px; margin-top:10px; border-radius:5px; font-size:10px; text-align:center; }
        .audit-box b { display:block; color:#0f0; font-size:14px; }
        .progress-container { width: 100%; background: #111; border: 1px solid #333; height: 10px; margin-top: 15px; border-radius: 10px; overflow: hidden; }
        .progress-bar { width: 0%; height: 100%; background: #0f0; box-shadow: 0 0 15px #0f0; transition: width 0.4s; }
        #map { width:100%; height:200px; margin-top:15px; border:1px solid #0f0; border-radius:10px; }
        .user-wall { background:#001a00; border:1px solid #0f0; padding:12px; margin-top:10px; font-size:13px; display:none; color:red; border-radius:5px; width:100%; }
        .nav { width:95%; max-width:440px; display:flex; justify-content:space-between; font-size:12px; margin-top:15px; color:#fff; }
        #overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:1000; justify-content:center; align-items:center; }
        .popup { width:350px; border:2px solid #ff0; padding:25px; background:#111; color:#fff; text-align:center; border-radius:15px; box-shadow: 0 0 30px #ff0; }
        .popup button { background:#ff0; color:#000; border:none; margin-top:20px; width:100%; font-weight:bold; }
    </style></head><body>

    <div id="overlay"><div class="popup"><h3>📢 SYSTEM ALERT</h3><p id="bc_text">...</p><button onclick="closeBC()">UNDERSTOOD</button></div></div>

    <div class="login-box" id="loginScreen">
        <h1 style="text-align:center;font-size:24px;letter-spacing:5px;">Ghop-Ghop GPS</h1>
        <input type="text" id="m_num" placeholder="MOBILE NUMBER">
        <input type="password" id="m_pass" placeholder="PASSWORD">
        <div class="chk-group" style="justify-content: center;"><input type="checkbox" id="rem" checked> <label for="rem">Remember Me</label></div>
        <button onclick="login()" style="background:#0f0;color:#000;border:none;margin-top:20px;">ACCESS SYSTEM</button>
        <div style="text-align:center; margin-top:20px;"><a href="https://wa.me/917464010787" style="color:#0f0;text-decoration:none;">[ CONTACT ADMIN ]</a></div>
    </div>

    <div class="nav" id="dashNav" style="display:none;"><span>USER: <b id="u_name" style="color:#0f0"></b></span><span onclick="logout()" style="color:red;cursor:pointer;font-weight:bold;">[ LOGOUT ]</span></div>
    
    <div class="dashboard" id="dashScreen" style="display:none;">
        <div class="conn-box"><span><span class="dot online" id="m_dot"></span>MAIN.PY</span><span><span class="dot" id="e_dot"></span>ENGINE.PY</span><span><span class="dot" id="d_dot"></span>DATABASE.PY</span></div>
        <div class="audit-box"><div>OK<b id="a_ok">0</b></div><div>FAIL<b id="a_fail">0</b></div><div>TOTAL<b id="a_total">0</b></div></div>
        <div class="user-wall" id="u_wall"></div>
        <input type="text" id="v" onblur="smartFetch()" placeholder="VEHICLE NUMBER">
        <input type="text" id="i" placeholder="IMEI">
        <select id="tagSel">
            <option value="ALL">ALL TAGS (MULTI-STREAM)</option>
            <option value="RA18">RA18</option><option value="WTEX">WTEX</option><option value="MARK">MARK</option>
            <option value="ASPL">ASPL</option><option value="LOCT14A">LOCT14A</option><option value="ACT1">ACT1</option>
            <option value="AMAZON">AMAZON</option><option value="BBOX77">BBOX77</option><option value="EGAS">EGAS</option>
            <option value="MENT">MENT</option><option value="MIJO">MIJO</option><option value="ROADRPA">ROADRPA</option><option value="GRL">GRL</option>
        </select>
        <div class="chk-group"><input type="checkbox" id="useDef"> <label for="useDef">Use Profile Default Location</label></div>
        <div style="display:flex;gap:5px;margin-top:10px;"><input type="text" id="lt" placeholder="LAT"><input type="text" id="ln" placeholder="LON"></div>
        <button onclick="getLocation()" style="font-size:11px;border-style:dashed;margin-top:5px;">[[ GET CURRENT LOCATION ]]</button>
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
        let map, marker, curUser = null, currentBCID = "";

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
            document.getElementById('loginScreen').style.display='none'; document.getElementById('dashScreen').style.display='block'; document.getElementById('dashNav').style.display='flex'; document.getElementById('u_name').innerText = curUser.mobile;
            initMap();
            fetch(`${DB}/app_config/broadcast.json`).then(r=>r.json()).then(bc => {
                if(bc && bc.id !== localStorage.getItem('last_bc_id')) { currentBCID = bc.id; document.getElementById('bc_text').innerText = bc.text; document.getElementById('overlay').style.display = 'flex'; }
            });
            fetch(`${DB}/user_messages/${curUser.mobile}.json`).then(r=>r.json()).then(mData => {
                if(mData && mData.text) { let wall = document.getElementById('u_wall'); wall.innerHTML = `● <b>ADMIN UPDATE:</b> ${mData.text}`; wall.style.display = 'block'; }
            });
        }
        function closeBC() { localStorage.setItem('last_bc_id', currentBCID); document.getElementById('overlay').style.display = 'none'; }
        function getLocation() { navigator.geolocation.getCurrentPosition(p=>{ document.getElementById('lt').value = p.coords.latitude.toFixed(7); document.getElementById('ln').value = p.coords.longitude.toFixed(7); map.setView([p.coords.latitude, p.coords.longitude], 15); marker.setLatLng([p.coords.latitude, p.coords.longitude]); }, (e)=>alert(e.message), {enableHighAccuracy:true}); }
        setInterval(() => { fetch('/status').then(r=>r.json()).then(d=> { 
            document.getElementById('m_dot').classList.add('online'); 
            document.getElementById('d_dot').classList.add('online'); 
            if(d.f) document.getElementById('e_dot').classList.add('online'); else document.getElementById('e_dot').classList.remove('online'); 
            document.getElementById('c').innerText = d.c; document.getElementById('a_total').innerText = d.c; document.getElementById('a_ok').innerText = d.c; 
            document.getElementById('pBar').style.width = (d.c % 101) + "%"; 
        }); }, 1000);

        async function smartFetch() { 
            let v = document.getElementById('v').value.toUpperCase().trim(); 
            if(!v) return; 
            let res = await fetch(`/fetch_data?vno=${v}`); 
            let d = await res.json(); 
            if(d.found){ 
                document.getElementById('i').value = d.imei; 
                // 🔥 Default Location Logic
                let lat = document.getElementById('useDef').checked ? (curUser.lat || d.lat) : d.lat;
                let lon = document.getElementById('useDef').checked ? (curUser.lon || d.lon) : d.lon;
                document.getElementById('lt').value = lat; 
                document.getElementById('ln').value = lon; 
                map.setView([lat, lon], 15); 
                marker.setLatLng([lat, lon]);
            } 
        }

        function st() { let v=document.getElementById('v').value, i=document.getElementById('i').value, lt=document.getElementById('lt').value, ln=document.getElementById('ln').value, t=document.getElementById('tagSel').value; fetch(`/init?v=${v}&i=${i}&lt=${lt}&ln=${ln}&t=${t}`); document.getElementById('st_text').innerText="FIRING"; }
        function sp() { fetch('/stop'); document.getElementById('st_text').innerText="IDLE"; }
        function logout() { localStorage.removeItem('nitro_user'); location.reload(); }
    </script></body></html>
    """
