from eelab import *
from eelab import hdl

META = dict(
    id="SL-044", title="Vending machine FSM with change and error states", level="E",
    tools="Verilog Mealy/Moore FSM, Icarus Verilog, Python reference model",
    summary="A 75-cent vending machine accepting nickels, dimes and quarters, returning change and "
            "handling a cancel button — checked against a Python model on 5,000 random coin sequences.",
    problem="Turn a vending specification (price, coins, change, refunds, invalid coins) into a state "
            "machine and show it never keeps or invents money.",
    theory=r"""The state is the credit in 5-cent units (0…14 → 15 states). A vend fires when credit ≥ 15 (75 ¢) and change
= credit − 15. Money conservation invariant: $\sum \text{coins in} = 75\cdot\#\text{vends} + \sum\text{change} + \sum\text{refunds}
+ \text{credit held}$. Invalid coins are rejected (returned immediately) without changing state.""",
    method="""Testbench streams random coin codes (nickel/dime/quarter/invalid/cancel), logs every vend, change and
refund event. Python replays the same sequence through an independent model and compares event-by-event,
then checks the conservation invariant.""",
)

VM = """
module vend(input clk, rst, input [2:0] coin, output reg vend, output reg [7:0] change, output reg [7:0] refund, output reg reject);
  // coin: 0 none, 1 nickel, 2 dime, 3 quarter, 4 invalid, 5 cancel
  reg [4:0] credit;  // units of 5 cents
  reg [5:0] c;
  always @(posedge clk) begin
    vend <= 0; change <= 0; refund <= 0; reject <= 0;
    if (rst) credit <= 0;
    else case (coin)
      1, 2, 3: begin
        c = credit + (coin == 1 ? 1 : coin == 2 ? 2 : 5);
        if (c >= 15) begin vend <= 1; change <= (c - 15) * 5; credit <= 0; end
        else credit <= c;
      end
      4: reject <= 1;
      5: begin refund <= credit * 5; credit <= 0; end
      default: ;
    endcase
  end
endmodule
"""
TB = """
module tb;
  reg clk = 0, rst = 1; reg [2:0] coin = 0; wire vend, reject; wire [7:0] change, refund;
  vend dut(clk, rst, coin, vend, change, refund, reject);
  integer i, seed = 7, r;
  always #5 clk = ~clk;
  initial begin
    #12 rst = 0;
    for (i = 0; i < 5000; i = i + 1) begin
      @(negedge clk);
      r = $random(seed) & 31;
      coin = (r < 9) ? 1 : (r < 18) ? 2 : (r < 27) ? 3 : (r < 29) ? 4 : (r < 30) ? 5 : 0;
      $display("IN %0d %0d", i, coin);
      @(posedge clk); #1;
      if (vend || refund || reject) $display("EV %0d %0d %0d %0d %0d", i, vend, change, refund, reject);
    end
    $finish;
  end
endmodule
"""


def model(coins):
    credit, ev = 0, {}
    for i, c in coins:
        if c in (1, 2, 3):
            credit += {1: 1, 2: 2, 3: 5}[c]
            if credit >= 15:
                ev[i] = (1, (credit - 15) * 5, 0, 0); credit = 0
        elif c == 4:
            ev[i] = (0, 0, 0, 1)
        elif c == 5:
            if credit:
                ev[i] = (0, 0, credit * 5, 0)
            credit = 0
    return ev, credit


def run(p):
    log, _ = hdl.simulate(p, {"vend.v": VM, "tb_vend.v": TB}, "tb")
    coins = [tuple(map(int, l.split()[1:])) for l in log.splitlines() if l.startswith("IN")]
    hw = {int(a[0]): tuple(map(int, a[1:])) for a in (l.split()[1:] for l in log.splitlines() if l.startswith("EV"))}
    sw, credit_end = model(coins)
    mism = sum(1 for k in set(hw) | set(sw) if hw.get(k) != sw.get(k))
    p.compare("Event mismatches hardware vs Python model", 0, mism, "", kind="abs")
    val = {1: 5, 2: 10, 3: 25}
    money_in = sum(val.get(c, 0) for _, c in coins)
    vends = sum(e[0] for e in hw.values())
    change = sum(e[1] for e in hw.values())
    refunds = sum(e[2] for e in hw.values())
    p.compare("Money conservation residual (¢)", 0, money_in - (75 * vends + change + refunds + credit_end * 5), "¢", kind="abs")
    p.metric("Coins inserted", sum(1 for _, c in coins if c in (1, 2, 3)))
    p.metric("Items vended", vends)
    p.metric("Invalid coins rejected", sum(e[3] for e in hw.values()))
    ch = [e[1] for e in hw.values() if e[0]]
    fig, ax = p.fig()
    vals, counts = np.unique(ch, return_counts=True)
    ax.bar([str(v) for v in vals], counts, color=C_MEAS)
    style_axes(ax, "change returned (¢)", "vends", "Change distribution over 5,000 random coins", legend=False)
    p.save(fig, "change_hist", "Only 0–20 ¢ change is possible because a quarter can overshoot 75 ¢ by at most 20 ¢.")
    p.discuss("""Hardware and model agree on every event and the conservation law balances to the cent. The change
histogram doubles as a design check: the maximum possible change is 20 ¢ (credit 70 ¢ + a quarter), so an
8-bit change output is generous — and the histogram shows no impossible values.""")
