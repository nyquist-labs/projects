# Project index

432 projects. Each row links to a folder with `project.py`, a README (problem → prediction → method → predicted-vs-measured table → discussion), figures and data.


## Applied Mathematics — 218 projects in electrical engineering


### A. Complex analysis & phasors

| # | Project | Lvl | Headline result |
|---|---|---|---|
| AM-001 | [Complex impedance calculator for R, L, C networks](projects/applied-math/A-complex-analysis-and-phasors/AM001-complex-impedance-calculator) | E | Worst relative \|Z_calc − Z_MNA\| over 5 networks × 400 frequencies: 0 → 1.6481e-13 (+1.6481e-13) |
| AM-002 | [Phasor diagram visualiser: lead and lag](projects/applied-math/A-complex-analysis-and-phasors/AM002-phasor-diagram-visualiser) | E | RL, \|X\| = 5 Ω, R = 10 Ω: phase of i relative to v: -26.57 ° → -26.54 ° (+0.02243 °) |
| AM-003 | [RLC resonance: Q is the pole's distance from the jω axis](projects/applied-math/A-complex-analysis-and-phasors/AM003-rlc-resonance-analysis) | M | R = 63.2 Ω: Q from pole geometry vs from simulated bandwidth: 0.5 → 0.4999 (-0.03 %) |
| AM-004 | [Pole-zero plotter and geometric frequency response](projects/applied-math/A-complex-analysis-and-phasors/AM004-pole-zero-plotter) | M | Geometric \|H\| vs direct evaluation, worst relative error (4 systems): 0 → 6.3061e-14 (+6.3061e-14) |
| AM-005 | [Bode plots from H(s): asymptotes vs exact](projects/applied-math/A-complex-analysis-and-phasors/AM005-bode-plot-from-hs) | M | Simple pole: asymptote error at the corner: -3.01 dB → -3.01 dB (+4.3360e-08 dB) |
| AM-006 | [Nyquist plot generator with encirclement counting](projects/applied-math/A-complex-analysis-and-phasors/AM006-nyquist-plot-generator) | M | Gains where the encirclement count ≠ number of RHP closed-loop poles (K = 1…200 except the marginal K = 60): 0 → 0 (+0) |
| AM-007 | [Smith chart from scratch: a Möbius transformation](projects/applied-math/A-complex-analysis-and-phasors/AM007-smith-chart-from-scratch) | H | Worst deviation of mapped lines from the predicted circles (centre/radius): 0 → 5.3395e-15 (+5.3395e-15) |
| AM-008 | [Reflection coefficient mapping: impedance → unit disc](projects/applied-math/A-complex-analysis-and-phasors/AM008-reflection-coefficient-mapping) | M | Lossless line: max change of \|Γ\| along the line: 0 → 4.4409e-16 (+4.4409e-16) |
| AM-009 | [s-plane explorer: drag a pole, watch the step response](projects/applied-math/A-complex-analysis-and-phasors/AM009-s-plane-explorer) | M | Max \|JS step − SciPy step\| over 200 pole pairs: 0 → 7.3497e-14 (+7.3497e-14) |
| AM-010 | [Complex power: P, Q and S as one complex number](projects/applied-math/A-complex-analysis-and-phasors/AM010-complex-power-triangle) | E | Real power P (mean of v·i): 1.636 kW → 1.636 kW (+0.02 %) |
| AM-011 | [Three-phase systems with the rotation operator a = e^{j2π/3}](projects/applied-math/A-complex-analysis-and-phasors/AM011-three-phase-phasor-analysis) | M | 1 + a + a² (should vanish): 0 → 3.3307e-16 (+3.3307e-16) |
| AM-012 | [Residue calculus: from H(s) to the impulse response](projects/applied-math/A-complex-analysis-and-phasors/AM012-partial-fractions-to-time-domain) | H | distinct real poles: residues vs scipy.signal.residue (worst difference): 0 → 4.9960e-16 (+4.9960e-16) |
| AM-013 | [All-pass filters: unity magnitude, useful phase](projects/applied-math/A-complex-analysis-and-phasors/AM013-all-pass-filter-phase-study) | M | Max deviation of \|H\| from 1 (0 dB) over 10 Hz–100 kHz: 0 dB → 3.5786e-05 dB (+3.5786e-05 dB) |
| AM-014 | [Group delay: numerical differentiation and pulse distortion](projects/applied-math/A-complex-analysis-and-phasors/AM014-group-delay-computation) | M | Bessel: numerical vs analytic group delay (worst relative error, Δω = 1.5 mrad/s): 0 → 3.3336e-07 (+3.3336e-07) |
| AM-015 | [Hilbert transform and instantaneous frequency (with real satellite audio)](projects/applied-math/A-complex-analysis-and-phasors/AM015-hilbert-transform-analytic-signal) | H | Own FFT Hilbert vs scipy.signal.hilbert (worst): 0 → 1.8344e-15 (+1.8344e-15) |
| AM-016 | [Complex baseband: why IQ sampling needs half the rate](projects/applied-math/A-complex-analysis-and-phasors/AM016-complex-baseband-representation) | H | Quadrature down-conversion recovers the complex envelope (SNR, my guess ≥ 40 dB): 40 dB → 253.9 dB (+213.9 dB) |
| AM-017 | [Root locus via the angle condition](projects/applied-math/A-complex-analysis-and-phasors/AM017-root-locus-via-complex-mapping) | M | Angle condition ∠G(s) = 180° at every computed closed-loop pole (worst error): 0 ° → 1.2722e-13 ° (+1.2722e-13 °) |
| AM-018 | [Stability from pole location, demonstrated](projects/applied-math/A-complex-analysis-and-phasors/AM018-stability-from-pole-location) | M | Impulse-response growth rate for poles at -0.5 ± 2j (= σ): -0.5 1/s → -0.5 1/s (-2.6573e-07 1/s) |

### B. Fourier analysis & transforms

| # | Project | Lvl | Headline result |
|---|---|---|---|
| AM-019 | [The DFT as a matrix-vector product](projects/applied-math/B-fourier-analysis-and-transforms/AM019-dft-from-first-principles) | M | Orthogonality: max \|WᴴW − NI\| / N over all N: 0 → 1.3545e-13 (+1.3545e-13) |
| AM-020 | [Radix-2 FFT: derive the butterfly, implement, benchmark](projects/applied-math/B-fourier-analysis-and-transforms/AM020-radix-2-fft) | H | Own radix-2 FFT vs numpy.fft, worst relative error (N = 16 … 65536): 0 → 9.4048e-16 (+9.4048e-16) |
| AM-021 | [Fourier-series synthesiser: square and sawtooth waves](projects/applied-math/B-fourier-analysis-and-transforms/AM021-fourier-series-synthesiser) | E | square: worst \|measured MSE / Parseval tail − 1\| over N = 1…200: 0 → 0.001062 (+0.001062) |
| AM-022 | [The Gibbs phenomenon: an overshoot that never goes away](projects/applied-math/B-fourier-analysis-and-transforms/AM022-gibbs-phenomenon-study) | M | Overshoot / jump at N = 2000 harmonics (Wilbraham–Gibbs 0.08949): 0.08949 → 0.08949 (-0.00 %) |
| AM-023 | [Windowing and spectral leakage: measured sidelobes](projects/applied-math/B-fourier-analysis-and-transforms/AM023-windowing-and-spectral-leakage) | M | boxcar: highest sidelobe: -13.3 dB → -13.25 dB (+0.04566 dB) |
| AM-024 | [Zero-padding vs resolution: what interpolation does not add](projects/applied-math/B-fourier-analysis-and-transforms/AM024-zero-padding-vs-resolution) | E | Resolvable separation Δf·T with 64× padding (median dip > 5 % over phases): 1 → 1 (+0) |
| AM-025 | [The convolution theorem, verified numerically](projects/applied-math/B-fourier-analysis-and-transforms/AM025-convolution-theorem-verification) | M | FFT convolution vs exact integer result, worst absolute error (N = M = 16384): 0 → 6.9849e-10 (+6.9849e-10) |
| AM-026 | [Circular vs linear convolution: the wrap-around error](projects/applied-math/B-fourier-analysis-and-transforms/AM026-circular-vs-linear-convolution) | M | Error equals the wrapped tail y_lin[n+L], worst mismatch over all L: 0 → 4.9960e-16 (+4.9960e-16) |
| AM-027 | [Overlap-add and overlap-save: fast long-signal filtering](projects/applied-math/B-fourier-analysis-and-transforms/AM027-overlap-add-and-overlap-save) | H | Overlap-add vs direct convolution, worst error: 0 → 1.3323e-15 (+1.3323e-15) |
| AM-028 | [STFT and spectrograms: the resolution trade-off](projects/applied-math/B-fourier-analysis-and-transforms/AM028-stft-and-spectrogram) | M | Δt·Δf (half-power widths) is constant across window lengths: max/min ratio: 1 → 1.154 (+15.45 %) |
| AM-029 | [The time–frequency uncertainty bound, measured](projects/applied-math/B-fourier-analysis-and-transforms/AM029-time-frequency-uncertainty) | H | Gaussian pulse: σ_t·σ_f (Gabor limit 1/4π): 0.07958 → 0.07958 (+0.00 %) |
| AM-030 | [Numerical Laplace inversion: Stehfest vs Talbot](projects/applied-math/B-fourier-analysis-and-transforms/AM030-numerical-laplace-inversion) | H | 1/(s+1) → e^(−t): Talbot worst error: 0 → 2.4163e-11 (+2.4163e-11) |
| AM-031 | [Designing in the z-plane: pole radius and decay](projects/applied-math/B-fourier-analysis-and-transforms/AM031-z-transform-digital-filter) | M | r = 0.8: envelope decay per sample = ln r: -0.2231 → -0.2231 (+0.00 %) |
| AM-032 | [Bilinear transform and frequency pre-warping](projects/applied-math/B-fourier-analysis-and-transforms/AM032-bilinear-transform) | H | Own bilinear mapping vs scipy.signal.bilinear_zpk (worst pole/gain difference): 0 → 5.9845e-16 (+5.9845e-16) |
| AM-033 | [FIR low-pass design by windowing the ideal sinc](projects/applied-math/B-fourier-analysis-and-transforms/AM033-fir-design-by-windowing) | M | boxcar: stopband attenuation: 21 dB → 20.98 dB (-0.0184 dB) |
| AM-034 | [Parks–McClellan from scratch: the Remez exchange algorithm](projects/applied-math/B-fourier-analysis-and-transforms/AM034-remez-parks-mcclellan) | H | Own Remez vs scipy.signal.remez, max \|h − h_scipy\|: 0 → 7.9269e-06 (+7.9269e-06) |
| AM-035 | [IIR filters from analog prototypes (Butterworth, Chebyshev)](projects/applied-math/B-fourier-analysis-and-transforms/AM035-iir-from-analog-prototype) | M | Butterworth N = 4: prototype poles vs SciPy (relative): 0 → 4.9953e-16 (+4.9953e-16) |
| AM-036 | [Wavelet multi-resolution analysis of a transient](projects/applied-math/B-fourier-analysis-and-transforms/AM036-wavelet-multi-resolution-analysis) | H | Haar: perfect reconstruction, max \|x − IDWT(DWT(x))\|: 0 → 3.5527e-15 (+3.5527e-15) |
| AM-037 | [The DCT and image compression — on a real satellite image](projects/applied-math/B-fourier-analysis-and-transforms/AM037-dct-and-compression) | M | DCT matrix orthonormal: max \|CCᵀ − I\|: 0 → 1.3978e-15 (+1.3978e-15) |
| AM-038 | [Chirp-Z transform: zooming into a spectral band](projects/applied-math/B-fourier-analysis-and-transforms/AM038-chirp-z-transform) | H | CZT vs direct DTFT evaluation (max relative error): 0 → 4.6051e-11 (+4.6051e-11) |
| AM-039 | [Goertzel algorithm: single-bin detection and DTMF](projects/applied-math/B-fourier-analysis-and-transforms/AM039-goertzel-algorithm) | M | Goertzel vs FFT bin (worst error / √N over 1000 cases): 0 → 1.4733e-12 (+1.4733e-12) |
| AM-040 | [Cepstral analysis: separating pitch from the vocal tract](projects/applied-math/B-fourier-analysis-and-transforms/AM040-cepstral-analysis) | H | Voiced frames where cepstral and autocorrelation pitch agree within 5 %: 90 % → 92.42 % (+2.42 pp) |
| AM-041 | [Wiener–Khinchin on real data: autocorrelation ↔ power spectrum](projects/applied-math/B-fourier-analysis-and-transforms/AM041-autocorrelation-and-psd) | M | Autocorrelation: direct vs via \|FFT\|² (max relative error): 0 → 2.9249e-15 (+2.9249e-15) |
| AM-042 | [Welch's method: trading resolution for variance](projects/applied-math/B-fourier-analysis-and-transforms/AM042-welchs-method) | M | No overlap, K = 4 segments: relative variance = 1/K: 0.25 → 0.2507 (+0.29 %) |
| AM-043 | [The sampling theorem, constructively](projects/applied-math/B-fourier-analysis-and-transforms/AM043-sampling-theorem-demonstration) | M | Relative RMS reconstruction error at f_s = 400 Hz (= 4B): 0 → 4.2208e-13 (+4.2208e-13) |

### C. Differential equations

| # | Project | Lvl | Headline result |
|---|---|---|---|
| AM-044 | [RC transient: solve the ODE, then check it](projects/applied-math/C-differential-equations/AM044-rc-transient-analysis) | E | Max \|simulation − analytic\| over charge and discharge: 0 V → 2.499 mV (+2.499 mV) |
| AM-045 | [RLC damping regimes from the characteristic equation](projects/applied-math/C-differential-equations/AM045-rlc-damping-regimes) | M | R = 20 Ω: max \|simulation − closed form\|: 0 V → 198.5 µV (+198.5 µV) |
| AM-046 | [Impulse and step response: the derivative relationship](projects/applied-math/C-differential-equations/AM046-impulse-and-step-response) | M | Closed-form impulse response vs numerical (max relative): 0 → 5.6713e-14 (+5.6713e-14) |
| AM-047 | [Euler vs RK4 on a circuit ODE: measured orders of accuracy](projects/applied-math/C-differential-equations/AM047-euler-vs-rk4-for-circuits) | M | Euler: observed order of accuracy: 1 → 1.013 (+0.01348) |
| AM-048 | [Stiff ODEs: why explicit methods die on switching circuits](projects/applied-math/C-differential-equations/AM048-stiff-odes-in-switching-circuits) | H | forward Euler: largest stable step (first unstable step in a fine sweep): 19.8 ns → 20.2 ns (+2.00 %) |
| AM-049 | [State-variable formulation of circuits](projects/applied-math/C-differential-equations/AM049-state-variable-formulation) | M | eig(A) vs 5th-order Butterworth poles (max relative distance): 0 → 5.4999e-05 (+5.4999e-05) |
| AM-050 | [Telegrapher's equations: travelling waves on a line](projects/applied-math/C-differential-equations/AM050-telegraphers-equations) | H | Z_L = 1e+06 Ω: reflection coefficient: 0.9999 → 0.9988 (-0.001125) |
| AM-051 | [Heat equation: temperature rise of a component](projects/applied-math/C-differential-equations/AM051-thermal-diffusion-model) | M | Semi-infinite bar: surface temperature rise at 1 s, FTCS vs 2q/k·√(αt/π): 30.49 K → 30.48 K (-0.01 %) |
| AM-052 | [1-D wave equation: reflecting and absorbing boundaries](projects/applied-math/C-differential-equations/AM052-1d-wave-equation) | M | fixed end, Courant 1.0: reflection coefficient: -1 → -1 (-1.7764e-15) |
| AM-053 | [Coupled LC oscillators: normal modes and beating](projects/applied-math/C-differential-equations/AM053-coupled-oscillators) | H | k = 0.02: lower mode ω0/√(1+k): 157.6 kHz → 157.6 kHz (-0.00 %) |
| AM-054 | [Van der Pol oscillator: limit cycles from weak to relaxation](projects/applied-math/C-differential-equations/AM054-van-der-pol-oscillator) | H | μ = 0.1: period ≈ 2π(1 + μ²/16): 6.287 → 6.287 (-0.00 %) |
| AM-055 | [Chua's circuit: a genuinely chaotic electronic circuit](projects/applied-math/C-differential-equations/AM055-chuas-circuit) | H | Equilibria x* = ±(m0−m1)/(m1+1) = ±1.5 satisfy the equations (max \|f\|): 0 → 3.4639e-15 (+3.4639e-15) |
| AM-056 | [Duffing oscillator: nonlinear resonance, hysteresis and jumps](projects/applied-math/C-differential-equations/AM056-duffing-oscillator) | H | Upward sweep: jump-down frequency (end of the upper branch): 1.31 rad/s → 1.33 rad/s (+1.55 %) |
| AM-057 | [Phase-portrait toolkit: equilibria, classification and trajectories](projects/applied-math/C-differential-equations/AM057-phase-portrait-toolkit) | M | Equilibria whose simulated neighbourhood behaves as the Jacobian classification predicts: 8 → 8 (+0) |
| AM-058 | [What sets an oscillator's amplitude?](projects/applied-math/C-differential-equations/AM058-limit-cycles-in-oscillators) | H | K = 3.05: steady input amplitude, describing function N(a) = 3: 424.5 mV → 424.5 mV (+0.00 %) |
| AM-059 | [Bifurcations: Hopf onset of oscillation and the period-doubling route to chaos](projects/applied-math/C-differential-equations/AM059-bifurcation-analysis) | H | Below the bifurcation (μ = −0.1): oscillation decays to 0: 0 → 1.0500e-11 (+1.0500e-11) |
| AM-060 | [Skin effect as a diffusion problem](projects/applied-math/C-differential-equations/AM060-skin-effect-diffusion) | H | Skin depth of copper at 1 MHz: 66 µm → 66.09 µm (+0.13 %) |
| AM-061 | [Boundary-value problems: shooting vs relaxation](projects/applied-math/C-differential-equations/AM061-boundary-value-problems) | H | Linear Poisson: shooting finds φ'(0) = ρL/2: 1 → 1 (+0.00 %) |

### D. Linear algebra

| # | Project | Lvl | Headline result |
|---|---|---|---|
| AM-062 | [Build a mini SPICE: modified nodal analysis from scratch](projects/applied-math/D-linear-algebra/AM062-build-a-mini-spice) | H | R-2R ladder: every node is half the previous (worst deviation of the ratio): 0 → 1.1102e-16 (+1.1102e-16) |
| AM-063 | [Sparse solvers on large resistor networks](projects/applied-math/D-linear-algebra/AM063-sparse-matrix-solvers) | H | Effective resistance to a neighbour, 500×500 grid (infinite grid: ½ Ω): 500 mΩ → 500 mΩ (-0.00 %) |
| AM-064 | [LU decomposition with partial pivoting, from scratch](projects/applied-math/D-linear-algebra/AM064-lu-decomposition-solver) | M | [[ε,1],[1,1]] with ε = 1e-16: error without pivoting (≈ 1 — the answer is wrong): 1 → 1.22 (+0.2204) |
| AM-065 | [Eigenvalues as natural frequencies of an LC ladder](projects/applied-math/D-linear-algebra/AM065-eigenvalues-as-natural-frequencies) | H | Eigenvalue frequencies vs 2/√(LC)·sin(kπ/2(N+1)) (worst relative): 0 → 4.2188e-15 (+4.2188e-15) |
| AM-066 | [State space ↔ transfer function, both directions](projects/applied-math/D-linear-algebra/AM066-state-space-to-transfer-function) | M | Round trip TF → canonical state space → Faddeev–LeVerrier → TF (worst relative): 0 → 2.2905e-09 (+2.2905e-09) |
| AM-067 | [Controllability and observability of a bridge circuit](projects/applied-math/D-linear-algebra/AM067-controllability-and-observability) | H | Balanced bridge: rank of the controllability matrix (n = 2): 1 → 1 (+0) |
| AM-068 | [SVD denoising: low-rank Hankel approximation](projects/applied-math/D-linear-algebra/AM068-svd-for-noise-reduction) | H | Noise-free Hankel matrix: numerical rank (3 sinusoids → 6): 6 → 6 (+0) |
| AM-069 | [PCA on 64-channel EEG: dominant spatial modes](projects/applied-math/D-linear-algebra/AM069-pca-on-signal-data) | M | Variance explained by the first 3 principal components (my guess > 50 %): 50 % → 86.72 % (+36.7 pp) |
| AM-070 | [Least-squares system identification (ARX)](projects/applied-math/D-linear-algebra/AM070-least-squares-identification) | M | Mean estimate − truth (worst parameter, equation-error noise) — unbiased: 0 σ → 0.07365 σ (+0.07365 σ) |
| AM-071 | [Matrix pencil: extracting damped exponentials from a transient](projects/applied-math/D-linear-algebra/AM071-matrix-pencil-method) | H | Noise-free: worst frequency error: 0 Hz → 160.1 pHz (+160.1 pHz) |
| AM-072 | [Resistor networks as graphs: Laplacian, effective resistance, Foster's theorem](projects/applied-math/D-linear-algebra/AM072-graph-laplacian-of-a-network) | H | Cube: opposite corners: 833.3 mΩ → 833.3 mΩ (-0.00 %) |
| AM-073 | [Two-port parameters: Z, Y and S matrices](projects/applied-math/D-linear-algebra/AM073-two-port-parameters) | M | π-network: Y from short-circuit tests = inverse of Z from open-circuit tests (worst relative): 0 → 3.6809e-11 (+3.6809e-11) |
| AM-074 | [Chaining filter stages with ABCD matrices](projects/applied-math/D-linear-algebra/AM074-cascade-abcd-matrices) | M | Cascade of ABCD matrices vs full-circuit simulation, max \|ΔS21\|: 0 → 7.7914e-16 (+7.7914e-16) |
| AM-075 | [MIMO capacity from singular values](projects/applied-math/D-linear-algebra/AM075-mimo-channel-capacity) | H | SVD precoding diagonalises H: max off-diagonal \|UᴴHV\|: 0 → 1.4457e-15 (+1.4457e-15) |
| AM-076 | [Beamforming as matrix algebra: delay-and-sum vs MVDR](projects/applied-math/D-linear-algebra/AM076-beamforming-as-matrix-algebra) | H | Delay-and-sum, noise only: array gain = N: 9.031 dB → 9.031 dB (+0 dB) |
| AM-077 | [The algebra of OFDM: circulant channels and Kronecker products](projects/applied-math/D-linear-algebra/AM077-kronecker-structure-in-ofdm) | H | Circulant channel: F H Fᴴ is diagonal (max off-diagonal / max diagonal): 0 → 2.4297e-16 (+2.4297e-16) |
| AM-078 | [Condition numbers: when linear algebra lies](projects/applied-math/D-linear-algebra/AM078-condition-number-study) | M | Hilbert systems: forward error ≤ κ·ε (fraction of sizes obeying the bound ×10): 1 → 1 (+0) |
| AM-079 | [Krylov model-order reduction of a large RC network](projects/applied-math/D-linear-algebra/AM079-krylov-model-reduction) | H | q = 4: moments matched (one-sided Krylov: ≥ q): 4 → 4 (+0) |

### E. Probability & stochastic processes

| # | Project | Lvl | Headline result |
|---|---|---|---|
| AM-080 | [Johnson noise and kT/C, verified by stochastic simulation](projects/applied-math/E-probability-and-stochastic-processes/AM080-thermal-noise-verification) | M | R = 1e+03 Ω, C = 1 pF: rms noise = √(kT/C): 64.36 µV → 64.66 µV (+0.47 %) |
| AM-081 | [Shot noise: Poisson electrons and the 2qI spectrum](projects/applied-math/E-probability-and-stochastic-processes/AM081-shot-noise-as-a-poisson-process) | M | I = 1e-12 A: PSD / 2qI (white, flat band): 1 → 0.9972 (-0.28 %) |
| AM-082 | [1/f flicker noise: synthesis, spectrum and Allan deviation](projects/applied-math/E-probability-and-stochastic-processes/AM082-1f-flicker-noise) | H | FFT-shaped noise: PSD slope (1/f → −1): -1 → -0.9991 (+8.8670e-04) |
| AM-083 | [Receiver noise figure: Friis formula and Monte-Carlo spread](projects/applied-math/E-probability-and-stochastic-processes/AM083-noise-figure-monte-carlo) | M | Friis cascade NF: 1.83 dB → 1.842 dB (+0.01246 dB) |
| AM-084 | [Bit-error rate vs SNR: Monte Carlo against theory](projects/applied-math/E-probability-and-stochastic-processes/AM084-ber-vs-snr-simulation) | M | BPSK: fraction of simulated points whose 95 % interval contains the formula: 1 → 0.9231 (-0.07692) |
| AM-085 | [The Q-function: derivation, bounds and rare-event estimation](projects/applied-math/E-probability-and-stochastic-processes/AM085-q-function-derivation) | M | Direct integral vs ½·erfc(x/√2) (worst relative, x = 0.5…7): 0 → 3.2245e-08 (+3.2245e-08) |
| AM-086 | [Manufacturing yield from component tolerances](projects/applied-math/E-probability-and-stochastic-processes/AM086-component-tolerance-yield-study) | M | Nominal −3 dB frequency: 1 kHz → 1.005 kHz (+0.49 %) |
| AM-087 | [Reliability: exponential and Weibull failure models, MTBF](projects/applied-math/E-probability-and-stochastic-processes/AM087-reliability-and-mtbf) | M | Series of 50 parts (λ = 1e-6/h each): system MTBF = 1/(50λ): 2e+04 h → 1.999e+04 h (-0.05 %) |
| AM-088 | [Bursty errors: a two-state Markov (Gilbert–Elliott) channel](projects/applied-math/E-probability-and-stochastic-processes/AM088-markov-chain-channel-model) | H | Fraction of time in the bad state = p/(p+q): 0.01961 → 0.01945 (-0.81 %) |
| AM-089 | [Rayleigh and Rician fading: distributions, level crossings, fade durations](projects/applied-math/E-probability-and-stochastic-processes/AM089-rayleigh-and-rician-fading) | H | Envelope PDF vs Rayleigh (max \|difference\|): 0 → 0.01593 (+0.01593) |
| AM-090 | [The central limit theorem in noise: why interference becomes Gaussian](projects/applied-math/E-probability-and-stochastic-processes/AM090-central-limit-theorem-in-noise) | E | random-phase sinusoid: excess kurtosis at N = 20 (= κ/N): -0.075 → -0.08405 (-0.009052) |
| AM-091 | [Maximum-likelihood detection when the noise depends on the symbol](projects/applied-math/E-probability-and-stochastic-processes/AM091-maximum-likelihood-detection) | H | Threshold minimising the simulated BER vs ML threshold: 0.3421 → 0.34 (-0.002147) |
| AM-092 | [MAP vs ML: when prior knowledge helps](projects/applied-math/E-probability-and-stochastic-processes/AM092-map-estimation) | H | N = 1: ML MSE = σ²/N: 1 → 0.9973 (-0.27 %) |
| AM-093 | [Recursive Bayesian filtering on a grid](projects/applied-math/E-probability-and-stochastic-processes/AM093-bayesian-filtering) | H | Linear-Gaussian case: grid posterior mean vs Kalman filter (max difference / σ): 0 → 7.8738e-08 (+7.8738e-08) |
| AM-094 | [The Kalman filter, derived and tested for consistency](projects/applied-math/E-probability-and-stochastic-processes/AM094-kalman-filter-derived) | H | Average NEES inside the 95 % χ² band (fraction of steps after convergence): 0.95 → 0.9628 (+0.01278) |
| AM-095 | [Particle filter vs extended Kalman filter on a nonlinear benchmark](projects/applied-math/E-probability-and-stochastic-processes/AM095-particle-filter) | H | RMSE ratio EKF / PF(1000) (my guess ≥ 3): 3 × → 4.622 × (+1.622 ×) |
| AM-096 | [The Wiener filter: optimal linear filtering in the frequency domain](projects/applied-math/E-probability-and-stochastic-processes/AM096-wiener-filter) | H | Wiener filter: simulated MSE vs theoretical minimum ∫S_xS_n/(S_x+S_n): 0.146 → 0.1463 (+0.21 %) |
| AM-097 | [LMS adaptive filters: step size, stability and misadjustment](projects/applied-math/E-probability-and-stochastic-processes/AM097-lms-convergence-analysis) | H | white: misadjustment ≈ μ·tr(R)/(1 − μ·tr(R)): 0.05263 → 0.05196 (-1.27 %) |
| AM-098 | [Random walks in integrators: noise that grows without bound](projects/applied-math/E-probability-and-stochastic-processes/AM098-random-walk-in-circuits) | M | Ideal integrator: Var(v) / t (= σ² = 1): 1 → 1.038 (+3.80 %) |
| AM-099 | [Queueing theory for packet buffers: M/M/1 and Little's law](projects/applied-math/E-probability-and-stochastic-processes/AM099-queueing-theory-basics) | M | ρ = 0.3: mean time in system 1/(μ−λ): 1.429 → 1.431 (+0.14 %) |

### F. Optimisation

| # | Project | Lvl | Headline result |
|---|---|---|---|
| AM-100 | [Filter design as constrained optimisation](projects/applied-math/F-optimisation/AM100-filter-design-as-optimisation) | H | Own weighted LS vs scipy.signal.firls (max \|Δh\|; firls integrates exactly, own uses a dense grid): 0 → 6.3358e-04 (+6.3358e-04) |
| AM-101 | [Broadband impedance matching by optimisation, against the Bode–Fano limit](projects/applied-math/F-optimisation/AM101-impedance-matching-optimisation) | H | Every optimised design respects Bode–Fano (worst \|Γ\| ≥ limit; 1 = yes): 1 → 1 (+0) |
| AM-102 | [Choosing real resistor values: discrete optimisation](projects/applied-math/F-optimisation/AM102-e-series-component-selection) | M | E24 single value: worst error (my guess: half a ~10 % step ≈ 5 %): 5 % → 7.227 % (+2.23 pp) |
| AM-103 | [Fitting a diode model: gradient descent vs Gauss–Newton](projects/applied-math/F-optimisation/AM103-gradient-descent-parameter-fitting) | M | LM fit: saturation current I_s: 2.5 nA → 2.52 nA (+0.80 %) |
| AM-104 | [Minimax FIR design as a linear program](projects/applied-math/F-optimisation/AM104-convex-optimisation-for-fir) | H | LP minimax vs Parks–McClellan: peak error (relative difference): 0.01033 → 0.01032 (-0.16 %) |
| AM-105 | [Genetic algorithm design of a 3-element Yagi](projects/applied-math/F-optimisation/AM105-genetic-algorithm-antenna-design) | H | GA best: directivity (literature for 3 elements ≈ 7–8 dBi): 7.5 dBi → 8.454 dBi (+0.9545 dBi) |
| AM-106 | [Simulated annealing for component placement](projects/applied-math/F-optimisation/AM106-simulated-annealing-placement) | H | SA reduction vs random placement (mean over 5 netlists; my guess 30–50 %): 40 % → 63.76 % (+23.8 pp) |
| AM-107 | [DC optimal power flow on a 5-bus network](projects/applied-math/F-optimisation/AM107-optimal-power-flow) | H | Line 1–2 limit binds in the constrained solution: 280 MW → 280 MW (+0.00 %) |
| AM-108 | [Economic dispatch: equal incremental cost](projects/applied-math/F-optimisation/AM108-economic-dispatch) | M | λ-bisection vs SLSQP optimum cost (worst relative over demands): 0 → 4.1588e-11 (+4.1588e-11) |
| AM-109 | [MPPT as online optimisation: perturb-and-observe vs incremental conductance](projects/applied-math/F-optimisation/AM109-mppt-as-hill-climbing) | M | Best tracking efficiency, P&O (my guess ≥ 99 %): 99 % → 99.95 % (+0.945 pp) |
| AM-110 | [Minimax polynomial approximation and why it is optimal](projects/applied-math/F-optimisation/AM110-minimax-approximation) | H | eˣ, degree 5: minimax error (my estimate ≈ 4.5e-5): 4.5000e-05 → 4.5206e-05 (+0.46 %) |
| AM-111 | [Fitting a real battery discharge curve: models, residuals and uncertainty](projects/applied-math/F-optimisation/AM111-least-squares-curve-fitting) | M | Shepherd model extrapolates to the knee better than a degree-12 polynomial (error ratio poly12 / Shepherd > 1): 3 × → 12.71 × (+9.713 ×) |
| AM-112 | [Tikhonov regularisation: deblurring a sensor signal](projects/applied-math/F-optimisation/AM112-regularisation-on-noisy-data) | H | Naive inversion: error norm / signal norm (≫ 1: noise amplified): 100 × → 2.0693e+15 × (+2.0693e+15 ×) |
| AM-113 | [Linear programming: allocating parts to board builds](projects/applied-math/F-optimisation/AM113-linear-programming-allocation) | M | Own simplex optimum profit vs HiGHS: 2.4e+04 $ → 2.4e+04 $ (-0.00 %) |
| AM-114 | [Multi-objective design: Pareto fronts for an anti-alias filter](projects/applied-math/F-optimisation/AM114-multi-objective-trade-study) | H | ε-constraint sweep reaches every Pareto point (fraction): 1 → 1 (+0.00 %) |

### G. Numerical methods

| # | Project | Lvl | Headline result |
|---|---|---|---|
| AM-115 | [Newton–Raphson for a diode circuit (what SPICE does inside)](projects/applied-math/G-numerical-methods/AM115-newton-raphson-for-diode-circuits) | H | Newton from 0.6 V converges to the Lambert-W solution: 692.5 mV → 692.5 mV (-0.00 %) |
| AM-116 | [Trapezoidal vs backward Euler in circuit transients](projects/applied-math/G-numerical-methods/AM116-transient-integration-methods) | H | Trapezoidal: energy after 200 cycles (conserved, \|R\| = 1): 1 → 1 (+0.00 %) |
| AM-117 | [1-D FDTD: Maxwell's equations on a Yee grid](projects/applied-math/G-numerical-methods/AM117-1d-fdtd) | M | Reflection coefficient vacuum → ε_r = 4: (1 − n)/(1 + n): -0.3333 → -0.3338 (-0.14 %) |
| AM-118 | [2-D FDTD: diffraction through a slit](projects/applied-math/G-numerical-methods/AM118-2d-fdtd-scattering) | H | First diffraction minimum angle: arcsin(λ/a) for a = 3λ: 19.47 ° → 19.5 ° (+0.02878 °) |
| AM-119 | [Finite elements from scratch: capacitance of a coaxial line](projects/applied-math/G-numerical-methods/AM119-finite-element-basics) | H | Finest mesh: FEM capacitance vs 2πε/ln(b/a): 44.41 pF/m → 44.41 pF/m (+0.01 %) |
| AM-120 | [Method of moments: charge on a conductor and current on a dipole](projects/applied-math/G-numerical-methods/AM120-method-of-moments) | H | Sphere a = 1 m: MoM capacitance (finest) vs 4πε₀a: 111.3 pF → 111.5 pF (+0.19 %) |
| AM-121 | [Computing Fourier coefficients accurately](projects/applied-math/G-numerical-methods/AM121-numerical-fourier-coefficients) | M | Smooth periodic f = e^{cos t}: trapezoid error for c₁ with N = 16 (spectral: ≈ I₁₅(1) ≈ 1e-19 → machine ε): 0 → 1.1102e-16 (+1.1102e-16) |
| AM-122 | [Root finding for resonance: bisection, secant and Newton](projects/applied-math/G-numerical-methods/AM122-root-finding-for-resonance) | E | Upper series resonance: bisection root vs closed form (quadratic in ω²): 3.25 MHz → 3.25 MHz (+0.00 %) |
| AM-123 | [Lookup tables: linear vs spline interpolation](projects/applied-math/G-numerical-methods/AM123-interpolation-for-lookup-tables) | M | ln R table, linear interpolation: error ∝ n^slope (−2): -2 → -2.017 (-0.01691) |
| AM-124 | [Fixed vs floating point in a DSP chain](projects/applied-math/G-numerical-methods/AM124-fixed-vs-floating-point) | H | 8-bit quantisation of a −1 dBFS sine: SQNR ≈ 6.02B + 1.76 − 1 dB: 48.92 dB → 49.06 dB (+0.1368 dB) |
| AM-125 | [Quantisation noise through a filter cascade: ordering matters](projects/applied-math/G-numerical-methods/AM125-quantisation-error-propagation) | H | Predicted vs measured output noise, worst ratio over all 24 orderings: 1 → 1.055 (+5.50 %) |
| AM-126 | [Where round-off destroys a filter: direct form vs second-order sections](projects/applied-math/G-numerical-methods/AM126-conditioning-in-dsp) | M | Direct form, 16-bit coefficients: largest pole radius ≥ 1 (unstable; 1 = yes): 1 → 1 (+0) |
| AM-127 | [Monte Carlo integration where quadrature fails](projects/applied-math/G-numerical-methods/AM127-monte-carlo-integration) | M | d = 1: Monte Carlo RMS error ∝ N^slope (−½, independent of d): -0.5 → -0.5323 (-0.03226) |
| AM-128 | [Numerical differentiation: step size, round-off and noise](projects/applied-math/G-numerical-methods/AM128-numerical-differentiation) | M | Central difference: log₁₀ of the optimal step, from (3ε_f/\|φ‴\|)^(1/3): -4.824 → -5.333 (-0.5096) |
| AM-129 | [Error-controlled adaptive time stepping (Dormand–Prince RK45)](projects/applied-math/G-numerical-methods/AM129-adaptive-step-size) | H | Tolerance proportionality: global error ∝ tol^slope (≈ 1): 1 → 1.221 (+0.2215) |
| AM-130 | [Verifying solvers: observed order of accuracy and manufactured solutions](projects/applied-math/G-numerical-methods/AM130-convergence-analysis) | H | Correct Poisson solver: observed order (5-point stencil → 2): 2 → 2 (+7.8071e-05) |
| AM-131 | [Stability regions of time-integration schemes](projects/applied-math/G-numerical-methods/AM131-stability-regions) | H | Agreement between \|R(z)\| ≤ 1 and 400-step simulations over all methods (excluding \|R\| ≈ 1 edge pixels): 1 → 0.9979 (-0.21 %) |
| AM-132 | [Mini SPICE, full version: MNA + Newton + transient](projects/applied-math/G-numerical-methods/AM132-mini-spice-full-version) | H | Mini SPICE vs repository simulator: max \|Δv_out\| after start-up: 0 V → 90.54 pV (+90.54 pV) |

### H. Discrete math, finite fields & coding

| # | Project | Lvl | Headline result |
|---|---|---|---|
| AM-133 | [Karnaugh-map solver: automatic grouping, verified](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM133-karnaugh-map-solver) | M | Covers that disagree with the truth table (4255 functions): 0 → 0 (+0) |
| AM-134 | [Quine–McCluskey: exact two-level minimisation](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM134-quine-mccluskey-minimiser) | H | Parity of 3 inputs: minimum product terms = 2^(n−1): 4 → 4 (+0) |
| AM-135 | [Boolean identity checker](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM135-boolean-identity-checker) | M | Textbook identities confirmed: 14 → 14 (+0) |
| AM-136 | [Binary decision diagrams: compressing truth tables](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM136-binary-decision-diagrams) | H | Canonicity: AB + A'C and AB + A'C + BC reduce to the identical node (1 = yes): 1 → 1 (+0) |
| AM-137 | [An ALU derived from Boolean algebra, gate by gate](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM137-alu-from-boolean-algebra) | M | Test vectors applied (7 operations × 2⁸ × 2⁸): 4.588e+05 → 4.588e+05 (+0) |
| AM-138 | [Carry-lookahead derived: from ripple to parallel prefix](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM138-carry-lookahead-derivation) | M | Unrolled c₄ equation vs recurrence vs true carry (512 inputs × both definitions of p): 0 mismatches → 0 mismatches (+0 mismatches) |
| AM-139 | [FSM state minimisation by partition refinement](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM139-fsm-state-minimisation) | H | Inflated machines reduced to exactly the known minimal size (300 machines, mean inflation 2.8×): 0 failures → 0 failures (+0 failures) |
| AM-140 | [State encoding optimisation: every assignment of a 5-state FSM](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM140-state-encoding-optimisation) | H | Assignments enumerated: 8!/3!: 6720 → 6720 (+0) |
| AM-141 | [Gray codes: one bit at a time](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM141-gray-code-generator) | E | Adjacent codes (incl. wrap-around) not differing in exactly one bit, n = 1…16: 0 → 0 (+0) |
| AM-142 | [LFSRs and primitive polynomials](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM142-lfsr-and-primitive-polynomials) | M | Degrees 2–16 where the count of primitive polynomials ≠ φ(2ⁿ − 1)/n: 0 → 0 (+0) |
| AM-143 | [A GF(2ᵐ) arithmetic library, verified against AES](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM143-gf2m-arithmetic-library) | H | GF(16): commutativity, associativity, distributivity violations (all triples): 0 → 0 (+0) |
| AM-144 | [CRC as polynomial division over GF(2)](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM144-crc-as-polynomial-division) | M | CRC-32 of "123456789": 3.4218e+09 → 3.4218e+09 (+0) |
| AM-145 | [Hamming codes: perfect single-error correction](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM145-hamming-codes) | M | (7,4) sphere packing: 2ᵏ(1 + n) / 2ⁿ: 1 → 1 (+0.00 %) |
| AM-146 | [Reed–Solomon codes: polynomials that survive erasure](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM146-reed-solomon-codes) | H | RS(7,3): minimum distance = n − k + 1: 5 → 5 (+0) |
| AM-147 | [BCH codes from cyclotomic cosets](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM147-bch-codes) | H | n = 15, t = 1: generator polynomial (as an integer) = 0x13: 19 → 19 (+0) |
| AM-148 | [Convolutional codes: state diagrams, trellises and distance spectra](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM148-convolutional-codes-and-trellises) | H | (7,5) K = 3: free distance: 5 → 5 (+0) |
| AM-149 | [The Viterbi algorithm as dynamic programming](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM149-viterbi-as-dynamic-programming) | H | Viterbi path metric vs exhaustive ML maximum over 1024 codewords (max difference, 400 blocks): 0 → 1.4211e-14 (+1.4211e-14) |
| AM-150 | [LDPC codes: decoding by passing messages on a bipartite graph](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM150-ldpc-codes-and-bipartite-graphs) | H | Column weight / row weight of H (regular: 3 and 6; number of violations): 0 → 0 (+0) |
| AM-151 | [Huffman coding: the optimal prefix code, built greedily](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM151-huffman-coding) | M | Huffman worse than the best prefix code found by exhaustive search (300 random sources, 3–6 symbols): 0 → 0 (+0) |
| AM-152 | [Routing as a graph problem: Lee, A*, and Steiner trees](projects/applied-math/H-discrete-math-finite-fields-and-coding/AM152-routing-as-a-graph-problem) | H | Lee and A* path length vs networkx shortest path (200 mazes, 196 routable): mismatches: 0 → 0 (+0) |

### I. Control theory

| # | Project | Lvl | Headline result |
|---|---|---|---|
| AM-153 | [PID control analysed with Laplace transforms](projects/applied-math/I-control-theory/AM153-pid-control-with-laplace) | M | P control: steady-state error 1/(1 + K_p·G(0)): 0.1 → 0.1 (-0.00 %) |
| AM-154 | [Routh–Hurwitz: stability without finding the roots](projects/applied-math/I-control-theory/AM154-routh-hurwitz-stability) | M | Routh sign changes vs number of RHP roots from numpy.roots (5000 random polynomials, degree 2–8): mismatches: 0 → 0 (+0) |
| AM-155 | [Root-locus construction rules, checked against the computed locus](projects/applied-math/I-control-theory/AM155-root-locus-construction) | M | Real-axis rule: real closed-loop poles found outside (−1, 0) ∪ (−∞, −2): 0 → 0 (+0) |
| AM-156 | [Gain and phase margins — and what they actually guarantee](projects/applied-math/I-control-theory/AM156-gain-and-phase-margins) | M | Phase-crossover frequency √5: 2.236 rad/s → 2.236 rad/s (+0.00 %) |
| AM-157 | [The Nyquist criterion: counting encirclements](projects/applied-math/I-control-theory/AM157-nyquist-criterion) | H | Z = N + P from the encirclement count vs closed-loop RHP poles from the roots (2000 random loops): mismatches: 0 → 0 (+0) |
| AM-158 | [Lead–lag compensator design in the frequency domain](projects/applied-math/I-control-theory/AM158-lead-lag-compensator-design) | M | Uncompensated phase margin 180° − 90° − arctan ω_gc: 17.96 ° → 17.96 ° (+0 °) |
| AM-159 | [State-feedback pole placement with Ackermann's formula](projects/applied-math/I-control-theory/AM159-state-feedback-pole-placement) | H | Ackermann: worst relative pole error over 200 random systems (n = 2…6): 0 → 5.0485e-07 (+5.0485e-07) |
| AM-160 | [LQR: optimal state feedback from the Riccati equation](projects/applied-math/I-control-theory/AM160-linear-quadratic-regulator) | H | Own Hamiltonian-eigenvector Riccati solution vs scipy (max relative difference): 0 → 7.8957e-16 (+7.8957e-16) |
| AM-161 | [Observer design and the separation principle](projects/applied-math/I-control-theory/AM161-observer-design) | H | Separation principle: eigenvalues of the observer-based loop vs eig(A−BK) ∪ eig(A−LC) (worst distance, 3 designs): 0 → 2.0128e-13 (+2.0128e-13) |
| AM-162 | [The Kalman filter as the optimal observer](projects/applied-math/I-control-theory/AM162-kalman-filter-as-optimal-observer) | H | Riccati recursion iterated to steady state vs scipy DARE (max relative difference): 0 → 1.0811e-14 (+1.0811e-14) |
| AM-163 | [Inverted pendulum on a cart: linear design, nonlinear reality](projects/applied-math/I-control-theory/AM163-inverted-pendulum) | H | Unstable pole of the linearisation √((M+m)g/(Ml)) vs eigenvalue of A: 6.766 1/s → 6.766 1/s (+0.00 %) |
| AM-164 | [Lyapunov stability: proving convergence without solving the equations](projects/applied-math/I-control-theory/AM164-lyapunov-stability) | H | 'P > 0' vs 'all eigenvalues in the left half-plane' on 2000 random matrices (848 stable): disagreements: 0 → 0 (+0) |
| AM-165 | [Describing functions: predicting limit cycles in nonlinear loops](projects/applied-math/I-control-theory/AM165-describing-functions) | H | Ideal relay: limit-cycle frequency √2: 1.414 rad/s → 1.38 rad/s (-2.40 %) |
| AM-166 | [Discrete-time control: ZOH models, deadbeat response and controller emulation](projects/applied-math/I-control-theory/AM166-discrete-time-control) | H | Own ZOH discretisation vs scipy.signal.cont2discrete (max difference): 0 → 0 (+0) |
| AM-167 | [How sampling erodes stability margins](projects/applied-math/I-control-theory/AM167-sampling-effects-on-stability) | H | T = 10 ms (ω_s/ω_gc = 154): discrete phase margin vs PM − ω_gc·T/2: 50.37 ° → 50.37 ° (+0.00175 °) |
| AM-168 | [Model predictive control: optimisation in the loop](projects/applied-math/I-control-theory/AM168-model-predictive-control) | H | Unconstrained MPC (N = 20, Riccati terminal weight): first-move gain vs LQR gain (max difference): 0 → 1.0658e-14 (+1.0658e-14) |

### J. Statistics & learning on real signals

| # | Project | Lvl | Headline result |
|---|---|---|---|
| AM-169 | [ECG R-peak detection as a statistical decision problem](projects/applied-math/J-statistics-and-learning-on-real-signals/AM169-ecg-r-peak-detection-statistics) | M | Fixed-threshold detector at its best F1: sensitivity (published detectors: > 99 %): 99 % → 99.26 % (+0.259 pp) |
| AM-170 | [Heart-rate variability: time-domain and spectral statistics](projects/applied-math/J-statistics-and-learning-on-real-signals/AM170-hrv-spectral-analysis) | M | Identity: RMSSD² = 2σ²(1 − ρ₁): 27.8 ms → 27.79 ms (-0.04 %) |
| AM-171 | [Hypothesis testing on real EEG: is alpha stronger with eyes closed?](projects/applied-math/J-statistics-and-learning-on-real-signals/AM171-hypothesis-testing-on-eeg) | M | Own paired t statistic vs scipy.stats: 7.785 → 7.785 (+0.00 %) |
| AM-172 | [ROC analysis of an arrhythmia detector](projects/applied-math/J-statistics-and-learning-on-real-signals/AM172-roc-analysis) | M | AUC by the trapezoid rule vs Mann–Whitney U/(n₊n₋) from ranks: 0.9881 → 0.9881 (-0.00 %) |
| AM-173 | [EMG features: what they measure and how much they overlap](projects/applied-math/J-statistics-and-learning-on-real-signals/AM173-emg-feature-statistics) | M | MAV/RMS of active surface EMG: Gaussian model √(2/π): 0.7979 → 0.7746 (-2.92 %) |
| AM-174 | [Linear discriminant analysis from scratch](projects/applied-math/J-statistics-and-learning-on-real-signals/AM174-lda-from-scratch) | M | Synthetic Gaussians, Δ = 1: test error vs Bayes error Φ(−Δ/2): 30.85 % → 30.99 % (+0.46 %) |
| AM-175 | [Support vector machines: margins, duality and kernels](projects/applied-math/J-statistics-and-learning-on-real-signals/AM175-support-vector-machine) | H | Separable data: distance of the closest points to the boundary on both sides are equal (ratio): 1 → 1 (-0.00 %) |
| AM-176 | [Logistic regression: likelihood, Newton's method and calibration](projects/applied-math/J-statistics-and-learning-on-real-signals/AM176-logistic-regression) | M | Analytic gradient vs central finite differences (worst relative error): 0 → 6.0291e-09 (+6.0291e-09) |
| AM-177 | [A neural network from scratch: backpropagation verified](projects/applied-math/J-statistics-and-learning-on-real-signals/AM177-neural-network-from-scratch) | H | Backpropagation vs central finite differences: worst relative error over all 119 parameters: 0 → 1.0244e-08 (+1.0244e-08) |
| AM-178 | [A convolutional network on spectrograms, written in NumPy](projects/applied-math/J-statistics-and-learning-on-real-signals/AM178-cnn-on-spectrograms) | H | CNN backward pass vs finite differences (sampled parameters of every layer): worst relative error: 0 → 1.4134e-09 (+1.4134e-09) |
| AM-179 | [Cross-validation done wrong and done right](projects/applied-math/J-statistics-and-learning-on-real-signals/AM179-cross-validation-methodology) | H | My expectation: 1-NN on randomly split overlapping windows looks near-perfect (> 98 %; 1 = yes): 1 → 0 (-1) |
| AM-180 | [Confusion matrices and class imbalance](projects/applied-math/J-statistics-and-learning-on-real-signals/AM180-confusion-matrices-and-class-imbalance) | M | Accuracy of a detector that never fires = 1 − prevalence: 96.04 % → 96.04 % (+0.00 %) |
| AM-181 | [Dimensionality reduction: PCA and t-SNE from scratch](projects/applied-math/J-statistics-and-learning-on-real-signals/AM181-dimensionality-reduction-pca-and-tsne) | H | PCA variances from the SVD vs eigenvalues of the covariance matrix (largest 50, worst relative difference): 0 → 4.0474e-15 (+4.0474e-15) |
| AM-182 | [Clustering without labels: k-means and Gaussian mixtures](projects/applied-math/J-statistics-and-learning-on-real-signals/AM182-clustering-real-signals) | M | k-means inertia never increases from one iteration to the next (violations, k = 2…10, all restarts): 0 → 0 (+0) |
| AM-183 | [Forecasting battery ageing: ARIMA and state-space models with honest intervals](projects/applied-math/J-statistics-and-learning-on-real-signals/AM183-time-series-forecasting) | H | Synthetic AR(2), φ₁ = 1.2: least-squares estimate: 1.2 → 1.2 (-0.02 %) |
| AM-184 | [Anomaly detection without labels: abnormal heartbeats as outliers](projects/applied-math/J-statistics-and-learning-on-real-signals/AM184-anomaly-detection) | H | Unsupervised detection (robust distance, no labels): mean within-patient AUC (supervised detector on unseen patients: 0.988): 0.988 → 0.9855 (-0.002539) |
| AM-185 | [Independent component analysis for removing eye blinks from EEG](projects/applied-math/J-statistics-and-learning-on-real-signals/AM185-ica-artifact-removal) | H | Synthetic mixtures: Amari index of W·A (0 = perfect separation; mean of 20 trials): 0 → 0.007507 (+0.007507) |
| AM-186 | [Feature selection with mutual information](projects/applied-math/J-statistics-and-learning-on-real-signals/AM186-information-theoretic-feature-selection) | H | Estimator check, binary symmetric channel ε = 0.1: I = 1 − H₂(ε): 0.531 bit → 0.5331 bit (+0.39 %) |
| AM-187 | [Bootstrap confidence intervals — and when they fail](projects/applied-math/J-statistics-and-learning-on-real-signals/AM187-bootstrap-confidence-intervals) | M | Bootstrap SE of the mean vs s·√((n−1)/n)/√n: 0.4037 → 0.4039 (+0.06 %) |
| AM-188 | [EMG cursor control: from classifier accuracy to task performance](projects/applied-math/J-statistics-and-learning-on-real-signals/AM188-simulated-emg-cursor-control) | H | Four direction gestures: Wolpaw ITR vs mutual information of the pooled confusion matrix (bits per decision): 1.633 bit → 1.539 bit (-5.78 %) |

### K. Fields, vector calculus & geometry

| # | Project | Lvl | Headline result |
|---|---|---|---|
| AM-189 | [A numerical field solver that obeys Gauss's law](projects/applied-math/K-fields-vector-calculus-and-geometry/AM189-numerical-field-solver-gauss-law) | M | Flux of D out of 5 closed boxes vs enclosed charge (worst relative error): 0 → 1.1241e-14 (+1.1241e-14) |
| AM-190 | [Laplace's equation by relaxation: Jacobi, Gauss–Seidel and SOR](projects/applied-math/K-fields-vector-calculus-and-geometry/AM190-laplace-relaxation-methods) | M | N = 63, Jacobi: measured error-reduction factor per sweep = cos(πh): 0.9988 → 0.9988 (-0.00 %) |
| AM-191 | [Biot–Savart integration for coils](projects/applied-math/K-fields-vector-calculus-and-geometry/AM191-biot-savart-integration) | M | Finite straight segment: μ₀I(sin α₂ − sin α₁)/(4πd): 9.94 µT → 9.94 µT (+0.00 %) |
| AM-192 | [Vector-calculus visualiser (interactive, verified)](projects/applied-math/K-fields-vector-calculus-and-geometry/AM192-vector-calculus-visualiser) | M | Divergence of (x²y, sin x cos y) vs 2xy − sin x sin y (worst abs. error, 400 points): 0 → 1.6637e-09 (+1.6637e-09) |
| AM-193 | [How Maxwell's equations make a wave: a 2-D Yee simulation](projects/applied-math/K-fields-vector-calculus-and-geometry/AM193-maxwell-equations-demo) | H | Gauss's law for magnetism: max \|∇·B\|·Δ / max \|H\| over the whole run (zero up to round-off): 0 → 1.2729e-14 (+1.2729e-14) |
| AM-194 | [Where the power flows: the Poynting vector in a transmission line](projects/applied-math/K-fields-vector-calculus-and-geometry/AM194-poynting-vector-energy-flow) | H | ∫(E×H)·ẑ dA over the cross-section = V·I (power is carried by the fields between the conductors): 16.51 mW → 16.26 mW (-1.51 %) |
| AM-195 | [Waveguide modes as a Helmholtz eigenvalue problem](projects/applied-math/K-fields-vector-calculus-and-geometry/AM195-waveguide-eigenmodes) | H | WR-90 TE10 cutoff (h = a/160): 6.557 GHz → 6.557 GHz (-0.00 %) |
| AM-196 | [Antenna far fields by numerical radiation integrals](projects/applied-math/K-fields-vector-calculus-and-geometry/AM196-antenna-radiation-integral) | H | Hertzian dipole ℓ = 0.01λ: R_rad = 80π²(ℓ/λ)²: 78.96 mΩ → 78.9 mΩ (-0.08 %) |
| AM-197 | [Antenna arrays: array factor, beam steering and pattern multiplication](projects/applied-math/K-fields-vector-calculus-and-geometry/AM197-array-factor-and-pattern-multiplication) | M | N = 8, d = λ/2 broadside: first null at arcsin(2/N) from broadside: 14.48 ° → 14.48 ° (+0.02 %) |
| AM-198 | [Conformal mapping for coplanar lines: exact answers from complex analysis](projects/applied-math/K-fields-vector-calculus-and-geometry/AM198-conformal-mapping-for-coplanar-lines) | H | CPW in air: Z₀ = 30π·K(k′)/K(k) vs extrapolated finite-difference solution: 120.6 Ω → 120.3 Ω (-0.23 %) |
| AM-199 | [Green's functions: solving field problems by superposition](projects/applied-math/K-fields-vector-calculus-and-geometry/AM199-greens-functions) | H | 1-D: inverse of the finite-difference matrix = h·G(xᵢ, xⱼ) at the nodes (max difference): 0 → 2.2985e-17 (+2.2985e-17) |
| AM-200 | [Spherical harmonics: radiation patterns as sums of modes](projects/applied-math/K-fields-vector-calculus-and-geometry/AM200-spherical-harmonics-in-radiation) | H | Orthonormality ⟨Y_lm, Y_l′m′⟩ = δ (l ≤ 10; worst deviation): 0 → 1.2479e-13 (+1.2479e-13) |
| AM-201 | [Skin depth from Maxwell's equations, verified by solving the diffusion equation](projects/applied-math/K-fields-vector-calculus-and-geometry/AM201-skin-depth-derivation) | M | 1 kHz: decay length of the amplitude vs δ = √(2/ωμσ): 2.09 mm → 2.09 mm (-0.00 %) |
| AM-202 | [Distributed vs lumped: exactly when the lumped model fails](projects/applied-math/K-fields-vector-calculus-and-geometry/AM202-distributed-vs-lumped-models) | M | Error of one π section grows as (βℓ)³: log-log slope at small electrical length (I first expected 2): 3 → 2.986 (-0.01447) |
| AM-203 | [Cylindrical and spherical coordinates: operators, Jacobians and a solved problem](projects/applied-math/K-fields-vector-calculus-and-geometry/AM203-coordinate-transformations) | M | Cylindrical Laplacian ∂ρρ + ∂ρ/ρ + ∂φφ/ρ² + ∂zz vs Cartesian (worst relative error, 300 points): 0 → 3.2885e-07 (+3.2885e-07) |

### L. Information theory

| # | Project | Lvl | Headline result |
|---|---|---|---|
| AM-204 | [Entropy calculator (interactive, verified on real text)](projects/applied-math/L-information-theory/AM204-entropy-calculator) | E | Entropy of 300 random distributions: JavaScript vs Python (max difference): 0 bit → 1.7764e-15 bit (+1.7764e-15 bit) |
| AM-205 | [Channel capacity: the Blahut–Arimoto algorithm](projects/applied-math/L-information-theory/AM205-channel-capacity) | H | BSC(ε = 0.01): capacity 1 − H₂(ε): 0.9192 bit → 0.9192 bit (+0.00 %) |
| AM-206 | [Mutual information of continuous signals: estimators and a real ECG](projects/applied-math/L-information-theory/AM206-mutual-information-estimation) | H | KSG estimator vs Gaussian closed form −½log₂(1 − ρ²), worst absolute error for ρ = 0…0.95: 0 bit → 0.03807 bit (+0.03807 bit) |
| AM-207 | [Rate–distortion theory against real quantisers](projects/applied-math/L-information-theory/AM207-rate-distortion) | H | Lloyd–Max, 1 bit: SNR (optimal 2-level quantiser of a Gaussian: 1 − 2/π distortion → 4.40 dB): 4.396 dB → 4.396 dB (+0 dB) |
| AM-208 | [Arithmetic coding: reaching the entropy bit by bit](projects/applied-math/L-information-theory/AM208-arithmetic-coding) | H | Bernoulli(0.01), 10⁵ symbols: code length vs the model's ideal −Σlog₂p: 8258 bit → 8260 bit (+1.694 bit) |
| AM-209 | [LZ77: universal compression by pointing into the past](projects/applied-math/L-information-theory/AM209-lz77-compression) | M | Round trip of the whole book (bytes differing): 0 → 0 (+0) |
| AM-210 | [AWGN capacity and what real constellations can achieve](projects/applied-math/L-information-theory/AM210-awgn-capacity) | H | Every constellation rate stays below the Shannon capacity (violations beyond Monte-Carlo noise): 0 → 0 (+0) |
| AM-211 | [Water-filling: optimal power allocation over parallel channels](projects/applied-math/L-information-theory/AM211-water-filling) | M | 200 random channel sets: best capacity found by SLSQP minus water-filling (never positive): 0 bit → 3.9413e-14 bit (+3.9413e-14 bit) |
| AM-212 | [MIMO capacity scaling: why more antennas mean more bits](projects/applied-math/L-information-theory/AM212-mimo-capacity-scaling) | H | 2×2: bits gained per 3 dB at high SNR = min(N_t, N_r): 2 bit → 1.942 bit (-2.88 %) |
| AM-213 | [Error exponents: how fast block error falls with code length](projects/applied-math/L-information-theory/AM213-error-exponents) | H | E_r at rate 0 equals E₀(1) (the cutoff rate R₀): 0.5765 bit → 0.5765 bit (+0.00 %) |
| AM-214 | [Compressed sensing: recovering sparse signals from few measurements](projects/applied-math/L-information-theory/AM214-compressed-sensing) | H | 50 % success point of OMP vs 2k·ln(N/k): ratio, median over k = 4…40: 1 → 0.7995 (-20.05 %) |
| AM-215 | [Nyquist and Shannon: sampling rate, signalling rate and capacity](projects/applied-math/L-information-theory/AM215-nyquist-vs-shannon) | M | Sampling at 2.5B: sinc reconstruction error (only truncation of the series): 0 → 9.8206e-04 (+9.8206e-04) |
| AM-216 | [How close do real codes get to the Shannon limit?](projects/applied-math/L-information-theory/AM216-gap-to-shannon-limit) | H | Shannon limit for rate ½ with binary inputs (E_b/N₀): 0.187 dB → 0.1784 dB (-0.008593 dB) |
| AM-217 | [The source coding theorem, demonstrated](projects/applied-math/L-information-theory/AM217-source-coding-theorem) | M | AEP: std of −(1/n)log₂p(Xⁿ) at n = 1000 vs σ/√n: 0.0253 bit → 0.02536 bit (+0.26 %) |
| AM-218 | [Kolmogorov complexity: compression as a (computable) upper bound](projects/applied-math/L-information-theory/AM218-kolmogorov-complexity) | H | Counting argument: random 1 kB strings that any of three compressors shortened (of 1000): 0 → 0 (+0) |

## Signal Lab — 214 electrical-engineering projects


### A. Analog circuit design & simulation

| # | Project | Lvl | Headline result |
|---|---|---|---|
| SL-001 | [RC low-pass filter](projects/signal-lab/A-analog-circuit-design/SL001-rc-lowpass-filter) | E | −3 dB cutoff frequency: 994.7 Hz → 964.7 Hz (-3.02 %) |
| SL-002 | [RC high-pass filter](projects/signal-lab/A-analog-circuit-design/SL002-rc-highpass-filter) | E | −3 dB cutoff frequency: 994.7 Hz → 964.5 Hz (-3.03 %) |
| SL-003 | [Sallen-Key active low-pass filter](projects/signal-lab/A-analog-circuit-design/SL003-sallen-key-lowpass) | M | Q=0.5: gain at f₀: -6.021 dB → -6.02 dB (+1.3289e-04 dB) |
| SL-004 | [Multiple-feedback band-pass filter](projects/signal-lab/A-analog-circuit-design/SL004-mfb-bandpass) | M | Centre frequency f₀: 1.015 kHz → 1.01 kHz (-0.51 %) |
| SL-005 | [Butterworth vs Chebyshev (4th order)](projects/signal-lab/A-analog-circuit-design/SL005-butterworth-vs-chebyshev) | M | Butterworth: gain at passband edge 1 kHz: -3.011 dB → -3.369 dB (-0.3587 dB) |
| SL-006 | [60 Hz twin-T notch filter](projects/signal-lab/A-analog-circuit-design/SL006-twin-t-notch) | M | Notch frequency: 60 Hz → 59.97 Hz (-0.05 %) |
| SL-007 | [Common-emitter BJT amplifier](projects/signal-lab/A-analog-circuit-design/SL007-common-emitter-amplifier) | M | Base voltage V_B: 2.105 V → 2.035 V (-3.35 %) |
| SL-008 | [BJT differential pair](projects/signal-lab/A-analog-circuit-design/SL008-differential-pair) | M | Tail current I_EE: 1.135 mA → 1.131 mA (-0.37 %) |
| SL-009 | [Op-amp gain lab](projects/signal-lab/A-analog-circuit-design/SL009-op-amp-gain-lab) | E | inverting A=-1: \|gain\|: 1 → 1 (-0.00 %) |
| SL-010 | [Three-op-amp instrumentation amplifier](projects/signal-lab/A-analog-circuit-design/SL010-instrumentation-amplifier) | M | Differential gain: 51 → 50.99 (-0.03 %) |
| SL-011 | [Wien bridge oscillator](projects/signal-lab/A-analog-circuit-design/SL011-wien-bridge-oscillator) | M | Oscillation frequency: 1 kHz → 991 Hz (-0.91 %) |
| SL-012 | [Colpitts LC oscillator](projects/signal-lab/A-analog-circuit-design/SL012-colpitts-oscillator) | M | L = 4.7 µH: frequency: 2.557 MHz → 2.553 MHz (-0.14 %) |
| SL-013 | [555 timer astable multivibrator](projects/signal-lab/A-analog-circuit-design/SL013-555-timer-astable) | E | R_A=1k R_B=10k C=10n: frequency: 6.871 kHz → 6.742 kHz (-1.89 %) |
| SL-014 | [Schmitt trigger (comparator with hysteresis)](projects/signal-lab/A-analog-circuit-design/SL014-schmitt-trigger) | E | Upper threshold V_T+: 250 mV → 264.8 mV (+5.92 %) |
| SL-015 | [Rectifier and reservoir-capacitor ripple study](projects/signal-lab/A-analog-circuit-design/SL015-rectifier-ripple-study) | E | half-wave, C = 470 µF: ripple (pk-pk): 5.647 V → 4.17 V (-26.16 %) |
| SL-016 | [LM317-style linear regulator](projects/signal-lab/A-analog-circuit-design/SL016-linear-voltage-regulator) | M | Output voltage (12 V in, 100 mA): 5.036 V → 5.034 V (-0.05 %) |
| SL-017 | [Zener shunt regulator](projects/signal-lab/A-analog-circuit-design/SL017-zener-shunt-regulator) | E | Output voltage at no load: 5.1 V → 5.147 V (+0.93 %) |
| SL-018 | [Charge pump / voltage doubler](projects/signal-lab/A-analog-circuit-design/SL018-charge-pump-voltage-doubler) | M | V_out at R_L = 5000 Ω: 9.477 V → 9.473 V (-0.04 %) |
| SL-019 | [Class-A vs Class-B vs Class-AB output stages](projects/signal-lab/A-analog-circuit-design/SL019-class-a-vs-class-ab) | M | class A: efficiency at V̂ ≈ 12.7 V: 17.72 % → 18.29 % (+0.565 pp) |
| SL-020 | [Class-D switching amplifier](projects/signal-lab/A-analog-circuit-design/SL020-class-d-amplifier) | H | 1 kHz output amplitude: 11.78 V → 11.76 V (-0.24 %) |
| SL-021 | [BJT current mirrors (basic vs Wilson)](projects/signal-lab/A-analog-circuit-design/SL021-current-mirror) | M | Basic: I_out/I_ref (β error, at V_CE = V_BE): 0.9938 → 0.9959 (+0.20 %) |
| SL-022 | [Envelope (AM peak) detector](projects/signal-lab/A-analog-circuit-design/SL022-envelope-peak-detector) | E | Best RC is within the no-clipping bound: 1 → 1 (+0) |
| SL-023 | [Precision (super-diode) rectifier](projects/signal-lab/A-analog-circuit-design/SL023-precision-rectifier) | M | plain: mean output at 100 mV peak: 31.83 mV → 41.04 µV (-99.87 %) |
| SL-024 | [Logarithmic and anti-log amplifiers](projects/signal-lab/A-analog-circuit-design/SL024-log-antilog-amplifier) | H | Log slope: -0.05954 V/dec → -0.05981 V/dec (-0.46 %) |
| SL-025 | [Four-quadrant analog multiplier (Gilbert cell)](projects/signal-lab/A-analog-circuit-design/SL025-analog-multiplier-gilbert-cell) | H | ΔV_out at v₁ = 20 mV, v₂ = 30 mV: 380.1 mV → 380.1 mV (-0.00 %) |

### B. Power electronics

| # | Project | Lvl | Headline result |
|---|---|---|---|
| SL-026 | [Buck (step-down) converter](projects/signal-lab/B-power-electronics/SL026-buck-converter) | M | D = 0.25: V_out (ideal D·V_in): 3 V → 2.752 V (-8.26 %) |
| SL-027 | [Boost converter: continuous vs discontinuous conduction](projects/signal-lab/B-power-electronics/SL027-boost-converter) | M | R_L = 10 Ω (CCM, K = 0.440): V_out: 9.65 V → 9.541 V (-1.12 %) |
| SL-028 | [Inverting buck-boost converter](projects/signal-lab/B-power-electronics/SL028-buck-boost-converter) | M | D = 0.33: V_out: -5.91 V → -5.649 V (+4.43 %) |
| SL-029 | [Flyback converter (isolated, coupled inductor)](projects/signal-lab/B-power-electronics/SL029-flyback-converter) | H | Output voltage (ideal n·V_in·D/(1−D)): 4 V → 3.502 V (-12.44 %) |
| SL-030 | [Full-bridge SPWM inverter](projects/signal-lab/B-power-electronics/SL030-full-bridge-inverter-spwm) | H | Bridge fundamental amplitude (m·V_dc): 160 V → 158.5 V (-0.92 %) |
| SL-031 | [Boost power-factor-correction stage](projects/signal-lab/B-power-electronics/SL031-power-factor-correction) | H | PFC power factor: 1 → 0.9968 (-0.32 %) |
| SL-032 | [MPPT solar tracker (perturb & observe)](projects/signal-lab/B-power-electronics/SL032-mppt-solar-tracker) | H | Steady-state tracking efficiency (1000 W/m²): 100 % → 99.98 % (-0.0122 pp) |
| SL-033 | [CC-CV lithium-ion charger](projects/signal-lab/B-power-electronics/SL033-cc-cv-battery-charger) | M | 1.0C: SOC at CC→CV transition: 85 % → 85 % (+3.87e-12 pp) |
| SL-034 | [Li-ion equivalent-circuit model fitted to NASA aging data](projects/signal-lab/B-power-electronics/SL034-li-ion-equivalent-model) | M | Load-step resistance ΔV/ΔI vs EIS (R_e + R_ct): 114.1 mΩ → 107.3 mΩ (-6.01 %) |
| SL-035 | [MOSFET loss & junction-temperature model](projects/signal-lab/B-power-electronics/SL035-mosfet-thermal-model) | M | T_j at 100 kHz: closed form vs Foster transient: 61.63 °C → 61.62 °C (-0.01 %) |
| SL-036 | [Gate resistance vs switching loss and EMI](projects/signal-lab/B-power-electronics/SL036-gate-driver-switching-loss) | H | R_g = 2 Ω: drain dV/dt: 41.46 GV/s → 40.25 GV/s (-2.93 %) |
| SL-037 | [Three-phase vs single-phase bridge rectifier](projects/signal-lab/B-power-electronics/SL037-three-phase-rectifier) | M | 6-pulse DC voltage: 540.2 V → 538.3 V (-0.35 %) |

### C. Digital logic & HDL

| # | Project | Lvl | Headline result |
|---|---|---|---|
| SL-038 | [Full adder from gates](projects/signal-lab/C-digital-logic-and-hdl/SL038-full-adder) | E | Truth-table errors (8 vectors): 0 → 0 (+0) |
| SL-039 | [Ripple-carry adder and its propagation delay](projects/signal-lab/C-digital-logic-and-hdl/SL039-4bit-ripple-carry-adder) | E | 4-bit worst-case delay: 7 gate delays → 7 gate delays (+0 gate delays) |
| SL-040 | [Carry-lookahead adder: speed vs area](projects/signal-lab/C-digital-logic-and-hdl/SL040-carry-lookahead-adder) | M | 4-bit CLA worst-case delay: 4 gate delays → 4 gate delays (+0 gate delays) |
| SL-041 | [8-bit ALU with flags](projects/signal-lab/C-digital-logic-and-hdl/SL041-8bit-alu) | M | Mismatches over 32,032 vectors (all ops): 0 → 0 (+0) |
| SL-042 | [Multi-port register file](projects/signal-lab/C-digital-logic-and-hdl/SL042-register-file) | M | Read mismatches in 20,000 random cycles: 0 → 0 (+0) |
| SL-043 | [Traffic-light finite state machine](projects/signal-lab/C-digital-logic-and-hdl/SL043-traffic-light-fsm) | E | Green phase duration (no request): 10 s → 10 s (+0 s) |
| SL-044 | [Vending machine FSM with change and error states](projects/signal-lab/C-digital-logic-and-hdl/SL044-vending-machine-fsm) | E | Event mismatches hardware vs Python model: 0 → 0 (+0) |
| SL-045 | [UART transmitter (8N1)](projects/signal-lab/C-digital-logic-and-hdl/SL045-uart-transmitter) | M | Bit period: 8680 ns → 8680 ns (+0.00 %) |
| SL-046 | [UART receiver with 16× oversampling](projects/signal-lab/C-digital-logic-and-hdl/SL046-uart-receiver) | M | Data-error-free limit, fast TX (\|ε\|): 0.0556 → 0.055 (-6.0000e-04) |
| SL-047 | [SPI master (mode 0)](projects/signal-lab/C-digital-logic-and-hdl/SL047-spi-master) | M | MISO bytes wrong (256 full-duplex transfers): 0 → 0 (+0) |
| SL-048 | [I²C master with ACK handling](projects/signal-lab/C-digital-logic-and-hdl/SL048-i2c-master) | H | Read-back errors (4 registers): 0 → 0 (+0) |
| SL-049 | [Parameterised PWM generator](projects/signal-lab/C-digital-logic-and-hdl/SL049-pwm-generator-hdl) | E | Duty at CMP = 1: 0.3906 % → 0.3906 % (+0 pp) |
| SL-050 | [Switch debouncer in logic](projects/signal-lab/C-digital-logic-and-hdl/SL050-switch-debouncer) | E | Output edges for 40 presses/releases: 40 → 40 (+0) |
| SL-051 | [Multiplexed 7-segment display driver](projects/signal-lab/C-digital-logic-and-hdl/SL051-seven-segment-driver) | E | Decoder mismatches (16 hex digits): 0 → 0 (+0) |
| SL-052 | [Binary-to-BCD (double-dabble) in hardware](projects/signal-lab/C-digital-logic-and-hdl/SL052-binary-to-bcd-double-dabble) | M | 8-bit: conversion errors over all 256 inputs: 0 → 0 (+0) |
| SL-053 | [LFSR pseudorandom generator and its statistics](projects/signal-lab/C-digital-logic-and-hdl/SL053-lfsr-pseudorandom-generator) | M | 8-bit period: 255 → 255 (+0) |
| SL-054 | [Asynchronous FIFO with Gray-code pointers](projects/signal-lab/C-digital-logic-and-hdl/SL054-async-fifo-cdc) | H | Ordering/data errors (5,000 words across domains): 0 → 0 (+0) |
| SL-055 | [Single-cycle RISC-V (RV32I subset) CPU](projects/signal-lab/C-digital-logic-and-hdl/SL055-single-cycle-risc-cpu) | H | sum_1_to_100: register mismatches vs ISS: 0 → 0 (+0) |
| SL-056 | [5-stage pipelined RISC-V with forwarding and hazards](projects/signal-lab/C-digital-logic-and-hdl/SL056-pipelined-cpu) | H | sum_1_to_100: architectural-state mismatches vs ISS: 0 → 0 (+0) |
| SL-057 | [Clock divider and prescaler (including odd 50 % duty)](projects/signal-lab/C-digital-logic-and-hdl/SL057-clock-divider) | E | ÷2: output frequency: 50 MHz → 50 MHz (+0.00 %) |
| SL-058 | [Asynchronous SRAM controller](projects/signal-lab/C-digital-logic-and-hdl/SL058-sram-controller) | M | 25 MHz: minimum wait states: 1 → 1 (+0) |
| SL-059 | [Verified testbench suite: assertions and coverage](projects/signal-lab/C-digital-logic-and-hdl/SL059-verified-testbench-suite) | M | Assertion failures on correct ALU: 0 → 0 (+0) |

### D. Digital signal processing

| # | Project | Lvl | Headline result |
|---|---|---|---|
| SL-060 | [FFT from scratch (DFT → radix-2)](projects/signal-lab/D-digital-signal-processing/SL060-fft-from-scratch) | M | Max relative error, iterative FFT (N = 4096): 1.2000e-14 → 7.2848e-16 (-1.1272e-14) |
| SL-061 | [Window functions and spectral leakage](projects/signal-lab/D-digital-signal-processing/SL061-window-function-comparison) | M | rectangular: highest sidelobe: -13.3 dB → -13.25 dB (+0.04568 dB) |
| SL-062 | [FIR filter designer (windowed sinc / Kaiser)](projects/signal-lab/D-digital-signal-processing/SL062-fir-filter-designer) | M | A = 40 dB: stopband attenuation: 40 dB → 39.87 dB (-0.1272 dB) |
| SL-063 | [IIR filter designer: bilinear transform, poles and quantisation](projects/signal-lab/D-digital-signal-processing/SL063-iir-filter-designer) | M | butter pre-warped: cutoff (−3 dB): 1 kHz → 1 kHz (-0.00 %) |
| SL-064 | [Convolution visualiser](projects/signal-lab/D-digital-signal-processing/SL064-convolution-visualiser) | E | Output length: 17 → 17 (+0) |
| SL-065 | [Multi-band audio equaliser (peaking biquads)](projects/signal-lab/D-digital-signal-processing/SL065-audio-equaliser) | M | 125 Hz band: gain at centre: -6 dB → -5.999 dB (+6.3742e-04 dB) |
| SL-066 | [Spectral-subtraction noise removal](projects/signal-lab/D-digital-signal-processing/SL066-audio-noise-removal) | M | SNR gain at 0 dB input vs oracle ideal binary mask: 16.11 dB → 8.36 dB (-7.746 dB) |
| SL-067 | [Spectrogram tool and the time-frequency trade-off](projects/signal-lab/D-digital-signal-processing/SL067-spectrogram-tool) | E | Own STFT vs scipy.signal.stft (max relative difference): 0 → 9.6198e-08 (+9.6198e-08) |
| SL-068 | [Pitch detection: autocorrelation vs cepstrum](projects/signal-lab/D-digital-signal-processing/SL068-pitch-detection) | M | Autocorrelation accuracy, full harmonics (±50 cents): 100 % → 99 % (-1 pp) |
| SL-069 | [Guitar tuner (cents-accurate note detection)](projects/signal-lab/D-digital-signal-processing/SL069-guitar-tuner) | M | String identified correctly (60 notes): 100 % → 100 % (+0 pp) |
| SL-070 | [DTMF decoder with the Goertzel algorithm](projects/signal-lab/D-digital-signal-processing/SL070-dtmf-decoder) | M | Goertzel power vs \|DFT bin\|² (697 Hz, bin-centred check): 1.053e+04 → 1.053e+04 (+0.00 %) |
| SL-071 | [Morse code (CW) decoder](projects/signal-lab/D-digital-signal-processing/SL071-morse-code-decoder) | M | 15 WPM: SNR where CER < 2 % (this decoder): -4.99 dB → -3 dB (+1.99 dB) |
| SL-072 | [Echo and Schroeder reverb from delay lines](projects/signal-lab/D-digital-signal-processing/SL072-echo-and-reverb) | E | RT60 (design 0.8 s): 800 ms → 801.2 ms (+0.15 %) |
| SL-073 | [Sample-rate conversion 48 kHz → 44.1 kHz (polyphase)](projects/signal-lab/D-digital-signal-processing/SL073-resampling-rate-conversion) | M | Passband gain at 1 kHz: 0 dB → -1.7694e-06 dB (-1.7694e-06 dB) |
| SL-074 | [Aliasing demonstrator (Nyquist in action)](projects/signal-lab/D-digital-signal-processing/SL074-aliasing-demonstrator) | E | Max \|apparent − predicted\| over 301 tones (away from 0 and f_s/2): 0 Hz → 82.51 µHz (+82.51 µHz) |
| SL-075 | [Quantisation noise and the 6 dB-per-bit rule](projects/signal-lab/D-digital-signal-processing/SL075-quantisation-noise-study) | M | 4-bit SNR: 25.83 dB → 23.28 dB (-2.555 dB) |
| SL-076 | [Dither: trading distortion for noise](projects/signal-lab/D-digital-signal-processing/SL076-dithering-demo) | M | RPDF: total error power re Δ²/12: 3.01 dB → 2.776 dB (-0.2341 dB) |
| SL-077 | [Adaptive LMS noise canceller](projects/signal-lab/D-digital-signal-processing/SL077-adaptive-lms-filter) | H | μ = 0.001: misadjustment (excess MSE / min MSE): 0.0159 → 0.01711 (+7.58 %) |
| SL-078 | [Kalman filter vs moving average](projects/signal-lab/D-digital-signal-processing/SL078-kalman-filter-tracking) | H | Kalman position RMSE (DARE prediction): 745.4 mm → 750.5 mm (+0.69 %) |
| SL-079 | [Wavelet multi-resolution analysis of a transient](projects/signal-lab/D-digital-signal-processing/SL079-wavelet-analysis) | H | haar: perfect reconstruction error (max \|Δ\|): 0 → 1.7764e-15 (+1.7764e-15) |
| SL-080 | [Cross-correlation time-delay estimation (TDOA)](projects/signal-lab/D-digital-signal-processing/SL080-cross-correlation-tdoa) | M | Delay RMSE at 10 dB SNR vs CRLB: 1.114 µs → 1.419 µs (+27.42 %) |
| SL-081 | [Delay-and-sum beamforming with a uniform linear array](projects/signal-lab/D-digital-signal-processing/SL081-beamforming-simulation) | H | Steer 0°: half-power beamwidth: 12.69 ° → 12.8 ° (+0.88 %) |
| SL-082 | [Compressive sensing: recovering sparse signals from few samples](projects/signal-lab/D-digital-signal-processing/SL082-compressive-sensing) | H | k = 4: M at 50 % recovery (2k·ln(N/k)): 33.27 measurements → 20.47 measurements (-38.47 %) |
| SL-083 | [Browser audio spectrum analyser (Web Audio API)](projects/signal-lab/D-digital-signal-processing/SL083-browser-audio-analyzer) | M | JS FFT vs numpy.fft (max relative error, N = 2048): 0 → 1.2335e-14 (+1.2335e-14) |
| SL-084 | [Goertzel vs FFT: when does a single bin win?](projects/signal-lab/D-digital-signal-processing/SL084-goertzel-vs-fft-benchmark) | M | N = 256: break-even tones (2·log₂N) vs counted multiplies: 16 tones → 15.81 tones (-1.16 %) |

### E. RF, radio & satellites (real signals)

| # | Project | Lvl | Headline result |
|---|---|---|---|
| SL-085 | [Decode a SatNOGS observation: pass geometry vs signal quality](projects/signal-lab/E-rf-radio-and-satellites/SL085-decode-a-satnogs-observation) | H | Max elevation of the pass (SGP4 vs SatNOGS schedule): 89 ° → 89.21 ° (+0.2096 °) |
| SL-086 | [NOAA APT weather-satellite image decoder](projects/signal-lab/E-rf-radio-and-satellites/SL086-noaa-apt-image-decode) | M | Words per line (sync spacing): 2080 words → 2080 words (-0.01 %) |
| SL-087 | [Meteor-M LRPT receive chain: QPSK, Viterbi, sync and derandomising](projects/signal-lab/E-rf-radio-and-satellites/SL087-meteor-lrpt-chain) | H | PN sequence period (x⁸+x⁷+x⁵+x³+1): 255 bits → 255 bits (+0 bits) |
| SL-088 | [ADS-B aircraft messages decoded from raw IQ samples](projects/signal-lab/E-rf-radio-and-satellites/SL088-adsb-decode-from-iq) | H | CRC false accepts among 20,000 random 112-bit blocks: 0.001192 → 0 (-0.001192) |
| SL-089 | [24-hour HF propagation on one path (WSPR network data)](projects/signal-lab/E-rf-radio-and-satellites/SL089-webSDR-propagation-study) | M | 20 m: fraction of spots with the path midpoint sunlit: 0.8 → 0.6278 (-0.1722) |
| SL-090 | [AM demodulation from complex baseband (IQ)](projects/signal-lab/E-rf-radio-and-satellites/SL090-am-demodulation-from-iq) | M | Synchronous detector SNR at CNR 15 dB: 5.627 dB → 5.848 dB (+0.221 dB) |
| SL-091 | [FM demodulation from IQ (phase differentiator) and the FM threshold](projects/signal-lab/E-rf-radio-and-satellites/SL091-fm-demodulation-from-iq) | M | β = 1: output SNR at CNR 20 dB: 18.24 dB → 18.74 dB (+0.5013 dB) |
| SL-092 | [SSB modulation and demodulation with the Hilbert transform](projects/signal-lab/E-rf-radio-and-satellites/SL092-ssb-demodulation) | H | 31-tap Hilbert: sideband suppression at 1 kHz (2/δ): 35.53 dB → 36.21 dB (+0.6792 dB) |
| SL-093 | [RTTY (45.45 Bd, 170 Hz FSK) decoder](projects/signal-lab/E-rf-radio-and-satellites/SL093-rtty-fsk-decoder) | M | Clean decode character errors: 0 → 0 (+0) |
| SL-094 | [Global WSPR spot statistics: distance by band](projects/signal-lab/E-rf-radio-and-satellites/SL094-wspr-spot-analysis) | M | 20 m: steepest fall in spot density (single-hop limit, h = 300 km): 3836 km → 4125 km (+7.54 %) |
| SL-095 | [Ionosphere from propagation data: day/night and seasonal behaviour](projects/signal-lab/E-rf-radio-and-satellites/SL095-ionosphere-study) | H | 10 m: local hour of peak long-path activity (midday F2 maximum): 13 h → 15 h (+2 h) |
| SL-096 | [Satellite Doppler shift through a pass](projects/signal-lab/E-rf-radio-and-satellites/SL096-doppler-shift-calculator) | M | Max Doppler shift at horizon: 10.5 kHz → 9.767 kHz (-6.95 %) |
| SL-097 | [Satellite pass predictor: two-body + J2 vs SGP4](projects/signal-lab/E-rf-radio-and-satellites/SL097-satellite-pass-predictor) | M | NOAA 19: Kepler-only position error after 24 h (J2 secular drift × a): 759 km → 766.2 km (+0.95 %) |
| SL-098 | [Link budget calculator (validated on a real NOAA pass)](projects/signal-lab/E-rf-radio-and-satellites/SL098-link-budget-calculator) | M | Free-space path loss at 1,500 km, 137.9 MHz: 138.8 dB → 138.8 dB (+0 dB) |
| SL-099 | [Wire-antenna simulator by the method of moments](projects/signal-lab/E-rf-radio-and-satellites/SL099-antenna-pattern-simulator) | H | λ/2 input resistance (a = λ/1000) vs induced-EMF 73.1 Ω: 73.1 Ω → 85.78 Ω (+17.35 %) |
| SL-100 | [Dipole vs 3-element Yagi: gain, beamwidth and front-to-back](projects/signal-lab/E-rf-radio-and-satellites/SL100-dipole-vs-yagi) | M | Dipole directivity: 2.15 dBi → 2.126 dBi (-0.02387 dBi) |
| SL-101 | [Interactive Smith chart](projects/signal-lab/E-rf-radio-and-satellites/SL101-interactive-smith-chart) | H | Γ: max \|JS − NumPy\| over 200 loads: 0 → 2.4825e-16 (+2.4825e-16) |
| SL-102 | [Transmission-line reflections, standing waves and VSWR](projects/signal-lab/E-rf-radio-and-satellites/SL102-transmission-line-reflections) | M | 150 Ω: settled source voltage: 857.1 mV → 857.1 mV (-53.98 µV) |
| SL-103 | [L-network impedance-matching designer](projects/signal-lab/E-rf-radio-and-satellites/SL103-matching-network-designer) | M | Solution 1: \|Γ\| at 100 MHz: 0 → 2.1316e-16 (+2.1316e-16) |
| SL-104 | [Noise-figure cascade (Friis) vs Monte Carlo](projects/signal-lab/E-rf-radio-and-satellites/SL104-noise-figure-cascade) | M | cable → LNA → mixer → IF: noise figure: 4.423 dB → 4.42 dB (-0.002924 dB) |
| SL-105 | [Spectrum occupancy survey of the WSPR sub-bands](projects/signal-lab/E-rf-radio-and-satellites/SL105-spectrum-occupancy-survey) | M | Fraction of transmissions within 6 Hz of another (uniform-spread Poisson): 0.9778 → 0.5988 (-0.379) |
| SL-106 | [Pulse-compression radar: range resolution and processing gain](projects/signal-lab/E-rf-radio-and-satellites/SL106-radar-range-simulation) | H | Compressed −3 dB width (≈ 0.886/B): 17.72 ns → 18.12 ns (+2.29 %) |

### F. Communication systems

| # | Project | Lvl | Headline result |
|---|---|---|---|
| SL-107 | [AM / FM / PM modulation visualiser](projects/signal-lab/F-communication-systems/SL107-modulation-visualiser) | E | β = 0.5: max \|sideband − \|J_n(β)\|\|: 0 → 1.6586e-13 (+1.6586e-13) |
| SL-108 | [BPSK bit-error rate vs SNR](projects/signal-lab/F-communication-systems/SL108-bpsk-ber-curve) | M | BER at Eb/N0 = 4 dB: 0.0125 → 0.01248 (-0.15 %) |
| SL-109 | [QPSK: twice the bits, same BER](projects/signal-lab/F-communication-systems/SL109-qpsk-system) | M | QPSK BER at 4 dB (= BPSK): 0.0125 → 0.01243 (-0.60 %) |
| SL-110 | [16-QAM: constellation, EVM and symbol errors](projects/signal-lab/F-communication-systems/SL110-16qam-constellation) | M | SER at Es/N0 = 14 dB: 0.03715 → 0.03692 (-0.62 %) |
| SL-111 | [OFDM with cyclic prefix over a multipath channel](projects/signal-lab/F-communication-systems/SL111-ofdm-simulation) | H | BER with CP at 8 dB (per-subcarrier Q-average): 0.0376 → 0.03787 (+0.72 %) |
| SL-112 | [Eye diagrams, ISI and raised-cosine pulses](projects/signal-lab/F-communication-systems/SL112-eye-diagram-generator) | M | Rectangular + RC channel f_c·T = 0.3: vertical eye opening: 0.6963 → 0.6963 (+1.4766e-10) |
| SL-113 | [Hamming (7,4) code: encode, corrupt, correct](projects/signal-lab/F-communication-systems/SL113-hamming-code) | M | G·Hᵀ = 0 (valid code): 0 → 0 (+0) |
| SL-114 | [Reed–Solomon RS(255,223): the satellite / CD code](projects/signal-lab/F-communication-systems/SL114-reed-solomon-codes) | H | Largest error count always corrected (t = (n−k)/2): 16 symbols → 16 symbols (+0 symbols) |
| SL-115 | [Convolutional code + Viterbi decoder: hard vs soft decisions](projects/signal-lab/F-communication-systems/SL115-convolutional-viterbi) | H | Soft Viterbi BER at 3 dB vs union bound: 3.3571e-04 → 6.6667e-05 (-2.6904e-04) |
| SL-116 | [CRC-32: what it catches and what it misses](projects/signal-lab/F-communication-systems/SL116-crc-checker) | M | Bitwise CRC-32 = zlib.crc32: 3.4251e+08 → 3.4251e+08 (+0) |
| SL-117 | [AWGN, Rayleigh and Rician fading channels](projects/signal-lab/F-communication-systems/SL117-channel-models) | M | Rayleigh BER at 12 dB: 0.01506 → 0.01509 (+0.17 %) |
| SL-118 | [Spread spectrum and CDMA with Walsh and Gold-like codes](projects/signal-lab/F-communication-systems/SL118-spread-spectrum-cdma) | H | Walsh codes: BER pooled over all K (should equal single-user BER): 1.9091e-04 → 1.7857e-04 (-6.46 %) |
| SL-119 | [Frequency hopping against a narrowband jammer](projects/signal-lab/F-communication-systems/SL119-frequency-hopping) | M | 1 jammed channels: uncoded BER: 0.01018 → 0.01011 (-0.66 %) |
| SL-120 | [Shannon capacity explorer](projects/signal-lab/F-communication-systems/SL120-shannon-capacity-explorer) | M | BPSK: BER at its predicted 10⁻⁵ operating point (Monte Carlo): 1.0000e-05 → 7.5000e-06 (-2.5000e-06) |
| SL-121 | [Carrier and timing recovery loops](projects/signal-lab/F-communication-systems/SL121-synchronisation-recovery) | H | B_L·T = 0.005: RMS phase jitter after lock: 0.01257 rad → 0.01149 rad (-8.59 %) |

### G. Electromagnetics & device physics

| # | Project | Lvl | Headline result |
|---|---|---|---|
| SL-122 | [1-D FDTD: an EM pulse hitting a dielectric](projects/signal-lab/G-electromagnetics-and-device-physics/SL122-1d-fdtd-wave-propagation) | M | Reflection coefficient r = (1−n)/(1+n): -0.3333 → -0.3337 (-0.10 %) |
| SL-123 | [2-D FDTD: diffraction through a slit](projects/signal-lab/G-electromagnetics-and-device-physics/SL123-2d-fdtd-scattering) | H | First diffraction null angle (sin θ = λ/a): 19.47 ° → 20 ° (+2.72 %) |
| SL-124 | [Rectangular waveguide modes and cutoff frequencies](projects/signal-lab/G-electromagnetics-and-device-physics/SL124-waveguide-mode-visualiser) | H | TE₁₀ cutoff: 6.557 GHz → 6.557 GHz (-0.00 %) |
| SL-125 | [Microstrip impedance: formula vs 2-D field solver](projects/signal-lab/G-electromagnetics-and-device-physics/SL125-microstrip-calculator) | M | w = 1.2 mm: Z₀ (FD, Richardson order ½, vs Hammerstad–Jensen): 81.1 Ω → 81.19 Ω (+0.12 %) |
| SL-126 | [Coaxial cable: fields, capacitance and impedance](projects/signal-lab/G-electromagnetics-and-device-physics/SL126-coaxial-cable-field-plot) | M | RG-58: capacitance per metre: 105.7 pF → 105.6 pF (-0.09 %) |
| SL-127 | [Parallel-plate capacitor: fringing fields by finite differences](projects/signal-lab/G-electromagnetics-and-device-physics/SL127-laplace-field-solver) | M | w/d = 1: C′/ε₀ vs Palmer fringing formula: 1.903 → 2.16 (+13.49 %) |
| SL-128 | [Biot–Savart: coils and the Helmholtz pair](projects/signal-lab/G-electromagnetics-and-device-physics/SL128-biot-savart-coil-fields) | M | Single loop: B at centre: 12.57 µT → 12.57 µT (-0.00 %) |
| SL-129 | [Skin effect in a round copper wire](projects/signal-lab/G-electromagnetics-and-device-physics/SL129-skin-effect-visualiser) | M | Skin depth of copper at 1 MHz: 66.1 µm → 66.09 µm (-0.02 %) |
| SL-130 | [Eddy-current loss in solid vs laminated cores](projects/signal-lab/G-electromagnetics-and-device-physics/SL130-eddy-current-simulation) | H | Loss density, 0.10 mm sheet (thin-sheet formula): 82.25 W/m³ → 82.24 W/m³ (-0.00 %) |
| SL-131 | [Transformer coupling: coefficient k and leakage inductance](projects/signal-lab/G-electromagnetics-and-device-physics/SL131-transformer-coupling-model) | M | k = 0.9: recovered from open/short tests: 0.9 → 0.9 (-0.00 %) |
| SL-132 | [Antenna near field vs far field (Hertzian dipole)](projects/signal-lab/G-electromagnetics-and-device-physics/SL132-antenna-near-far-field) | H | Wave impedance at kr = 60 (far field): 376.7 Ω → 376.6 Ω (-0.03 %) |
| SL-133 | [PCB crosstalk vs trace spacing](projects/signal-lab/G-electromagnetics-and-device-physics/SL133-emi-coupling-demo) | M | s = 0.15 mm: near-end crosstalk (¼(Cm/C + Lm/L)): 0.08116 → 0.07947 (-2.08 %) |
| SL-134 | [RF shielding effectiveness: Schelkunoff vs exact](projects/signal-lab/G-electromagnetics-and-device-physics/SL134-rf-shielding-calculator) | M | Copper 35 µm at 1e+05 Hz: Schelkunoff A+R+B vs exact: 111.7 dB → 111.7 dB (-6.7500e-06 dB) |
| SL-135 | [PN junction from device physics (Poisson + drift-diffusion)](projects/signal-lab/G-electromagnetics-and-device-physics/SL135-pn-junction-simulator) | H | Built-in potential: 776 mV → 776 mV (-0.00 %) |
| SL-136 | [MOSFET I–V families and threshold-voltage extraction](projects/signal-lab/G-electromagnetics-and-device-physics/SL136-mosfet-characteristics) | H | Threshold by linear extrapolation (ELR): 700 mV → 715.6 mV (+15.57 mV) |

### H. Embedded systems (simulated)

| # | Project | Lvl | Headline result |
|---|---|---|---|
| SL-137 | [PWM LED 'breathing' fade with gamma correction](projects/signal-lab/H-embedded-systems/SL137-pwm-led-fade) | E | PWM frequency: 976.6 Hz → 976.6 Hz (+0.00 %) |
| SL-138 | [I²C temperature-sensor driver with bus capture](projects/signal-lab/H-embedded-systems/SL138-i2c-sensor-reader) | E | Max conversion error (12-bit, 0.0625 °C LSB → ≤ 0.03125): 0.03125 °C → 0.0288 °C (-0.00245 °C) |
| SL-139 | [SSD1306 OLED driver: framebuffer, font and refresh rate](projects/signal-lab/H-embedded-systems/SL139-oled-display-driver) | E | Bytes per frame on the bus (1,024 data + 32 prefixes + 7 cmd): 1063 → 1063 (+0) |
| SL-140 | [Hobby-servo controller: angle from pulse width](projects/signal-lab/H-embedded-systems/SL140-servo-controller) | E | Servo frame period: 20 ms → 20 ms (+0.00 %) |
| SL-141 | [Stepper-motor driver with trapezoidal acceleration](projects/signal-lab/H-embedded-systems/SL141-stepper-motor-driver) | M | Move time (S/v_max + v_max/α): 1.1 s → 1.055 s (-4.05 %) |
| SL-142 | [Quadrature rotary-encoder decoder](projects/signal-lab/H-embedded-systems/SL142-rotary-encoder-decoder) | M | Poll 1 kHz: limit 1/(96·(T_poll + t_bounce)) lies between last pass and first fail: 1 → 1 (+0) |
| SL-143 | [4×4 matrix keypad scanner with debouncing (and ghosting)](projects/signal-lab/H-embedded-systems/SL143-matrix-keypad-scanner) | E | Keys detected (16 pressed one at a time): 16 → 16 (+0) |
| SL-144 | [Timestamped data logger with flash wear levelling](projects/signal-lab/H-embedded-systems/SL144-data-logger) | M | Erases per sector after 30 days (N / 400 / 16): 405 → 405 (+0.00 %) |
| SL-145 | [Polling vs interrupts: response latency and jitter](projects/signal-lab/H-embedded-systems/SL145-interrupt-driven-timing) | M | Polling: mean latency (≈ T/2 = 250 µs): 250 µs → 256.1 µs (+2.43 %) |
| SL-146 | [Bit-banged SPI and its maximum clock rate](projects/signal-lab/H-embedded-systems/SL146-bit-banged-spi) | M | Mode 0: bytes decoded incorrectly (of 64): 0 → 0 (+0) |
| SL-147 | [MCU ADC sampling with a fixed-point digital filter](projects/signal-lab/H-embedded-systems/SL147-mcu-adc-digital-filter) | M | Moving average (M = 16): SNR gain: 12.04 dB → 11.91 dB (-0.1329 dB) |
| SL-148 | [DDS waveform generator (phase accumulator + DAC)](projects/signal-lab/H-embedded-systems/SL148-dac-waveform-generator) | M | Actual output frequency (Δφ/2³²·f_clk) vs target: 1.235 kHz → 1.235 kHz (+0.00 %) |
| SL-149 | [Rate-monotonic RTOS scheduling: response times vs analysis](projects/signal-lab/H-embedded-systems/SL149-rtos-task-scheduling) | H | Task 1 (C=1 ms, T=5 ms): worst response time (RTA): 1000 µs → 1000 µs (+0 µs) |
| SL-150 | [MQTT publisher: packet encoding and a round-trip test](projects/signal-lab/H-embedded-systems/SL150-mqtt-publisher) | M | CONNACK return code (0 = accepted): 0 → 0 (+0) |
| SL-151 | [Embedded web server: control page and REST endpoint](projects/signal-lab/H-embedded-systems/SL151-esp32-web-server) | M | Correct status codes (150 × 200, 50 × 404): 200 → 200 (+0) |
| SL-152 | [IMU sensor fusion with a complementary filter](projects/signal-lab/H-embedded-systems/SL152-sensor-fusion) | H | Optimal time constant τ* = (σ_a²·dt/(2b²))^(1/3): 698 ms → 501.2 ms (-28.19 %) |
| SL-153 | [CAN bus: bit-wise arbitration, stuffing and worst-case latency](projects/signal-lab/H-embedded-systems/SL153-can-bus-simulation) | H | Lowest ID wins every contested arbitration: 33 → 33 (+0) |
| SL-154 | [Low-power firmware state machine and battery-life estimate](projects/signal-lab/H-embedded-systems/SL154-low-power-state-machine) | M | Average current (duty-cycle formula): 2.542 µA → 2.541 µA (-0.04 %) |
| SL-155 | [A custom Wokwi chip: I²C 12-bit DAC written with the Chips API](projects/signal-lab/H-embedded-systems/SL155-custom-wokwi-chip) | H | Addresses other than 0x60 that ACK (of 127): 0 → 0 (+0) |
| SL-156 | [Firmware unit tests on the host (with mutation testing)](projects/signal-lab/H-embedded-systems/SL156-firmware-unit-tests) | M | Tests failing on the correct code: 0 → 0 (+0) |

### I. Control systems

| # | Project | Lvl | Headline result |
|---|---|---|---|
| SL-157 | [PID control of a second-order plant](projects/signal-lab/I-control-systems/SL157-pid-controller-sim) | M | P: overshoot from dominant poles: 24.92 % → 25.09 % (+0.173 pp) |
| SL-158 | [PID auto-tuning: relay feedback + Ziegler–Nichols](projects/signal-lab/I-control-systems/SL158-pid-auto-tuning) | H | Ultimate period T_u (relay vs exact 2π/√3): 3.628 s → 3.86 s (+6.41 %) |
| SL-159 | [Inverted pendulum on a cart: LQR stabilisation](projects/signal-lab/I-control-systems/SL159-inverted-pendulum) | H | Unstable open-loop pole √(g(M+m)/(Mℓ)): 4.852 1/s → 4.852 1/s (+0.00 %) |
| SL-160 | [Cruise control: rejecting a hill with PI feedback](projects/signal-lab/I-control-systems/SL160-cruise-control-model) | M | Cruise force on the flat (½ρC_dAv² + C_r mg): 360.6 N → 360.6 N (+0.00 %) |
| SL-161 | [DC motor speed control (with current limiting)](projects/signal-lab/I-control-systems/SL161-dc-motor-speed-control) | M | No-load speed K·V/(K² + bR): 239 rad/s → 239 rad/s (+0.00 %) |
| SL-162 | [Temperature control with dead time: why lag causes oscillation](projects/signal-lab/I-control-systems/SL162-temperature-control-loop) | M | Ultimate gain K_u (phase-crossover prediction): 8.175 %/°C → 8.156 %/°C (-0.24 %) |
| SL-163 | [Bode/Nyquist margin analyser](projects/signal-lab/I-control-systems/SL163-bode-nyquist-analysis-tool) | M | K = 1: gain margin 20·log₁₀(11/K): 20.83 dB → 20.83 dB (-7.0000e-04 dB) |
| SL-164 | [Root locus: asymptotes, breakaway and the stability limit](projects/signal-lab/I-control-systems/SL164-root-locus-explorer) | M | Breakaway point (dK/ds = 0): -0.8804 → -0.8801 (+2.4540e-04) |
| SL-165 | [State-feedback pole placement for a two-mass system](projects/signal-lab/I-control-systems/SL165-state-space-controller) | H | Controllability matrix rank: 4 → 4 (+0) |
| SL-166 | [LQR optimal control vs a tuned PID](projects/signal-lab/I-control-systems/SL166-lqr-optimal-control) | H | LQR position gain vs closed form 1/√ρ: 3.162 → 3.162 (+0.00 %) |
| SL-167 | [Luenberger observer: estimating hidden states](projects/signal-lab/I-control-systems/SL167-state-observer) | H | Observability rank from x₂ alone: 4 → 4 (+0) |
| SL-168 | [Ball and beam: a nonlinear, open-loop-unstable plant](projects/signal-lab/I-control-systems/SL168-ball-and-beam) | H | Small step (0.1 m), no limits: overshoot (ζ = 0.8): 1.516 % → 1.17 % (-0.346 pp) |
| SL-169 | [Quadcopter attitude: cascaded rate and angle loops](projects/signal-lab/I-control-systems/SL169-quadcopter-attitude-control) | H | roll: angle-loop rise time ≈ 2.2/k_a (k_a = 6 rad/s): 366.7 ms → 280 ms (-23.64 %) |
| SL-170 | [Discrete-time control: how sampling erodes stability](projects/signal-lab/I-control-systems/SL170-discrete-time-control) | M | T = 50 ms: phase margin ≈ PM₀ − ω_c·T/2: 69.38 ° → 67.36 ° (-2.025 °) |
| SL-171 | [Integrator windup and anti-windup strategies](projects/signal-lab/I-control-systems/SL171-anti-windup-strategies) | M | No anti-windup: overshoot area ≈ error integrated beyond the linear integrator state: 413.2 ms → 441.8 ms (+6.91 %) |

### J. Biosignals & HCI (real patient data)

| # | Project | Lvl | Headline result |
|---|---|---|---|
| SL-172 | [ECG R-peak detection (Pan–Tompkins) on MIT-BIH](projects/signal-lab/J-biosignals-and-hci/SL172-ecg-r-peak-detection) | M | Gross sensitivity (Pan & Tompkins 1985 report 99.3 %): 99.3 % → 98.58 % (-0.716 pp) |
| SL-173 | [Heart-rate variability: time and frequency domain](projects/signal-lab/J-biosignals-and-hci/SL173-heart-rate-variability) | M | SDNN: detected peaks vs annotation reference: 35.95 ms → 35.95 ms (-0.01 %) |
| SL-174 | [Premature ventricular contraction detection (inter-patient)](projects/signal-lab/J-biosignals-and-hci/SL174-arrhythmia-classification) | H | Inter-patient PVC sensitivity (literature ≈ 80–90 %): 85 % → 96.93 % (+11.9 pp) |
| SL-175 | [ECG denoising with real noise from the Noise Stress Test Database](projects/signal-lab/J-biosignals-and-hci/SL175-ecg-denoising) | M | baseline wander: SNR gain vs −10·log₁₀(in-band noise fraction): 17.63 dB → 16.7 dB (-0.9255 dB) |
| SL-176 | [EMG envelope extraction and amplitude estimators](projects/signal-lab/J-biosignals-and-hci/SL176-emg-envelope-extraction) | M | MAV / RMS during contraction (Gaussian: √(2/π)): 0.7979 → 0.5924 (-25.75 %) |
| SL-177 | [Hand-gesture classification from 8-channel forearm EMG](projects/signal-lab/J-biosignals-and-hci/SL177-emg-gesture-classification) | H | Within-subject accuracy (Hudgins features + LDA, literature 90–95 %): 92 % → 94.87 % (+2.87 pp) |
| SL-178 | [EMG-driven cursor control (HCI without hardware)](projects/signal-lab/J-biosignals-and-hci/SL178-simulated-emg-cursor-control) | H | Progress toward target per decision = P(correct) − P(opposite): 0.9271 steps → 0.928 steps (+0.09 %) |
| SL-179 | [Detecting the eyes-closed alpha rhythm in real EEG](projects/signal-lab/J-biosignals-and-hci/SL179-eeg-alpha-wave-detection) | M | Median eyes-closed / eyes-open alpha increase (3–10 dB typical): 6 dB → 4.02 dB (-1.98 dB) |
| SL-180 | [Removing eye-blink artefacts from EEG with ICA](projects/signal-lab/J-biosignals-and-hci/SL180-eeg-artifact-removal) | H | Blink variance removed at Fp1/Fpz/Fp2 (inside blink windows): 80 % → 86.12 % (+6.12 pp) |
| SL-181 | [Motor-imagery brain–computer interface (CSP + LDA)](projects/signal-lab/J-biosignals-and-hci/SL181-motor-imagery-bci) | H | Mean CV accuracy over 10 subjects (published CSP+LDA ≈ 60–80 %): 70 % → 64 % (-6 pp) |
| SL-182 | [Heart rate from PPG, validated against ECG (BIDMC)](projects/signal-lab/J-biosignals-and-hci/SL182-ppg-heart-rate-extraction) | M | Median per-patient HR error, PPG vs ECG (8-s windows) — expected < 1 bpm on clean PPG: 0 bpm → 0.5847 bpm (+0.5847 bpm) |
| SL-183 | [Respiration rate derived from the ECG (EDR)](projects/signal-lab/J-biosignals-and-hci/SL183-respiration-from-ecg) | H | EDR (R-amplitude) respiration-rate MAE: 0 breaths/min → 2.146 breaths/min (+2.146 breaths/min) |
| SL-184 | [Sleep-stage scoring from EEG (Sleep-EDF)](projects/signal-lab/J-biosignals-and-hci/SL184-sleep-stage-classification) | H | Accuracy on an unseen subject's night (simple classifiers: 70–80 %): 75 % → 70.15 % (-4.85 pp) |
| SL-185 | [Epileptic seizure detection in scalp EEG (CHB-MIT)](projects/signal-lab/J-biosignals-and-hci/SL185-seizure-detection) | H | Line-length increase during the seizure (several-fold expected): 3 × → 1.844 × (-1.156 ×) |
| SL-186 | [Eye-movement analysis from the EOG: finding REM sleep](projects/signal-lab/J-biosignals-and-hci/SL186-eog-eye-movement-analysis) | M | REM / N2 mean saccade-rate ratio (≫ 1 expected): 5 × → 5.258 × (+0.2584 ×) |
| SL-187 | [Muscle fatigue: the EMG median-frequency shift](projects/signal-lab/J-biosignals-and-hci/SL187-muscle-fatigue-analysis) | M | Relative median-frequency decline over 60 s (= relative velocity decline 20 %): -20 % → -18.23 % (+1.77 pp) |
| SL-188 | [Webcam gesture control in the browser](projects/signal-lab/J-biosignals-and-hci/SL188-webcam-gesture-recognition) | M | Noise-free accuracy over pose variation (all poses): 100 % → 99.62 % (-0.383 pp) |
| SL-189 | [Spoken-command recognition with MFCCs and DTW](projects/signal-lab/J-biosignals-and-hci/SL189-voice-controlled-interface) | M | Speaker-dependent accuracy (5 templates/word, same speaker): 95 % → 87.25 % (-7.75 pp) |
| SL-190 | [Your phone as a free sensor: IMU capture page + cadence analysis](projects/signal-lab/J-biosignals-and-hci/SL190-phone-imu-gesture-capture) | M | Median walking cadence (adult norm ≈ 100–120 steps/min): 110 steps/min → 105.5 steps/min (-4.531 steps/min) |
| SL-191 | [Human-activity recognition from smartphone IMU data](projects/signal-lab/J-biosignals-and-hci/SL191-human-activity-recognition) | M | Test accuracy on 9 unseen subjects (published SVM: 96 %): 96 % → 94.5 % (-1.5 pp) |
| SL-192 | [Automatic ECG signal-quality checker](projects/signal-lab/J-biosignals-and-hci/SL192-biosignal-quality-checker) | M | Specificity on clean segments: 95 % → 80.63 % (-14.4 pp) |

### K. Interactive tools & web apps

| # | Project | Lvl | Headline result |
|---|---|---|---|
| SL-193 | [Voltage divider calculator with live schematic](projects/signal-lab/K-interactive-tools-and-web-apps/SL193-voltage-divider-calculator) | E | Max \|Vout(JS) − Vout(MNA simulator)\| over 500 random loaded dividers: 0 V → 7.105 fV (+7.105 fV) |
| SL-194 | [Resistor colour-code decoder and encoder](projects/signal-lab/K-interactive-tools-and-web-apps/SL194-resistor-colour-code-decoder) | E | Round-trip failures over 240 E24 + 864 E96 values (E24 0.1 Ω–910 MΩ, E96 1 Ω–976 MΩ): 0 → 0 (+0) |
| SL-195 | [Active filter design calculator (Sallen-Key)](projects/signal-lab/K-interactive-tools-and-web-apps/SL195-filter-design-calculator) | M | Prototype table in calc.js vs SciPy poles (worst relative error in f0 or Q): 0 % → 0.008614 % (+0.00861 pp) |
| SL-196 | [Fourier-series drawing tool (epicycles)](projects/signal-lab/K-interactive-tools-and-web-apps/SL196-fourier-series-drawing-tool) | M | square (corners): RMS error ∝ N^slope — slope: -1.5 → -1.44 (+0.05985) |
| SL-197 | [Logic gate playground with live truth tables](projects/signal-lab/K-interactive-tools-and-web-apps/SL197-logic-gate-playground) | M | Truth-table rows where JS ≠ Python (304 circuits, 6888 rows): 0 → 0 (+0) |
| SL-198 | [Op-amp configuration explorer](projects/signal-lab/K-interactive-tools-and-web-apps/SL198-op-amp-configuration-explorer) | M | Worst \|DC gain(JS, finite A0) − simulated\| over all configurations: 0 % → 5.4078e-05 % (+5.41e-05 pp) |
| SL-199 | [Antenna length calculator — and when the 0.95 rule is right](projects/signal-lab/K-interactive-tools-and-web-apps/SL199-antenna-length-calculator) | E | 146 MHz dipole total length (0.95·λ/2): 975.4 mm → 975.4 mm (+0.00 %) |
| SL-200 | [dB / dBm / watts / volts converter](projects/signal-lab/K-interactive-tools-and-web-apps/SL200-db-dbm-watts-converter) | E | Worst relative round-trip error over 1800 conversions (90 unit pairs): 0 → 4.1045e-14 (+4.1045e-14) |
| SL-201 | [Battery life estimator with sleep-mode modelling](projects/signal-lab/K-interactive-tools-and-web-apps/SL201-battery-life-estimator) | E | Worst \|average-current model − coulomb-counting simulation\| (300 profiles): 0 % → 9.7503e-04 % (+0.000975 pp) |
| SL-202 | [PCB trace width calculator (IPC-2221) vs a thermal model](projects/signal-lab/K-interactive-tools-and-web-apps/SL202-pcb-trace-width-calculator) | E | 3 A, ΔT 10 °C, 1 oz outer: width = A/1.378 mil: 53.82 mil → 53.82 mil (+0.00 %) |
| SL-203 | [Unit converter for EE (prefixes, value codes, AWG, PCB units)](projects/signal-lab/K-interactive-tools-and-web-apps/SL203-unit-converter-for-ee) | E | Worst AWG diameter deviation from the published table (values given to 0.001 mm): 0 mm → 4.7461e-04 mm (+4.7461e-04 mm) |
| SL-204 | [Bit manipulation visualiser (shifts, masks, two's complement)](projects/signal-lab/K-interactive-tools-and-web-apps/SL204-bit-manipulation-visualiser) | E | BigInt library vs Python integers (24000 random ops, widths 8–64): 0 → 0 (+0) |

### L. PCB design

| # | Project | Lvl | Headline result |
|---|---|---|---|
| SL-205 | [Stereo op-amp preamplifier board](projects/signal-lab/L-pcb-design/SL205-amplifier-board) | M | Mid-band gain into 10 kΩ: 20.74 dB → 20.74 dB (-9.7694e-04 dB) |
| SL-206 | [I²C temperature-sensor breakout board](projects/signal-lab/L-pcb-design/SL206-sensor-breakout-board) | M | DRC violations (clearance, widths, drills, annular rings, edge, courtyards, connectivity): 0 → 0 (+0) |
| SL-207 | [Linear power-supply board (LM317, 12 V → 5 V, 1 A)](projects/signal-lab/L-pcb-design/SL207-power-supply-board) | M | Nominal output with E96 parts: 5.01 V → 5.01 V (-0.00 %) |
| SL-208 | [Arduino Uno R3 shield (LEDs, button, potentiometer, I²C port)](projects/signal-lab/L-pcb-design/SL208-arduino-shield) | M | D7 → D8 pin spacing from the KiCad library (the 160-mil quirk): 4.064 mm → 4.06 mm (-0.10 %) |
| SL-209 | [Controlled-impedance RF board: 50 Ω microstrip vs grounded CPW](projects/signal-lab/L-pcb-design/SL209-controlled-impedance-rf-board) | H | Microstrip w = 3.2 mm: Hammerstad–Jensen vs field solver: 48.89 Ω → 48.53 Ω (-0.72 %) |
| SL-210 | [2-layer vs 4-layer stack-up: impedance, inductance and crosstalk](projects/signal-lab/L-pcb-design/SL210-4-layer-stackup-study) | H | 2-layer (h = 1.6 mm): inductance of a 0.2 mm trace, formula (Z0·√εeff/c) vs field solver: 832.5 nH/m → 796.5 nH/m (-4.31 %) |
| SL-211 | [DRC and manufacturability report (with seeded defects)](projects/signal-lab/L-pcb-design/SL211-drc-manufacturability-report) | M | Violations on the clean board: 0 → 0 (+0) |
| SL-212 | [BOM, pick-and-place and assembly documentation package](projects/signal-lab/L-pcb-design/SL212-bom-and-assembly-docs) | M | BOM quantities sum to the number of placed parts: 18 → 18 (+0) |
| SL-213 | [Footprint library from IPC-7351 equations, checked against KiCad's](projects/signal-lab/L-pcb-design/SL213-component-footprint-library) | M | Generated .kicad_mod files that kiutils parses with the right pad count: 6 → 6 (+0) |
| SL-214 | [Design review: critiquing and re-laying-out the preamp board](projects/signal-lab/L-pcb-design/SL214-design-review-write-up) | M | DRC violations (clearance, widths, drills, annular rings, edge, courtyards, connectivity): 0 → 0 (+0) |
