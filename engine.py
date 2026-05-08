import socket
import threading
import time
from datetime import datetime, timedelta, timezone

# 🔥 Class name fixed to match main.py import
class GpsEngine:
    def __init__(self, stop_event, lock):
        self.stop_event = stop_event
        self.lock = lock
        self.total_sent = 0

    def handshake_worker(self, tag, imei, vno, lat, lon):
        try:
            lat_v, lon_v = float(lat), float(lon)
        except Exception as e:
            print(f"Coord Error: {e}")
            return

        while not self.stop_event.is_set():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    s.settimeout(2)
                    s.connect(("vlts.bihar.gov.in", 9999))
                    while not self.stop_event.is_set():
                        for _ in range(50):
                            if self.stop_event.is_set(): break
                            now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                            
                            # 🔥 Strict Packet Pattern
                            pkt_str = f"$PVT,{tag},1.ONTC,NR,01,L,{imei},{vno},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{lat_v:.6f},N,{lon_v:.6f},E,0.0,348.79,31,0033.96,2.00,0.40,airtel,0,1,029.2,004.1,0,C,29,405,52,065d,45c2,45c1,065d,24,eeca,065d,17,bfd4,065d,17,384c,065d,16,0000,00,014722,A3270A39*"
                            
                            # End with strict line endings
                            full_pkt = pkt_str.encode('ascii') + b'\r\n'
                            
                            try:
                                s.sendall(full_pkt)
                                with self.lock:
                                    self.total_sent += 1
                            except:
                                break
                            time.sleep(0.005)
                        time.sleep(0.05)
            except Exception as e:
                time.sleep(0.5)
