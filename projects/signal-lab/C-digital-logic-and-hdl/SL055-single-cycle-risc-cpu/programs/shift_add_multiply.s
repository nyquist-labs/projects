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
