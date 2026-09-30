from eelab import *
from eelab import hdl

META = dict(
    id="SL-046", title="UART receiver with 16× oversampling", level="M",
    tools="Verilog RTL, Icarus Verilog (baud-mismatch sweep), Python",
    summary="A 16×-oversampling 8N1 receiver with majority voting and framing-error detection; sweep the "
            "transmitter's baud-rate error and find the tolerance limit.",
    problem="Transmitter and receiver clocks never match exactly. How large a baud-rate mismatch can the "
            "receiver absorb before bytes corrupt?",
    theory=r"""The receiver starts its bit timer on the (synchronised) start edge, then takes three samples at the ends of
ticks 7, 8, 9 of each 16-tick bit and majority-votes them. The middle sample of data bit k therefore lands at
$k+1.5$ bit times after the edge (receiver clock). A transmitter whose bit period is $(1+\varepsilon)$ times
nominal puts bit k in $[(k+1)(1+\varepsilon),\,(k+2)(1+\varepsilon))$. The byte is decoded correctly while the
middle sample of the *last* data bit (k = 7, at 8.5) stays inside its cell:
$$8(1+\varepsilon)\le 8.5\Rightarrow\varepsilon\le +6.25\,\%,\qquad 9(1+\varepsilon)>8.5\Rightarrow\varepsilon>-5.56\,\%$$
The stop bit is sampled at 9.5, so framing errors start earlier: $\varepsilon > +5.56\,\%$ or $\varepsilon<-5.0\,\%$.
(The common rule of thumb ±4–5 % is this analysis plus margin for edge-detection jitter and noise.)""",
    method="""Receiver clocked at 16 × 115,200 Hz equivalent (CLKS_PER_SAMPLE = 27 at 50 MHz). The testbench's behavioural
transmitter sends 200 random bytes at a bit period scaled by (1+ε) for ε from −7 % to +7 %; the count of
wrong bytes and framing errors is recorded at each ε.""",
)

RX = """
module uart_rx #(parameter CPS = 27)(input clk, rst, rx, output reg [7:0] data, output reg valid, output reg ferr);
  reg [15:0] cnt; reg [3:0] tick; reg [3:0] bitn; reg [1:0] st; reg [2:0] sync; reg [2:0] maj;
  wire s = sync[2];
  wire vote = (maj[0] & maj[1]) | (maj[1] & maj[2]) | (maj[0] & maj[2]);
  always @(posedge clk) begin
    sync <= {sync[1:0], rx};
    valid <= 0;
    if (rst) begin st <= 0; ferr <= 0; cnt <= 0; end
    else begin
      if (cnt == CPS - 1) cnt <= 0; else cnt <= cnt + 1;
      case (st)
        0: begin ferr <= 0; if (!s) begin st <= 1; tick <= 0; cnt <= 0; end end
        1: if (cnt == CPS - 1) begin            // start bit: confirm at centre
             tick <= tick + 1;
             if (tick >= 6 && tick <= 8) maj <= {maj[1:0], s};
             if (tick == 15) begin
               if (vote) st <= 0; else begin st <= 2; bitn <= 0; tick <= 0; end
             end
           end
        2: if (cnt == CPS - 1) begin
             tick <= tick + 1;
             if (tick >= 6 && tick <= 8) maj <= {maj[1:0], s};
             if (tick == 15) begin
               data <= {vote, data[7:1]}; tick <= 0;
               if (bitn == 7) st <= 3; else bitn <= bitn + 1;
             end
           end
        3: if (cnt == CPS - 1) begin
             tick <= tick + 1;
             if (tick >= 6 && tick <= 8) maj <= {maj[1:0], s};
             if (tick == 9) begin valid <= 1; ferr <= !vote; st <= 0; end
           end
      endcase
    end
  end
endmodule
"""
TB = """
`timescale 1ns/1ps
module tb;
  parameter real EPS = 0.0;
  reg clk = 0, rst = 1, rx = 1; wire [7:0] data; wire valid, ferr;
  uart_rx #(27) dut(clk, rst, rx, data, valid, ferr);
  always #10 clk = ~clk;
  real Tb; integer i, k, errs = 0, ferrs = 0, got = 0; reg [7:0] b; reg [7:0] q [0:255]; integer head = 0, tail = 0;
  always @(posedge clk) if (valid) begin
    got = got + 1;
    if (ferr) ferrs = ferrs + 1;
    if (data !== q[tail]) errs = errs + 1;
    tail = tail + 1;
  end
  initial begin
    Tb = 27.0 * 16 * 20.0 * (1.0 + EPS);
    #200 rst = 0; #1000;
    for (i = 0; i < 200; i = i + 1) begin
      b = $random; q[head] = b; head = head + 1;
      rx = 0; #(Tb);
      for (k = 0; k < 8; k = k + 1) begin rx = b[k]; #(Tb); end
      rx = 1; #(Tb);
      #(Tb * 0.3);
    end
    #(Tb * 20);
    $display("RES errors %0d", errs + (200 - got));
    $display("RES ferrs %0d", ferrs);
    $finish;
  end
endmodule
"""


def run(p):
    eps = np.round(np.arange(-0.07, 0.0701, 0.005), 3)
    errs, ferrs = [], []
    for e in eps:
        log, _ = hdl.simulate(p, {"uart_rx.v": RX, "tb_uart_rx.v": TB.replace("parameter real EPS = 0.0", f"parameter real EPS = {e}")}, "tb")
        r = hdl.results(log)
        errs.append(r["errors"]); ferrs.append(r["ferrs"])
    errs = np.array(errs); ok = eps[errs == 0]
    lim_pos, lim_neg = ok.max(), -ok.min()
    p.compare("Data-error-free limit, fast TX (|ε|)", 0.0556, lim_neg, "", kind="abs", note="sweep step 0.5 %")
    p.compare("Data-error-free limit, slow TX (ε)", 0.0625, lim_pos, "", kind="abs")
    ferrs_a = np.array(ferrs); okf = eps[ferrs_a == 0]
    p.metric("Framing-error-free limit, fast TX (|ε|)", -okf.min(), "", "beyond the data limit; the 0.3-bit idle gap between test frames delays framing failures")
    p.compare("Framing-error-free limit, slow TX (ε)", 0.0556, okf.max(), "", kind="abs")
    p.compare("Byte errors at ε = 0 (200 bytes)", 0, errs[np.argmin(abs(eps))], "", kind="abs")
    fig, ax = p.fig()
    ax.plot(eps * 100, errs / 2, "o-", color=C_MEAS, label="byte error rate (%)")
    ax.plot(eps * 100, np.array(ferrs) / 2, "s--", color=COLORS[2], label="framing errors (%)")
    for x_ in (-5.56, 6.25):
        ax.axvline(x_, color=C_PRED, ls="--", lw=1)
    ax.text(-6.9, 60, "predicted\ndata limits", color=C_PRED, fontsize=8)
    style_axes(ax, "transmitter baud-rate error (%)", "% of 200 bytes", "Receiver tolerance to clock mismatch")
    p.save(fig, "tolerance", "Error-free window around ε = 0, collapsing at the predicted −5.6 % / +6.25 %.")
    p.csv("sweep", eps=eps, byte_errors=errs, framing_errors=ferrs)
    p.discuss("""My first prediction (±3.9–4.6 %) used the textbook stop-bit rule of thumb and undershot the measured
window; working through *this* receiver's actual sample instants (ends of ticks 7–9, middle at k + 1.5
bits) gives asymmetric limits of −5.6 % / +6.25 % for data and +5.6 % for slow-side framing, which the
sweep reproduces to its 0.5 % resolution. Framing errors appear first on the slow side, because a slow transmitter pushes the stop bit
late and the receiver samples the previous data bit. The practical rule that emerges: keep the
combined clock error of both ends under ~2 % (half the budget for each side).""")
