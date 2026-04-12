import os, socket, threading, time, requests, uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "nitro_v82_hybrid_final_v3"

# --- FIREBASE CONFIG ---
FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"

TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "VLT", "GPS", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "EMR", "ROADRPA"]
NEW_SUFFIX = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
FIXED_CS = "DDE3"

user_sessions = {}

def get_ist_time():
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

# --- UI (DASHBOARD) ---
DASH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 - HYBRID MASTER</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background: #000; color: #0f0; font-family: monospace; padding: 10px; display: flex; flex-direction: column; align-items: center; }
        .header { width: 100%; max-width: 480px; display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #0f0; margin-bottom: 10px; }
        .logout { color: #f00; text-decoration: none; border: 1px solid #f00; padding: 2px 8px; border-radius: 5px; }
        .box { border: 2px solid #0f0; padding: 20px; border-radius: 15px; width: 100%; max-width: 480px; background: #050505; box-shadow: 0 0 20px #0f0; }
        #map { height: 200px; width: 100%; border: 1px solid #0f0; border-radius: 10px; margin-bottom: 10px; }
        .metric { font-size: 50px; color: #fff; text-align: center; margin: 10px 0; font-weight: bold; }
        input { width: 92%; padding: 12px; margin: 5px 0; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; font-weight: bold; }
        .btn { padding: 15px; font-size: 16px; width: 100%; font-weight: bold; text-transform: uppercase; margin-top: 10px; cursor: pointer; border-radius: 8px; border: none; }
        .start { background: #008000; color: #fff; } .stop { background: #800; color: #fff; } .reset { background: #333; color: #fff; }
        .gps-btn { background: #00f; color: #fff; padding: 10px; border-radius: 5px; margin-bottom: 10px; width: 100%; border: none; cursor: pointer; }
        .preview { background: #111; color: yellow; padding: 10px; font-size: 10px; word-break: break-all; margin-top: 10px; border: 1px dashed #0f0; min-height: 40px; }
    </style>
</head>
<body>
    <div class="header">
        <span>ID: {{user_id}}</span>
        <a href="/logout" class="logout">LOGOUT</a>
    </div>
    <div class="box">
        <div id="map"></div>
        <button class="gps-btn" onclick="getLocation()">📍 GET CURRENT LOCATION</button>
        <div class="metric" id="cnt">0</div>
        <form action="/action" method="post">
            <input type="text" name="vno" id="vno" placeholder="VEHICLE NO" value="{{status.vno}}" oninput="this.value=this.value.toUpperCase(); updatePreview();">
            <input type="text" name="imei" id="imei" placeholder="IMEI" value="{{status.imei}}" oninput="updatePreview();">
            <div style="display:flex; gap:10px;">
                <input type="text" name="lat" id="lat" value="{{status.lat}}" oninput="updatePreview();">
                <input type="text" name="lon" id="lon" value="{{status.lon}}" oninput="updatePreview();">
            </div>
            <div class="preview" id="preview">Ready...</div>
            <button class="btn start" name="btn" value="start">🚀 START HYBRID ENGINE</button>
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
                    marker.setLatLng([lt, ln]); map.setView([lt, ln], 15);
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
            document.getElementById('preview').innerText = `$PVT,RA18,2.1.1,NR,01,L,${i},${v},1,${dt},${lt},N,${ln},E,...DDE3* \r \n`;
        }
        
        setInterval(() => {
            fetch('/data').then(r => r.json()).then(d => {
                document.getElementById('cnt').innerText = d.count;
                if(d.firing) document.getElementById('preview').innerText = d.last_pkt;
            });
        }, 1000);
    </script>
</body>
</html>
"""

# Backend Logic (Login/Action/Firing) same rahega, bas dashboard route ko fix kar diya hai.
@app.route('/dashboard')
def dashboard():
    uid = session.get('user')
    sid = session.get('device_sid')
    if not uid or sid not in user_sessions: return redirect(url_for('login'))
    # Firebase default values ko safe rakha hai crash rokne ke liye
    s = user_sessions[sid]
    return render_template_string(DASH_HTML, user_id=uid, status=s)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('/'))
