module tb;
  parameter N = 8;
  reg [N-1:0] a, b; reg [3:0] ctl; wire [N-1:0] y; wire zero, ovf, cout;
  alu #(N) dut(a, b, ctl, y, zero, ovf, cout);
  integer i, j, k, errs, n; reg [N-1:0] ey; reg eo;
  reg [3:0] ops [0:6];
  initial begin
    ops[0] = 0; ops[1] = 1; ops[2] = 2; ops[3] = 6; ops[4] = 7; ops[5] = 12; ops[6] = 13;
    errs = 0; n = 0;
    for (k = 0; k < 7; k = k + 1) for (i = 0; i < (1 << N); i = i + 1) for (j = 0; j < (1 << N); j = j + 1) begin
      a = i; b = j; ctl = ops[k]; eo = 0;
      case (ctl)
        0: ey = a & b;
        1: ey = a | b;
        2: begin ey = a + b; eo = (a[N-1] == b[N-1]) && (ey[N-1] != a[N-1]); end
        6: begin ey = a - b; eo = (a[N-1] != b[N-1]) && (ey[N-1] != a[N-1]); end
        7: ey = ($signed(a) < $signed(b)) ? 1 : 0;
        12: ey = ~(a | b);
        13: ey = ~(a & b);
      endcase
      #1; n = n + 1;
      if (y !== ey || zero !== (ey == 0) || ((ctl == 2 || ctl == 6) && ovf !== eo)) errs = errs + 1;
    end
    $display("RES vectors %0d", n); $display("RES errors %0d", errs); $finish;
  end
endmodule
