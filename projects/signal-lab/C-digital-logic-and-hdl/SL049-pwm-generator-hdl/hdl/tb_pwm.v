`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1; reg [8:0] cmp = 0; wire out;
  pwm #(8) dut(clk, rst, cmp, out);
  always #10 clk = ~clk;
  integer i; integer vals [0:7];
  initial begin
    $dumpfile("pwm.vcd"); $dumpvars(0, tb.out, tb.cmp);
    vals[0] = 0; vals[1] = 1; vals[2] = 32; vals[3] = 64; vals[4] = 128; vals[5] = 200; vals[6] = 255; vals[7] = 256;
    #100 rst = 0;
    for (i = 0; i < 8; i = i + 1) begin
      #(20 * 256 * 4 + ($random & 1023)); cmp = vals[i];
    end
    #(20 * 256 * 5) $finish;
  end
endmodule
