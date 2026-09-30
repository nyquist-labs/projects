module c9(input wire i0, i1, i2, i3, i4, output wire o0, o1, o2);
  wire g0 = ~(i1 ^ i4 ^ i2);
  wire g1 = ~i4;
  wire g2 = ~(g0 ^ i4);
  wire g3 = i0;
  wire g4 = ~(g3 & g2 & i3);
  wire g5 = g2 & i2 & i3;
  wire g6 = g5 | g1;
  wire g7 = g5;
  wire g8 = ~(g2 ^ g7 ^ g2);
  wire g9 = ~(i1 | g0);
  wire g10 = ~(g7 & i4 & i4);
  wire g11 = ~(g1 | i3 | i4);
  wire g12 = i3;
  wire g13 = g10 ^ g2 ^ g10;
  assign o0 = g13;
  assign o1 = g12;
  assign o2 = g11;
endmodule
