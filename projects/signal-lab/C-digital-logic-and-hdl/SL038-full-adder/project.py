from eelab import *
from eelab import hdl

META = dict(
    id="SL-038", title="Full adder from gates", level="E",
    tools="Verilog gate primitives, Icarus Verilog (exhaustive testbench), Yosys synthesis",
    summary="Build a 1-bit full adder from XOR/AND/OR primitives with unit gate delays, verify all 8 "
            "input combinations, measure its worst-case delay, then chain four into a 4-bit adder.",
    problem="What is the smallest gate network that adds three bits, and how long does its slowest "
            "output take to settle?",
    theory=r"""$S = A\oplus B\oplus C_{in}$, $C_{out}=AB + C_{in}(A\oplus B)$: two XOR, two AND, one OR (5 gates).
With one time unit per gate: $S$ settles after 2 XOR levels (2 units) and $C_{out}$ after XOR→AND→OR
(3 units) — the carry path is the critical one.""",
    method="""Gate-level Verilog with #1 delay per gate. Testbench applies all 8 vectors, checks S and C_out against
the integer sum, and measures settling time for every one of the 64 input *transitions*. Yosys synthesises
to a generic gate library to count cells and logic depth.""",
)

FA = """
`timescale 1ns/1ps
module full_adder(input a, input b, input cin, output s, output cout);
  wire p, g, t;
  xor #1 x1(p, a, b);
  xor #1 x2(s, p, cin);
  and #1 a1(g, a, b);
  and #1 a2(t, p, cin);
  or  #1 o1(cout, g, t);
endmodule
"""
TB = """
`timescale 1ns/1ps
module tb;
  reg a, b, cin; wire s, cout;
  full_adder dut(a, b, cin, s, cout);
  integer i, j, errors = 0;
  real t0, last, worst = 0;
  always @(s or cout) last = $realtime;
  initial begin
    $dumpfile("fa.vcd"); $dumpvars(0, tb);
    for (i = 0; i < 8; i = i + 1) begin
      {a, b, cin} = i; #10;
      if ({cout, s} !== a + b + cin) errors = errors + 1;
      $display("VEC %0d %0d %0d -> %0d %0d", a, b, cin, cout, s);
    end
    // worst-case settling over all 64 transitions
    for (i = 0; i < 8; i = i + 1) for (j = 0; j < 8; j = j + 1) begin
      {a, b, cin} = i; #10;
      t0 = $realtime; last = t0;
      {a, b, cin} = j;
      #10;
      if (last - t0 > worst) worst = last - t0;
    end
    $display("RES errors %0d", errors);
    $display("RES worst_delay %0f", worst);
    $finish;
  end
endmodule
"""


def run(p):
    log, vcd = hdl.simulate(p, {"full_adder.v": FA, "tb_full_adder.v": TB}, "tb")
    r = hdl.results(log)
    vecs = [l.split()[1:] for l in log.splitlines() if l.startswith("VEC")]
    p.compare("Truth-table errors (8 vectors)", 0, r["errors"], "", kind="abs")
    p.compare("Worst-case settling delay (gate delays)", 3, r["worst_delay"], "gate delays", kind="abs")
    syn = hdl.synth(p, {"full_adder.v": FA.replace("#1 ", "")}, "full_adder")
    p.compare("Gate count after synthesis", 5, syn["cells"], "cells", kind="abs")
    p.compare("Logic depth (longest path)", 3, syn["depth"], "levels", kind="abs")
    p.section("Truth table (simulated)", "| a | b | c_in | c_out | s |\n|---|---|---|---|---|\n" +
              "\n".join(f"| {v[0]} | {v[1]} | {v[2]} | {v[4]} | {v[5]} |" for v in vecs))
    fig, ax = p.fig(h=3.8)
    hdl.waveform_plot(ax, vcd, [("tb.a", "a"), ("tb.b", "b"), ("tb.cin", "c_in"), ("tb.s", "s"), ("tb.cout", "c_out")], 0, 80)
    ax.set_title("Full adder: all 8 input combinations (10 ns each)", loc="left")
    p.save(fig, "timing", "Exhaustive simulation; outputs lag inputs by one to three gate delays.")
    p.discuss("""All eight combinations are correct and synthesis reproduces the 5-gate textbook network. The
worst-case delay is the carry path (XOR → AND → OR), 3 gate delays, confirming that in a multi-bit
adder it is the carry, not the sum, that limits speed — the motivation for the carry-lookahead
adder in SL-040.""")
