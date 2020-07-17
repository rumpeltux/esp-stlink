#!/usr/bin/env python3
import collections

Record = collections.namedtuple('Record', 'addr type data')

Type_EOF = 1

def load(filename: str):
  """Load an Intel IHX file, yielding Record objects"""
  for line in open(filename):
    assert line[0] == ':'
    data = bytes.fromhex(line[1:])
    r = Record(addr=data[1] << 8 | data[2], type=data[3], data=data[4:-1])
    assert len(r.data) == data[0], "len mismatch"
    yield r

def load_merged(filename: str):
  """Sorts records and merges adjacent sections."""
  records = []
  for record in load(filename):
    if record.type == Type_EOF: break
    assert record.type == 0, "invalid record type %s" % repr(record)
    records.append(record)
  records.sort(key=lambda r: r.addr)
  merged = []
  addr, data = 0, b''
  for i in range(len(records)):
    if addr + len(data) == records[i].addr:
      data += records[i].data
    else:
      if data:
        yield Record(addr=addr, data=data, type=None)
      addr, data = records[i].addr, records[i].data
  if data:
    yield Record(addr=addr, data=data, type=None)

if __name__ == '__main__':
  import sys

  for filename in sys.argv[1:]:
    for record in load_merged(filename):
      print('%s:\t%04x [%d]\t' % (filename, record.addr, len(record.data)), record)
    
