module tb;
  reg clk = 0, we; reg [4:0] wa, ra1, ra2; reg [31:0] wd; wire [31:0] rd1, rd2;
  regfile dut(clk, we, wa, ra1, ra2, wd, rd1, rd2);
  reg [31:0] model [0:31];
  integer i, errs = 0, raw = 0;
  reg [31:0] e1, e2;
  initial begin
    for (i = 0; i < 32; i = i + 1) model[i] = 0;
    // initialise hardware registers
    we = 1; for (i = 1; i < 32; i = i + 1) begin wa = i; wd = 0; #1 clk = 1; #1 clk = 0; end
    for (i = 0; i < 20000; i = i + 1) begin
      we = $random; wa = $random; wd = $random; ra1 = $random; ra2 = (i % 7 == 0) ? wa : $random;
      #1;
      e1 = (ra1 == 0) ? 0 : (we && wa == ra1) ? wd : model[ra1];
      e2 = (ra2 == 0) ? 0 : (we && wa == ra2) ? wd : model[ra2];
      if (we && (wa == ra1 || wa == ra2) && wa != 0) raw = raw + 1;
      if (rd1 !== e1 || rd2 !== e2) errs = errs + 1;
      clk = 1; #1; if (we && wa != 0) model[wa] = wd; clk = 0;
    end
    $display("RES errors %0d", errs);
    $display("RES raw_cases %0d", raw);
    $finish;
  end
endmodule
