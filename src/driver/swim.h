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

#ifndef DRIVER_SWIM_H
#define DRIVER_SWIM_H
#include <c_types.h>
#include <stdint.h>

#define SWIM_ERROR_READ_BIT_TIMEOUT -1
#define SWIM_ERROR_INVALID_TARGET_ID -2
#define SWIM_ERROR_PARITY -3
#define SWIM_ERROR_NACK -4
#define SWIM_ERROR_SYNC_TIMEOUT_1 -5
#define SWIM_ERROR_SYNC_TIMEOUT_2 -6

void generate_len_and_address_spec(uint8_t *dest, size_t len, uint32_t address);
int rotf(const uint8_t *len_and_address_spec, uint8_t *dest);
int wotf(const uint8_t *data);
int srst();
int swim_entry();
void reset(int on);
void swim_init();

#endif
