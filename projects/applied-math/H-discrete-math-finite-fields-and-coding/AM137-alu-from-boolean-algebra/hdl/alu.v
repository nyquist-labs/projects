module alu_slice(input a, b, less, cin, ainv, binv, input [3:0] sel, output y, cout, sum);
  wire a1, b1, g, o, x, t1, m0, m1, m2, m3, o1, o2;
  xor (a1, a, ainv);  xor (b1, b, binv);
  and (g, a1, b1);    or  (o, a1, b1);
  xor (x, a1, b1);    xor (sum, x, cin);
  and (t1, x, cin);   or  (cout, g, t1);
  and (m0, sel[0], g); and (m1, sel[1], o); and (m2, sel[2], sum); and (m3, sel[3], less);
  or  (o1, m0, m1);   or  (o2, m2, m3);   or (y, o1, o2);
endmodule

module alu #(parameter N = 8) (input [N-1:0] a, b, input [3:0] ctl, output [N-1:0] y, output zero, ovf, cout);
  // ctl = {ainv, binv, op[1:0]}: 0000 AND, 0001 OR, 0010 ADD, 0110 SUB, 0111 SLT, 1100 NOR, 1101 NAND
  wire n0, n1, set; wire [3:0] sel; wire [N:0] c; wire [N-1:0] s;
  wire [N-1:0] less = {{(N-1){1'b0}}, set};
  not (n0, ctl[0]); not (n1, ctl[1]);
  and (sel[0], n1, n0); and (sel[1], n1, ctl[0]); and (sel[2], ctl[1], n0); and (sel[3], ctl[1], ctl[0]);
  assign c[0] = ctl[2];
  genvar i;
  generate for (i = 0; i < N; i = i + 1) begin : slices
    alu_slice u(a[i], b[i], less[i], c[i], ctl[3], ctl[2], sel, y[i], c[i+1], s[i]);
  end endgenerate
  xor (ovf, c[N-1], c[N]);
  xor (set, s[N-1], ovf);
  assign cout = c[N];
  // zero flag: balanced OR tree over y (generated for the chosen N)
  wire zt0; or (zt0, y[0], y[1]);
  wire zt1; or (zt1, y[2], y[3]);
  wire zt2; or (zt2, y[4], y[5]);
  wire zt3; or (zt3, y[6], y[7]);
  wire zt4; or (zt4, zt0, zt1);
  wire zt5; or (zt5, zt2, zt3);
  wire zt6; or (zt6, zt4, zt5);
  not (zero, zt6);
endmodule
