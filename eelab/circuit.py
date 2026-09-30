"""eelab.circuit — a compact SPICE-like circuit simulator (Modified Nodal Analysis).

Supports R, C, L (+ mutual coupling K), independent V/I sources (DC, AC, arbitrary
waveform), VCVS/VCCS, diode, BJT (Ebers-Moll transport + Early), MOSFET (square law
with smooth EKV-style subthreshold), a single-pole op-amp macromodel with slew-rate
and rail limits, and time-controlled switches.

Analyses: .op (Newton-Raphson), .ac (small-signal about the operating point) and
.tran (backward-Euler or trapezoidal companion models with Newton at every step).

System form:   G x + C dx/dt + f(x) = b(t)
x = [node voltages (ground excluded), branch currents]
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import lu_factor, lu_solve

VT = 0.025852  # thermal voltage at 300 K


def _limexp(u, umax=40.0):
    """exp with linear continuation above umax (keeps Newton finite)."""
    u = np.asarray(u, float)
    e = np.exp(np.minimum(u, umax))
    val = np.where(u > umax, e * (1 + u - umax), e)
    der = e
    return val, der


class Circuit:
    def __init__(self, title="circuit"):
        self.title = title
        self.nodes = {"0": -1, "gnd": -1}
        self.node_names = []
        self.elems = []
        self.branches = []           # names of branch-current unknowns
        self.nl = []                 # nonlinear devices
        self.couplings = []
        self.x0 = None

    # ------------------------------------------------------------ topology
    def n(self, name):
        name = str(name)
        if name not in self.nodes:
            self.nodes[name] = len(self.node_names)
            self.node_names.append(name)
        return self.nodes[name]

    def _br(self, name):
        self.branches.append(name)
        return len(self.branches) - 1

    def R(self, name, a, b, r):
        self.elems.append(("R", name, self.n(a), self.n(b), float(r)))

    def C(self, name, a, b, c):
        self.elems.append(("C", name, self.n(a), self.n(b), float(c)))

    def L(self, name, a, b, l):
        self.elems.append(("L", name, self.n(a), self.n(b), float(l), self._br(name)))

    def K(self, l1, l2, k):
        self.couplings.append((l1, l2, float(k)))

    def V(self, name, a, b, dc=0.0, ac=0.0, wave=None):
        """wave: callable t -> volts (overrides dc in transient)."""
        self.elems.append(("V", name, self.n(a), self.n(b), dc, ac, wave, self._br(name)))

    def I(self, name, a, b, dc=0.0, ac=0.0, wave=None):
        """Current dc flows from node a, through the source, into node b."""
        self.elems.append(("I", name, self.n(a), self.n(b), dc, ac, wave))

    def E(self, name, a, b, ca, cb, gain):
        self.elems.append(("E", name, self.n(a), self.n(b), self.n(ca), self.n(cb), float(gain),
                           self._br(name)))

    def G(self, name, a, b, ca, cb, gm):
        self.elems.append(("G", name, self.n(a), self.n(b), self.n(ca), self.n(cb), float(gm)))

    def SW(self, name, a, b, ctrl, ron=0.01, roff=1e7):
        """Switch: ctrl(t) -> bool. For .op/.ac ctrl(0) is used."""
        self.elems.append(("SW", name, self.n(a), self.n(b), ctrl, ron, roff))

    def D(self, name, a, k, Is=1e-14, N=1.0, Rs=0.0, BV=None, Cj=0.0, IBV=1e-3):
        if Rs > 0:
            mid = f"{name}_int"
            self.R(f"{name}_rs", a, mid, Rs)
            a = mid
        if Cj > 0:
            self.C(f"{name}_cj", a, k, Cj)
        self.nl.append(("D", name, self.n(a), self.n(k), Is, N, BV, IBV))

    def Q(self, name, c, b, e, pol="npn", Is=1e-15, BF=100, BR=1, VAF=np.inf, Cbe=0.0, Cbc=0.0):
        if Cbe:
            self.C(f"{name}_cbe", b, e, Cbe)
        if Cbc:
            self.C(f"{name}_cbc", b, c, Cbc)
        self.nl.append(("Q", name, self.n(c), self.n(b), self.n(e), 1 if pol == "npn" else -1,
                        Is, BF, BR, VAF))

    def M(self, name, d, g, s, pol="n", K=2e-3, VT0=1.0, LAMBDA=0.01, NSUB=1.5, Cgs=0.0, Cgd=0.0):
        """Square-law MOSFET, K = mu*Cox*W/L [A/V^2]. Smooth subthreshold via softplus."""
        if Cgs:
            self.C(f"{name}_cgs", g, s, Cgs)
        if Cgd:
            self.C(f"{name}_cgd", g, d, Cgd)
        self.nl.append(("M", name, self.n(d), self.n(g), self.n(s), 1 if pol == "n" else -1,
                        K, VT0, LAMBDA, NSUB))

    def OPAMP(self, name, inp, inn, out, A0=2e5, GBW=1e6, SR=0.5e6, VSAT=13.0, ROUT=50.0,
              VOS=0.0):
        """Single-pole op-amp: gm stage (slew limited) -> R||C pole -> rail-limited buffer."""
        x = f"{name}_x"
        fp = GBW / A0
        R1 = 1e6
        C1 = 1 / (2 * np.pi * fp * R1)
        gm = A0 / R1
        imax = SR * C1
        self.R(f"{name}_r1", x, "0", R1)
        self.C(f"{name}_c1", x, "0", C1)
        self.R(f"{name}_rin", inp, inn, 1e12)
        self.nl.append(("GTANH", name, self.n(x), self.n(inp), self.n(inn), gm, imax, VOS))
        o = f"{name}_o"
        # internal node clamp (prevents unrealistic integrator wind-up in saturation)
        self.nl.append(("CLAMP", name, self.n(x), 1.5 * VSAT, 1.0, 0.02))
        self.nl.append(("ETANH", name, self.n(o), self.n(x), VSAT, self._br(f"{name}_out")))
        self.R(f"{name}_ro", o, out, ROUT)
        self.opamp_meta = getattr(self, "opamp_meta", {})
        self.opamp_meta[name] = dict(inp=inp, inn=inn, out=out, A0=A0, GBW=GBW, SR=SR, VSAT=VSAT)

    # ------------------------------------------------------------ assembly
    def _size(self):
        return len(self.node_names) + len(self.branches)

    def _build_linear(self, t=None, sw_state=None):
        N = len(self.node_names)
        S = self._size()
        G = np.zeros((S, S))
        Cm = np.zeros((S, S))
        Ls = {}

        def st(M, i, j, v):
            if i >= 0 and j >= 0:
                M[i, j] += v

        for e in self.elems:
            k = e[0]
            if k in ("R", "SW"):
                a, b = e[2], e[3]
                if k == "R":
                    g = 1 / e[4]
                else:
                    on = e[4](0.0 if t is None else t) if sw_state is None else sw_state[e[1]]
                    g = 1 / (e[5] if on else e[6])
                st(G, a, a, g); st(G, b, b, g); st(G, a, b, -g); st(G, b, a, -g)
            elif k == "C":
                a, b, c = e[2], e[3], e[4]
                st(Cm, a, a, c); st(Cm, b, b, c); st(Cm, a, b, -c); st(Cm, b, a, -c)
            elif k == "L":
                a, b, l, br = e[2], e[3], e[4], N + e[5]
                st(G, a, br, 1); st(G, b, br, -1); st(G, br, a, 1); st(G, br, b, -1)
                Cm[br, br] -= l
                Ls[e[1]] = (br, l)
            elif k == "V":
                a, b, br = e[2], e[3], N + e[7]
                st(G, a, br, 1); st(G, b, br, -1); st(G, br, a, 1); st(G, br, b, -1)
            elif k == "E":
                a, b, ca, cb, gain, br = e[2], e[3], e[4], e[5], e[6], N + e[7]
                st(G, a, br, 1); st(G, b, br, -1); st(G, br, a, 1); st(G, br, b, -1)
                st(G, br, ca, -gain); st(G, br, cb, gain)
            elif k == "G":
                a, b, ca, cb, gm = e[2], e[3], e[4], e[5], e[6]
                st(G, a, ca, gm); st(G, a, cb, -gm); st(G, b, ca, -gm); st(G, b, cb, gm)
        for l1, l2, kk in self.couplings:
            (b1, L1), (b2, L2) = Ls[l1], Ls[l2]
            m = kk * np.sqrt(L1 * L2)
            Cm[b1, b2] -= m
            Cm[b2, b1] -= m
        return G, Cm

    def _rhs(self, t, ac=False):
        N = len(self.node_names)
        b = np.zeros(self._size(), complex if ac else float)
        for e in self.elems:
            if e[0] == "V":
                v = e[5] if ac else (e[6](t) if (e[6] is not None and t is not None) else e[4])
                b[N + e[7]] += v
            elif e[0] == "I":
                i = e[4 + 0] if not ac else e[5]
                if not ac and e[6] is not None and t is not None:
                    i = e[6](t)
                if e[2] >= 0:
                    b[e[2]] -= i
                if e[3] >= 0:
                    b[e[3]] += i
        return b

    def _nonlinear(self, x, gmin=1e-12):
        """Return f(x) (currents leaving nodes / branch residuals) and Jacobian df/dx."""
        S = self._size()
        N = len(self.node_names)
        f = np.zeros(S)
        J = np.zeros((S, S))
        v = lambda i: x[i] if i >= 0 else 0.0

        def addf(i, val):
            if i >= 0:
                f[i] += val

        def addJ(i, j, val):
            if i >= 0 and j >= 0:
                J[i, j] += val

        for d in self.nl:
            k = d[0]
            if k == "D":
                _, _, a, c, Is, Nn, BV, IBV = d
                vd = v(a) - v(c)
                ex, dex = _limexp(vd / (Nn * VT))
                i = Is * (ex - 1) + gmin * vd
                g = Is * dex / (Nn * VT) + gmin
                if BV is not None:  # reverse breakdown (zener)
                    exb, dexb = _limexp((-vd - BV) / (Nn * VT))
                    i -= IBV * exb
                    g += IBV * dexb / (Nn * VT)
                addf(a, i); addf(c, -i)
                addJ(a, a, g); addJ(a, c, -g); addJ(c, a, -g); addJ(c, c, g)
            elif k == "Q":
                _, _, c, b, e, p, Is, BF, BR, VAF = d
                vbe = p * (v(b) - v(e))
                vbc = p * (v(b) - v(c))
                ef, def_ = _limexp(vbe / VT)
                er, der = _limexp(vbc / VT)
                If, gf = Is * (ef - 1), Is * def_ / VT
                Ir, gr = Is * (er - 1), Is * der / VT
                vce = vbe - vbc
                early = 1 + vce / VAF if np.isfinite(VAF) else 1.0
                dearly = 1 / VAF if np.isfinite(VAF) else 0.0
                ict = (If - Ir) * early
                ic = ict - Ir / BR
                ib = If / BF + Ir / BR
                # partial derivatives wrt vbe, vbc (in polarity-normalised frame)
                dic_dvbe = gf * early + (If - Ir) * dearly
                dic_dvbc = -gr * early - (If - Ir) * dearly - gr / BR
                dib_dvbe = gf / BF
                dib_dvbc = gr / BR
                ic += gmin * vce
                dic_dvbe += gmin
                dic_dvbc -= gmin
                # currents into device terminals c,b ; emitter = -(ic+ib)
                # In node frame: current leaving node c into device = p*ic
                for node, cur, dvbe, dvbc in ((c, ic, dic_dvbe, dic_dvbc),
                                              (b, ib, dib_dvbe, dib_dvbc),
                                              (e, -(ic + ib), -(dic_dvbe + dib_dvbe),
                                               -(dic_dvbc + dib_dvbc))):
                    addf(node, p * cur)
                    # vbe = p(vb - ve), vbc = p(vb - vc)
                    addJ(node, b, p * p * (dvbe + dvbc))
                    addJ(node, e, -p * p * dvbe)
                    addJ(node, c, -p * p * dvbc)
            elif k == "M":
                _, _, dn, g, s, p, K, VT0, LAM, NS = d
                vd_, vg_, vs_ = p * v(dn), p * v(g), p * v(s)
                swap = vd_ < vs_
                if swap:
                    vd_, vs_ = vs_, vd_
                vgs, vds = vg_ - vs_, vd_ - vs_
                u = (vgs - VT0) / (NS * VT)
                vov = NS * VT * (np.logaddexp(0, u))
                dvov = 1 / (1 + np.exp(-np.clip(u, -60, 60)))
                if vds < vov:
                    ids0 = K * (vov * vds - 0.5 * vds * vds)
                    dI_dvov = K * vds
                    dI_dvds = K * (vov - vds)
                else:
                    ids0 = 0.5 * K * vov * vov
                    dI_dvov = K * vov
                    dI_dvds = 0.0
                cl = 1 + LAM * vds
                ids = ids0 * cl + gmin * vds
                gm = dI_dvov * dvov * cl
                gds = dI_dvds * cl + ids0 * LAM + gmin
                # current flows drain->source (in normalised frame), dependence on vg, vd, vs
                dD, dS = (s, dn) if swap else (dn, s)
                # ids depends on vgs = vg - vS, vds = vD - vS (S=dS, D=dD)
                sgn = p
                addf(dD, sgn * ids); addf(dS, -sgn * ids)
                for node, sg in ((dD, 1), (dS, -1)):
                    addJ(node, g, sg * gm)
                    addJ(node, dD, sg * gds)
                    addJ(node, dS, sg * (-gm - gds))
            elif k == "GTANH":
                _, _, xo, ip, inn, gm, imax, vos = d
                vdiff = v(ip) - v(inn) + vos
                if getattr(self, "_dcmode", False):   # slew limiting is a dynamic effect only
                    i, gd = gm * vdiff, gm
                else:
                    u = gm * vdiff / imax
                    th = np.tanh(u)
                    i = imax * th                     # current INTO node x
                    gd = gm * (1 - th * th)
                addf(xo, -i)
                addJ(xo, ip, -gd); addJ(xo, inn, gd)
            elif k == "ETANH":
                # soft output limit: vo = vx / (1 + |vx/vsat|^8)^(1/8)  (linear until near the rail)
                _, _, o, xi, vsat, br = d
                row = N + br
                u = v(xi) / vsat
                base = 1 + abs(u) ** 8
                vo = v(xi) * base ** (-1 / 8)
                dvo = base ** (-1 / 8 - 1)
                f[row] += v(o) - vo
                addJ(row, o, 1.0)
                addJ(row, xi, -dvo)
                addf(o, x[row])
                addJ(o, row, 1.0)
            elif k == "CLAMP":
                _, _, xi, vc, gc, w = d
                vx = v(xi)
                a1, a2 = (vx - vc) / w, (-vx - vc) / w
                sp = lambda z: np.logaddexp(0, z)
                sg = lambda z: 1 / (1 + np.exp(-np.clip(z, -60, 60)))
                i = gc * w * (sp(a1) - sp(a2))
                g = gc * (sg(a1) + sg(a2))
                addf(xi, i)
                addJ(xi, xi, g)
        return f, J

    # ------------------------------------------------------------ solvers
    def _newton(self, A, rhs, x, extra=None, maxit=150, tol=1e-9):
        """Solve A x + f(x) = rhs by damped Newton-Raphson with a backtracking line search."""
        if not self.nl:
            return np.linalg.solve(A, rhs), 1
        f, J = self._nonlinear(x)
        F = A @ x + f - rhs
        nF = np.linalg.norm(F)
        for it in range(maxit):
            try:
                dx = np.linalg.solve(A + J, -F)
            except np.linalg.LinAlgError:
                dx = np.linalg.lstsq(A + J, -F, rcond=None)[0]
            N = len(self.node_names)
            mx = np.max(np.abs(dx[:N])) if N else 0
            if mx > 20.0:
                dx *= 20.0 / mx
            lam = min(1.0, self._junction_limit(x, dx))
            while True:
                xn = x + lam * dx
                fn, Jn = self._nonlinear(xn)
                Fn = A @ xn + fn - rhs
                nFn = np.linalg.norm(Fn)
                if nFn <= (1 - 1e-4 * lam) * nF or lam < 1.0 / 1024:
                    break
                lam *= 0.5
            step = lam * dx
            x, f, J, F, nF = xn, fn, Jn, Fn, nFn
            if np.max(np.abs(step)) < tol * (1 + np.max(np.abs(x))) and nF < 1e-6 * (1 + np.max(np.abs(rhs))):
                return x, it + 1
            if nF < 1e-12 * (1 + np.max(np.abs(rhs))):
                return x, it + 1
        raise RuntimeError(f"Newton did not converge ({self.title})")

    def _junction_limit(self, x, dx, vcrit=0.55, dmax=0.08):
        """SPICE-style junction limiting: never let a forward-biased junction jump by more
        than ~3 V_T per iteration (returns a step scale in (0, 1])."""
        v = lambda i, vec: vec[i] if i >= 0 else 0.0
        scale = 1.0
        for d in self.nl:
            if d[0] == "D":
                pairs = [(d[2], d[3], 1)]
            elif d[0] == "Q":
                pairs = [(d[3], d[4], d[5]), (d[3], d[2], d[5])]
            else:
                continue
            for a, c, pol in pairs:
                vo = pol * (v(a, x) - v(c, x))
                dv = pol * (v(a, dx) - v(c, dx))
                if vo + dv > vcrit and dv > dmax:
                    scale = min(scale, max(dmax, vcrit - vo) / dv)
        return max(scale, 1e-3)

    def op(self, x0=None, t=0.0, guess=None):
        """DC operating point. Fallbacks: gmin stepping, then source stepping."""
        self._dcmode = True
        try:
            return self._op(x0, t, guess)
        finally:
            self._dcmode = False

    def _op(self, x0, t, guess):
        G, _ = self._build_linear(t)
        rhs = self._rhs(t)
        x = np.zeros(self._size()) if x0 is None else x0.copy()
        for nm, val in (guess or {}).items():
            x[self.nodes[str(nm)]] = val
        start = x.copy()
        try:
            x, _ = self._newton(G, rhs, x)
        except RuntimeError:
            N = len(self.node_names)
            try:
                x = start.copy()
                for gs in [1e-1, 1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9, 1e-10, 1e-12, 0.0]:
                    Gg = G.copy()
                    Gg[np.arange(N), np.arange(N)] += gs
                    x, _ = self._newton(Gg, rhs, x)
            except RuntimeError:
                x = start.copy()
                for sc in np.linspace(0.02, 1, 50):
                    x, _ = self._newton(G, rhs * sc, x)
        self.x0 = x
        return self._pack(x)

    def ac(self, freqs, x_op=None):
        if x_op is None:
            self.op()
            x_op = self.x0
        G, Cm = self._build_linear(0.0)
        Jn = self._nonlinear(x_op)[1] if self.nl else 0
        b = self._rhs(None, ac=True)
        out = np.zeros((len(freqs), self._size()), complex)
        for i, fr in enumerate(freqs):
            A = G + Jn + 1j * 2 * np.pi * fr * Cm
            out[i] = np.linalg.solve(A, b)
        return ACResult(self, np.asarray(freqs), out)

    def tran(self, tstop, dt, method="trap", uic=False, x_init=None, tstart_save=0.0, save_every=1,
             ic=None, controller=None):
        """Transient analysis.
        ic: {node or 'I(branch)': value} initial conditions (implies uic).
        controller: f(t, v, i) -> {switch_name: bool}, called before every step with getters for
        the previous solution — lets switches be driven by feedback (PWM loops, hysteretic control)."""
        G0, Cm = self._build_linear(0.0)
        has_sw = any(e[0] == "SW" for e in self.elems)
        if x_init is not None:
            x = x_init.copy()
        elif uic or ic:
            x = np.zeros(self._size())
            for k_, val in (ic or {}).items():
                if k_.startswith("I("):
                    x[len(self.node_names) + self.branches.index(k_[2:-1])] = val
                else:
                    x[self.nodes[k_]] = val
        else:
            self.op(t=0.0)
            x = self.x0.copy()
        ctrl_state = {}
        lu_lin = {}
        state = None
        nsteps = int(round(tstop / dt))
        ts, xs = [0.0], [x.copy()]
        # derivative term q' = C x' at t=0 (for trapezoidal)
        f0, _ = self._nonlinear(x) if self.nl else (np.zeros_like(x), None)
        qd = self._rhs(0.0) - G0 @ x - f0
        lu_cache = {}
        sw_elems = [e for e in self.elems if e[0] == "SW"]
        for k in range(1, nsteps + 1):
            t = k * dt
            if controller is not None:
                xv = x
                getv = lambda nm, xv=xv: xv[self.nodes[str(nm)]] if self.nodes[str(nm)] >= 0 else 0.0
                geti = lambda bn, xv=xv: xv[len(self.node_names) + self.branches.index(bn)]
                ctrl_state.update(controller(t, getv, geti))
            if has_sw:
                state = tuple(bool(ctrl_state[e[1]]) if e[1] in ctrl_state else bool(e[4](t)) for e in sw_elems)
                if state not in lu_cache:
                    lu_cache[state] = self._build_linear(t, sw_state={e[1]: s_ for e, s_ in zip(sw_elems, state)})[0]
                G = lu_cache[state]
            else:
                G = G0
            use_be = method == "be" or k == 1
            a = 1 / dt if use_be else 2 / dt
            A = G + a * Cm
            rhs = self._rhs(t) + a * (Cm @ x) + (0 if use_be else qd)
            if not self.nl:
                key = (state if has_sw else None, use_be)
                if key not in lu_lin:
                    lu_lin[key] = lu_factor(A)
                x_new = lu_solve(lu_lin[key], rhs)
                qd = Cm @ (x_new - x) / dt if use_be else 2 * Cm @ (x_new - x) / dt - qd
                x = x_new
                if t >= tstart_save and k % save_every == 0:
                    ts.append(t)
                    xs.append(x.copy())
                continue
            try:
                x_new, _ = self._newton(A, rhs, x.copy())
                if use_be:
                    qd = Cm @ (x_new - x) / dt
                else:
                    qd = 2 * Cm @ (x_new - x) / dt - qd
            except RuntimeError:
                x_new = self._substep(G, Cm, x, t - dt, dt, depth=0)
                qd = Cm @ (x_new - x) / dt
            x = x_new
            if t >= tstart_save and k % save_every == 0:
                ts.append(t)
                xs.append(x.copy())
        return TranResult(self, np.array(ts), np.array(xs))

    def _substep(self, G, Cm, x, t0, dt, depth):
        """Recover from a failed step: split it into 8 backward-Euler sub-steps (recursively)."""
        if depth > 3:
            raise RuntimeError(f"transient step failed at t={t0:.3e} ({self.title})")
        h = dt / 8
        for j in range(1, 9):
            A = G + Cm / h
            rhs = self._rhs(t0 + j * h) + (Cm @ x) / h
            try:
                x, _ = self._newton(A, rhs, x.copy())
            except RuntimeError:
                x = self._substep(G, Cm, x, t0 + (j - 1) * h, h, depth + 1)
        return x

    def _pack(self, x):
        d = {nm: x[i] for nm, i in self.nodes.items() if i >= 0}
        for j, bn in enumerate(self.branches):
            d[f"I({bn})"] = x[len(self.node_names) + j]
        return d

    # ------------------------------------------------------------ export
    def to_spice(self):
        """Export a SPICE netlist (LTspice / ngspice compatible, op-amps as behavioural)."""
        nm = {i: n for n, i in self.nodes.items() if n not in ("gnd",)}
        nm[-1] = "0"
        L = [f"* {self.title} — exported by eelab.circuit"]
        for e in self.elems:
            k, name = e[0], e[1]
            if "_" in name and any(name.endswith(s) for s in ("_r1", "_c1", "_rin", "_ro")):
                continue
            if k == "R":
                L.append(f"R{name} {nm[e[2]]} {nm[e[3]]} {e[4]:.6g}")
            elif k == "C":
                L.append(f"C{name} {nm[e[2]]} {nm[e[3]]} {e[4]:.6g}")
            elif k == "L":
                L.append(f"L{name} {nm[e[2]]} {nm[e[3]]} {e[4]:.6g}")
            elif k == "V":
                L.append(f"V{name} {nm[e[2]]} {nm[e[3]]} DC {e[4]} AC {e[5]}"
                         + ("  ; time-varying in eelab" if e[6] else ""))
            elif k == "I":
                L.append(f"I{name} {nm[e[2]]} {nm[e[3]]} DC {e[4]} AC {e[5]}")
            elif k == "E":
                L.append(f"E{name} {nm[e[2]]} {nm[e[3]]} {nm[e[4]]} {nm[e[5]]} {e[6]}")
            elif k == "G":
                L.append(f"G{name} {nm[e[2]]} {nm[e[3]]} {nm[e[4]]} {nm[e[5]]} {e[6]}")
            elif k == "SW":
                L.append(f"* switch {name} between {nm[e[2]]} and {nm[e[3]]} (Ron={e[5]}, Roff={e[6]})")
        for l1, l2, k in self.couplings:
            L.append(f"K_{l1}_{l2} L{l1} L{l2} {k}")
        models = set()
        for d in self.nl:
            k, name = d[0], d[1]
            if k == "D":
                L.append(f"D{name} {nm[d[2]]} {nm[d[3]]} D_{name}")
                models.add(f".model D_{name} D(Is={d[4]:.3g} N={d[5]}"
                           + (f" BV={d[6]}" if d[6] else "") + ")")
            elif k == "Q":
                L.append(f"Q{name} {nm[d[2]]} {nm[d[3]]} {nm[d[4]]} Q_{name}")
                models.add(f".model Q_{name} {'NPN' if d[5] > 0 else 'PNP'}(Is={d[6]:.3g} BF={d[7]}"
                           f" BR={d[8]}" + (f" VAF={d[9]}" if np.isfinite(d[9]) else "") + ")")
            elif k == "M":
                L.append(f"M{name} {nm[d[2]]} {nm[d[3]]} {nm[d[4]]} {nm[d[4]]} M_{name}")
                models.add(f".model M_{name} {'NMOS' if d[5] > 0 else 'PMOS'}(KP={d[6]:.3g} "
                           f"VTO={d[7] * d[5]} LAMBDA={d[8]})")
        for name, m in getattr(self, "opamp_meta", {}).items():
            L.append(f"* op-amp {name}: A0={m['A0']:.3g}, GBW={m['GBW']:.3g} Hz, SR={m['SR']:.3g} V/s")
            L.append(f"XU{name} {m['inp']} {m['inn']} {m['out']} OPAMP1P A0={m['A0']:.4g} "
                     f"GBW={m['GBW']:.4g}")
        if getattr(self, "opamp_meta", None):
            L += [".subckt OPAMP1P inp inn out A0=2e5 GBW=1e6",
                  "G1 0 x inp inn {A0/1e6}", "R1 x 0 1e6", "C1 x 0 {1/(6.2832*GBW/A0*1e6)}",
                  "E1 o 0 x 0 1", "Ro o out 50", ".ends"]
        L += sorted(models)
        L += [".end"]
        return "\n".join(L) + "\n"


class ACResult:
    def __init__(self, ckt, f, X):
        self.ckt, self.f, self.X = ckt, f, X

    def v(self, node):
        i = self.ckt.nodes[str(node)]
        return np.zeros(len(self.f), complex) if i < 0 else self.X[:, i]

    def i(self, branch):
        return self.X[:, len(self.ckt.node_names) + self.ckt.branches.index(branch)]


class TranResult:
    def __init__(self, ckt, t, X):
        self.ckt, self.t, self.X = ckt, t, X

    def v(self, node):
        i = self.ckt.nodes[str(node)]
        return np.zeros(len(self.t)) if i < 0 else self.X[:, i]

    def i(self, branch):
        return self.X[:, len(self.ckt.node_names) + self.ckt.branches.index(branch)]


def e_series(value, series=24):
    """Nearest standard E-series value."""
    tables = {
        12: [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2],
        24: [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3,
             4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1],
    }
    t = np.array(tables[series])
    dec = 10 ** np.floor(np.log10(value))
    cands = np.concatenate([t * dec, [10 * dec]])
    return float(cands[np.argmin(np.abs(np.log(cands / value)))])
