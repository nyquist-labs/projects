from eelab import *

META = dict(
    id="AM-099", title="Queueing theory for packet buffers: M/M/1 and Little's law", level="M",
    tools="Event-driven simulation of a single-server queue (Poisson arrivals, exponential service), M/M/1 formulas, Little's law, finite buffers and loss probability (M/M/1/K), a deterministic-service comparison (M/D/1)",
    summary="Simulate a router buffer, verify the M/M/1 predictions for queue length, waiting time and their blow-up as load approaches 1, confirm "
            "Little's law, size a finite buffer for a target loss rate, and show how deterministic packet lengths halve the waiting time.",
    problem="A link is 90 % utilised. How long do packets wait, and how large must the buffer be to lose fewer than one in a million?",
    theory=r"""M/M/1 with load ρ = λ/μ: mean number in system L = ρ/(1−ρ), mean time W = 1/(μ−λ); Little's law L = λW (for any stable queue). Finite buffer K (M/M/1/K): loss $P_K=\frac{(1-ρ)ρ^K}{1-ρ^{K+1}}$ ⇒ K ≈ ln(10⁻⁶)/ln ρ ≈ 131 at ρ = 0.9. M/D/1
(constant service): waiting time in queue $W_q=\frac{ρ}{2μ(1-ρ)}$, half the M/M/1 value — variability, not load alone, creates delay.""",
    method="""Lindley recursion for waiting times, 10⁶ packets per load, ρ = 0.1…0.95; time-average number in system from the sample path; finite-buffer simulation for K = 10…40 at ρ = 0.9 (losses counted directly where
measurable) and the formula extrapolated to 10⁻⁶.""",
)


def mm1(lam, mu, n, r, det=False):
    a = r.exponential(1 / lam, n); s = np.full(n, 1 / mu) if det else r.exponential(1 / mu, n)
    wq = np.zeros(n)
    for k in range(1, n):
        wq[k] = max(0.0, wq[k - 1] + s[k - 1] - a[k])
    return wq, s, np.cumsum(a)


def mm1k(lam, mu, K, n, r):
    t = 0.0; q = 0; lost = 0; next_a = r.exponential(1 / lam); next_d = np.inf; arrivals = 0
    while arrivals < n:
        if next_a < next_d:
            t = next_a; arrivals += 1
            if q >= K:
                lost += 1
            else:
                q += 1
                if q == 1:
                    next_d = t + r.exponential(1 / mu)
            next_a = t + r.exponential(1 / lam)
        else:
            t = next_d; q -= 1; next_d = t + r.exponential(1 / mu) if q > 0 else np.inf
    return lost / n


def run(p):
    r = p.rng; mu = 1.0; rows = []
    for rho in (0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95):
        wq, s, ta = mm1(rho * mu, mu, 10 ** 6, r)
        W = np.mean(wq + s)
        L_time = np.sum(wq + s) / ta[-1]
        rows.append((rho, W, 1 / (mu - rho * mu), L_time, rho / (1 - rho)))
    rr = np.array(rows)
    for rho, W, Wp, L, Lp in rr[[1, 5]]:
        p.compare(f"ρ = {rho}: mean time in system 1/(μ−λ)", Wp, W, "", tol=5)
        p.compare(f"ρ = {rho}: Little's law — time-average number = λ·W", rho * W, L, "", tol=1)
    p.compare("ρ = 0.95: mean number in system ρ/(1−ρ) (slow convergence near saturation)", 19.0, rr[-1, 3], "", tol=15)
    wqd, _, _ = mm1(0.9, 1.0, 10 ** 6, r, det=True)
    p.compare("M/D/1 at ρ = 0.9: queueing delay = ρ/(2μ(1−ρ)) (half of M/M/1)", 0.9 / (2 * 0.1), wqd.mean(), "", tol=5)
    Ks = [5, 10, 20, 30]
    loss = [(K, mm1k(0.9, 1.0, K, 400000, r), (1 - 0.9) * 0.9 ** K / (1 - 0.9 ** (K + 1))) for K in Ks]
    for K, lm, lp in loss[1:3]:
        p.compare(f"M/M/1/K, ρ = 0.9, K = {K}: loss probability", lp, lm, "", tol=10)
    Kneed = int(np.ceil(np.log(1e-6 * (1 - 0.9 ** 200) / (1 - 0.9)) / np.log(0.9)))
    p.metric("Buffer needed for loss < 10⁻⁶ at ρ = 0.9 (formula)", Kneed, "packets")
    fig, ax = p.fig(1, 2, w=11)
    rg = np.linspace(0.05, 0.96, 100)
    ax[0].plot(rr[:, 0], rr[:, 1], "o", color=C_MEAS, label="simulated W"); ax[0].plot(rg, 1 / (1 - rg), "--", color=C_PRED, label="1/(μ−λ)")
    ax[0].set_ylim(0, 25)
    style_axes(ax[0], "load ρ", "mean time in system (× service time)", "Delay explodes as ρ → 1")
    lk = np.array(loss)
    kk = np.arange(1, 140); ax[1].semilogy(kk, (1 - 0.9) * 0.9 ** kk / (1 - 0.9 ** (kk + 1)), color=C_PRED, label="M/M/1/K formula")
    ax[1].semilogy(lk[:, 0], lk[:, 1], "o", color=C_MEAS, label="simulated"); ax[1].axhline(1e-6, color="gray", ls=":")
    style_axes(ax[1], "buffer size K (packets)", "loss probability", "Sizing a buffer at ρ = 0.9")
    p.save(fig, "queueing", "Mean delay vs load for an M/M/1 queue, and packet loss vs buffer size.")
    p.discuss(f"""The simulated queue reproduces the M/M/1 results and makes the non-linearity tangible: at 50 % load a packet spends 2 service times in the system, at
90 % 10, at 95 % 20 — the last doubling of utilisation is paid for in delay. Little's law holds exactly, as it must for any stable system. Buffer
sizing follows the geometric tail: loss falls by a factor ρ per extra slot, so at ρ = 0.9 about {Kneed} packets of buffering are needed for 10⁻⁶ loss.
The M/D/1 comparison shows that variability, not only load, creates queues: constant-length packets wait half as long. Real traffic is burstier
than Poisson, which makes the M/M/1 numbers optimistic — the main reason operators keep links well below full load.""")
# tol-convention: relative tolerances are in percent
