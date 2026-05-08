import socket
import time
import threading
from datetime import datetime, timedelta, timezone

class GpsEngine:
    def __init__(self, stop_event, lock):
        self.stop_event = stop_event
        self.lock = lock
        self.total_sent = 0

    def create_nitro_packet(self, tag, imei, vno, lat, lon):
        now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        dt, tm = now_ist.strftime('%d%m%Y'), now_ist.strftime('%H%M%S')
        # 🔥 Nitro-V82 Protocol with DDE3 Checksum
        return f"$PVT,{tag},2.1.1,NR,01,L,{imei},{vno},1,{dt},{tm},{lat},N,{lon},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*\\r\\n"

    def handshake_worker(self, tag, imei, vno, lat, lon):
        while not self.stop_event.is_set():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect(("vlts.bihar.gov.in", 9999))
                pkt = self.create_nitro_packet(tag, imei, vno, lat, lon)
                s.sendall(pkt.encode('ascii'))
                with self.lock:
                    self.total_sent += 1
                s.close()
                time.sleep(0.05) # Firing interval
            except:
                time.sleep(1)
                continue
