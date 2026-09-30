from eelab import *
from scipy import signal

META = dict(
    id="AM-125", title="Quantisation noise through a filter cascade: ordering matters", level="H",
    tools="Bit-true direct-form-I biquad cascade with the accumulator rounded to Q15 inside each recursion, L∞ scaling between sections for every ordering, noise-gain prediction from each rounding point to the output, all 24 orderings of four sections simulated in parallel",
    summary="Implement an 8th-order narrow band-pass as four fixed-point biquads, scale each ordering so that no internal node can overflow on a sine wave, "
            "predict the output round-off noise from the noise gains, verify all 24 section orderings against a bit-true simulation, and measure how much the ordering alone changes the noise.",
    problem="Same filter, same word length — why does re-ordering the sections change the output noise?",
    theory=r"""Rounding the accumulator of section k injects white noise of variance q²/12 *inside* its recursion, so it reaches the output through $1/A_k(z)$ and all later (scaled) sections: $σ^2=\frac{q^2}{12}\sum_k\|\,\tfrac{1}{A_k}\prod_{j>k}s_jH_j\|_2^2$.
The scale factors $s_j$ are forced by overflow: the response from the input to every section output must not exceed 1 (L∞ scaling). Ordering changes both the scale factors and what each noise source sees downstream, so the output noise depends on the order
even though the overall transfer function does not. Rule of thumb (Jackson): order sections by increasing pole radius — the peakiest section last.""",
    method="""8th-order elliptic band-pass (0.19–0.21 fs) → 4 SOS. For each of the 24 orderings: L∞ scaling of the partial cascades, then a bit-true simulation (rounding to 2⁻¹⁵ in every recursion) of 2¹⁷ samples of white noise at −26 dBFS against the same scaled
cascade in float64. Predicted σ² from 60 000-sample impulse responses.""",
)


def run(p):
    from itertools import permutations
    sos0 = signal.ellip(4, 0.5, 60, [0.38, 0.42], btype="band", output="sos")
    q = 2.0 ** -15
    r = p.rng; N = 1 << 17
    x = np.round(r.normal(0, 0.05, N) / q) * q
    perms = list(permutations(range(4))); P = len(perms)
    wz = np.linspace(0, pi, 1 << 14)
    SC = np.zeros((P, 4, 6)); pred = np.zeros(P)
    imp = np.zeros(60000); imp[0] = 1
    for i, perm in enumerate(perms):
        S = sos0[list(perm)].copy(); Hc = np.ones(len(wz), complex)
        for k in range(4):                                     # L∞ scaling: peak of the input → section-k-output response = 1
            Hk = signal.sosfreqz(S[k:k + 1], worN=wz)[1]
            s_k = 1 / np.abs(Hc * Hk).max(); S[k, :3] *= s_k; Hc = Hc * Hk * s_k
        SC[i] = S
        for k in range(4):
            g = signal.lfilter([1.0], S[k, 3:], imp)
            if k < 3:
                g = signal.sosfilt(S[k + 1:], g)
            pred[i] += np.sum(g ** 2)
    pred *= q * q / 12
    # bit-true DF1 cascade, all orderings advanced together
    b0, b1, b2, a1, a2 = (SC[:, :, j].copy() for j in (0, 1, 2, 4, 5))
    x1 = np.zeros((P, 4)); x2 = np.zeros((P, 4)); y1 = np.zeros((P, 4)); y2 = np.zeros((P, 4)); out = np.zeros((P, N))
    for n in range(N):
        v = np.full(P, x[n])
        for k in range(4):
            acc = b0[:, k] * v + b1[:, k] * x1[:, k] + b2[:, k] * x2[:, k] - a1[:, k] * y1[:, k] - a2[:, k] * y2[:, k]
            yq = np.round(acc / q) * q
            x2[:, k] = x1[:, k]; x1[:, k] = v; y2[:, k] = y1[:, k]; y1[:, k] = yq; v = yq
        out[:, n] = v
    ideal = np.array([signal.sosfilt(SC[i], x) for i in range(P)])
    meas = np.var(out[:, 5000:] - ideal[:, 5000:], axis=1)
    p.compare("Predicted vs measured output noise, worst ratio over all 24 orderings", 1.0, np.max(np.maximum(meas / pred, pred / meas)), "", tol=30)
    best, worst = int(np.argmin(meas)), int(np.argmax(meas))
    sp_meas = 10 * np.log10(meas[worst] / meas[best]); sp_pred = 10 * np.log10(pred.max() / pred.min())
    p.compare("Spread between best and worst ordering: bit-true simulation vs noise-gain model", sp_pred, sp_meas, "dB", kind="abs", tol=1.5)
    p.compare("The model picks the same best ordering as the simulation (1 = yes)", 1, int(np.argmin(pred) == best), "", kind="abs")
    rad = np.array([abs(np.roots(s_[3:])[0]) for s_ in sos0])
    p.metric("Section pole radii (sections 0…3)", ", ".join(f"{v:.4f}" for v in rad))
    p.metric("Best / worst ordering (section indices)", f"{perms[best]} / {perms[worst]}")
    jackson = tuple(int(i) for i in np.argsort(rad))
    jm = meas[perms.index(jackson)]
    p.metric("Rule of thumb 'increasing pole radius' ordering: noise relative to the best", 10 * np.log10(jm / meas[best]), "dB", f"ordering {jackson}")
    p.metric("Output noise of the best ordering, in units of q²/12", meas[best] / (q * q / 12), "", "i.e. the noise gain of the whole structure")
    p.csv("orderings", ordering=[" ".join(map(str, pm)) for pm in perms], predicted_var=pred, measured_var=meas)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].loglog(pred, meas, "o", color=C_MEAS); m = [pred.min(), pred.max()]; ax[0].plot(m, m, "--", color=C_PRED, label="measured = predicted")
    style_axes(ax[0], "predicted noise variance", "measured noise variance (bit-true)", "All 24 section orderings")
    o = np.argsort(meas)
    ax[1].bar(range(24), 10 * np.log10(meas[o] / meas.min()), color=C_MEAS)
    style_axes(ax[1], "ordering (sorted)", "output noise relative to best (dB)", "Same filter, different order", legend=False)
    p.save(fig, "cascade_noise", "Predicted vs measured round-off noise for every ordering of the four sections.")
    p.discuss(f"""The noise-gain model matches the bit-true simulation for every ordering, and re-arranging the same four sections changes the output round-off noise by
{sp_meas:.1f} dB (the model says {sp_pred:.1f} dB) — {sp_meas / 6.02:.1f} bits of word length for free. The first version of this project got this badly wrong in an
instructive way: it rounded only each section's *output* and scaled every section to unit peak gain independently, and found a spread of 0.1 dB —
no ordering effect at all. The effect appears only when the model is faithful to a real fixed-point filter: the rounding happens inside the
recursion, so each noise source is amplified by its own poles (enormously, for pole radii close to 1), and the inter-section scale factors needed to
prevent overflow depend on the order. The best ordering here is {perms[best]}; the classical 'peakiest section last' rule lands within
{10 * np.log10(jm / meas[best]):.1f} dB of it. This is why tools such as zpk2sos pair poles with zeros and order sections deliberately.""")
# tol-convention: relative tolerances are in percent
