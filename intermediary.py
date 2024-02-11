#!/bin/python
import subprocess
import base64
import sys

data = sys.argv[1]

try:
    subprocess.check_call(["sudo", "python", "writer.py", data])
except subprocess.CalledProcessError:
    exit(1)
