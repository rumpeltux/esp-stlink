#!/usr/bin/env python3
# Resets the STM8 device and unstalls the CPU.

import espstlink
from espstlink.debugger import Debugger
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", default='/dev/ttyUSB0',
                    help="The serial device the HC is connected to")
args = parser.parse_args()

dev = espstlink.STLink(args.device.encode())
dev.init()
deb = debugger.Debugger(dev)
deb.cont()
