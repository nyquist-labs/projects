from eelab import *
from eelab import hdl

META = dict(
    id="SL-052", title="Binary-to-BCD (double-dabble) in hardware", level="M",
    tools="Verilog (combinational shift-add-3 network), Icarus Verilog exhaustive test, Yosys",
    summary="Convert 8-, 10- and 12-bit binary to packed BCD with the shift-and-add-3 algorithm, verify "
            "every input exhaustively and measure how the hardware grows with width.",
    problem="Displays want decimal digits, logic produces binary. Convert without a divider.",
    theory=r"""Double dabble shifts the binary number left into a BCD register n times; before each shift any BCD digit
≥ 5 gets +3 (so that after doubling it overflows correctly into the next digit). Unrolled, an n-bit input
needs about $\sum$ (digits active at each step) "add-3" cells — roughly $n^2/8$ for n up to 16:
7 cells for 8 bits, 13 for 10 bits, 21 for 12 bits (counting only cells whose digit can reach ≥ 5).""",
    method="""Unrolled combinational Verilog with a generic loop (the synthesiser removes cells that can never
trigger). Testbench checks all 2ⁿ inputs against integer division/modulo. Yosys (with ABC) reports gate
count and depth for each width.""",
)

SRC = """
module dd #(parameter N = 8, D = 3)(input [N-1:0] bin, output reg [4*D-1:0] bcd);
  integer i, j;
  reg [4*D+N-1:0] s;
  always @* begin
    s = 0; s[N-1:0] = bin;
    for (i = 0; i < N; i = i + 1) begin
      for (j = 0; j < D; j = j + 1)
        if (s[N + 4*j +: 4] >= 5) s[N + 4*j +: 4] = s[N + 4*j +: 4] + 3;
      s = s << 1;
    end
    bcd = s[4*D+N-1:N];
  end
endmodule
"""
TB = """
module tb;
  parameter N = 8, D = 3;
  reg [N-1:0] b; wire [4*D-1:0] q; integer i, errs = 0, v, k, dec;
  dd #(N, D) u(b, q);
  initial begin
    for (i = 0; i < (1 << N); i = i + 1) begin
      b = i; #1;
      v = i; dec = 0;
      for (k = 0; k < D; k = k + 1) begin dec = dec | ((v % 10) << (4*k)); v = v / 10; end
      if (q !== dec) errs = errs + 1;
    end
    $display("RES errors %0d", errs);
    $finish;
  end
endmodule
"""


def run(p):
    rows = []
    for N, Dg, cells_pred in ((8, 3, 7), (10, 4, 13), (12, 4, 21)):
        tb = TB.replace("parameter N = 8, D = 3", f"parameter N = {N}, D = {Dg}")
        log, _ = hdl.simulate(p, {"double_dabble.v": SRC, "tb_double_dabble.v": tb}, "tb")
        r = hdl.results(log)
        p.compare(f"{N}-bit: conversion errors over all {2**N} inputs", 0, r["errors"], "", kind="abs")
        syn = hdl.synth(p, {"dd.v": SRC.replace("parameter N = 8, D = 3", f"parameter N = {N}, D = {Dg}")}, "dd")
        rows.append((N, syn["cells"], syn["depth"], cells_pred))
        p.metric(f"{N}-bit synthesised", syn["cells"], "gates", f"depth {syn['depth']}")
    N_, cells, depth, cp = map(np.array, zip(*rows))
    k = cells / cp
    p.compare("Gates per add-3 cell, 8 → 12 bit (should be constant)", k[0], k[-1], "", tol=25)
    fig, ax = p.fig()
    ax.plot(N_, cells, "o-", color=C_MEAS, label="synthesised gates")
    ax.plot(N_, cp * k[0], "--", color=C_PRED, label="add-3 cell count × gates/cell")
    style_axes(ax, "input width (bits)", "gates", "Double-dabble hardware grows ~quadratically")
    p.save(fig, "area", "Gate count tracks the number of add-3 cells in the unrolled network.")
    p.csv("area", width=N_, gates=cells, depth=depth, add3_cells=cp)
    p.discuss("""All inputs convert correctly at every width. The gate count scales with the number of add-3 cells,
which grows roughly quadratically because each extra input bit adds a shift stage *and* eventually a new
decimal digit to correct. For wide numbers a sequential (one shift per clock) version trades this area
for n clock cycles of latency.""")
