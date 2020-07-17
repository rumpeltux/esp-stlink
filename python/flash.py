#!/usr/bin/env python3
import espstlink
from espstlink.flash import Flash
from espstlink.debugger import Debugger
import ihx

class Flasher(object):
  def __init__(self, tty):
    self.dev = espstlink.STLink(tty.encode())
    self.dev.init()
    self.flash = Flash(self.dev)
    self.flash.unlock_prog()

  def write_segment(self, addr: int, data: bytes):
    """Writes a continuous segment of data to a destination address."""
    # fill in incomplete blocks if necessary
    missing = addr & 0x3F
    if missing != 0:
      addr -= missing
      data = self.dev.read_bytes(addr, missing) + data
    missing = len(data) & 0x3F
    if missing != 0:
      data += self.dev.read_bytes(addr + len(data), 0x40 - missing)

    for offset in range(0, len(data), 0x40):
      print('.', end='', flush=True)
      self.flash.write(addr + offset, data[offset:offset + 0x40])

  def write_ihx(self, ihx_filename: str):
    """Reads records from an ihx file and writes them to a target device."""
    for record in ihx.load_merged(ihx_filename):
      print('%04x:%04x\t%d blocks (%d bytes) ' % (record.addr, record.addr + len(record.data), len(record.data) / 0x40, len(record.data)), end='')
      self.write_segment(record.addr, record.data)
      print()

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("-d", "--device", default='/dev/ttyUSB0',
                    help="The serial device the HC is connected to")
  parser.add_argument("-s", "--stall", action='store_true',
                    help="Keep the CPU stalled after flashing")
  parser.add_argument("-i", "--ihx", help="The ihx output from sdcc for flashing")
  parser.add_argument("-b", "--bin", help="A binary file for flashing")
  parser.add_argument("--addr", type=lambda x: int(x,0), help="The destination address (requires --bin)")
  args = parser.parse_args()
  
  if args.addr is not None:
    assert args.bin, '--bin flag required for use with --addr'

  f = Flasher(args.device)

  if args.bin is not None:
    assert args.ihx is None, '--ihx flag cannot be used together with --bin'
    f.write_segment(args.addr, open(args.bin, 'rb').read())
  elif args.ihx is not None:
    f.write_ihx(args.ihx)
  else:
    raise RuntimeError("No --ihx nor --bin file specified for flashing.")

  if not args.stall:
    Debugger(f.dev).cont()
