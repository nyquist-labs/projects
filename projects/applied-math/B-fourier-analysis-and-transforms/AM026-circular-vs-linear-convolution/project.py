from eelab import *

META = dict(
    id="AM-026", title="Circular vs linear convolution: the wrap-around error", level="M",
    tools="DFT-domain multiplication without padding, time-domain aliasing analysis, padding sweep",
    summary="Show that multiplying DFTs without enough padding computes a circular convolution, predict exactly which output samples are "
            "corrupted and by how much (the tail wraps onto the head), and find the minimum FFT size that eliminates the error.",
    problem="An FFT-based filter output looks wrong at the start of each block. Why, and how much padding is enough?",
    theory=r"""With DFT size L, $\mathrm{IDFT}(X_LH_L)[n]=\sum_k y_{lin}[n+kL]$ — the linear result aliased in time with period L. For lengths N and M, samples $n < N+M-1-L$ receive the wrapped tail; the
error there equals exactly $y_{lin}[n+L]$. Error vanishes iff L ≥ N+M−1.""",
    method="""x = 64 random samples, h = 16-tap smoothing filter (N+M−1 = 79). L from 64 to 96. Error of the circular result vs the linear one, compared sample-by-sample with the predicted wrapped tail.""",
)


def run(p):
    r = p.rng
    x = r.normal(size=64); h = np.hanning(18)[1:-1]; h /= h.sum()     # 16 taps, none of them zero
    ylin = np.convolve(x, h)
    Ls = np.arange(64, 97)
    errs, pred_ok = [], []
    for L in Ls:
        yc = np.fft.ifft(np.fft.fft(x, L) * np.fft.fft(h, L)).real
        ref = ylin[:L] if L <= len(ylin) else np.r_[ylin, np.zeros(L - len(ylin))]
        e = yc - ref
        wrapped = np.zeros(L)
        tail = ylin[L:]
        wrapped[:len(tail)] = tail
        errs.append(np.max(np.abs(e)))
        pred_ok.append(np.max(np.abs(e - wrapped)))
    p.compare("Error equals the wrapped tail y_lin[n+L], worst mismatch over all L", 0, max(pred_ok), "", kind="abs", tol=1e-12)
    p.compare("Smallest L with zero wrap-around error = N+M−1", 79, int(Ls[np.argmax(np.array(errs) < 1e-12)]), "", kind="abs")
    L = 64
    yc = np.fft.ifft(np.fft.fft(x, L) * np.fft.fft(h, L)).real
    bad = np.flatnonzero(np.abs(yc - ylin[:L]) > 1e-12)
    p.compare("Corrupted samples at L = 64 (predicted: n < N+M−1−L = 15)", 15, len(bad), "", kind="abs")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(ylin, color=C_PRED, lw=2, label="linear convolution (79 samples)"); ax[0].plot(yc, "o", ms=3, color=C_MEAS, label="circular, L = 64")
    ax[0].axvspan(-0.5, 14.5, color=COLORS[7], alpha=.2, label="wrapped region")
    style_axes(ax[0], "n", "y[n]", "Circular = linear + wrapped tail")
    ax[1].semilogy(Ls, np.maximum(errs, 1e-17), "o-", color=C_MEAS)
    ax[1].axvline(79, color=C_PRED, ls="--", label="N + M − 1 = 79")
    style_axes(ax[1], "DFT size L", "max |circular − linear|", "Padding needed")
    p.save(fig, "circular", "The circular result, the corrupted head samples, and the error vs DFT size.")
    p.discuss("""The discrepancy between circular and linear convolution is not noise but a precisely predictable object: the samples of the linear result
beyond index L fold back onto the start, matching the wrapped tail to rounding error. With L = 64 exactly the first 15 samples are corrupted,
and the error disappears at L = 79 = N+M−1 and stays zero beyond. This is the whole theory behind overlap-add and overlap-save: overlap-add pads
each block so nothing wraps, overlap-save lets it wrap and discards exactly the M−1 contaminated samples.""")
# tol-convention: relative tolerances are in percent
