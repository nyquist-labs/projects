module c18(input wire i0, i1, output wire o0, o1, o2);
  wire g0 = i0 ^ i0 ^ i0;
  wire g1 = g0;
  wire g2 = g0 & g1 & g1;
  wire g3 = ~(g2 ^ i1);
  wire g4 = g3 ^ g0 ^ i1;
  wire g5 = ~(g3 | g1);
  wire g6 = ~(i0 | g2);
  assign o0 = g6;
  assign o1 = g5;
  assign o2 = g4;
endmodule
