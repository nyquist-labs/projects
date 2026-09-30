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
