module alu8(input [7:0] a, b, input [2:0] op, output reg [7:0] y, output z, n, output reg c, v);
  wire [8:0] add = {1'b0, a} + {1'b0, b};
  wire [8:0] sub = {1'b0, a} + {1'b0, ~b} + 9'd1;
  always @* begin
    c = 0; v = 0;
    case (op)
      3'd0: begin y = add[7:0]; c = add[8]; v = (a[7] == b[7]) && (y[7] != a[7]); end
      3'd1: begin y = sub[7:0]; c = sub[8]; v = (a[7] != b[7]) && (y[7] != a[7]); end
      3'd2: y = a & b;
      3'd3: y = a | b;
      3'd4: y = a ^ b;
      3'd5: begin y = a << 1; c = a[7]; end
      3'd6: begin y = a >> 1; c = a[0]; end
      3'd7: begin y = {7'd0, ~sub[8]}; end
    endcase
  end
  assign z = (y == 0);
  assign n = y[7];
endmodule
