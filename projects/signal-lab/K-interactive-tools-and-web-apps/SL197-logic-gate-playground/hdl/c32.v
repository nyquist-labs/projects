module c32(input wire i0, i1, i2, i3, output wire o0, o1, o2);
  wire g0 = ~(i2 & i0);
  wire g1 = ~(i0 ^ i1 ^ i3);
  wire g2 = ~(g1 ^ i1 ^ i0);
  wire g3 = i2 ^ i1 ^ g0;
  wire g4 = ~(i2 | g3);
  wire g5 = ~(g4 & g3);
  wire g6 = ~(g4 ^ g0);
  wire g7 = ~(i3 ^ i0 ^ g5);
  wire g8 = i2 | g4 | g1;
  assign o0 = g8;
  assign o1 = g7;
  assign o2 = g6;
endmodule
