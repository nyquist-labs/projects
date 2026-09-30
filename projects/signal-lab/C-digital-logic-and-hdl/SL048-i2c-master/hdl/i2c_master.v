module i2c_master #(parameter DIV = 125)(input clk, rst, input go, input rw, input [6:0] addr, input [7:0] reg_a,
    input [7:0] wdata, output reg [7:0] rdata, output reg busy, output reg nack, inout sda, inout scl);
  reg sda_o, scl_o;  // 1 = release (high-Z), 0 = pull low
  assign sda = sda_o ? 1'bz : 1'b0;
  assign scl = scl_o ? 1'bz : 1'b0;
  reg [15:0] q; reg [1:0] ph; reg [5:0] st; reg [3:0] bitn; reg [7:0] sh; reg phase_tick;
  always @(posedge clk) begin
    phase_tick <= 0;
    if (rst) begin q <= 0; ph <= 0; end
    else if (busy) begin if (q == DIV - 1) begin q <= 0; ph <= ph + 1; phase_tick <= 1; end else q <= q + 1; end
  end
  // states: 0 idle,1 start,2 byte,3 ack,4 next,5 rstart,6 read byte,7 master nack,8 stop,9 done
  reg [1:0] which;  // which byte: 0 addr+W, 1 reg, 2 data/addr+R
  always @(posedge clk) begin
    if (rst) begin busy <= 0; sda_o <= 1; scl_o <= 1; st <= 0; nack <= 0; end
    else case (st)
      0: if (go) begin busy <= 1; nack <= 0; st <= 1; which <= 0; end
      1: if (phase_tick) case (ph)            // START: SDA low while SCL high
           1: sda_o <= 0;
           2: scl_o <= 0;
           3: begin st <= 2; sh <= {addr, 1'b0}; bitn <= 0; end
         endcase
      2: if (phase_tick) case (ph)            // send bit: set SDA at ph0, SCL high ph1-2, low ph3
           0: sda_o <= sh[7];
           1: scl_o <= 1;
           3: begin scl_o <= 0; sh <= {sh[6:0], 1'b0}; if (bitn == 7) st <= 3; else bitn <= bitn + 1; end
         endcase
      3: if (phase_tick) case (ph)            // ACK from slave
           0: sda_o <= 1;
           1: scl_o <= 1;
           2: if (sda) nack <= 1;
           3: begin scl_o <= 0;
                if (nack) st <= 8;
                else if (which == 0) begin which <= 1; sh <= reg_a; bitn <= 0; st <= 2; end
                else if (which == 1 && !rw) begin which <= 2; sh <= wdata; bitn <= 0; st <= 2; end
                else if (which == 1 && rw) st <= 5;
                else if (which == 3) begin bitn <= 0; st <= 6; end
                else st <= 8;
              end
         endcase
      5: if (phase_tick) case (ph)            // repeated START
           0: sda_o <= 1;
           1: scl_o <= 1;
           2: sda_o <= 0;
           3: begin scl_o <= 0; which <= 3; sh <= {addr, 1'b1}; bitn <= 0; st <= 2; end
         endcase
      6: if (phase_tick) case (ph)            // read bit
           0: sda_o <= 1;
           1: scl_o <= 1;
           2: rdata <= {rdata[6:0], sda};
           3: begin scl_o <= 0; if (bitn == 7) st <= 7; else bitn <= bitn + 1; end
         endcase
      7: if (phase_tick) case (ph)            // master NACK (last byte)
           0: sda_o <= 1;
           1: scl_o <= 1;
           3: begin scl_o <= 0; st <= 8; end
         endcase
      8: if (phase_tick) case (ph)            // STOP
           0: sda_o <= 0;
           1: scl_o <= 1;
           2: sda_o <= 1;
           3: st <= 9;
         endcase
      9: begin busy <= 0; st <= 0; end
    endcase
  end
endmodule
