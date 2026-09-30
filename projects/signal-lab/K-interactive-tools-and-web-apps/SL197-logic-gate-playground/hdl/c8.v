module c8(input wire i0, i1, output wire o0, o1, o2);
  wire g0 = ~(i0 & i0);
  wire g1 = i1 | i0 | g0;
  wire g2 = g1 & g0;
  wire g3 = g0;
  wire g4 = i0 | i1;
  wire g5 = g1;
  wire g6 = g4 ^ g4 ^ g2;
  wire g7 = ~(i0 ^ i0);
  wire g8 = ~(i1 & g1);
  wire g9 = g1 & g3 & i1;
  wire g10 = g1 ^ g1;
  wire g11 = ~(g3 | g2);
  assign o0 = g11;
  assign o1 = g10;
  assign o2 = g9;
endmodule
