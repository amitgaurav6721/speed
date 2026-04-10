import os, requests
from datetime import datetime
from flask import Flask, render_template_string, request, session, redirect

app = Flask(__name__)
app.secret_key = "ghop_ghop_ultra_secure"

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
        .attack-count { color: #0ff; font-weight: bold; font-size: 15px; }
    </style>
</head>
<body>
    <div style="display:flex; justify-content:space-between; align-items:center; padding:10px;">
        <h2 style="color:var(--neon)">🚀 ATTACK TRACKER</h2>
        <a href="/logout" style="color:red; text-decoration:none;">LOGOUT</a>
    </div>

    <div class="section">
        <h3 style="color:var(--neon)">📅 SELECT DATE TO CHECK LOGS</h3>
        <form action="/panel" method="GET" style="display:flex; gap:10px;">
            <input type="date" name="date" value="{{selected_date}}" required>
            <button class="primary" style="width: 150px;">FETCH LOGS</button>
        </form>
    </div>

    <div class="section">
        <h2>👥 USERS ACTIVITY ON {{selected_date}}</h2>
        <div style="overflow-x:auto;">
            <table>
                <tr style="color:var(--neon)"><th>USER ID</th><th>FIRE COUNT (CALCULATED)</th><th>ACTION</th></tr>
                {% for uid, data in users.items() %}
                <tr>
                    <td><b>{{uid}}</b></td>
                    <td class="attack-count">🚀 {{ counts.get(uid, 0) }} Hits</td>
                    <td>
                        <button onclick="editU('{{uid}}','{{data.password}}','{{data.lat}}','{{data.lon}}','{{data.expiry}}','{{data.access_level}}')">EDIT</button>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
    </body>
</html>
"""

@app.route('/panel')
def admin_panel():
    if not session.get('admin_in'): return redirect('/')
    
    # Date filter logic
    target_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # Get all users and the history for specific date
    users = requests.get(f"{FB_URL}/users.json?auth={FB_SECRET}").json() or {}
    all_history = requests.get(f"{FB_URL}/Attack_History/{target_date}.json?auth={FB_SECRET}").json() or {}
    
    # User-wise Calculation
    calculated_counts = {}
    if all_history:
        for uid, vehicles in all_history.items():
            user_total = 0
            if isinstance(vehicles, dict):
                for vno, times in vehicles.items():
                    if isinstance(times, dict):
                        # Ginn rahe hain kitne time stamps (packets) bhejey gaye
                        user_total += len(times)
            calculated_counts[uid] = user_total

    return render_template_string(ADMIN_HTML, users=users, counts=calculated_counts, selected_date=target_date)

# ... (Login/Logout/Save routes as before) ...
