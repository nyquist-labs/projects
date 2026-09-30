module c37(input wire a, b, cin, output wire s, cout);
  wire x1 = a ^ b;
  wire x2 = x1 ^ cin;
  wire a1 = a & b;
  wire a2 = x1 & cin;
  wire o1 = a1 | a2;
  assign s = x2;
  assign cout = o1;
endmodule
