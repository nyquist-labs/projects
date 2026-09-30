module spi_master #(parameter DIV = 5)(input clk, rst, start, input [7:0] tx, output reg [7:0] rx,
                                        output reg done, output reg sclk, output reg mosi, output reg cs, input miso);
  reg [7:0] sh; reg [3:0] n; reg [15:0] c; reg act;
  always @(posedge clk) begin
    done <= 0;
    if (rst) begin sclk <= 0; cs <= 1; act <= 0; mosi <= 0; end
    else if (!act && start) begin act <= 1; cs <= 0; sh <= tx; mosi <= tx[7]; n <= 0; c <= 0; end
    else if (act) begin
      if (c == DIV - 1) begin
        c <= 0;
        if (!sclk) begin sclk <= 1; rx <= {rx[6:0], miso}; end     // rising: sample
        else begin
          sclk <= 0;                                               // falling: shift
          if (n == 7) begin act <= 0; cs <= 1; done <= 1; end
          else begin n <= n + 1; sh <= {sh[6:0], 1'b0}; mosi <= sh[6]; end
        end
      end else c <= c + 1;
    end
  end
endmodule
