module rv_pipe(input clk, rst);
  reg [31:0] imem [0:255]; reg [31:0] dmem [0:255]; reg [31:0] x [0:31];
  integer i; initial for (i = 0; i < 32; i = i + 1) x[i] = 0;
  // ---------------- pipeline registers
  reg [31:0] pc, d_pc, d_ins; reg d_v;
  reg [31:0] e_pc, e_ins, e_a, e_b; reg e_v;
  reg [31:0] m_alu, m_b, m_ins; reg m_v;
  reg [31:0] w_val, w_ins; reg w_v;
  // ---------------- helpers
  function uses_rs1(input [31:0] ins); uses_rs1 = !(ins[6:0] == 7'h6F || ins[6:0] == 7'h37); endfunction
  function uses_rs2(input [31:0] ins); uses_rs2 = (ins[6:0] == 7'h33 || ins[6:0] == 7'h23 || ins[6:0] == 7'h63); endfunction
  function writes(input [31:0] ins); writes = !(ins[6:0] == 7'h23 || ins[6:0] == 7'h63) && ins[11:7] != 0; endfunction
  // ---------------- ID: register read with WB bypass
  wire [4:0] d_rs1 = d_ins[19:15], d_rs2 = d_ins[24:20];
  wire [31:0] rf1 = (w_v && writes(w_ins) && w_ins[11:7] == d_rs1) ? w_val : x[d_rs1];
  wire [31:0] rf2 = (w_v && writes(w_ins) && w_ins[11:7] == d_rs2) ? w_val : x[d_rs2];
  wire load_use = e_v && e_ins[6:0] == 7'h03 && e_ins[11:7] != 0 && d_v &&
                  ((uses_rs1(d_ins) && e_ins[11:7] == d_rs1) || (uses_rs2(d_ins) && e_ins[11:7] == d_rs2));
  // ---------------- EX with forwarding
  wire [4:0] e_rs1 = e_ins[19:15], e_rs2 = e_ins[24:20];
  wire fwd_m1 = m_v && writes(m_ins) && m_ins[11:7] == e_rs1;
  wire fwd_w1 = w_v && writes(w_ins) && w_ins[11:7] == e_rs1;
  wire fwd_m2 = m_v && writes(m_ins) && m_ins[11:7] == e_rs2;
  wire fwd_w2 = w_v && writes(w_ins) && w_ins[11:7] == e_rs2;
  wire [31:0] a = fwd_m1 ? m_alu : fwd_w1 ? w_val : e_a;
  wire [31:0] b = fwd_m2 ? m_alu : fwd_w2 ? w_val : e_b;
  wire [6:0] opc = e_ins[6:0]; wire [2:0] f3 = e_ins[14:12]; wire [6:0] f7 = e_ins[31:25];
  wire [31:0] imm_i = {{20{e_ins[31]}}, e_ins[31:20]};
  wire [31:0] imm_s = {{20{e_ins[31]}}, e_ins[31:25], e_ins[11:7]};
  wire [31:0] imm_b = {{19{e_ins[31]}}, e_ins[31], e_ins[7], e_ins[30:25], e_ins[11:8], 1'b0};
  wire [31:0] imm_j = {{11{e_ins[31]}}, e_ins[31], e_ins[19:12], e_ins[20], e_ins[30:21], 1'b0};
  wire [31:0] op2 = (opc == 7'h33) ? b : imm_i;
  reg [31:0] alu, ex_val; reg take, jump; reg [31:0] target;
  always @* begin
    case (f3)
      3'd0: alu = (opc == 7'h33 && f7[5]) ? a - op2 : a + op2;
      3'd1: alu = a << op2[4:0];
      3'd2: alu = ($signed(a) < $signed(op2)) ? 1 : 0;
      3'd4: alu = a ^ op2;
      3'd5: alu = a >> op2[4:0];
      3'd6: alu = a | op2;
      default: alu = a & op2;
    endcase
    case (f3)
      3'd0: take = (a == b); 3'd1: take = (a != b);
      3'd4: take = ($signed(a) < $signed(b)); 3'd5: take = ($signed(a) >= $signed(b));
      default: take = 0;
    endcase
    jump = 0; target = 0; ex_val = alu;
    case (opc)
      7'h03: ex_val = a + imm_i;
      7'h23: ex_val = a + imm_s;
      7'h63: begin jump = take; target = e_pc + imm_b; end
      7'h6F: begin jump = 1; target = e_pc + imm_j; ex_val = e_pc + 4; end
      7'h67: begin jump = 1; target = (a + imm_i) & ~32'd1; ex_val = e_pc + 4; end
      7'h37: ex_val = {e_ins[31:12], 12'd0};
    endcase
  end
  wire redirect = e_v && jump;
  // ---------------- clocked pipeline
  always @(posedge clk) begin
    if (rst) begin pc <= 0; d_v <= 0; e_v <= 0; m_v <= 0; w_v <= 0; end
    else begin
      // WB
      if (w_v && writes(w_ins)) x[w_ins[11:7]] <= w_val;
      // MEM -> WB
      w_v <= m_v; w_ins <= m_ins;
      w_val <= (m_ins[6:0] == 7'h03) ? dmem[m_alu[9:2]] : m_alu;
      if (m_v && m_ins[6:0] == 7'h23) dmem[m_alu[9:2]] <= m_b;
      // EX -> MEM
      m_v <= e_v; m_ins <= e_ins; m_alu <= ex_val; m_b <= b;
      // ID -> EX (bubble on load-use or redirect)
      if (redirect || load_use) begin e_v <= 0; e_ins <= 32'h00000013; end
      else begin e_v <= d_v; e_ins <= d_ins; e_pc <= d_pc; e_a <= rf1; e_b <= rf2; end
      // IF -> ID
      if (redirect) begin d_v <= 0; d_ins <= 32'h00000013; pc <= target; end
      else if (!load_use) begin d_v <= 1; d_ins <= imem[pc[9:2]]; d_pc <= pc; pc <= pc + 4; end
    end
  end
endmodule
