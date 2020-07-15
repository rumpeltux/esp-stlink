from . import register


class Port(RegisterCollection):
  def __init__(self, stlink, offset):
    self.stlink = stlink
    self.add_register('ODR', offset+0)
    self.add_register('IDR', offset+1)
    self.add_register('DDR', offset+2)
    self.add_register('CR1', offset+3)
    self.add_register('CR2', offset+4)

  def set_output(self, index, push_pull=True, open_drain=False, fast_switching=True):
    assert push_pull != open_drain
    self['DDR'][index] = 1
    self['CR1'][index] = push_pull 
    self['CR2'][index] = fast_switching

  def set_input(self, index, pull_up=True, interrupts=False):
    self['DDR'][index] = 0
    self['CR1'][index] = pull_up
    self['CR2'][index] = interrupts

  def set(self, index, value):
    self['ODR'][index] = value

  def get(self, index):
    return self['IDR'][index]
