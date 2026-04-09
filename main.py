import os, socket, threading, time, requests
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from bs4 import BeautifulSoup

app = Flask(__name__)

# --- CONFIG ---
DEFAULTS = {
    "tag": "EGAS", "imei": "862567075041793", "vno": "BR03GB9117",
    "lat": "25.65", "lon": "84.78", "proto": "UDP"
}
status = {"firing": False, "count": 0, "p_stat": "IDLE", "sync": "NEVER", "p_date": "WAITING...", **DEFAULTS}

HTML_V82 = """
<!DOCTYPE html>
<html>
<head>
    <title>NITRO V82 ULTIMATE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #000; color: #0f0; font-family: 'Courier New', monospace; text-align: center; padding: 10px; }
        .box { border: 2px solid #0f0; padding: 15px; display: inline-block; border-radius: 15px; width: 100%; max-width: 420px; box-shadow: 0 0 20px #0f0; background: #050505; }
        .metric { font-size: 50px; color: #fff; margin: 10px 0; text-shadow: 0 0 10px #0f0; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; text-align: left; }
        input, select { width: 90%; padding: 10px; margin: 4px 0; background: #111; border: 1px solid #0f0; color: #0f0; border-radius: 5px; text-transform: uppercase; }
        .full { grid-column: span 2; }
        .btn { padding: 15px; font-size: 18px; cursor: pointer; border: none; border-radius: 8px; width: 100%; font-weight: bold; margin-top: 10px; text-transform: uppercase; }
        .start { background: #004d00; color: #fff; border: 1px solid #0f0; }
        .stop { background: #600; color: #fff; border: 1px solid #f00; }
        .status-bar { background: #111; padding: 10px; margin: 10px 0; border-radius: 8px; font-size: 12px; border: 1px solid #333; color: yellow; text-align: left; }
    </style>
</head>
<body>
    <div class="box">
        <h3>🚀 NITRO V82 KHANAN-SPEC</h3>
        <div class="metric" id="cnt">0</div>
        <div class="status-bar">
            📡 Portal: <span id="ps">{{p_stat}}</span><br>
            📅 Captured Date: <span id="pd" style="color:#fff">{{p_date}}</span><br>
            🕒 Sync Time: <span id="ls">{{sync}}</span>
        </div>
        <form action="/action" method="post" class="grid">
            <div class="full"><label>VEHICLE NO (FOR SEARCH)</label><input type="text" name="vno" value="{{vno}}"></div>
            <div><label>IMEI</label><input type="text" name="imei" value="{{imei}}"></div>
            <div><label>TAG</label><input type="text" name="tag" value="{{tag}}"></div>
            <div><label>LAT</label><input type="text" name="lat" value="{{lat}}"></div>
            <div><label>LON</label><input type="text" name="lon" value="{{lon}}"></div>
            <div class="full">
                <select name="proto">
                    <option value="UDP" {% if proto == 'UDP' %}selected{% endif %}>UDP (HIGH SPEED)</option>
                    <option value="TCP" {% if proto == 'TCP' %}selected{% endif %}>TCP (STABLE)</option>
                </select>
            </div>
            <button class="btn start full" name="btn" value="start">🔥 FORCE START</button>
            <button class="btn stop full" name="btn" value="stop">🛑 STOP ENGINE</button>
        </form>
    </div>
    <script>
        setInterval(() => {
            fetch('/data').then(r => r.json()).then(d => {
                document.getElementById('cnt').innerText = d.count.toLocaleString();
                document.getElementById('ps').innerText = d.p_stat;
                document.getElementById('ls').innerText = d.sync;
                document.getElementById('pd').innerText = d.p_date;
            });
        }, 1000);
    </script>
</body>
</html>
