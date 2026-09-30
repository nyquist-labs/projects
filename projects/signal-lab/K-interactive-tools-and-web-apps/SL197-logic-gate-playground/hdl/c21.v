module c21(input wire i0, i1, i2, output wire o0, o1, o2);
  wire g0 = ~(i0 | i1);
  wire g1 = i2 & i2;
  wire g2 = ~(g0 ^ i1);
  wire g3 = g0 & g0;
  assign o0 = g3;
  assign o1 = g2;
  assign o2 = g1;
endmodule
