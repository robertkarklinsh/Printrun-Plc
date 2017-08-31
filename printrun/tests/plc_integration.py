import sys

import printrun.plc_core as plc_core

CONTROLLINO_PORT = '/dev/ttyACM2'
CONTROLLINO_BAUD = 57600

if __name__ == '__main__':
    plc_connection = plc_core.PlcConnection(baud=CONTROLLINO_BAUD, port=CONTROLLINO_PORT)
    plc_connection.open()
    while True:
        try:
            msg = raw_input('Type message to send\n')
            if msg == 'exit':
                plc_connection.close()
                sys.exit()
            else:
                plc_connection.send(msg + '\n')

        except EOFError as e:
            plc_connection.close()
            sys.exit()
