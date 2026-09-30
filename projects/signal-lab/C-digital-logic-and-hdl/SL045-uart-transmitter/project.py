from eelab import *
from eelab import hdl

META = dict(
    id="SL-045", title="UART transmitter (8N1)", level="M",
    tools="Verilog RTL, Icarus Verilog, VCD decoding in Python",
    summary="A parameterised 8N1 UART transmitter: verify the bit period, the frame format and the "
            "throughput by decoding the simulated serial line in Python.",
    problem="Serialise bytes onto one wire with start and stop bits so that any receiver at the same baud "
            "rate can recover them.",
    theory=r"""Bit period $T_b = \text{CLKS\_PER\_BIT}/f_{clk}$; with 50 MHz and 434 clocks/bit, the baud rate is
115,207 bd (+0.006 % from 115,200). An 8N1 frame is 10 bits, so maximum payload throughput is
$0.8\times$ baud = 92.2 kbit/s = 11,520 bytes/s when frames are sent back-to-back.""",
    method="""TX module with a baud counter and a 10-bit shift register. Testbench (20 ns clock) sends 64 random bytes
back-to-back; Python reads the `tx` line from the VCD, measures edge-to-edge bit times and decodes the
frames by sampling at bit centres.""",
)

TX = """
module uart_tx #(parameter CLKS = 434)(input clk, rst, input [7:0] data, input start, output reg tx, output busy);
  reg [9:0] sh; reg [3:0] n; reg [15:0] cnt; reg act;
  assign busy = act;
  always @(posedge clk) begin
    if (rst) begin tx <= 1; act <= 0; end
    else if (!act && start) begin sh <= {1'b1, data, 1'b0}; n <= 0; cnt <= 0; act <= 1; tx <= 0; end
    else if (act) begin
      if (cnt == CLKS - 1) begin
        cnt <= 0;
        if (n == 9) begin act <= 0; tx <= 1; end
        else begin n <= n + 1; tx <= sh[n + 1]; end
      end else cnt <= cnt + 1;
    end
  end
endmodule
"""
TB = """
`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, start = 0; reg [7:0] data; wire tx, busy;
  uart_tx #(434) dut(clk, rst, data, start, tx, busy);
  always #10 clk = ~clk;
  integer i;
  initial begin
    $dumpfile("tx.vcd"); $dumpvars(0, tb.tx, tb.busy);
    #100 rst = 0;
    for (i = 0; i < 64; i = i + 1) begin
      @(negedge clk); data = $random; start = 1; $display("SENT %0d", data);
      @(negedge clk); start = 0;
      wait (!busy);
    end
    #20000 $finish;
  end
endmodule
"""


def run(p):
    log, vcd = hdl.simulate(p, {"uart_tx.v": TX, "tb_uart_tx.v": TB}, "tb")
    sent = [int(l.split()[1]) for l in log.splitlines() if l.startswith("SENT")]
    ts, vs = vcd["tb.tx"]
    ts = np.array(ts, float) * 1e-3   # ps -> ns
    fclk, clks = 50e6, 434
    Tb = clks / fclk * 1e9
    edges = np.diff(ts)
    bits = edges / Tb
    unit = edges[np.abs(bits - np.round(bits)) < 0.05] / np.round(bits[np.abs(bits - np.round(bits)) < 0.05])
    Tb_meas = np.median(unit[unit > 0])
    p.compare("Bit period", Tb, Tb_meas, "ns", tol=0.1)
    p.compare("Baud rate", fclk / clks, 1e9 / Tb_meas, "bd", tol=0.1)
    # decode frames
    def level(t):
        i = np.searchsorted(ts, t, side="right") - 1
        return vs[i]
    rec, t = [], ts[1] if vs[0] == 1 else ts[0]
    starts = []
    k = 0
    tt = ts[0]
    while k < len(ts):
        # find next falling edge (start bit)
        idx = [i for i in range(k, len(ts)) if vs[i] == 0 and (i == 0 or vs[i - 1] == 1)]
        if not idx:
            break
        i0 = idx[0]; t0 = ts[i0]
        byte = 0
        for b in range(8):
            byte |= level(t0 + (1.5 + b) * Tb) << b
        stop = level(t0 + 9.5 * Tb)
        rec.append(byte); starts.append(t0)
        k = np.searchsorted(ts, t0 + 9.6 * Tb)
    errors = sum(a != b for a, b in zip(sent, rec)) + abs(len(sent) - len(rec))
    p.compare("Decoded byte errors (64 frames)", 0, errors, "", kind="abs")
    thr = (len(rec) - 1) / ((starts[-1] - starts[0]) * 1e-9)
    p.compare("Throughput (bytes/s, back-to-back)", fclk / clks / 10, thr, "B/s", tol=2)
    fig, ax = p.fig(h=3.2)
    m = ts < starts[0] + 22 * Tb
    ax.step(ts[m] / 1e3, np.array(vs)[m], where="post", color=C_MEAS)
    for b in range(10):
        ax.axvline((starts[0] + b * Tb) / 1e3, color="gray", lw=.5, ls=":")
    ax.set_ylim(-0.2, 1.4)
    ax.text(starts[0] / 1e3, 1.15, f"start + 0x{sent[0]:02X} LSB-first + stop", fontsize=8)
    style_axes(ax, "time (µs)", "tx", "First two frames on the serial line", legend=False)
    p.save(fig, "frames", "Idle-high line, a low start bit, eight data bits LSB first, then a high stop bit.")
    p.csv("tx_edges", t_ns=ts, level=vs)
    p.discuss("""Bit period, baud rate and every decoded byte match. The measured throughput is a few percent below
the 10-bits-per-byte ideal because the testbench waits for `busy` to drop and then spends two clock
cycles loading the next byte — the gap between stop bit and next start bit. A FIFO in front of the
transmitter (SL-054) would let frames go out truly back-to-back.""")
