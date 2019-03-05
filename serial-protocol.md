# Serial protocol used by ESP-STLINK

## Request

A command consists of at least one byte command code, optionally followed
by command-specific further data. The `Len` is just listed for completeness
and is not sent over the wire:

| Command     | Len | CMD |       |            |           |      |       |
|-------------|-----|-----|-------|------------|-----------|------|-------|
| Soft Reset  | 1   | 0   |       |            |           |      |       |
| Read        | 5   | 1   | count | addr >> 16 | addr >> 8 | addr |       |
| Write       | 5+x | 2   | count | addr >> 16 | addr >> 8 | addr | data… |
| Reset       | 2   | FD  | on\*  |            |           |      |       |
| Swim Entry  | 1   | FE  |       |            |           |      |       |
| Get Version | 1   | FF  |       |            |           |      |       |

* The `reset` command toggles the GPIO Pin 5 (D1 on NodeMCU).
  `on` can take these values:
  * `0`: pin is pulled high (no reset)
  * `1`: pin is pulled low (RESET)
  * `0xFF`: pin is a pull-up input (default)

## Response

* Upon reception of a command (including all arguments), the device sends
  the command code back as an ack.
* Upon completion, an error indicator byte is sent, which is either 0 (no
  error) or 0xFF (error).
* In the error case a 16-bit error code is added.

|              |     |    |           |      |
|--------------|-----|----|-----------|------|
| Success Case | CMD | 00 | …         |      |
| Error Case   | CMD | FF | code >> 8 | code |

Here are the specific success case responses for each command:

| Command     | Len | CMD | Success |              |            |           |      |       |
|-------------|-----|-----|---------|--------------|------------|-----------|------|-------|
| Soft Reset  | 2   | 0   | 0       |              |            |           |      |       |
| Read        | 6+x | 1   | 0       | count        | addr >> 16 | addr >> 8 | addr | data… |
| Write       | 6   | 2   | 0       | count        | addr >> 16 | addr >> 8 | addr |       |
| Reset       | 2   | FD  | 0       |              |            |           |      |       |
| Swim Entry  | 4   | FE  | 0       | cycles >> 8  | cycles     |           |      |       |
| Get Version | 4   | FF  | 0       | version >> 8 | version    |           |      |       |

* Swim Entry returns the number of cycles the sync sequence took.
  It should be 16μs, i.e. 0x500 @80MHz. The value may differ a bit due to
  measuring inaccuracies.



