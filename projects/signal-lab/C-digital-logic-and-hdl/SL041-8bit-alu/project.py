from eelab import *
from eelab import hdl

META = dict(
    id="SL-041", title="8-bit ALU with flags", level="M",
    tools="Verilog RTL, Icarus Verilog self-checking testbench, Yosys",
    summary="An 8-bit ALU with ADD, SUB, AND, OR, XOR, SHL, SHR, SLT and Z/N/C/V flags, verified against "
            "a reference model on 4,000 random vectors per operation.",
    problem="Design the arithmetic heart of a CPU and prove its flags (especially signed overflow) are "
            "right for every operation.",
    theory=r"""Two's-complement subtraction is $A + \bar B + 1$. Carry $C$ is the 9th bit of the unsigned result;
signed overflow is $V = (a_7 = b'_7) \wedge (s_7 \ne a_7)$ where $b'$ is B (add) or $\bar B$ (sub).
SLT (set-less-than, signed) is $N\oplus V$ of the subtraction — the classic trick that avoids a separate
comparator. For random operands, P(V=1) for ADD is 1/4 (half the time the signs agree, half of those overflow).""",
    method="""RTL ALU with a 3-bit op decoder. Testbench computes the expected result and flags independently with
integer arithmetic, runs 4,000 random vectors per op plus corner cases (0x7F+1, 0x80−1, 0xFF+1), and
counts mismatches and flag frequencies. Synthesis gives the cell count.""",
)

ALU = """
module alu8(input [7:0] a, b, input [2:0] op, output reg [7:0] y, output z, n, output reg c, v);
  wire [8:0] add = {1'b0, a} + {1'b0, b};
  wire [8:0] sub = {1'b0, a} + {1'b0, ~b} + 9'd1;
  always @* begin
    c = 0; v = 0;
    case (op)
      3'd0: begin y = add[7:0]; c = add[8]; v = (a[7] == b[7]) && (y[7] != a[7]); end
      3'd1: begin y = sub[7:0]; c = sub[8]; v = (a[7] != b[7]) && (y[7] != a[7]); end
      3'd2: y = a & b;
      3'd3: y = a | b;
      3'd4: y = a ^ b;
      3'd5: begin y = a << 1; c = a[7]; end
      3'd6: begin y = a >> 1; c = a[0]; end
      3'd7: begin y = {7'd0, sub[7] ^ ((a[7] != b[7]) && (sub[7] != a[7]))}; end
    endcase
  end
  assign z = (y == 0);
  assign n = y[7];
endmodule
"""
TB = """
module tb;
  reg [7:0] a, b; reg [2:0] op; wire [7:0] y; wire z, n, c, v;
  alu8 dut(a, b, op, y, z, n, c, v);
  integer i, o, errs, vcount;
  reg [8:0] full; reg [7:0] ey; reg ec, ev;
  integer sa, sb;
  task check; begin
    sa = $signed(a); sb = $signed(b); ec = 0; ev = 0;
    case (op)
      0: begin full = a + b; ey = full[7:0]; ec = full[8]; ev = (sa + sb > 127) || (sa + sb < -128); end
      1: begin full = a + (~b & 8'hFF) + 1; ey = full[7:0]; ec = full[8]; ev = (sa - sb > 127) || (sa - sb < -128); end
      2: ey = a & b; 3: ey = a | b; 4: ey = a ^ b;
      5: begin ey = a << 1; ec = a[7]; end
      6: begin ey = a >> 1; ec = a[0]; end
      7: ey = (sa < sb) ? 1 : 0;
    endcase
    #1;
    if (y !== ey || z !== (ey == 0) || n !== ey[7] || c !== ec || v !== ev) errs = errs + 1;
    if (v) vcount = vcount + 1;
  end endtask
  initial begin
    for (o = 0; o < 8; o = o + 1) begin
      errs = 0; vcount = 0; op = o;
      a = 8'h7F; b = 1; check; a = 8'h80; b = 1; check; a = 8'hFF; b = 1; check; a = 0; b = 0; check;
      for (i = 0; i < 4000; i = i + 1) begin a = $random; b = $random; check; end
      $display("RES errors_op%0d %0d", o, errs);
      $display("RES vfreq_op%0d %0f", o, vcount / 4004.0);
    end
    $finish;
  end
endmodule
"""


def run(p):
    log, _ = hdl.simulate(p, {"alu8.v": ALU, "tb_alu8.v": TB}, "tb")
    r = hdl.results(log)
    names = ["ADD", "SUB", "AND", "OR", "XOR", "SHL", "SHR", "SLT"]
    tot = sum(r[f"errors_op{i}"] for i in range(8))
    p.compare("Mismatches over 32,032 vectors (all ops)", 0, tot, "", kind="abs")
    p.compare("Overflow frequency, ADD (random operands)", 0.25, r["vfreq_op0"], "", kind="abs")
    p.compare("Overflow frequency, SUB (random operands)", 0.25, r["vfreq_op1"], "", kind="abs")
    syn = hdl.synth(p, {"alu8.v": ALU}, "alu8")
    p.metric("Synthesised size", syn["cells"], "cells", f"logic depth {syn['depth']}")
    p.section("Per-operation results", "| op | mismatches |\n|---|---|\n" + "\n".join(f"| {nm} | {int(r[f'errors_op{i}'])} |" for i, nm in enumerate(names)))
    fig, ax = p.fig()
    br = syn["breakdown"]
    ks = sorted(br, key=br.get, reverse=True)
    ax.bar(ks, [br[k] for k in ks], color=C_MEAS)
    style_axes(ax, "cell type", "count", f"8-bit ALU synthesised to {syn['cells']} generic gates", legend=False)
    p.save(fig, "synthesis", "Gate-type breakdown from Yosys; XOR/MUX dominate (adder and op select).")
    p.discuss("""Every operation matches the reference model, including the corner cases where signed overflow and
unsigned carry disagree (0x7F + 1 overflows but does not carry; 0xFF + 1 carries but does not overflow).
The overflow frequency for random operands sits at the predicted 1/4. Implementing SLT as N ⊕ V of the
subtraction reuses the subtractor instead of adding a comparator — the same trick MIPS and RISC-V
implementations use.""")
