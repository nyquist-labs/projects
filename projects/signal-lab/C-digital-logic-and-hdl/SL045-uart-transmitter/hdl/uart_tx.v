module uart_tx #(parameter CLKS = 434)(input clk, rst, input [7:0] data, input start, output reg tx, output busy);
  reg [9:0] sh; reg [3:0] n; reg [15:0] cnt; reg act;
  assign busy = act;
  always @(posedge clk) begin
    if (rst) begin tx <= 1; act <= 0; end
    else if (!act && start) begin sh <= {1'b1, data, 1'b0}; n <= 0; cnt <= 0; act <= 1; tx <= 0; end
    else if (act) begin
      if (cnt == CLKS - 1) begin
        cnt <= 0;
        if (n == 9) begin act <= 0; tx <= 1; end
        else begin n <= n + 1; tx <= sh[n + 1]; end
      end else cnt <= cnt + 1;
    end
  end
endmodule
