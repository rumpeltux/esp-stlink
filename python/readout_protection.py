#!/usr/bin/env python3
# Turns readout protection on / off

import espstlink
from espstlink.flash import Options

class ReadoutProtection(object):
    def __init__(self, dev=None):
        dev = dev or espstlink.STLink()
        dev.init(reset=False)
        self.dev = dev
        self.options = Options(dev)

    def set(self, enable):
        self.options.unlock()
        self.options.enable_rop(enable)
        print('ROP', self.options['ROP'].status())
        self.dev.reset(1)
        time.sleep(0.001)
        self.dev.reset(0, input=True)
        print('ROP', self.options['ROP'].status())

if __name__ == '__main__':
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--device", default='/dev/ttyUSB0',
                        help="The serial device the HC is connected to")
    parser.add_argument("enable_rop", type=bool,
                        help="Whether to enable ROP or not", nargs='?')
    args = parser.parse_args()

    r = ReadoutProtection()
    print('ROP', r.options['ROP'].status())
    if args.rop is not None:
      r.set(args.enable_rop)
