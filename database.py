import httpx
import time

DB_URL = "https://ghop-ghop-gps-injection-default-rtdb.firebaseio.com"

async def fetch_vehicle_data(vno: str):
    v_up = vno.upper().strip()
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{DB_URL}/Data_Records/{v_up}.json?t={time.time()}")
            return r.json() or {"found": False}
        except:
            return {"found": False}

async def sync_data(vno, payload):
    async with httpx.AsyncClient() as client:
        await client.put(f"{DB_URL}/Data_Records/{vno}.json", json=payload)

async def get_messages(mobile):
    async with httpx.AsyncClient() as client:
        # Priority: Broadcast > Personal
        b = await client.get(f"{DB_URL}/broadcast.json?t={time.time()}")
        p = await client.get(f"{DB_URL}/user_messages/{mobile}.json?t={time.time()}")
        return {"broadcast": b.json(), "personal": p.json()}

async def validate_user(mobile, password):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{DB_URL}/users/{mobile}.json")
        data = r.json()
        if data and data.get("password") == password:
            return data
        return None
