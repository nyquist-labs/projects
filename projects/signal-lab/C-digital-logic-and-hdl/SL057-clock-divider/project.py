from eelab import *
from eelab import hdl

META = dict(
    id="SL-057", title="Clock divider and prescaler (including odd 50 % duty)", level="E",
    tools="Verilog RTL, Icarus Verilog, VCD frequency/duty measurement",
    summary="Divide a 100 MHz clock by 2, 3, 5, 10 and 1000 with exact 50 % duty — including odd ratios "
            "that need both clock edges — and measure frequency and duty from the waveform.",
    problem="Dividing by an even number is easy. How do you divide by 3 or 5 and still get a 50 % duty "
            "cycle, and what does it cost?",
    theory=r"""Even N: toggle every N/2 input cycles → $f/N$, 50 % duty. Odd N with a single edge gives duty
$\lfloor N/2\rfloor/N$ (33 % for N = 3). ORing a rising-edge and a falling-edge version of the same
counter output (shifted by half an input period) gives $\frac{(N-1)/2 + 1/2}{N}=50\,\%$ exactly.""",
    method="""Parameterised divider module with an odd/even generate branch. Input clock 100 MHz (10 ns). Python measures
each output's period and high time from the VCD.""",
)

SRC = """
module clkdiv #(parameter N = 3)(input clk, rst, output out);
  generate if (N % 2 == 0) begin : even
    reg [15:0] c; reg o;
    always @(posedge clk) if (rst) begin c <= 0; o <= 0; end
      else if (c == N/2 - 1) begin c <= 0; o <= ~o; end else c <= c + 1;
    assign out = o;
  end else begin : odd
    reg [15:0] c; reg p, n;
    always @(posedge clk) if (rst) c <= 0; else c <= (c == N - 1) ? 0 : c + 1;
    always @(posedge clk) if (rst) p <= 0; else p <= (c < (N - 1) / 2);
    always @(negedge clk) if (rst) n <= 0; else n <= p;
    assign out = p | n;
  end endgenerate
endmodule
"""
TB = """
`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1; wire o2, o3, o5, o10, o1000;
  clkdiv #(2) d2(clk, rst, o2); clkdiv #(3) d3(clk, rst, o3); clkdiv #(5) d5(clk, rst, o5);
  clkdiv #(10) d10(clk, rst, o10); clkdiv #(1000) d1000(clk, rst, o1000);
  always #5 clk = ~clk;
  initial begin $dumpfile("div.vcd"); $dumpvars(0, tb.o2, tb.o3, tb.o5, tb.o10, tb.o1000, tb.clk); #52 rst = 0; #60000 $finish; end
endmodule
"""


def run(p):
    log, vcd = hdl.simulate(p, {"clkdiv.v": SRC, "tb_clkdiv.v": TB}, "tb")
    fig, ax = p.fig(h=3.6)
    for N in (2, 3, 5, 10, 1000):
        ts, vs = vcd[f"tb.o{N}"]
        ts = np.array(ts) * 1e-3
        vs = [0 if v is None else v for v in vs]
        rises = np.array([t for t, a, b in zip(ts[1:], vs[:-1], vs[1:]) if b == 1 and a == 0])
        falls = np.array([t for t, a, b in zip(ts[1:], vs[:-1], vs[1:]) if b == 0 and a == 1])
        per = np.median(np.diff(rises))
        hi = np.median([f - r for r in rises for f in falls[falls > r][:1]])
        p.compare(f"÷{N}: output frequency", 100e6 / N, 1e9 / per, "Hz", tol=0.01)
        p.compare(f"÷{N}: duty cycle", 50, hi / per * 100, "%", kind="abs")
    vcdn = {k: (list(np.array(v[0]) * 1e-3), v[1]) for k, v in vcd.items()}
    hdl.waveform_plot(ax, vcdn, [("tb.clk", "clk 100 MHz"), ("tb.o2", "÷2"), ("tb.o3", "÷3"), ("tb.o5", "÷5"), ("tb.o10", "÷10")], 100, 260)
    ax.set_title("Odd dividers use both clock edges to reach 50 % duty", loc="left")
    p.save(fig, "timing", "÷3 and ÷5 outputs are the OR of a rising-edge and a falling-edge register.")
    p.discuss("""All ratios hit their frequency exactly and all duty cycles are 50 %, including ÷3 and ÷5 which a
single-edge counter can only make 33 % and 40 %. The cost of the odd-N trick is that the output depends
on the *falling* edge too, so its duty accuracy depends on the input clock's own duty cycle, and the OR
gate creates a combinational clock — acceptable for driving an external pin, but on an FPGA you would use
a PLL/MMCM or a clock-enable instead of routing a logic-generated clock.""")
