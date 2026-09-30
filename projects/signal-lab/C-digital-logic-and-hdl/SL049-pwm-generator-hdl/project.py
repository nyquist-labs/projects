from eelab import *
from eelab import hdl

META = dict(
    id="SL-049", title="Parameterised PWM generator", level="E",
    tools="Verilog RTL, Icarus Verilog, VCD duty-cycle measurement",
    summary="A counter-compare PWM with N-bit resolution: verify frequency f_clk/2ᴺ and duty = compare/2ᴺ "
            "for a sweep of compare values, and glitch-free updates at period boundaries.",
    problem="Generate an exact duty cycle in hardware, and make sure changing the duty mid-period never "
            "produces a runt pulse.",
    theory=r"""Free-running N-bit counter; output high while count < CMP. Frequency $f_{clk}/2^N$; duty exactly
$CMP/2^N$, resolution $1/2^N$ (8 bits → 0.39 %). The compare register is double-buffered and loaded only when
the counter wraps, so a new duty takes effect on the next full period.""",
    method="""8-bit PWM at 50 MHz clock (195.3 kHz PWM). Testbench steps CMP through 0, 1, 32, 64, 128, 200, 255, 256 (100 %),
changing CMP at random times. Python measures high time/period for each settled period and flags any
period shorter than 2⁸ clocks.""",
)

PWM = """
module pwm #(parameter N = 8)(input clk, rst, input [N:0] cmp_in, output reg out);
  reg [N-1:0] cnt; reg [N:0] cmp;
  always @(posedge clk) begin
    if (rst) begin cnt <= 0; cmp <= 0; out <= 0; end
    else begin
      cnt <= cnt + 1;
      if (cnt == {N{1'b1}}) cmp <= cmp_in;     // double-buffered update at wrap
      out <= ({1'b0, cnt + 1'b1} < ((cnt == {N{1'b1}}) ? cmp_in : cmp));
    end
  end
endmodule
"""
TB = """
`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1; reg [8:0] cmp = 0; wire out;
  pwm #(8) dut(clk, rst, cmp, out);
  always #10 clk = ~clk;
  integer i; integer vals [0:7];
  initial begin
    $dumpfile("pwm.vcd"); $dumpvars(0, tb.out, tb.cmp);
    vals[0] = 0; vals[1] = 1; vals[2] = 32; vals[3] = 64; vals[4] = 128; vals[5] = 200; vals[6] = 255; vals[7] = 256;
    #100 rst = 0;
    for (i = 0; i < 8; i = i + 1) begin
      #(20 * 256 * 4 + ($random & 1023)); cmp = vals[i];
    end
    #(20 * 256 * 5) $finish;
  end
endmodule
"""


def run(p):
    log, vcd = hdl.simulate(p, {"pwm.v": PWM, "tb_pwm.v": TB}, "tb")
    ot, ov = vcd["tb.out"]; ot = np.array(ot) * 1e-3
    ct, cv = vcd["tb.cmp"]; ct = np.array(ct) * 1e-3
    T = 256 * 20.0
    rises = [t for t, v in zip(ot, ov) if v == 1]
    falls = [t for t, v in zip(ot, ov) if v == 0]
    res = []
    for c, tc in zip(cv, ct):
        if c in (0, 256) or tc < 50:
            continue
        rs = [r for r in rises if r > tc + 2 * T][:2]
        if len(rs) < 2:
            continue
        per = rs[1] - rs[0]
        fl = [f for f in falls if f > rs[0]][0]
        res.append((c, (fl - rs[0]) / per, per))
        p.compare(f"Duty at CMP = {c}", c / 256 * 100, (fl - rs[0]) / per * 100, "%", kind="abs")
    p.compare("PWM frequency", 50e6 / 256, 1e9 / np.median([r[2] for r in res]), "Hz", tol=0.1)
    hi = np.diff(ot)
    periods = np.diff(rises)
    runts = int(np.sum(periods < T - 1))
    p.compare("Runt periods (shorter than 256 clocks)", 0, runts, "", kind="abs")
    fig, ax = p.fig(h=3.3)
    vcdn = {"out": (list(ot / 1e3), ov), "cmp": (list(ct / 1e3), cv)}
    hdl.waveform_plot(ax, vcdn, [("cmp", "CMP"), ("out", "PWM out")], 0, ot[-1] / 1e3, unit="µs")
    ax.set_title("Duty follows CMP; updates take effect at the next period", loc="left")
    p.save(fig, "timing", "CMP steps 0 → 256 (0 % → 100 %).")
    p.discuss("""Every duty cycle equals CMP/256 exactly — a digital PWM has no analog error, only quantisation. The
double-buffered compare register means a CMP change in mid-period never truncates a pulse: there are no
periods shorter than 256 clocks. The 9-bit CMP input makes 100 % duty reachable (CMP = 256), a detail
that an N-bit compare register would miss.""")
