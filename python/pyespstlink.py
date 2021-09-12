"""
Very basic pure python implementation of the esp-stlink serial protocol.

For reference only; not currently maintained!
Prefer using the libespstlink library that is guaranteed to be in sync with
the firmware implementation and provides better error handling.
"""
import serial

class Command:
    RESET = 0
    READ = 1
    WRITE = 2

class EspStlink(object):
    def __init__(self, tty):
        self.pgm = serial.Serial(tty, 115200, timeout=.1)

    def reset(self):
        cmd = bytearray([Command.RESET])
        
    def read(self, addr, length):
        cmd = bytearray([Command.READ, length, addr >> 16, (addr >> 8) & 0xff, addr & 0xff])
        self.pgm.write(cmd)
        response = bytearray(self.pgm.read(6 + length))
        self.check_success(cmd[0], response)
        assert cmd[1:4] == response[2:5], (cmd, response)
        assert len(response) == 6 + length, (cmd, response)
        return response[6:]

    def write(self, addr, data):
        cmd = bytearray([Command.WRITE, len(data), addr >> 16, (addr >> 8) & 0xff, addr & 0xff])
        self.pgm.write(cmd + data)
        response = bytearray(self.pgm.read(6))
        self.check_success(cmd[0], response)
        assert cmd[1:4] == response[2:5], (cmd, response)
    
    def check_success(self, cmd, response):
        if len(response) >= 2 and response[1] == 0: return True
        if len(response) < 4 or response[1] != 0xff:
            raise RuntimeError('SWIM communation error (read {})'.format(response))
        if response[0] != cmd:
            raise RuntimeError('SWIM communication error (expected command {expected} but got {actual}, read {response})'.format(
                expected=cmd, actual=response[0], response=response))
        raise RuntimeError('SWIM command {cmd} failed with code {code:x}'.format(cmd=cmd, code=(response[1]<<8 | response[0])))
