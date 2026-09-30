"""Shared communications helpers: convolutional code (k=7, r=1/2) + Viterbi, bit utilities."""
import numpy as np

G1, G2 = 0o171, 0o133   # CCSDS / NASA standard polynomials (also used by Meteor-M LRPT)


def conv_encode(bits, g1=G1, g2=G2, K=7):
    state = 0; out = []
    for b in list(bits) + [0] * (K - 1):
        state = ((state << 1) | int(b)) & ((1 << K) - 1)
        out.append(bin(state & g1).count("1") & 1)
        out.append(bin(state & g2).count("1") & 1)
    return np.array(out, np.int8)


def viterbi_decode(soft, nbits, g1=G1, g2=G2, K=7):
    """Soft-decision Viterbi. soft: array of +/-1-ish values (positive = bit 0 sent as +1)."""
    S = 1 << (K - 1)
    states = np.arange(S)
    outs = {}
    for s in range(S):
        for b in (0, 1):
            full = ((s << 1) | b) & ((1 << K) - 1)
            outs[(s, b)] = (bin(full & g1).count("1") & 1, bin(full & g2).count("1") & 1, full & (S - 1))
    # vectorised tables
    nxt = np.zeros((S, 2), int); o1 = np.zeros((S, 2)); o2 = np.zeros((S, 2))
    for (s, b), (a, c, n) in outs.items():
        nxt[s, b] = n; o1[s, b] = 1 - 2 * a; o2[s, b] = 1 - 2 * c
    metric = np.full(S, -1e18); metric[0] = 0
    T = len(soft) // 2
    back = np.zeros((T, S), np.int32); bitdec = np.zeros((T, S), np.int8)
    for t in range(T):
        r1, r2 = soft[2 * t], soft[2 * t + 1]
        cand = metric[:, None] + r1 * o1 + r2 * o2         # (S, 2)
        newm = np.full(S, -1e18); prev = np.zeros(S, int); bb = np.zeros(S, np.int8)
        for b in (0, 1):
            ns = nxt[:, b]
            better = cand[:, b] > newm[ns]
            # resolve collisions: two states map to same next state for each b
            order = np.argsort(cand[:, b])
            for s in order:
                n = ns[s]
                if cand[s, b] > newm[n]:
                    newm[n] = cand[s, b]; prev[n] = s; bb[n] = b
        metric = newm; back[t] = prev; bitdec[t] = bb
    s = int(np.argmax(metric)); dec = []
    for t in range(T - 1, -1, -1):
        dec.append(bitdec[t, s]); s = back[t, s]
    return np.array(dec[::-1][:nbits], np.int8)


def conv_encode_batch(bits, gens=(0o7, 0o5), K=3, terminate=True):
    """Rate-1/n convolutional encoder for a batch. bits: (B, N) 0/1. Returns (B, T, n) with T = N + K − 1 when
    terminated. Same register convention as conv_encode (newest bit is the LSB of the K-bit register)."""
    bits = np.atleast_2d(np.asarray(bits, np.int8))
    B, N = bits.shape
    u = np.concatenate([np.zeros((B, K - 1), np.int8), bits, np.zeros((B, K - 1 if terminate else 0), np.int8)], 1)
    T = u.shape[1] - (K - 1)
    out = np.zeros((B, T, len(gens)), np.int8)
    for j, g in enumerate(gens):
        for i in range(K):
            if (g >> i) & 1:
                out[:, :, j] ^= u[:, K - 1 - i: K - 1 - i + T]
    return out


def viterbi_batch(soft, gens=(0o7, 0o5), K=3, terminated=True, return_all=False):
    """Vectorised soft-decision Viterbi for a batch of blocks. soft: (B, T, n), positive = bit 0.
    Returns decoded bits (B, T); with return_all also the survivor decisions (T, B, S) and the best state per step."""
    soft = np.asarray(soft, np.float32)
    B, T, n = soft.shape
    S = 1 << (K - 1)
    st = np.arange(S)
    prev = np.zeros((2, S), int); sign = np.zeros((2, S, n), np.float32)
    for hb in (0, 1):
        full = st | (hb << (K - 1))
        prev[hb] = full >> 1
        for j, g in enumerate(gens):
            par = np.array([bin(int(f) & g).count("1") & 1 for f in full])
            sign[hb, :, j] = 1 - 2 * par
    metric = np.full((B, S), -1e9, np.float32); metric[:, 0] = 0
    dec = np.zeros((T, B, S), np.uint8); best = np.zeros((T, B), np.int32) if return_all else None
    for t in range(T):
        c0 = metric[:, prev[0]] + soft[:, t, :] @ sign[0].T
        c1 = metric[:, prev[1]] + soft[:, t, :] @ sign[1].T
        d = c1 > c0
        dec[t] = d; metric = np.where(d, c1, c0)
        if return_all:
            best[t] = metric.argmax(1)
    state = np.zeros(B, int) if terminated else metric.argmax(1)
    out = np.zeros((B, T), np.int8); bi = np.arange(B)
    for t in range(T - 1, -1, -1):
        out[:, t] = state & 1
        state = (state | (dec[t, bi, state].astype(int) << (K - 1))) >> 1
    if return_all:
        return out, dec, best, metric
    return out
