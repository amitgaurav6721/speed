import os, socket, threading, time, requests, random, uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "nitro_v82_hybrid_ultimate_fixed_final"

# --- FIREBASE CONFIG ---
FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"

TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "VLT", "GPS", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "EMR", "ROADRPA"]
NEW_SUFFIX = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
FIXED_CS = "DDE3"

user_sessions = {}

def get_ist_time():
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

def get_sid():
    return session.get('device_sid', 'guest')

# --- DASHBOARD UI (FIXED) ---
DASH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 - HYBRID MASTER</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background: #000; color: #0f0; font-family: monospace; padding: 10px; display: flex; flex-direction: column; align-items: center; }
        .header-bar { width: 100%; max-width: 480px; display: flex; justify-content: space-between; padding: 10px; font-weight: bold; border-bottom: 1px solid #0f0; margin-bottom: 10px; }
        .logout-btn { color: #f00; text-decoration: none; border: 1px solid #f00; padding: 2px 8px; border-radius: 5px; }
        .score-bar { background: #050505; border: 1px solid #0f0; width: 100%; max-width: 480px; padding: 10px; border-radius: 10px; display: flex; justify-content: space-around; font-size: 11px; margin-bottom: 10px; box-shadow: 0 0 10px #0f0; }
        .box { border: 2px solid #0f0; padding: 20px; border-radius: 15px; width: 100%; max-width: 480px; background: #050505; box-shadow: 0 0 20px #0f0; }
        #map { height: 200px; width: 100%; border: 1px solid #0f0; border-radius: 10px; margin-bottom: 15px; }
        .metric { font-size: 55px; color: #fff; margin: 5px 0; font-weight: bold; text-align: center; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        input { width: 92%; padding: 12px; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; font-weight: bold; }
        .full { grid-column: span 2; }
        .btn { padding: 15px; font-size: 16px; cursor: pointer; border: none; border-radius: 8px; width: 100%; font-weight: bold; text-transform: uppercase; margin-top: 5px; }
        .start { background: #008000; color: #fff; } .stop { background: #800; color: #fff; } .reset { background: #333; color: #fff; }
        .gps-btn { background: #00f; color: #fff; padding: 10px; font-size: 12px; border-radius: 5px; margin-bottom: 10px; width: 100%; cursor: pointer; border: none; }
        .preview { background: #111; color: yellow; padding: 12px; font-size: 10px; word-break: break-all; margin-top: 10px; border: 1px dashed #0f0; min-height: 50px; }
    </style>
</head>
<body>
    <div class="header-bar">
        <span>ID: {{user_id}}</span>
        <a href="/logout" class="logout-btn">LOGOUT</a>
    </div>
    <div class="score-bar">
        <span>TOTAL: <span id="s_total">0</span></span>
        <span>OK: <span id="s_ok" style="color:#0f0">0</span></span>
        <span>FAIL: <span id="s_fail" style="color:#f00">0</span></span>
    </div>
    <div class="box">
        <div id="map"></div>
        <button class="gps-btn" onclick="getLocation()">📍 GET CURRENT LOCATION</button>
        <div class="metric" id="cnt">0</div>
        <form action="/action" method="post" class="grid">
            <div class="full"><input type="text" name="vno" id="vno" placeholder="VEHICLE NO" value="{{status.vno}}" oninput="this.value = this.value.toUpperCase(); updatePreview();"></div>
            <div class="full"><input type="text" name="imei" id="imei" placeholder="IMEI" value="{{status.imei}}" oninput="updatePreview();"></div>
            <div><input type="number" step="0.0000001" name="lat" id="lat" value="{{status.lat}}" oninput="updatePreview();"></div>
            <div><input type="number" step="0.0000001" name="lon" id="lon" value="{{status.lon}}" oninput="updatePreview();"></div>
            <div class="full"><div class="preview" id="preview">{{status.last_pkt}}</div></div>
            <button class="btn start full" name="btn" value="start">🚀 START HYBRID ENGINE</button>
            <button class="btn stop" name="btn" value="stop">🛑 STOP</button>
            <button class="btn reset" name="btn" value="reset">🔄 RESET</button>
        </form>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([{{status.lat}}, {{status.lon}}], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        var marker = L.marker([{{status.lat}}, {{status.lon}}]).addTo(map);

        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(pos => {
                    let lt = pos.coords.latitude.toFixed(7);
                    let ln = pos.coords.longitude.toFixed(7);
                    document.getElementById('lat').value = lt;
                    document.getElementById('lon').value = ln;
                    marker.setLatLng([lt, ln]);
                    map.setView([lt, ln], 15);
                    updatePreview();
                });
            }
        }

        function updatePreview() {
            let v = document.getElementById('vno').value;
            let i = document.getElementById('imei').value;
            let lt = document.getElementById('lat').value;
            let ln = document.getElementById('lon').value;
            let dt = new Date().toLocaleDateString('en-GB').replace(/\//g, '') + "," + new Date().toLocaleTimeString('en-GB').replace(/:/g, '');
            document.getElementById('preview').innerText = `$PVT,RA18,2.1.1,NR,01,L,${i},${v},1,${dt},${lt},N,${ln},E,...DDE3*`;
        }

        setInterval(() => {
            fetch('/data').then(r => r.json()).then(d => {
                document.getElementById('cnt').innerText = d.count;
                if(d.firing) document.getElementById('preview').innerText = d.last_pkt;
                if(d.score) {
                    document.getElementById('s_total').innerText = d.score.total || 0;
                    document.getElementById('s_ok').innerText = d.score.ok || 0;
                    document.getElementById('s_fail').innerText = d.score.fail || 0;
                }
            });
        }, 1000);
    </script>
</body>
</html>
"""

# --- BACKEND LOGIC ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/action', methods=['POST'])
def action():
    sid, val = get_sid(), request.form.get('btn')
    if val == "start":
        user_sessions[sid].update({
            "firing": True, 
            "session_id": get_ist_time().strftime('%H%M%S'), 
            "imei": request.form.get('imei'), 
            "vno": request.form.get('vno').upper(), 
            "lat": request.form.get('lat'), 
            "lon": request.form.get('lon')
        })
        # DB Sync for History
        log_to_firebase(session['user'], user_sessions[sid])
        threading.Thread(target=firing_engine, args=(sid,), daemon=True).start()
    elif val == "stop": user_sessions[sid]["firing"] = False
    elif val == "reset": user_sessions[sid].update({"firing": False, "count": 0, "imei": "", "vno": ""})
    return redirect(url_for('dashboard'))

# (Baki firing_engine, log_to_firebase aur login logic same rahega...)
