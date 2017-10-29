from plc_connection import PlcConnection
import socket

RASP_DEFAULT_HOSTNAME = 'localhost'
RASP_DEFAULT_PORT = 8080


class PlcRemoteConnection(PlcConnection):
    def __init__(self):
        self.hostname = RASP_DEFAULT_HOSTNAME
        PlcConnection.__init__(self)
        self.port = RASP_DEFAULT_PORT
        self.socket = None

    def open(self, port=None, baud=None, printer_port=None):
        self.plc = socket.socket(socket.AF_INET,
                                 socket.SOCK_STREAM)
        self.plc.setsockopt(
            socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.plc.settimeout(10.0)
        try:
            if port is not None:
                hostname, port = port.split(':')
                if hostname is not None:
                    self.hostname = hostname
                if port is not None:
                    self.port = port
            self.plc.connect((self.hostname, self.port))
            self.plc.settimeout(10.0)
            self.plc = self.plc.makefile('rw')
        except socket.error as e:
            e.strerror = ""
            self.logError(("Could not connect to %s:%s:") % (self.hostname, self.port) +
                          "\n" + ("Socket error %s:") % e.errno +
                          "\n" + e.strerror)
            self.plc = None
            return False
        return True

    def close(self):
        PlcConnection.close(self, force=True)
