module tb;
  reg clk = 0, rst = 1;
  rv_pipe cpu(clk, rst);
  integer cycles = 0, i;
  initial begin
    $readmemh("prog.hex", cpu.imem);
    for (i = 0; i < 256; i = i + 1) cpu.dmem[i] = 0;
    $readmemh("data.hex", cpu.dmem);
    #1 clk = 1; #1 clk = 0; rst = 0;
    while (!(cpu.w_v && cpu.w_ins == 32'h0000006F) && cycles < 200000) begin #1 clk = 1; #1 clk = 0; cycles = cycles + 1; end
    #1 clk = 1; #1 clk = 0; cycles = cycles + 1;   // the halt's own write-back cycle
    $display("RES cycles %0d", cycles);
    for (i = 0; i < 32; i = i + 1) $display("REG %0d %0d", i, cpu.x[i]);
    for (i = 0; i < 256; i = i + 1) $display("MEM %0d %0d", i, cpu.dmem[i]);
    $finish;
  end
endmodule
