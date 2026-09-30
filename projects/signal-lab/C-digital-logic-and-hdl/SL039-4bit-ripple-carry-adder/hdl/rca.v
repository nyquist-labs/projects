`timescale 1ns/1ps
module fa(input a, b, cin, output s, cout);
  wire p, g, t;
  xor #1 (p, a, b); xor #1 (s, p, cin); and #1 (g, a, b); and #1 (t, p, cin); or #1 (cout, g, t);
endmodule
module rca #(parameter N = 4)(input [N-1:0] a, b, output [N-1:0] s, output cout);
  wire [N:0] c; assign c[0] = 1'b0;
  genvar i;
  generate for (i = 0; i < N; i = i + 1) begin : st
    fa u(a[i], b[i], c[i], s[i], c[i+1]);
  end endgenerate
  assign cout = c[N];
endmodule
