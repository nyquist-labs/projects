module c38(input wire s, d0, d1, output wire y);
  wire n1 = ~s;
  wire a0 = n1 & d0;
  wire a1 = s & d1;
  wire o1 = a0 | a1;
  assign y = o1;
endmodule
