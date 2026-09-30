/* hal_sim.h — a tiny simulated microcontroller HAL for running firmware logic on a PC.
 * Time is simulated in microseconds; every pin change is logged as "G <t_us> <pin> <level>"
 * so a Python "logic analyser" can reconstruct waveforms. Deterministic by construction. */
#ifndef HAL_SIM_H
#define HAL_SIM_H
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static uint64_t sim_us = 0;          /* simulated time */
static uint8_t pin_state[64];
static int log_pins = 1;

static inline uint64_t micros(void) { return sim_us; }
static inline uint64_t millis(void) { return sim_us / 1000; }
static inline void delay_us(uint64_t us) { sim_us += us; }
static inline void delay_ms(uint64_t ms) { sim_us += ms * 1000; }

static inline void digitalWrite(int pin, int v) {
    v = v ? 1 : 0;
    if (pin_state[pin] != v) {
        pin_state[pin] = (uint8_t)v;
        if (log_pins) printf("G %llu %d %d\n", (unsigned long long)sim_us, pin, v);
    }
}
static inline int digitalRead(int pin) { return pin_state[pin]; }

/* deterministic PRNG (xorshift32) for stimulus */
static uint32_t rng_state = 2463534242u;
static inline uint32_t rnd32(void) { uint32_t x = rng_state; x ^= x << 13; x ^= x >> 17; x ^= x << 5; return rng_state = x; }
static inline double rnd01(void) { return (rnd32() >> 8) * (1.0 / 16777216.0); }
static inline double rndn(void) { double u = rnd01() + 1e-12, v = rnd01(); return sqrt(-2 * log(u)) * cos(6.283185307179586 * v); }

#define RES(name, fmt, val) printf("RES %s " fmt "\n", name, val)
#endif
