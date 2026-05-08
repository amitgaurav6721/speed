from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
import threading
from engine import AttackEngine
from database import fetch_vehicle_data, sync_data, get_messages, validate_user
from datetime import datetime, timedelta, timezone

app = FastAPI()
stop_event = threading.Event()
stop_event.set()
lock = threading.Lock()
engine = AttackEngine(stop_event, lock)

@app.get("/init")
async def init(v:str, i:str, lt:str, ln:str, t:str, background_tasks: BackgroundTasks):
    if stop_event.is_set():
        v_up, t_up = v.upper().strip(), t.upper().strip()
        try:
            lt_f, ln_f = float(lt), float(ln)
        except: return {"ok": False}
        
        engine.total_sent = 0
        stop_event.clear()
        
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        payload = {"Vehicle_No": v_up, "IMEI_No": str(i), "Lat": f"{lt_f:.7f}", "Lon": f"{ln_f:.7f}", "Saved_Tag": t_up, "Status": "Active", "Time": now.strftime('%H:%M:%S')}
        background_tasks.add_task(sync_data, v_up, payload)
        
        threading.Thread(target=engine.handshake_worker, args=(t_up, i, v_up, lt_f, ln_f), daemon=True).start()
    return {"ok": True}

@app.get("/status")
def status(): return {"c": engine.total_sent, "f": not stop_event.is_set()}

@app.get("/stop")
def stop(): stop_event.set(); return {"ok": True}

@app.get("/", response_class=HTMLResponse)
async def home():
    # Frontend ka sara Graphic code yahan rahega (Audit Box, Map, Inputs etc.)
    return """
    <html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ghop-Ghop GPS</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { background:#000; color:#0f0; font-family:monospace; margin:0; display:flex; flex-direction:column; align-items:center; }
        .dashboard, .login-box { width:95%; max-width:440px; border:2px solid #0f0; padding:15px; border-radius:15px; margin-top:20px; box-sizing: border-box; }
        input, select { width:100%; background:#000; border:1px solid #333; color:#0f0; padding:12px; margin-top:10px; font-size:16px; border-radius:5px; }
        .audit-box { display:flex; justify-content:space-between; background:rgba(0,40,0,0.5); border:1px solid #0f0; padding:8px; border-radius:5px; text-align:center; font-size:10px; margin-bottom:10px;}
        .audit-box b { display:block; font-size:14px; color:#0f0; }
        .user-wall { background:#001a00; border:1px solid #0f0; padding:10px; margin-bottom:10px; display:none; color:red; border-radius:5px; }
        #map { width:100%; height:200px; margin-top:15px; border:1px solid #0f0; border-radius:10px; }
        button { width:100%; padding:14px; margin-top:10px; background:transparent; border:1px solid #0f0; color:#0f0; font-weight:bold; cursor:pointer; }
    </style></head><body>
    <div id="loginScreen" class="login-box">
        <h1>Ghop-Ghop GPS</h1>
        <input type="text" id="m" placeholder="MOBILE">
        <input type="password" id="p" placeholder="PASSWORD">
        <button onclick="login()">ACCESS SYSTEM</button>
    </div>
    <div id="dashScreen" class="dashboard" style="display:none;">
        <div class="audit-box"><div>OK<b>0</b></div><div>FAIL<b>0</b></div><div>TOTAL<b>0</b></div></div>
        <div id="u_wall" class="user-wall"></div>
        <input type="text" id="v" placeholder="VEHICLE" onblur="smartFetch()">
        <input type="text" id="i" placeholder="IMEI">
        <select id="tag"></select>
        <div style="display:flex;gap:5px;"><input type="text" id="lt" placeholder="LAT"><input type="text" id="ln" placeholder="LON"></div>
        <button onclick="st()" id="startBtn" style="background:#0f0;color:#000;">START INJECTION</button>
        <button onclick="sp()" style="color:red;border-color:red;">ABORT</button>
        <div id="map"></div>
        <div style="margin-top:10px;">SENT: <b id="c">0</b> <span id="st_text" style="float:right;color:lime;">IDLE</span></div>
    </div>
    <script>
        // JS logic to call /init, /status, /fetch_data etc.
        // Fixed NAN logic here: (d.Lon || d.lon || "83.790586")
    </script>
    </body></html>
    """
