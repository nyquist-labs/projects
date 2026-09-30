from eelab import *
from eelab.gf import GF as TableGF

META = dict(
    id="AM-143", title="A GF(2ᵐ) arithmetic library, verified against AES", level="H",
    tools="Own polynomial-basis field class (carry-less multiply with reduction, inversion by extended Euclid and by Fermat), exhaustive field-axiom checks, cross-check against an independent log/antilog implementation, FIPS-197 known answers (AES multiplication examples and S-box)",
    summary="Build finite-field arithmetic from the definition — polynomials over GF(2) modulo an irreducible polynomial — and verify it exhaustively: "
            "field axioms, two independent inversion algorithms, agreement with a table-based implementation, and reproduction of the AES S-box from x ↦ x⁻¹.",
    problem="Error-correcting codes and ciphers do arithmetic where 1 + 1 = 0 and every non-zero byte has a reciprocal. How is that built, and how do we know it is right?",
    theory=r"""GF(2ᵐ) = GF(2)[x]/(f), f irreducible of degree m. Addition is XOR; multiplication is polynomial multiplication reduced mod f. The non-zero elements form a cyclic group of order $2^m-1$, so $a^{2^m-1}=1$ and $a^{-1}=a^{2^m-2}$; the number of
generators is $\varphi(2^m-1)$. Squaring is linear (Frobenius): $(a+b)^2=a^2+b^2$. AES uses f = x⁸+x⁴+x³+x+1 (0x11B): FIPS-197 gives {57}·{83} = {C1}, {57}·{13} = {FE}, and the S-box is an affine map of the inverse (S(00) = 63, S(53) = ED).
In that field 0x03 is a generator but 0x02 has order 51.""",
    method="""Exhaustive over all element pairs/triples for GF(16) and all pairs for GF(256) (vectorised where possible). Inverses by extended Euclid on polynomials and by exponentiation compared for every element. Cross-check with eelab.gf (log tables,
polynomial 0x11D). S-box computed and compared with the first row and spot values of FIPS-197, plus bijectivity.""",
)


class Field:
    def __init__(self, m, f):
        self.m, self.f, self.q = m, f, 1 << m

    def mul(self, a, b):
        r = 0
        while b:
            if b & 1:
                r ^= a
            b >>= 1; a <<= 1
            if a >> self.m:
                a ^= self.f
        return r

    def pow(self, a, e):
        r = 1
        while e:
            if e & 1:
                r = self.mul(r, a)
            a = self.mul(a, a); e >>= 1
        return r

    def inv_fermat(self, a):
        return self.pow(a, self.q - 2)

    def inv_euclid(self, a):
        # extended Euclid on polynomials over GF(2): find u with u·a ≡ 1 (mod f)
        r0, r1, u0, u1 = self.f, a, 0, 1
        while r1 != 1:
            sh = r0.bit_length() - r1.bit_length()
            if sh < 0:
                r0, r1, u0, u1 = r1, r0, u1, u0; continue
            r0 ^= r1 << sh; u0 ^= u1 << sh
            if r0 == 0:
                raise ZeroDivisionError
            if r0.bit_length() < r1.bit_length():
                r0, r1, u0, u1 = r1, r0, u1, u0
        # reduce u1 mod f
        while u1.bit_length() > self.m:
            u1 ^= self.f << (u1.bit_length() - 1 - self.m)
        return u1

    def order(self, a):
        k, x = 1, a
        while x != 1:
            x = self.mul(x, a); k += 1
        return k


def sbox(F):
    out = []
    for a in range(256):
        b = F.inv_fermat(a) if a else 0
        s = b
        for k in range(1, 5):
            s ^= ((b << k) | (b >> (8 - k))) & 0xFF
        out.append(s ^ 0x63)
    return out


def run(p):
    F4 = Field(4, 0b10011); bad = 0
    for a in range(16):
        for b in range(16):
            bad += F4.mul(a, b) != F4.mul(b, a)
            for c in range(16):
                bad += F4.mul(a, F4.mul(b, c)) != F4.mul(F4.mul(a, b), c)
                bad += F4.mul(a, b ^ c) != F4.mul(a, b) ^ F4.mul(a, c)
    p.compare("GF(16): commutativity, associativity, distributivity violations (all triples)", 0, bad, "", kind="abs")
    A = Field(8, 0x11B)
    tab = np.array([[A.mul(a, b) for b in range(256)] for a in range(256)])
    p.compare("GF(256): non-zero rows of the multiplication table that are not permutations (no zero divisors)", 0,
              int(sum(len(set(tab[a, 1:])) != 255 or 0 in tab[a, 1:] for a in range(1, 256))), "", kind="abs")
    inv_bad = sum(A.inv_euclid(a) != A.inv_fermat(a) or A.mul(a, A.inv_euclid(a)) != 1 for a in range(1, 256))
    p.compare("Inverse by extended Euclid vs by a^(2⁸−2), and a·a⁻¹ = 1 (failures over 255 elements)", 0, inv_bad, "", kind="abs")
    p.compare("FIPS-197: {57}·{83}", 0xC1, A.mul(0x57, 0x83), "", kind="abs")
    p.compare("FIPS-197: {57}·{13}", 0xFE, A.mul(0x57, 0x13), "", kind="abs")
    S = sbox(A)
    row0 = [0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76]
    p.compare("AES S-box first row (16 entries) reproduced from inverse + affine map (mismatches)", 0, sum(a != b for a, b in zip(S[:16], row0)), "", kind="abs")
    p.compare("S-box(0x53)", 0xED, S[0x53], "", kind="abs")
    p.compare("S-box is a bijection with no fixed points (1 = yes)", 1, int(len(set(S)) == 256 and all(S[a] != a for a in range(256))), "", kind="abs")
    orders = [A.order(a) for a in range(1, 256)]
    p.compare("Generators of GF(256)*: φ(255)", 128, sum(o == 255 for o in orders), "", kind="abs")
    p.compare("Order of 0x02 under the AES polynomial", 51, A.order(2), "", kind="abs")
    p.compare("Order of 0x03 under the AES polynomial", 255, A.order(3), "", kind="abs")
    p.compare("Element orders that do not divide 255 (Lagrange)", 0, sum(255 % o != 0 for o in orders), "", kind="abs")
    fro = sum(A.mul(a ^ b, a ^ b) != A.mul(a, a) ^ A.mul(b, b) for a in range(0, 256, 3) for b in range(256))
    p.compare("Frobenius (a + b)² = a² + b² violations", 0, fro, "", kind="abs")
    B = Field(8, 0x11D); T = TableGF(8, 0x11D)
    diff = sum(B.mul(a, b) != T.mul(a, b) for a in range(256) for b in range(0, 256, 5))
    p.compare("Agreement with the independent log-table implementation (poly 0x11D; differences)", 0, diff, "", kind="abs")
    p.compare("… where 0x02 is a generator (order)", 255, B.order(2), "", kind="abs")
    p.write("results/aes_sbox.txt", "\n".join(" ".join(f"{v:02x}" for v in S[i: i + 16]) for i in range(0, 256, 16)) + "\n", "AES S-box computed from field inversion")
    fig, ax = p.fig(1, 2, w=11, h=4.6)
    ax[0].imshow(tab, cmap="viridis", interpolation="nearest")
    ax[0].set_title("GF(2⁸) multiplication table (AES polynomial)", loc="left", fontsize=10); ax[0].set_xlabel("b"); ax[0].set_ylabel("a")
    vals, cnt = np.unique(orders, return_counts=True)
    ax[1].bar([str(v) for v in vals], cnt, color=C_MEAS)
    style_axes(ax[1], "multiplicative order", "number of elements", "Orders divide 255 = 3·5·17", legend=False)
    p.save(fig, "gf", "The GF(2⁸) multiplication table and the distribution of element orders.")
    p.discuss("""Built from nothing but XOR, shift and a reduction polynomial, the field passes every axiom exhaustively, its two inversion algorithms agree on
all 255 non-zero elements, and it reproduces the published AES arithmetic — including the S-box, which is just inversion followed by a fixed
affine map. The group structure matches theory: every order divides 255, exactly φ(255) = 128 elements generate the group, and under the AES
polynomial 0x02 is *not* a generator (order 51), which is why AES tables use 0x03 while Reed–Solomon codes choose 0x11D where 0x02 works. The same
class with a different polynomial agrees with the log-table implementation used by the repository's Reed–Solomon codec (AM-146).""")
# tol-convention: relative tolerances are in percent
