#include "hal_sim.h"
#define SCL 1
#define SDA 2
static int m_sda = 1, m_scl = 1, s_sda = 1;      /* open-drain drivers: 1 = released */
static double temp_c = 25.0;
static uint8_t ptr = 0, sbuf[2]; static int sbit = 0, sbyte = 0, s_state = 0, s_addr_rw = 0, s_ack = 0, s_shift = 0, s_nbits = 0;
static void bus_update(void) { digitalWrite(SCL, m_scl); digitalWrite(SDA, m_sda && s_sda); }
static void slave_on_scl_rise(void);
static void slave_on_scl_fall(void);
static void half(void) { delay_us(5); }
static void scl(int v) { int old = m_scl; m_scl = v; bus_update(); if (!old && v) slave_on_scl_rise(); if (old && !v) slave_on_scl_fall(); bus_update(); }
static void sda(int v) {
    int bus_old = m_sda && s_sda; m_sda = v; bus_update(); int bus_new = m_sda && s_sda;
    if (m_scl && bus_old && !bus_new) { s_state = 1; s_nbits = 0; s_shift = 0; sbyte = 0; }   /* START */
    if (m_scl && !bus_old && bus_new) { s_state = 0; }                                    /* STOP  */
}
/* ---------------- slave (TMP102-like at 0x48) ---------------- */
static void slave_on_scl_rise(void) {
    if (s_state == 1 || s_state == 2) { s_shift = (s_shift << 1) | (m_sda && s_sda); s_nbits++; }
}
static int reading = 0, rbyte = 0, rbit = 0;
static void slave_on_scl_fall(void) {
    if (s_ack) { s_sda = 1; s_ack = 0; if (reading) { s_nbits = 0; } }
    if (reading && s_state == 3) {
        if (rbit < 8) { s_sda = (sbuf[rbyte] >> (7 - rbit)) & 1; rbit++; }
        else { s_sda = 1; rbit = 0; rbyte++; if (rbyte > 1) { reading = 0; } }
        return;
    }
    if (s_nbits == 8) {
        s_nbits = 0;
        if (sbyte == 0) {
            if ((s_shift >> 1) == 0x48) {
                s_sda = 0; s_ack = 1;
                if (s_shift & 1) {   /* read: load register */
                    int16_t raw = (int16_t)lround(temp_c / 0.0625);
                    uint16_t v = (uint16_t)(raw << 4); sbuf[0] = v >> 8; sbuf[1] = v & 0xFF;
                    reading = 1; rbyte = 0; rbit = 0; s_state = 3;
                } else s_state = 2;
            }
        } else if (s_state == 2) { ptr = (uint8_t)s_shift; s_sda = 0; s_ack = 1; }
        sbyte++; s_shift = 0;
    }
}
/* ---------------- master driver ---------------- */
static void start(void) { sda(1); scl(1); half(); sda(0); half(); scl(0); half(); }
static void stop(void) { sda(0); half(); scl(1); half(); sda(1); half(); }
static int write_byte(uint8_t b) {
    for (int i = 7; i >= 0; i--) { sda((b >> i) & 1); half(); scl(1); half(); scl(0); }
    sda(1); half(); scl(1); int ack = !(m_sda && s_sda); half(); scl(0); return ack;
}
static uint8_t read_byte(int ack) {
    uint8_t b = 0; sda(1);
    for (int i = 0; i < 8; i++) { half(); scl(1); b = (b << 1) | (m_sda && s_sda); half(); scl(0); }
    sda(!ack); half(); scl(1); half(); scl(0); sda(1); return b;
}
static double tmp102_read(void) {
    start(); write_byte(0x48 << 1); write_byte(0x00);
    start(); write_byte((0x48 << 1) | 1);
    uint8_t hi = read_byte(1), lo = read_byte(0); stop();
    int16_t raw = (int16_t)((hi << 8) | lo) >> 4;
    return raw * 0.0625;
}
int main(void) {
    bus_update();
    for (int k = 0; k < 40; k++) {
        temp_c = -25.0 + 150.0 * k / 39.0;
        uint64_t t0 = sim_us;
        double r = tmp102_read();
        printf("T %.4f %.4f %llu\n", temp_c, r, (unsigned long long)(sim_us - t0));
        delay_ms(2);
    }
    return 0;
}
