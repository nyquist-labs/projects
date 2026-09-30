#include "hal_sim.h"
#define FLASH 65536
#define SECT 4096
#define PAGE 256
static uint8_t flash[FLASH]; static uint32_t erases[FLASH / SECT];
static void f_erase(int s) { memset(flash + s * SECT, 0xFF, SECT); erases[s]++; }
static void f_write(uint32_t a, const uint8_t *d, int n) { for (int i = 0; i < n; i++) flash[a + i] &= d[i]; }
static uint16_t crc16(const uint8_t *d, int n) { uint16_t c = 0xFFFF; for (int i = 0; i < n; i++) { c ^= d[i] << 8; for (int b = 0; b < 8; b++) c = c & 0x8000 ? (c << 1) ^ 0x1021 : c << 1; } return c; }
int main(void) {
    log_pins = 0;
    for (int s = 0; s < FLASH / SECT; s++) f_erase(s);
    for (int s = 0; s < FLASH / SECT; s++) erases[s] = 0;
    uint32_t wp = 0; uint8_t pagebuf[PAGE]; int fill = 0;
    const long N = 30L * 86400;
    for (long k = 0; k < N; k++) {
        uint8_t rec[10]; uint32_t t = (uint32_t)k; float val = (float)(20 + 5 * sin(k / 3600.0));
        memcpy(rec, &t, 4); memcpy(rec + 4, &val, 4); uint16_t c = crc16(rec, 8); memcpy(rec + 8, &c, 2);
        memcpy(pagebuf + fill, rec, 10); fill += 10;
        if (fill + 10 > PAGE) {
            if (wp % SECT == 0) f_erase(wp / SECT);
            memset(pagebuf + fill, 0xFF, PAGE - fill);
            f_write(wp, pagebuf, PAGE); wp = (wp + PAGE) % FLASH; fill = 0;
        }
    }
    uint32_t mx = 0, mn = 1u << 31; for (int s = 0; s < FLASH / SECT; s++) { if (erases[s] > mx) mx = erases[s]; if (erases[s] < mn) mn = erases[s]; }
    RES("max_erases", "%u", mx); RES("min_erases", "%u", mn);
    /* readback of the whole ring */
    long good = 0, bad = 0;
    for (uint32_t a = 0; a < FLASH; a += PAGE) for (int o = 0; o + 10 <= PAGE; o += 10) {
        uint8_t *r = flash + a + o; if (r[0] == 0xFF && r[1] == 0xFF && r[8] == 0xFF) continue;
        uint16_t c; memcpy(&c, r + 8, 2); if (crc16(r, 8) == c) good++; else bad++;
    }
    RES("readback_good", "%ld", good); RES("readback_bad", "%ld", bad);
    /* torn write: program only the first half of a fresh page */
    uint32_t tp = wp; if (tp % SECT == 0) f_erase(tp / SECT);
    uint8_t pb[PAGE]; memset(pb, 0x5A, PAGE); for (int o = 0; o + 10 <= PAGE; o += 10) { uint16_t c = crc16(pb + o, 8); memcpy(pb + o + 8, &c, 2); }
    f_write(tp, pb, PAGE / 2 + 3);   /* power fails mid-page */
    long tg = 0, tb = 0; for (int o = 0; o + 10 <= PAGE; o += 10) { uint8_t *r = flash + tp + o; if (r[0] == 0xFF && r[8] == 0xFF) continue; uint16_t c; memcpy(&c, r + 8, 2); if (crc16(r, 8) == c) tg++; else tb++; }
    RES("torn_good", "%ld", tg); RES("torn_detected", "%ld", tb);
    return 0;
}
