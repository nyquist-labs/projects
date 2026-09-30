module c24(input wire i0, i1, i2, i3, output wire o0, o1, o2);
  wire g0 = ~(i3 & i3 & i3);
  wire g1 = ~(i3 ^ i0 ^ i1);
  wire g2 = ~(i3 | i3);
  wire g3 = ~(i3 & i2);
  wire g4 = g1 & g0;
  wire g5 = i3 & g3;
  wire g6 = i1 & i0 & g1;
  wire g7 = i3 ^ g0 ^ g3;
  assign o0 = g7;
  assign o1 = g6;
  assign o2 = g5;
endmodule
