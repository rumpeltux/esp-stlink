#!/usr/bin/env python3
# Finishes a factory reset, by restoring correct default option bytes.
import espstlink
from espstlink.flash import Options

dev = espstlink.STLink()
dev.init()
Options(dev).unlock()
dev.write_bytes(0x4800, bytearray([0, 0, 0xff, 0, 0xff, 0, 0xff, 0, 0xff, 0, 0xff]))
dev.soft_reset()
