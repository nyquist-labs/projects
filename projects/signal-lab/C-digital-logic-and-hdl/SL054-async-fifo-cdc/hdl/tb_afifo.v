`timescale 1ns/1ps
module tb;
  parameter integer RPCT = 100;
  reg wclk = 0, rclk = 0, rst = 1, we = 0, re = 0; reg [15:0] wd = 0; wire [15:0] rd; wire full, empty;
  afifo #(16, 4) f(wclk, rst, we, wd, full, rclk, rst, re, rd, empty);
  always #10 wclk = ~wclk;
  always #13.5 rclk = ~rclk;
  integer written = 0, readn = 0, errs = 0, fullcyc = 0, emptycyc = 0, seed = 11;
  reg [15:0] expectv = 0; time t0, t1;
  always @(posedge wclk) if (!rst) begin
    if (we && !full) begin written = written + 1; wd <= wd + 1; end
    if (full) fullcyc = fullcyc + 1;
    we <= (written < 5000) && (($random(seed) % 100 + 100) % 100 < 70);
  end
  always @(posedge rclk) if (!rst) begin
    if (re && !empty) begin
      if (rd !== expectv) errs = errs + 1;
      expectv = expectv + 1; readn = readn + 1;
      if (readn == 100) t0 = $time;
      if (readn == 4900) t1 = $time;
    end
    if (empty) emptycyc = emptycyc + 1;
    re <= (($random(seed) % 100 + 100) % 100 < RPCT);
  end
  initial begin
    #100 rst = 0;
    wait (readn == 5000);
    $display("RES errors %0d", errs);
    $display("RES written %0d", written);
    $display("RES read %0d", readn);
    $display("RES rate %0f", 4800.0 / ((t1 - t0) * 1e-9));
    $display("RES full_cycles %0d", fullcyc);
    $display("RES empty_cycles %0d", emptycyc);
    $finish;
  end
endmodule
