from eelab import *
from eelab import hdl

META = dict(
    id="SL-054", title="Asynchronous FIFO with Gray-code pointers", level="H",
    tools="Verilog RTL (dual-clock FIFO, 2-FF synchronisers), Icarus Verilog stress test",
    summary="A 16-entry FIFO between unrelated 50 MHz and 37 MHz clocks, using Gray-coded pointers "
            "synchronised across domains; stress it with random bursts and check ordering, full/empty "
            "flags and throughput.",
    problem="Passing data between two clock domains is where hardware bugs hide. Why do the pointers "
            "have to be Gray-coded, and does the FIFO stay correct under arbitrary throttling?",
    theory=r"""Binary pointers can change several bits at once, so a synchroniser sampling mid-transition could see a
wildly wrong value. Gray code changes one bit per increment, so a mis-sampled pointer is off by at most
one — which only makes full/empty *pessimistic*, never wrong. Pointers carry one extra bit to tell full
from empty. Throughput is bounded by the slower side: max rate = 37 M words/s, and the 2-FF synchronisers
add 2–3 cycles of latency to the flags.""",
    method="""Writer at 50 MHz pushes 5,000 incrementing words with random stalls (writes attempted 70 % of cycles);
reader at 37 MHz pops with random stalls (60 %). Checks: every word read in order exactly once, no write
accepted when full, no read accepted when empty. A second run with the reader always enabled measures
throughput.""",
)

FIFO = """
module afifo #(parameter W = 16, A = 4)(input wclk, wrst, we, input [W-1:0] wd, output full,
                                       input rclk, rrst, re, output [W-1:0] rd, output empty);
  reg [W-1:0] mem [0:(1<<A)-1];
  reg [A:0] wbin, wgray, rbin, rgray, wq1, wq2, rq1, rq2;
  wire [A:0] wbin_n = wbin + (we & ~full), rbin_n = rbin + (re & ~empty);
  wire [A:0] wgray_n = (wbin_n >> 1) ^ wbin_n, rgray_n = (rbin_n >> 1) ^ rbin_n;
  always @(posedge wclk) if (wrst) begin wbin <= 0; wgray <= 0; end else begin
    if (we & ~full) mem[wbin[A-1:0]] <= wd;
    wbin <= wbin_n; wgray <= wgray_n; end
  always @(posedge rclk) if (rrst) begin rbin <= 0; rgray <= 0; end else begin rbin <= rbin_n; rgray <= rgray_n; end
  always @(posedge wclk) if (wrst) {wq2, wq1} <= 0; else {wq2, wq1} <= {wq1, rgray};  // read ptr into write domain
  always @(posedge rclk) if (rrst) {rq2, rq1} <= 0; else {rq2, rq1} <= {rq1, wgray};  // write ptr into read domain
  assign full = (wgray == {~wq2[A:A-1], wq2[A-2:0]});
  assign empty = (rgray == rq2);
  assign rd = mem[rbin[A-1:0]];
endmodule
"""
TB = """
`timescale 1ns/1ps
module tb;
  parameter integer RPCT = 60;
  reg wclk = 0, rclk = 0, rst = 1, we = 0, re = 0; reg [15:0] wd = 0; wire [15:0] rd; wire full, empty;
  afifo #(16, 4) f(wclk, rst, we, wd, full, rclk, rst, re, rd, empty);
  always #10 wclk = ~wclk;
  always #13.5 rclk = ~rclk;
  integer written = 0, readn = 0, errs = 0, fullcyc = 0, emptycyc = 0, seed = 11;
  reg [15:0] expectv = 0; time t0, t1;
  always @(posedge wclk) if (!rst) begin
    if (we && !full) begin written = written + 1; wd <= wd + 1; end
    if (full) fullcyc = fullcyc + 1;
    we <= (written < 5000) && (($random(seed) % 100 + 100) % 100 < 70);
  end
  always @(posedge rclk) if (!rst) begin
    if (re && !empty) begin
      if (rd !== expectv) errs = errs + 1;
      expectv = expectv + 1; readn = readn + 1;
      if (readn == 100) t0 = $time;
      if (readn == 4900) t1 = $time;
    end
    if (empty) emptycyc = emptycyc + 1;
    re <= (($random(seed) % 100 + 100) % 100 < RPCT);
  end
  initial begin
    #100 rst = 0;
    wait (readn == 5000);
    $display("RES errors %0d", errs);
    $display("RES written %0d", written);
    $display("RES read %0d", readn);
    $display("RES rate %0f", 4800.0 / ((t1 - t0) * 1e-9));
    $display("RES full_cycles %0d", fullcyc);
    $display("RES empty_cycles %0d", emptycyc);
    $finish;
  end
endmodule
"""


def run(p):
    log, _ = hdl.simulate(p, {"afifo.v": FIFO, "tb_afifo.v": TB}, "tb")
    r = hdl.results(log)
    p.compare("Ordering/data errors (5,000 words across domains)", 0, r["errors"], "", kind="abs")
    p.compare("Words read = words written", r["written"], r["read"], "", kind="abs")
    p.compare("Throughput, random stalls (limited by 0.7·50 M vs 0.6·37 M)", min(0.7 * 50e6, 0.6 * 37.04e6), r["rate"], "words/s", tol=5)
    p.metric("Write cycles spent full", r["full_cycles"]); p.metric("Read cycles spent empty", r["empty_cycles"])
    log2, _ = hdl.simulate(p, {"afifo.v": FIFO, "tb_afifo.v": TB.replace("parameter integer RPCT = 60", "parameter integer RPCT = 100")}, "tb")
    r2 = hdl.results(log2)
    p.compare("Throughput, reader always ready (write side limits: 0.7·50 M)", min(0.7 * 50e6, 37.04e6), r2["rate"], "words/s", tol=5)
    p.compare("Ordering errors, second run", 0, r2["errors"], "", kind="abs")
    # illustrate gray vs binary multi-bit transitions
    b = np.arange(32); g = b ^ (b >> 1)
    hb = [bin(int(x ^ y)).count("1") for x, y in zip(b[:-1], b[1:])]
    hg = [bin(int(x ^ y)).count("1") for x, y in zip(g[:-1], g[1:])]
    fig, ax = p.fig()
    ax.bar(np.arange(31) - 0.2, hb, 0.4, color=COLORS[1], label="binary pointer")
    ax.bar(np.arange(31) + 0.2, hg, 0.4, color=C_MEAS, label="Gray pointer")
    style_axes(ax, "increment n → n+1", "bits that change", "Why Gray code: one bit changes per increment")
    p.save(fig, "gray_vs_binary", "Binary increments flip up to 5 bits at once; Gray always flips exactly one.")
    syn = hdl.synth(p, {"afifo.v": FIFO}, "afifo")
    p.metric("Synthesised size (16 × 16-bit)", syn["cells"], "cells", f"{syn['ffs']} flip-flops incl. storage")
    p.discuss("""All 5,000 words cross the clock boundary in order, with no overflow or underflow despite random stalls on
both sides. Throughput settles at the slower side's effective rate as predicted. Simulation cannot
reproduce metastability itself (Icarus has no analog settling), so the Gray-code argument is what
guarantees safety: the synchronised pointer is either the old or the new value, both of which are safe
for the flag logic.""")
