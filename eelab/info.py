"""Information-theory helpers: entropies, mutual information of a joint table, Blahut–Arimoto capacity."""
import numpy as np


def H(p):
    p = np.asarray(p, float); p = p[p > 0] / p.sum()
    return float(-np.sum(p * np.log2(p)))


def h2(e):
    e = np.clip(e, 1e-300, 1 - 1e-16)
    return -e * np.log2(e) - (1 - e) * np.log2(1 - e)


def mutual_info(px, W):
    """I(X;Y) in bits for input distribution px and channel matrix W[x, y] = P(y|x)."""
    py = px @ W; J = px[:, None] * W; nz = J > 0
    return float(np.sum(J[nz] * np.log2(W[nz] / np.broadcast_to(py, W.shape)[nz])))


def blahut_arimoto(W, tol=1e-12, maxit=100000):
    """Capacity (bits) and optimal input distribution of a discrete memoryless channel, with the upper/lower bound gap."""
    nx = W.shape[0]; p = np.full(nx, 1 / nx)
    for it in range(maxit):
        py = p @ W
        with np.errstate(divide="ignore", invalid="ignore"):
            D = np.sum(np.where(W > 0, W * np.log2(W / py), 0.0), 1)
        lo, up = np.log2(np.sum(p * 2 ** D)), D.max()
        if up - lo < tol:
            break
        p = p * 2 ** D; p /= p.sum()
    return lo, p, up - lo, it + 1
