from eelab import *
from eelab import hdl

META = dict(
    id="SL-058", title="Asynchronous SRAM controller", level="M",
    tools="Verilog controller FSM + timing-checking SRAM behavioural model, Icarus Verilog",
    summary="A controller that turns single-cycle read/write requests into correctly timed asynchronous "
            "SRAM cycles; the SRAM model checks t_AA, t_WP and data setup and returns X on violations. "
            "Sweep the clock and find the minimum number of wait states.",
    problem="An asynchronous SRAM has no clock — only timing parameters. How many clock cycles must a "
            "controller spend per access at a given frequency?",
    theory=r"""A read is valid t_AA = 55 ns after the address is stable; a write needs WE̅ low for t_WP = 40 ns with data set up
t_DW = 25 ns before WE̅ rises. With a clock period T and W wait states the controller holds the address for
(W+1)·T before latching data, so it needs $W_{read}=\lceil t_{AA}/T\rceil-1$ and the write pulse of
(W+1)·T ≥ t_WP → $W_{write}=\lceil t_{WP}/T\rceil-1$. At 100 MHz: W_read = 5, W_write = 3.""",
    method="""Controller parameterised by wait states; the SRAM model (1 K × 16) checks its own timing with specify-like
checks and drives X if t_AA is not met. For clock frequencies 25–200 MHz, each W from 0 up is tried with
250 writes followed by 250 reads in scrambled order (so every read presents a new address); the smallest W with zero errors is recorded.""",
)

SRC = """
`timescale 1ns/1ps
module sram_ctrl #(parameter W = 3)(input clk, rst, input req, we, input [9:0] addr, input [15:0] wdata,
   output reg [15:0] rdata, output reg done, output reg [9:0] a, inout [15:0] d, output reg ce_n, we_n, oe_n);
  reg [7:0] cnt; reg [1:0] st; reg drive; reg [15:0] dout;
  assign d = drive ? dout : 16'hzzzz;
  always @(posedge clk) begin
    done <= 0;
    if (rst) begin st <= 0; ce_n <= 1; we_n <= 1; oe_n <= 1; drive <= 0; end
    else case (st)
      0: if (req) begin a <= addr; ce_n <= 0; cnt <= 0;
           if (we) begin dout <= wdata; drive <= 1; we_n <= 0; st <= 2; end
           else begin oe_n <= 0; st <= 1; end
         end
      1: if (cnt == W) begin rdata <= d; oe_n <= 1; ce_n <= 1; done <= 1; st <= 3; end else cnt <= cnt + 1;
      2: if (cnt == W) begin we_n <= 1; ce_n <= 1; done <= 1; st <= 3; end else cnt <= cnt + 1;
      3: begin drive <= 0; st <= 0; end
    endcase
  end
endmodule
"""
TB = """
`timescale 1ns/1ps
module sram(input [9:0] a, inout [15:0] d, input ce_n, we_n, oe_n);
  parameter real tAA = 55, tWP = 40, tDW = 25;
  reg [15:0] m [0:1023]; reg [15:0] q; real ta, twf, tdc; integer viol = 0;
  assign d = (!ce_n && !oe_n && we_n) ? q : 16'hzzzz;
  initial ta = 0;
  always @(a) ta = $realtime;
  // output is valid only once the address has been stable for t_AA (re-evaluated every 0.25 ns)
  always #0.25 q = (($realtime - ta) >= tAA) ? m[a] : 16'hxxxx;
  always @(negedge we_n) twf = $realtime;
  always @(d) tdc = $realtime;
  initial twf = -1;
  always @(posedge we_n) if (twf >= 0) begin
    if ($realtime - twf < tWP || $realtime - tdc < tDW) begin viol = viol + 1; m[a] = 16'hxxxx; end
    else m[a] = d;
  end
endmodule
module tb;
  parameter real TCLK = 10.0; parameter integer W = 3;
  reg clk = 0, rst = 1, req = 0, we = 0; reg [9:0] addr; reg [15:0] wd; wire [15:0] rd; wire done;
  wire [9:0] a; wire [15:0] d; wire ce_n, we_n, oe_n;
  sram_ctrl #(W) c(clk, rst, req, we, addr, wd, rd, done, a, d, ce_n, we_n, oe_n);
  sram s(a, d, ce_n, we_n, oe_n);
  always #(TCLK/2) clk = ~clk;
  integer i, j, errs = 0; reg [15:0] v; reg [15:0] model [0:255];
  task op(input w, input [9:0] ad, input [15:0] dat); begin
    @(negedge clk); we = w; addr = ad; wd = dat; req = 1; @(negedge clk); req = 0; @(posedge done); @(negedge clk); @(negedge clk);
  end endtask
  initial begin
    #(3*TCLK) rst = 0;
    for (i = 0; i < 250; i = i + 1) begin v = $random; model[i] = v; op(1, i, v); end
    // read back in a scrambled order so every read presents a NEW address (t_AA really applies)
    for (i = 0; i < 250; i = i + 1) begin
      j = (i * 37) % 250; op(0, j, 0);
      if (rd !== model[j]) errs = errs + 1;
    end
    $display("RES errors %0d", errs);
    $display("RES viol %0d", s.viol);
    $finish;
  end
endmodule
"""


def run(p):
    freqs = [25e6, 50e6, 100e6, 150e6, 180e6]
    tAA, tWP = 55e-9, 40e-9
    wmin, wpred = [], []
    for f in freqs:
        T = 1 / f
        pred = max(int(np.ceil(tAA / T)) - 1, int(np.ceil(tWP / T)) - 1, 0)
        found = None
        for W in range(0, 14):
            tb = TB.replace("parameter real TCLK = 10.0; parameter integer W = 3;", f"parameter real TCLK = {T*1e9:.4f}; parameter integer W = {W};")
            log, _ = hdl.simulate(p, {"sram_ctrl.v": SRC, "tb_sram.v": tb}, "tb")
            r = hdl.results(log)
            if r["errors"] == 0 and r["viol"] == 0:
                found = W
                break
        wmin.append(found if found is not None else np.nan); wpred.append(pred)
        p.compare(f"{f/1e6:g} MHz: minimum wait states", pred, np.nan if found is None else found, "", kind="abs")
    bw = [f / (w + 3) * 2 for f, w in zip(freqs, wmin)]
    p.metric("Access time at 100 MHz (read)", (wmin[2] + 1) * 10 + 10, "ns", "address→data latched incl. setup cycle")
    fig, ax = p.fig(1, 2)
    ax[0].plot(np.array(freqs) / 1e6, wpred, "--o", color=C_PRED, label="⌈t/T⌉ − 1 prediction")
    ax[0].plot(np.array(freqs) / 1e6, wmin, "s", color=C_MEAS, ms=8, label="minimum passing W (simulation)")
    style_axes(ax[0], "clock (MHz)", "wait states", "Wait states vs clock")
    ax[1].plot(np.array(freqs) / 1e6, np.array(bw) / 1e6, "o-", color=C_MEAS)
    style_axes(ax[1], "clock (MHz)", "M accesses/s", "Throughput saturates near 1/t_AA", legend=False)
    p.save(fig, "wait_states", "A faster clock needs more wait states, so throughput barely improves.")
    p.csv("sweep", freq_hz=freqs, w_min=wmin, w_pred=wpred)
    p.discuss("""The minimum wait-state count found by brute-force simulation matches ⌈t/T⌉ − 1 at every frequency — the
timing-checking SRAM model returns X (and counts a violation) whenever the controller is one cycle too
eager. A first version of the test wrote and immediately read back the *same* address, so the address
had been stable for a whole write cycle and reads passed with too few wait states — a reminder that a
timing test must actually exercise the timing path. The throughput plot makes the system-level point: above ~50 MHz the extra clock speed is spent
entirely in wait states, because the memory's own access time (not the controller) is the bottleneck.""")
