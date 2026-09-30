module tb;
  parameter N = 16; parameter [N-1:0] T = 16'hB400;
  reg clk = 0, rst = 1; wire [N-1:0] s; wire b;
  lfsr #(N, T) u(clk, rst, s, b);
  integer per = 0, f;
  initial begin
    f = $fopen("bits.txt", "w");
    #1 clk = 1; #1 clk = 0; rst = 0;
    forever begin
      $fwrite(f, "%0d", b);
      #1 clk = 1; #1 clk = 0; per = per + 1;
      if (s == 1) begin $display("RES period %0d", per); $fclose(f); $finish; end
    end
  end
endmodule
