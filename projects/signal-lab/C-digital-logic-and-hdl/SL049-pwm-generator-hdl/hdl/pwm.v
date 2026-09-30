module pwm #(parameter N = 8)(input clk, rst, input [N:0] cmp_in, output reg out);
  reg [N-1:0] cnt; reg [N:0] cmp;
  always @(posedge clk) begin
    if (rst) begin cnt <= 0; cmp <= 0; out <= 0; end
    else begin
      cnt <= cnt + 1;
      if (cnt == {N{1'b1}}) cmp <= cmp_in;     // double-buffered update at wrap
      out <= ({1'b0, cnt + 1'b1} < ((cnt == {N{1'b1}}) ? cmp_in : cmp));
    end
  end
endmodule
