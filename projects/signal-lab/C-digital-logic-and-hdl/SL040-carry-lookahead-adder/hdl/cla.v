`timescale 1ns/1ps
module cla4(input [3:0] a, b, input c0, output [3:0] s, output G, P);
  wire [3:0] g, p; wire c1, c2, c3;
  and #1 g0(g[0], a[0], b[0]); and #1 g1(g[1], a[1], b[1]); and #1 g2(g[2], a[2], b[2]); and #1 g3(g[3], a[3], b[3]);
  xor #1 p0(p[0], a[0], b[0]); xor #1 p1(p[1], a[1], b[1]); xor #1 p2(p[2], a[2], b[2]); xor #1 p3(p[3], a[3], b[3]);
  wire t10, t20, t21, t30, t31, t32;
  and #1 (t10, p[0], c0); or #1 (c1, g[0], t10);
  and #1 (t20, p[1], g[0]); and #1 (t21, p[1], p[0], c0); or #1 (c2, g[1], t20, t21);
  and #1 (t30, p[2], g[1]); and #1 (t31, p[2], p[1], g[0]); and #1 (t32, p[2], p[1], p[0], c0); or #1 (c3, g[2], t30, t31, t32);
  wire u0, u1, u2;
  and #1 (u0, p[3], g[2]); and #1 (u1, p[3], p[2], g[1]); and #1 (u2, p[3], p[2], p[1], g[0]); or #1 (G, g[3], u0, u1, u2);
  and #1 (P, p[3], p[2], p[1], p[0]);
  xor #1 s0(s[0], p[0], c0); xor #1 s1(s[1], p[1], c1); xor #1 s2(s[2], p[2], c2); xor #1 s3(s[3], p[3], c3);
endmodule
module lcu4(input [3:0] G, P, input c0, output [4:1] c, output GG, PP);
  wire a1, a2, a3, a4, a5, a6, a7, a8, a9, a10;
  and #1 (a1, P[0], c0); or #1 (c[1], G[0], a1);
  and #1 (a2, P[1], G[0]); and #1 (a3, P[1], P[0], c0); or #1 (c[2], G[1], a2, a3);
  and #1 (a4, P[2], G[1]); and #1 (a5, P[2], P[1], G[0]); and #1 (a6, P[2], P[1], P[0], c0); or #1 (c[3], G[2], a4, a5, a6);
  and #1 (a7, P[3], G[2]); and #1 (a8, P[3], P[2], G[1]); and #1 (a9, P[3], P[2], P[1], G[0]); or #1 (GG, G[3], a7, a8, a9);
  and #1 (PP, P[3], P[2], P[1], P[0]);
  and #1 (a10, PP, c0); or #1 (c[4], GG, a10);
endmodule
module cla16(input [15:0] a, b, input c0, output [15:0] s, output cout, output GG, PP);
  wire [3:0] G, P; wire [4:1] c;
  cla4 b0(a[3:0], b[3:0], c0, s[3:0], G[0], P[0]);
  cla4 b1(a[7:4], b[7:4], c[1], s[7:4], G[1], P[1]);
  cla4 b2(a[11:8], b[11:8], c[2], s[11:8], G[2], P[2]);
  cla4 b3(a[15:12], b[15:12], c[3], s[15:12], G[3], P[3]);
  lcu4 l(G, P, c0, c, GG, PP);
  assign cout = c[4];
endmodule
module add4(input [3:0] a, b, output [3:0] s, output cout);
  wire G, P, t; cla4 u(a, b, 1'b0, s, G, P); assign cout = G;
endmodule
module add8(input [7:0] a, b, output [7:0] s, output cout);
  wire G0, P0, G1, P1, c4, t; cla4 u0(a[3:0], b[3:0], 1'b0, s[3:0], G0, P0);
  assign c4 = G0; cla4 u1(a[7:4], b[7:4], c4, s[7:4], G1, P1);
  and #1 (t, P1, G0); or #1 (cout, G1, t);
endmodule
module add16(input [15:0] a, b, output [15:0] s, output cout);
  wire GG, PP; cla16 u(a, b, 1'b0, s, cout, GG, PP);
endmodule
module add32(input [31:0] a, b, output [31:0] s, output cout);
  wire c16, g0, p0, g1, p1;
  cla16 lo(a[15:0], b[15:0], 1'b0, s[15:0], c16, g0, p0);
  cla16 hi(a[31:16], b[31:16], c16, s[31:16], cout, g1, p1);
endmodule
