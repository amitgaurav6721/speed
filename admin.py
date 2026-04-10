import os, requests
from datetime import datetime
from flask import Flask, render_template_string, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "ghop_ghop_ultra_final_boss"

FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"
ADMIN_UID, ADMIN_PASS = "admin", "admin6721"

# --- MAIN ADMIN PANEL HTML ---
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ULTRA ADMIN</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --neon: #0f0; --bg: #000; }
        body { background: var(--bg); color: #fff; font-family: sans-serif; padding: 10px; margin:0; }
        .section { background: #0a0a0a; padding: 20px; border-radius: 12px; border: 1px solid #222; margin-bottom: 20px; }
        input, select, button { background: #111; border: 1px solid #333; color: #fff; padding: 12px; border-radius: 8px; width: 100%; margin-bottom: 10px; box-sizing: border-box; font-size: 16px; }
        button.primary { background: var(--neon); color: #000; font-weight: bold; border: none; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #222; }
        .hit-badge { color: #0ff; font-weight: bold; text-shadow: 0 0 5px #0ff; }
    </style>
</head>
<body>
    <div style="display:flex; justify-content:space-between; align-items:center; padding: 10px; border-bottom: 1px solid #222;">
        <h2 style="color:var(--neon); margin:0;">🚀 VIP CONTROL</h2>
        <a href="/logout" style="color:red; text-decoration:none; font-weight:bold;">LOGOUT</a>
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
            <button class="primary">SAVE / UPDATE USER</button>
        </form>
    </div>

    <div class="section">
        <h3 style="color:var(--neon)">📅 ATTACK LOGS: {{selected_date}}</h3>
        <form action="/panel" method="GET" style="display:flex; gap:10px;">
            <input type="date" name="date" value="{{selected_date}}">
            <button class="primary" style="width:100px;">FETCH</button>
        </form>
        <div style="overflow-x:auto;">
            <table>
                <tr style="color:var(--neon)"><th>USER ID</th><th>DAILY HITS</th><th>ACTION</th></tr>
                {% for uid, data in users.items() %}
                <tr>
                    <td><b>{{uid}}</b></td>
                    <td class="hit-badge">🚀 {{ counts.get(uid, 0) }} Hits</td>
                    <td><button onclick="editU('{{uid}}','{{data.password}}','{{data.lat}}','{{data.lon}}','{{data.expiry}}','{{data.access_level}}')" style="padding:5px; background:#222; border:1px solid #0f0; color:#0f0; border-radius:5px;">EDIT</button></td>
                </tr>
                {% endfor %}
            </table>
        </div>
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

# --- FLASK ROUTES ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if session.get('admin_in'): return redirect(url_for('admin_panel'))
    if request.method == 'POST':
        if request.form.get('uid') == ADMIN_UID and request.form.get('pw') == ADMIN_PASS:
            session['admin_in'] = True
            return redirect(url_for('admin_panel'))
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background: #000; color: #0f0; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { border: 2px solid #0f0; padding: 40px; border-radius: 20px; box-shadow: 0 0 25px #0f0; width: 85%; max-width: 400px; text-align: center; background: #0a0a0a; }
            h2 { font-size: 32px; margin-bottom: 30px; text-shadow: 0 0 10px #0f0; }
            input { width: 100%; padding: 18px; margin-bottom: 20px; border-radius: 10px; border: 1px solid #333; background: #111; color: #fff; font-size: 18px; box-sizing: border-box; }
            button { width: 100%; padding: 18px; border-radius: 10px; border: none; background: #0f0; color: #000; font-weight: bold; font-size: 22px; cursor: pointer; box-shadow: 0 0 10px #0f0; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🚀 ULTRA ADMIN</h2>
            <form method="POST">
                <input name="uid" placeholder="ADMIN ID" required>
                <input type="password" name="pw" placeholder="PASSWORD" required>
                <button type="submit">LOGIN SYSTEM</button>
            </form>
        </div>
    </body>
    </html>
    ''')

@app.route('/panel')
def admin_panel():
    if not session.get('admin_in'): return redirect(url_for('login'))
    target_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    users = requests.get(f"{FB_URL}/users.json?auth={FB_SECRET}").json() or {}
    all_history = requests.get(f"{FB_URL}/Attack_History/{target_date}.json?auth={FB_SECRET}").json() or {}
    
    calculated_counts = {}
    for uid, vehicles in all_history.items():
        total = 0
        if isinstance(vehicles, dict):
            for vno, times in vehicles.items():
                if isinstance(times, dict): total += len(times)
        calculated_counts[uid] = total

    return render_template_string(ADMIN_HTML, users=users, counts=calculated_counts, selected_date=target_date)

@app.route('/save', methods=['POST'])
def save():
    if not session.get('admin_in'): return redirect(url_for('login'))
    uid = request.form.get('uid').strip()
    data = {"password": request.form.get('pw'), "lat": request.form.get('lat'), "lon": request.form.get('lon'), "expiry": request.form.get('expiry'), "access_level": request.form.get('level'), "status": "Active"}
    requests.patch(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}", json=data)
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
