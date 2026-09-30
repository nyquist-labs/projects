`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1; wire o2, o3, o5, o10, o1000;
  clkdiv #(2) d2(clk, rst, o2); clkdiv #(3) d3(clk, rst, o3); clkdiv #(5) d5(clk, rst, o5);
  clkdiv #(10) d10(clk, rst, o10); clkdiv #(1000) d1000(clk, rst, o1000);
  always #5 clk = ~clk;
  initial begin $dumpfile("div.vcd"); $dumpvars(0, tb.o2, tb.o3, tb.o5, tb.o10, tb.o1000, tb.clk); #52 rst = 0; #60000 $finish; end
endmodule
