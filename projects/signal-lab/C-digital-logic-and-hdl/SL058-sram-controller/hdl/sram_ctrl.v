`timescale 1ns/1ps
module sram_ctrl #(parameter W = 3)(input clk, rst, input req, we, input [9:0] addr, input [15:0] wdata,
   output reg [15:0] rdata, output reg done, output reg [9:0] a, inout [15:0] d, output reg ce_n, we_n, oe_n);
  reg [7:0] cnt; reg [1:0] st; reg drive; reg [15:0] dout;
  assign d = drive ? dout : 16'hzzzz;
  always @(posedge clk) begin
    done <= 0;
    if (rst) begin st <= 0; ce_n <= 1; we_n <= 1; oe_n <= 1; drive <= 0; end
    else case (st)
      0: if (req) begin a <= addr; ce_n <= 0; cnt <= 0;
           if (we) begin dout <= wdata; drive <= 1; we_n <= 0; st <= 2; end
           else begin oe_n <= 0; st <= 1; end
         end
      1: if (cnt == W) begin rdata <= d; oe_n <= 1; ce_n <= 1; done <= 1; st <= 3; end else cnt <= cnt + 1;
      2: if (cnt == W) begin we_n <= 1; ce_n <= 1; done <= 1; st <= 3; end else cnt <= cnt + 1;
      3: begin drive <= 0; st <= 0; end
    endcase
  end
endmodule
