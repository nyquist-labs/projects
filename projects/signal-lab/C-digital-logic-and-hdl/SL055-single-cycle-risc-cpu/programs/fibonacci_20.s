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
