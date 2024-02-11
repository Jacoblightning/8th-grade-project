import os
import subprocess
import base64


def isPrinterConnected():
    return os.path.exists("/dev/usb/lp0")


def printIfConnected(commands: bytes):
    if isPrinterConnected():  # Sanity check
        sendCommand(commands)
    else:
        raise FileNotFoundError("Printer Not Found")


def _protectedSend(command: bytes):
    try:
        subprocess.check_call(["./intermediary.py", base64.b64encode(command)])
    except subprocess.CalledProcessError as e:
        raise IOError(e)


def sendCommand(command: bytes):
    _protectedSend(command)


def binComm(bina):
    return chr(bina).encode("ascii")
