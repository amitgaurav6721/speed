import os, requests
from flask import Flask, render_template_string, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "ghop_ghop_admin"

FB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com/"
FB_SECRET = "hpa10b2FOtP4nP5aYjtMWSoq3bdp1n5sbH6lPDjE"

# --- ADMIN LOGIN CREDENTIALS ---
ADMIN_UID = "admin"
ADMIN_PASS = "admin6721"

# --- LOGIN HTML ---
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>ADMIN LOGIN</title><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{background:#000;color:#0f0;font-family:monospace;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}.box{border:2px solid #0f0;padding:40px;text-align:center;border-radius:15px;background:#050505;}input{width:100%;padding:12px;margin:10px 0;background:#111;border:1px solid #0f0;color:#0f0;border-radius:5px;box-sizing:border-box;}.btn{padding:12px;width:100%;background:#0f0;color:#000;border:none;font-weight:bold;cursor:pointer;margin-top:10px;}</style></head>
<body><div class="box"><h2>🔐 ADMIN CONTROL</h2>{% if error %}<p style="color:red">{{error}}</p>{% endif %}<form method="POST"><input name="uid" placeholder="ADMIN ID" required><input type="password" name="pw" placeholder="PASSWORD" required><button class="btn">ENTER SYSTEM</button></form></div></body></html>
"""

# --- ADMIN PANEL HTML ---
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ULTRA ADMIN</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --neon: #0f0; --bg: #000; --card: #0a0a0a; }
        body { background: var(--bg); color: #fff; font-family: sans-serif; padding: 15px; }
        .nav { background: var(--card); padding: 15px; border-bottom: 2px solid var(--neon); display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .section { background: var(--card); padding: 20px; border-radius: 12px; border: 1px solid #222; margin-bottom: 20px; }
        input, select, button { background: #111; border: 1px solid #333; color: #fff; padding: 12px; border-radius: 8px; width: 100%; margin-bottom: 10px; box-sizing: border-box; }
        button.primary { background: var(--neon); color: #000; font-weight: bold; border: none; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #222; }
        .pro-badge { color: gold; font-weight: bold; border: 1px solid gold; padding: 2px 5px; border-radius: 3px; font-size: 10px; }
    </style>
</head>
<body>
    <div class="nav">
        <b>🚀 GHOP-GHOP ADMIN</b>
        <a href="/logout" style="color:red; text-decoration:none;">LOGOUT</a>
    </div>

    <div class="section">
        <h2>➕ CREATE / EDIT USER</h2>
        <form action="/save" method="POST">
            <input name="uid" placeholder="User ID (Mobile)" required>
            <input name="pw" placeholder="Password" required>
            <div style="display:flex; gap:10px;"><input name="lat" placeholder="Lat"><input name="lon" placeholder="Lon"></div>
            <div style="display:flex; gap:10px;"><input type="date" name="expiry" required><select name="level"><option value="pro">Pro Mode</option><option value="normal">Normal</option></select></div>
            <button class="primary">SAVE / UPDATE USER</button>
        </form>
    </div>

    <div class="section">
        <h2>👥 TOTAL USERS: {{users|length}}</h2>
        <div style="overflow-x:auto;">
            <table>
                <tr><th>USER</th><th>PASS</th><th>EXPIRY</th><th>LEVEL</th><th>ACTION</th></tr>
                {% for uid, data in users.items() %}
                <tr>
                    <td>{{uid}}</td><td>{{data.password}}</td><td>{{data.expiry}}</td>
                    <td>{% if data.access_level == 'pro' %}<span class="pro-badge">PRO</span>{% else %}STD{% endif %}</td>
                    <td><a href="/toggle/{{uid}}" style="color:yellow;">[B]</a> <a href="/delete/{{uid}}" style="color:red;">[X]</a></td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'): return redirect(url_for('admin_panel'))
    error = None
    if request.method == 'POST':
        if request.form.get('uid') == ADMIN_UID and request.form.get('pw') == ADMIN_PASS:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        error = "INVALID ACCESS"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/panel')
def admin_panel():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    u = requests.get(f"{FB_URL}/users.json?auth={FB_SECRET}").json() or {}
    return render_template_string(ADMIN_HTML, users=u)

@app.route('/save', methods=['POST'])
def save_user():
    if not session.get('admin_logged_in'): return redirect('/')
    uid = request.form.get('uid').strip()
    data = {"password": request.form.get('pw'), "lat": request.form.get('lat') or "25.6", "lon": request.form.get('lon') or "84.7", "expiry": request.form.get('expiry'), "access_level": request.form.get('level'), "status": "Active"}
    requests.patch(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}", json=data)
    return redirect(url_for('admin_panel'))

@app.route('/toggle/<uid>')
def toggle_user(uid):
    if not session.get('admin_logged_in'): return redirect('/')
    r = requests.get(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}").json()
    new_s = "Blocked" if r.get('status') == "Active" else "Active"
    requests.patch(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}", json={"status": new_s})
    return redirect(url_for('admin_panel'))

@app.route('/delete/<uid>')
def delete_user(uid):
    if not session.get('admin_logged_in'): return redirect('/')
    requests.delete(f"{FB_URL}/users/{uid}.json?auth={FB_SECRET}")
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
