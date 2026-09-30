from eelab import *
from eelab import hdl
from eelab.rv32 import assemble, iss
from eelab.rv32_programs import PROGRAMS

META = dict(
    id="SL-055", title="Single-cycle RISC-V (RV32I subset) CPU", level="H",
    tools="Verilog RTL, Python assembler + golden ISA simulator, Icarus Verilog",
    summary="A single-cycle processor that executes real RV32I machine code (ALU, loads/stores, "
            "branches, JAL/JALR): four programs are assembled, run on the Verilog CPU and checked "
            "register-for-register against an independent instruction-set simulator.",
    problem="Build the smallest processor that runs real instructions, and prove it computes exactly what "
            "the ISA specification says.",
    theory=r"""A single-cycle datapath fetches, decodes, executes, accesses memory and writes back in one clock, so
CPI = 1 exactly and cycles = dynamic instruction count. The cost is the clock period: it must cover the
slowest instruction (lw: instruction memory → register read → ALU address add → data memory → write-back
mux). Correctness criterion: after each program, all 31 registers and every data-memory word equal the
golden ISS's final state.""",
    method="""Programs (hand-written RISC-V assembly, assembled by `eelab.rv32`): sum 1…100, first 20 Fibonacci numbers
to memory, bubble sort of 16 signed words, and a shift-and-add multiply subroutine called with JAL/JALR.
The Verilog core loads the machine code with $readmemh, runs until it reaches the `j halt` self-loop,
dumps registers/memory; Python compares with the ISS.""",
)

CPU = """
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
"""
TB = """
module tb;
  reg clk = 0, rst = 1; wire [31:0] pc, ins;
  rv_single cpu(clk, rst, pc, ins);
  integer cycles = 0, i;
  initial begin
    $readmemh("prog.hex", cpu.imem);
    for (i = 0; i < 256; i = i + 1) cpu.dmem[i] = 0;
    $readmemh("data.hex", cpu.dmem);
    #1 clk = 1; #1 clk = 0; rst = 0;
    while (ins !== 32'h0000006F && cycles < 100000) begin #1 clk = 1; #1 clk = 0; cycles = cycles + 1; end
    $display("RES cycles %0d", cycles);
    for (i = 0; i < 32; i = i + 1) $display("REG %0d %0d", i, cpu.x[i]);
    for (i = 0; i < 256; i = i + 1) $display("MEM %0d %0d", i, cpu.dmem[i]);
    $finish;
  end
endmodule
"""


def run_cpu(p, cpu_src, tb_src, name, prog, mem_init):
    words, _ = assemble(prog)
    hexs = "\n".join(f"{w:08x}" for w in words) + "\n"
    data = ["00000000"] * 256
    for k, v in mem_init.items():
        data[k] = f"{v & 0xFFFFFFFF:08x}"
    (p.dir / "hdl").mkdir(exist_ok=True)
    (p.dir / "hdl" / "prog.hex").write_text(hexs)
    (p.dir / "hdl" / "data.hex").write_text("\n".join(data) + "\n")
    p.write(f"programs/{name}.s", prog.strip() + "\n", "RISC-V assembly")
    p.write(f"programs/{name}.hex", hexs, "machine code")
    log, _ = hdl.simulate(p, {"cpu.v": cpu_src, "tb_cpu.v": tb_src}, "tb")
    r = hdl.results(log)
    regs = [int(l.split()[2]) for l in log.splitlines() if l.startswith("REG")]
    mem = [int(l.split()[2]) for l in log.splitlines() if l.startswith("MEM")]
    gx, gm, trace = iss(words, mem_init)
    reg_err = sum(a != (b & 0xFFFFFFFF) for a, b in zip(regs, gx))
    mem_err = sum(a != (b & 0xFFFFFFFF) for a, b in zip(mem, gm))
    for f in ("prog.hex", "data.hex"):
        (p.dir / "hdl" / f).unlink()
    return r, reg_err, mem_err, trace, gx, gm


def run(p):
    from eelab.rv32_programs import SORT_DATA
    counts = []
    for name, (prog, mem_init) in PROGRAMS.items():
        r, re_, me_, trace, gx, gm = run_cpu(p, CPU, TB, name, prog, mem_init)
        p.compare(f"{name}: register mismatches vs ISS", 0, re_, "", kind="abs")
        p.compare(f"{name}: memory mismatches vs ISS", 0, me_, "", kind="abs")
        p.compare(f"{name}: cycles (CPI = 1 → dynamic instruction count)", len(trace) - 1, r["cycles"], "cycles", kind="abs")
        counts.append((name, len(trace) - 1))
        if name == "sum_1_to_100":
            p.metric("sum 1..100 stored in mem[0]", gm[0])
        if name == "bubble_sort_16":
            srt = [(v - (1 << 32)) if v >> 31 else v for v in gm[64:80]]
            p.compare("bubble sort output is sorted(input)", 1, int(srt == sorted(SORT_DATA)), "", kind="abs")
        if name == "shift_add_multiply":
            p.compare("123 × 45 via shift-and-add", 5535, gm[2], "", kind="abs")
    fig, ax = p.fig()
    ax.barh([c[0] for c in counts], [c[1] for c in counts], color=C_MEAS)
    style_axes(ax, "cycles (= instructions, CPI = 1)", None, "Dynamic instruction counts of the test programs", legend=False)
    p.save(fig, "cycles", "Each program's cycle count equals its dynamic instruction count on the single-cycle core.")
    p.discuss("""All four programs finish with every register and memory word identical to the independent ISS, and the
cycle count equals the instruction count, i.e. CPI = 1 by construction. The price is the clock period: one
cycle must cover instruction fetch → register read → ALU → data memory → write-back mux, the whole
datapath in series, so the clock must be slow. That is the motivation for the pipelined version in SL-056, which
runs the same programs.""")
