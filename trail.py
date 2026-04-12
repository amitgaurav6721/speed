import os, socket, threading, time, requests, uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "nitro_v82_hybrid_ultimate_fix_final"

# --- FIREBASE CONFIG ---
FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"

TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "VLT", "GPS", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "EMR", "ROADRPA"]
NEW_SUFFIX = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
FIXED_CS = "DDE3"

user_sessions = {}

def get_ist_time():
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

# --- DASHBOARD HTML (FIXED UI & STRIP) ---
DASH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 - HYBRID MASTER</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background: #000; color: #0f0; font-family: monospace; padding: 10px; display: flex; flex-direction: column; align-items: center; }
        .score-bar { background: #050505; border: 1px solid #0f0; width: 100%; max-width: 480px; padding: 10px; border-radius: 10px; display: flex; justify-content: space-around; font-size: 11px; margin-bottom: 10px; box-shadow: 0 0 10px #0f0; }
        .s-val { color: #fff; font-weight: bold; }
        .header { width: 100%; max-width: 480px; display: flex; justify-content: space-between; padding: 5px; font-size: 12px; margin-bottom: 5px; }
        .box { border: 2px solid #0f0; padding: 20px; border-radius: 15px; width: 100%; max-width: 480px; background: #050505; box-shadow: 0 0 20px #0f0; }
        #map { height: 180px; width: 100%; border: 1px solid #0f0; border-radius: 10px; margin-bottom: 10px; }
        .metric { font-size: 50px; color: #fff; text-align: center; margin: 10px 0; font-weight: bold; }
        input { width: 92%; padding: 12px; margin: 5px 0; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; font-weight: bold; }
        .btn { padding: 15px; font-size: 16px; width: 100%; font-weight: bold; text-transform: uppercase; margin-top: 10px; cursor: pointer; border-radius: 8px; border: none; }
        .start { background: #008000; color: #fff; } .stop { background: #800; color: #fff; } .reset { background: #333; color: #fff; }
        .preview { background: #111; color: yellow; padding: 10px; font-size: 10px; word-break: break-all; margin-top: 10px; border: 1px dashed #0f0; min-height: 60px; }
    </style>
</head>
<body>
    <div class="header"><span>ID: {{user_id}}</span><a href="/logout" style="color:red">LOGOUT</a></div>
    <div class="score-bar">
        <span>TOTAL: <span id="s_total" class="s-val">0</span></span>
        <span>SUCCESS: <span id="s_ok" class="s-val" style="color:#0f0">0</span></span>
        <span>FAIL: <span id="s_fail" class="s-val" style="color:#f00">0</span></span>
    </div>
    <div class="box">
        <div id="map"></div>
        <div class="metric" id="cnt">0</div>
        <form action="/action" method="post">
            <input type="text" name="vno" id="vno" placeholder="VEHICLE NO" value="{{status.vno}}" oninput="this.value=this.value.toUpperCase();">
            <input type="text" name="imei" id="imei" placeholder="IMEI NO" value="{{status.imei}}">
            <div style="display:flex; gap:10px;">
                <input type="text" name="lat" id="lat" value="{{status.lat}}">
                <input type="text" name="lon" id="lon" value="{{status.lon}}">
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

        // IMEI FETCH FROM DATA_RECORDS
        document.getElementById('vno').addEventListener('blur', function() {
            fetch('/check_vehicle?vno=' + this.value)
            .then(r => r.json())
            .then(d => { if(d.imei) document.getElementById('imei').value = d.imei; });
        });

        setInterval(() => {
            fetch('/data').then(r => r.json()).then(d => {
                document.getElementById('cnt').innerText = d.count;
                document.getElementById('preview').innerText = d.last_pkt;
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

# --- BACKEND LOGIC (FIXED ENDPOINTS) ---
@app.route('/check_vehicle')
def check_vehicle():
    vno = request.args.get('vno', '').upper()
    res = requests.get(f"{FB_URL}/Data_Records/{vno}.json?auth={FB_SECRET}").json()
    return jsonify({"imei": res.get('IMEI_No') if res else ""})

@app.route('/data')
def data():
    sid = session.get('device_sid')
    if sid in user_sessions:
        today = get_ist_time().strftime('%Y-%m-%d')
        score = requests.get(f"{FB_URL}/User_Audit/{today}/{user_sessions[sid]['uid']}.json?auth={FB_SECRET}").json()
        user_sessions[sid]['score'] = score if score else {}
    return jsonify(user_sessions.get(sid, {}))

@app.route('/action', methods=['POST'])
def action():
    sid = session.get('device_sid')
    val = request.form.get('btn')
    if val == "start":
        user_sessions[sid].update({
            "firing": True, "imei": request.form.get('imei'),
            "vno": request.form.get('vno').upper(),
            "lat": request.form.get('lat'), "lon": request.form.get('lon')
        })
        threading.Thread(target=firing_engine, args=(sid,), daemon=True).start()
    elif val == "stop": user_sessions[sid]["firing"] = False
    elif val == "reset": user_sessions[sid].update({"firing":False, "count":0, "imei":"", "vno":""})
    return redirect(url_for('dashboard'))

def firing_engine(sid):
    target = ("vlts.bihar.gov.in", 9999)
    while user_sessions.get(sid, {}).get("firing"):
        try:
            s = user_sessions[sid]
            tag = TAG_LIST[s["count"] % len(TAG_LIST)]
            dt = get_ist_time().strftime("%d%m%Y,%H%M%S")
            # Hybrid String with Termination Point 3
            pkt = f"$PVT,{tag},2.1.1,NR,01,L,{s['imei']},{s['vno']},1,{dt},{s['lat']},N,{s['lon']},E,{NEW_SUFFIX},{FIXED_CS}*"
            payload = pkt + " \r \n "
            user_sessions[sid]["last_pkt"] = pkt
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(payload.encode('ascii'), target)
            user_sessions[sid]["count"] += 1
            sock.close()
            time.sleep(0.05)
        except: time.sleep(1)

# (Login route same rahega...)
