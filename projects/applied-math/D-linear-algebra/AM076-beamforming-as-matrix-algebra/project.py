from eelab import *

META = dict(
    id="AM-076", title="Beamforming as matrix algebra: delay-and-sum vs MVDR", level="H",
    tools="Uniform linear array steering vectors, sample covariance, delay-and-sum and minimum-variance distortionless-response (MVDR/Capon) weights, SINR and pattern measurements",
    summary="Form beams with an 8-element array by choosing weight vectors: delay-and-sum gains N in SNR, MVDR solves a constrained quadratic "
            "optimisation that places nulls on interferers. Predicted SINR gains are compared with Monte-Carlo measurements.",
    problem="Eight antennas, one wanted signal and a strong jammer. What weights maximise signal quality — and why is it a linear-algebra problem?",
    theory=r"""Steering vector $a(θ)_m=e^{jπm\sin θ}$ (half-wavelength spacing). Delay-and-sum w = a(θ_s)/N: array gain N (9.0 dB) against white noise, but only sidelobe-level rejection of interference. MVDR:
minimise wᴴRw subject to wᴴa(θ_s) = 1 ⇒ $w=\frac{R^{-1}a}{a^HR^{-1}a}$; with a strong interferer it puts a deep null on it, achieving SINR ≈ N·SNR (the interference-free optimum) when the jammer is outside the mainlobe.""",
    method="""N = 8, desired at 0°, SNR 0 dB per element; jammer at 20°, INR 30 dB (a first choice of 30° landed exactly on a null of the uniform 8-element pattern, sin 30° = 4/8, which made delay-and-sum look perfect); noise white. Covariance estimated from 1000 snapshots (and exact). Output SINR computed from the weights and true covariances;
Monte-Carlo check from simulated snapshots. Patterns |wᴴa(θ)|².""",
)


def steer(theta, N=8):
    return np.exp(1j * pi * np.arange(N) * np.sin(np.deg2rad(theta)))


def run(p):
    N = 8; r = p.rng
    a_s, a_j = steer(0), steer(20)          # (30° would sit exactly on a null of the 8-element uniform pattern: sin 30° = 2·2/8)
    Rn = np.eye(N); Rj = 1000 * np.outer(a_j, a_j.conj()); Rs = np.outer(a_s, a_s.conj())
    Ri = Rn + Rj
    sinr = lambda w: np.real(w.conj() @ Rs @ w) / np.real(w.conj() @ Ri @ w)
    w_ds = a_s / N
    w_mv = np.linalg.solve(Ri, a_s); w_mv /= a_s.conj() @ w_mv
    p.compare("Delay-and-sum, noise only: array gain = N", 10 * np.log10(N), 10 * np.log10(np.real(w_ds.conj() @ Rs @ w_ds) / np.real(w_ds.conj() @ Rn @ w_ds)), "dB", kind="abs", tol=1e-9)
    opt = np.real(a_s.conj() @ np.linalg.solve(Ri, a_s))                      # optimum SINR = a_sᴴ R_i⁻¹ a_s (for unit signal power)
    p.compare("MVDR with jammer: output SINR = a_sᴴR⁻¹a_s (optimum)", 10 * np.log10(opt), 10 * np.log10(sinr(w_mv)), "dB", kind="abs", tol=1e-6)
    p.metric("… which is below the interference-free N by", 10 * np.log10(N) - 10 * np.log10(opt), "dB", "the price of a null 20° from the look direction")
    p.metric("Delay-and-sum with the same jammer: output SINR", 10 * np.log10(sinr(w_ds)), "dB")
    p.compare("MVDR distortionless constraint wᴴa(0°) = 1", 1.0, abs(w_mv.conj() @ a_s), "", tol=1e-10)
    p.compare("MVDR null toward the jammer deeper than −60 dB (1 = yes)", 1, int(db(abs(w_mv.conj() @ a_j)) < -60), "", kind="abs")
    K = 1000
    S = (r.normal(size=K) + 1j * r.normal(size=K)) / np.sqrt(2)
    J = np.sqrt(1000) * (r.normal(size=K) + 1j * r.normal(size=K)) / np.sqrt(2)
    Nn = (r.normal(size=(N, K)) + 1j * r.normal(size=(N, K))) / np.sqrt(2)
    X = np.outer(a_s, S) + np.outer(a_j, J) + Nn
    Rhat = X @ X.conj().T / K
    w_smi = np.linalg.solve(Rhat, a_s); w_smi /= a_s.conj() @ w_smi
    loss = 10 * np.log10(sinr(w_mv)) - 10 * np.log10(sinr(w_smi))
    p.compare("Sample-matrix MVDR (K = 1000 snapshots, includes the signal): SINR loss vs ideal (Reed–Mallett–Brennan: ~(N−1)/K → small)", 0, loss, "dB", kind="abs", tol=1.5)
    y = w_mv.conj() @ (np.outer(a_j, J) + Nn)
    p.compare("Monte-Carlo output interference+noise power vs wᴴRw", np.real(w_mv.conj() @ Ri @ w_mv), np.mean(np.abs(y) ** 2), "", tol=10)
    th = np.linspace(-90, 90, 721)
    A = np.array([steer(t) for t in th])
    fig, ax = p.fig(1, 1, w=8, h=4.5)
    ax.plot(th, db(np.abs(A @ w_ds.conj()) + 1e-9), color=COLORS[1], label="delay-and-sum")
    ax.plot(th, db(np.abs(A @ w_mv.conj()) + 1e-9), color=C_MEAS, label="MVDR (exact R)")
    ax.plot(th, db(np.abs(A @ w_smi.conj()) + 1e-9), ":", color=COLORS[2], label="MVDR (1000 snapshots)")
    ax.axvline(20, color=C_PRED, ls="--", label="jammer 20°"); ax.set_ylim(-80, 5)
    style_axes(ax, "angle (°)", "array response (dB)", "Beam patterns, 8-element λ/2 array")
    p.save(fig, "beamforming", "Delay-and-sum and MVDR beam patterns: MVDR keeps unit gain at 0° and nulls the jammer.")
    p.discuss(f"""Delay-and-sum delivers exactly the N = 8 (9.0 dB) array gain against white noise but only its fixed sidelobe level against the 30 dB jammer at 20°, so its
output SINR collapses to {10 * np.log10(sinr(w_ds)):.1f} dB. MVDR — the solution of a linear-algebra optimisation, R⁻¹a normalised — keeps unit gain toward 0°, carves a null
more than 60 dB deep toward the jammer and recovers the optimum SINR a_sᴴR⁻¹a_s — within a fraction of a dB of the interference-free 9 dB (the null, only 20° from the look direction, costs a little mainlobe gain). Estimated from 1000 real snapshots (which
include the desired signal, the harsher case) it loses only a fraction of a dB, consistent with the (N−1)/K sample-support rule. The fragility of
MVDR in practice is steering-vector mismatch: if the true desired direction differs slightly from the assumed one, MVDR treats the desired signal
as interference and nulls it, which is why robust variants add diagonal loading.""")
# tol-convention: relative tolerances are in percent
