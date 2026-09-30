// wokwi-api.h (host mock) — just enough of the Wokwi Chips API to unit-test chip.c on a PC
#pragma once
#include <stdint.h>
#include <stdbool.h>
typedef int pin_t;
enum { INPUT, OUTPUT, ANALOG };
typedef struct { void *user_data; uint32_t address; pin_t scl, sda;
  bool (*connect)(void *, uint32_t, bool); uint8_t (*read)(void *); bool (*write)(void *, uint8_t); void (*disconnect)(void *); } i2c_config_t;
pin_t pin_init(const char *name, int mode);
void pin_dac_write(pin_t pin, float v);
int i2c_init(const i2c_config_t *cfg);
