import time
import os.path
import sys
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname( __file__),os.path.pardir)))

from plc import *
from plc_handler import PlcHandler

RASP_DEFAULT_PORT = '8080'

msg_handlers = {
    'poweron':PWR_UP,
    'poweroff':PWR_DOWN,
    'suspend':SUSPEND,
    'continue':CONTINUE,
    'stop':STOP,
    'enable':ENABLE,
    'hardreset':HARDRESET
}


def main():

    parser = argparse.ArgumentParser(description='Simple console client to send commands to plc through raspberry')
    parser.add_argument('--hostname', default='10.0.0.31', dest='hostname', help="IP socket hostname of raspberry ")
    parser.add_argument('--local', action='store_true')
    args = parser.parse_args()

    plc = PlcHandler() if args.local else PlcHandler(local=False, printer_port=args.hostname + ':' + RASP_DEFAULT_PORT)

    try:
        # stop = plc.stopped
        pipe = plc.subscribe()
        plc.start()
        time.sleep(1)


        while True:
            user_input = str(raw_input("Enter your command: "))
            command = msg_handlers[user_input] + REQ
            if plc.connected.is_set():
                pipe.send(command)
            else:
                print ("Plc disconnected, exiting...")
                return 1

    except KeyError as e:
        print("The entered command is invalid, try again")
    except KeyboardInterrupt as e:
        print("Goodbye")
        plc.stopped.set()
        plc.join()
        return 0
    except Exception as e:
        plc.stopped.set()
        plc.join()
        return 1

if __name__ == '__main__':
    main()


