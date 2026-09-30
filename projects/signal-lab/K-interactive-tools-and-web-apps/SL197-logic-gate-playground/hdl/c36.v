module c36(input wire a, b, output wire s, c);
  wire x1 = a ^ b;
  wire a1 = a & b;
  assign s = x1;
  assign c = a1;
endmodule
