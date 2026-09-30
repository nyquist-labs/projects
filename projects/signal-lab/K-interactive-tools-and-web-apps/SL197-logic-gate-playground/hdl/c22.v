module c22(input wire i0, i1, i2, i3, i4, i5, output wire o0, o1, o2);
  wire g0 = ~(i3 | i2 | i0);
  wire g1 = i3 ^ i2 ^ i5;
  wire g2 = i5 ^ g1 ^ i0;
  wire g3 = ~(i2 | g0);
  wire g4 = ~(g0 & i2);
  wire g5 = i4 ^ g2;
  wire g6 = g4;
  wire g7 = ~(i5 | i2 | g4);
  wire g8 = i1;
  wire g9 = ~g2;
  wire g10 = g5 & g8 & g5;
  wire g11 = g4;
  assign o0 = g11;
  assign o1 = g10;
  assign o2 = g9;
endmodule
