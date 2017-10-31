from mock import Mock
from threading import Thread
from printrun.plc.plc_handler import *
from printrun.plc.plc_forwarder import *

if __name__ == '__main__':

    test_msg = PWR_UP

    plc_forwarder = PlcForwarder()
    plc_forwarder.serial_conn = PlcConnection()
    plc_forwarder.serial_conn.send = Mock()
    plc_handler = PlcHandler()
    try:
        thread = Thread(target=plc_forwarder.open_tcp_connection)
        thread.start()
        time.sleep(1)
        plc_handler.start()
        if thread is not None:
            thread.join()
        thread = Thread(target=plc_forwarder.start)
        thread.start()
        pipe = plc_handler.subscribe()
        pipe.send(PWR_UP + REQ)
        time.sleep(1)
        plc_handler.stopped.set()
        plc_handler.join()
        plc_forwarder.exit()
        if thread is not None:
            thread.join()
        plc_forwarder.serial_conn.send.assert_any_call(test_msg + "\n")
        sys.exit(0)
    except Exception as e:
        logging.error('Error: %s' % e)
        sys.exit(1)
