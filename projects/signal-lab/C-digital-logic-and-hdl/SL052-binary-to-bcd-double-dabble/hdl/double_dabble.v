module dd #(parameter N = 8, D = 3)(input [N-1:0] bin, output reg [4*D-1:0] bcd);
  integer i, j;
  reg [4*D+N-1:0] s;
  always @* begin
    s = 0; s[N-1:0] = bin;
    for (i = 0; i < N; i = i + 1) begin
      for (j = 0; j < D; j = j + 1)
        if (s[N + 4*j +: 4] >= 5) s[N + 4*j +: 4] = s[N + 4*j +: 4] + 3;
      s = s << 1;
    end
    bcd = s[4*D+N-1:N];
  end
endmodule
