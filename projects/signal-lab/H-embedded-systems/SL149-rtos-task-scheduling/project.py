from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-149", title="Rate-monotonic RTOS scheduling: response times vs analysis", level="H",
    tools="C discrete-event simulation of a preemptive fixed-priority scheduler (1 µs resolution), response-time analysis in Python",
    summary="Schedule four periodic tasks with rate-monotonic priorities in a preemptive kernel simulation; predict each task's "
            "worst-case response time with exact response-time analysis (RTA), measure it, and push the load until a "
            "deadline is missed.",
    problem="Can you prove a set of real-time tasks will always meet its deadlines before running it?",
    theory=r"""Liu & Layland: n tasks are schedulable under RM if $U=\sum C_i/T_i\le n(2^{1/n}-1)$ (0.757 for n = 4) — sufficient only. Exact RTA:
$R_i = C_i + \sum_{j<i}\lceil R_i/T_j\rceil C_j$, iterated to a fixed point; task i meets its deadline iff $R_i\le T_i$. Worst case at the critical instant (all
tasks released together).""",
    method="""Tasks (C, T) in ms: (1, 5), (2, 10), (3, 20), (4, 40) → U = 0.65; then C₄ increased until a miss. Kernel: 1 µs ticks, highest-priority ready task runs,
preemption at releases, 10 hyperperiods simulated; response time = completion − release.""",
)

C_SRC = r"""
#include "hal_sim.h"
int main(int argc, char **argv) {
    log_pins = 0;
    int n = 4; long Cc[4], T[4];
    for (int i = 0; i < 4; i++) { Cc[i] = atol(argv[1 + 2 * i]) ; T[i] = atol(argv[2 + 2 * i]); }
    long rem[4] = {0}, rel[4] = {0}; long worst[4] = {0}; int miss[4] = {0};
    long H = 40000L * 10;
    for (long t = 0; t < H; t++) {
        for (int i = 0; i < n; i++) if (t % T[i] == 0) { if (rem[i] > 0) miss[i]++; rem[i] = Cc[i]; rel[i] = t; }
        for (int i = 0; i < n; i++) if (rem[i] > 0) { rem[i]--; if (rem[i] == 0) { long r = t + 1 - rel[i]; if (r > worst[i]) worst[i] = r; } break; }
    }
    for (int i = 0; i < n; i++) printf("W %d %ld %d\n", i, worst[i], miss[i]);
    return 0;
}
"""


def rta(C, T):
    R = []
    for i in range(len(C)):
        r = C[i]
        while True:
            nr = C[i] + sum(np.ceil(r / T[j]) * C[j] for j in range(i))
            if nr == r or nr > 10 * T[i]:
                break
            r = nr
        R.append(r)
    return R


def run(p):
    C = [1000, 2000, 3000, 4000]; T = [5000, 10000, 20000, 40000]
    args = sum(([c, t] for c, t in zip(C, T)), [])
    log = fwk.run(p, {"rm_sched.c": C_SRC}, args=args)
    W = fwk.rows(log, "W")
    R = rta(C, T)
    for i in range(4):
        p.compare(f"Task {i+1} (C={C[i]/1000:g} ms, T={T[i]/1000:g} ms): worst response time (RTA)", R[i], W[i, 1], "µs", kind="abs")
    U = sum(c / t for c, t in zip(C, T))
    p.metric("Utilisation U", U, "", f"Liu–Layland bound for 4 tasks: {4*(2**0.25-1):.3f}")
    res = []
    for c4 in range(4000, 26001, 2000):
        Cx = C[:3] + [c4]
        log = fwk.run(p, {"rm_sched.c": C_SRC}, args=sum(([c, t] for c, t in zip(Cx, T)), []))
        W2 = fwk.rows(log, "W")
        Rx = rta(Cx, T)
        Ux = sum(c / t for c, t in zip(Cx, T))
        res.append((Ux, W2[3, 1], Rx[3], int(W2[3, 2] > 0)))
    Ux, Wm, Rp, miss = map(np.array, zip(*res))
    first_miss = Ux[np.argmax(miss)] if miss.any() else np.nan
    pred_miss = Ux[np.argmax(Rp > T[3])]
    p.compare("Utilisation at the first deadline miss (RTA prediction vs simulation)", pred_miss, first_miss, "", kind="abs")
    fig, ax = p.fig()
    ax.plot(Ux, Rp / 1000, "--", color=C_PRED, label="RTA prediction (task 4)")
    ax.plot(Ux, Wm / 1000, "o", color=C_MEAS, label="simulated worst response")
    ax.axhline(T[3] / 1000, color=COLORS[7], ls=":", label="deadline = period 40 ms")
    ax.axvline(4 * (2**0.25 - 1), color="gray", ls=":", label="Liu–Layland bound")
    style_axes(ax, "total utilisation U", "task-4 response time (ms)", "Growing the lowest-priority task until it misses")
    p.save(fig, "rta", "RTA predicts every worst-case response exactly; the task set stays schedulable well beyond the Liu–Layland bound.")
    import pandas as pd
    p.csv_df("sweep", pd.DataFrame(res, columns=["U", "sim_worst_us", "rta_us", "missed"]))
    p.discuss("""Simulated worst-case response times equal the RTA fixed point exactly, because the simulation starts all tasks at the critical
instant (t = 0) where the analysis says the worst case occurs. The Liu–Layland bound (0.757) is only sufficient: with these
harmonic periods (each divides the next) the task set remains schedulable up to U = 1, and the first miss appears exactly
where RTA says R₄ exceeds 40 ms. Harmonic periods are a practical design trick for exactly this reason.""")
