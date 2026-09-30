`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, start = 0; reg [7:0] data; wire tx, busy;
  uart_tx #(434) dut(clk, rst, data, start, tx, busy);
  always #10 clk = ~clk;
  integer i;
  initial begin
    $dumpfile("tx.vcd"); $dumpvars(0, tb.tx, tb.busy);
    #100 rst = 0;
    for (i = 0; i < 64; i = i + 1) begin
      @(negedge clk); data = $random; start = 1; $display("SENT %0d", data);
      @(negedge clk); start = 0;
      wait (!busy);
    end
    #20000 $finish;
  end
endmodule
