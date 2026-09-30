from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-154", title="Low-power firmware state machine and battery-life estimate", level="M",
    tools="C firmware (sleep/wake state machine with an energy ledger per state) on the simulated MCU",
    summary="A sensor node that sleeps, wakes on a timer or button interrupt, samples, and transmits in bursts: log the time "
            "spent in each power state, compute the average current and battery life, and compare with the duty-cycle formula.",
    problem="A coin cell holds 220 mAh. Will a sensor node last a month or five years — and which state dominates the budget?",
    theory=r"""$\bar I=\sum_s I_s\,t_s/T$ and life = capacity/$\bar I$. Currents: deep sleep 2 µA, wake + sample 1.5 mA for 5 ms every 60 s, radio TX 12 mA for 20 ms every
10 minutes, button wake (random, ~20/day) 1.5 mA for 50 ms. Predicted $\bar I$ ≈ 2 + 1500·5/60,000 + 12,000·20/600,000 + (20/86,400)·1500·0.05 ≈ 2 + 0.125 + 0.4 + 0.017 ≈ 2.54 µA
→ life ≈ 220 mAh / 2.54 µA ≈ 9.9 years (before self-discharge).""",
    method="""State machine SLEEP → WAKE → SAMPLE → (every 10th sample) TX → SLEEP; button events from a Poisson process. 30 simulated days at 1 µs resolution for
state changes; ledger accumulates charge per state.""",
)

C = r"""
#include "hal_sim.h"
enum { SLEEP, SAMPLE, TX, BUTTON, NSTATE };
static const double I_uA[NSTATE] = {2.0, 1500.0, 12000.0, 1500.0};
static double charge[NSTATE], tin[NSTATE];
static void spend(int s, double us) { charge[s] += I_uA[s] * us; tin[s] += us; sim_us += (uint64_t)us; }
int main(void) {
    log_pins = 0;
    const double T_end = 30.0 * 86400e6;
    double next_sample = 60e6, next_button = -log(rnd01()) * 86400e6 / 20;
    int samples = 0;
    while (sim_us < T_end) {
        double t = (double)sim_us;
        double nxt = next_sample < next_button ? next_sample : next_button;
        if (nxt > T_end) nxt = T_end;
        spend(SLEEP, nxt - t);
        if (nxt == next_sample) {
            spend(SAMPLE, 5000); samples++;
            if (samples % 10 == 0) spend(TX, 20000);
            next_sample += 60e6;
        } else if (nxt == next_button) {
            spend(BUTTON, 50000); next_button += -log(rnd01()) * 86400e6 / 20;
        } else break;
    }
    double T = (double)sim_us, Q = 0;
    for (int s = 0; s < NSTATE; s++) { Q += charge[s]; printf("S %d %f %f\n", s, tin[s] / T, charge[s] / T); }
    printf("RES avg_uA %f\n", Q / T);
    return 0;
}
"""


def run(p):
    log = fwk.run(p, {"lowpower.c": C})
    r = fwk.results(log)
    S = fwk.rows(log, "S")
    pred = 2.0 * (1 - 5e-3 / 60 - 20e-3 / 600) + 1500 * 5 / 60000 + 12000 * 20 / 600000 + 20 / 86400 * 1500 * 0.05
    p.compare("Average current (duty-cycle formula)", pred, r["avg_uA"], "µA", tol=2)
    life = 220e3 / r["avg_uA"] / 24 / 365
    p.compare("Battery life on a 220 mAh CR2032", 220e3 / pred / 24 / 365, life, "years", tol=2)
    names = ["sleep", "sample", "radio TX", "button"]
    shares = S[:, 2] / S[:, 2].sum() * 100
    for n, sh, tf in zip(names, shares, S[:, 1]):
        p.metric(f"{n}: share of charge / share of time", f"{sh:.1f} % / {tf*100:.4f} %")
    fig, ax = p.fig(1, 2, w=10)
    ax[0].bar(names, S[:, 1] * 100, color=C_MEAS); ax[0].set_yscale("log")
    style_axes(ax[0], None, "% of time (log)", "Where the time goes", legend=False)
    ax[1].bar(names, shares, color=COLORS[1])
    style_axes(ax[1], None, "% of charge", "Where the charge goes", legend=False)
    p.save(fig, "budget", "The node sleeps 99.99 % of the time, yet sleep current is still the largest share of the budget.")
    p.discuss("""The ledger reproduces the duty-cycle arithmetic to a fraction of a percent, giving ~9–10 years on a coin cell — in practice capped
by the cell's self-discharge (~1 %/year) and by radio retries. The instructive part is the breakdown: the radio burns 12 mA but only
for 20 ms per 10 minutes, so the 2 µA sleep current is the biggest single consumer. Halving sleep current does more for battery life
than halving the transmit time — the reason low-power MCU datasheets lead with their sleep-mode numbers.""")
