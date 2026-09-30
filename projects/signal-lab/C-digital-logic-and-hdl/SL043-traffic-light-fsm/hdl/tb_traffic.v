`timescale 1s/1ms
module tb;
  reg clk = 0, rst = 1, ped = 0; wire [2:0] ns, ew;
  traffic dut(clk, rst, ped, ns, ew);
  always #0.5 clk = ~clk;
  initial begin
    $dumpfile("traffic.vcd"); $dumpvars(0, tb);
    #2 rst = 0;
    #100 ped = 1; #1 ped = 0;
    #57 ped = 1; #1 ped = 0;
    #140 $finish;
  end
endmodule
