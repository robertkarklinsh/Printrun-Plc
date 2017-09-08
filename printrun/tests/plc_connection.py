import sys
import time
from multiprocessing import Queue

from printrun.plc.plc_handler import PlcHandler


def test_connection(f, q):
    def wrapped(*args, **kwargs):
        q.put('OK')
        return f(*args, **kwargs)

    return wrapped


def log_to_stdout(f):
    def wrapped(self, msg):
        sys.stdout.write(msg)

    return wrapped


if __name__ == '__main__':
    q = Queue()
    PlcHandler.check_status = test_connection(PlcHandler.check_status, q)
    PlcHandler.log = log_to_stdout(PlcHandler.log)
    PlcHandler.logError = log_to_stdout(PlcHandler.logError)
    plc_proc = PlcHandler()
    plc_proc.start()
    time.sleep(30)
    plc_proc.stopped.set()
    plc_proc.join()
    try:
        msg = q.get(block=False)
        sys.exit(0) if msg == 'OK' else sys.exit(1)
    except Exception:
        sys.exit(1)
