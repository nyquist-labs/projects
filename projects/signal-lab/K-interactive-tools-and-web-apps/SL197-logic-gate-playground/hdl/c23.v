module c23(input wire i0, i1, i2, output wire o0, o1, o2);
  wire g0 = i1 ^ i2 ^ i0;
  wire g1 = ~(g0 | i2 | i2);
  wire g2 = i2 & i2;
  wire g3 = i0 | i1;
  wire g4 = i1;
  wire g5 = i1 | i2;
  wire g6 = ~(g3 ^ g5);
  wire g7 = g5;
  wire g8 = g4 ^ g7 ^ i0;
  wire g9 = ~(g8 ^ g3 ^ i2);
  assign o0 = g9;
  assign o1 = g8;
  assign o2 = g7;
endmodule
