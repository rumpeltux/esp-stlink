from . import register

BREAKPOINT_MODES = {name: [int(i) for i in mode.split(' ')] for mode, name in [
  # BC2 BC1 BC0 BIR BIW
  ['0 0 0 0 0', 'Disabled'],
  ['0 0 0 0 1', 'Data Write on @=BK1 and Data=BK2L'],
  ['0 0 0 1 0', 'Data Read on @=BK1 and Data=BK2L'],
  ['0 0 0 1 1', 'Data R/W on @=BK1 and Data=BK2L'],
  ['0 0 1 0 0', 'Instruction fetch BK1<=@<=BK2'],
  ['0 0 1 0 1', 'Data Write on BK1<=@<=BK2'],
  ['0 0 1 1 0', 'Data Read on BK1<=@<=BK2'],
  ['0 0 1 1 1', 'Data R/W on BK1<=@<=BK2'],
  ['0 1 0 0 0', 'Instruction fetch on @<= BK1 or BK2<=@'],
  ['0 1 0 0 1', 'Data Write on @<= BK1 or BK2<=@'],
  ['0 1 0 1 0', 'Data Read on @<= BK1 or BK2<=@'],
  ['0 1 0 1 1', 'Data R/W on @<= BK1 or BK2<=@'],
  ['1 0 0 0 0', 'Instruction fetch on @=BK1 then on @=BK2'],
  ['1 0 0 0 1', 'Data Write on @=BK1 or @=BK2'],
  ['1 0 0 1 0', 'Data Read on @=BK1 or @=BK2'],
  ['1 0 0 1 1', 'Data R/W on @=BK1 or @=BK2'],
  ['1 0 1 0 0', 'Instruction fetch on @=BK1 or @=BK2'],
  ['1 0 1 0 1', 'Instruction fetch on @=BK1 / Data Write on @=BK2'],
  ['1 0 1 1 0', 'Instruction fetch on @=BK1 / Data Read on @=BK2'],
  ['1 0 1 1 1', 'Instruction fetch on @=BK1 / Data R/W on @=BK2'],
  ['1 1 1 0 0', 'Data Write in Stack on @<=BK1 / Instruction fetch on @=BK2'],
  ['1 1 1 0 1', 'Data Write in Stack on @<=BK1 / Data Write on @=BK2'],
  ['1 1 1 1 0', 'Data Write in Stack on @<=BK1 / Data Read on @=BK2'],
  ['1 1 1 1 1', 'Data Write in Stack on @<=BK1 / Data R/W on @=BK2']
]}

class Debugger(object):
  def __init__(self, stlink):
    self.DM_BKR1 = register.WRegister(stlink, 'DM_BKR1', 0x7F90, 3)
    self.DM_BKR2 = register.WRegister(stlink, 'DM_BKR2', 0x7F93, 3)
    self.DM_CR1 = register.Register(stlink, 'DM_CR1', 0x7F96, {'WDGOFF': 7, 'BC': (3, 7), 'BIR': 2, 'BIW': 1, 'BC*': (1, 0x1f)})
    self.DM_CR2 = register.Register(stlink, 'DM_CR2', 0x7F97, {'FV_ROM': 2, 'FV_RAM': 1})
    self.DM_CSR1 = register.Register(stlink, 'DM_CSR1', 0x7F98, {'STE': 6, 'STF': 5, 'RST': 4, 'BRW': 3, 'BK2F': 2, 'BK1F': 1})
    self.DM_CSR2 = register.Register(stlink, 'DM_CSR2', 0x7F99, {'SWBKE': 5, 'SWBKF': 4, 'STALL': 3, 'FLUSH': 0})

  def pause(self):
    self.DM_CSR2['STALL'] = 1
    
  def cont(self):
    self.DM_CSR2['STALL'] = 0
  
  def step(self):
    """Returns true if the device was stopped due to the step instruction."""
    self.DM_CSR1['STE'] = 1
    self.cont()
    while self.DM_CSR2['STALL'] == 0:
      pass
    self.DM_CSR1['STE'] = 0
    return self.DM_CSR1['STF']

  def breakpoint(self, mode_str, bk1=0, bk2=0):
    mode = BREAKPOINT_MODES[mode_str]
    self.DM_CR1['BC*'] = mode[0] << 4 | mode[1] << 3 | mode[2] << 2 | mode[3] << 1 | mode[4]
    self.DM_BKR1.value = bk1
    self.DM_BKR2.value = bk2
    
  def clear_breakpoint(self):
    self.breakpoint('Disabled', 0, 0)


class CPU(register.Collection):
  REGISTERS = {
    'A' 	: 0x7F00,
    'PCE'	: 0x7F01,
    'PCH'	: 0x7F02,
    'PCL'	: 0x7F03,
    'XH'	: 0x7F04,
    'XL'	: 0x7F05,
    'YH'	: 0x7F06,
    'YL'	: 0x7F07,
    'SPH'	: 0x7F08,
    'SPL'	: 0x7F09,
    'CC'	: 0x7F0A
  }
  def __init__(self, stlink):
    self.stlink = stlink
    self.registers = {}
    for k, v in self.REGISTERS.items():
      self.add_register(k, v)
    self.add_wregister('PC', 0x7F01, 3)
    self.add_wregister( 'X', 0x7F04, 2)
    self.add_wregister( 'Y', 0x7F06, 2)
    self.add_wregister('SP', 0x7F08, 2)
    self['CC'].add_bits({'V': 7, 'I1': 5, 'H': 4 , 'I0': 3, 'N': 2, 'Z': 1, 'C': 0})

    self.add_wregister('TIM1_CNTR', 0x525E, 2)
    self.add_register('TIM1_CR1',   0x5250, {'CEN': 0})
    self.add_register('TIM1_SMCR',  0x5252, {'SMS': (0, 7), 'TS': (4, 7), 'MSM': 7})
    self.add_register('TIM1_ETR',   0x5253, {'ETF': (0, 15), 'ETPS': (4, 3), 'ECE': 6, 'ETP': 7})
    self.add_register('CLK_CMSR', 0x50C3)
    self.add_register('CLK_SWR',  0x50C4)
    self.add_register('CLK_SWCR', 0x50C5, {'SWIF': 3, 'SWIEN': 2, 'SWEN': 1, 'SWBSY': 0})
    self.add_register('SWIM_CSR', 0x7F80, {'SAFE_MASK': 7, 'NO_ACCESS': 6, 'SWIM_DM': 5, 'HS': 4, 'OSCOFF': 3, 'RST': 2, 'HSIT': 1, 'PRI': 0})
