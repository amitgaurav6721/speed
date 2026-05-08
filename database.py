import httpx
import time

DB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com"

async def fetch_vehicle_data(vno: str):
    v_up = vno.upper().strip()
    async with httpx.AsyncClient() as client:
        try:
            # Data_Records se fetch karega
            r = await client.get(f"{DB_URL}/Data_Records/{v_up}.json?t={time.time()}")
            return r.json() or {"found": False}
        except: return {"found": False}

# 🔥 Iska naam main.py se match kar diya hai
async def sync_to_firebase(vno, payload):
    async with httpx.AsyncClient() as client:
        try:
            await client.put(f"{DB_URL}/Data_Records/{vno}.json", json=payload)
        except Exception as e:
            print(f"DB Error: {e}")

async def get_system_messages(mobile):
    async with httpx.AsyncClient() as client:
        b = await client.get(f"{DB_URL}/broadcast.json?t={time.time()}")
        p = await client.get(f"{DB_URL}/user_messages/{mobile}.json?t={time.time()}")
        return {"b": b.json(), "p": p.json()}
