module lfsr #(parameter N = 16, parameter [N-1:0] TAPS = 16'hB400)(input clk, rst, output reg [N-1:0] s, output bitout);
  // Galois form: shift right, XOR taps when the LSB is 1
  assign bitout = s[0];
  always @(posedge clk) if (rst) s <= 1; else s <= (s >> 1) ^ (s[0] ? TAPS : {N{1'b0}});
endmodule
