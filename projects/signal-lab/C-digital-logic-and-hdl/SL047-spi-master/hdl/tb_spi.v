`timescale 1ns/1ps
module slave(input sclk, cs, mosi, output miso);
  reg [7:0] sr = 8'hA5;
  assign miso = sr[7];
  reg [7:0] last;
  always @(posedge sclk) if (!cs) sr <= {sr[6:0], mosi};
endmodule
module tb;
  reg clk = 0, rst = 1, start = 0; reg [7:0] tx; wire [7:0] rx; wire done, sclk, mosi, cs, miso;
  spi_master #(5) m(clk, rst, start, tx, rx, done, sclk, mosi, cs, miso);
  slave s(sclk, cs, mosi, miso);
  always #10 clk = ~clk;
  integer i, errs = 0; reg [7:0] prev;
  initial begin
    $dumpfile("spi.vcd"); $dumpvars(0, tb.sclk, tb.mosi, tb.cs, tb.miso);
    prev = 8'hA5;
    #100 rst = 0;
    for (i = 0; i < 256; i = i + 1) begin
      @(negedge clk); tx = $random; start = 1; @(negedge clk); start = 0;
      @(posedge done); #1;
      if (rx !== prev) errs = errs + 1;
      prev = tx;
      #200;
    end
    $display("RES errors %0d", errs);
    $finish;
  end
endmodule
