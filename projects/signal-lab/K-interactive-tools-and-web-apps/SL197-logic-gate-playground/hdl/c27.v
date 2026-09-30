module c27(input wire i0, i1, i2, i3, i4, i5, output wire o0, o1, o2);
  wire g0 = i5 ^ i2;
  wire g1 = i3 & i1 & i0;
  wire g2 = ~(i0 ^ g1 ^ i1);
  wire g3 = i3 & i1;
  wire g4 = g3;
  wire g5 = ~(g1 | g0 | i4);
  wire g6 = g5 ^ i1 ^ i2;
  wire g7 = ~i2;
  wire g8 = ~(i4 & i1 & g7);
  wire g9 = i1;
  assign o0 = g9;
  assign o1 = g8;
  assign o2 = g7;
endmodule
