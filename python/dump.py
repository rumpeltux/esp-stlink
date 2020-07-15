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
  import time
  start = time.time()
  for i in range(10):
    dev.read(0x505F)
  print(time.time() - start)
  for addr in range(0x7F80, 0xa000, 0x80):
    pass#sys.stdout.buffer.write(dev.read_bytes(addr, 0x80))
