from . import register

class FlashRegister(register.Register):
  def __init__(self, flash, *args, **kwargs):
    self.flash = flash
    super().__init__(*args, **kwargs)

  def __setitem__(self, name, value):
    super().__setitem__(name, value)
    self.flash.wait_till_ready()

class Options(register.Collection):
  def __init__(self, stlink):
    self.stlink = stlink
    self.flash = Flash(stlink)
    self.add_register( 'ROP', 0x4800)
    self.add_register( 'UBC', 0x4801)
    self.add_register('NUBC', 0x4802)
    self.add_register( 'OPT4', 0x4807, {'EXTCLK': 3})
    self.add_register('NOPT4', 0x4808, {'EXTCLK': 3})

  def add_register(self, name, offset, bits={}):
    self[name] = FlashRegister(self.flash, self.stlink, name, offset, bits)

  def enable_rop(self, enable=True):
    self['ROP'].value = 0xAA if enable else 0

  def unlock(self):
    self.flash.unlock_option_bytes()
    self.flash.unlock()

class Flash(register.Collection):
  def __init__(self, stlink):
    self.stlink = stlink
    self.add_register('FLASH_PUKR', 0x5062)
    self.add_register('FLASH_DUKR', 0x5064)
    self.add_register('FLASH_FPR', 0x505D)
    self.add_register('FLASH_NFPR', 0x505D)
    self.add_register('FLASH_IAPSR', 0x505F, {'HVOFF': 6, 'DUL': 3, 'EOP': 2, 'PUL': 1, 'WR_PG_DIS': 0})
    self.add_register('FLASH_CR1', 0x505A)
    self.add_register('FLASH_CR2', 0x505B, {'OPT': 7, 'PRG': 0})
    self.add_register('FLASH_NCR2', 0x505C, {'OPT': 7, 'PRG': 0})

  def unlock_option_bytes(self):
    self['FLASH_CR2']['OPT'] = 1
    self['FLASH_NCR2']['OPT'] = 0

  def unlock_data(self):
    """unlocks the data area (eeprom, option bytes)"""
    self['FLASH_DUKR'].value = 0xAE
    self['FLASH_DUKR'].value = 0x56
    assert self['FLASH_IAPSR']['DUL'], 'not unlocked'

  def unlock_prog(self):
    """unlocks the main program area"""
    self['FLASH_PUKR'].value = 0x56
    self['FLASH_PUKR'].value = 0xAE
    assert self['FLASH_IAPSR']['PUL'], 'not unlocked'

  def lock(self):
    self['FLASH_IAPSR']['DUL'] = 0

  def wait_till_ready(self):
    while self['FLASH_IAPSR']['EOP']: pass
  
  def write(self, addr: int, block: bytes):
    assert (addr & 0x3f) == 0, "addr must be on a 64 byte boundary"
    assert len(block) == 64, "block must be exactly 64 bytes long"
    
    # we do this manually for speed
    vals = self.stlink.read_bytes(self['FLASH_CR2'].offset, 2)
    assert (vals[0] & 1) == 0, "FLASH_CR2.PRG bit is still set"
    assert (vals[1] & 1) == 1, "FLASH_NCR2.PRG bit is still unset"
    vals[0] |= 1
    vals[1] -= 1
    self.stlink.write_bytes(self['FLASH_CR2'].offset, vals)
    self.stlink.write_bytes(addr, block)
    for i in range(320): # busy wait until programming finished
      if self['FLASH_IAPSR']['EOP']: return
    assert self['FLASH_IAPSR']['WR_PG_DIS'] == 0, "flash failed, page is write-protected"
    raise RuntimeError('Flash %s @%04x failed.' % (block, addr))
