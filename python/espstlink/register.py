class Bit(object):
  def __init__(self, start=0, mask=1, register=None):
    self.register = register
    self.start = start
    self.mask = mask << start
  
  def set_register(self, register):
    assert self.register is None
    self.register = register
    return self
  
  def set(self, value):
    self.register.value = (self.register.value & ~self.mask) | ((value << self.start) & self.mask)
  
  def get(self):
    return (self.register.value & self.mask) >> self.start
  
  def __repr__(self):
    return '{name}:{mask}={value}'.format(name=self.register.name, mask=self.mask, value=self.get())


class WRegister(object):
  """A register consisting of multiple bytes."""
  def __init__(self, stlink, name, offset, size=2):
    self.stlink = stlink
    self.name = name
    self.offset = offset
    self.size = size
  
  @property
  def value(self):
    return self.stlink.read_w(self.offset, self.size)
  
  @value.setter
  def value(self, value):
    return self.stlink.write_w(self.offset, self.size, value)


class Register(object):
  def __init__(self, stlink, name, offset, bits={}):
    self.stlink = stlink
    self.name = name
    self.offset = offset
    self.bits = {}
    self.add_bits(bits)
    
  def add_bit(self, name, start, mask=1):
    self.bits[name] = Bit(start=start, mask=mask, register=self)

  def add_bits(self, bits):
    for name, start in bits.items():
      mask = 1
      if isinstance(start, tuple):
        start, mask = start
      self.add_bit(name, start, mask)

  def __getitem__(self, name):
    if type(name) == int and 0 <= name <= 7:
      return (self.value >> name) & 1
    return self.bits[name].get()
  
  def __setitem__(self, name, value):
    if type(name) == int and 0 <= name <= 7:
      Bit(name, register=self).set(value)
    else:
      self.bits[name].set(value)
  
  @property
  def value(self):
    return self.stlink.read(self.offset)

  @value.setter
  def value(self, value):
    return self.stlink.write(self.offset, value)
  
  def status(self):
    result = ['{} (*{:x}={:02x})'.format(self.name, self.offset, self.value)]
    for k, v in sorted(self.bits.items(), key=lambda x: x[1].start):
      result.append('  {}={}'.format(k, v.get()))
    return '\n'.join(result)


class Collection(dict):
  def __init__(self, stlink):
    self.stlink = stlink

  def add_register(self, name, offset, bits={}):
    self[name] = Register(self.stlink, name, offset, bits)
  
  def add_wregister(self, name, offset, size):
    self[name] = WRegister(self.stlink, name, offset, size)
