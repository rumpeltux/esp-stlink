#!/usr/bin/env python3
import espstlink
import sys
from espstlink.debugger import Debugger, CPU
import string

class BufferedStlink(espstlink.STLink):
  def __init__(self, stlink):
    self.stlink = stlink
    self.buf = {}
    self.pgm = None

  def buffer(self, addr, size):
    self.buf[addr] = self.stlink.read_bytes(addr, size)

  def read_bytes(self, addr, size):
    for k, v in self.buf.items():
      if addr >= k and addr <= k + len(v):
        return v[addr - k:addr - k + size]
    #print(addr, size, 'not found')
    #print(self.buf)
    

def h(val, size):
  """static-sized hex"""
  return hex(val | (1 << (size * 8)))[3:]

printable = ''.join(set(string.printable) - set(string.whitespace))

def reg(s, name, size):
  """string representation of a register"""
  return f"{name}={h(s[name], size)} {s[name]} {chr(s[name]) if chr(s[name]) in printable else '.'}"

class CpuState(dict):
  def __init__(self, cpu):
    super(CpuState, self).__init__()
    data = cpu.stlink.buffer(0x7F00, 11)
    for k in ['PC', 'X', 'Y', 'A', 'SP', 'CC']:
      self[k] = cpu[k].value
    self['stack'] = cpu.stlink.stlink.read_bytes(self['SP'], 8)

  def __str__(self):
    s = self
    return f"{h(s['PC'], 3)}: {reg(s, 'X', 2)} {reg(s, 'Y', 2)} {reg(s, 'A', 2)} SP={h(s['SP'], 2)} CC={bin(s['CC'])[2:]}"

def trace(dev):
  deb = Debugger(dev)
  buf = BufferedStlink(dev)
  cpu = CPU(buf)
  
  while True:
    s = CpuState(cpu)
    print(str(s))
    deb.step()

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("-d", "--device", default='/dev/ttyUSB0',
                    help="The serial device the HC is connected to")
  args = parser.parse_args()
  dev = espstlink.STLink(args.device.encode())
  dev.init(reset=False)
  trace(dev)
