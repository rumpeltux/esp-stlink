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
#include "driver/swim.h"
#include "driver/uart.h"
#include "espmissingincludes.h"
#include "user_interface.h"
#include "version.h"

#define serial_recvTaskPrio 0
#define serial_recvTaskQueueLen 64
os_event_t serial_recvTaskQueue[serial_recvTaskQueueLen];
static void serial_recvTask(os_event_t *events);

static int cmd_buf_idx = 0;
/**
 * Multi-use buffer for recv and send.
 * 1 byte command
 * 1 byte length
 * 3 byte address
 * 255 byte user data
 */
static uint8_t cmd_buf[1 + 4 + 255];

#define HAVE_SERIAL_DATA() \
  (READ_PERI_REG(UART_STATUS(UART0)) & (UART_RXFIFO_CNT << UART_RXFIFO_CNT_S))
#define READ_BYTE_FROM_SERIAL() (READ_PERI_REG(UART_FIFO(UART0)) & 0xFF);
#define TICKLE_WATCHDOG() WRITE_PERI_REG(0X60000914, 0x73)

#define CMD_SRST 0
#define CMD_ROTF 1
#define CMD_WOTF 2
#define CMD_RESET 0xFD
#define CMD_INIT 0xFE
#define CMD_VERSION 0xFF

static void ICACHE_FLASH_ATTR send_error(int code) {
  uart_tx_one_char(UART0, 0xFF);
  code = -code;
  uart_tx_one_char(UART0, code >> 8);
  uart_tx_one_char(UART0, code);
}

static void ICACHE_FLASH_ATTR send_ack() {
  uart_tx_one_char(UART0, cmd_buf[0]);
}

static void ICACHE_FLASH_ATTR serial_recvTask(os_event_t *events) {
  while (HAVE_SERIAL_DATA()) {
    TICKLE_WATCHDOG();
    cmd_buf[cmd_buf_idx++] = READ_BYTE_FROM_SERIAL();

    // See serial-protocol.md for a description.
    // Here we check that any given command is complete including all arguments.
    if (cmd_buf[0] == CMD_ROTF && cmd_buf_idx < 5) continue;
    if (cmd_buf[0] == CMD_WOTF && cmd_buf[1] != cmd_buf_idx - 5) continue;
    if (cmd_buf[0] == CMD_RESET && cmd_buf_idx < 2) continue;

    int result = 0;
    send_ack();
    switch (cmd_buf[0]) {
      case CMD_SRST:
        result = srst();
        break;
      case CMD_ROTF:
        result = rotf(cmd_buf + 1, cmd_buf + 5);
        cmd_buf_idx += cmd_buf[1];
        break;
      case CMD_WOTF:
        result = wotf(cmd_buf + 1);
        cmd_buf_idx = 5;
        break;
      case CMD_INIT:
        result = swim_entry();
        cmd_buf[cmd_buf_idx++] = result >> 8;
        cmd_buf[cmd_buf_idx++] = result;
        break;
      case CMD_RESET:
        reset(cmd_buf[1]);
        cmd_buf_idx = 1;
        break;
      case CMD_VERSION:
        cmd_buf[cmd_buf_idx++] = FIRMWARE_VERSION_MAJOR;
        cmd_buf[cmd_buf_idx++] = FIRMWARE_VERSION_MINOR;
        break;
      default:
        result = -1;
    }
    if (result < 0)
      send_error(result);
    else {
      cmd_buf[0] = 0;
      uart0_tx_buffer(cmd_buf, cmd_buf_idx);
    }
    cmd_buf_idx = 0;
  }

  // Clear some registers if necessary...
  if (UART_RXFIFO_FULL_INT_ST ==
      (READ_PERI_REG(UART_INT_ST(UART0)) & UART_RXFIFO_FULL_INT_ST)) {
    WRITE_PERI_REG(UART_INT_CLR(UART0), UART_RXFIFO_FULL_INT_CLR);
  } else if (UART_RXFIFO_TOUT_INT_ST ==
             (READ_PERI_REG(UART_INT_ST(UART0)) & UART_RXFIFO_TOUT_INT_ST)) {
    WRITE_PERI_REG(UART_INT_CLR(UART0), UART_RXFIFO_TOUT_INT_CLR);
  }
  ETS_UART_INTR_ENABLE();
}

void ICACHE_FLASH_ATTR serial_init(void) {
  system_os_task(serial_recvTask, serial_recvTaskPrio, serial_recvTaskQueue,
                 serial_recvTaskQueueLen);
}
