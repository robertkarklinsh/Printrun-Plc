import Queue
import logging
import multiprocessing
from threading import Timer

from printrun.plc import (ACK, PWR_ON, PWR_OFF, E_LIMIT, E_BUTTON)
from printrun.plc.plc_connection import PlcConnection
from printrun.utils import PlcError

PLC_CHECK_STATUS_TIMEOUT = 5
PLC_INFO_TIMEOUT = 0.25

CONTROLLINO_PORT = '/dev/ttyACM'
CONTROLLINO_BAUD = 57600

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# def allow_subscription(f):
#     def wrapped(*args, **kwargs):
#         if wrapped.callbacks is None:
#             return f(*args, **kwargs)
#         else:
#             for callback in wrapped.callbacks:
#                 callback(f(*args, **kwargs))
#
#     wrapped.callbacks = []
#     return wrapped


def set_timeout(timeout):
    def wrapper(f):
        def wrapped(self, *args, **kwargs):
            timer = wrapped.timer
            if timer is not None:
                timer.cancel()
            wrapped.timer = timer = Timer(timeout, self.on_error, [wrapped.e])
            timer.start()
            return f(self, *args, **kwargs)

        wrapped.e = PlcError()
        wrapped.e.message = 'Could not receive OK signal on %(port)s for %(timeout)s'
        wrapped.e.timeout = timeout
        wrapped.timer = None
        return wrapped

    return wrapper


class PlcHandler(multiprocessing.Process):
    def __init__(self, printer_port=None):
        multiprocessing.Process.__init__(self)

        self.outer_pipe = multiprocessing.Pipe()

        self.connection = PlcConnection()
        self.printer_port = printer_port
        self.connection.on_recv = self.on_recv
        self.connection.on_disconnect = self.on_disconnect
        self.connection.log = self.log
        self.connection.logError = self.logError
        self.connection.logDebug = self.logDebug
        self.msg_queue = None

        self.connected = multiprocessing.Event()
        self.stopped = multiprocessing.Event()

        self.msg_handlers = {
            ACK: self.check_status,
            PWR_ON: self.power_switching,
            PWR_OFF: self.power_switching,
            E_LIMIT: self.emergency_limit_stop,
            E_BUTTON: None,
        }

    def run(self):

        if self.connection.open(printer_port=self.printer_port):
            self.msg_queue = Queue.Queue()
            self.connected.set()
        else:
            return
        while not self.stopped.is_set():
            try:
                msg = self.msg_queue.get_nowait()
                if msg is not None:
                    try:
                        if len(msg) > 0:
                            self.msg_handlers[msg[0]](msg[1:])
                        else:
                            self.msg_handlers[msg[0]]()
                    except Exception as ex:
                        e = PlcError('Received corrupted message: ' + msg +
                                     'on %(port)s, check connection' +
                                     '\n' + 'Error: %s' % ex,
                                     port=self.connection.port)
                        self.on_error(e)
            except Queue.Empty:
                pass

        if self.connected.is_set():
            self.connected.clear()
            self.connection.close()
        else:
            self.connection.close(force=True)

    def subscribe(self):
        return self.outer_pipe[1]

    def log(self, msg):
        self.outer_pipe[0].send('l' + msg)

    def logDebug(self, msg):
        self.outer_pipe[0].send('d' + msg)

    def logError(self, msg):
        self.outer_pipe[0].send('e' + msg)

    def on_disconnect(self):
        self.connected.clear()
        self.stopped.set()

    def on_recv(self, msg):
        if self.msg_queue is not None:
            try:
                self.msg_queue.put(msg)
            except Queue.Full as e:
                logger.error('Message queue overflow: %s' % e)

    def on_error(self, e):
        self.outer_pipe[0].send('e' + e.message)
        pass

    @set_timeout(PLC_CHECK_STATUS_TIMEOUT)
    def check_status(self, *args):
        self.log('CONTROLLINO: OK')
        return True

    def power_switching(self, msg):
        # write power status to console
        raise NotImplementedError

    def emergency_limit_stop(self, msg):
        raise NotImplementedError
