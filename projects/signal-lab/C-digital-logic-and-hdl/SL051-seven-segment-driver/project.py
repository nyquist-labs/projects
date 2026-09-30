from eelab import *
from eelab import hdl

META = dict(
    id="SL-051", title="Multiplexed 7-segment display driver", level="E",
    tools="Verilog RTL (hex decoder + 4-digit time multiplexing), Icarus Verilog",
    summary="Decode 16 hex digits to segments and time-multiplex four digits; verify the decode table "
            "exhaustively and measure refresh rate and per-digit duty.",
    problem="Drive four 7-segment digits with only 7 segment lines + 4 digit enables, fast enough that the "
            "eye sees them all lit.",
    theory=r"""Each digit is enabled for $2^{K}$ clocks in turn, so the refresh rate is $f_{clk}/(4\cdot2^K)$ and each digit
is on for 25 % of the time (brightness ∝ duty). With 50 MHz and K = 16: 190.7 Hz refresh — above the
~60 Hz flicker-fusion threshold. The decoder is a 16-entry truth table (active-low segments a–g).""",
    method="""Testbench checks all 16 codes against a reference table, then displays 0x2B7F and samples which digit is
enabled and what segments are shown over 20 ms. (For simulation speed K = 10 is used and the time axis is
scaled; the refresh prediction uses the same K.)""",
)

SEG = """
module hex7(input [3:0] h, output reg [6:0] seg);  // {g,f,e,d,c,b,a}, active high
  always @* case (h)
    4'h0: seg = 7'b0111111; 4'h1: seg = 7'b0000110; 4'h2: seg = 7'b1011011; 4'h3: seg = 7'b1001111;
    4'h4: seg = 7'b1100110; 4'h5: seg = 7'b1101101; 4'h6: seg = 7'b1111101; 4'h7: seg = 7'b0000111;
    4'h8: seg = 7'b1111111; 4'h9: seg = 7'b1101111; 4'hA: seg = 7'b1110111; 4'hB: seg = 7'b1111100;
    4'hC: seg = 7'b0111001; 4'hD: seg = 7'b1011110; 4'hE: seg = 7'b1111001; 4'hF: seg = 7'b1110001;
  endcase
endmodule
module mux7 #(parameter K = 16)(input clk, rst, input [15:0] val, output [6:0] seg, output reg [3:0] an);
  reg [K+1:0] cnt; wire [1:0] sel = cnt[K+1:K];
  always @(posedge clk) if (rst) cnt <= 0; else cnt <= cnt + 1;
  always @* an = 4'b0001 << sel;
  hex7 d(val[sel*4 +: 4], seg);
endmodule
"""
TB = """
`timescale 1ns/1ps
module tb;
  reg [3:0] h; wire [6:0] s; hex7 dec(h, s);
  reg clk = 0, rst = 1; wire [6:0] seg; wire [3:0] an;
  mux7 #(10) m(clk, rst, 16'h2B7F, seg, an);
  always #10 clk = ~clk;
  integer i;
  initial begin
    for (i = 0; i < 16; i = i + 1) begin h = i; #1; $display("DEC %0d %0d", i, s); end
    $dumpfile("seg.vcd"); $dumpvars(0, tb.an, tb.seg);
    #100 rst = 0;
    #(20 * 4096 * 5) $finish;
  end
endmodule
"""
REF = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F, 0x77, 0x7C, 0x39, 0x5E, 0x79, 0x71]


def run(p):
    log, vcd = hdl.simulate(p, {"seg7.v": SEG, "tb_seg7.v": TB}, "tb")
    dec = {int(a): int(b) for a, b in (l.split()[1:] for l in log.splitlines() if l.startswith("DEC"))}
    errs = sum(dec[i] != REF[i] for i in range(16))
    p.compare("Decoder mismatches (16 hex digits)", 0, errs, "", kind="abs")
    at, av = vcd["tb.an"]; at = np.array(at) * 1e-3
    K = 10
    one = [t for t, v in zip(at, av) if v == 1]
    per = np.median(np.diff(one))
    p.compare("Refresh rate (K = 10, simulation)", 50e6 / (4 * 2**K), 1e9 / per, "Hz", tol=0.1)
    p.metric("Refresh rate with K = 16 (hardware setting)", 50e6 / (4 * 2**16), "Hz", "> 60 Hz flicker threshold")
    dur = {}
    for i in range(len(at) - 1):
        dur[av[i]] = dur.get(av[i], 0) + at[i + 1] - at[i]
    tot = sum(v for k, v in dur.items() if k in (1, 2, 4, 8))
    p.compare("Per-digit on-time fraction", 25, dur.get(1, 0) / tot * 100, "%", kind="abs")
    st, sv = vcd["tb.seg"]; st = np.array(st) * 1e-3
    shown = {}
    for t, v in zip(st, sv):
        a = av[np.searchsorted(at, t, side="right") - 1]
        shown[a] = v
    digits = {1: 0xF, 2: 0x7, 4: 0xB, 8: 0x2}
    ok = all(shown.get(k) == REF[d] for k, d in digits.items())
    p.compare("Digits shown for 0x2B7F correct", 1, int(ok), "", kind="abs")
    fig, axs = p.fig(2, 8, w=10, h=3.2)
    segs = {"a": [(0.2, 0.9), (0.8, 0.9)], "b": [(0.8, 0.9), (0.8, 0.5)], "c": [(0.8, 0.5), (0.8, 0.1)],
            "d": [(0.2, 0.1), (0.8, 0.1)], "e": [(0.2, 0.1), (0.2, 0.5)], "f": [(0.2, 0.5), (0.2, 0.9)], "g": [(0.2, 0.5), (0.8, 0.5)]}
    for i, ax in enumerate(np.array(axs).ravel()):
        code = dec[i]
        for j, nm in enumerate("abcdefg"):
            on = (code >> j) & 1
            (x0, y0), (x1, y1) = segs[nm]
            ax.plot([x0, x1], [y0, y1], lw=5, color=C_MEAS if on else "#e4e3df", solid_capstyle="round")
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_title(f"{i:X}", fontsize=9)
    p.save(fig, "decoder", "All 16 decoder outputs rendered from the simulated segment codes.")
    p.discuss("""The decoder matches the reference table for every hex digit and the multiplexer cycles through the four
anodes with exactly 25 % duty each. The scaled simulation (K = 10) runs at 12.2 kHz refresh; the same
counter with K = 16 gives 190.7 Hz in hardware — fast enough to avoid flicker while slow enough that the
digit drivers' switching losses and ghosting stay small.""")
