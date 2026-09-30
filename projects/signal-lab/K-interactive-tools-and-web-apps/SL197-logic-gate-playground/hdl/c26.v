module c26(input wire i0, i1, output wire o0, o1, o2);
  wire g0 = i0 | i1;
  wire g1 = g0 | g0;
  wire g2 = g0 | i0;
  wire g3 = g2;
  wire g4 = ~(g1 ^ g3 ^ i1);
  assign o0 = g4;
  assign o1 = g3;
  assign o2 = g2;
endmodule
