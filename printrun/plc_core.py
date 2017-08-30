import sys
import logging
import time

from threading import Lock, Thread, Event
from Queue import Queue, Full
from plc_event_handler import PlcEventHandler
from serialWrapper import Serial, PARITY_ODD, SerialException
from functools import wraps


def locked(f):
    @wraps(f)
    def inner(*args, **kw):
        with inner.lock:
            return f(*args, **kw)

    inner.lock = Lock()
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
        self.parity = PARITY_ODD
        self.plc = None
        self.plc_event_handler = None
        self.command_queue = Queue()
        self.stop_listen, self.stop_send = None, None
        self.listen_thread, self.send_thread = None, None

    @locked
    def open(self):
        try:
            self.plc = Serial(port=self.port,
                              baudrate=self.baud,
                              timeout=self.timeout,
                              parity=self.parity)
        except SerialException as e:
            self.logError(("Could not connect to %s at baudrate %s:") % (self.port, self.baud) +
                          "\n" + ("Serial error: %s") % e)
            return
        except IOError as e:
            self.logError(("Could not connect to %s at baudrate %s:") % (self.port, self.baud) +
                          "\n" + ("IO error: %s") % e)
            return
        self.plc_event_handler = PlcEventHandler()
        self.stop_listen, self.stop_send = False, False
        self.listen_thread = Thread(target=self._listen(), name='listen_thread')
        self.send_thread = Thread(target=self._send(), name='send_thread')

    def send(self, command):
        try:
            self.command_queue.put(command, timeout=self.timeout)
        except Full as e:
            self.logError('Could not send command to %s:' % self.port +
                          '\n' + 'Queue error %s' % e)
        except Exception as e:
            self.logError('Could not send command to %s:' % self.port +
                          '\n' + 'Error %s' % e)

    def close(self):
        try:
            self.stop_listen, self.stop_send = True, True
            self.listen_thread.join()
            self.send_thread.join()
            self.plc.close()
        except Exception as e:
            self.self.logError('Could not close connection %s:' % self.port +
                               '\n' + 'Error %s' % e)

    def _listen(self):
        while not self.stop_listen:
            try:
                # Reads until '\n' is found or timeout expires.
                msg = self.plc.read_until()
                self.plc_event_handler.on_recv(msg)
            except SerialException as e:
                self.logError('Could not read data from %s:' % self.port +
                              '\n' + 'Serial error %s' % e)
            except Exception as e:
                self.logError('Could not read data from %s:' % self.port +
                              '\n' + 'Error %s' % e)

    def _send(self):
        while not self.stop_send:
            try:
                # Send next command from queue
                self.plc.write(self.command_queue.get())
                self.command_queue.task_done()
            except SerialException as e:
                self.logError('Could not send command to %s:' % self.port +
                              '\n' + 'Serial error %s' % e)
            except Exception as e:
                self.logError('Could not send command to %s:' % self.port +
                              '\n' + 'Error %s' % e)
