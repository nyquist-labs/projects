module c0(input wire i0, i1, output wire o0, o1, o2);
  wire g0 = ~(i0 & i1 & i1);
  wire g1 = ~(g0 ^ i1);
  wire g2 = ~i0;
  wire g3 = g0 ^ g2;
  wire g4 = ~(g0 & g2 & g3);
  wire g5 = ~g0;
  assign o0 = g5;
  assign o1 = g4;
  assign o2 = g3;
endmodule
