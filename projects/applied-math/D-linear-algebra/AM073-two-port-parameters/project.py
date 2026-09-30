from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-073", title="Two-port parameters: Z, Y and S matrices", level="M",
    tools="Two-port extraction by AC simulation (test sources at each port), Z↔Y↔S conversions, reciprocity and losslessness checks",
    summary="Extract the Z and Y matrices of a π-network and an LC filter by simulating test excitations, convert them to scattering parameters, "
            "and verify the identities that must hold: Y = Z⁻¹, reciprocity (S₁₂ = S₂₁) and, for lossless networks, SᴴS = I.",
    problem="A two-port is fully described by a 2×2 matrix — but which one, and how do they relate?",
    theory=r"""Z: v = Zi (open-circuit tests), Y = Z⁻¹ (short-circuit tests). With reference impedance Z0: $S=(Z-Z_0I)(Z+Z_0I)^{-1}$ (normalised). Reciprocal (passive, no ferrites) networks have Z₁₂ = Z₂₁ ⇒ S₁₂ = S₂₁;
lossless networks have unitary S: $|S_{11}|^2+|S_{21}|^2=1$ at every frequency. For a symmetric π-network the analytic Y is $[[Y_a+Y_c, -Y_c], [-Y_c, Y_b+Y_c]]$.""",
    method="""π-network: shunt 100 Ω, series 50 Ω + 1 µH, shunt 200 Ω || 1 nF, at 1–100 MHz. LC: 3rd-order Butterworth low-pass (50 Ω, 30 MHz), lossless. Z from two open-circuit simulations (1 A into each port),
Y from two short-circuit simulations (1 V at each port); S from Z.""",
)


def zparams(build, f):
    Z = np.zeros((len(f), 2, 2), complex)
    for k, port in enumerate(("p1", "p2")):
        ck = build(); ck.I("t", "0", port, ac=1.0); ck.R("open1", "p1", "0", 1e12); ck.R("open2", "p2", "0", 1e12)
        ac = ck.ac(f); Z[:, 0, k] = ac.v("p1"); Z[:, 1, k] = ac.v("p2")
    return Z


def yparams(build, f):
    Y = np.zeros((len(f), 2, 2), complex)
    for k, (port, other) in enumerate((("p1", "p2"), ("p2", "p1"))):
        ck = build(); ck.V("t", port, "0", ac=1.0); ck.V("s", other, "0", ac=0.0)
        ac = ck.ac(f)
        cur = {port: -ac.i("t"), other: -ac.i("s")}
        Y[:, 0, k] = cur["p1"]; Y[:, 1, k] = cur["p2"]
    return Y


def pi_net():
    ck = Circuit("pi"); ck.R("a", "p1", "0", 100.0); ck.R("c", "p1", "m", 50.0); ck.L("c", "m", "p2", 1e-6); ck.R("b", "p2", "0", 200.0); ck.C("b", "p2", "0", 1e-9)
    return ck


def lc_net():
    w = 2 * pi * 30e6; ck = Circuit("lc")
    ck.C("1", "p1", "0", 1 / (50 * w)); ck.L("2", "p1", "p2", 2 * 50 / w); ck.C("3", "p2", "0", 1 / (50 * w))
    return ck


def s_from_z(Z, Z0=50.0):
    I = np.eye(2)
    return np.array([(z - Z0 * I) @ np.linalg.inv(z + Z0 * I) for z in Z])


def run(p):
    f = np.logspace(6, 8, 200); w = 2 * pi * f
    Z = zparams(pi_net, f); Y = yparams(pi_net, f)
    p.compare("π-network: Y from short-circuit tests = inverse of Z from open-circuit tests (worst relative)", 0,
              max(np.max(np.abs(Y[k] - np.linalg.inv(Z[k]))) / np.max(np.abs(Y[k])) for k in range(len(f))), "", kind="abs", tol=1e-6)
    Ya, Yb, Yc = 1 / 100, 1 / 200 + 1j * w * 1e-9, 1 / (50 + 1j * w * 1e-6)
    Yan = np.array([[[ya + yc, -yc], [-yc, yb + yc]] for ya, yb, yc in zip(np.full_like(w, Ya), Yb, Yc)])
    p.compare("π-network: simulated Y vs analytic [[Ya+Yc, −Yc], [−Yc, Yb+Yc]] (worst relative)", 0, np.max(np.abs(Y - Yan)) / np.max(np.abs(Yan)), "", kind="abs", tol=1e-6)
    S = s_from_z(Z)
    p.compare("Reciprocity: max |S₁₂ − S₂₁|", 0, np.max(np.abs(S[:, 0, 1] - S[:, 1, 0])), "", kind="abs", tol=1e-9)
    loss = 1 - np.abs(S[:, 0, 0]) ** 2 - np.abs(S[:, 1, 0]) ** 2
    p.metric("π-network power absorbed (1 − |S11|² − |S21|²) range", f"{loss.min():.3f} – {loss.max():.3f}", "", "resistive: > 0")
    Zl = zparams(lc_net, f); Sl = s_from_z(Zl)
    p.compare("Lossless LC filter: max |SᴴS − I| (unitary)", 0, max(np.max(np.abs(s.conj().T @ s - np.eye(2))) for s in Sl), "", kind="abs", tol=1e-6)
    k30 = np.argmin(abs(f - 30e6))
    p.compare("Butterworth LC at its cutoff: |S21| = −3 dB", -3.0103, db(abs(Sl[k30, 1, 0])), "dB", kind="abs", tol=0.05)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogx(f, db(np.abs(Sl[:, 1, 0])), color=C_MEAS, label="|S21|"); ax[0].semilogx(f, db(np.abs(Sl[:, 0, 0]) + 1e-12), color=C_PRED, label="|S11|")
    style_axes(ax[0], "frequency (Hz)", "dB", "Lossless LC low-pass: |S11|² + |S21|² = 1")
    ax[1].semilogx(f, np.abs(Sl[:, 0, 0]) ** 2 + np.abs(Sl[:, 1, 0]) ** 2, color=C_MEAS, label="LC (lossless)"); ax[1].semilogx(f, np.abs(S[:, 0, 0]) ** 2 + np.abs(S[:, 1, 0]) ** 2, color=COLORS[2], label="π-network (resistive)")
    ax[1].set_ylim(0, 1.1)
    style_axes(ax[1], "frequency (Hz)", "|S11|² + |S21|²", "Power conservation")
    p.save(fig, "twoport", "S-parameters of the lossless LC filter and the power balance of both networks.")
    p.discuss("""Open-circuit and short-circuit experiments give Z and Y independently, and Y equals Z⁻¹ to simulator precision; the π-network's Y also matches its
by-inspection formula. Converting to S makes the physics visible: both networks are reciprocal (S₁₂ = S₂₁ to 1e-12, as any network of R, L, C must
be), the LC filter's S matrix is unitary at every frequency — reflected plus transmitted power equals incident power — and at 30 MHz it passes
exactly half. The resistive π-network absorbs power, so |S11|² + |S21|² < 1. S-parameters are preferred at RF because they are measured with
matched loads rather than opens and shorts, which high-frequency parasitics make impossible to realise.""")
# tol-convention: relative tolerances are in percent
