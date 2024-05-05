#!/usr/bin/env python3
# Turns readout protection on / off

import espstlink
import time
from espstlink.flash import Options

class ReadoutProtection(object):
    def __init__(self, dev=None):
        dev = dev or espstlink.STLink()
        dev.init(reset=True)
        self.dev = dev
        self.options = Options(dev)

    def set(self, enable):
        self.options.unlock()
        print('Enabling' if enable else 'Disabling')
        self.options.enable_rop(enable)
        print('New ROP', self.options['ROP'].status())
        self.dev.reset(1)
        self.dev.reset(0, input=True)
        time.sleep(0.01)
        print('After reset: ROP', self.options['ROP'].status())

if __name__ == '__main__':
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--device", default='/dev/ttyUSB0',
                        help="The serial device the HC is connected to")
    parser.add_argument("enable_rop", type=int, choices=[0, 1],
                        help="Whether to enable ROP (1) or not (0)", nargs='?')
    args = parser.parse_args()

    r = ReadoutProtection()
    print('Current ROP', r.options['ROP'].status())
    if args.enable_rop is not None:
      r.set(args.enable_rop)
