`timescale 1ns/1ps
module tb;
  reg a, b, cin; wire s, cout;
  full_adder dut(a, b, cin, s, cout);
  integer i, j, errors = 0;
  real t0, last, worst = 0;
  always @(s or cout) last = $realtime;
  initial begin
    $dumpfile("fa.vcd"); $dumpvars(0, tb);
    for (i = 0; i < 8; i = i + 1) begin
      {a, b, cin} = i; #10;
      if ({cout, s} !== a + b + cin) errors = errors + 1;
      $display("VEC %0d %0d %0d -> %0d %0d", a, b, cin, cout, s);
    end
    // worst-case settling over all 64 transitions
    for (i = 0; i < 8; i = i + 1) for (j = 0; j < 8; j = j + 1) begin
      {a, b, cin} = i; #10;
      t0 = $realtime; last = t0;
      {a, b, cin} = j;
      #10;
      if (last - t0 > worst) worst = last - t0;
    end
    $display("RES errors %0d", errors);
    $display("RES worst_delay %0f", worst);
    $finish;
  end
endmodule
