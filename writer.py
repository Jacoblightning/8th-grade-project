#!/bin/python
import sys
import base64
import os

data = base64.b64decode(sys.argv[1])

if not os.path.exists("/dev/usb/lp0"):
    exit(1)

with open("/dev/usb/lp0", "wb") as printer:
    printer.write(data)

exit(0)
# Final check (too complicated so skipped)
with open("/dev/usb/lp0") as nothing:
    if printer.read(len(data)) == data:
        exit(1)
