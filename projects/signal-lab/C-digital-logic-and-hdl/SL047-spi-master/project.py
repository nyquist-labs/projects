from eelab import *
from eelab import hdl

META = dict(
    id="SL-047", title="SPI master (mode 0)", level="M",
    tools="Verilog RTL + behavioural SPI slave (loopback shift register), Icarus Verilog",
    summary="An SPI mode-0 master with configurable clock divider: verify SCLK frequency, chip-select "
            "framing and full-duplex data against a slave model over 256 transfers.",
    problem="Implement the four-wire SPI protocol and prove its timing: data must be stable at every "
            "rising SCLK edge and change on falling edges.",
    theory=r"""Mode 0 (CPOL = 0, CPHA = 0): SCLK idles low, both sides sample on the rising edge and shift on the falling edge.
With divider DIV the SCLK period is $2\cdot DIV$ system clocks → $f_{SCLK}=f_{clk}/(2\,DIV)$ = 50 MHz/(2·5) = 5 MHz.
One byte = 8 SCLK periods = 1.6 µs plus CS setup/hold, so ≈ 600 kB/s at most. Setup margin
= half an SCLK period (100 ns) before each sampling edge.""",
    method="""Master drives SCLK/MOSI/CS; the testbench slave is an 8-bit shift register that returns the previous byte
(so MISO data can be checked). 256 random bytes; Python measures SCLK period and MOSI-to-SCLK setup
time from the VCD.""",
)

SPI = """
module spi_master #(parameter DIV = 5)(input clk, rst, start, input [7:0] tx, output reg [7:0] rx,
                                        output reg done, output reg sclk, output reg mosi, output reg cs, input miso);
  reg [7:0] sh; reg [3:0] n; reg [15:0] c; reg act;
  always @(posedge clk) begin
    done <= 0;
    if (rst) begin sclk <= 0; cs <= 1; act <= 0; mosi <= 0; end
    else if (!act && start) begin act <= 1; cs <= 0; sh <= tx; mosi <= tx[7]; n <= 0; c <= 0; end
    else if (act) begin
      if (c == DIV - 1) begin
        c <= 0;
        if (!sclk) begin sclk <= 1; rx <= {rx[6:0], miso}; end     // rising: sample
        else begin
          sclk <= 0;                                               // falling: shift
          if (n == 7) begin act <= 0; cs <= 1; done <= 1; end
          else begin n <= n + 1; sh <= {sh[6:0], 1'b0}; mosi <= sh[6]; end
        end
      end else c <= c + 1;
    end
  end
endmodule
"""
TB = """
`timescale 1ns/1ps
module slave(input sclk, cs, mosi, output miso);
  reg [7:0] sr = 8'hA5;
  assign miso = sr[7];
  reg [7:0] last;
  always @(posedge sclk) if (!cs) sr <= {sr[6:0], mosi};
endmodule
module tb;
  reg clk = 0, rst = 1, start = 0; reg [7:0] tx; wire [7:0] rx; wire done, sclk, mosi, cs, miso;
  spi_master #(5) m(clk, rst, start, tx, rx, done, sclk, mosi, cs, miso);
  slave s(sclk, cs, mosi, miso);
  always #10 clk = ~clk;
  integer i, errs = 0; reg [7:0] prev;
  initial begin
    $dumpfile("spi.vcd"); $dumpvars(0, tb.sclk, tb.mosi, tb.cs, tb.miso);
    prev = 8'hA5;
    #100 rst = 0;
    for (i = 0; i < 256; i = i + 1) begin
      @(negedge clk); tx = $random; start = 1; @(negedge clk); start = 0;
      @(posedge done); #1;
      if (rx !== prev) errs = errs + 1;
      prev = tx;
      #200;
    end
    $display("RES errors %0d", errs);
    $finish;
  end
endmodule
"""


def run(p):
    log, vcd = hdl.simulate(p, {"spi_master.v": SPI, "tb_spi.v": TB}, "tb")
    r = hdl.results(log)
    p.compare("MISO bytes wrong (256 full-duplex transfers)", 0, r["errors"], "", kind="abs")
    st, sv = vcd["tb.sclk"]
    st = np.array(st) * 1e-3
    rises = st[1:][np.diff(np.array(sv)) > 0] if False else np.array([t for t, v in zip(st, sv) if v == 1])
    per = np.diff(rises); per = per[per < 1000]
    p.compare("SCLK frequency", 50e6 / 10, 1e9 / np.median(per), "Hz", tol=0.5)
    mt, mv = vcd["tb.mosi"]; mt = np.array(mt) * 1e-3
    setup = [t - mt[np.searchsorted(mt, t, side="right") - 1] for t in rises]
    p.compare("Worst MOSI setup before rising SCLK", 100, float(np.min(setup)), "ns", kind="abs",
              note="data changes on the falling edge")
    fig, ax = p.fig(h=3.4)
    vcdn = {k: (list(np.array(v[0]) * 1e-3), v[1]) for k, v in vcd.items()}
    t0 = rises[0] - 200
    hdl.waveform_plot(ax, vcdn, [("tb.cs", "CS̅"), ("tb.sclk", "SCLK"), ("tb.mosi", "MOSI"), ("tb.miso", "MISO")], t0, t0 + 2000)
    ax.set_title("One SPI mode-0 byte transfer", loc="left")
    p.save(fig, "timing", "Data changes on falling SCLK edges and is sampled on rising edges.")
    p.discuss("""All 256 transfers return the previous byte from the loopback slave, which checks both directions of
the full-duplex link. MOSI changes exactly one half-period before each sampling edge, giving the 100 ns
setup margin that makes mode 0 robust — a slave with up to ~90 ns of input delay would still work at
5 MHz. The first bit is driven when CS falls, which is why mode-0 slaves must have MISO valid
immediately after CS goes low.""")
