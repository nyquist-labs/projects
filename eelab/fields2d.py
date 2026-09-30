"""2-D electrostatic cross-section solver for PCB transmission lines (quasi-TEM).

Rectangular grid inside a grounded box; the bottom edge is the reference plane (y = 0). Dielectric
layers and rectangular conductors (traces, coplanar grounds, planes) are given in metres.
Capacitance matrices come from the field energy; the inductance matrix from the air-filled
capacitance, L = μ0 ε0 C0⁻¹ (valid for TEM/quasi-TEM lines).
"""
import numpy as np
from scipy.special import ellipk

from .laplace import solve, energy

EPS0, MU0, C0 = 8.8541878128e-12, 4e-7 * np.pi, 299792458.0


class Section:
    def __init__(self, width, height, dx):
        self.dx = dx
        self.nx, self.ny = int(round(width / dx)) + 1, int(round(height / dx)) + 1
        self.x = (np.arange(self.nx) - (self.nx - 1) / 2) * dx
        self.y = np.arange(self.ny) * dx
        self.layers = []           # (y0, y1, er)
        self.conductors = []       # list of lists of rectangles (x0, x1, y0, y1)
        self.grounds = []          # extra grounded rectangles

    def dielectric(self, y0, y1, er):
        self.layers.append((y0, y1, er))

    def conductor(self, *rects):
        self.conductors.append(list(rects))
        return len(self.conductors) - 1

    def ground(self, *rects):
        self.grounds += list(rects)

    def _mask(self, rects):
        X, Y = np.meshgrid(self.x, self.y)
        m = np.zeros((self.ny, self.nx), bool)
        tol = self.dx * 0.5
        for x0, x1, y0, y1 in rects:
            m |= (X >= x0 - tol) & (X <= x1 + tol) & (Y >= y0 - tol) & (Y <= y1 + tol)
        return m

    def eps(self, air=False):
        e = np.ones((self.ny, self.nx))
        if air:
            return e
        Y = self.y[:, None] * np.ones((1, self.nx))
        for y0, y1, er in self.layers:
            inside = (Y > y0 + 1e-12) & (Y < y1 - 1e-12)
            e[inside] = er
            for yb in (y0, y1):                     # interface nodes get the mean of both sides
                j = int(round(yb / self.dx))
                if 0 <= j < self.ny:
                    above = next((l[2] for l in self.layers if l[0] <= yb + 1e-12 < l[1]), 1.0)
                    below = next((l[2] for l in self.layers if l[0] - 1e-12 < yb <= l[1]), 1.0)
                    e[j, :] = 0.5 * (above + below)
        return e

    def cap_matrix(self, air=False):
        n = len(self.conductors)
        masks = [self._mask(r) for r in self.conductors]
        gnd = np.zeros((self.ny, self.nx), bool)
        gnd[0, :] = gnd[-1, :] = True; gnd[:, 0] = gnd[:, -1] = True
        if self.grounds:
            gnd |= self._mask(self.grounds)
        fixed = gnd.copy()
        for m in masks:
            fixed |= m
        e = self.eps(air)
        W = {}

        def energy_for(on):
            V0 = np.zeros((self.ny, self.nx))
            for k in on:
                V0[masks[k]] = 1.0
            V = solve(fixed, V0, e)
            return energy(V, e, self.dx) / EPS0 * EPS0   # energy() already includes ε0
        for i in range(n):
            W[(i,)] = energy_for([i])
        C = np.zeros((n, n))
        for i in range(n):
            C[i, i] = 2 * W[(i,)]
            for j in range(i + 1, n):
                C[i, j] = C[j, i] = energy_for([i, j]) - W[(i,)] - W[(j,)]
        return C

    def line(self):
        """Returns dict with C, C0, L matrices, Z0 (single conductor) or Z-matrix, eps_eff."""
        C = self.cap_matrix(); Ca = self.cap_matrix(air=True)
        L = MU0 * EPS0 * np.linalg.inv(Ca)
        out = dict(C=C, C0=Ca, L=L)
        if C.shape == (1, 1):
            out["Z0"] = float(np.sqrt(L[0, 0] / C[0, 0])); out["eps_eff"] = float(C[0, 0] / Ca[0, 0])
            out["vp"] = C0 / np.sqrt(out["eps_eff"])
        return out


def hammerstad(w, h, er, t=0.0):
    """Hammerstad–Jensen microstrip Z0 and εeff (with a simple thickness correction)."""
    if t > 0:
        w = w + t / np.pi * (1 + np.log(2 * h / t))
    u = w / h
    ee = (er + 1) / 2 + (er - 1) / 2 / np.sqrt(1 + 12 / u)
    z = 60 / np.sqrt(ee) * np.log(8 / u + u / 4) if u < 1 else 120 * np.pi / (np.sqrt(ee) * (u + 1.393 + 0.667 * np.log(u + 1.444)))
    return z, ee


def wheeler_width(z0, h, er):
    """Microstrip synthesis (Wheeler / Hammerstad): width for a target Z0."""
    A = z0 / 60 * np.sqrt((er + 1) / 2) + (er - 1) / (er + 1) * (0.23 + 0.11 / er)
    B = 377 * np.pi / (2 * z0 * np.sqrt(er))
    u = 8 * np.exp(A) / (np.exp(2 * A) - 2)
    if u > 2:
        u = 2 / np.pi * (B - 1 - np.log(2 * B - 1) + (er - 1) / (2 * er) * (np.log(B - 1) + 0.39 - 0.61 / er))
    return u * h


def gcpw(w, s, h, er):
    """Grounded coplanar waveguide (conformal mapping, zero thickness): Z0, εeff."""
    K = lambda k: ellipk(k * k)
    k = w / (w + 2 * s)
    k3 = np.tanh(np.pi * w / (4 * h)) / np.tanh(np.pi * (w + 2 * s) / (4 * h))
    kp, k3p = np.sqrt(1 - k * k), np.sqrt(1 - k3 * k3)
    r = K(kp) * K(k3) / (K(k) * K(k3p))
    ee = (1 + er * r) / (1 + r)
    z = 60 * np.pi / np.sqrt(ee) / (K(k) / K(kp) + K(k3) / K(k3p))
    return z, ee


def extrapolate(build, dxs=(0.2e-3, 0.1e-3, 0.05e-3), key="Z0"):
    """Run a Section factory on three halving grids and Richardson-extrapolate `key` with the observed order.
    Returns (extrapolated value, list of raw values, observed order)."""
    vals = [build(dx).line()[key] for dx in dxs]
    d1, d2 = vals[1] - vals[0], vals[2] - vals[1]
    r = d2 / d1 if d1 else 0.0
    if 0 < r < 1:
        order = np.log2(1 / r)
        return vals[2] + d2 * r / (1 - r), vals, order
    return vals[2], vals, float("nan")
