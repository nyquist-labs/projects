from eelab import *
from eelab import hdl

META = dict(
    id="SL-053", title="LFSR pseudorandom generator and its statistics", level="M",
    tools="Verilog Fibonacci LFSRs, Icarus Verilog, NumPy statistics",
    summary="Build 8-, 12- and 16-bit maximal-length LFSRs, measure their periods (2ⁿ−1), and test the "
            "output bitstream for balance, run lengths and autocorrelation.",
    problem="An LFSR is a few flip-flops and XORs, yet its output looks random. Which properties are "
            "guaranteed, and where does the illusion break?",
    theory=r"""With a primitive feedback polynomial the state visits every non-zero n-bit value: period $2^n-1$.
Over one period the output has exactly $2^{n-1}$ ones and $2^{n-1}-1$ zeros; runs of length k occur
$2^{n-k-1}$ times (for k < n−1); the periodic autocorrelation is 1 at lag 0 and exactly $-1/(2^n-1)$ at
every other lag — ideal for spread spectrum. But it is linear: 2n consecutive bits reveal the whole
sequence (Berlekamp–Massey), so it is useless for cryptography.""",
    method="""Taps: x⁸+x⁶+x⁵+x⁴+1, x¹²+x¹¹+x¹⁰+x⁴+1, x¹⁶+x¹⁵+x¹³+x⁴+1. Testbench runs each until the seed state repeats and
dumps the full output sequence; Python checks balance, run-length distribution and autocorrelation, and
runs Berlekamp–Massey to recover the polynomial from 32 bits.""",
)

SRC = """
module lfsr #(parameter N = 16, parameter [N-1:0] TAPS = 16'hB400)(input clk, rst, output reg [N-1:0] s, output bitout);
  // Galois form: shift right, XOR taps when the LSB is 1
  assign bitout = s[0];
  always @(posedge clk) if (rst) s <= 1; else s <= (s >> 1) ^ (s[0] ? TAPS : {N{1'b0}});
endmodule
"""
TB = """
module tb;
  parameter N = 8; parameter [N-1:0] T = 8'hB8;
  reg clk = 0, rst = 1; wire [N-1:0] s; wire b;
  lfsr #(N, T) u(clk, rst, s, b);
  integer per = 0, f;
  initial begin
    f = $fopen("bits.txt", "w");
    #1 clk = 1; #1 clk = 0; rst = 0;
    forever begin
      $fwrite(f, "%0d", b);
      #1 clk = 1; #1 clk = 0; per = per + 1;
      if (s == 1) begin $display("RES period %0d", per); $fclose(f); $finish; end
    end
  end
endmodule
"""


def berlekamp_massey(bits):
    n = len(bits); c = [1] + [0] * n; b = [1] + [0] * n; L, m = 0, -1
    for i in range(n):
        d = bits[i]
        for j in range(1, L + 1):
            d ^= c[j] & bits[i - j]
        if d:
            t = c[:]
            for j in range(n - i + m):
                if i - m + j <= n:
                    c[i - m + j] ^= b[j]
            if L <= i // 2:
                L, m, b = i + 1 - L, i, t
    return L


def run(p):
    cfg = [(8, "8'hB8"), (12, "12'hE08"), (16, "16'hB400")]
    fig, axs = p.fig(1, 2)
    for idx, (n, taps) in enumerate(cfg):
        tb = TB.replace("parameter N = 8; parameter [N-1:0] T = 8'hB8", f"parameter N = {n}; parameter [N-1:0] T = {taps}")
        log, _ = hdl.simulate(p, {"lfsr.v": SRC, "tb_lfsr.v": tb}, "tb")
        r = hdl.results(log)
        bits = np.array([int(c) for c in (p.dir / "hdl" / "bits.txt").read_text().strip()], int)
        (p.dir / "hdl" / "bits.txt").unlink()
        P = 2**n - 1
        p.compare(f"{n}-bit period", P, r["period"], "", kind="abs")
        p.compare(f"{n}-bit ones per period", 2**(n - 1), bits.sum(), "", kind="abs")
        x = 2 * bits - 1.0
        X = np.fft.fft(x)
        ac = np.real(np.fft.ifft(X * np.conj(X))) / len(x)
        p.compare(f"{n}-bit off-peak autocorrelation", -1 / P, float(np.max(np.abs(ac[1:]))) * -1, "", kind="abs")
        L = berlekamp_massey(list(bits[:2 * n + 8]))
        p.compare(f"{n}-bit linear complexity (Berlekamp–Massey)", n, L, "", kind="abs")
        if n == 16:
            ch = np.flatnonzero(np.diff(np.r_[bits[-1] + 7, bits, bits[0] + 7]) != 0)
            runs = np.diff(ch)
            ks = np.arange(1, 12)
            cnt = [np.sum(runs == k) for k in ks]
            axs[0].semilogy(ks, cnt, "o", color=C_MEAS, ms=7, label="measured run counts")
            axs[0].semilogy(ks, 2.0**(n - ks - 1) * 2, "--", color=C_PRED, label="2·2^(n−k−1) (ones + zeros)")
            style_axes(axs[0], "run length k", "number of runs", "16-bit LFSR run lengths")
            axs[1].plot(np.arange(-60, 61), np.r_[ac[-60:], ac[:61]], color=C_MEAS)
            style_axes(axs[1], "lag", "autocorrelation", "Two-valued autocorrelation", legend=False)
            p.csv("runs_16bit", run_length=ks, count=cnt, predicted=2.0**(n - ks - 1) * 2)
    p.save(fig, "statistics", "Run lengths halve with each extra bit; autocorrelation is 1 at lag 0 and −1/(2ⁿ−1) elsewhere.")
    p.write("hdl/README_taps.md", "Galois taps used: 0xB8 (x⁸+x⁶+x⁵+x⁴+1), 0xE08 (x¹²+x¹¹+x¹⁰+x⁴+1), 0xB400 (x¹⁶+x¹⁴+x¹³+x¹¹+1).\n")
    p.discuss("""Every statistical property that follows from the primitive polynomial is reproduced exactly: full
period, one more 1 than 0, run counts halving per length, and the two-valued autocorrelation. The last
row is the catch: Berlekamp–Massey needs only ~2n output bits to recover an equivalent n-stage LFSR, so
predicting the entire 65,535-bit sequence from 40 bits is trivial. LFSRs are excellent for
spreading codes, scramblers and BIST — never for secrets.""")
