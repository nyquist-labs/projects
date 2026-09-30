`timescale 1ns/1ps
module tb;
  parameter N = 32;
  reg [N-1:0] a, b; wire [N-1:0] s; wire cout;
  add32 dut(a, b, s, cout);
  integer k, errs;
  real t0, last, worst, sum, w;
  always @(s or cout) last = $realtime;
  task measure; begin
    t0 = $realtime; last = t0;
    #40;
  end endtask
  initial begin
    errs = 0; sum = 0; worst = 0;
    for (k = 0; k < 300; k = k + 1) begin
      a = (k == 0) ? 0 : $random; b = (k == 0) ? 0 : $random; #45;
      if (k == 1) begin a = {1'b0, {(N-1){1'b1}}}; b = 1; end else begin a = $random; b = $random; end
      measure;
      w = last - t0;
      if (w > worst) worst = w;
      if ({cout, s} !== a + b) errs = errs + 1;
      sum = sum + w;
    end
    a = 0; b = 0; #45; a = {N{1'b1}}; b = 1; measure; w = last - t0; if (w > worst) worst = w;
    a = 0; b = 0; #45; a = {1'b0, {(N-1){1'b1}}}; b = 1; measure; w = last - t0; if (w > worst) worst = w;
    $display("RES worst %0f", worst);
    $display("RES avg %0f", sum / 300.0);
    $display("RES errors %0d", errs);
    $finish;
  end
endmodule
