module rv_single(input clk, rst, output reg [31:0] pc, output [31:0] ins);
  reg [31:0] imem [0:255]; reg [31:0] dmem [0:255]; reg [31:0] x [0:31];
  assign ins = imem[pc[9:2]];
  wire [6:0] opc = ins[6:0]; wire [4:0] rd = ins[11:7], rs1 = ins[19:15], rs2 = ins[24:20];
  wire [2:0] f3 = ins[14:12]; wire [6:0] f7 = ins[31:25];
  wire [31:0] imm_i = {{20{ins[31]}}, ins[31:20]};
  wire [31:0] imm_s = {{20{ins[31]}}, ins[31:25], ins[11:7]};
  wire [31:0] imm_b = {{19{ins[31]}}, ins[31], ins[7], ins[30:25], ins[11:8], 1'b0};
  wire [31:0] imm_j = {{11{ins[31]}}, ins[31], ins[19:12], ins[20], ins[30:21], 1'b0};
  wire [31:0] imm_u = {ins[31:12], 12'd0};
  wire [31:0] a = x[rs1], b = x[rs2];
  wire [31:0] op2 = (opc == 7'h33) ? b : imm_i;
  reg [31:0] alu;
  always @* case (f3)
    3'd0: alu = (opc == 7'h33 && f7[5]) ? a - op2 : a + op2;
    3'd1: alu = a << op2[4:0];
    3'd2: alu = ($signed(a) < $signed(op2)) ? 1 : 0;
    3'd4: alu = a ^ op2;
    3'd5: alu = a >> op2[4:0];
    3'd6: alu = a | op2;
    default: alu = a & op2;
  endcase
  wire [31:0] addr = a + ((opc == 7'h23) ? imm_s : imm_i);
  reg take;
  always @* case (f3)
    3'd0: take = (a == b); 3'd1: take = (a != b);
    3'd4: take = ($signed(a) < $signed(b)); 3'd5: take = ($signed(a) >= $signed(b));
    default: take = 0;
  endcase
  reg [31:0] npc, wd; reg we;
  always @* begin
    npc = pc + 4; we = 1; wd = alu;
    case (opc)
      7'h33, 7'h13: ;
      7'h03: wd = dmem[addr[9:2]];
      7'h23: we = 0;
      7'h63: begin we = 0; if (take) npc = pc + imm_b; end
      7'h6F: begin wd = pc + 4; npc = pc + imm_j; end
      7'h67: begin wd = pc + 4; npc = (a + imm_i) & ~32'd1; end
      7'h37: wd = imm_u;
      default: we = 0;
    endcase
  end
  integer i;
  initial for (i = 0; i < 32; i = i + 1) x[i] = 0;
  always @(posedge clk) begin
    if (rst) pc <= 0;
    else begin
      pc <= npc;
      if (we && rd != 0) x[rd] <= wd;
      if (opc == 7'h23) dmem[addr[9:2]] <= b;
    end
  end
endmodule
