import Queue
import logging
import multiprocessing
from threading import Timer

from printrun.plc import *
from printrun.plc.plc_connection import PlcConnection
from printrun.utils import PlcError

CHECK_STATUS_TIMEOUT = 5
SUSPEND_TIMEOUT = 1
STOP_TIMEOUT = 0.1
POWER_UP_TIMEOUT = 5
POWER_DOWN_TIMEOUT = 5
INFO_TIMEOUT = 0.25

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


def set_for_callback(self, timeout, arg=None):
    def wrapper(f):
        def wrapped(_arg=None, *args, **kwargs):
            if wrapped.arg is None or _arg == wrapped.arg:
                if wrapped.timer.isAlive():  # or wrapped.arg == args[0]:
                    try:
                        wrapped.timer.cancel()
                    except Exception:
                        pass
            return f(_arg, *args, **kwargs)

        if not hasattr(f, 'timer'):
            wrapped.e = PlcError()
            wrapped.e.timeout = timeout
            wrapped.e.message = 'Could not receive response signal on %(port)s for %(timeout)s seconds'
            wrapped.arg = arg
            timer = wrapped.timer = Timer(timeout, self.on_error, [wrapped.e])
            timer.start()
            return wrapped
        f.arg = arg
        timer = f.timer = Timer(timeout, self.on_error, [f.e])
        timer.start()
        return f

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
        self.inner_queue = None

        self.connected = multiprocessing.Event()
        self.stopped = multiprocessing.Event()

        self.msg_handlers = {
            ACK: self.check_status,
            HALT: self.check_status,
            E_LIMIT: self.on_e_limits,
            E_BUTTON: self.on_e_button,
            PWR_UP: self.on_power_up,
            PWR_DOWN: self.on_power_down,
            SUSPEND: self.on_suspend,
            CONTINUE: self.on_continue,
            STOP: self.on_stop,
            ENABLE: self.on_enable
        }

    def run(self):

        if self.connection.open(printer_port=self.printer_port):
            self.inner_queue = Queue.Queue()
            self.connected.set()
            self.check_status = set_for_callback(self, CHECK_STATUS_TIMEOUT)(self.check_status)
            self.update_handlers()
        else:
            return
        while not self.stopped.is_set():
            try:
                if self.outer_pipe[1].poll():
                    msg = self.outer_pipe[1].recv()
                elif not self.inner_queue.empty():
                    msg = self.inner_queue.get_nowait()
                else:
                    msg = None
                if msg is not None:
                    try:
                        if len(msg) > 1:
                            self.msg_handlers[msg[0]](msg[1:])
                        else:
                            self.msg_handlers[msg[0]]()
                    except Exception as ex:
                        e = PlcError('Received corrupted message on %(port)s, check connection' +
                                     '\n' + 'Error: %s' % ex,
                                     port=self.connection.port)
                        self.on_error(e)
            except Exception:
                pass

        if self.connected.is_set():
            self.connected.clear()
            self.connection.close()
        else:
            self.connection.close(force=True)

    def subscribe(self):
        return self.outer_pipe[0]

    def update_handlers(self):
        self.msg_handlers = {
            ACK: self.check_status,
            HALT: self.check_status,
            E_LIMIT: self.on_e_limits,
            E_BUTTON: self.on_e_button,
            PWR_UP: self.on_power_up,
            PWR_DOWN: self.on_power_down,
            SUSPEND: self.on_suspend,
            CONTINUE: self.on_continue,
            STOP: self.on_stop,
            ENABLE: self.on_enable
        }

    def log(self, msg):
        self.outer_pipe[1].send('l' + msg)

    def logDebug(self, msg):
        self.outer_pipe[1].send('d' + msg)

    def logError(self, msg):
        self.outer_pipe[1].send('e' + msg)

    def on_disconnect(self):
        self.connected.clear()
        self.stopped.set()

    def on_recv(self, msg):
        if self.inner_queue is not None:
            try:
                self.inner_queue.put(msg)
            except Queue.Full as e:
                logger.error('Message queue overflow: %s' % e)

    def on_error(self, e):
        self.outer_pipe[1].send('e' + e.message)
        pass

    def on_power_up(self, msg=None):
        if msg[0] == REQ:
            self.log('Powering up...')
            self.connection.send(PWR_UP)
            self.on_power_up = set_for_callback(self, POWER_UP_TIMEOUT, RESP)(self.on_power_up)
            self.update_handlers()
        elif msg[0] == RESP:
            self.log('RECV: power up')

    def on_power_down(self, msg=None):
        if msg[0] == REQ:
            self.log('Powering down...')
            self.connection.send(PWR_DOWN)
            self.on_power_down = set_for_callback(self, POWER_DOWN_TIMEOUT, RESP)(self.on_power_down)
            self.update_handlers()
        elif msg[0] == RESP:
            self.log('RECV: power down')

    def on_suspend(self, msg=None):
        if msg[0] == REQ:
            self.log('Suspending print...')
            self.connection.send(SUSPEND)
            self.on_suspend = set_for_callback(self, SUSPEND_TIMEOUT, RESP)(self.on_suspend)
            self.update_handlers()
        if msg[0] == RESP:
            self.logDebug('RECV: print suspended')

    def on_continue(self, msg=None):
        if msg[0] == REQ:
            self.log('Continuing print...')
            self.connection.send(CONTINUE)
            self.on_continue = set_for_callback(self, SUSPEND_TIMEOUT, RESP)(self.on_continue)
            self.update_handlers()
        if msg[0] == RESP:
            self.logDebug('RECV: print continued')

    def on_stop(self, msg=None):
        if msg[0] == REQ:
            self.log('Stopping printer...')
            self.connection.send(STOP)
            self.on_stop = set_for_callback(self, STOP_TIMEOUT, RESP)(self.on_stop)
            self.update_handlers()
        if msg[0] == RESP:
            self.logDebug('RECV: printer stopped')

    def on_enable(self, msg=None):
        if msg[0] == REQ:
            self.log('Enabling printer...')
            self.connection.send(ENABLE)
            self.on_enable = set_for_callback(self, STOP_TIMEOUT, RESP)(self.on_enable)
            self.update_handlers()
        if msg[0] == RESP:
            self.logDebug('RECV: printer enabled')

    def check_status(self, msg=None):
        if msg is None:
            self.logDebug('RECV: plc is ok')
        elif msg[0] == HALT:
            self.logDebug('RECV: plc in halt state')
        self.check_status = set_for_callback(self, CHECK_STATUS_TIMEOUT)(self.check_status)
        self.update_handlers()
        return True

    def on_e_limits(self, msg=None):
        self.log('Emergency limit activated!')

    def on_e_button(self, msg=None):
        self.log('Emergency button pressed!')