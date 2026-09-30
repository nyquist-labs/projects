`timescale 1ns/1ps
module tb;
  parameter real EPS = 0.07;
  reg clk = 0, rst = 1, rx = 1; wire [7:0] data; wire valid, ferr;
  uart_rx #(27) dut(clk, rst, rx, data, valid, ferr);
  always #10 clk = ~clk;
  real Tb; integer i, k, errs = 0, ferrs = 0, got = 0; reg [7:0] b; reg [7:0] q [0:255]; integer head = 0, tail = 0;
  always @(posedge clk) if (valid) begin
    got = got + 1;
    if (ferr) ferrs = ferrs + 1;
    if (data !== q[tail]) errs = errs + 1;
    tail = tail + 1;
  end
  initial begin
    Tb = 27.0 * 16 * 20.0 * (1.0 + EPS);
    #200 rst = 0; #1000;
    for (i = 0; i < 200; i = i + 1) begin
      b = $random; q[head] = b; head = head + 1;
      rx = 0; #(Tb);
      for (k = 0; k < 8; k = k + 1) begin rx = b[k]; #(Tb); end
      rx = 1; #(Tb);
      #(Tb * 0.3);
    end
    #(Tb * 20);
    $display("RES errors %0d", errs + (200 - got));
    $display("RES ferrs %0d", ferrs);
    $finish;
  end
endmodule
