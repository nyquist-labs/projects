`timescale 1us/1ns
module tb;
  reg clk = 0, rst = 1, in = 0, tick = 0; wire out;
  debounce #(10) dut(clk, tick, rst, in, out);
  always #0.5 clk = ~clk;
  integer tc = 0; always @(posedge clk) begin tc = tc + 1; tick <= (tc % 1000 == 0); end
  integer i, k, nb, seed = 3; real gap;
  initial begin
    $dumpfile("db.vcd"); $dumpvars(0, tb.in, tb.out);
    #10 rst = 0; #20000;
    for (i = 0; i < 40; i = i + 1) begin
      nb = 3 + ($random(seed) & 15) + ($random(seed) & 7);
      for (k = 0; k < nb; k = k + 1) begin
        in = ~in; gap = 5 + ($random(seed) & 127);
        #(gap);
      end
      in = (i % 2 == 0) ? 1 : 0;
      $display("LAST %0f", $realtime);
      #40000;
    end
    $finish;
  end
endmodule
