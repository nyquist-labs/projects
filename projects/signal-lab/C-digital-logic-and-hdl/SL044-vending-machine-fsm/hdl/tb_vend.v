module tb;
  reg clk = 0, rst = 1; reg [2:0] coin = 0; wire vend, reject; wire [7:0] change, refund;
  vend dut(clk, rst, coin, vend, change, refund, reject);
  integer i, seed = 7, r;
  always #5 clk = ~clk;
  initial begin
    #12 rst = 0;
    for (i = 0; i < 5000; i = i + 1) begin
      @(negedge clk);
      r = $random(seed) & 31;
      coin = (r < 9) ? 1 : (r < 18) ? 2 : (r < 27) ? 3 : (r < 29) ? 4 : (r < 30) ? 5 : 0;
      $display("IN %0d %0d", i, coin);
      @(posedge clk); #1;
      if (vend || refund || reject) $display("EV %0d %0d %0d %0d %0d", i, vend, change, refund, reject);
    end
    $finish;
  end
endmodule
