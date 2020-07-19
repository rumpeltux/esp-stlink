This directory contains a few python tools to interact with the SWIM interface using espstlink.

The `espstlink` directory contains the SWIM interface and python bindings for `../lib/libespstlink.c`.

To use it run `make -C ../lib` first.

# Tools

* `./dump.py > firmware.bin` dumps flash contents of an STM8 device
* `./factory_reset.py` disables ROP and restores option bytes
* `./flash.py -i firmware.ihx` flashes the ihx file (replacement for stm8flash)
* `./readout_protection.py` enables/disables ROP
* `./reset.py` resets the STM8 device and unstalls the CPU
