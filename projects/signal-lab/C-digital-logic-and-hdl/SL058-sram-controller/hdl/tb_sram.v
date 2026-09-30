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
  parameter real TCLK = 5.5556; parameter integer W = 9;
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
