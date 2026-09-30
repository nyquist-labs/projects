module tb;
  parameter N = 12, D = 4;
  reg [N-1:0] b; wire [4*D-1:0] q; integer i, errs = 0, v, k, dec;
  dd #(N, D) u(b, q);
  initial begin
    for (i = 0; i < (1 << N); i = i + 1) begin
      b = i; #1;
      v = i; dec = 0;
      for (k = 0; k < D; k = k + 1) begin dec = dec | ((v % 10) << (4*k)); v = v / 10; end
      if (q !== dec) errs = errs + 1;
    end
    $display("RES errors %0d", errs);
    $finish;
  end
endmodule
