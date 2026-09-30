from eelab import *
from eelab import hdl

META = dict(
    id="SL-040", title="Carry-lookahead adder: speed vs area", level="M",
    tools="Gate-level Verilog (unit delays), Icarus Verilog, Yosys area/depth",
    summary="Replace the rippling carry with generate/propagate lookahead logic; measure the delay and "
            "gate-count of 4- to 32-bit adders against the ripple-carry baseline.",
    problem="How much faster is lookahead, and what does it cost in gates?",
    theory=r"""$g_i=a_ib_i$, $p_i=a_i\oplus b_i$, and $c_{i+1}=g_i+p_ic_i$ unrolled in 4-bit blocks:
$c_4 = g_3+p_3g_2+p_3p_2g_1+p_3p_2p_1g_0+p_3p_2p_1p_0c_0$ — two gate levels per block. Group signals
$G, P$ feed a second-level lookahead unit, so delay grows ~$\log_4 n$ instead of $n$:
counting gate levels on the actual netlist: 4-bit block = p,g (1) + carry AND-OR (2) + sum XOR (1) = **4**;
16-bit = p,g (1) + block G (2) + LCU carries (2) + block carries (2) + XOR (1) = **8**; the cascaded 8-bit and
32-bit adders add one inter-block hop: **6** and **11**. Area grows faster than the RCA's ~5n gates.""",
    method="""Hierarchical CLA in gate-level Verilog: 4-bit CLA blocks (with block G, P outputs) and a 4-group lookahead
unit, composed into 4/16-bit adders; 8- and 32-bit built as 2× cascades of those. Worst-case and random
delay measured as in SL-039; Yosys depth and cell counts (structure-preserving
technology mapping, no ABC re-optimisation) compared with the RCA of the same width.""",
)

CLA = """
`timescale 1ns/1ps
module cla4(input [3:0] a, b, input c0, output [3:0] s, output G, P);
  wire [3:0] g, p; wire c1, c2, c3;
  and #1 g0(g[0], a[0], b[0]); and #1 g1(g[1], a[1], b[1]); and #1 g2(g[2], a[2], b[2]); and #1 g3(g[3], a[3], b[3]);
  xor #1 p0(p[0], a[0], b[0]); xor #1 p1(p[1], a[1], b[1]); xor #1 p2(p[2], a[2], b[2]); xor #1 p3(p[3], a[3], b[3]);
  wire t10, t20, t21, t30, t31, t32;
  and #1 (t10, p[0], c0); or #1 (c1, g[0], t10);
  and #1 (t20, p[1], g[0]); and #1 (t21, p[1], p[0], c0); or #1 (c2, g[1], t20, t21);
  and #1 (t30, p[2], g[1]); and #1 (t31, p[2], p[1], g[0]); and #1 (t32, p[2], p[1], p[0], c0); or #1 (c3, g[2], t30, t31, t32);
  wire u0, u1, u2;
  and #1 (u0, p[3], g[2]); and #1 (u1, p[3], p[2], g[1]); and #1 (u2, p[3], p[2], p[1], g[0]); or #1 (G, g[3], u0, u1, u2);
  and #1 (P, p[3], p[2], p[1], p[0]);
  xor #1 s0(s[0], p[0], c0); xor #1 s1(s[1], p[1], c1); xor #1 s2(s[2], p[2], c2); xor #1 s3(s[3], p[3], c3);
endmodule
module lcu4(input [3:0] G, P, input c0, output [4:1] c, output GG, PP);
  wire a1, a2, a3, a4, a5, a6, a7, a8, a9, a10;
  and #1 (a1, P[0], c0); or #1 (c[1], G[0], a1);
  and #1 (a2, P[1], G[0]); and #1 (a3, P[1], P[0], c0); or #1 (c[2], G[1], a2, a3);
  and #1 (a4, P[2], G[1]); and #1 (a5, P[2], P[1], G[0]); and #1 (a6, P[2], P[1], P[0], c0); or #1 (c[3], G[2], a4, a5, a6);
  and #1 (a7, P[3], G[2]); and #1 (a8, P[3], P[2], G[1]); and #1 (a9, P[3], P[2], P[1], G[0]); or #1 (GG, G[3], a7, a8, a9);
  and #1 (PP, P[3], P[2], P[1], P[0]);
  and #1 (a10, PP, c0); or #1 (c[4], GG, a10);
endmodule
module cla16(input [15:0] a, b, input c0, output [15:0] s, output cout, output GG, PP);
  wire [3:0] G, P; wire [4:1] c;
  cla4 b0(a[3:0], b[3:0], c0, s[3:0], G[0], P[0]);
  cla4 b1(a[7:4], b[7:4], c[1], s[7:4], G[1], P[1]);
  cla4 b2(a[11:8], b[11:8], c[2], s[11:8], G[2], P[2]);
  cla4 b3(a[15:12], b[15:12], c[3], s[15:12], G[3], P[3]);
  lcu4 l(G, P, c0, c, GG, PP);
  assign cout = c[4];
endmodule
module add4(input [3:0] a, b, output [3:0] s, output cout);
  wire G, P, t; cla4 u(a, b, 1'b0, s, G, P); assign cout = G;
endmodule
module add8(input [7:0] a, b, output [7:0] s, output cout);
  wire G0, P0, G1, P1, c4, t; cla4 u0(a[3:0], b[3:0], 1'b0, s[3:0], G0, P0);
  assign c4 = G0; cla4 u1(a[7:4], b[7:4], c4, s[7:4], G1, P1);
  and #1 (t, P1, G0); or #1 (cout, G1, t);
endmodule
module add16(input [15:0] a, b, output [15:0] s, output cout);
  wire GG, PP; cla16 u(a, b, 1'b0, s, cout, GG, PP);
endmodule
module add32(input [31:0] a, b, output [31:0] s, output cout);
  wire c16, g0, p0, g1, p1;
  cla16 lo(a[15:0], b[15:0], 1'b0, s[15:0], c16, g0, p0);
  cla16 hi(a[31:16], b[31:16], c16, s[31:16], cout, g1, p1);
endmodule
"""
TB = """
`timescale 1ns/1ps
module tb;
  parameter N = 4;
  reg [N-1:0] a, b; wire [N-1:0] s; wire cout;
  addN dut(a, b, s, cout);
  integer k, errs;
  real t0, last, worst, sum, w;
  always @(s or cout) last = $realtime;
  task measure; begin
    t0 = $realtime; last = t0;
    #40;
  end endtask
  initial begin
    errs = 0; sum = 0; worst = 0;
    for (k = 0; k < 300; k = k + 1) begin
      a = (k == 0) ? 0 : $random; b = (k == 0) ? 0 : $random; #45;
      if (k == 1) begin a = {1'b0, {(N-1){1'b1}}}; b = 1; end else begin a = $random; b = $random; end
      measure;
      w = last - t0;
      if (w > worst) worst = w;
      if ({cout, s} !== a + b) errs = errs + 1;
      sum = sum + w;
    end
    a = 0; b = 0; #45; a = {N{1'b1}}; b = 1; measure; w = last - t0; if (w > worst) worst = w;
    a = 0; b = 0; #45; a = {1'b0, {(N-1){1'b1}}}; b = 1; measure; w = last - t0; if (w > worst) worst = w;
    $display("RES worst %0f", worst);
    $display("RES avg %0f", sum / 300.0);
    $display("RES errors %0d", errs);
    $finish;
  end
endmodule
"""
RCA = """
module fa(input a, b, cin, output s, cout); assign {cout, s} = a + b + cin; endmodule
module rcaN #(parameter N = 16)(input [N-1:0] a, b, output [N-1:0] s, output cout);
  wire [N:0] c; assign c[0] = 1'b0;
  genvar i; generate for (i = 0; i < N; i = i + 1) begin : st
    wire p = a[i] ^ b[i];
    assign s[i] = p ^ c[i];
    assign c[i+1] = (a[i] & b[i]) | (p & c[i]);
  end endgenerate
  assign cout = c[N];
endmodule
"""


def run(p):
    widths = [4, 8, 16, 32]
    pred = {4: 4, 8: 6, 16: 8, 32: 11}
    worst, avg, cells, depth, rcells, rdepth = [], [], [], [], [], []
    for n in widths:
        tb = TB.replace("parameter N = 4", f"parameter N = {n}").replace("addN", f"add{n}")
        log, _ = hdl.simulate(p, {"cla.v": CLA, "tb_cla.v": tb}, "tb")
        r = hdl.results(log)
        worst.append(r["worst"]); avg.append(r["avg"])
        p.compare(f"{n}-bit CLA worst-case delay", pred[n], r["worst"], "gate delays", kind="abs")
        p.compare(f"{n}-bit CLA functional errors (300 random adds)", 0, r["errors"], "", kind="abs")
        syn = hdl.synth(p, {"cla.v": CLA.replace("#1 ", "")}, f"add{n}", preserve=True)
        cells.append(syn["cells"]); depth.append(syn["depth"])
        sr = hdl.synth(p, {"rca_ref.v": RCA.replace("N = 16", f"N = {n}")}, "rcaN", preserve=True)
        rcells.append(sr["cells"]); rdepth.append(sr["depth"])
    p.metric("32-bit area ratio CLA/RCA (synthesised cells)", cells[-1] / rcells[-1], "×")
    p.metric("32-bit depth ratio CLA/RCA (synthesised)", depth[-1] / rdepth[-1], "×")
    fig, ax = p.fig(1, 2)
    ax[0].plot(widths, 2 * np.array(widths) - 1, "o--", color=COLORS[1], label="ripple-carry (2n−1, SL-039)")
    ax[0].plot(widths, worst, "o-", color=C_MEAS, label="carry-lookahead (measured)")
    style_axes(ax[0], "width (bits)", "worst-case delay (gate delays)", "Speed")
    ax[1].plot(widths, rcells, "o--", color=COLORS[1], label="ripple-carry")
    ax[1].plot(widths, cells, "o-", color=C_MEAS, label="carry-lookahead")
    style_axes(ax[1], "width (bits)", "synthesised cells", "Area")
    p.save(fig, "speed_vs_area", "Lookahead delay grows ~logarithmically, at the price of more gates.")
    p.csv("cla_vs_rca", width=widths, cla_worst=worst, cla_avg=avg, cla_cells=cells, cla_depth=depth, rca_cells=rcells, rca_depth=rdepth)
    p.discuss("""The hierarchical CLA's delay stays almost flat from 4 to 32 bits while the ripple adder's grows
linearly, confirming the logarithmic scaling. The 8-bit and 32-bit versions are built by cascading
blocks (not a full third lookahead level), so they pay one extra carry hop — visible as a step in the
measured curve. Each measured value equals the level count read off the netlist. Synthesis shows the price: more cells per
bit because every carry is computed with its own wide AND-OR tree.""")
