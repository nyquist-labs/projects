module uart_rx #(parameter CPS = 27)(input clk, rst, rx, output reg [7:0] data, output reg valid, output reg ferr);
  reg [15:0] cnt; reg [3:0] tick; reg [3:0] bitn; reg [1:0] st; reg [2:0] sync; reg [2:0] maj;
  wire s = sync[2];
  wire vote = (maj[0] & maj[1]) | (maj[1] & maj[2]) | (maj[0] & maj[2]);
  always @(posedge clk) begin
    sync <= {sync[1:0], rx};
    valid <= 0;
    if (rst) begin st <= 0; ferr <= 0; cnt <= 0; end
    else begin
      if (cnt == CPS - 1) cnt <= 0; else cnt <= cnt + 1;
      case (st)
        0: begin ferr <= 0; if (!s) begin st <= 1; tick <= 0; cnt <= 0; end end
        1: if (cnt == CPS - 1) begin            // start bit: confirm at centre
             tick <= tick + 1;
             if (tick >= 6 && tick <= 8) maj <= {maj[1:0], s};
             if (tick == 15) begin
               if (vote) st <= 0; else begin st <= 2; bitn <= 0; tick <= 0; end
             end
           end
        2: if (cnt == CPS - 1) begin
             tick <= tick + 1;
             if (tick >= 6 && tick <= 8) maj <= {maj[1:0], s};
             if (tick == 15) begin
               data <= {vote, data[7:1]}; tick <= 0;
               if (bitn == 7) st <= 3; else bitn <= bitn + 1;
             end
           end
        3: if (cnt == CPS - 1) begin
             tick <= tick + 1;
             if (tick >= 6 && tick <= 8) maj <= {maj[1:0], s};
             if (tick == 9) begin valid <= 1; ferr <= !vote; st <= 0; end
           end
      endcase
    end
  end
endmodule
