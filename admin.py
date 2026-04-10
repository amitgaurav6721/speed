import os, requests
from flask import Flask, render_template_string, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "ghop_ghop_admin_ultra_fixed"

FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"

# --- ADMIN LOGIN ---
ADMIN_UID = "admin"
ADMIN_PASS = "admin6721"

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ULTRA ADMIN</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --neon: #0f0; --bg: #000; }
        body { background: var(--bg); color: #fff; font-family: sans-serif; padding: 15px; }
        .section { background: #0a0a0a; padding: 20px; border-radius: 12px; border: 1px solid #222; margin-bottom: 20px; }
        input, select, button { background: #111; border: 1px solid #333; color: #fff; padding: 12px; border-radius: 8px; width: 100%; margin-bottom: 10px; box-sizing: border-box; }
        button.primary { background: var(--neon); color: #000; font-weight: bold; border: none; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #222; }
        .pro-badge { color: gold; font-weight: bold; border: 1px solid gold; padding: 2px 5px; border-radius: 3px; }
        .attack-count { color: #0ff; font-weight: bold; font-size: 15px; }
    </style>
</head>
<body>
    <div style="display:flex; justify-content:space-between; align-items:center; padding:10px;">
        <h2 style="color:var(--neon)">🚀 VIP CONTROL</h2>
        <a href="/logout" style="color:red; text-decoration:none;">LOGOUT</a>
    </div>

    <div class="section">
        <h2 style="color:var(--neon)">➕ CREATE / EDIT USER</h2>
        <form action="/save" method="POST">
            <input name="uid" id="in_uid" placeholder="User ID (Mobile)" required>
            <input name="pw" id="in_pw" placeholder="Password" required>
            <div style="display:flex; gap:10px;"><input name="lat" id="in_lat" placeholder="Lat"><input name="lon" id="in_lon" placeholder="Lon"></div>
            <div style="display:flex; gap:10px;"><input type="date" name="expiry" id="in_exp" required><select name="level" id="in_lvl"><option value="pro">Pro Mode</option><option value="normal">Normal</option></select></div>
            <button class="primary">SAVE DATA</button>
        </form>
    </div>

    <div class="section">
        <h2>👥 TOTAL USERS: {{users|length}}</h2>
        <div style="overflow-x:auto;">
            <table>
                <tr style="color:var(--neon)"><th>USER</th><th>EXPIRY</th><th>LEVEL</th><th>ATTACKS</th><th>ACTION</th></tr>
                {% for uid, data in users.items() %}
                <tr>
                    <td><b>{{uid}}</b></td>
                    <td>{{data.expiry}}</td>
                    <td>{% if data.access_level == 'pro' %}<span class="pro-badge">PRO</span>{% else %}STD{% endif %}</td>
                    <td class="attack-count">🚀 {{data.total_attacks or 0}}</td>
                    <td>
                        <button onclick="editUser('{{uid}}','{{data.password}}','{{data.lat}}','{{data.lon}}','{{data.expiry}}','{{data.access_level}}')" style="padding:5px 10px; background:#222; color:#0f0; border:1px solid #0f0; border-radius:4px; cursor:pointer;">EDIT</button>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>

    <script>
    function editUser(u,p,la,lo,e,lvl) {
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
    if session.get('admin_in'): return redirect('/panel')
    if request.method == 'POST':
        if request.form.get('uid') == ADMIN_UID and request.form.get('pw') == ADMIN_PASS:
            session['admin_in'] = True
            return redirect('/panel')
    return render_template_string('<body style="background:#000;color:#0f0;text-align:center;padding:50px;"><form method="POST" style="border:1px solid #0f0;display:inline-block;padding:30px;"><h2>ADMIN</h2><input name="uid" placeholder="ID"><br><br><input type="password" name="pw" placeholder="PASS"><br><br><button>ENTER</button></form></body>')

@app.route('/panel')
def admin_panel():
    if not session.get('admin_in'): return redirect('/')
    u = requests.get(f"{FB_URL}/users.json?auth={FB_SECRET}").json() or {}
    return render_template_string(ADMIN_HTML, users=u)

@app.route('/save', methods=['POST'])
def save():
    uid = request.form.get('uid').strip()
    data = {"password": request.form.get('pw'), "lat": request.form.get('lat'), "lon": request.form.get('lon'), "expiry": request.form.get('expiry'), "access_level": request.form.get('level'), "status": "Active"}
    requests.patch(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}", json=data)
    return redirect('/panel')

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
