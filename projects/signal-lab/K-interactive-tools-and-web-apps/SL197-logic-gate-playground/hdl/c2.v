module c2(input wire i0, i1, i2, i3, i4, output wire o0, o1, o2);
  wire g0 = ~i1;
  wire g1 = i4 | g0;
  wire g2 = ~i2;
  wire g3 = ~(i0 | i2 | g1);
  wire g4 = i1;
  wire g5 = ~(i3 & g3 & g2);
  assign o0 = g5;
  assign o1 = g4;
  assign o2 = g3;
endmodule
