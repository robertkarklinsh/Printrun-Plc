import sys
import logging
import time
import threading

from Queue import Queue, Full, Empty
from plc_event_handler import PlcEventHandler
from serialWrapper import Serial, PARITY_NONE, PARITY_ODD, SerialException
from functools import wraps

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
    def __init__(self, baud=None, port=None):
        self.baud = baud
        self.port = port
        self.timeout = 0.25
        self.parity = PARITY_NONE
        self.plc = None
        self.plc_event_handler = None
        self.command_queue = Queue()
        self.stop_listen, self.stop_send = None, None
        self.listen_thread, self.send_thread = None, None

    @locked
    def open(self):

        try:
            logger.debug('Opening connection on %s ...' % self.port)
            self.plc = Serial(port=self.port,
                              baudrate=self.baud,
                              timeout=self.timeout,
                              parity=self.parity)
        except SerialException as e:
            logger.error(("Could not connect to %s at baudrate %s:") % (self.port, self.baud) +
                         "\n" + ("Serial error: %s") % e)
            return
        except IOError as e:
            logger.error(("Could not connect to %s at baudrate %s:") % (self.port, self.baud) +
                         "\n" + ("IO error: %s") % e)
            return
        self.plc_event_handler = PlcEventHandler()
        self.stop_listen, self.stop_send = False, False
        self.listen_thread = threading.Thread(target=self._listen, name='listen_thread')
        self.listen_thread.start()

    def send(self, command):
        try:
            self.command_queue.put(command, timeout=self.timeout)
            if self.send_thread is None:
                self.send_thread = threading.Thread(target=self._send, name='send_thread')
                self.send_thread.start()
        except Full:
            logger.error('Could not send command to %s:' % self.port +
                         '\n' + 'Command queue overflow')
        except Exception as e:
            logger.error('Could not send command to %s:' % self.port +
                         '\n' + 'Error %s' % e)

    def close(self):
        try:
            logger.debug('Closing connection on %s ...' % self.port)
            self.stop_listen, self.stop_send = True, True
            if self.listen_thread is not None:
                self.listen_thread.join()
            if self.send_thread is not None:
                self.send_thread.join()
            if self.plc is not None:
                self.plc.close()
        except Exception as e:
            logger.error('Could not close connection %s:' % self.port +
                         '\n' + 'Error %s' % e)

    def _listen(self):
        while not self.stop_listen:
            try:
                # Reads until '\n' is found or timeout expires.
                msg = self.plc.read_until()
                if msg:
                    logger.debug('Received message from %s: ' % self.port +
                                 '\n' + msg)
                    self.plc_event_handler.on_recv(msg)
            except SerialException as e:
                logger.error('Could not read data from %s:' % self.port +
                             '\n' + 'Serial error %s' % e)
            except Exception as e:
                logger.error('Could not read data from %s:' % self.port +
                             '\n' + 'Error %s' % e)

    def _send(self):
        while not self.stop_send:
            try:
                # Send next command from queue
                msg = self.command_queue.get(timeout=self.timeout)
                self.plc.write(msg)
                self.command_queue.task_done()
                logger.debug('Sent message to %s: ' % self.port +
                             '\n' + msg)
            except Empty:
                pass
            except SerialException as e:
                logger.error('Could not send command to %s:' % self.port +
                             '\n' + 'Serial error %s' % e)
            except Exception as e:
                logger.error('Could not send command to %s:' % self.port +
                             '\n' + 'Error %s' % e)
