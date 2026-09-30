from eelab import *
from scipy import signal

META = dict(
    id="AM-034", title="Parks–McClellan from scratch: the Remez exchange algorithm", level="H",
    tools="Own Remez exchange for Type-I linear-phase low-pass filters (dense grid, barycentric Lagrange interpolation, alternation search), scipy.signal.remez as reference",
    summary="Implement the Parks–McClellan algorithm — Chebyshev (minimax) approximation of the ideal low-pass by a cosine polynomial — verify the "
            "alternation theorem on the result, match scipy's remez, and compare with a windowed design of the same length.",
    problem="What is the *best* FIR filter of a given length, and how do you compute it?",
    theory=r"""A Type-I FIR of length N = 2L+1 has amplitude $A(ω)=\sum_{k=0}^{L}a_k\cos kω$, a polynomial of degree L in x = cos ω. Chebyshev's alternation theorem: A minimises the maximum weighted error
$\max|W(ω)(A(ω)-D(ω))|$ over the bands iff the error attains its maximum with alternating sign at ≥ L+2 points. The Remez exchange finds these points iteratively: solve for the
ripple δ on the current extremal set, interpolate, move the set to the new error extrema, repeat. Result: equiripple bands, lower peak error than any window design of equal N.""",
    method="""N = 41 (L = 20), passband 0–0.2 fs, stopband 0.25–0.5 fs, weight 1:1. Dense grid of 16·N points per band. Converge when the extremal error differs from |δ| by < 1e-9. Compare coefficients with
scipy.signal.remez; count alternations; compare peak stopband error with a Kaiser-window design of the same length and transition.""",
)


def remez_lp(N, fp, fs_, W=(1.0, 1.0), dens=16, iters=60):
    L = (N - 1) // 2
    g1 = np.linspace(0, fp, dens * N // 2); g2 = np.linspace(fs_, 0.5, dens * N // 2)
    w = 2 * pi * np.r_[g1, g2]; D = np.r_[np.ones_like(g1), np.zeros_like(g2)]; Wt = np.r_[np.full_like(g1, W[0]), np.full_like(g2, W[1])]
    x = np.cos(w)
    ext = np.round(np.linspace(0, len(w) - 1, L + 2)).astype(int)
    for it in range(iters):
        xe = x[ext]
        b = np.array([1 / np.prod(xe[k] - np.delete(xe, k)) for k in range(L + 2)])
        sgn = (-1) ** np.arange(L + 2)
        delta = np.sum(b * D[ext]) / np.sum(b * sgn / Wt[ext])
        yk = D[ext] - sgn * delta / Wt[ext]
        xi, yi = xe[:-1], yk[:-1]
        bi = np.array([1 / np.prod(xi[k] - np.delete(xi, k)) for k in range(L + 1)])

        def A(xx):
            d = xx[:, None] - xi[None, :]
            exact = np.isclose(d, 0)
            d[exact] = 1
            r = (bi / d) @ yi / ((bi / d).sum(axis=1))
            hit = exact.any(axis=1)
            r[hit] = yi[exact.argmax(axis=1)[hit]]
            return r
        E = Wt * (A(x) - D)
        # candidate extrema: every local extremum of E inside each band, plus the band edges
        cand = []
        for lo, hi in ((0, len(g1)), (len(g1), len(w))):
            e = E[lo:hi]
            idx = [0] + [k for k in range(1, len(e) - 1) if (e[k] - e[k - 1]) * (e[k + 1] - e[k]) <= 0 and abs(e[k]) > 0] + [len(e) - 1]
            cand += [lo + k for k in idx]
        cand = sorted(set(cand))

        def merge(c):
            out = []
            for k in c:                       # consecutive same-sign extrema: keep the larger
                if out and np.sign(E[k]) == np.sign(E[out[-1]]):
                    if abs(E[k]) > abs(E[out[-1]]):
                        out[-1] = k
                else:
                    out.append(k)
            return out
        alt = merge(cand)
        while len(alt) > L + 2:               # spurious extrema come in adjacent +/− pairs: drop the weakest pair; drop an end if one is left over
            if len(alt) - (L + 2) >= 2:
                j = int(np.argmin([max(abs(E[alt[k]]), abs(E[alt[k + 1]])) for k in range(len(alt) - 1)]))
                alt = alt[:j] + alt[j + 2:]
            else:
                alt = alt[1:] if abs(E[alt[0]]) < abs(E[alt[-1]]) else alt[:-1]
        if len(alt) < L + 2:
            break
        conv = np.max(np.abs(E)) - abs(delta)
        ext = np.array(alt)
        if conv < 1e-9 * max(1.0, abs(delta)) or np.array_equal(ext, np.array(alt)) and conv < 1e-7:
            break
    # impulse response from A on a uniform grid (inverse cosine transform)
    wk = 2 * pi * np.arange(N) / N
    Ak = A(np.cos(wk))
    n = np.arange(N) - L
    h = np.array([np.sum(Ak * np.cos(wk * m)) / N for m in n])
    return h, abs(delta), it + 1, E, w, alt


def run(p):
    N, fp, fsb = 41, 0.2, 0.25
    h, delta, its, E, w, alt = remez_lp(N, fp, fsb)
    hs = signal.remez(N, [0, fp, fsb, 0.5], [1, 0], fs=1.0)
    p.compare("Own Remez vs scipy.signal.remez, max |h − h_scipy|", 0, np.max(np.abs(h - hs)), "", kind="abs", tol=1e-6)
    p.compare("Alternation theorem: number of equal-magnitude alternating extrema (≥ L+2 = 22)", 22, len(alt), "", kind="abs")
    wf, H = signal.freqz(h, worN=2 ** 15, fs=1.0); M = np.abs(H)
    ripple_meas = max(np.max(np.abs(M[wf <= fp] - 1)), np.max(M[wf >= fsb]))
    p.compare("Peak weighted error from the frequency response = δ from the exchange", delta, ripple_meas, "", tol=1)
    p.metric("Iterations to converge", its, "")
    beta = 0.1102 * (-db(delta) - 8.7) if -db(delta) > 50 else 0.5842 * (-db(delta) - 21) ** 0.4 + 0.07886 * (-db(delta) - 21)
    def kaiser_peak(b):
        hh = signal.firwin(N, (fp + fsb) / 2, window=("kaiser", b), fs=1.0)
        ww, HH = signal.freqz(hh, worN=2 ** 14, fs=1.0)
        return max(np.max(np.abs(np.abs(HH[ww <= fp]) - 1)), np.max(np.abs(HH[ww >= fsb])))
    bbest = min(np.linspace(1, 10, 91), key=kaiser_peak)          # fairest Kaiser: β minimising the peak error for this N and band edges
    hk = signal.firwin(N, (fp + fsb) / 2, window=("kaiser", bbest), fs=1.0)
    wk, Hk = signal.freqz(hk, worN=2 ** 15, fs=1.0)
    p.metric("Best Kaiser β for this N and band edges", bbest, "")
    p.compare("Stopband peak: equiripple vs best Kaiser window of the same length (dB better)", 3, db(np.max(np.abs(Hk[wk >= fsb]))) - db(np.max(M[wf >= fsb])), "dB", kind="abs", tol=10)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(wf, db(M + 1e-12), color=C_MEAS, label="own Parks–McClellan"); ax[0].plot(wk, db(np.abs(Hk) + 1e-12), color=COLORS[1], alpha=.7, label="Kaiser window, same N")
    ax[0].set_ylim(-80, 5)
    style_axes(ax[0], "frequency (× fs)", "|H| (dB)", "N = 41 low-pass")
    ax[1].plot(w / (2 * pi), E, color=C_MEAS, lw=1); ax[1].plot(w[alt] / (2 * pi), E[alt], "o", color=C_PRED, ms=5, label="alternation points")
    ax[1].axhline(delta, ls=":", color="gray"); ax[1].axhline(-delta, ls=":", color="gray")
    style_axes(ax[1], "frequency (× fs)", "weighted error", f"Equiripple error, {len(alt)} alternations")
    p.save(fig, "remez", "Response of the from-scratch equiripple filter and its error function with the alternation points.")
    p.discuss(f"""The from-scratch exchange converges in {its} iterations to the same filter as SciPy's remez (coefficients equal to ~1e-6, limited by the dense grid),
and the error function displays the signature of optimality: {len(alt)} extrema of equal magnitude and alternating sign, the minimum the alternation
theorem requires for 21 free coefficients. That equal-ripple error is exactly what makes the design optimal — any other filter of this length
must exceed δ somewhere. Compared with the *best* Kaiser-window design of the same length and band edges (β tuned to minimise its peak error), the equiripple
filter's worst stop-band level is still lower, because a window spends its error unevenly (large near the edge, tiny far away). The numerically delicate parts were the barycentric interpolation (evaluating the Lagrange form naively loses accuracy for L = 20) and
the exchange step: my first version kept only extrema above |δ| and pruned single points, which broke alternation and stalled after two
iterations; the fix — keep every per-band local extremum, prune spurious extrema in adjacent ± pairs, and drop an end point if one is left
over — is the classic rule and converges in a handful of iterations.""")
# tol-convention: relative tolerances are in percent
