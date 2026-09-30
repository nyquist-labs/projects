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
