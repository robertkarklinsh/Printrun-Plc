#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

class EventHandler(object):
    '''
    Abstract event handler
    '''

    def __init__(self):
        pass

    def on_init(self):
        pass

    def on_send(self, msg):
        pass

    def on_recv(self, msg):
        pass

    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    def on_error(self, error):
        pass
