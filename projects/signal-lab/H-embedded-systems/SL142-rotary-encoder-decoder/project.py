from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-142", title="Quadrature rotary-encoder decoder", level="M",
    tools="C firmware (Gray-code state-table decoder, polled at a fixed rate) on the simulated MCU, stimulus with bounce",
    summary="Decode a mechanical quadrature encoder (with contact bounce) using a 16-entry transition table polled at "
            "1–20 kHz; count errors for spins of increasing speed and find the speed where polling becomes too slow.",
    problem="Rotary encoders produce two offset square waves. How do you count reliably in both directions, reject bounce, "
            "and how fast can the knob turn before the MCU misses steps?",
    theory=r"""Valid transitions change exactly one of A/B (Gray code), so a 4×4 table maps (old, new) → −1/0/+1, and invalid double-changes are
ignored (they indicate a missed state). Bounce on one channel only toggles between two adjacent states, which the table cancels.
A poll at f_s can follow at most one state change per sample, and each edge is followed by up to 30 µs of bounce. A
sample must land in the *settled* part of every edge interval, so the edge interval must exceed T_poll + t_bounce: maximum speed ≈
1/(96·(T_poll + t_bounce)) rev/s (96 edges/rev). At slow polling this is ≈ f_s/96; at fast polling the bounce time dominates.""",
    method="""Stimulus: encoder rotated ±… with 24 detents × 4 edges/rev, speed 0.5–40 rev/s, forward then back, 30 µs of bounce (3 chatter edges) on each edge.
Firmware polls at 1, 5, 20 kHz; net count compared with the true count.""",
)

C = r"""
#include "hal_sim.h"
static const int8_t TAB[16] = {0,-1, 1,0, 1,0,0,-1, -1,0,0,1, 0,1,-1,0};
int main(int argc, char **argv) {
    double fpoll = atof(argv[1]), rps = atof(argv[2]);
    log_pins = 0;
    const int edges_per_rev = 96;
    double edge_dt = 1.0 / (rps * edges_per_rev);
    /* build edge schedule: forward 3 rev, back 1 rev */
    int nedge = edges_per_rev * 4;
    double t = 0.001; int state = 0, truecount = 0;
    const int seqf[4] = {0, 1, 3, 2};
    int pos = 0;
    double *et = malloc(sizeof(double) * nedge * 4); int *es = malloc(sizeof(int) * nedge * 4); int ne = 0;
    for (int k = 0; k < nedge; k++) {
        int dir = k < edges_per_rev * 3 ? 1 : -1;
        pos = (pos + dir + 4) % 4; truecount += dir;
        int ns = seqf[pos];
        int changed = ns ^ state;             /* one bit */
        for (int b = 0; b < 3; b++) { et[ne] = t + b * 8e-6; es[ne] = (b % 2 == 0) ? ns : state; ne++; }  /* bounce */
        et[ne] = t + 30e-6; es[ne] = ns; ne++;
        state = ns; t += edge_dt; (void)changed;
    }
    double dtp = 1.0 / fpoll; int count = 0, prev = 0, idx = 0, cur = 0;
    for (double tp = 0; tp < t + 0.01; tp += dtp) {
        while (idx < ne && et[idx] <= tp) { cur = es[idx]; idx++; }
        count -= TAB[(prev << 2) | cur]; prev = cur;     /* table sign convention: CW sequence 00→01→11→10 counts up */
    }
    printf("RES count %d\nRES truth %d\n", count, truecount);
    return 0;
}
"""


def run(p):
    rows = []
    fig, ax = p.fig()
    for i, fp in enumerate((1000, 5000, 20000)):
        errs = []
        speeds = [0.5, 1, 2, 4, 8, 12, 16, 24, 40, 60, 100, 160, 250]
        for rps in speeds:
            log = fwk.run(p, {"encoder.c": C}, args=(fp, rps))
            r = fwk.results(log)
            errs.append(abs(r["count"] - r["truth"]))
        errs = np.array(errs)
        ok = np.array(speeds)[errs == 0]
        lim = ok.max() if len(ok) else 0
        pred = 1 / (96 * (1 / fp + 30e-6))          # a clean sample needs the stable part of each edge interval ≥ one poll period
        nxt = [s_ for s_ in speeds if s_ > lim]
        p.compare(f"Poll {fp/1e3:g} kHz: limit 1/(96·(T_poll + t_bounce)) lies between last pass and first fail", 1, int(lim <= pred <= (nxt[0] if nxt else np.inf)), "", kind="abs",
                  note=f"last error-free {lim} rev/s, predicted {pred:.1f} rev/s")
        rows.append((fp, speeds, errs))
        ax.semilogx(speeds, errs, "o-", color=COLORS[i], label=f"poll {fp/1e3:g} kHz")
        ax.axvline(pred, color=COLORS[i], ls=":", lw=1)
    style_axes(ax, "rotation speed (rev/s)", "|count error| after 3 rev fwd + 1 back", "Polling rate vs knob speed (dotted: predicted limit)")
    p.save(fig, "encoder", "Bounce never causes errors; speed does, once edges arrive faster than ~half the poll rate.")
    p.discuss("""At low speed the decoder counts exactly, even though every edge carries three bounce transitions — the state table turns
bounce into +1/−1 pairs that cancel. Errors appear where predicted once bounce is included: at 20 kHz a bare
edge-rate argument (f_s/96 = 208 rev/s) overestimates the limit because the 30 µs of chatter eats into each edge interval (my first
check even had the table's sign convention backwards, so every speed 'failed' with a count of exactly −truth). A hand-turned knob rarely exceeds ~5 rev/s (480 edges/s), so 5 kHz polling is ample; motor encoders need
interrupt- or hardware-timer-based decoding (quadrature counter peripherals).""")
