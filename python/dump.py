#!/usr/bin/env python3
import espstlink
import sys

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("-d", "--device", default='/dev/ttyUSB0',
                    help="The serial device the HC is connected to")
  args = parser.parse_args()
  dev = espstlink.STLink(args.device.encode())
  dev.init()
  for addr in range(0x8000, 0xa000, 0x80):
    chunk = dev.read_bytes(addr, 0x80)
    #sys.stdout.buffer.write(chunk)
