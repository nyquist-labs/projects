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
