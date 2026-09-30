module tb;
  reg [7:0] a, b; reg [2:0] op; wire [7:0] y; wire z, n, c, v;
  alu8 dut(a, b, op, y, z, n, c, v);
  integer i, o, errs, vcount;
  reg [8:0] full; reg [7:0] ey; reg ec, ev;
  integer sa, sb;
  task check; begin
    sa = $signed(a); sb = $signed(b); ec = 0; ev = 0;
    case (op)
      0: begin full = a + b; ey = full[7:0]; ec = full[8]; ev = (sa + sb > 127) || (sa + sb < -128); end
      1: begin full = a + (~b & 8'hFF) + 1; ey = full[7:0]; ec = full[8]; ev = (sa - sb > 127) || (sa - sb < -128); end
      2: ey = a & b; 3: ey = a | b; 4: ey = a ^ b;
      5: begin ey = a << 1; ec = a[7]; end
      6: begin ey = a >> 1; ec = a[0]; end
      7: ey = (sa < sb) ? 1 : 0;
    endcase
    #1;
    if (y !== ey || z !== (ey == 0) || n !== ey[7] || c !== ec || v !== ev) errs = errs + 1;
    if (v) vcount = vcount + 1;
  end endtask
  initial begin
    for (o = 0; o < 8; o = o + 1) begin
      errs = 0; vcount = 0; op = o;
      a = 8'h7F; b = 1; check; a = 8'h80; b = 1; check; a = 8'hFF; b = 1; check; a = 0; b = 0; check;
      for (i = 0; i < 4000; i = i + 1) begin a = $random; b = $random; check; end
      $display("RES errors_op%0d %0d", o, errs);
      $display("RES vfreq_op%0d %0f", o, vcount / 4004.0);
    end
    $finish;
  end
endmodule
