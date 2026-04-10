import os, requests
from datetime import datetime
from flask import Flask, render_template_string, request, session, redirect

app = Flask(__name__)
app.secret_key = "ghop_ghop_admin_key_99"

# --- CONFIGURATION ---
FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"

# --- ADMIN PANEL UI (Bade Fonts + Professional Look) ---
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>GHOP-GHOP | VIP ADMIN</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --neon: #0f0; --bg: #000; --card: #0a0a0a; }
        body { background: var(--bg); color: #fff; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 15px; }
        .nav { background: var(--card); padding: 20px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; font-weight: bold; font-size: 20px; }
        .section { background: var(--card); padding: 25px; border-radius: 15px; margin: 20px 0; border: 1px solid #222; box-shadow: 0 0 15px rgba(0,255,0,0.1); }
        h2 { color: var(--neon); font-size: 22px; text-transform: uppercase; border-left: 5px solid var(--neon); padding-left: 15px; }
        input, button { background: #111; border: 1px solid #333; color: #fff; padding: 15px; border-radius: 8px; width: 100%; margin-bottom: 15px; font-size: 16px; }
        button.primary { background: var(--neon); color: #000; font-weight: bold; border: none; cursor: pointer; transition: 0.3s; }
        button.primary:hover { background: #0c0; transform: scale(1.01); }
        .table-box { overflow-x: auto; margin-top: 20px; }
        table { width: 100%; border-collapse: collapse; min-width: 600px; }
        th { background: #1a1a1a; color: var(--neon); padding: 18px; text-align: left; font-size: 14px; border-bottom: 2px solid #333; }
        td { padding: 18px; border-bottom: 1px solid #111; font-size: 15px; }
        .badge { padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .Active { color: #0f0; background: rgba(0,255,0,0.1); }
        .Blocked { color: #f00; background: rgba(255,0,0,0.1); }
        .row { display: flex; gap: 15px; }
    </style>
</head>
<body>
    <div class="nav"><span>🚀 GHOP-GHOP <span style="color:var(--neon)">VIP ADMIN</span></span></div>

    <div class="section">
        <h2>➕ ADD NEW CLIENT</h2>
        <form action="/add" method="POST">
            <input name="new_uid" placeholder="User ID (Mobile No)" required>
            <input name="new_pw" placeholder="Create Password" required>
            <div class="row">
                <input name="base_lat" placeholder="Default Latitude (e.g. 25.29)">
                <input name="base_lon" placeholder="Default Longitude (e.g. 84.65)">
            </div>
            <input type="date" name="expiry" required>
            <button class="primary">CREATE VIP ACCOUNT</button>
        </form>
    </div>

    <div class="section">
        <h2>👥 ALL REGISTERED USERS</h2>
        <div class="table-box">
            <table>
                <tr><th>USER ID</th><th>PASS</th><th>EXPIRY</th><th>LOCATION</th><th>STATUS</th><th>ACTION</th></tr>
                {% for uid, data in users.items() %}
                <tr>
                    <td><b>{{uid}}</b></td>
                    <td>{{data.password}}</td>
                    <td>{{data.expiry}}</td>
                    <td style="color:#888;">{{data.lat}}, {{data.lon}}</td>
                    <td><span class="badge {{data.status}}">{{data.status}}</span></td>
                    <td>
                        <a href="/toggle/{{uid}}" style="color:yellow; text-decoration:none; margin-right:10px;">[BLOCK]</a>
                        <a href="/delete/{{uid}}" style="color:red; text-decoration:none;" onclick="return confirm('Delete user?')">[DELETE]</a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

# --- ROUTES ---
@app.route('/')
def admin_panel():
    u = requests.get(f"{FB_URL}/users.json?auth={FB_SECRET}").json() or {}
    return render_template_string(ADMIN_HTML, users=u)

@app.route('/add', methods=['POST'])
def add_user():
    uid = request.form.get('new_uid').strip()
    p = {
        "access_level": "pro", 
        "expiry": request.form.get('expiry'), 
        "password": request.form.get('new_pw'), 
        "status": "Active", 
        "lat": request.form.get('base_lat') or "25.2988", 
        "lon": request.form.get('base_lon') or "84.6510"
    }
    requests.put(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}", json=p)
    return redirect('/')

@app.route('/toggle/<uid>')
def toggle_user(uid):
    r = requests.get(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}").json()
    new_s = "Blocked" if r.get('status') == "Active" else "Active"
    requests.patch(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}", json={"status": new_s})
    return redirect('/')

@app.route('/delete/<uid>')
def delete_user(uid):
    requests.delete(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}")
    return redirect('/')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
