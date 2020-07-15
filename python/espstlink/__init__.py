from ctypes import *
import time
import os

for location in [
  os.path.join(os.path.dirname(__file__), "..", "..", "lib", "libespstlink.so"),
  os.path.join(os.path.dirname(__file__), "libespstlink.so"),
  "libespstlink.so"]:
  try:
    stlink = cdll.LoadLibrary(location)
  except:
    pass

if stlink is None:
  raise RuntimeError("libespstlink.so could not be found. Was it compiled in espstlink_base/lib/?")

stlink.espstlink_open.argtypes = [c_char_p]
stlink.espstlink_open.restype = c_void_p

stlink.espstlink_swim_entry.argtypes = [c_void_p]
stlink.espstlink_swim_srst.argtypes = [c_void_p]
stlink.espstlink_reset.argtypes = [c_void_p, c_bool, c_bool]
stlink.espstlink_close.argtypes = [c_void_p]
stlink.espstlink_swim_read.argtypes = [c_void_p, c_char_p, c_uint, c_uint]
stlink.espstlink_swim_write.argtypes = [c_void_p, c_char_p, c_uint, c_uint]
stlink.espstlink_fetch_version.argtypes = [c_void_p]

class _STLinkError(Structure):
    _fields_ = [("code", c_int),
                ("message", c_char_p),
                ("data", c_ubyte * 256),
                ("data_len", c_size_t),
                ("device_code", c_int)]

stlink.espstlink_get_last_error.restype = POINTER(_STLinkError)

class STLinkException(Exception):
  def __init__(self):
    error = stlink.espstlink_get_last_error().contents
    self.code = error.code
    self.data = bytearray(error.data[:error.data_len])
    self.device_code = error.device_code
    super().__init__('Device Error ({code}): {message} (data={data})'.format(
      code = self.code, message=error.message, data=self.data))

class STLink(object):
  def __init__(self, tty: bytes=b"/dev/ttyUSB0"):
    self.pgm = stlink.espstlink_open(tty)
    if not self.pgm:
        raise STLinkException()
    if not stlink.espstlink_fetch_version(self.pgm):
        raise STLinkException()

  def init(self, swim_entry=True, reset=True):
    """
    Starts a swim session.
    
    If reset=True the chip will be put into reset for this.
    """
    if reset:
      self.reset(1)
    if swim_entry:
      self.swim_entry()
    self.write(0x7f80, 0xA0)
    if reset:
      self.reset(0)
    time.sleep(0.001)

  def swim_entry(self):
    """Starts a swim session (without reset)."""
    if not stlink.espstlink_swim_entry(self.pgm):
      raise STLinkException()

  def reset(self, value, input=False):
    """
    Performs a hardware reset of the STM8 device.
    
    If input is True, the reset line will be configured as input.
    """
    if not stlink.espstlink_reset(self.pgm, input, value):
      raise STLinkException()

  def __del__(self):
    if self.pgm:
      stlink.espstlink_close(self.pgm)

  def soft_reset(self):
    """Performs a software reset of the STM8 device."""
    if not stlink.espstlink_swim_srst(self.pgm):
      raise STLinkException()

  def read(self, address: int) -> int:
    """Reads one byte at address"""
    return self.read_bytes(address, 1)[0]

  def read_bytes(self, address: int, length: int) -> bytes:
    """Reads up to 255 bytes starting from address."""
    assert length < 255
    result = create_string_buffer(length)
    if not stlink.espstlink_swim_read(self.pgm, result, address, length):
        raise STLinkException()
    return bytearray(result)

  def read_w(self, address: int, size: int) -> int:
    """Reads a multibyte integer starting from address."""
    value = 0
    for i in self.read_bytes(address, size):
      value = value << 8 | i
    return value


  def write_bytes(self, address: int, buf: bytes) -> bool:
    """Writes up to 255 bytes starting from address."""
    assert len(buf) < 255
    if not stlink.espstlink_swim_write(self.pgm, create_string_buffer(bytes(buf)), address, len(buf)):
        raise STLinkException()
    return True

  def write(self, address: int, value: int) -> bool:
    """Writes a single byte to address."""
    return self.write_bytes(address, bytearray([value]))

  def write_w(self, address: int, size: int, value: int) -> bool:
    """Writes a multibyte integer starting to address."""
    out = bytearray(size)
    for i in range(size):
      out[i] = value & 0xff
      value >>= 8
    return self.write_bytes(address, out)

#  def get_cycles(self, address):
#    """Returns the number of CPU cycles needed to access a given address."""
#    if address < 0x4000: return 8
#    if address < 0x4880: return 9
#    if address < 0x6000: return 8
#    if address < 0x6800: return 9
#    if address < 0x7F80: return 8
#    if address < 0x8000:
#      if address == 0x7f80: return 0
#      if address < 0x7FC0: return 7
#      return 8
#    if address < 0xA000: return 9
#    return 8
