module fa(input a, b, cin, output s, cout); assign {cout, s} = a + b + cin; endmodule
module rcaN #(parameter N = 4)(input [N-1:0] a, b, output [N-1:0] s, output cout);
  wire [N:0] c; assign c[0] = 1'b0;
  genvar i; generate for (i = 0; i < N; i = i + 1) begin : st
    wire p = a[i] ^ b[i];
    assign s[i] = p ^ c[i];
    assign c[i+1] = (a[i] & b[i]) | (p & c[i]);
  end endgenerate
  assign cout = c[N];
endmodule
