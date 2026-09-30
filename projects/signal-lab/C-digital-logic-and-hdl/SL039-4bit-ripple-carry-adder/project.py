from eelab import *
from eelab import hdl

META = dict(
    id="SL-039", title="Ripple-carry adder and its propagation delay", level="E",
    tools="Gate-level Verilog (unit delays), Icarus Verilog, Yosys",
    summary="Chain full adders into 4-, 8-, 16- and 32-bit ripple-carry adders and measure how the "
            "worst-case delay grows with width.",
    problem="A ripple-carry adder is simple, but every bit must wait for the carry from the bit below. "
            "How does the delay scale, and which input pair triggers the worst case?",
    theory=r"""Each stage adds 2 gate delays to the carry path (AND→OR after the first XOR), so the worst case is
$t_{RCA}(n) = 2n + 1$ gate delays (first XOR, then n carry stages; the final sum XOR overlaps). The worst
case is a carry generated at bit 0 that propagates through every bit: $A = 0111\ldots1$, $B = 0\ldots01$.""",
    method="""Parameterised gate-level RCA (generate loop of the SL-038 full adder, 1 ns per gate). For each width the
testbench applies the worst-case transition 0+0 → (2ⁿ⁻¹−1)+1 and measures when the last output bit
settles; 200 random transitions give the average. Yosys reports cell count and logic depth.""",
)

SRC = """
`timescale 1ns/1ps
module fa(input a, b, cin, output s, cout);
  wire p, g, t;
  xor #1 (p, a, b); xor #1 (s, p, cin); and #1 (g, a, b); and #1 (t, p, cin); or #1 (cout, g, t);
endmodule
module rca #(parameter N = 4)(input [N-1:0] a, b, output [N-1:0] s, output cout);
  wire [N:0] c; assign c[0] = 1'b0;
  genvar i;
  generate for (i = 0; i < N; i = i + 1) begin : st
    fa u(a[i], b[i], c[i], s[i], c[i+1]);
  end endgenerate
  assign cout = c[N];
endmodule
"""
TB = """
`timescale 1ns/1ps
module tb;
  parameter N = 4;
  reg [N-1:0] a, b; wire [N-1:0] s; wire cout;
  rca #(N) dut(a, b, s, cout);
  integer k, errs;
  real t0, last, sum;
  always @(s or cout) last = $realtime;
  task measure; begin
    t0 = $realtime; last = t0;
    #(4*N + 10);
  end endtask
  initial begin
    errs = 0; sum = 0.0;
    a = 0; b = 0; #50;
    a = {1'b0, {(N-1){1'b1}}}; b = 1; measure;
    $display("RES worst %0f", last - t0);
    for (k = 0; k < 200; k = k + 1) begin
      a = $random; b = $random; #(4*N + 10);
      a = $random; b = $random; measure;
      if ({cout, s} !== a + b) errs = errs + 1;
      sum = sum + (last - t0);
    end
    $display("RES avg %0f", sum / 200.0);
    $display("RES errors %0d", errs);
    $finish;
  end
endmodule
"""


def run(p):
    widths = [4, 8, 16, 32]
    worst, avg = [], []
    for n in widths:
        tb = TB.replace("parameter N = 4", f"parameter N = {n}")
        log, _ = hdl.simulate(p, {"rca.v": SRC, "tb_rca.v": tb}, "tb")
        r = hdl.results(log)
        worst.append(r["worst"]); avg.append(r["avg"])
        p.compare(f"{n}-bit worst-case delay", 2 * n - 1, r["worst"], "gate delays", kind="abs")
        if r["errors"]:
            p.metric(f"{n}-bit functional errors", r["errors"])
    syn = hdl.synth(p, {"rca.v": SRC.replace("#1 ", "").replace("module rca #(parameter N = 4)", "module rca #(parameter N = 16)")}, "rca")
    p.metric("16-bit RCA after synthesis", syn["cells"], "cells", f"logic depth {syn['depth']}")
    p.metric("Average random-input delay, 32-bit", avg[-1], "gate delays", "longest carry chain is only ~log₂n on average")
    fig, ax = p.fig()
    ax.plot(widths, 2 * np.array(widths) - 1, "--", color=C_PRED, label="predicted worst case 2n−1")
    ax.plot(widths, worst, "o", color=C_MEAS, ms=8, label="measured worst case")
    ax.plot(widths, avg, "s-", color=COLORS[2], label="measured average (random inputs)")
    style_axes(ax, "adder width n (bits)", "delay (gate delays)", "Ripple-carry delay grows linearly with width")
    p.save(fig, "delay_vs_width", "Worst case is linear in n; typical random additions settle much sooner.")
    p.csv("delay", width=widths, worst=worst, average=avg, predicted=2 * np.array(widths) - 1)
    p.discuss("""The measured worst case matches 2n − 1 exactly. My first prediction used the textbook 2n + 1 and was
off by two gate delays for every width — the constant offset showed the error was in the bookkeeping of
the first stage (c₀ = 0 is constant, so bit 0 needs no XOR before its carry), not in the per-stage
cost. The gate-level simulation is event-accurate, so it is a sharp check that the analysis counts the
right path. The more interesting result is the
average: for random inputs the longest carry chain is only about log₂n bits, so typical additions
finish far sooner than the worst case. Synchronous designs cannot exploit that (the clock must cover the
worst case), which is why faster adder structures are needed.""")
