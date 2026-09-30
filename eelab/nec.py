"""Thin-wire method of moments for parallel z-directed wires (dipoles, Yagis).

Piecewise-sinusoidal (PWS) Galerkin method (Richmond): each basis/test function is a
sinusoidal 'V' spanning two segments; the near field of a sinusoidal current filament is
known in closed form (Schelkunoff), so Z_mn = -∫ f_m(z) E_z^n(z) dz needs only a 1-D
Gauss quadrature. Self terms are evaluated on the wire surface (ρ = radius).
"""
import numpy as np

ETA = 376.730313


def _ez(rho, z, zc, d, k):
    """E_z of a PWS mode centred at zc (half-length d, unit current at the centre)."""
    R1 = np.sqrt(rho ** 2 + (z - (zc - d)) ** 2)
    R2 = np.sqrt(rho ** 2 + (z - (zc + d)) ** 2)
    R0 = np.sqrt(rho ** 2 + (z - zc) ** 2)
    return (-1j * ETA / (4 * np.pi * np.sin(k * d))) * (np.exp(-1j * k * R1) / R1 + np.exp(-1j * k * R2) / R2
                                                       - 2 * np.cos(k * d) * np.exp(-1j * k * R0) / R0)


def solve(wires, lam=1.0, nseg=40, radius=None, nq=24):
    """wires: list of (x, length, fed). Returns (list of (x, z_nodes, I_nodes)), Z_in."""
    k = 2 * np.pi / lam
    a = radius if radius is not None else lam / 1000
    modes = []
    for w, (x, L, fed) in enumerate(wires):
        d = L / nseg
        nodes = -L / 2 + d * np.arange(1, nseg)
        for j, zc in enumerate(nodes):
            modes.append((w, x, zc, d, fed and j == (nseg - 1) // 2))
    M = len(modes)
    gx, gw = np.polynomial.legendre.leggauss(nq)
    Z = np.zeros((M, M), complex)
    for m, (wm, xm, zm, dm, _) in enumerate(modes):
        # test function samples on both halves
        zt = np.r_[zm - dm + (gx + 1) * dm / 2, zm + (gx + 1) * dm / 2]
        wt = np.r_[gw, gw] * dm / 2
        ft = np.sin(k * (dm - np.abs(zt - zm))) / np.sin(k * dm)
        for n, (wn, xn, zn, dn, _) in enumerate(modes):
            rho = a if wm == wn else max(abs(xm - xn), a)
            Z[m, n] = -np.sum(wt * ft * _ez(rho, zt, zn, dn, k))
    V = np.array([1.0 if f else 0.0 for *_, f in modes], complex)
    I = np.linalg.solve(Z, V)
    feed = [i for i, md in enumerate(modes) if md[4]][0]
    out = []
    for w, (x, L, fed) in enumerate(wires):
        idx = [i for i, md in enumerate(modes) if md[0] == w]
        zn = np.r_[-L / 2, [modes[i][2] for i in idx], L / 2]
        In = np.r_[0, I[idx], 0]
        out.append((x, zn, In))
    return out, 1.0 / I[feed]


def far_field(currents, lam, theta, phi=0.0, npts=400):
    """|E_theta| (arbitrary units) of parallel z-wires. currents: [(x, z_nodes, I_nodes)]."""
    k = 2 * np.pi / lam
    th = np.atleast_1d(theta)
    E = np.zeros(len(th), complex)
    for x, zn, In in currents:
        zf = np.linspace(zn[0], zn[-1], npts)
        # sinusoidal interpolation between nodes ≈ linear on fine grid is adequate here
        If = np.interp(zf, zn, In.real) + 1j * np.interp(zf, zn, In.imag)
        ph = np.exp(1j * k * (np.outer(np.cos(th), zf) + np.outer(np.sin(th) * np.cos(phi), np.full_like(zf, x))))
        E += np.sin(th) * np.trapezoid(If[None, :] * ph, zf, axis=1)
    return np.abs(E) if np.ndim(theta) else np.abs(E[0])


def directivity(currents, lam, n=361):
    """Directivity (linear) of a z-wire array by integrating over the full sphere."""
    th = np.linspace(1e-3, np.pi - 1e-3, 181)
    ph = np.linspace(0, 2 * np.pi, n)
    P = np.array([far_field(currents, lam, th, p_) ** 2 for p_ in ph])   # (phi, theta)
    tot = np.trapezoid(np.trapezoid(P * np.sin(th)[None, :], th, axis=1), ph)
    return 4 * np.pi * P.max() / tot, P, th, ph
