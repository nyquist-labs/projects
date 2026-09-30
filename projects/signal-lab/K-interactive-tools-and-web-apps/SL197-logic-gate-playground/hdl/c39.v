module c39(input wire a, b, output wire y);
  wire n1 = ~(a & b);
  wire n2 = ~(a & n1);
  wire n3 = ~(b & n1);
  wire n4 = ~(n2 & n3);
  assign y = n4;
endmodule
