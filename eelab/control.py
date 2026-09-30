"""Small control-systems helpers (transfer functions as numerator/denominator arrays)."""
import numpy as np
from scipy import signal


def step_info(t, y, yf=None):
    yf = y[-1] if yf is None else yf
    os_ = max(0.0, (np.max(y) - yf) / abs(yf) * 100)
    i10 = np.argmax(y >= 0.1 * yf); i90 = np.argmax(y >= 0.9 * yf)
    out = np.abs(y - yf) > 0.02 * abs(yf)
    ts = t[np.flatnonzero(out)[-1] + 1] if out.any() and np.flatnonzero(out)[-1] + 1 < len(t) else t[0]
    return dict(overshoot=os_, rise=t[i90] - t[i10], settle=ts, final=yf)


def feedback(num_ol, den_ol):
    num = np.atleast_1d(num_ol); den = np.atleast_1d(den_ol)
    n = max(len(num), len(den))
    num_p = np.pad(num, (n - len(num), 0)); den_p = np.pad(den, (n - len(den), 0))
    return num, np.polyadd(den_p, num_p)


def margins(num, den, w=None):
    w = np.logspace(-3, 4, 200000) if w is None else w
    _, H = signal.freqs(num, den, worN=w)
    mag, ph = np.abs(H), np.unwrap(np.angle(H))
    gm = pm = wgc = wpc = np.nan
    i = np.flatnonzero(np.diff(np.sign(mag - 1)))
    if len(i):
        k = i[0]; wgc = w[k]; pm = 180 + np.degrees(ph[k])
    j = np.flatnonzero(np.diff(np.sign(np.degrees(ph) + 180)))
    if len(j):
        k = j[0]; wpc = w[k]; gm = -20 * np.log10(mag[k])
    return dict(gm_db=gm, pm_deg=pm, wgc=wgc, wpc=wpc)


def zoh(A, B, dt):
    """Exact zero-order-hold discretisation x[k+1] = Ad x[k] + Bd u[k]."""
    from scipy.linalg import expm
    A = np.atleast_2d(A); B = np.atleast_2d(B).reshape(A.shape[0], -1)
    n, m = A.shape[0], B.shape[1]
    M = np.zeros((n + m, n + m)); M[:n, :n] = A; M[:n, n:] = B
    E = expm(M * dt)
    return E[:n, :n], E[:n, n:]


def loop_with_delay(num, den, delay, t_end, dt=1e-3, r=1.0):
    """Unity-feedback loop around L(s) = num/den with a pure time delay in the loop, simulated in the time domain:
    exact ZOH stepping of the plant, the error delayed by round(delay/dt) samples. Returns (t, y)."""
    from scipy import signal
    A, B, C, D = signal.tf2ss(num, den)
    Ad, Bd = zoh(A, B, dt)
    nd = int(round(delay / dt)); n = int(round(t_end / dt))
    x = np.zeros(A.shape[0]); buf = np.zeros(nd + 1); y = np.zeros(n)
    Bd = Bd[:, 0]; C = C[0]
    for k in range(n):
        y[k] = C @ x
        buf[k % (nd + 1)] = r - y[k]
        u = buf[(k - nd) % (nd + 1)] if k >= nd else 0.0
        x = Ad @ x + Bd * u
    return np.arange(n) * dt, y


def exact_margins(num, den):
    """Gain/phase margins by root finding on the frequency response (first crossings)."""
    from scipy.optimize import brentq
    L = lambda w: np.polyval(num, 1j * w) / np.polyval(den, 1j * w)
    w = np.logspace(-3, 4, 20000); H = L(w); mag = np.abs(H); ph = np.unwrap(np.angle(H))
    out = dict(gm=np.inf, pm=np.inf, wgc=np.nan, wpc=np.nan)
    i = np.flatnonzero(np.diff(np.sign(mag - 1)))
    if len(i):
        wg = brentq(lambda x: abs(L(x)) - 1, w[i[0]], w[i[0] + 1]); k = i[0]
        out["wgc"] = wg; out["pm"] = 180 + np.degrees(ph[k] + (np.angle(L(wg)) - np.angle(H[k])))
    j = np.flatnonzero(np.diff(np.sign(ph + np.pi)))
    if len(j):
        k = j[0]
        wp = brentq(lambda x: np.imag(L(x)), w[k], w[k + 1])
        out["wpc"] = wp; out["gm"] = 1 / abs(L(wp))
    return out
