from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-144", title="Timestamped data logger with flash wear levelling", level="M",
    tools="C firmware (record packing, CRC-16, page buffer, circular log over a simulated NOR flash with erase counters)",
    summary="Log 10-byte timestamped sensor records to a simulated 64 KiB flash (256-byte pages, 4 KiB sectors) for a "
            "simulated 30 days at 1 record/s; verify every record by CRC after readback and predict flash lifetime from "
            "the measured erase counts.",
    problem="Flash can only be erased ~100,000 times per sector. How long will a data logger last, and how do you make sure "
            "no record is silently corrupted?",
    theory=r"""Record = 4-byte time + 4-byte value + 2-byte CRC-16 = 10 B → 25 records per 256-B page, 400 per 4 KiB sector. At 1 record/s a sector fills
every 400 s; a circular log over 16 sectors erases each sector once per 6,400 s → 100,000 cycles last 6.4×10⁸ s ≈ 20 years. Writing each
record directly (erase-per-record) would wear out a sector in 28 hours.""",
    method="""Simulated flash enforces NOR semantics (writes can only clear bits; erase sets a 4 KiB sector to 0xFF and increments its counter). 30 days ×
86,400 records; power-fail test: a random page write is torn (half written) and readback must detect it by CRC.""",
)

C = r"""
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
"""


def run(p):
    log = fwk.run(p, {"logger.c": C})
    r = fwk.results(log)
    N = 30 * 86400
    recs_per_sector = 4096 // 256 * (256 // 10)
    pred_erases = N / recs_per_sector / 16
    p.compare("Erases per sector after 30 days (N / 400 / 16)", pred_erases, r["max_erases"], "", tol=2)
    p.compare("Erase-count spread across sectors (wear levelling)", 0, r["max_erases"] - r["min_erases"], "", kind="abs")
    life_s = 100000 * 16 * recs_per_sector
    p.metric("Predicted flash life at 1 record/s (100k cycles)", life_s / 86400 / 365, "years")
    p.compare("Records in the ring that pass CRC (capacity = 16 × 400)", 16 * recs_per_sector, r["readback_good"], "", kind="abs")
    p.compare("Records failing CRC in normal operation", 0, r["readback_bad"], "", kind="abs")
    p.metric("Torn-page test: intact records / records flagged by CRC", f"{int(r['torn_good'])} / {int(r['torn_detected'])}")
    fig, ax = p.fig()
    strategies = ["erase per record", "page buffer, 1 sector", "page buffer, 16-sector ring"]
    life = [100000 / 3600 / 24, 100000 * recs_per_sector / 86400, life_s / 86400]
    ax.barh(strategies, np.log10(life), color=[COLORS[7], COLORS[3], C_MEAS])
    ax.set_xticks([0, 1, 2, 3, 4]); ax.set_xticklabels(["1 d", "10 d", "100 d", "3 y", "27 y"])
    style_axes(ax, "flash lifetime at 1 record/s (log scale)", None, "Why loggers buffer and rotate", legend=False)
    p.save(fig, "lifetime", "Buffering records into pages and rotating over sectors stretches lifetime by five orders of magnitude.")
    p.discuss("""After 30 simulated days every sector has the same erase count as predicted (the ring spreads wear perfectly evenly), all 6,400
records currently in flash verify by CRC, and the projected lifetime is ~20 years. The torn-write test shows the value of a per-record
CRC: when power fails mid-page, records that were fully programmed still verify and the partially written one is flagged instead of
being read back as plausible garbage.""")
