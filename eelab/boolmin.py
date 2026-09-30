"""Two-level Boolean minimisation helpers shared by AM-133/134: prime implicants (Quine–McCluskey
merging), exact minimum cover (branch and bound), greedy cover, and evaluation of covers.
An implicant is (value, mask): bits set in mask are don't-care positions."""
from itertools import combinations


def prime_implicants(minterms, dontcares, n):
    terms = {(m, 0) for m in set(minterms) | set(dontcares)}
    primes = set()
    while terms:
        merged, used = set(), set()
        by = {}
        for v, m in terms:
            by.setdefault((m, bin(v).count("1")), []).append(v)
        for (m, c), vs in by.items():
            for v in vs:
                for w in by.get((m, c + 1), []):
                    d = v ^ w
                    if d & (d - 1) == 0 and not (d & m):
                        merged.add((v & ~d, m | d)); used.add((v, m)); used.add((w, m))
        primes |= terms - used
        terms = merged
    return primes


def covers(imp, minterm):
    v, m = imp
    return (minterm & ~m) == v


def literals(imp, n):
    return n - bin(imp[1]).count("1")


def greedy_cover(primes, minterms, n):
    left = set(minterms); chosen = []
    cov = {p: {m for m in minterms if covers(p, m)} for p in primes}
    # essential primes first (a minterm covered by exactly one prime), then largest remaining group
    for m in list(left):
        who = [p for p in primes if m in cov[p]]
        if len(who) == 1 and who[0] not in chosen:
            chosen.append(who[0])
    for p in chosen:
        left -= cov[p]
    while left:
        best = max(primes, key=lambda p: (len(cov[p] & left), -literals(p, n)))
        chosen.append(best); left -= cov[best]
    return chosen


def exact_cover(primes, minterms, n):
    """Minimum number of product terms (ties broken toward fewer literals where the reductions allow).
    Classical covering-table method: essential columns, row dominance, column dominance, then branch and bound
    with an independent-set lower bound on the remaining cyclic core."""
    primes = list(primes)
    lits = [literals(p, n) for p in primes]
    col_rows = [frozenset(m for m in minterms if covers(p, m)) for p in primes]
    best = [greedy_cover(set(primes), minterms, n)]

    def reduce(rows, cols, sel):
        rows = set(rows); cols = set(cols); sel = list(sel)
        changed = True
        while changed and rows:
            changed = False
            cols = {c for c in cols if col_rows[c] & rows}
            rc = {r: [c for c in cols if r in col_rows[c]] for r in rows}
            for r, cs in rc.items():                           # essential columns
                if r in rows and len(cs) == 1:
                    c = cs[0]; sel.append(c); rows -= col_rows[c]; cols.discard(c); changed = True
            if changed:
                continue
            rl = sorted(rows, key=lambda r: len(rc[r]))
            sets = {r: frozenset(rc[r]) for r in rl}
            drop = set()
            for i, r1 in enumerate(rl):                        # row dominance: a row whose column set contains another's is redundant
                if r1 in drop:
                    continue
                for r2 in rl[i + 1:]:
                    if r2 not in drop and sets[r1] <= sets[r2]:
                        drop.add(r2)
            if drop:
                rows -= drop; changed = True; continue
            cl = sorted(cols, key=lambda c: -len(col_rows[c] & rows))
            cr = {c: col_rows[c] & rows for c in cl}
            dropc = set()
            for i, c1 in enumerate(cl):                        # column dominance
                if c1 in dropc:
                    continue
                for c2 in cl[i + 1:]:
                    if c2 not in dropc and cr[c2] <= cr[c1] and lits[c1] <= lits[c2]:
                        dropc.add(c2)
            if dropc:
                cols -= dropc; changed = True
        return rows, cols, sel

    def lower_bound(rows, cols):
        used = set(); k = 0
        for r in sorted(rows, key=lambda r: sum(r in col_rows[c] for c in cols)):
            cs = {c for c in cols if r in col_rows[c]}
            if not (cs & used):
                used |= cs; k += 1
        return k

    def cost(sel):
        return (len(sel), sum(lits[c] if isinstance(c, int) else literals(c, n) for c in sel))

    def rec(rows, cols, sel):
        rows, cols, sel = reduce(rows, cols, sel)
        if not rows:
            if cost(sel) < cost(best[0]):
                best[0] = [primes[c] for c in sel]
            return
        if len(sel) + lower_bound(rows, cols) > len(best[0]):
            return
        r = min(rows, key=lambda q: sum(q in col_rows[c] for c in cols))
        for c in sorted((c for c in cols if r in col_rows[c]), key=lambda c: -len(col_rows[c] & rows)):
            rec(rows - col_rows[c], cols - {c}, sel + [c])

    rec(set(minterms), set(range(len(primes))), [])
    return best[0]


def evaluate(cover, x):
    return any(covers(p, x) for p in cover)


def to_sop(cover, names):
    n = len(names); out = []
    for v, m in cover:
        lits = [(names[i] if (v >> (n - 1 - i)) & 1 else names[i] + "'") for i in range(n) if not (m >> (n - 1 - i)) & 1]
        out.append("".join(lits) or "1")
    return " + ".join(out) or "0"
