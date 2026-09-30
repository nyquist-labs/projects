from eelab import *
from eelab import hdl

META = dict(
    id="SL-048", title="I²C master with ACK handling", level="H",
    tools="Verilog RTL (open-drain bus with pull-ups), behavioural I²C slave, Icarus Verilog",
    summary="An I²C master that generates START/STOP, sends a 7-bit address + R/W, writes and reads data "
            "bytes and detects NACKs, tested against a slave model on a wired-AND open-drain bus.",
    problem="I²C shares two open-drain wires between many devices. Implement the start/stop conditions, "
            "addressing and acknowledge protocol, and show the master handles a missing device.",
    theory=r"""START = SDA falls while SCL high; STOP = SDA rises while SCL high; data may only change while SCL is low.
Each byte is followed by an ACK bit driven low by the receiver. Open-drain wired-AND: the line is low if
*any* device pulls it low. Bus rate $f_{SCL}=f_{clk}/(4\cdot DIV)$ = 50 MHz/(4·125) = 100 kHz (standard mode).
A write of one register = START + addr + reg + data + STOP = 3·9 + 2 ≈ 29 SCL periods ≈ 290 µs.""",
    method="""Master state machine with a quarter-period phase counter. Slave model at address 0x42 with a 4-byte
register file, open-drain modelled with `tri1` nets (pull-up) and conditional drivers. Test: write
bytes to 4 registers, read them back, then address a non-existent device (0x13) and check the NACK flag.""",
)

I2C = """
module i2c_master #(parameter DIV = 125)(input clk, rst, input go, input rw, input [6:0] addr, input [7:0] reg_a,
    input [7:0] wdata, output reg [7:0] rdata, output reg busy, output reg nack, inout sda, inout scl);
  reg sda_o, scl_o;  // 1 = release (high-Z), 0 = pull low
  assign sda = sda_o ? 1'bz : 1'b0;
  assign scl = scl_o ? 1'bz : 1'b0;
  reg [15:0] q; reg [1:0] ph; reg [5:0] st; reg [3:0] bitn; reg [7:0] sh; reg phase_tick;
  always @(posedge clk) begin
    phase_tick <= 0;
    if (rst) begin q <= 0; ph <= 0; end
    else if (busy) begin if (q == DIV - 1) begin q <= 0; ph <= ph + 1; phase_tick <= 1; end else q <= q + 1; end
  end
  // states: 0 idle,1 start,2 byte,3 ack,4 next,5 rstart,6 read byte,7 master nack,8 stop,9 done
  reg [1:0] which;  // which byte: 0 addr+W, 1 reg, 2 data/addr+R
  always @(posedge clk) begin
    if (rst) begin busy <= 0; sda_o <= 1; scl_o <= 1; st <= 0; nack <= 0; end
    else case (st)
      0: if (go) begin busy <= 1; nack <= 0; st <= 1; which <= 0; end
      1: if (phase_tick) case (ph)            // START: SDA low while SCL high
           1: sda_o <= 0;
           2: scl_o <= 0;
           3: begin st <= 2; sh <= {addr, 1'b0}; bitn <= 0; end
         endcase
      2: if (phase_tick) case (ph)            // send bit: set SDA at ph0, SCL high ph1-2, low ph3
           0: sda_o <= sh[7];
           1: scl_o <= 1;
           3: begin scl_o <= 0; sh <= {sh[6:0], 1'b0}; if (bitn == 7) st <= 3; else bitn <= bitn + 1; end
         endcase
      3: if (phase_tick) case (ph)            // ACK from slave
           0: sda_o <= 1;
           1: scl_o <= 1;
           2: if (sda) nack <= 1;
           3: begin scl_o <= 0;
                if (nack) st <= 8;
                else if (which == 0) begin which <= 1; sh <= reg_a; bitn <= 0; st <= 2; end
                else if (which == 1 && !rw) begin which <= 2; sh <= wdata; bitn <= 0; st <= 2; end
                else if (which == 1 && rw) st <= 5;
                else if (which == 3) begin bitn <= 0; st <= 6; end
                else st <= 8;
              end
         endcase
      5: if (phase_tick) case (ph)            // repeated START
           0: sda_o <= 1;
           1: scl_o <= 1;
           2: sda_o <= 0;
           3: begin scl_o <= 0; which <= 3; sh <= {addr, 1'b1}; bitn <= 0; st <= 2; end
         endcase
      6: if (phase_tick) case (ph)            // read bit
           0: sda_o <= 1;
           1: scl_o <= 1;
           2: rdata <= {rdata[6:0], sda};
           3: begin scl_o <= 0; if (bitn == 7) st <= 7; else bitn <= bitn + 1; end
         endcase
      7: if (phase_tick) case (ph)            // master NACK (last byte)
           0: sda_o <= 1;
           1: scl_o <= 1;
           3: begin scl_o <= 0; st <= 8; end
         endcase
      8: if (phase_tick) case (ph)            // STOP
           0: sda_o <= 0;
           1: scl_o <= 1;
           2: sda_o <= 1;
           3: st <= 9;
         endcase
      9: begin busy <= 0; st <= 0; end
    endcase
  end
endmodule
"""
TB = """
`timescale 1ns/1ps
module i2c_slave #(parameter ADDR = 7'h42)(inout sda, input scl);
  reg sda_o = 1; assign sda = sda_o ? 1'bz : 1'b0;
  reg [7:0] mem [0:3]; reg [7:0] sh; reg [3:0] n; reg [1:0] ptr; reg active = 0, rd = 0, addr_ok = 0;
  integer byte_i = 0; reg ackphase = 0, sending = 0;
  always @(negedge sda) if (scl) begin active <= 1; n <= 0; byte_i <= 0; ackphase <= 0; sending <= 0; sda_o <= 1; end
  always @(posedge sda) if (scl) begin active <= 0; sda_o <= 1; end
  always @(posedge scl) if (active && !ackphase && !sending) begin sh <= {sh[6:0], sda}; n <= n + 1; end
  always @(negedge scl) if (active) begin
    if (sending) begin
      if (n == 8) begin sda_o <= 1; sending <= 0; ackphase <= 1; n <= 0; end
      else begin sda_o <= sh[7]; sh <= {sh[6:0], 1'b0}; n <= n + 1; end
    end else if (ackphase) begin
      ackphase <= 0; sda_o <= 1;
      if (rd && addr_ok && byte_i == 1) begin sending <= 1; byte_i <= 2; sh <= {mem[ptr][6:0], 1'b0}; sda_o <= mem[ptr][7]; n <= 1; end
    end else if (n == 8) begin
      n <= 0;
      if (byte_i == 0) begin
        addr_ok = (sh[7:1] == ADDR); rd = sh[0];
        if (addr_ok) begin sda_o <= 0; ackphase <= 1; end
      end else if (addr_ok && byte_i == 1 && !rd) begin ptr <= sh[1:0]; sda_o <= 0; ackphase <= 1; end
      else if (addr_ok && byte_i == 2) begin mem[ptr] <= sh; sda_o <= 0; ackphase <= 1; end
      byte_i <= (byte_i == 0 && rd) ? 1 : byte_i + 1;
    end
  end
endmodule
module tb;
  reg clk = 0, rst = 1, go = 0, rw = 0; reg [6:0] addr; reg [7:0] ra, wd; wire [7:0] rdata; wire busy, nack;
  tri1 sda, scl;
  i2c_master #(125) m(clk, rst, go, rw, addr, ra, wd, rdata, busy, nack, sda, scl);
  i2c_slave #(7'h42) s(sda, scl);
  always #10 clk = ~clk;
  integer i, errs = 0; reg [7:0] vals [0:3];
  time t0, t1;
  task xfer(input r, input [6:0] a, input [7:0] reg_, input [7:0] d); begin
    @(negedge clk); rw = r; addr = a; ra = reg_; wd = d; go = 1; @(negedge clk); go = 0;
    wait (!busy); #2000;
  end endtask
  initial begin
    $dumpfile("i2c.vcd"); $dumpvars(0, tb.sda, tb.scl);
    #200 rst = 0;
    vals[0] = 8'h3C; vals[1] = 8'hA7; vals[2] = 8'h01; vals[3] = 8'hFE;
    t0 = $time;
    xfer(0, 7'h42, 0, vals[0]);
    t1 = $time;
    $display("RES write_time_ns %0d", t1 - t0);
    for (i = 1; i < 4; i = i + 1) xfer(0, 7'h42, i, vals[i]);
    for (i = 0; i < 4; i = i + 1) begin
      // set pointer (write with no data) then read: emulate with a pointer write followed by read
      xfer(1, 7'h42, i, 0);
      if (rdata !== vals[i] || nack) errs = errs + 1;
      $display("READ %0d %0h", i, rdata);
    end
    xfer(0, 7'h13, 0, 8'h55);
    $display("RES nack_missing %0d", nack);
    $display("RES errors %0d", errs);
    $finish;
  end
endmodule
"""


def run(p):
    log, vcd = hdl.simulate(p, {"i2c_master.v": I2C, "tb_i2c.v": TB}, "tb")
    r = hdl.results(log)
    p.compare("Read-back errors (4 registers)", 0, r["errors"], "", kind="abs")
    p.compare("NACK flagged for absent address 0x13", 1, r["nack_missing"], "", kind="abs")
    st, sv = vcd["tb.scl"]; st = np.array(st) * 1e-3
    rises = np.array([t for t, v in zip(st, sv) if v == 1])
    per = np.diff(rises); per = per[per < 20000]
    p.compare("SCL frequency", 100e3, 1e9 / np.median(per), "Hz", tol=1)
    p.compare("Single-register write duration", 29 / 100e3 + 2e-6, r["write_time_ns"] * 1e-9, "s", tol=10)
    fig, ax = p.fig(h=3.2)
    vcdn = {k: (list(np.array(v[0]) * 1e-3 / 1e3), v[1]) for k, v in vcd.items()}
    hdl.waveform_plot(ax, vcdn, [("tb.scl", "SCL"), ("tb.sda", "SDA")], 0, 320, unit="µs")
    ax.set_title("I²C write: START, 0x42+W, ACK, reg, ACK, data, ACK, STOP", loc="left")
    p.save(fig, "timing", "The first transaction on the bus; SDA only changes while SCL is low except at START/STOP.")
    p.discuss("""The master writes and reads back all four registers through a repeated-START read, and flags a
NACK when it addresses a device that is not on the bus — the check most hobby I²C drivers omit.
Modelling the bus with `tri1` (pull-up) nets and drivers that can only pull low reproduces the wired-AND
behaviour that lets a slave hold SDA low to acknowledge. The first version of the *slave model* had a real bug that this test caught: after the master's final
NACK it started re-sending the byte, and whenever that byte's MSB was 0 it held SDA low through the STOP
condition, so the next transaction never started (2 of 4 read-backs failed, and the missing-device test
silently passed for the wrong reason). A slave must stop driving after a NACK. Clock stretching and
multi-master arbitration are not implemented; both would reuse the same "release and read back the line" mechanism.""")
