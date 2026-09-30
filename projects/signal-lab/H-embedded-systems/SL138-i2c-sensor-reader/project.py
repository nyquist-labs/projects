from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-138", title="I²C temperature-sensor driver with bus capture", level="E",
    tools="C firmware (bit-level I²C master) + simulated TMP102-style sensor on a wired-AND bus, Python protocol decoder",
    summary="Write a TMP102-style driver: pointer-register write, two-byte read, 12-bit two's-complement conversion. The "
            "simulated bus logs every SCL/SDA edge; Python decodes the transactions and checks the temperatures and the "
            "100 kHz timing.",
    problem="Reading a sensor over I²C involves addressing, register pointers, repeated starts and number formats. Get "
            "every layer right and prove it from the bus waveform.",
    theory=r"""TMP102: 12-bit temperature in the upper bits of two bytes, LSB = 0.0625 °C, two's complement for negative values. One read =
START + addr/W + pointer + repeated START + addr/R + 2 data bytes + STOP = 5 bytes × 9 clocks = 45 clocks, plus ≈ 1.5 clock-times
each for START, repeated START and STOP → ≈ 49.5 SCL periods = 0.495 ms at 100 kHz.""",
    method="""Sensor model returns a temperature profile from −25 °C to +125 °C (including 0 and negative values); firmware reads it 40 times. Bus = open-drain AND of
master and slave drivers. Decoder rebuilds bytes from SCL rising edges and START/STOP conditions.""",
)

C = r"""
#include "hal_sim.h"
#define SCL 1
#define SDA 2
static int m_sda = 1, m_scl = 1, s_sda = 1;      /* open-drain drivers: 1 = released */
static double temp_c = 25.0;
static uint8_t ptr = 0, sbuf[2]; static int sbit = 0, sbyte = 0, s_state = 0, s_addr_rw = 0, s_ack = 0, s_shift = 0, s_nbits = 0;
static void bus_update(void) { digitalWrite(SCL, m_scl); digitalWrite(SDA, m_sda && s_sda); }
static void slave_on_scl_rise(void);
static void slave_on_scl_fall(void);
static void half(void) { delay_us(5); }
static void scl(int v) { int old = m_scl; m_scl = v; bus_update(); if (!old && v) slave_on_scl_rise(); if (old && !v) slave_on_scl_fall(); bus_update(); }
static void sda(int v) {
    int bus_old = m_sda && s_sda; m_sda = v; bus_update(); int bus_new = m_sda && s_sda;
    if (m_scl && bus_old && !bus_new) { s_state = 1; s_nbits = 0; s_shift = 0; sbyte = 0; }   /* START */
    if (m_scl && !bus_old && bus_new) { s_state = 0; }                                    /* STOP  */
}
/* ---------------- slave (TMP102-like at 0x48) ---------------- */
static void slave_on_scl_rise(void) {
    if (s_state == 1 || s_state == 2) { s_shift = (s_shift << 1) | (m_sda && s_sda); s_nbits++; }
}
static int reading = 0, rbyte = 0, rbit = 0;
static void slave_on_scl_fall(void) {
    if (s_ack) { s_sda = 1; s_ack = 0; if (reading) { s_nbits = 0; } }
    if (reading && s_state == 3) {
        if (rbit < 8) { s_sda = (sbuf[rbyte] >> (7 - rbit)) & 1; rbit++; }
        else { s_sda = 1; rbit = 0; rbyte++; if (rbyte > 1) { reading = 0; } }
        return;
    }
    if (s_nbits == 8) {
        s_nbits = 0;
        if (sbyte == 0) {
            if ((s_shift >> 1) == 0x48) {
                s_sda = 0; s_ack = 1;
                if (s_shift & 1) {   /* read: load register */
                    int16_t raw = (int16_t)lround(temp_c / 0.0625);
                    uint16_t v = (uint16_t)(raw << 4); sbuf[0] = v >> 8; sbuf[1] = v & 0xFF;
                    reading = 1; rbyte = 0; rbit = 0; s_state = 3;
                } else s_state = 2;
            }
        } else if (s_state == 2) { ptr = (uint8_t)s_shift; s_sda = 0; s_ack = 1; }
        sbyte++; s_shift = 0;
    }
}
/* ---------------- master driver ---------------- */
static void start(void) { sda(1); scl(1); half(); sda(0); half(); scl(0); half(); }
static void stop(void) { sda(0); half(); scl(1); half(); sda(1); half(); }
static int write_byte(uint8_t b) {
    for (int i = 7; i >= 0; i--) { sda((b >> i) & 1); half(); scl(1); half(); scl(0); }
    sda(1); half(); scl(1); int ack = !(m_sda && s_sda); half(); scl(0); return ack;
}
static uint8_t read_byte(int ack) {
    uint8_t b = 0; sda(1);
    for (int i = 0; i < 8; i++) { half(); scl(1); b = (b << 1) | (m_sda && s_sda); half(); scl(0); }
    sda(!ack); half(); scl(1); half(); scl(0); sda(1); return b;
}
static double tmp102_read(void) {
    start(); write_byte(0x48 << 1); write_byte(0x00);
    start(); write_byte((0x48 << 1) | 1);
    uint8_t hi = read_byte(1), lo = read_byte(0); stop();
    int16_t raw = (int16_t)((hi << 8) | lo) >> 4;
    return raw * 0.0625;
}
int main(void) {
    bus_update();
    for (int k = 0; k < 40; k++) {
        temp_c = -25.0 + 150.0 * k / 39.0;
        uint64_t t0 = sim_us;
        double r = tmp102_read();
        printf("T %.4f %.4f %llu\n", temp_c, r, (unsigned long long)(sim_us - t0));
        delay_ms(2);
    }
    return 0;
}
"""


def decode(g):
    ts, vs = g[1]; td, vd = g[2]
    events = sorted([(t, "scl", v) for t, v in zip(ts, vs)] + [(t, "sda", v) for t, v in zip(td, vd)])
    scl = sda = 1; bits = []; frames = []; cur = []
    for t, which, v in events:
        if which == "sda":
            if scl and sda == 1 and v == 0:
                if cur: frames.append(cur)
                cur = ["S"]; bits = []
            elif scl and sda == 0 and v == 1:
                cur.append("P"); frames.append(cur); cur = []; bits = []
            sda = v
        else:
            if v == 1 and scl == 0:
                bits.append(sda)
                if len(bits) == 9:
                    cur.append((int("".join(map(str, bits[:8])), 2), bits[8]))
                    bits = []
            scl = v
    return frames


def run(p):
    log = fwk.run(p, {"tmp102.c": C})
    T = fwk.rows(log, "T")
    err = np.abs(T[:, 1] - T[:, 0])
    p.compare("Max conversion error (12-bit, 0.0625 °C LSB → ≤ 0.03125)", 0.03125, err.max(), "°C", kind="abs")
    p.compare("Negative temperatures decoded correctly (two's complement)", 1, int(np.all(err[T[:, 0] < 0] <= 0.0313)), "", kind="abs")
    p.compare("Transaction time at 100 kHz (5 bytes × 9 + 3 × 1.5 clocks)", 49.5 * 10e-6, np.median(T[:, 2]) * 1e-6, "s", tol=5)
    frames = decode(fwk.gpio(log))
    nbytes = [sum(1 for x in f if isinstance(x, tuple)) for f in frames]
    p.metric("Bus frames decoded (START…START/STOP)", len(frames), "", f"bytes per read transaction: {nbytes[0]} + {nbytes[1]}")
    first = [f"0x{b:02X}{'A' if a == 0 else 'N'}" for b, a in [x for x in frames[0] + frames[1] if isinstance(x, tuple)]]
    p.section("First transaction as decoded from the bus", "`S " + " ".join(first[:2]) + " Sr " + " ".join(first[2:]) + " P`  (A = ACK, N = NACK)")
    g = fwk.gpio(log)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(T[:, 0], T[:, 1] - T[:, 0], "o", color=C_MEAS)
    ax[0].axhline(0.03125, color=C_PRED, ls="--"); ax[0].axhline(-0.03125, color=C_PRED, ls="--", label="±½ LSB")
    style_axes(ax[0], "true temperature (°C)", "read − true (°C)", "Quantisation error")
    t1, v1 = g[1]; t2, v2 = g[2]
    m1 = t1 < 500; m2 = t2 < 500
    ax[1].step(t1[m1], v1[m1] + 1.5, where="post", color=C_MEAS, label="SCL")
    ax[1].step(t2[m2], v2[m2], where="post", color=COLORS[1], label="SDA")
    style_axes(ax[1], "time (µs)", "", "First transaction on the bus")
    p.save(fig, "i2c", "Every reading is within half an LSB; the bus capture shows address, pointer, repeated start and data.")
    p.discuss("""All 40 readings — including negative temperatures, where a sign-extension bug is the classic driver error — are within
half an LSB (0.03 °C) of the true value, and each read takes ~0.5 ms of bus time at 100 kHz, as predicted from the bit count
(my first estimate forgot that the address is sent twice — once to write the pointer, once to read). Decoding the raw SCL/SDA log (rather than trusting the firmware's own view) is what a logic analyser does in the
lab: it shows the ACKs, the repeated START that switches to reading, and the final NACK that tells the sensor to stop.""")
