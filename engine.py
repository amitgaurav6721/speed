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
        # Optimized Packet Structure for Bihar (vlts.bihar.gov.in)
        now = datetime.now()
        dt = now.strftime("%d%m%y")
        tm = now.strftime("%H%M%S")
        
        if is_handshake:
            # Login Packet (Handshake)
            return f"L,{tag},{imei},{v_no},01,1.0.0*\r\n"
        else:
            # High-Speed Data Packet
            return f"D,{tag},{imei},{v_no},A,{dt},{tm},{lat},{lon},000.0,000,12,01,100,00,00000000*\r\n"

    def handshake_worker(self, tag, imei, v_no, lat, lon):
        while not self.stop_event.is_set():
            try:
                # 🔥 Open new socket for every tag stream
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(10)
                    s.connect(("vlts.bihar.gov.in", 9999))
                    
                    # 1. First Handshake
                    h_pkt = self.create_packet(tag, imei, v_no, lat, lon, is_handshake=True)
                    s.sendall(h_pkt.encode())
                    time.sleep(0.1) # Wait for server acknowledgment
                    
                    # 2. Continuous Rapid Firing
                    # Reconnect every 1000 packets to keep connection fresh
                    for _ in range(1000):
                        if self.stop_event.is_set(): break
                        
                        d_pkt = self.create_packet(tag, imei, v_no, lat, lon)
                        s.sendall(d_pkt.encode())
                        
                        with self.lock:
                            self.total_sent += 1
                        
                        # 🔥 MAX SPEED: Only 1 millisecond sleep
                        time.sleep(0.001) 
                        
            except Exception as e:
                # Auto-retry on connection drop
                time.sleep(2)
                continue
