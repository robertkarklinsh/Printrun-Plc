import sys
import os.path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

from plc_connection import PlcConnection
from utils import PlcError
import socket
import threading

RASP_DEFAULT_HOSTNAME = '10.0.0.31'
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
        try:
            if port is not None:
                hostname, port = port.split(':')
                if hostname is not None:
                    self.hostname = hostname
                if port is not None:
                    self.port = int(port)
            #self.logDebug('Connecting to ' + self.hostname + ':' + str(self.port) + '...')
            self.plc.connect((self.hostname, self.port))
            #self.logDebug('Connected!')
            self.socket = self.plc
            self.plc = self.plc.makefile(mode='r+')
            self.on_write = self.plc.flush
            self.listen_thread = threading.Thread(target=self._listen, name='listen_thread')
            self.listen_thread.start()
        except socket.error as e:
            e.strerror = ""
            self.logError(("Could not connect to %s:%s") % (self.hostname, self.port) +
                          "\n" + ("Socket error %s:") % e.errno +
                          "\n" + e.strerror)
            self.plc = None
            return False
        except PlcError as e:
            self.logError(e.message)
            return False
        return True

    def close(self, force=True):
        PlcConnection.close(self, force)
        self.socket.close()
