import Queue
import logging
import multiprocessing
from threading import Timer
import sys
import os.path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

from plc import *
from plc.plc_remote_connection import PlcRemoteConnection
from plc.plc_connection import PlcConnection
from utils import PlcError

CHECK_STATUS_TIMEOUT = 5
SUSPEND_TIMEOUT = 1
STOP_TIMEOUT = 0.1
POWER_UP_TIMEOUT = 5
POWER_DOWN_TIMEOUT = 5
HARD_RESET_TIMEOUT = 5
INFO_TIMEOUT = 0.25

CONTROLLINO_PORT = '/dev/ttyACM'
CONTROLLINO_BAUD = 57600

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Set callback to fire with (*callback_args[0], **callback_args[1]) if wrapped function isn't called with
# (*wrapped_args[0], **wrapped_args[1]) for timeout
def set_callback(callback=None, timeout=None, wrapped_args=((), {}), callback_args=((), {})):
    def wrapper(f):
        if hasattr(f, 'timer'):
            f.callback = callback
            f.timeout = timeout
            f.args = wrapped_args
            f.callback_args = callback_args

            f.timer = Timer(timeout, callback, args=callback_args[0], kwargs=callback_args[1])
            return f

        def wrapped(*_args, **_kwargs):
            if not wrapped.args[0] and not wrapped.args[1]:
                if wrapped.timer.isAlive():
                    try:
                        wrapped.timer.cancel()
                    except Exception:
                        pass
                return f(*_args, **_kwargs)
            if wrapped.args[0]:
                if _args == wrapped.args[0]:
                    if wrapped.timer.isAlive():
                        try:
                            wrapped.timer.cancel()
                        except Exception:
                            pass
            else:
                if _kwargs == wrapped.args[1]:
                    if wrapped.timer.isAlive():
                        try:
                            wrapped.timer.cancel()
                        except Exception:
                            pass
            return f(*_args, **_kwargs)

        wrapped.callback = callback
        wrapped.timeout = timeout
        wrapped.args = wrapped_args
        wrapped.callback_args = callback_args

        wrapped.timer = Timer(timeout, callback, args=callback_args[0], kwargs=callback_args[1])
        return wrapped

    return wrapper


def update_timer(f):
    if hasattr(f, 'timer'):
        timer = f.timer = Timer(f.timeout, f.callback, args=f.callback_args[0], kwargs=f.callback_args[1])
        timer.start()


class PlcHandler(multiprocessing.Process):
    def __init__(self, local=True, printer_port=None):
        multiprocessing.Process.__init__(self)

        self.outer_pipe = multiprocessing.Pipe()
        # self.connection = PlcConnection()
        # Remote connection is established via Raspberry as ethernet-to-serial adapter
        if local:
            self.connection = PlcConnection()
        else:
            self.connection = PlcRemoteConnection()
        self.printer_port = printer_port
        self.connection.on_recv = self.on_recv
        self.connection.on_disconnect = self.on_disconnect
        self.connection.log = self.log
        self.connection.logError = self.logError
        self.connection.logDebug = self.logDebug
        self.inner_queue = None

        self.connected = multiprocessing.Event()
        self.stopped = multiprocessing.Event()

    def run(self):

        @set_callback()
        def check_status(msg=None):
            if msg is None:
                self.logDebug('RECV:PLC: ok')
            elif msg == HALT:
                self.logDebug('RECV:PLC: !!')
            update_timer(check_status)
            return True

        @set_callback()
        def on_power_up(context, msg=None):
            if context == REQ:
                self.log('Powering up...')
                self.connection.send(PWR_UP)
                set_callback(self.on_error, POWER_UP_TIMEOUT, wrapped_args=((RESP,), {}), callback_args=((
                                                                                                             'Could not receive response for poweron for %s' % POWER_UP_TIMEOUT,),
                                                                                                         {}))(
                    on_power_up)
                on_power_up.timer.start()
                # self.update_handlers()
            elif context == RESP:
                self.log('RECV: Power is ON!')

        @set_callback()
        def on_power_down(context, msg=None):
            if context == REQ:
                self.log('Powering down...')
                self.connection.send(PWR_DOWN)
                set_callback(self.on_error, POWER_DOWN_TIMEOUT, wrapped_args=((RESP,), {}), callback_args=(
                    (
                        'Could not receive response for poweroff for %s' % POWER_DOWN_TIMEOUT,),
                    {}))(on_power_down)

            elif context == RESP:
                self.log('RECV: Power is OFF!')

        @set_callback()
        def on_suspend(context, msg=None):
            if context == REQ:
                self.logDebug('Suspending print...')
                self.connection.send(SUSPEND)
                set_callback(self.on_error, SUSPEND_TIMEOUT, wrapped_args=((RESP,), {}), callback_args=((
                                                                                                            'Could not receive response for suspend for %s' % SUSPEND_TIMEOUT,),
                                                                                                        {}))(
                    on_suspend)
            elif context == RESP:
                self.logDebug('RECV:PLC: Print suspended')

        @set_callback()
        def on_continue(context, msg=None):
            if context == REQ:
                self.logDebug('Continuing print...')
                self.connection.send(CONTINUE)
                set_callback(self.on_error, POWER_DOWN_TIMEOUT, wrapped_args=((RESP,), {}), callback_args=((
                                                                                                               'Could not receive response for continue for %s' % SUSPEND_TIMEOUT,),
                                                                                                           {}))(
                    on_continue)
            if context == RESP:
                self.logDebug('RECV:PLC: Print continued')

        @set_callback()
        def on_stop(context, msg=None):
            if context == REQ:
                self.logDebug('Stopping printer...')
                self.connection.send(STOP)
                set_callback(self.on_error, STOP_TIMEOUT, wrapped_args=((RESP,), {}), callback_args=((
                                                                                                         'Could not receive response for stop for %s' % STOP_TIMEOUT,),
                                                                                                     {}))(
                    on_stop)
            if context == RESP:
                self.logDebug('RECV:PLC: Printer stopped')

        @set_callback()
        def on_enable(context, msg=None):
            if context == REQ:
                self.logDebug('Enabling printer...')
                self.connection.send(ENABLE)
                set_callback(self.on_error, STOP_TIMEOUT, wrapped_args=((RESP,), {}), callback_args=((
                                                                                                         'Could not receive response for enable for %s' % STOP_TIMEOUT,),
                                                                                                     {}))(
                    on_enable)
            if context == RESP:
                self.logDebug('RECV:PLC: Printer enabled')

        @set_callback()
        def on_hardreset(context, msg=None):
            if context == REQ:
                self.connection.send(HARDRESET)
                set_callback(self.on_error, HARD_RESET_TIMEOUT, wrapped_args=((RESP,), {}), callback_args=((
                                                                                                         'Could not receive response for hardreset for %s' % HARD_RESET_TIMEOUT,),
                                                                                                     {}))(
                    on_hardreset)
            if context == RESP:
                self.logDebug('RECV:PLC: Hard reset issued, please wait')

        def on_e_limits(msg=None):
            self.log('RECV: Emergency limit activated!')

        def on_e_button(msg=None):
            self.log('RECV: Emergency button pressed!')

        if self.connection.open(port=self.printer_port):
            self.inner_queue = Queue.Queue()
            self.connected.set()
            set_callback(self.on_error, CHECK_STATUS_TIMEOUT, callback_args=(
                ('Plc not responding on %(hostname)s:%(port)s',),
                {}))(check_status)
            check_status.timer.start()
        else:
            return

        msg_handlers = {
            ACK: check_status,
            HALT: check_status,
            E_LIMIT: on_e_limits,
            E_BUTTON: on_e_button,
            PWR_UP: on_power_up,
            PWR_DOWN: on_power_down,
            SUSPEND: on_suspend,
            CONTINUE: on_continue,
            STOP: on_stop,
            ENABLE: on_enable,
            HARDRESET: on_hardreset
        }

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
                        if len(msg) > 2:
                            msg_handlers[msg[0]](msg[1], msg[2:])
                        elif len(msg) > 1:
                            msg_handlers[msg[0]](msg[1])
                        else:
                            msg_handlers[msg]()
                    except Exception as ex:
                        e = PlcError('Received corrupted message on %(port)s, check connection' +
                                     '\n' + 'Error: %s' % ex,
                                     port=self.connection.port)
                        self.on_error(e.message)
            except Exception:
                pass

        if self.connected.is_set():
            self.connected.clear()
            self.connection.close()
        else:
            self.connection.close(force=True)

    def subscribe(self):
        return self.outer_pipe[0]

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
                self.inner_queue.put(msg.rstrip(' \n'))
            except Queue.Full as e:
                self.logError('Message queue overflow: %s' % e)

    def on_error(self, msg, **kwargs):
        e = PlcError()
        e.message = msg
        if self.connected.is_set():
            e.port = self.connection.port
            if self.connection.hostname is not None:
                e.hostname = self.connection.hostname
        for kw in kwargs:
            e.__setattr__(kw, kwargs[kw])
        self.outer_pipe[1].send('e' + e.message)