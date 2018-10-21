import logging
import threading
import time
import sys
import os.path


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

from Queue import Queue, Full, Empty
from serialWrapper import Serial, PARITY_NONE, PARITY_ODD, SerialException
from functools import wraps
from utils import PlcError
from plc import (ACK, SYN, EOT)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

PLC_CONNECTION_TIMEOUT = 0.25

CONTROLLINO_PORT = '/dev/ttyACM'
CONTROLLINO_BAUD = 57600
CONNECTION_RETRIES_NUMBER = 5
MAX_READ_ATTEMPTS = 5


# ch = logging.StreamHandler()
# logger.addHandler(ch)


def locked(f):
    @wraps(f)
    def inner(*args, **kw):
        with inner.lock:
            return f(*args, **kw)

    inner.lock = threading.Lock()
    return inner


def terminate_with(event, f):
    @wraps(f)
    def inner(self, *args, **kwargs):
        while not getattr(self, event):
            f(self, *args, **kwargs)
        return

    return inner


class PlcConnection(object):
    def __init__(self):
        self.port = CONTROLLINO_PORT
        self.baud = CONTROLLINO_BAUD
        self.hostname = None
        self.timeout = PLC_CONNECTION_TIMEOUT
        self.parity = PARITY_NONE
        self.plc = None
        self.msg_queue = None
        self.command_queue = Queue()
        self.stop_listen, self.stop_send = False, False
        self.listen_thread, self.send_thread = None, None

        # Handles new messages from plc
        self.on_recv = None
        self.on_write = None
        self.on_disconnect = None
        self.log = logging.log
        self.logDebug = logging.debug
        self.logError = logging.error

    @locked
    def open(self, port=None, baud=None, printer_port=None):

        if baud is not None:
            self.baud = baud
        i = 0
        default_port = self.port
        while i < 5:
            try:
                if port is None:
                    self.port = default_port + str(i)
                else:
                    self.port = port
                    i = 4
                if self.port == printer_port:
                    continue
                self.logDebug("Opening plc connection on %s ..." % self.port)
                self.plc = Serial(port=self.port,
                                  baudrate=self.baud,
                                  timeout=self.timeout,
                                  parity=self.parity)
                self._handshake()
            except SerialException as e:
                self.logError(("Could not connect to plc on %s at baudrate %s:") % (self.port, self.baud) +
                              "\n" + ("Serial error: %s") % e)
            except PlcError as e:
                self.logError(("Could not connect to plc on %s at baudrate %s:") % (self.port, self.baud) +
                              "\n" + "PlcError: " + e.message)
            except Exception as e:
                self.logError(("Could not connect to plc on %s at baudrate %s:") % (self.port, self.baud) +
                              "\n" + ("Error: %s") % e)
            else:
                self.logDebug('Plc is online')
                self.listen_thread = threading.Thread(target=self._listen, name='listen_thread')
                self.listen_thread.start()
                return True
            finally:
                i += 1
        return False

    def _handshake(self):
        if self.plc is not None:
            for i in xrange(CONNECTION_RETRIES_NUMBER):
                self.plc.write(SYN + '\n')
                time.sleep(0.1)
                msg = self.plc.readline().rstrip()
                if msg == SYN + ACK:
                    self.plc.write(ACK + '\n')
                    return True
                else:
                    self.plc.write(EOT + '\n')
                    time.sleep(0.1)
            e = PlcError('handshaking on %(port)s failed after %(num)s attemts',
                         port=self.port, num=CONNECTION_RETRIES_NUMBER)
            raise e
        else:
            e = PlcError('handshaking on %(port)s failed, serial connection must be opened first',
                         port=self.port)
            raise e

    def send(self, command):
        try:
            if command is None or len(command) == 0:
                return
            if command[len(command) - 1] != '\n':
                command += '\n'
            self.command_queue.put(command, timeout=self.timeout)
            if self.send_thread is None:
                self.send_thread = threading.Thread(target=self._send, name='send_thread')
                self.send_thread.start()
        except Full:
            self.logError('Could not send command to %s:' % self.port +
                          '\n' + 'Command queue overflow')
        except Exception as e:
            self.logError('Could not send command to %s:' % self.port +
                          '\n' + 'Error %s' % e)

    def close(self, force=False):
        try:
            self.logDebug('Closing connection on %s ...' % self.port)
            self.stop_listen, self.stop_send = True, True
            if self.listen_thread is not None:
                self.listen_thread.join()
            if self.send_thread is not None:
                self.send_thread.join()
            if self.plc is not None:
                if not force:
                    self.plc.write(EOT + '\n')
                self.plc.close()
        except Exception as e:
            e = PlcError("Couldn't close connection on %(port)s" +
                         "\n" + "Error: %s" % e, port=self.port)
            raise e

    def _listen(self):
        fail_count = 0
        while not self.stop_listen:
            try:
                # Reads until '\n' is found or timeout expires.
                msg = self.plc.readline()
                # self.logDebug('Received message on serial: ' + msg)
            except PlcError as e:
                self.logError('PlcCommunicationError on %s:' % self.port +
                              '\n' + e.message)
                fail_count += 1
            except SerialException as e:
                self.logError('Could not read data from %s:' % self.port +
                              '\n' + 'Serial error %s' % e)
                fail_count += 1
            except Exception as e:
                self.logError('Could not read data from %s:' % self.port +
                              '\n' + 'Error %s' % e)
                fail_count += 1
            else:
                fail_count = 0
                # On_recv exceptions must be handled outside
                if msg:
                    if self.on_recv is not None:
                        try:
                            msg = msg.rstrip(' \n')
                            self.on_recv(msg + '\n')
                            # self.logDebug('Handled message on serial: ' + msg)
                        except Exception as e:
                            self.logError('%s' % e)

            finally:
                if fail_count > MAX_READ_ATTEMPTS - 2:
                    self.logError('Closing plc connection after %s ' % MAX_READ_ATTEMPTS + 'read attempts...')
                    self.on_disconnect()
                    return

    def _send(self):
        while not self.stop_send:
            try:
                # Try sending next command from queue or raise Empty exception after timeout
                msg = self.command_queue.get(timeout=self.timeout)
                self.plc.write(msg)
                if self.on_write is not None:
                    try:
                        self.on_write()
                    except Exception as e:
                        self.logError('%s' % e)
                self.command_queue.task_done()
                # logger.debug('Sent message to %s: ' % self.port +
                #              '\n' + msg)
            except Empty:
                pass
            except SerialException as e:
                self.logError('Could not send command to %s:' % self.port +
                              '\n' + 'Serial error %s' % e)
            except Exception as e:
                self.logError('Could not send command to %s:' % self.port +
                              '\n' + 'Error %s' % e)
