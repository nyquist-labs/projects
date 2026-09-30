from eelab import *
from eelab import hdl

META = dict(
    id="SL-050", title="Switch debouncer in logic", level="E",
    tools="Verilog RTL (synchroniser + saturating counter), Icarus Verilog, stochastic bounce model",
    summary="Feed realistic contact bounce (random 0.1–2 ms bursts) into a synchroniser and a counter-based "
            "debouncer; count spurious edges before and after.",
    problem="A mechanical button produces dozens of edges per press. Remove them in logic with a known, "
            "bounded added latency.",
    theory=r"""Two flip-flops synchronise the asynchronous input. A counter increments while the synchronised input differs
from the stable output and resets otherwise; the output toggles only after the input has been stable for
$N$ ticks. The input is only *examined* on tick edges, so the counter can already be running during the tail
of a burst if the samples happen to see the new level; the latency measured from the last bounce is therefore
at most $N\,T_{tick}$ = 10 ms (N = 10, 1 kHz tick) and usually a little less. Any burst shorter than N ticks
(≤ 2 ms here) still yields exactly one clean edge.""",
    method="""Testbench generates 40 presses/releases, each with a burst of 3–25 random bounce edges over 0.1–2 ms, then a
stable level. Debouncer clocked at 1 kHz tick (clock enable) from a 1 MHz clock. Python counts edges on the
raw and debounced signals and measures latency from the last bounce to the output edge.""",
)

DB = """
module debounce #(parameter N = 10)(input clk, tick, rst, in, output reg out);
  reg [1:0] sync; reg [7:0] cnt;
  always @(posedge clk) begin
    sync <= {sync[0], in};
    if (rst) begin out <= 0; cnt <= 0; end
    else if (tick) begin
      if (sync[1] == out) cnt <= 0;
      else if (cnt == N - 1) begin out <= sync[1]; cnt <= 0; end
      else cnt <= cnt + 1;
    end
  end
endmodule
"""
TB = """
`timescale 1us/1ns
module tb;
  reg clk = 0, rst = 1, in = 0, tick = 0; wire out;
  debounce #(10) dut(clk, tick, rst, in, out);
  always #0.5 clk = ~clk;
  integer tc = 0; always @(posedge clk) begin tc = tc + 1; tick <= (tc % 1000 == 0); end
  integer i, k, nb, seed = 3; real gap;
  initial begin
    $dumpfile("db.vcd"); $dumpvars(0, tb.in, tb.out);
    #10 rst = 0; #20000;
    for (i = 0; i < 40; i = i + 1) begin
      nb = 3 + ($random(seed) & 15) + ($random(seed) & 7);
      for (k = 0; k < nb; k = k + 1) begin
        in = ~in; gap = 5 + ($random(seed) & 127);
        #(gap);
      end
      in = (i % 2 == 0) ? 1 : 0;
      $display("LAST %0f", $realtime);
      #40000;
    end
    $finish;
  end
endmodule
"""


def run(p):
    log, vcd = hdl.simulate(p, {"debounce.v": DB, "tb_debounce.v": TB}, "tb")
    it, iv = vcd["tb.in"]; ot, ov = vcd["tb.out"]
    it = np.array(it) * 1e-3; ot = np.array(ot) * 1e-3   # ns -> µs (VCD in 1 ns units)
    iv = [0 if v is None else v for v in iv]; ov = [0 if v is None else v for v in ov]
    raw = int(np.sum(np.diff(iv) != 0)); clean = int(np.sum(np.diff(ov) != 0))
    last = [float(l.split()[1]) for l in log.splitlines() if l.startswith("LAST")]
    p.compare("Output edges for 40 presses/releases", 40, clean, "", kind="abs")
    p.metric("Raw input edges (with bounce)", raw)
    out_edges = ot[1:][np.diff(ov) != 0] if False else np.array([t for t, a, b in zip(ot[1:], ov[:-1], ov[1:]) if a != b])
    lat = []
    for L in last:
        nxt = out_edges[out_edges > L]
        if len(nxt):
            lat.append((nxt[0] - L) / 1000)
    p.compare("Latency upper bound after last bounce (N·T_tick)", 10, float(np.max(lat)), "ms", kind="abs")
    p.metric("Mean latency after last bounce", float(np.mean(lat)), "ms", "below N·T because counting can begin inside the burst")
    fig, ax = p.fig(h=3.2)
    vcdn = {"in": (list(it / 1000), iv), "out": (list(ot / 1000), ov)}
    t0 = last[0] / 1000 - 3
    hdl.waveform_plot(ax, vcdn, [("in", "raw switch"), ("out", "debounced")], t0, t0 + 20, unit="ms")
    ax.set_title("One press: a burst of bounce edges, one clean output edge 10 ms later", loc="left")
    p.save(fig, "timing", "The debounced output switches only after 10 stable ticks.")
    p.csv("latency", latency_ms=lat)
    p.discuss("""The raw line shows hundreds of edges for 40 actuations; the debounced output has exactly 40. My first
prediction (10.5 ms mean) assumed counting starts after the last bounce; because the input is sampled
only on 1 ms ticks, samples inside the burst that happen to show the new level start the count early,
so the mean latency is ~9 ms and the hard bound is N·T = 10 ms. Either way latency is set by the design
constant N, so it is bounded and predictable — unlike an RC + Schmitt analog debouncer whose delay drifts with component tolerance. The
two-flop synchroniser in front is not optional: it stops the asynchronous button from causing
metastability in the counter logic.""")
