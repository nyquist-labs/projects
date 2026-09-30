"""Test programs shared by the single-cycle (SL-055) and pipelined (SL-056) RISC-V cores."""

SUM = """
    li t0, 0
    li t1, 1
    li t2, 101
loop:
    add t0, t0, t1
    addi t1, t1, 1
    bne t1, t2, loop
    sw t0, 0(x0)
halt: j halt
"""

FIB = """
    li t0, 0
    li t1, 1
    li a0, 64
    li a1, 20
fib:
    sw t0, 0(a0)
    add t2, t0, t1
    mv t0, t1
    mv t1, t2
    addi a0, a0, 4
    addi a1, a1, -1
    bne a1, x0, fib
halt: j halt
"""

SORT = """
    li s0, 16
outer:
    addi s0, s0, -1
    beq s0, x0, done
    li a0, 256
    mv s1, s0
inner:
    lw t0, 0(a0)
    lw t1, 4(a0)
    blt t0, t1, noswap
    beq t0, t1, noswap
    sw t1, 0(a0)
    sw t0, 4(a0)
noswap:
    addi a0, a0, 4
    addi s1, s1, -1
    bne s1, x0, inner
    j outer
done:
halt: j halt
"""

MUL = """
    li a0, 123
    li a1, 45
    jal ra, mul
    sw a0, 8(x0)
halt: j halt
mul:
    li t0, 0
mloop:
    andi t1, a1, 1
    beq t1, x0, skip
    add t0, t0, a0
skip:
    slli a0, a0, 1
    srli a1, a1, 1
    bne a1, x0, mloop
    mv a0, t0
    jalr x0, ra, 0
"""

SORT_DATA = [37, -5, 901, 12, 0, 44, 7, -200, 63, 18, 5, 99, -1, 250, 3, 71]
PROGRAMS = {"sum_1_to_100": (SUM, {}), "fibonacci_20": (FIB, {}),
            "bubble_sort_16": (SORT, {64 + i: v for i, v in enumerate(SORT_DATA)}),
            "shift_add_multiply": (MUL, {})}
