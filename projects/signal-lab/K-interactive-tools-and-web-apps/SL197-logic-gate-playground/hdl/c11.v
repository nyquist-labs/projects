module c11(input wire i0, i1, i2, i3, output wire o0, o1, o2);
  wire g0 = ~(i3 & i2);
  wire g1 = i3 ^ i2;
  wire g2 = ~(i0 ^ g1 ^ g1);
  wire g3 = g0 | i2;
  wire g4 = ~(g2 & g3 & i1);
  wire g5 = i0 | i2;
  wire g6 = g1 ^ i0 ^ g0;
  wire g7 = g6 & g4 & g5;
  wire g8 = g3;
  wire g9 = g7 ^ g8;
  wire g10 = g9;
  assign o0 = g10;
  assign o1 = g9;
  assign o2 = g8;
endmodule
