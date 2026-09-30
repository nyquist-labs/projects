module c34(input wire i0, i1, output wire o0, o1, o2);
  wire g0 = ~(i1 & i0 & i1);
  wire g1 = ~(g0 & i1 & i0);
  wire g2 = ~(i1 & g0);
  wire g3 = ~(g1 ^ i1);
  wire g4 = i0 & i0;
  assign o0 = g4;
  assign o1 = g3;
  assign o2 = g2;
endmodule
