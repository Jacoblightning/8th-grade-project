#!/usr/bin/env python3

import os
import datetime, time
import sys

import driver
from driver import printIfConnected

LF = b"\x0A"
CF = "\n".encode("ascii")
INITALIZE = b"\x1B\x40"
SET_SIZE = b"\x1d\x21"


# Function to get the current date in mm/dd/yyyy format
def get_date():
    return datetime.datetime.now().strftime("%m/%d/%Y")


# Function to get the current time
def get_time():
    """Gets the current time in a human-readable format"""
    return datetime.datetime.now().strftime("%I:%M %p")


def simplePrint(text):
    finaltext = text.encode("ascii").replace(CF, LF)
    # Command Reference: https://reference.epson-biz.com/modules/ref_escpos/index.php?content_id=72#commands
    # Backup: http://web.archive.org/web/20240208194111/https://reference.epson-biz.com/modules/popup/index.php/termsofuse_reference/index.php?m=ref_escpos&cid=72&PHPSESSID=be1f982d549616f05fa773f11fe980ab#commands
    # ESC/POS commands for initializing printer, centering text, and cutting paper
    esc_pos_commands = (
        finaltext
        + b"\x0A"  # Formatted text and line feed
        + (LF * 10)  # Space to make it easy to tear
        + b"\x1B\x64\x02"  # Cut paper (partial cut)
    )
    # Send ESC/POS commands directly to /dev/lp0 (thermal printer)
    printIfConnected(esc_pos_commands)


def printlate(name):
    # Formatted text to be printed
    formatted_text = f"LATE SLIP\nName: {name}\nTime: {get_time()}\nDate: {get_date()}"
    simplePrint(formatted_text)


def printvisitor(name):
    # Formatted text to be printed
    formatted_text = f"VISITOR:\nName: {name}\nTime: {get_time()}\nDate: {get_date()}"
    simplePrint(formatted_text)
