#include <stdio.h>
#include "wokwi-api.h"
static i2c_config_t bus; static float last_v = -1;
pin_t pin_init(const char *name, int mode) { (void)name; (void)mode; return 1; }
void pin_dac_write(pin_t pin, float v) { (void)pin; last_v = v; }
int i2c_init(const i2c_config_t *cfg) { bus = *cfg; return 0; }
void chip_init(void);
int main(void) {
    chip_init();
    int wrong_addr_acks = 0;
    for (uint32_t a = 0; a < 128; a++) if (a != 0x60 && bus.connect(bus.user_data, a, false)) wrong_addr_acks++;
    printf("RES wrong_addr_acks %d\n", wrong_addr_acks);
    for (int code = 0; code < 4096; code++) {
        bus.connect(bus.user_data, 0x60, false);
        bus.write(bus.user_data, (uint8_t)(code >> 8)); bus.write(bus.user_data, (uint8_t)(code & 0xFF));
        bus.disconnect(bus.user_data);
        printf("V %d %.7f\n", code, last_v);
    }
    return 0;
}
