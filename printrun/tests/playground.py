from printrun.plc.plc_forwarder import PlcForwarder
from printrun.plc.plc_remote_connection import PlcRemoteConnection
import socket
import sys
import logging

fwd = PlcForwarder()
fwd.listen()
# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
plc_conn = PlcRemoteConnection()
plc_conn.open()
# sock.connect(('localhost', 8080))
conn, addrs = fwd.accept()
conn.settimeout(5.0)
conn = conn.makefile('rw')
# sock = sock.makefile('rw')
sock = plc_conn.plc
sock.write('Hello!')
sock.flush()
#plc_conn.socket.close()
sock.close()
msg = conn.read(1024)
print msg
conn.close()
