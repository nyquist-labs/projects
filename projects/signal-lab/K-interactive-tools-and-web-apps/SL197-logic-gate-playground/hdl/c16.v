module c16(input wire i0, i1, i2, i3, i4, i5, output wire o0, o1, o2);
  wire g0 = i4 | i3;
  wire g1 = ~i1;
  wire g2 = i5 | i3;
  wire g3 = ~(g1 & g0 & i0);
  assign o0 = g3;
  assign o1 = g2;
  assign o2 = g1;
endmodule
