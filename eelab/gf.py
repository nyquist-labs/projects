"""GF(2^m) arithmetic (log/antilog tables) and a Reed–Solomon codec (Berlekamp–Massey, Chien, Forney)."""
import numpy as np


class GF:
    def __init__(self, m=8, prim=0x11D):
        self.m, self.q = m, 1 << m
        self.exp = np.zeros(2 * self.q, int); self.log = np.zeros(self.q, int)
        x = 1
        for i in range(self.q - 1):
            self.exp[i] = x; self.log[x] = i
            x <<= 1
            if x & self.q:
                x ^= prim
        self.exp[self.q - 1: 2 * self.q] = self.exp[: self.q + 1][: 2 * self.q - self.q + 1]
        for i in range(self.q - 1, 2 * self.q):
            self.exp[i] = self.exp[i - (self.q - 1)]

    def mul(self, a, b):
        return 0 if a == 0 or b == 0 else int(self.exp[self.log[a] + self.log[b]])

    def div(self, a, b):
        if b == 0:
            raise ZeroDivisionError
        return 0 if a == 0 else int(self.exp[(self.log[a] - self.log[b]) % (self.q - 1)])

    def inv(self, a):
        return int(self.exp[(self.q - 1 - self.log[a]) % (self.q - 1)])

    def pow(self, a, n):
        return 0 if a == 0 else int(self.exp[(self.log[a] * n) % (self.q - 1)])

    def poly_mul(self, p, q):
        r = [0] * (len(p) + len(q) - 1)
        for i, a in enumerate(p):
            if a:
                for j, b in enumerate(q):
                    if b:
                        r[i + j] ^= self.mul(a, b)
        return r

    def poly_eval(self, p, x):      # p[0] is the highest-degree coefficient
        y = 0
        for c in p:
            y = self.mul(y, x) ^ c
        return y


class RS:
    """Systematic Reed–Solomon RS(n, k) over GF(2^m), first consecutive root α^fcr."""
    def __init__(self, n=255, k=223, gf=None, fcr=0):
        self.gf = gf or GF()
        self.n, self.k, self.t, self.fcr = n, k, (n - k) // 2, fcr
        g = [1]
        for i in range(n - k):
            g = self.gf.poly_mul(g, [1, self.gf.pow(2, i + fcr)])
        self.g = g

    def encode(self, msg):
        msg = list(msg)
        rem = msg + [0] * (self.n - self.k)
        for i in range(self.k):
            c = rem[i]
            if c:
                for j in range(1, len(self.g)):
                    rem[i + j] ^= self.gf.mul(self.g[j], c)
        return msg + rem[self.k:]

    def decode(self, r):
        gf = self.gf; n = self.n
        r = list(r)
        S = [gf.poly_eval(r, gf.pow(2, i + self.fcr)) for i in range(n - self.k)]
        if max(S) == 0:
            return r[: self.k], 0
        # Berlekamp–Massey (Λ stored lowest degree first)
        L, C, B, b, m = 0, [1], [1], 1, 1
        for i in range(len(S)):
            d = S[i]
            for j in range(1, L + 1):
                if j < len(C):
                    d ^= gf.mul(C[j], S[i - j])
            if d == 0:
                m += 1
            elif 2 * L <= i:
                T = C[:]
                coef = gf.div(d, b)
                C = C + [0] * max(0, len(B) + m - len(C))
                for j, bj in enumerate(B):
                    C[j + m] ^= gf.mul(coef, bj)
                L, B, b, m = i + 1 - L, T, d, 1
            else:
                coef = gf.div(d, b)
                C = C + [0] * max(0, len(B) + m - len(C))
                for j, bj in enumerate(B):
                    C[j + m] ^= gf.mul(coef, bj)
                m += 1
        lam = C[: L + 1]
        # Chien search: roots X^-1 of Λ; error at position with locator X = α^(n-1-pos)
        pos = []
        for i in range(n):
            xinv = gf.pow(2, (gf.q - 1 - (n - 1 - i)) % (gf.q - 1))
            val = 0
            for j, c in enumerate(lam):
                val ^= gf.mul(c, gf.pow(xinv, j))
            if val == 0:
                pos.append(i)
        if len(pos) != L:
            raise ValueError("uncorrectable")
        # Forney: Ω(x) = S(x)Λ(x) mod x^(2t)
        Sx = S
        om = [0] * (n - self.k)
        for i in range(n - self.k):
            for j in range(min(i + 1, len(lam))):
                om[i] ^= gf.mul(lam[j], Sx[i - j])
        for p_ in pos:
            X = gf.pow(2, n - 1 - p_); Xi = gf.inv(X)
            num = 0
            for i, c in enumerate(om):
                num ^= gf.mul(c, gf.pow(Xi, i))
            den = 0
            for j in range(1, len(lam), 2):
                den ^= gf.mul(lam[j], gf.pow(Xi, j - 1))
            e = gf.mul(gf.pow(X, 1 - self.fcr), gf.div(num, den))
            r[p_] ^= e
        if max(gf.poly_eval(r, gf.pow(2, i + self.fcr)) for i in range(n - self.k)) != 0:
            raise ValueError("uncorrectable")
        return r[: self.k], len(pos)
