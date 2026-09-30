"""Finite-difference Laplace solver on a uniform 2-D grid with fixed-potential masks (SciPy sparse)."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve


def solve(fixed, V0, eps=None):
    """fixed: bool mask of Dirichlet nodes, V0: their values, eps: optional cell permittivity (same shape)."""
    ny, nx = fixed.shape
    eps = np.ones((ny, nx)) if eps is None else eps
    idx = -np.ones((ny, nx), int)
    free = ~fixed
    idx[free] = np.arange(free.sum())
    rows, cols, vals = [], [], []
    rhs = np.zeros(free.sum())
    J, I = np.nonzero(free)
    for dj, di in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        jj, ii = J + dj, I + di
        ok = (jj >= 0) & (jj < ny) & (ii >= 0) & (ii < nx)
        e = np.where(ok, 0.5 * (eps[J, I] + eps[np.clip(jj, 0, ny - 1), np.clip(ii, 0, nx - 1)]), 0.0)
        k = idx[J, I]
        rows += list(k); cols += list(k); vals += list(e)
        nb_free = ok & free[np.clip(jj, 0, ny - 1), np.clip(ii, 0, nx - 1)]
        rows += list(k[nb_free]); cols += list(idx[jj[nb_free], ii[nb_free]]); vals += list(-e[nb_free])
        nb_fix = ok & fixed[np.clip(jj, 0, ny - 1), np.clip(ii, 0, nx - 1)]
        np.add.at(rhs, k[nb_fix], e[nb_fix] * V0[jj[nb_fix], ii[nb_fix]])
    A = coo_matrix((vals, (rows, cols)), shape=(free.sum(), free.sum())).tocsr()
    V = V0.astype(float).copy()
    V[free] = spsolve(A, rhs)
    return V


def energy(V, eps, h):
    """Electrostatic energy per unit length (2-D), eps in units of ε0."""
    Ex = np.diff(V, axis=1) / h; Ey = np.diff(V, axis=0) / h
    e1 = 0.5 * (eps[:, 1:] + eps[:, :-1]); e2 = 0.5 * (eps[1:, :] + eps[:-1, :])
    return 0.5 * 8.854e-12 * (np.sum(e1 * Ex**2) + np.sum(e2 * Ey**2)) * h * h
