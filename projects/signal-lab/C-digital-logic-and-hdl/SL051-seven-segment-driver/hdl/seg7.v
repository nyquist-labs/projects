module hex7(input [3:0] h, output reg [6:0] seg);  // {g,f,e,d,c,b,a}, active high
  always @* case (h)
    4'h0: seg = 7'b0111111; 4'h1: seg = 7'b0000110; 4'h2: seg = 7'b1011011; 4'h3: seg = 7'b1001111;
    4'h4: seg = 7'b1100110; 4'h5: seg = 7'b1101101; 4'h6: seg = 7'b1111101; 4'h7: seg = 7'b0000111;
    4'h8: seg = 7'b1111111; 4'h9: seg = 7'b1101111; 4'hA: seg = 7'b1110111; 4'hB: seg = 7'b1111100;
    4'hC: seg = 7'b0111001; 4'hD: seg = 7'b1011110; 4'hE: seg = 7'b1111001; 4'hF: seg = 7'b1110001;
  endcase
endmodule
module mux7 #(parameter K = 16)(input clk, rst, input [15:0] val, output [6:0] seg, output reg [3:0] an);
  reg [K+1:0] cnt; wire [1:0] sel = cnt[K+1:K];
  always @(posedge clk) if (rst) cnt <= 0; else cnt <= cnt + 1;
  always @* an = 4'b0001 << sel;
  hex7 d(val[sel*4 +: 4], seg);
endmodule
