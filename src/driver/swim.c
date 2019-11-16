/**
 * Copyright (C) 2017 Hagen Fritsch
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "swim.h"
#include <driver/uart.h>
#include <espmissingincludes.h>
#include <sys/param.h>
#include <user_interface.h>

#define SWIM BIT4
#define NRST BIT5

#define SET_PIN_HIGH(pin) (GPIO_REG_WRITE(GPIO_OUT_W1TS_ADDRESS, pin))
#define SET_PIN_LOW(pin) (GPIO_REG_WRITE(GPIO_OUT_W1TC_ADDRESS, pin))

#define PIN_AS_OUTPUT(pin)                         \
  {                                                \
    SET_PIN_HIGH(pin);                             \
    GPIO_REG_WRITE(GPIO_ENABLE_W1TS_ADDRESS, pin); \
  }
#define PIN_AS_INPUT(pin)                          \
  {                                                \
    GPIO_REG_WRITE(GPIO_ENABLE_W1TC_ADDRESS, pin); \
    PIN_PULLUP_EN(PERIPHS_IO_MUX_GPIO4_U);         \
  }

#define READ_PIN(pin) (GPIO_REG_READ(GPIO_IN_ADDRESS) & pin)

// SWIM slow format is 8 MHz, 2 cycles high, 20 cycles low (or vice versa)
// Translated to 80 MHz ESP clock (+ some empirical adjustments)
#define SHORT_PERIOD_LENGTH 27
#define SWIM_CLOCK 10
#define BIT_HALF_TIME (9 * SWIM_CLOCK) // We start the read after 9 swim clocks and use this input.
#define BIT_TOTAL_PERIOD_LENGTH (22 * SWIM_CLOCK)

// Read Set Interrupt Level
#define RSIL(r) __asm__ __volatile__("rsil %0,15 ; esync" : "=a"(r))
// Write Register Processor State
#define WSR_PS(w) __asm__ __volatile__("wsr %0,ps ; esync" ::"a"(w) : "memory")
#define MICROS_TO_CYCLES(x) (x * 80)

static uint32_t TIMEOUT = 0x7FF;

/** Disable all interrupts. Used for timing-critical parts. */
static inline uint32_t esp8266_enter_critical() {
  uint32_t state;
  RSIL(state);
  return state;
}

static inline void esp8266_leave_critical(uint32_t state) { WSR_PS(state); }

/** Returns the CPU’s cycle count. */
#define RSR_CCOUNT(r) __asm__ __volatile__("rsr %0,ccount" : "=a"(r))
static inline uint32_t get_ccount(void) {
  uint32_t ccount;
  RSR_CCOUNT(ccount);
  return ccount;
}

/** Waits until the CPU’s cycle count passes a given number. */
static inline void sync_ccount(uint32_t next) {
  // get_ccount() < next
  while ((int32_t) get_ccount() - (int32_t) next < 0)
    ;
}

/**
 * Returns the pin to the HIGH state at the appropriate time.
 * last is the cycle count at the start of the current bit.
 * PIN must be in OUTPUT mode.
 */
static inline void finish_sync(uint32_t last) {
  sync_ccount(last + BIT_TOTAL_PERIOD_LENGTH - SHORT_PERIOD_LENGTH);
  SET_PIN_HIGH(SWIM);
}

/**
 * Writes one bit. PIN must be in OUTPUT mode.
 * If the bit is 0, only writes the falling edge. The rising edge must be
 * written in the next invocation or using finish_sync().
 * * next is the cycle count at which the bit should start.
 * * prev_bit is the previous bit in case we haven't already switched to HIGH
 * * current_bit is the current bit to be written.
 */
static void write_bit_sync(uint32_t next, uint32_t prev_bit,
                           uint32_t current_bit) {
  if (!prev_bit) {
    sync_ccount(next - SHORT_PERIOD_LENGTH);
    SET_PIN_HIGH(SWIM);
  }
  sync_ccount(next);
  SET_PIN_LOW(SWIM);
  if (current_bit) {
    sync_ccount(next + SHORT_PERIOD_LENGTH);
    SET_PIN_HIGH(SWIM);
  }
}

static int read_bit(uint32_t *start);

/**
 * Sends up to 32 bits of data plus a parity bit and waits for an ack.
 * The position mask indicates how many bits to write. E.g. BIT0 writes 1 +
 * parity. BIT8 writes 9 + parity. Return value is that of read_bit() for the
 * ACK/NACK. *pnext is set to the cycles of start of the ACK bit.
 */
static int write_byte(uint32_t *pnext, uint32_t data, uint32_t mask) {
  uint32_t parity = 0;
  uint32_t next = *pnext;
  next += 200;  // Some artificial delay. The target device doesn't mind and
                // this makes it easier to distinguish byte boundaries when
                // debugging in a logic analyzer.
  while (mask) {
    uint32_t bit = data & mask;
    write_bit_sync(next, data & (mask << 1), bit);
    mask >>= 1;
    parity ^= !!bit;
    next += BIT_TOTAL_PERIOD_LENGTH;
  }
  write_bit_sync(next, data & 1, parity);
  finish_sync(next);
  PIN_AS_INPUT(SWIM);
  return read_bit(pnext);
}

/**
 * Reads one bit. PIN must be in INPUT mode.
 * In SWIM protocol a bit starts LOW.
 * a) On invocation, PIN must be HIGH (when starting the read after the previous
 *    bit) or LOW when starting the read after the device already sent LOW.
 * b) *start is set to the time at which we first realized that the bit is LOW
 *    so only shortly after the actual bit start.
 * Before the next read invocation, cycles must be synced to
 *     at least *start + 200 to guarantee (a).
 * Before the next sending, cycles must be synced to at least
 *     *start + BIT_TOTAL_PERIOD_LENGTH.
 * Returns the bit received or -1 if no response was
 * received (in which case *start is not modified).
 */
static int read_bit(uint32_t *start) {
  uint32_t timeout = TIMEOUT;
  while (READ_PIN(SWIM) && --timeout)
    ;
  if (!timeout) return SWIM_ERROR_READ_BIT_TIMEOUT;
  *start = get_ccount();
  sync_ccount(*start + BIT_HALF_TIME);
  return READ_PIN(SWIM);
}

/**
 * Reads one byte from the host and sends an ACK/NACK. PIN must be in INPUT
 * mode.
 * Reads the host-bit (0), 8 data bits and the parity bit.
 * If parity matches, sends an ACK, otherwise a NACK.
 *
 * Returns -1 if the host bit is not 0 or if no bit is received after timeout.
 * Returns -2 if parity doesn’t match.
 */
static int read_byte() {
  uint32_t next;
  int status;
  if ((status = read_bit(&next)) !=
      BIT4)  // the target always starts with a 1 bit
    return status < 0 ? status : SWIM_ERROR_INVALID_TARGET_ID;
  uint32_t result = 0;
  uint32_t parity = 0;
  uint32_t i;
  for (i = 0; i < 9; i++) {
    sync_ccount(next + 18 * SWIM_CLOCK);
    int bit = read_bit(&next);
    if (bit == SWIM_ERROR_READ_BIT_TIMEOUT) {
      // indicate which bit failed (for debugging)
      return -i - 20;
    }
    result = result << 1 | !!bit;
    parity ^= result;
  }
  next += BIT_TOTAL_PERIOD_LENGTH;  // TODO: should substract a few cycles that
                                    // we lost while calculating the value...
  PIN_AS_OUTPUT(SWIM);
  write_bit_sync(next, 0, !(parity & 1));
  finish_sync(next);
  PIN_AS_INPUT(SWIM);
  if (parity & 1) return SWIM_ERROR_PARITY;
  return result >> 1;
}

/**
 * Sends a command bit sequence plus all specified data bytes in succession.
 * Returns -1 if the host failed to ACK a packet within TIMEOUT.
 */
int send_command(uint32_t cmd, size_t len, const uint8_t *data) {
  PIN_AS_OUTPUT(SWIM);
  uint32_t next = get_ccount() + 40;
  int status = write_byte(&next, cmd, BIT3);
  if (status != BIT4) return status < 0 ? status : SWIM_ERROR_NACK;
  for (int i = 0; i < len; i++) {
    next = MAX(next + BIT_TOTAL_PERIOD_LENGTH, get_ccount() + 40);
    PIN_AS_OUTPUT(SWIM);
    int status = write_byte(&next, data[i], BIT8);
    if (status == BIT4)  // ACK received
      continue;
    else if (status == 0)  // NACK received, resend the bit
      i--;
    else if (status < 0)
      return status;
  }
  return 0;
}

/**
 * Encodes len and address into a 4 byte buffer.
 */
void generate_len_and_address_spec(uint8_t *dest, size_t len, uint32_t addr) {
  dest[0] = len;
  dest[1] = addr >> 16;
  dest[2] = addr >> 8;
  dest[3] = addr;
}

/**
 * Issues a read-on-the-fly command to read up to 255 bytes from a specified
 * address.
 */
int rotf(const uint8_t *len_and_address_spec, uint8_t *dest) {
  uint32_t state = esp8266_enter_critical();
  int status = send_command(1, 4, len_and_address_spec);
  if (status < 0) {
    esp8266_leave_critical(state);
    return status;
  }
  for (int i = 0; i < len_and_address_spec[0]; i++) {
    int result = read_byte();
    if (result < 0) {
      esp8266_leave_critical(state);
      return result;
    }
    dest[i] = result;
  }
  esp8266_leave_critical(state);
  return 0;
}

/**
 * Issues a write-on-the-fly command to write up to 255 bytes to a specified
 * address.
 *
 * Data is the buffer filled with 4 bytes using generate_len_and_address_spec
 * plus the actual data to be written.
 */
int wotf(const uint8_t *data) {
  uint32_t state = esp8266_enter_critical();
  int result = send_command(2, 4 + data[0], data);
  esp8266_leave_critical(state);
  return result;
}

/** Sends the SWIM command to perform a soft-reset of the device. */
int srst() {
  uint32_t state = esp8266_enter_critical();
  int result = send_command(0, 0, NULL);
  esp8266_leave_critical(state);
  return result;
}

/** Sends the SWIM activation sequence. */
int swim_entry() {
  // Set GPIO2 to output mode
  PIN_AS_OUTPUT(SWIM);
  uint32_t counter = get_ccount();

  // Initial 16us LOW
  SET_PIN_LOW(SWIM);
  counter += 80 * 16;  // 16μs
  sync_ccount(counter);

  // 4 pulses at 1kHz, 4 pulses at 2kHz
  for (int i = 0; i < 16; i++) {
    i & 1 ? SET_PIN_LOW(SWIM) : SET_PIN_HIGH(SWIM);
    // 1st 8 iterations: 500us per state, last 8 iterations: 250us per state.
    for (int j = 0; j < 50; j++) {
      system_soft_wdt_feed();
      counter += (i < 8 ? MICROS_TO_CYCLES(10) : MICROS_TO_CYCLES(5));
      sync_ccount(counter);
    }
  }

  // Now comes the tricky part where communication is relatively fast, so
  // we don’t want to have any interrupts etc disturbing us.
  uint32_t state = esp8266_enter_critical();
  SET_PIN_HIGH(SWIM);
  PIN_AS_INPUT(SWIM);

  // Give the device 10us to respond.
  uint32_t timeout = MICROS_TO_CYCLES(30) / 6;
  while (READ_PIN(SWIM) && --timeout)
    ;  // ~6 cycles
  counter = get_ccount();
  if (!timeout) return SWIM_ERROR_SYNC_TIMEOUT_1;

  // Now comes the sync bit, that would allow us to calibrate our clock.
  // 128 cycles (@8MHz) i.e. 16us. We currently just use it as a sanity
  // check to make sure the (right) device responds.
  timeout = MICROS_TO_CYCLES(30) / 6;
  while (!READ_PIN(SWIM) && --timeout)
    ;  // ~6 cycles
  int duration = get_ccount() - counter;
  if (!timeout) return SWIM_ERROR_SYNC_TIMEOUT_2;

  esp8266_leave_critical(state);
  sync_ccount(counter + duration +
              24);  // Need to wait at least 300ns (=24 cycles)

  return duration;
}

/** Toggles the reset PIN. */
void reset(int on) {
  if (on == 0xFF) {
    PIN_AS_INPUT(NRST);
  } else {
    PIN_AS_OUTPUT(NRST);
    on ? SET_PIN_LOW(NRST) : SET_PIN_HIGH(NRST);
  }
}

/** On boot initialization. */
void swim_init() {
  SET_PIN_HIGH(NRST);
  PIN_AS_OUTPUT(NRST);
}
