import os, socket, threading, time
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# --- TAG ROTATION LIST (14 TAGS) ---
TAG_LIST = [
    "RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", 
    "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"
]

# --- ENGINE STATE ---
status = {
    "firing": False, "count": 0, "proto": "UDP",
    "imei": "", "vno": "", "lat": "", "lon": ""
}

HTML_V82_NITRO = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 - AUTO ROTATE</title>
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
        .start { background: #008000; color: #fff; box-shadow: 0 0 10px #0f0; }
        .stop { background: #800; color: #fff; }
        .gps { background: #004466; color: #fff; border: 1px solid #00ffff; }
        .reset { background: #333; color: #fff; }
        .preview { background: #111; color: yellow; padding: 12px; font-size: 11px; word-break: break-all; margin-top: 15px; border: 1px dashed #0f0; min-height: 60px; line-height: 1.4; }
        label { font-size: 12px; color: #aaa; margin-bottom: 2px; display: block; }
        .tag-info { color: #00ffff; font-size: 12px; font-weight: bold; margin-bottom: 5px; }
    </style>
</head>
<body>
    <div class="box">
        <h2 style="margin:0;">🚀 V82 AUTO-ROTATE</h2>
        <div class="metric" id="cnt">0</div>
        <div class="tag-info">SYSTEM: 14 TAGS LOADED (AUTO-ROTATE)</div>
        
        <form action="/action" method="post" class="grid">
            <div class="full"><label>VEHICLE NO</label><input type="text" name="vno" id="vno" value="{{vno}}" placeholder="BR01..." oninput="updateUI()"></div>
            <div class="full"><label>IMEI</label><input type="text" name="imei" id="imei" value="{{imei}}" placeholder="862..." oninput="updateUI()"></div>
            <div><label>LATITUDE</label><input type="text" name="lat" id="lat" value="{{lat}}" placeholder="25.65..." oninput="updateUI()"></div>
            <div><label>LONGITUDE</label><input type="text" name="lon" id="lon" value="{{lon}}" placeholder="84.78..." oninput="updateUI()"></div>
            
            <button type="button" class="btn gps full" onclick="getLocation()">📍 GET CURRENT LOCATION</button>
            
            <div class="full">
                <label>PROTOCOL (50 PKT/SEC)</label>
                <select name="proto" id="proto" onchange="updateUI()">
                    <option value="UDP" {% if proto == 'UDP' %}selected{% endif %}>UDP (Line-by-Line)</option>
                    <option value="TCP" {% if proto == 'TCP' %}selected{% endif %}>TCP (One-by-One)</option>
                </select>
            </div>

            <div class="full">
                <label>📋 PACKET PREVIEW (TAG ROTATION INCLUDED)</label>
                <div class="preview" id="preview">Ready to fire...</div>
            </div>

            <button class="btn start full" name="btn" value="start">🔥 START ENGINE</button>
            <button class="btn stop full" name="btn" value="stop">🛑 STOP ENGINE</button>
            <button class="btn reset full" name="btn" value="reset">🔄 RESET ALL DATA</button>
        </form>
    </div>
    
    <div id="map"></div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([25.65, 84.78], 10);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        var marker = L.marker([25.65, 84.78]).addTo(map);
        
        const tags = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"];
        let currentCnt = 0;

        function updateUI() {
            let v = document.getElementById('vno').value.toUpperCase();
            let i = document.getElementById('imei').value;
            let la = document.getElementById('lat').value || "0.000000";
            let lo = document.getElementById('lon').value || "0.000000";
            let p = document.getElementById('proto').value;
            
            let d = new Date().toLocaleDateString('en-GB').replace(/\\//g, '');
            let h = new Date().toLocaleTimeString('en-GB', {hour12: false}).replace(/:/g, '');
            
            // Preview logic with rotation visual
            let t = tags[currentCnt % tags.length];
            let fullPacket = `$PVT,${t},${i || 'IMEI'},${v || 'VNO'},1,${d},${h},${la},N,${lo},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a,e3,e3,0a,7,e3,0a,7,c7,0a,10,e3,0a,0,0001,00,000041,DDE3*`;
            document.getElementById('preview').innerText = `[${p}] ${fullPacket}`;

            if(la !== "0.000000" && lo !== "0.000000") {
                let pos = [parseFloat(la), parseFloat(lo)];
                map.setView(pos, 15);
                marker.setLatLng(pos);
            }
        }

        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(pos => {
                    document.getElementById('lat').value = pos.coords.latitude.toFixed(6);
                    document.getElementById('lon').value = pos.coords.longitude.toFixed(6);
                    updateUI();
                }, () => alert("Location permission denied."));
            }
        }

        setInterval(() => {
            fetch('/data').then(r => r.json()).then(d => {
                currentCnt = d.count;
                document.getElementById('cnt').innerText = d.count.toLocaleString();
                if(d.firing) updateUI(); // Update preview tag live while firing
            });
        }, 1000);
        
        updateUI();
    </script>
</body>
</html>
"""

def firing_engine():
    target = ("vlts.bihar.gov.in", 9999)
    while status["firing"]:
        try:
            # LINE-WISE TAG ROTATION LOGIC
            tag_to_use = TAG_LIST[status["count"] % len(TAG_LIST)]
            
            now = datetime.now()
            pkt = f"$PVT,{tag_to_use},{status['imei']},{status['vno']},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{status['lat']},N,{status['lon']},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a,e3,e3,0a,7,e3,0a,7,c7,0a,10,e3,0a,0,0001,00,000041,DDE3*".encode()
            
            if status["proto"] == "UDP":
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(pkt, target)
                status["count"] += 1
                sock.close()
                time.sleep(0.02) # Exactly 50 pkt/sec
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                try:
                    sock.connect(target)
                    sock.send(pkt)
                    status["count"] += 1
                finally:
                    sock.close()
                time.sleep(0.02)
        except:
            time.sleep(1)

@app.route('/')
def home():
    return render_template_string(HTML_V82_NITRO, **status)

@app.route('/data')
def data():
    return jsonify(status)

@app.route('/action', methods=['POST'])
def action():
    val = request.form.get('btn')
    if val == "reset":
        status.update({"firing": False, "count": 0, "imei": "", "vno": "", "lat": "", "lon": ""})
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
                threading.Thread(target=firing_engine, daemon=True).start()
        elif val == "stop":
            status["firing"] = False
            
    return home()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
