module c3(input wire i0, i1, output wire o0, o1, o2);
  wire g0 = i1 | i1 | i1;
  wire g1 = ~(g0 & i1 & i0);
  wire g2 = ~(g0 | g1 | i0);
  wire g3 = ~(g1 ^ i1 ^ i0);
  wire g4 = g2 | i1 | g1;
  wire g5 = ~(g1 | g4);
  wire g6 = ~(g0 | g5);
  wire g7 = ~g6;
  assign o0 = g7;
  assign o1 = g6;
  assign o2 = g5;
endmodule
