from eelab import *

META = dict(
    id="SL-064", title="Convolution visualiser", level="E",
    tools="NumPy, Matplotlib frame sequence + animated GIF",
    summary="Animate the flip-slide-multiply-sum picture of discrete convolution, verify it equals "
            "numpy.convolve and FFT multiplication, and export the animation.",
    problem="Convolution is the operation behind every filter, yet its formula hides a simple picture. "
            "Make the picture and prove it computes the same thing.",
    theory=r"""$y[n]=\sum_k x[k]\,h[n-k]$: flip h, slide it to offset n, multiply overlapping samples, sum. Output length
$N_x+N_h-1$. Convolution theorem: $Y = X\cdot H$ with FFTs of length ≥ $N_x+N_h-1$ (otherwise circular wraparound).""",
    method="""x = a 12-sample pulse train, h = a 6-tap decaying exponential. Frame-by-frame sliding computation
(explicit Python loop), numpy.convolve, and zero-padded FFT product; max differences reported. 18 frames
exported as an animated GIF; four key frames shown as a figure.""",
)


def run(p):
    x = np.array([0, 1, 1, 1, 0, 0, 2, 2, 0, 0, -1, 0], float)
    h = 0.6 ** np.arange(6)
    Nx, Nh = len(x), len(h)
    L = Nx + Nh - 1
    y_loop = np.zeros(L)
    frames = []
    for n in range(L):
        prod = np.zeros(Nx)
        for k in range(Nx):
            if 0 <= n - k < Nh:
                prod[k] = x[k] * h[n - k]
        y_loop[n] = prod.sum()
        frames.append(prod)
    y_np = np.convolve(x, h)
    y_fft = np.real(np.fft.ifft(np.fft.fft(x, L) * np.fft.fft(h, L)))
    y_circ = np.real(np.fft.ifft(np.fft.fft(x, Nx) * np.fft.fft(h, Nx)))
    p.compare("Output length", Nx + Nh - 1, len(y_loop), "", kind="abs")
    p.compare("Sliding sum vs numpy.convolve (max |Δ|)", 0, np.max(abs(y_loop - y_np)), "", kind="abs")
    p.compare("Sliding sum vs FFT product, zero-padded (max |Δ|)", 0, np.max(abs(y_loop - y_fft)), "", kind="abs")
    aliased = y_np[:Nx] + np.r_[y_np[Nx:], np.zeros(Nx - (L - Nx))]
    p.metric("FFT product WITHOUT padding: error vs true convolution", np.max(abs(y_circ - y_np[:Nx])), "", "the tail wraps onto the start")
    p.compare("Unpadded result = linear result + wrapped tail (max |Δ|)", 0, np.max(abs(y_circ - aliased)), "", kind="abs")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
    fig, axs = plt.subplots(2, 1, figsize=(7.6, 5))
    def draw(n):
        for a in axs:
            a.cla()
        ks = np.arange(Nx)
        axs[0].stem(ks, x, linefmt=C_MEAS, markerfmt="o", basefmt="gray", label="x[k]")
        hk = np.array([h[n - k] if 0 <= n - k < Nh else np.nan for k in ks])
        kk = np.arange(n - Nh + 1, n + 1)
        axs[0].plot(kk, h[::-1], "s--", color=C_PRED, label=f"h[{n}−k] (flipped, shifted)")
        axs[0].bar(ks, frames[n], color=COLORS[2], alpha=.35, label="products")
        axs[0].set_xlim(-6, L); axs[0].set_ylim(-1.2, 2.3); axs[0].legend(loc="upper right", fontsize=8)
        axs[0].set_title(f"n = {n}: y[n] = Σ products = {y_loop[n]:.3f}", loc="left")
        axs[1].stem(np.arange(n + 1), y_loop[: n + 1], linefmt=C_MEAS, markerfmt="o", basefmt="gray")
        axs[1].set_xlim(-6, L); axs[1].set_ylim(-1.5, 3.5); axs[1].set_title("output y[n] so far", loc="left")
    anim = FuncAnimation(fig, draw, frames=L, interval=450)
    (p.dir / "figures").mkdir(exist_ok=True)
    anim.save(p.dir / "figures" / "convolution.gif", writer=PillowWriter(fps=2))
    plt.close(fig)
    p.files.append(("figures/convolution.gif", "animated flip-slide-sum"))
    fig, axs = p.fig(2, 2, w=10, h=6)
    for a, n in zip(np.ravel(axs), [2, 6, 9, 14]):
        a.stem(np.arange(Nx), x, linefmt=C_MEAS, markerfmt="o", basefmt="gray")
        a.plot(np.arange(n - Nh + 1, n + 1), h[::-1], "s--", color=C_PRED)
        a.bar(np.arange(Nx), frames[n], color=COLORS[2], alpha=.35)
        a.set_xlim(-6, L); a.set_title(f"n = {n}: y = {y_loop[n]:.2f}", loc="left")
    p.save(fig, "key_frames", "Flip h, slide it to n, multiply the overlap and sum — four snapshots.")
    p.section("Animation", "![convolution animation](figures/convolution.gif)")
    p.csv("convolution", n=np.arange(L), y_sliding=y_loop, y_numpy=y_np, y_fft=y_fft)
    p.discuss("""The three methods agree to machine precision, confirming the picture is the definition. Dropping the
zero-padding shows the classic FFT pitfall: an N-point FFT computes *circular* convolution, so the tail
of the output wraps around onto its start — which is exactly what overlap-add/overlap-save (AM-027) are
designed to avoid.""")
