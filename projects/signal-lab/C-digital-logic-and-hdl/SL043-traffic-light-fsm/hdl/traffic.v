module traffic(input clk, rst, ped, output reg [2:0] ns, ew);  // {red, yellow, green}
  localparam NSG = 0, NSY = 1, AR1 = 2, EWG = 3, EWY = 4, AR2 = 5;
  reg [2:0] st; reg [4:0] cnt; reg req;
  always @(posedge clk) begin
    if (rst) begin st <= NSG; cnt <= 9; req <= 0; end
    else begin
      if (ped) req <= 1;
      if ((st == NSG || st == EWG) && req && cnt > 4) begin cnt <= 4; req <= 0; end
      else if (cnt != 0) cnt <= cnt - 1;
      else begin
        case (st)
          NSG: begin st <= NSY; cnt <= 2; end
          NSY: begin st <= AR1; cnt <= 0; end
          AR1: begin st <= EWG; cnt <= 9; req <= 0; end
          EWG: begin st <= EWY; cnt <= 2; end
          EWY: begin st <= AR2; cnt <= 0; end
          AR2: begin st <= NSG; cnt <= 9; req <= 0; end
        endcase
      end
    end
  end
  always @* begin
    ns = 3'b100; ew = 3'b100;
    case (st)
      NSG: ns = 3'b001; NSY: ns = 3'b010;
      EWG: ew = 3'b001; EWY: ew = 3'b010;
    endcase
  end
endmodule
