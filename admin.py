# --- ISKO GITHUB PAR PURA REPLACE KARO ---
import os, requests
from datetime import datetime
from flask import Flask, render_template_string, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "ghop_ghop_fixed_final"

FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"
ADMIN_UID, ADMIN_PASS = "admin", "admin6721"

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ULTRA ADMIN</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --neon: #0f0; --bg: #000; }
        body { background: var(--bg); color: #fff; font-family: sans-serif; padding: 10px; }
        .section { background: #0a0a0a; padding: 20px; border-radius: 12px; border: 1px solid #222; margin-bottom: 20px; }
        input, select, button { background: #111; border: 1px solid #333; color: #fff; padding: 12px; border-radius: 8px; width: 100%; margin-bottom: 10px; box-sizing: border-box; }
        button.primary { background: var(--neon); color: #000; font-weight: bold; border: none; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #222; }
    </style>
</head>
<body>
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <h2 style="color:var(--neon)">🚀 CONTROL CENTER</h2>
        <a href="/logout" style="color:red; text-decoration:none;">LOGOUT</a>
    </div>

    <div class="section">
        <h2 style="color:var(--neon)">➕ CREATE / EDIT USER</h2>
        <form action="/save" method="POST">
            <input name="uid" id="in_uid" placeholder="User ID (Mobile)" required>
            <input name="pw" id="in_pw" placeholder="Password" required>
            <div style="display:flex; gap:10px;">
                <input name="lat" id="in_lat" placeholder="Lat">
                <input name="lon" id="in_lon" placeholder="Lon">
            </div>
            <div style="display:flex; gap:10px;">
                <input type="date" name="expiry" id="in_exp" required>
                <select name="level" id="in_lvl">
                    <option value="pro">Pro Mode</option>
                    <option value="normal">Normal</option>
                </select>
            </div>
            <button class="primary">SAVE USER DATA</button>
        </form>
    </div>

    <div class="section">
        <h3 style="color:var(--neon)">📅 ATTACK LOGS FOR: {{selected_date}}</h3>
        <form action="/panel" method="GET" style="display:flex; gap:10px;">
            <input type="date" name="date" value="{{selected_date}}">
            <button class="primary" style="width:100px;">FETCH</button>
        </form>
        <table>
            <tr style="color:var(--neon)"><th>USER ID</th><th>HITS</th><th>ACTION</th></tr>
            {% for uid, data in users.items() %}
            <tr>
                <td>{{uid}}</td>
                <td style="color:#0ff; font-weight:bold;">🚀 {{ counts.get(uid, 0) }} Hits</td>
                <td><button onclick="editU('{{uid}}','{{data.password}}','{{data.lat}}','{{data.lon}}','{{data.expiry}}','{{data.access_level}}')">EDIT</button></td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <script>
    function editU(u,p,la,lo,e,lvl) {
        document.getElementById('in_uid').value = u;
        document.getElementById('in_pw').value = p;
        document.getElementById('in_lat').value = la;
        document.getElementById('in_lon').value = lo;
        document.getElementById('in_exp').value = e;
        document.getElementById('in_lvl').value = lvl;
        window.scrollTo(0,0);
    }
    </script>
</body>
</html>
"""

# --- ROUTES (Wahi purane jo work kar rahe the) ---
@app.route('/save', methods=['POST'])
def save():
    uid = request.form.get('uid').strip()
    data = {"password": request.form.get('pw'), "lat": request.form.get('lat'), "lon": request.form.get('lon'), "expiry": request.form.get('expiry'), "access_level": request.form.get('level'), "status": "Active"}
    requests.patch(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}", json=data)
    return redirect('/panel')
# ... (Baaki routes same rahenge) ...
