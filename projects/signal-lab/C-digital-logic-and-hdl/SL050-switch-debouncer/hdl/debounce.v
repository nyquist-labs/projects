module debounce #(parameter N = 10)(input clk, tick, rst, in, output reg out);
  reg [1:0] sync; reg [7:0] cnt;
  always @(posedge clk) begin
    sync <= {sync[0], in};
    if (rst) begin out <= 0; cnt <= 0; end
    else if (tick) begin
      if (sync[1] == out) cnt <= 0;
      else if (cnt == N - 1) begin out <= sync[1]; cnt <= 0; end
      else cnt <= cnt + 1;
    end
  end
endmodule
