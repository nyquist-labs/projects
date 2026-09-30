module tb;
  reg [7:0] a, b; reg [2:0] op; wire [7:0] y; wire z, n, c, v;
  alu8 dut(a, b, op, y, z, n, c, v);
  reg hit [0:47]; integer nbins_hit = 0, draws = 0, fails = 0, target, i, seed = 5;
  integer sa, sb; reg [8:0] full; reg [7:0] ey; reg ec;
  function integer bin(input [2:0] o, input [7:0] r, input cc);
    bin = o * 6 + ((r == 0) ? 0 : r[7] ? 1 : 2) * 2 + cc;
  endfunction
  initial begin
    target = 32;
    for (i = 0; i < 48; i = i + 1) hit[i] = 0;
    while (nbins_hit < target && draws < 2000000) begin
      a = $random(seed); b = $random(seed); op = $random(seed); #1;
      sa = $signed(a); sb = $signed(b); ec = 0;
      case (op)
        0: begin full = a + b; ey = full[7:0]; ec = full[8]; end
        1: begin full = a + (~b & 8'hFF) + 1; ey = full[7:0]; ec = full[8]; end
        2: ey = a & b; 3: ey = a | b; 4: ey = a ^ b;
        5: begin ey = a << 1; ec = a[7]; end
        6: begin ey = a >> 1; ec = a[0]; end
        7: ey = (sa < sb) ? 1 : 0;
      endcase
      // immediate assertions
      if (y !== ey) begin fails = fails + 1; if (fails < 4) $display("ASSERT FAIL op=%0d a=%0d b=%0d y=%0d exp=%0d", op, a, b, y, ey); end
      if (z !== (y == 0)) fails = fails + 1;
      if (c !== ec) fails = fails + 1;
      draws = draws + 1;
      if (!hit[bin(op, y, c)]) begin hit[bin(op, y, c)] = 1; nbins_hit = nbins_hit + 1; $display("COV %0d %0d", draws, nbins_hit); end
    end
    $display("RES draws %0d", draws);
    $display("RES bins %0d", nbins_hit);
    $display("RES fails %0d", fails);
    $finish;
  end
endmodule
