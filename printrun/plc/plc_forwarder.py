import sys
import socket
import logging
import argparse
import time

from serial import SerialException
from plc_connection import PlcConnection
from printrun.utils import PlcError

RASP_DEFAULT_HOSTNAME = 'localhost'
RASP_DEFAULT_PORT = 8080

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def flushed_write(file_object):
    def wrraped(msg):
        file_object.write(msg)
        file_object.flush()

    return wrraped


class PlcForwarder(object):
    def __init__(self):
        self.serial_conn = PlcConnection()
        self.serial_conn.log, self.serial_conn.logError, self.serial_conn.logDebug = logger.log, logger.error, logger.debug
        self.sock = None
        self.tcp_conn = None
        self.hostname = RASP_DEFAULT_HOSTNAME
        self.port = RASP_DEFAULT_PORT
        self.client_addr = None
        self.stop_forwarding = False

    def open_tcp_connection(self, hostname=None, port=None):
        self.sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.sock.setsockopt(
            socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        # self.sock.settimeout(30.0)

        if hostname is not None: self.hostname = hostname
        if port is not None: self.port = port

        try:
            self.sock.bind((self.hostname, self.port))
            self.sock.listen(1)
            logger.debug('Listening on ' + self.hostname + ':' + str(self.port) + ' ...')
            self.tcp_conn, addr = self.sock.accept()
            self.client_addr = addr[0]
            logger.debug("%s " % self.client_addr + "connected")
            self.sock = self.tcp_conn
            self.tcp_conn = self.tcp_conn.makefile(mode='r+')
        except Exception as er:
            logger.error("Couldn't open tcp connection %s:%s" % (self.hostname, self.port) +
                         "\n" + "Socket error: %s" % er)

            self.exit()
        return True

    def open_serial_connection(self, port=None, baud=None):
        if self.tcp_conn is None:
            logger.error("Can't open serial with no tcp connection, exiting...")
            self.exit()
        if self.serial_conn is None:
            self.serial_conn = PlcConnection()
        if not self.serial_conn.open(port, baud):
            logger.error("Couldn't open serial connection, exiting...")
            self.exit()
        self.serial_conn.on_recv = flushed_write(self.tcp_conn)
        self.serial_conn.on_disconnect = self.exit
        return True

    def start(self):

        if self.serial_conn is None:
            logger.error("Couldn't start forwarding, no serial connection")
            self.exit()
        if self.tcp_conn is None:
            logger.error("Couldn't start forwarding, no tcp connection")
            self.exit()
        read_attempts_count = 4
        while not self.stop_forwarding:
            if read_attempts_count < 1:
                logger.error("Closing connections and exiting after 4 read attempts...")
                self.exit()
            try:
                msg = self.tcp_conn.readline()
                logger.debug("Received message on tcp:" + msg)
            except socket.error as er:
                logger.error("Couldn't read from tcp" + '\n' +
                             "Socket error: %s" % er)
                read_attempts_count -= 1
            except Exception as er:
                logger.error("Couldn't read from tcp" + '\n' +
                             "Error: %s" % er)
                read_attempts_count -= 1
            else:
                read_attempts_count = 4
                if msg:
                    if len(msg) > 0:
                        self.serial_conn.send(msg)
                else:
                    logger.debug("%s " % self.client_addr + " disconnected, closing connections...")
                    if self.serial_conn is not None:
                        try:
                            self.serial_conn.close()
                        except PlcError as er:
                            logger.error(er.message)
                            self.exit()
                        self.serial_conn = None
                    if self.tcp_conn is not None:
                        try:
                            logger.debug("Closing connection on %s:%s..." % (self.hostname, self.port))
                            self.tcp_conn.close()
                            self.sock.close()
                        except Exception as er:
                            logger.error("Couldn't close tcp connection on %s:%s" % (self.hostname, self.port)
                                         + "\n" + "Error: %s" % er)
                            self.exit()
                        self.tcp_conn = None
                    self.stop_forwarding = True

    def exit(self, status=1):
        self.stop_forwarding = True
        if self.serial_conn is not None:
            try:
                self.serial_conn.close()
            except PlcError as er:
                logger.error(er.message)
        if self.tcp_conn is not None:
            try:
                self.tcp_conn.close()
                self.sock.close()
            except Exception as er:
                logger.error("Couldn't close tcp connection on %s:%s" % (self.hostname, self.port)
                             + "\n" + "Error: %s" % er)
        sys.exit(status)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ethernet to serial adapter for plc')
    parser.add_argument('--hostname', dest='hostname', default=RASP_DEFAULT_HOSTNAME,
                        help='Hostname of socket to listen')
    parser.add_argument('--port', dest='port', default=RASP_DEFAULT_PORT, help='Port of socket to listen')
    parser.add_argument('--serial', dest='serial', help='Plc serial port name')
    args = parser.parse_args()

    plc_forwarder = PlcForwarder()

    address = args.hostname + ':' + args.port
    plc_forwarder.hostname, port = args.tcp.split(':')
    plc_forwarder.port = int(port)

    try:
        while True:
            if not plc_forwarder.open_tcp_connection():
                plc_forwarder.exit()
            if not plc_forwarder.open_serial_connection(port=args.serial):
                plc_forwarder.exit()
            plc_forwarder.start()
            plc_forwarder.stop_forwarding = False

    except KeyboardInterrupt:
        print ("Closing connections and exiting...")
        plc_forwarder.exit()
    except Exception as e:
        print (str(e) + "\n")
        plc_forwarder.exit()
