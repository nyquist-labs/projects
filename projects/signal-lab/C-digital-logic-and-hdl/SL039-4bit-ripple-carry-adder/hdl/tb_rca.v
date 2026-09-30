`timescale 1ns/1ps
module tb;
  parameter N = 32;
  reg [N-1:0] a, b; wire [N-1:0] s; wire cout;
  rca #(N) dut(a, b, s, cout);
  integer k, errs;
  real t0, last, sum;
  always @(s or cout) last = $realtime;
  task measure; begin
    t0 = $realtime; last = t0;
    #(4*N + 10);
  end endtask
  initial begin
    errs = 0; sum = 0.0;
    a = 0; b = 0; #50;
    a = {1'b0, {(N-1){1'b1}}}; b = 1; measure;
    $display("RES worst %0f", last - t0);
    for (k = 0; k < 200; k = k + 1) begin
      a = $random; b = $random; #(4*N + 10);
      a = $random; b = $random; measure;
      if ({cout, s} !== a + b) errs = errs + 1;
      sum = sum + (last - t0);
    end
    $display("RES avg %0f", sum / 200.0);
    $display("RES errors %0d", errs);
    $finish;
  end
endmodule
