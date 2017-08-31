import logging

from event_handler import EventHandler


class PlcEventHandler(EventHandler):
    '''
    Defines behavior logic for hal when he communicates with plc
    '''

    def on_send(self, msg):
        pass

    def on_recv(self, msg):
        logging.log(4, msg)

    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    def on_error(self, error):
        pass
