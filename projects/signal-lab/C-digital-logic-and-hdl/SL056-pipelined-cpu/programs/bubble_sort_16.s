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
