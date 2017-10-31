Link to original project: https://github.com/kliment/Printrun
## About
Fork of Pronterface which makes possible to use PLC together with 3d printing controller as a low cost alternative to CNC. The primary goal was to provide CNC level scalability and reliability with no need to pay price for closed-ecosystem industrial controllers which use tedious legacy tools e.g. ladder logic.

Instead of command-by-command printing over serial TCP/IP is used as communication mechanism of choice. This unlocks true network printing capabilities when main server can stream gcode and control state of several remote printers.

Basic setup consists of:
 1. Server running host program
 2. Ethernet-capable 3d printing contoller (e.g. Smoothieboard)
 3. Ethernet-capable PLC (e.g. Controllino)

For PLC's with no ethernet port it is possible to use raspberry as tcp-serial adapter.
