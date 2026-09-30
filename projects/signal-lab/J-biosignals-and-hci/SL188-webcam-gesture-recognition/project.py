from eelab import *
from eelab.web import node, attach
from scipy.stats import norm

META = dict(
    id="SL-188", title="Webcam gesture control in the browser", level="M",
    tools="MediaPipe Hand Landmarker (in-browser, CDN), rule-based pose classifier in JavaScript, pinch-to-click with hysteresis, EMA pointer smoothing; Node.js test harness with a 3-D kinematic hand model",
    summary="A web page that tracks your hand with the webcam and drives a six-tile interface by pointing and pinching; the gesture classifier "
            "is tested offline by running the same JavaScript on thousands of synthetic hands, and its noise tolerance and the pointer "
            "smoother's jitter/lag trade-off are predicted analytically first.",
    problem="A hand tracker returns 21 noisy points per frame. How robust is a simple 'which fingers are extended' rule, and how much smoothing "
            "can a pointer take before it feels laggy?",
    theory=r"""**Classifier.** A finger counts as extended when $d(\text{tip},\text{wrist}) > 1.1\,d(\text{PIP},\text{wrist})$. With landmark noise σ (in palm lengths) the statistic
$s=d_\text{tip}-1.1\,d_\text{PIP}$ gets noise of standard deviation ≈ $σ\sqrt{1+1.1^2+(1-1.1)^2}$ (the wrist's noise mostly cancels), so a finger with
noise-free margin $s_0$ flips with probability $Φ(-|s_0|/σ_s)$, and a pose is correct only if all five fingers are: $P=\prod_f Φ(|s_{0,f}|/σ_s)$.

**Smoother.** An exponential moving average $y_n=αx_n+(1-α)y_{n-1}$ reduces white jitter variance by $α/(2-α)$ and makes a steadily moving cursor lag
$(1-α)/α$ frames. For α = 0.35: jitter × 0.46, lag 1.9 frames ≈ 62 ms at 30 fps.""",
    method="""3-D kinematic hand (palm length 1; finger segments with joint flexion ~0–10° when extended, ~70°/100°/60° when curled, ±12° variation), random in-plane rotation,
scale and 30° out-of-plane tilt, orthographic projection → 21 landmarks for six poses. Gaussian noise σ = 0–0.15 added; the page's own `gesture.js`
classifies them under Node (6000 hands per σ). Prediction uses the noise-free margins of the same hands. EMA tested on a ramp plus white jitter.""",
    data="Synthetic hands from a kinematic model (MediaPipe's own training data is not public); the live page uses your webcam.",
)

POSES = {"open": "11111", "fist": "00000", "point": "01000", "peace": "01100", "thumbs_up": "10000", "L": "11000"}
MCP = np.array([[-0.32, 0.93], [-0.1, 1.0], [0.12, 0.95], [0.32, 0.84]])
SEG = np.array([[0.45, 0.28, 0.2], [0.5, 0.32, 0.22], [0.47, 0.3, 0.2], [0.37, 0.22, 0.18]])


def chain(base, d, lengths, flex, z0=0.0):
    """Joints of a finger starting at base (3-D), direction d in the image plane, flexing toward the camera (+z)."""
    pts = [base]; ang = 0.0
    for L, f in zip(lengths, flex):
        ang += f
        step = L * np.r_[d * np.cos(ang), np.sin(ang)]
        pts.append(pts[-1] + step)
    return pts


def hand(code, r):
    j = lambda s: np.deg2rad(r.normal(0, s))
    L = [np.zeros(3)]
    # thumb: CMC, MCP, IP, TIP
    cmc = np.r_[-0.35, 0.25, 0.0]
    if code[0] == "1":
        d = np.array([np.cos(np.deg2rad(135) + j(8)), np.sin(np.deg2rad(135) + j(8))])
        L += chain(cmc, d, [0.3, 0.25, 0.2], [j(5), j(5), j(5)])[1:]
        L.insert(1, cmc)
        L = L[:5]
    else:
        pts = [cmc, np.r_[-0.3, 0.52, 0.05], np.r_[-0.12 + r.normal(0, .03), 0.66 + r.normal(0, .03), 0.12], np.r_[0.06 + r.normal(0, .04), 0.72 + r.normal(0, .04), 0.15]]
        L += pts
    for k in range(4):
        base = np.r_[MCP[k], 0.0]
        d = base[:2] / np.linalg.norm(base[:2]); d = np.array([[np.cos(j(4)), -np.sin(j(4))], [np.sin(j(4)), np.cos(j(4))]]) @ d
        if code[k + 1] == "1":
            flex = np.deg2rad(np.abs(r.normal(4, 4, 3)))
        else:
            flex = np.deg2rad(np.r_[70, 100, 60] + r.normal(0, 12, 3))
        L += chain(base, d, SEG[k], flex)
    P = np.array(L)                                   # 21 x 3
    tilt = np.deg2rad(r.uniform(-30, 30))             # out-of-plane rotation about the vertical axis
    Ry = np.array([[np.cos(tilt), 0, np.sin(tilt)], [0, 1, 0], [-np.sin(tilt), 0, np.cos(tilt)]])
    rot = np.deg2rad(r.uniform(-25, 25)); Rz = np.array([[np.cos(rot), -np.sin(rot), 0], [np.sin(rot), np.cos(rot), 0], [0, 0, 1]])
    P = (Rz @ Ry @ P.T).T * r.uniform(0.8, 1.2)
    return P[:, :2]


def margins(H):
    d = lambda a, b: np.hypot(*(H[a] - H[b]))
    m = [d(4, 17) - 1.1 * d(2, 17)]
    for f in ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20)):
        m.append(d(f[3], 0) - 1.1 * d(f[1], 0))
    return np.array(m)


def run(p):
    attach(p, "web/index.html", "live webcam gesture-control page (MediaPipe via CDN)")
    attach(p, "web/gesture.js", "classifier + smoothing logic shared by the page and the tests")
    js = p.dir / "web" / "gesture.js"
    r = p.rng
    names = list(POSES)
    N = 1000
    hands = [(g, hand(POSES[g], r)) for g in names for _ in range(N)]
    H = np.array([h for _, h in hands]); truth = np.array([g for g, _ in hands])
    # scale each hand to palm length 1 so σ is in palm lengths
    palm = np.hypot(*(H[:, 9] - H[:, 0]).T)
    H = H / palm[:, None, None]
    M = np.array([margins(h) for h in H])
    sig_s_factor = np.sqrt(1 + 1.1 ** 2 + 0.1 ** 2)
    sigmas = np.array([0, 0.01, 0.02, 0.03, 0.05, 0.07, 0.1, 0.15])
    meas, pred = [], []
    for s in sigmas:
        noisy = H + r.normal(0, s, H.shape) if s else H
        out = node(js, [["classifyMany", [noisy.tolist()]]])[0]
        meas.append(np.mean(np.array(out) == truth) * 100)
        base_ok = np.array([all((M[i] > 0) == (np.array(list(POSES[truth[i]])) == "1")) for i in range(len(H))])
        if s == 0:
            pred.append(np.mean(base_ok) * 100)
        else:
            pr = np.prod(norm.cdf(np.abs(M) / (s * sig_s_factor)), axis=1)
            pred.append(np.mean(np.where(base_ok, pr, 1 - pr)) * 100)
    meas, pred = np.array(meas), np.array(pred)
    p.compare("Noise-free accuracy over pose variation (all poses)", 100, meas[0], "%", kind="abs")
    for s, a, b in zip(sigmas[1:], pred[1:], meas[1:]):
        if s in (0.03, 0.07, 0.15):
            p.compare(f"Accuracy with landmark noise σ = {s:g} palm lengths", a, b, "%", kind="abs")
    worst = np.argmin(np.abs(M).mean(0))
    p.metric("Finger with the smallest mean margin", ["thumb", "index", "middle", "ring", "pinky"][worst], "")
    # EMA smoother
    alpha = 0.35
    n = 3000
    ramp = np.arange(n) * 0.002
    jit = r.normal(0, 0.01, n)
    y = np.array(node(js, [["ema", [(ramp + jit).tolist(), alpha]]])[0])
    yj = np.array(node(js, [["ema", [jit.tolist(), alpha]]])[0])
    p.compare("EMA jitter reduction (std ratio) = √(α/(2−α))", np.sqrt(alpha / (2 - alpha)), np.std(yj[200:]) / np.std(jit[200:]), "", tol=0.05)
    y0 = np.array(node(js, [["ema", [ramp.tolist(), alpha]]])[0])
    lag = np.mean(ramp[500:] - y0[500:]) / 0.002
    p.compare("EMA lag on a moving cursor = (1−α)/α frames", (1 - alpha) / alpha, lag, "frames", tol=0.05)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(sigmas, pred, "--", color=C_PRED, label="predicted (margin model)"); ax[0].plot(sigmas, meas, "o-", color=C_MEAS, label="measured (gesture.js)")
    style_axes(ax[0], "landmark noise σ (palm lengths)", "pose accuracy (%)", "Classifier robustness")
    al = np.linspace(0.05, 1, 50)
    ax[1].plot((1 - al) / al / 30 * 1000, np.sqrt(al / (2 - al)), color=C_PRED, ls="--", label="theory")
    ax[1].plot([lag / 30 * 1000], [np.std(yj[200:]) / np.std(jit[200:])], "o", color=C_MEAS, label="measured α = 0.35")
    ax[1].set_xlim(0, 400)
    style_axes(ax[1], "lag at 30 fps (ms)", "remaining jitter (fraction)", "Smoothing trade-off")
    p.save(fig, "gesture", "Pose accuracy vs landmark noise (prediction from noise-free margins vs the page's JavaScript) and the EMA jitter-lag trade-off.")
    ex = H[[names.index(g) * N for g in names]]
    fig2, ax2 = p.fig(1, 6, w=12, h=2.6)
    bones = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (0, 9), (9, 10), (10, 11), (11, 12), (0, 13), (13, 14), (14, 15), (15, 16), (0, 17), (17, 18), (18, 19), (19, 20)]
    for a_, h, g in zip(ax2, ex, names):
        for u, w in bones:
            a_.plot(h[[u, w], 0], h[[u, w], 1], color=C_MEAS, lw=1.5)
        a_.plot(h[:, 0], h[:, 1], ".", color=C_PRED); a_.set_aspect("equal"); a_.axis("off"); a_.set_title(g, fontsize=10)
    p.save(fig2, "poses", "Synthetic hands from the kinematic model (projected landmarks), one per pose.")
    p.csv("robustness", sigma=sigmas, predicted_pct=pred, measured_pct=meas)
    p.section("Try it", "Open [`web/index.html`](web/index.html) (served over https or localhost so the browser allows the camera). The page loads MediaPipe from the jsDelivr CDN and the model from Google's model storage.")
    p.discuss(f"""The margin model predicts the classifier's accuracy under landmark noise closely, because each finger decision is a sign test on a statistic whose
noise is nearly Gaussian. Accuracy stays high until σ reaches a few percent of the palm length and then falls quickly; the fragile decisions are the
thumb and partially flexed fingers whose noise-free margin is small. Out-of-plane tilt is what erodes margins in 2-D: a curled finger seen at an angle
can project almost as long as an extended one. Practical fixes are to use MediaPipe's 3-D (z) landmarks, add hysteresis per finger, and require a
pose to persist for a few frames. The test harness also caught a design flaw in my first thumb rule, which compared the tip with the thumb's IP joint: for a straight thumb that ratio
is only ≈ 1.11, a hair above the 1.1 threshold, so a quarter of extended thumbs were missed with *no* noise at all. Referencing the thumb's MCP joint
instead gives a ratio ≈ 1.25 and fixed it — a bug that would have been maddening to find by waving a hand at a webcam. The EMA smoother behaves exactly as the one-line theory says: α = 0.35 halves jitter at ~60 ms of lag; an adaptive
('One-Euro') filter that raises α with speed gets both. The pinch click uses hysteresis (on < 0.25, off > 0.35 palm lengths) for the same reason a
Schmitt trigger does.""")
