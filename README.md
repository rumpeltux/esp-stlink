# STLINK implementation for ESP8266
This ESP8266 firmware implements the SWIM protocol for debug access / flashing
of STM8 devices.

The STM8 SWIM protocol is well documented in [UM0470](http://www.st.com/content/ccc/resource/technical/document/user_manual/ca/89/41/4e/72/31/49/f4/CD00173911.pdf/files/CD00173911.pdf/jcr:content/translations/en.CD00173911.pdf).
Communication runs @8MHz, as such the ESP (running at 80MHz) is well-suited
for bit-banging this protocol and leaves enough computing capacity for
implementing this without paying too much attention to instruction cpu
cycles.

I built this, because I was debugging a chip, clocked by a slow external clock.
Since debug access is based on the cpu’s clock rate, the SWIM module was too
slow to respond for the stlink device I had used before. Taking a look at my
logic analyzer I saw that the microcontroller indeed sent a response, but I
was unable to get it out.
Also I really don't see the point of needing a special one-purpose-only device
to flash the stm8 chips (even though they are cheap).

The timing is based on counting cpu-cycles, as such the code currently only
orks if the ESP is running at 80MHz and not at 160MHz.
Only slow data transfer speed is implemented, but this shouldn’t really matter.
From what my logic analyzer told me the actual stlink device didn’t use
high-speed either.

## Building

1. Install [esp-open-sdk](https://github.com/pfalcon/esp-open-sdk)
1. Compile and flash

```
ESP_OPEN_SDK=/opt/esp-open-sdk
export XTENSA_TOOLS_ROOT=$ESP_OPEN_SDK/xtensa-lx106-elf/bin SDK_BASE=$ESP_OPEN_SDK/sdk flash
make flash
```

## Connecting

* The STM8 device of course needs G and 3.3V connections.
* RST stays unconnected for now (potential future version could introduce a
  RST feature though).
* SWIM is connected to ESP8266 GPIO4 (e.g. D2 on NodeMCU) **via a 1kΩ pull-up
  resistor** (this is important since the builtin pullup resistor is not
  capable of pulling up the line fast enough!).

## Using ESP-STLINK with stm8flash

Grab stm8flash from https://github.com/rumpeltux/stm8flash.

    stm8flash -c espstlink -p stm8s103f3 -w sample.ihx
    
### Compatibility

So far this has only been tested with an stm8s103f3 chip.
It’s likely that other devices work as well, but since there may be issues
regarding timing of the wire protocol, there’s no guarantee that it’ll
work.

## Related software

[stm8spi](http://kuku.eu.org/?projects/stm8spi/stm8spi) is a related
implementation (ab)using the raspberry PI’s SPI to perform SWIM communication.
However, due to relying on SPI and its timing, it's severly limited and
wouldn't work for my use-case either.
