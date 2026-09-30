module c20(input wire i0, i1, i2, output wire o0, o1, o2);
  wire g0 = i0;
  wire g1 = i0;
  wire g2 = g1 ^ i0 ^ g0;
  wire g3 = i2 | g0 | i2;
  wire g4 = g2 | i0 | g1;
  wire g5 = g2;
  assign o0 = g5;
  assign o1 = g4;
  assign o2 = g3;
endmodule
