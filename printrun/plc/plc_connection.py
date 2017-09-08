import logging
import threading
import time

from Queue import Queue, Full, Empty
from printrun.serialWrapper import Serial, PARITY_NONE, PARITY_ODD, SerialException
from functools import wraps
from printrun.utils import PlcError
from printrun.plc import (ACK, SYN, EOT)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

PLC_CONNECTION_TIMEOUT = 1

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
        self.timeout = PLC_CONNECTION_TIMEOUT
        self.parity = PARITY_NONE
        self.plc = None
        self.msg_queue = None
        self.command_queue = Queue()
        self.stop_listen, self.stop_send = None, None
        self.listen_thread, self.send_thread = None, None

        # Handles new messages from plc
        self.on_recv = None
        self.on_disconnect = None
        self.log = None
        self.logError = None

    @locked
    def open(self, port=None, baud=None):

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
                self.log('Opening plc connection on %s ...' % self.port)
                self.plc = Serial(port=self.port,
                                  baudrate=self.baud,
                                  timeout=self.timeout,
                                  parity=self.parity)
                self._handshake()
            except SerialException as e:
                self.logError(("Could not connect to plc on %s at baudrate %s:") % (self.port, self.baud) +
                              "\n" + ("Serial error: %s") % e)
            except Exception as e:
                self.logError(("Could not connect to plc on %s at baudrate %s:") % (self.port, self.baud) +
                              "\n" + ("Error: %s") % e)
            else:
                self.log('Plc is online')
                self.stop_listen, self.stop_send = False, False
                self.listen_thread = threading.Thread(target=self._listen, name='listen_thread')
                self.listen_thread.start()
                return True
            finally:
                i += 1
        return False

        # raise PlcError('could not connect to plc')

    def send(self, command):
        try:
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
            self.log('Closing connection on %s ...' % self.port)
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
            self.logError('Could not close connection %s:' % self.port +
                          '\n' + 'Error %s' % e)

    def _handshake(self):
        if self.plc is not None:
            for i in xrange(CONNECTION_RETRIES_NUMBER):
                self.plc.write(SYN + '\n')
                time.sleep(0.1)
                msg = self.plc.read_until().rstrip()
                if msg == SYN + ACK:
                    self.plc.write(ACK + '\n')
                    return
                else:
                    self.plc.write(EOT + '\n')
                    time.sleep(0.1)

        raise PlcError('handshaking failed')

    def _listen(self):
        fail_count = 0
        while not self.stop_listen:
            try:
                # Reads until '\n' is found or timeout expires.
                msg = self.plc.read_until()
                if msg:
                    # self.log('Received message from %s: ' % self.port +
                    #          '\n' + msg)
                    self.on_recv(msg.rstrip())
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
