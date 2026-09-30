module clkdiv #(parameter N = 3)(input clk, rst, output out);
  generate if (N % 2 == 0) begin : even
    reg [15:0] c; reg o;
    always @(posedge clk) if (rst) begin c <= 0; o <= 0; end
      else if (c == N/2 - 1) begin c <= 0; o <= ~o; end else c <= c + 1;
    assign out = o;
  end else begin : odd
    reg [15:0] c; reg p, n;
    always @(posedge clk) if (rst) c <= 0; else c <= (c == N - 1) ? 0 : c + 1;
    always @(posedge clk) if (rst) p <= 0; else p <= (c < (N - 1) / 2);
    always @(negedge clk) if (rst) n <= 0; else n <= p;
    assign out = p | n;
  end endgenerate
endmodule
