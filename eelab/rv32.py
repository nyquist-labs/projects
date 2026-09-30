"""Tiny RV32I-subset assembler and golden instruction-set simulator (ISS).

Supported: lui addi slti andi ori xori slli srli add sub and or xor slt sll srl lw sw
beq bne blt bge jal jalr (+ pseudo: li (12-bit), mv, j, nop).
"""
from __future__ import annotations

import re

REG = {f"x{i}": i for i in range(32)}
REG.update({"zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4, "t0": 5, "t1": 6, "t2": 7, "s0": 8, "s1": 9,
            "a0": 10, "a1": 11, "a2": 12, "a3": 13, "a4": 14, "a5": 15, "a6": 16, "a7": 17,
            "s2": 18, "s3": 19, "s4": 20, "s5": 21, "t3": 28, "t4": 29, "t5": 30, "t6": 31})
R = {"add": (0, 0x00), "sub": (0, 0x20), "sll": (1, 0), "slt": (2, 0), "xor": (4, 0), "srl": (5, 0),
     "or": (6, 0), "and": (7, 0)}
I = {"addi": 0, "slti": 2, "xori": 4, "ori": 6, "andi": 7, "slli": 1, "srli": 5}
B = {"beq": 0, "bne": 1, "blt": 4, "bge": 5}


def _imm(s, labels, pc):
    s = s.strip()
    if s in labels:
        return labels[s] - pc
    return int(s, 0)


def assemble(src: str):
    lines = []
    for raw in src.splitlines():
        line = raw.split("#")[0].strip()
        if not line:
            continue
        while ":" in line:
            lab, line = line.split(":", 1)
            lines.append(("label", lab.strip()))
            line = line.strip()
        if line:
            lines.append(("ins", line))
    labels, pc = {}, 0
    expanded = []
    for kind, v in lines:
        if kind == "label":
            labels[v] = pc
        else:
            expanded.append((pc, v))
            pc += 4
    words = []
    for pc, line in expanded:
        op, *rest = line.replace(",", " ").split()
        a = [x for x in rest]
        if op == "nop":
            op, a = "addi", ["x0", "x0", "0"]
        elif op == "li":
            op, a = "addi", [a[0], "x0", a[1]]
        elif op == "mv":
            op, a = "addi", [a[0], a[1], "0"]
        elif op == "j":
            op, a = "jal", ["x0", a[0]]
        if op in R:
            f3, f7 = R[op]
            rd, rs1, rs2 = (REG[x] for x in a)
            w = (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x33
        elif op in I:
            rd, rs1 = REG[a[0]], REG[a[1]]
            imm = _imm(a[2], {}, pc) & 0xFFF
            if op in ("slli", "srli"):
                imm &= 0x1F
            w = (imm << 20) | (rs1 << 15) | (I[op] << 12) | (rd << 7) | 0x13
        elif op == "lw" or op == "sw":
            m = re.match(r"(-?\w+)\((\w+)\)", a[1])
            imm, rs1 = int(m.group(1), 0) & 0xFFF, REG[m.group(2)]
            if op == "lw":
                w = (imm << 20) | (rs1 << 15) | (2 << 12) | (REG[a[0]] << 7) | 0x03
            else:
                rs2 = REG[a[0]]
                w = ((imm >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (2 << 12) | ((imm & 31) << 7) | 0x23
        elif op in B:
            rs1, rs2 = REG[a[0]], REG[a[1]]
            off = _imm(a[2], labels, pc) & 0x1FFF
            w = (((off >> 12) & 1) << 31) | (((off >> 5) & 0x3F) << 25) | (rs2 << 20) | (rs1 << 15) | \
                (B[op] << 12) | (((off >> 1) & 0xF) << 8) | (((off >> 11) & 1) << 7) | 0x63
        elif op == "jal":
            rd = REG[a[0]]
            off = _imm(a[1], labels, pc) & 0x1FFFFF
            w = (((off >> 20) & 1) << 31) | (((off >> 1) & 0x3FF) << 21) | (((off >> 11) & 1) << 20) | \
                (((off >> 12) & 0xFF) << 12) | (rd << 7) | 0x6F
        elif op == "jalr":
            rd, rs1 = REG[a[0]], REG[a[1]]
            imm = int(a[2], 0) & 0xFFF if len(a) > 2 else 0
            w = (imm << 20) | (rs1 << 15) | (rd << 7) | 0x67
        elif op == "lui":
            w = ((int(a[1], 0) & 0xFFFFF) << 12) | (REG[a[0]] << 7) | 0x37
        else:
            raise ValueError(f"unknown instruction {line}")
        words.append(w & 0xFFFFFFFF)
    return words, labels


def _sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def iss(words, mem_init=None, max_steps=200000, dmem_words=256):
    """Execute until a 'jal x0, 0' self-loop (halt). Returns (regs, mem, trace)."""
    x = [0] * 32
    mem = [0] * dmem_words
    for k, v in (mem_init or {}).items():
        mem[k] = v & 0xFFFFFFFF
    pc, trace = 0, []
    for _ in range(max_steps):
        w = words[pc // 4]
        if w == 0x0000006F:  # jal x0, 0  -> halt
            trace.append(dict(pc=pc, op="halt", rd=0, rs=(), taken=False, load=False))
            break
        opc, rd, f3 = w & 0x7F, (w >> 7) & 31, (w >> 12) & 7
        rs1, rs2, f7 = (w >> 15) & 31, (w >> 20) & 31, w >> 25
        npc, taken, load, used = pc + 4, False, False, (rs1,)
        if opc == 0x33:
            a, b = x[rs1], x[rs2]
            used = (rs1, rs2)
            if f3 == 0:
                r = a - b if f7 == 0x20 else a + b
            elif f3 == 1:
                r = a << (b & 31)
            elif f3 == 2:
                r = int(_sx(a, 32) < _sx(b, 32))
            elif f3 == 4:
                r = a ^ b
            elif f3 == 5:
                r = (a & 0xFFFFFFFF) >> (b & 31)
            elif f3 == 6:
                r = a | b
            else:
                r = a & b
            wr = r
        elif opc == 0x13:
            imm = _sx(w >> 20, 12)
            a = x[rs1]
            wr = {0: a + imm, 2: int(_sx(a, 32) < imm), 4: a ^ imm, 6: a | imm, 7: a & imm,
                  1: a << (imm & 31), 5: (a & 0xFFFFFFFF) >> (imm & 31)}[f3]
        elif opc == 0x03:
            wr = mem[((x[rs1] + _sx(w >> 20, 12)) & 0xFFFFFFFF) // 4 % dmem_words]
            load = True
        elif opc == 0x23:
            imm = _sx(((w >> 25) << 5) | ((w >> 7) & 31), 12)
            mem[((x[rs1] + imm) & 0xFFFFFFFF) // 4 % dmem_words] = x[rs2] & 0xFFFFFFFF
            rd, wr, used = 0, None, (rs1, rs2)
        elif opc == 0x63:
            imm = _sx((((w >> 31) & 1) << 12) | (((w >> 7) & 1) << 11) | (((w >> 25) & 0x3F) << 5) |
                      (((w >> 8) & 0xF) << 1), 13)
            a, b = _sx(x[rs1], 32), _sx(x[rs2], 32)
            taken = {0: a == b, 1: a != b, 4: a < b, 5: a >= b}[f3]
            if taken:
                npc = pc + imm
            rd, wr, used = 0, None, (rs1, rs2)
        elif opc == 0x6F:
            imm = _sx((((w >> 31) & 1) << 20) | (((w >> 12) & 0xFF) << 12) | (((w >> 20) & 1) << 11) |
                      (((w >> 21) & 0x3FF) << 1), 21)
            wr, npc, taken, used = pc + 4, pc + imm, True, ()
        elif opc == 0x67:
            wr, npc, taken = pc + 4, (x[rs1] + _sx(w >> 20, 12)) & ~1, True
        elif opc == 0x37:
            wr, used = w & 0xFFFFF000, ()
        else:
            raise ValueError(f"bad opcode at {pc:#x}")
        trace.append(dict(pc=pc, rd=rd if wr is not None else 0, rs=tuple(r for r in used if r), taken=taken, load=load))
        if wr is not None and rd:
            x[rd] = wr & 0xFFFFFFFF
        pc = npc
    return x, mem, trace


def pipeline_cycles(trace, branch_penalty=2, load_use=1, fill=4):
    """Predicted cycles for a classic 5-stage pipeline with full forwarding,
    load-use interlock (1 bubble) and branches/jumps resolved in EX (2 flushed slots)."""
    cyc = len(trace) + fill
    stalls = flush = 0
    for prev, cur in zip(trace, trace[1:]):
        if prev["load"] and prev["rd"] and prev["rd"] in cur["rs"]:
            stalls += load_use
    for t in trace:
        if t["taken"] and t.get("op") != "halt":
            flush += branch_penalty
    return cyc + stalls + flush, stalls, flush
