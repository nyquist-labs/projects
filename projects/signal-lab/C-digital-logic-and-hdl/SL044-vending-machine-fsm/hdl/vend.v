module vend(input clk, rst, input [2:0] coin, output reg vend, output reg [7:0] change, output reg [7:0] refund, output reg reject);
  // coin: 0 none, 1 nickel, 2 dime, 3 quarter, 4 invalid, 5 cancel
  reg [4:0] credit;  // units of 5 cents
  reg [5:0] c;
  always @(posedge clk) begin
    vend <= 0; change <= 0; refund <= 0; reject <= 0;
    if (rst) credit <= 0;
    else case (coin)
      1, 2, 3: begin
        c = credit + (coin == 1 ? 1 : coin == 2 ? 2 : 5);
        if (c >= 15) begin vend <= 1; change <= (c - 15) * 5; credit <= 0; end
        else credit <= c;
      end
      4: reject <= 1;
      5: begin refund <= credit * 5; credit <= 0; end
      default: ;
    endcase
  end
endmodule
