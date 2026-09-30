"""2-D finite-volume Poisson solver  −∇·(ε∇V) = ρ  on a uniform grid with Dirichlet nodes (SciPy sparse),
plus flux/field helpers used by the field-theory projects."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

EPS0 = 8.8541878128e-12


def solve(fixed, V0, rho, h, eps=None):
    """fixed: bool mask of Dirichlet nodes; V0: their values; rho: charge density (C/m³ ≙ C/m² per unit length in 2-D) at nodes;
    eps: relative permittivity per node (face values are harmonic means). Returns V."""
    ny, nx = fixed.shape; eps = np.ones((ny, nx)) if eps is None else eps
    idx = -np.ones((ny, nx), int); free = ~fixed; idx[free] = np.arange(free.sum())
    J, I = np.nonzero(free); k = idx[J, I]
    rows, cols, vals = [k], [k], [np.zeros(len(k))]; rhs = rho[J, I] * h * h / EPS0
    diag = np.zeros(len(k))
    for dj, di in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        jj, ii = J + dj, I + di; ok = (jj >= 0) & (jj < ny) & (ii >= 0) & (ii < nx)
        jc, ic = np.clip(jj, 0, ny - 1), np.clip(ii, 0, nx - 1)
        e = np.where(ok, 2 * eps[J, I] * eps[jc, ic] / (eps[J, I] + eps[jc, ic]), 0.0)
        diag += e
        nf = ok & free[jc, ic]; rows.append(k[nf]); cols.append(idx[jj[nf], ii[nf]]); vals.append(-e[nf])
        nd = ok & fixed[jc, ic]; np.add.at(rhs, k[nd], e[nd] * V0[jj[nd], ii[nd]])
    vals[0] = diag
    A = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(len(k), len(k))).tocsr()
    V = V0.astype(float).copy(); V[free] = spsolve(A, rhs)
    return V


def flux_through_box(V, eps, h, j0, j1, i0, i1):
    """Outward flux of D = −ε0 εr ∇V through the rectangle of cell faces between node rows j0..j1 and columns i0..i1 (per unit depth)."""
    def face(a, b):
        return 2 * a * b / (a + b)
    fl = 0.0
    for i in range(i0, i1 + 1):
        fl += -face(eps[j1 + 1, i], eps[j1, i]) * (V[j1 + 1, i] - V[j1, i]) / h * h
        fl += -face(eps[j0 - 1, i], eps[j0, i]) * (V[j0 - 1, i] - V[j0, i]) / h * h
    for j in range(j0, j1 + 1):
        fl += -face(eps[j, i1 + 1], eps[j, i1]) * (V[j, i1 + 1] - V[j, i1]) / h * h
        fl += -face(eps[j, i0 - 1], eps[j, i0]) * (V[j, i0 - 1] - V[j, i0]) / h * h
    return fl * EPS0
