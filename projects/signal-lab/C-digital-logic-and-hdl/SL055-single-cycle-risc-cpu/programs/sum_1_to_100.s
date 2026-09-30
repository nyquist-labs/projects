li t0, 0
    li t1, 1
    li t2, 101
loop:
    add t0, t0, t1
    addi t1, t1, 1
    bne t1, t2, loop
    sw t0, 0(x0)
halt: j halt
