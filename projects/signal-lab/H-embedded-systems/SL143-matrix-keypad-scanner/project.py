from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-143", title="4×4 matrix keypad scanner with debouncing (and ghosting)", level="E",
    tools="C firmware (row-drive / column-read scanning, per-key debounce counters) with a simulated switch matrix",
    summary="Scan a 16-key matrix with 8 pins, debounce each key with an integrator, measure detection latency and verify "
            "every key; then press three keys at the corners of a rectangle and watch the 'ghost' fourth key appear "
            "without diodes.",
    problem="How can 8 wires read 16 buttons, how quickly does a press register, and what breaks when several keys are "
            "held?",
    theory=r"""Driving one row low at a time and reading the columns identifies each key; a full scan of 4 rows at a 1 ms row period takes 4 ms. A key
must read pressed on N consecutive scans (N = 5) → latency ≈ N × 4 ms = 20 ms (+ up to one scan). With three keys pressed at (r1,c1),
(r1,c2), (r2,c1), current flows r2→c1→r1→c2, so (r2,c2) reads pressed too: ghosting (fixed by a diode per switch).""",
    method="""Each of the 16 keys is pressed once with 3 ms of bounce, then released; firmware scans every 1 ms per row. Then keys 1, 2, 5 held
together. Latency = time from bounce end to the debounced 'press' event.""",
)

C = r"""
#include "hal_sim.h"
static int pressed[4][4];
static int read_col(int row, int col, int ghost) {
    if (pressed[row][col]) return 0;
    if (ghost) {   /* current path through three closed switches without diodes */
        for (int r2 = 0; r2 < 4; r2++) for (int c2 = 0; c2 < 4; c2++)
            if (r2 != row && c2 != col && pressed[row][c2] && pressed[r2][c2] && pressed[r2][col]) return 0;
    }
    return 1;
}
int main(void) {
    log_pins = 0;
    int integ[4][4] = {0}, state[4][4] = {0};
    const int N = 5;
    uint64_t press_t[16]; int got[16] = {0};
    for (int k = 0; k < 16; k++) {
        int r = k / 4, c = k % 4;
        uint64_t t0 = sim_us;
        for (uint64_t tt = 0; tt < 80000; tt += 1000) {
            for (int row = 0; row < 4; row++) {
                uint64_t now = t0 + tt + row * 250;
                memset(pressed, 0, sizeof pressed);
                if (now - t0 >= 5000 && now - t0 < 60000) {
                    if (now - t0 < 8000) pressed[r][c] = ((now / 300) % 2); else pressed[r][c] = 1;
                }
                for (int col = 0; col < 4; col++) {
                    int down = !read_col(row, col, 0);
                    if (down && integ[row][col] < N) integ[row][col]++;
                    if (!down && integ[row][col] > 0) integ[row][col]--;
                    if (integ[row][col] == N && !state[row][col]) { state[row][col] = 1; printf("P %d %llu\n", row * 4 + col, (unsigned long long)(now - t0)); if (row * 4 + col == k && !got[k]) { got[k] = 1; press_t[k] = now - t0; } }
                    if (integ[row][col] == 0 && state[row][col]) state[row][col] = 0;
                }
            }
        }
        sim_us = t0 + 100000;
    }
    int ok = 0; for (int k = 0; k < 16; k++) ok += got[k];
    RES("keys_detected", "%d", ok);
    memset(pressed, 0, sizeof pressed); pressed[0][0] = pressed[0][1] = pressed[1][0] = 1;
    int seen = 0;
    for (int row = 0; row < 4; row++) for (int col = 0; col < 4; col++) if (!read_col(row, col, 1)) { seen++; printf("GH %d\n", row * 4 + col); }
    RES("keys_seen_with_3_pressed", "%d", seen);
    return 0;
}
"""


def run(p):
    log = fwk.run(p, {"keypad.c": C})
    r = fwk.results(log)
    P = fwk.rows(log, "P")
    p.compare("Keys detected (16 pressed one at a time)", 16, r["keys_detected"], "", kind="abs")
    lat = P[:, 1] / 1000 - 8.0
    p.compare("Worst detection latency after bounce ends (≤ N × 1 ms scan)", 5.0, float(np.max(lat)), "ms", kind="abs",
              note="N = 5; the integrator may already be part-way up when the bounce ends")
    p.metric("Median detection latency after bounce ends", float(np.median(lat)), "ms")
    p.compare("Keys reported with 3 held (ghost appears)", 4, r["keys_seen_with_3_pressed"], "", kind="abs")
    ghosts = [int(l.split()[1]) for l in log.splitlines() if l.startswith("GH")]
    grid = np.zeros((4, 4))
    for g in ghosts:
        grid[g // 4, g % 4] = 1
    grid[1, 1] = 2 if grid[1, 1] else 0
    fig, ax = p.fig(1, 2, w=10)
    ax[0].hist(lat, bins=10, color=C_MEAS)
    style_axes(ax[0], "latency after bounce (ms)", "keys", "Debounce latency", legend=False)
    ax[1].imshow(grid, cmap="Oranges", vmin=0, vmax=2)
    for (i, j), lab in zip([(0, 0), (0, 1), (1, 0), (1, 1)], ["held", "held", "held", "GHOST"]):
        ax[1].text(j, i, lab, ha="center", va="center", fontsize=9)
    ax[1].set_xticks(range(4)); ax[1].set_yticks(range(4)); ax[1].set_title("3 keys held → 4 reported", loc="left", fontsize=10)
    p.save(fig, "keypad", "Debounce adds a fixed ~5 ms latency; three keys in a rectangle create a ghost fourth key.")
    p.discuss("""Every key is found and debounced; the latency after the bounce ends is set by the integrator (5 consecutive reads of that key's
row, one per 1 ms scan slot) — short enough to feel instant. The ghosting test reproduces the classic matrix limitation: with
three corners of a rectangle held, current sneaks through the three closed switches and the fourth corner reads as pressed.
Gaming keyboards add a diode per key (or scan each key individually) to get 'n-key rollover'.""")
