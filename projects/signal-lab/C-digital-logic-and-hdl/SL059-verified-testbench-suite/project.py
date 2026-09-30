from eelab import *
from eelab import hdl

META = dict(
    id="SL-059", title="Verified testbench suite: assertions and coverage", level="M",
    tools="SystemVerilog-style testbench (immediate assertions, functional coverage bins), Icarus Verilog",
    summary="Build a self-checking, coverage-driven testbench for the SL-041 ALU: 8 ops × 4 flag outcomes × "
            "operand-class bins; measure how many random vectors reach full coverage, catch an injected "
            "bug, and compare with the coupon-collector prediction.",
    problem="How do you know a testbench has tested enough? Measure functional coverage, and check that "
            "the checker actually catches bugs.",
    theory=r"""With B equally likely bins, the expected number of random draws to hit all of them is the coupon-collector
value $B\,H_B \approx B(\ln B + 0.577)$. Rare bins break the equal-probability assumption — e.g. "ADD with
signed overflow AND zero result" happens only for $a=b=-128$ (p = 2⁻¹⁶) — so constrained-random or
directed vectors are needed for those. A mutation (injected bug) must make at least one assertion fire.""",
    method="""Coverage model: op (8) × result class {zero, negative, positive} (3) × carry (2) = 48 bins, of which the
reachable ones are counted by exhaustive enumeration in Python. Testbench draws random vectors, updates
bins, and stops at full reachable coverage. Then the ALU is mutated (SLT using unsigned compare) and the
same testbench must report assertion failures.""",
)

import importlib.util, pathlib


def load_alu():
    spec = importlib.util.spec_from_file_location("sl041", pathlib.Path(__file__).parent.parent / "SL041-8bit-alu" / "project.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.ALU


TB = """
module tb;
  reg [7:0] a, b; reg [2:0] op; wire [7:0] y; wire z, n, c, v;
  alu8 dut(a, b, op, y, z, n, c, v);
  reg hit [0:47]; integer nbins_hit = 0, draws = 0, fails = 0, target, i, seed = 5;
  integer sa, sb; reg [8:0] full; reg [7:0] ey; reg ec;
  function integer bin(input [2:0] o, input [7:0] r, input cc);
    bin = o * 6 + ((r == 0) ? 0 : r[7] ? 1 : 2) * 2 + cc;
  endfunction
  initial begin
    target = TARGET;
    for (i = 0; i < 48; i = i + 1) hit[i] = 0;
    while (nbins_hit < target && draws < 2000000) begin
      a = $random(seed); b = $random(seed); op = $random(seed); #1;
      sa = $signed(a); sb = $signed(b); ec = 0;
      case (op)
        0: begin full = a + b; ey = full[7:0]; ec = full[8]; end
        1: begin full = a + (~b & 8'hFF) + 1; ey = full[7:0]; ec = full[8]; end
        2: ey = a & b; 3: ey = a | b; 4: ey = a ^ b;
        5: begin ey = a << 1; ec = a[7]; end
        6: begin ey = a >> 1; ec = a[0]; end
        7: ey = (sa < sb) ? 1 : 0;
      endcase
      // immediate assertions
      if (y !== ey) begin fails = fails + 1; if (fails < 4) $display("ASSERT FAIL op=%0d a=%0d b=%0d y=%0d exp=%0d", op, a, b, y, ey); end
      if (z !== (y == 0)) fails = fails + 1;
      if (c !== ec) fails = fails + 1;
      draws = draws + 1;
      if (!hit[bin(op, y, c)]) begin hit[bin(op, y, c)] = 1; nbins_hit = nbins_hit + 1; $display("COV %0d %0d", draws, nbins_hit); end
    end
    $display("RES draws %0d", draws);
    $display("RES bins %0d", nbins_hit);
    $display("RES fails %0d", fails);
    $finish;
  end
endmodule
"""


def reachable():
    bins = {}
    for o in range(8):
        for a in range(256):
            for b in range(256):
                sa, sb = a - 256 * (a > 127), b - 256 * (b > 127)
                c = 0
                if o == 0: f = a + b; y = f & 255; c = f >> 8
                elif o == 1: f = a + (~b & 255) + 1; y = f & 255; c = f >> 8
                elif o == 2: y = a & b
                elif o == 3: y = a | b
                elif o == 4: y = a ^ b
                elif o == 5: y = (a << 1) & 255; c = a >> 7
                elif o == 6: y = a >> 1; c = a & 1
                else: y = int(sa < sb)
                k = o * 6 + (0 if y == 0 else 1 if y > 127 else 2) * 2 + c
                bins[k] = bins.get(k, 0) + 1
    return bins


def expected_draws(probs):
    """Coupon collector with unequal probabilities: E[T] = ∫₀^∞ (1 − Π(1 − e^{−p_i t})) dt."""
    t = np.logspace(0, 9, 20000)
    surv = 1 - np.prod(1 - np.exp(-np.outer(t, probs)), axis=1)
    return float(np.trapezoid(surv, t) + 1.0)


def run(p):
    ALU = load_alu()
    reach = reachable()
    B = len(reach)
    p.metric("Reachable coverage bins (of 48)", B, "", "found by exhaustive enumeration")
    log, _ = hdl.simulate(p, {"alu8.v": ALU, "tb_coverage.v": TB.replace("TARGET", str(B))}, "tb")
    r = hdl.results(log)
    cov = np.array([list(map(int, l.split()[1:])) for l in log.splitlines() if l.startswith("COV")])
    p.compare("Assertion failures on correct ALU", 0, r["fails"], "", kind="abs")
    p.compare("Coverage reached (bins)", B, r["bins"], "", kind="abs")
    H = sum(1 / k for k in range(1, B + 1))
    probs = np.array([c / (8 * 65536) for c in reach.values()])
    Et = expected_draws(probs)
    p.metric("Naive equal-bin estimate B·H_B", B * H, "draws", "badly wrong: bins are far from equiprobable")
    p.compare("Random draws to full coverage (unequal-probability coupon collector)", Et, r["draws"], "draws",
              note="single run; the rarest bin makes this nearly exponential, σ ≈ mean")
    rare = sorted(reach.items(), key=lambda kv: kv[1])[:3]
    names = ["ADD", "SUB", "AND", "OR", "XOR", "SHL", "SHR", "SLT"]
    cls = ["zero", "negative", "positive"]
    p.metric("Rarest bin", f"{names[rare[0][0] // 6]} {cls[(rare[0][0] % 6) // 2]} carry={rare[0][0] % 2}: p = {rare[0][1]}/524288 per draw")
    bug = ALU.replace("sub[7] ^ ((a[7] != b[7]) && (sub[7] != a[7]))", "~sub[8]")   # unsigned compare bug
    log2, _ = hdl.simulate(p, {"alu8_mutant.v": bug, "tb_coverage.v": TB.replace("TARGET", str(B))}, "tb")
    r2 = hdl.results(log2)
    p.compare("Injected bug detected (assertion failures > 0)", 1, int(r2["fails"] > 0), "", kind="abs")
    p.metric("Assertion failures with mutated SLT", r2["fails"])
    fig, ax = p.fig()
    ax.semilogx(cov[:, 0], cov[:, 1], drawstyle="steps-post", color=C_MEAS, label="measured coverage")
    k = np.arange(1, B + 1)
    exp_draws = np.cumsum(B / (B - k + 1))
    ax.semilogx(exp_draws, k, "--", color=C_PRED, label="coupon-collector expectation (equal bins)")
    style_axes(ax, "random vectors applied", "bins hit", "Coverage closure: the last few bins take most of the time")
    p.save(fig, "coverage", "Coverage rises fast, then stalls on rare bins until luck (or a directed test) hits them.")
    p.csv("coverage_curve", draws=cov[:, 0], bins=cov[:, 1])
    p.discuss(f"""Of 48 cross bins only {B} are reachable (e.g. AND can never carry), which exhaustive enumeration finds
before any random testing — declaring unreachable bins is the first step of real coverage closure. The
textbook coupon-collector estimate (B·H_B ≈ 130 draws) is wrong by four orders of magnitude because the
bins are nowhere near equiprobable: the rarest needs a single specific operand pair. Weighting the bins by
their exact probabilities (computed by enumeration) predicts the right order of magnitude; the single
random run scatters around it because the waiting time is dominated by one nearly-exponential event.
The practical lesson: once random coverage plateaus, write a *directed* vector for each rare bin. The mutation test
shows the checker has teeth: turning SLT's signed comparison into an unsigned one is flagged immediately.""")
