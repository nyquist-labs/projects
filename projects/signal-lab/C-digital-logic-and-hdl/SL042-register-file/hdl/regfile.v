module regfile(input clk, input we, input [4:0] wa, ra1, ra2, input [31:0] wd, output [31:0] rd1, rd2);
  reg [31:0] r [1:31];
  always @(posedge clk) if (we && wa != 0) r[wa] <= wd;
  // write-through bypass so a same-cycle read sees the value being written
  assign rd1 = (ra1 == 0) ? 32'd0 : (we && wa == ra1) ? wd : r[ra1];
  assign rd2 = (ra2 == 0) ? 32'd0 : (we && wa == ra2) ? wd : r[ra2];
endmodule
