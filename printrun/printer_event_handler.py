from event_handler import EventHandler


class PrinterEventHandler(EventHandler):
    '''
    Defines a skeletton of an event-handler for printer events. It
    allows attaching to the printcore and will be triggered for
    different events.
    '''

    def on_send(self, command, gline):
        '''
        Called on every command sent to the printer.

        @param command: The command to be sent.
        @param gline: The parsed high-level command.
        '''
        pass

    def on_recv(self, line):
        '''
        Called on every line read from the printer.

        @param line: The data has been read from printer.
        '''
        pass

    def on_online(self):
        '''
        Called when printer got online.
        '''
        pass

    def on_temp(self, line):
        '''
        Called for temp, status, whatever.

        @param line: Line of data.
        '''
        pass

    def on_layerchange(self, layer):
        '''
        Called on layer changed.

        @param layer: The new layer.
        '''
        pass

    def on_preprintsend(self, gline, index, mainqueue):
        '''
        Called pre sending printing command.

        @param gline: Line to be send.
        @param index: Index in the mainqueue.
        @param mainqueue: The main queue of commands.
        '''
        pass

    def on_printsend(self, gline):
        '''
        Called whenever a line is sent to the printer.

        @param gline: The line send to the printer.
        '''
        pass
