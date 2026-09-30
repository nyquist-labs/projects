from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-145", title="Polling vs interrupts: response latency and jitter", level="M",
    tools="C firmware scheduling model (main loop with variable work, ISR entry cost, critical sections) on the simulated MCU",
    summary="Measure how long firmware takes to respond to 10,000 random external events when it polls in the main loop "
            "versus when it uses an interrupt — including the effect of a critical section that disables interrupts.",
    problem="Why do real-time systems use interrupts, and what determines their worst-case latency?",
    theory=r"""Polling with a loop of period T responds after a delay uniform in [0, T] (+ handler time): mean T/2, worst T. An interrupt responds after the
fixed entry cost (~12 cycles + instruction completion) unless interrupts are masked, in which case the worst case adds the longest critical
section C: latency ∈ [t_entry, t_entry + C].""",
    method="""Loop period 500 µs (variable work 400–600 µs), ISR entry 0.75 µs (12 cycles at 16 MHz), a 50 µs critical section executed once per loop. 10,000 events at
random times; latency to the first instruction of the handler recorded for both strategies.""",
)

C = r"""
#include "hal_sim.h"
int main(void) {
    log_pins = 0;
    const int NEV = 10000; double t_loop_start = 0;
    for (int e = 0; e < NEV; e++) {
        double ev = e * 7919.0 + rnd01() * 5000.0;            /* event time, µs */
        /* main loop timeline around the event: loop iterations with random work 400–600 µs */
        double t = floor(ev / 500.0) * 500.0 - 1000.0; double poll_resp = -1, crit_s = 0, crit_e = 0;
        while (1) {
            double work = 400 + 200 * rnd01();
            double cs = t + work * rnd01(); crit_s = cs; crit_e = cs + 50;
            if (t >= ev && poll_resp < 0) poll_resp = t;           /* the flag is checked at the top of the loop */
            if (t > ev + 2000) break;
            if (crit_s <= ev && ev < crit_e) { printf("M %f\n", crit_e - ev); }
            t += work;
        }
        double isr = 0.75; double lat_irq = isr;
        /* is the event inside a critical section of the iteration containing it? */
        double it0 = floor(ev / 500.0) * 500.0; double cs0 = it0 + 250 * rnd01();
        if (cs0 <= ev && ev < cs0 + 50) lat_irq += cs0 + 50 - ev;
        printf("L %f %f\n", poll_resp - ev, lat_irq);
    }
    return 0;
}
"""


def run(p):
    log = fwk.run(p, {"latency.c": C})
    L = fwk.rows(log, "L")
    poll, irq = L[:, 0], L[:, 1]
    p.compare("Polling: mean latency (≈ T/2 = 250 µs)", 250, poll.mean(), "µs", tol=10)
    p.compare("Polling: worst latency (≈ max loop period 600 µs)", 600, poll.max(), "µs", tol=10)
    p.compare("Interrupt: minimum latency (entry cost)", 0.75, irq.min(), "µs", kind="abs")
    p.compare("Interrupt: worst latency (entry + 50 µs critical section)", 50.75, irq.max(), "µs", tol=3)
    frac = np.mean(irq > 1)
    p.metric("Fraction of interrupt events delayed by a critical section", frac * 100, "%", "≈ 50 µs / 500 µs × ½ window")
    fig, ax = p.fig()
    ax.hist(poll, 50, color=COLORS[1], alpha=.8, label="polling")
    ax.hist(irq, 50, color=C_MEAS, alpha=.8, label="interrupt")
    ax.set_yscale("log")
    style_axes(ax, "response latency (µs)", "events", "10,000 events: polling vs interrupt")
    p.save(fig, "latency", "Polling latency is uniform up to the loop period; interrupts respond in ~1 µs unless masked.")
    p.csv("latency", poll_us=poll, irq_us=irq)
    p.discuss("""Polling latency is spread uniformly up to the loop period (mean ~T/2, worst ~T), so it grows with every feature added to the
main loop. The interrupt responds in the entry cost almost always — but its *worst case* is set by the longest stretch
with interrupts disabled, which is why real-time code keeps critical sections to a few microseconds and why RTOS vendors
quote 'interrupt latency' as entry cost plus longest masked section.""")
