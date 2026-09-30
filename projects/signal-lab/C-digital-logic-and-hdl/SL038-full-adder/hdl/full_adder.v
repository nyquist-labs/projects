`timescale 1ns/1ps
module full_adder(input a, input b, input cin, output s, output cout);
  wire p, g, t;
  xor #1 x1(p, a, b);
  xor #1 x2(s, p, cin);
  and #1 a1(g, a, b);
  and #1 a2(t, p, cin);
  or  #1 o1(cout, g, t);
endmodule
