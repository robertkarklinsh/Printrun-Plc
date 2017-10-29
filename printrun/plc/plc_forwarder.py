import sys
import socket
import logging
import argparse
import time

from serial import SerialException
from plc_connection import PlcConnection

RASP_DEFAULT_HOSTNAME = 'localhost'
RASP_DEFAULT_PORT = 8080


class PlcForwarder(object):
    def __init__(self):
        self.serial_conn = PlcConnection()
        self.serial_conn.log, self.serial_conn.logError, self.serial_conn.logDebug = logging.log, logging.debug, logging.error
        self.sock = None
        self.tcp_conn = None
        self.hostname = RASP_DEFAULT_HOSTNAME
        self.port = RASP_DEFAULT_PORT
        self.stop_forwarding = False

    def open_tcp_connection(self, hostname=None, port=None):
        self.sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_STREAM)
        self.sock.setsockopt(
            socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        #self.sock.settimeout(30.0)

        if hostname is not None: self.hostname = hostname
        if port is not None: self.port = port

        try:
            self.sock.bind((self.hostname, self.port))
            self.sock.listen(1)
            self.tcp_conn, addr = self.sock.accept()
            self.tcp_conn = self.tcp_conn.makefile()
        except Exception as e:
            logging.error("Couldn't open tcp connection %s:%s" % (self.hostname, self.port) +
                          "\n" + "Socket error: %s" % e)

            self.stop()
            sys.exit(1)
        else:
            logging.debug("%s " % addr[0] + "connected")
            return True

    def open_serial_connection(self, port=None, baud=None):
        if not self.serial_conn.open(port, baud):
            self.stop()
            sys.exit(1)
        else:
            return True

    def start(self):

        if self.serial_conn is None:
            raise Exception("Couldn't start forwarding, no serial connection")
        if self.tcp_conn is None:
            raise Exception("Couldn't start forwarding, no tcp connection")
        msg = None
        read_attempts_count = 4
        write_attempts_count = 4
        self.serial_conn.on_recv = self.sock.send
        while not self.stop_forwarding:
            if read_attempts_count < 1:
                raise Exception("Closing connections and exiting after 4 read attempts...")
            if write_attempts_count < 1:
                raise Exception("Closing connections and exiting after 4 write attempts...")
            try:
                msg = self.tcp_conn.readline()
            except socket.error as e:
                logging.error("Couldn't read from tcp" + '\n' +
                              "Socket error: %s" % e)
                read_attempts_count -= 1
            except Exception as e:
                logging.error("Couldn't read from tcp" + '\n' +
                              "Error: %s" % e)
                read_attempts_count -= 1
            else:
                read_attempts_count = 4
            try:
                self.serial_conn.send(msg)
            except SerialException as e:
                logging.error("Couldn't write to serial" + '\n' +
                              "Serial error: %s" % e)
                write_attempts_count -= 1
            except Exception as e:
                logging.error("Couldn't write to serial" + '\n' +
                              "Error: %s" % e)
                write_attempts_count -= 1
            else:
                write_attempts_count = 4
        return True

    def stop(self):
        self.stop_forwarding = True
        if self.serial_conn is not None:
            self.serial_conn.close(force=True)
        if self.tcp_conn is not None:
            self.tcp_conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ethernet to serial adapter for plc')
    parser.add_argument('--tcp', dest='tcp', help="IP socket address to listen in format 'hostname:port' ")
    parser.add_argument('--serial', dest='serial', help='Plc serial port name')
    args = parser.parse_args()

    plc_forwarder = PlcForwarder()
    plc_forwarder.open_serial_connection(port=args.serial)
    if args.tcp is not None:
        hostname, port = args.tcp.split(':')
        port = int(port)
        plc_forwarder.open_tcp_connection(hostname, port)
    else:
        plc_forwarder.open_tcp_connection()
    try:
        plc_forwarder.start()
    except KeyboardInterrupt:
        print "Closing connections and exiting..."
        plc_forwarder.stop()
        sys.exit(0)
    except Exception as e:
        plc_forwarder.stop()
        print str(e) + "\n"
        sys.exit(1)
