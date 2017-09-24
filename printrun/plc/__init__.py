# Pronterface <-> PlcHandler <-> Plc communication protocol
ACK = '\x06'
SYN = '\x16'
EOT = '\x04'
E_LIMIT = '\xff'
E_BUTTON = '\xf0'
HALT = "\x21"
REQ = '\x12'
RESP = '\x13'
PWR_UP = '\x14'
PWR_DOWN = '\x15'
SUSPEND = '\x17'
CONTINUE = '\x18'
STOP = '\x19'
ENABLE = '\x20'
LOG = 'l'
ERR = 'e'
ACT = 'a'

DEVICES_DESCRIPTION = {
    'A1': 'Smoothie',
    'A2': 'X/Y axis driver',
    'A3': 'Controllino',
    'A4': 'X/Y axis driver',
    'G1': '24V PSU',
    'G2': 'Z axis 36V PSU',
    'G3': '5V PSU',
    'G4': 'Z axis 36V PSU',
    'G5': 'Z axis 36V PSU',
    'G6': 'Z axis 36V PSU',
    'S7': 'Emergency limit switch',
    'S8': 'Emergency limit switch',
    'S9': 'Emergency limit switch',
    'S10': 'Emergency limit switch',
    'S11': 'Emergency limit switch',
    'S12': 'Emergency limit switch',
    'S13': 'ESTOP button'

}
