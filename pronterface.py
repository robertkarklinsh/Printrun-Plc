#!/usr/bin/env python

# This file is part of the Printrun-Plc suite.
#
# Printrun-Plc is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun-Plc is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun-Plc.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import getopt

try:
    import wx  # NOQA
except:
    print("wxPython is not installed. This program requires wxPython to run.")
    if sys.version_info.major >= 3:
        print("""\
As you are currently running python3, this is most likely because wxPython is
not yet available for python3. You should try running with python2 instead.""")
        sys.exit(-1)
    else:
        raise

from printrun.pronterface import PronterApp

if __name__ == '__main__':

    from printrun.printcore import __version__ as printcore_version

    os.environ['GDK_BACKEND'] = 'x11'

    usage = "Usage:\n"+\
            "  pronterface [OPTIONS] [FILE]\n\n"+\
            "Options:\n"+\
            "  -h, --help\t\t\tPrint this help message and exit\n"+\
            "  -V, --version\t\t\tPrint program's version number and exit\n"+\
            "  -v, --verbose\t\t\tIncrease verbosity\n"+\
            "  -a, --autoconnect\t\tAutomatically try to connect to printer on startup\n"+\
            "  -c, --conf, --config=CONFIG_FILE\tLoad this file on startup instead of .pronsolerc; you may chain config files, if so settings auto-save will use the last specified file\n"+\
            "  -e, --execute=COMMAND\t\tExecutes command after configuration/.pronsolerc is loaded; macros/settings from these commands are not autosaved"

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hVvac:e:", ["help", "version", "verbose", "autoconnect", "conf=", "config=", "execute="])
    except getopt.GetoptError, err:
        print str(err)
        print usage
        sys.exit(2)
    for o, a in opts:
        if o in ('-V','--version'):
            print "printrun "+printcore_version
            sys.exit(0)
        elif o in ('-h', '--help'):
            print usage
            sys.exit(0)

    app = PronterApp(False)
    try:
        app.MainLoop()
    except KeyboardInterrupt:
        pass
    del app
