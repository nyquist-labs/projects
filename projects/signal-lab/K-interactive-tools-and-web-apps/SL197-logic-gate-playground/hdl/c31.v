module c31(input wire i0, i1, output wire o0, o1, o2);
  wire g0 = i0;
  wire g1 = i1;
  wire g2 = ~i0;
  wire g3 = i1 | g2 | g2;
  wire g4 = g0 & g1 & g2;
  wire g5 = g3 & g0 & i0;
  wire g6 = g4 ^ g4 ^ g2;
  wire g7 = ~(g1 ^ g2 ^ g2);
  wire g8 = g1;
  wire g9 = ~g6;
  assign o0 = g9;
  assign o1 = g8;
  assign o2 = g7;
endmodule
