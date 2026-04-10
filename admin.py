# --- ADMIN PANEL HTML WITH AUTO-FETCH & ATTACK LOGS ---
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ULTRA ADMIN | GHOP-GHOP</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --neon: #0f0; --bg: #000; }
        body { background: var(--bg); color: #fff; font-family: sans-serif; padding: 15px; }
        .section { background: #0a0a0a; padding: 20px; border-radius: 12px; border: 1px solid #222; margin-bottom: 20px; }
        input, select, button { background: #111; border: 1px solid #333; color: #fff; padding: 12px; border-radius: 8px; width: 100%; margin-bottom: 10px; box-sizing: border-box; }
        button.primary { background: var(--neon); color: #000; font-weight: bold; border: none; cursor: pointer; font-size: 16px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #222; }
        .pro-badge { color: gold; font-weight: bold; border: 1px solid gold; padding: 2px 5px; border-radius: 3px; }
        .attack-count { color: #0ff; font-weight: bold; font-family: monospace; font-size: 16px; }
    </style>
</head>
<body>
    <div class="section">
        <h2 style="color:var(--neon)">➕ CREATE / EDIT USER</h2>
        <form action="/save" method="POST" id="userForm">
            <input name="uid" id="input_uid" placeholder="User ID (Mobile)" oninput="fetchOldData()" required>
            <input name="pw" id="input_pw" placeholder="Password" required>
            <div style="display:flex; gap:10px;">
                <input name="lat" id="input_lat" placeholder="Lat">
                <input name="lon" id="input_lon" placeholder="Lon">
            </div>
            <div style="display:flex; gap:10px;">
                <input type="date" name="expiry" id="input_exp" required>
                <select name="level" id="input_level">
                    <option value="pro">Pro Mode</option>
                    <option value="normal">Normal</option>
                </select>
            </div>
            <button class="primary">SAVE / UPDATE USER DATA</button>
        </form>
    </div>

    <div class="section">
        <h2>👥 TOTAL USERS: {{users|length}}</h2>
        <div style="overflow-x:auto;">
            <table>
                <tr style="color:var(--neon)"><th>USER ID</th><th>EXPIRY</th><th>LEVEL</th><th>FIRE COUNT</th><th>ACTION</th></tr>
                {% for uid, data in users.items() %}
                <tr id="row_{{uid}}">
                    <td class="u_id">{{uid}}</td>
                    <td class="u_exp">{{data.expiry}}</td>
                    <td class="u_lvl" data-val="{{data.access_level}}">{% if data.access_level == 'pro' %}<span class="pro-badge">PRO</span>{% else %}STD{% endif %}</td>
                    <td class="attack-count">🚀 {{data.total_attacks or 0}}</td>
                    <td>
                        <button onclick="editThis('{{uid}}', '{{data.password}}', '{{data.lat}}', '{{data.lon}}', '{{data.expiry}}', '{{data.access_level}}')" style="background:none; border:1px solid #555; color:#fff; cursor:pointer;">EDIT</button>
                        <a href="/toggle/{{uid}}" style="color:yellow; text-decoration:none; margin-left:5px;">[B]</a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>

    <script>
    function editThis(uid, pw, lat, lon, exp, lvl) {
        document.getElementById('input_uid').value = uid;
        document.getElementById('input_pw').value = pw;
        document.getElementById('input_lat').value = lat;
        document.getElementById('input_lon').value = lon;
        document.getElementById('input_exp').value = exp;
        document.getElementById('input_level').value = lvl;
        window.scrollTo(0,0);
    }

    function fetchOldData() {
        let val = document.getElementById('input_uid').value;
        // Agar table mein ye ID milti hai toh auto-fill kar do
        let row = document.getElementById('row_' + val);
        if(row) {
            // Humne button mein pehle se hi data-attributes ya simple function rakha hai
            // Tu seedha 'EDIT' button par click kar sakta hai ya type karke bhi check kar sakta hai
        }
    }
    </script>
</body>
</html>
