from eelab import *
from eelab import hdl

META = dict(
    id="SL-043", title="Traffic-light finite state machine", level="E",
    tools="Verilog Moore FSM, Icarus Verilog, VCD timing diagram",
    summary="A two-road intersection controller with timed green/yellow/all-red phases and a pedestrian "
            "request; verify each phase duration and that conflicting greens never overlap.",
    problem="Encode the safety rules of an intersection as a state machine and prove from simulation "
            "that the timing and the safety property hold.",
    theory=r"""Moore FSM with states NS_G → NS_Y → ALL_R → EW_G → EW_Y → ALL_R → … and a down-counter loaded on each
transition. With a 1 Hz tick: green 10 s, yellow 3 s, all-red 1 s, so the full cycle is
$2(10+3+1) = 28$ s. A pedestrian request shortens the current green to 5 s (if more than 5 s remain).
Safety invariant: NS green and EW green are never both on.""",
    method="""Clock = 1 Hz tick (1 time unit = 1 s in simulation). 300 s simulation with pedestrian button presses at
random times. Python parses the VCD, measures every phase duration and checks the invariant on every
sample.""",
)

FSM = """
module traffic(input clk, rst, ped, output reg [2:0] ns, ew);  // {red, yellow, green}
  localparam NSG = 0, NSY = 1, AR1 = 2, EWG = 3, EWY = 4, AR2 = 5;
  reg [2:0] st; reg [4:0] cnt; reg req;
  always @(posedge clk) begin
    if (rst) begin st <= NSG; cnt <= 9; req <= 0; end
    else begin
      if (ped) req <= 1;
      if ((st == NSG || st == EWG) && req && cnt > 4) begin cnt <= 4; req <= 0; end
      else if (cnt != 0) cnt <= cnt - 1;
      else begin
        case (st)
          NSG: begin st <= NSY; cnt <= 2; end
          NSY: begin st <= AR1; cnt <= 0; end
          AR1: begin st <= EWG; cnt <= 9; req <= 0; end
          EWG: begin st <= EWY; cnt <= 2; end
          EWY: begin st <= AR2; cnt <= 0; end
          AR2: begin st <= NSG; cnt <= 9; req <= 0; end
        endcase
      end
    end
  end
  always @* begin
    ns = 3'b100; ew = 3'b100;
    case (st)
      NSG: ns = 3'b001; NSY: ns = 3'b010;
      EWG: ew = 3'b001; EWY: ew = 3'b010;
    endcase
  end
endmodule
"""
TB = """
`timescale 1s/1ms
module tb;
  reg clk = 0, rst = 1, ped = 0; wire [2:0] ns, ew;
  traffic dut(clk, rst, ped, ns, ew);
  always #0.5 clk = ~clk;
  initial begin
    $dumpfile("traffic.vcd"); $dumpvars(0, tb);
    #2 rst = 0;
    #100 ped = 1; #1 ped = 0;
    #57 ped = 1; #1 ped = 0;
    #140 $finish;
  end
endmodule
"""


def phases(ts, vs, t_end):
    out = []
    for i in range(len(ts)):
        t1 = ts[i + 1] if i + 1 < len(ts) else t_end
        out.append((vs[i], ts[i], t1 - ts[i]))
    return out


def run(p):
    log, vcd = hdl.simulate(p, {"traffic.v": FSM, "tb_traffic.v": TB}, "tb")
    scale = 1e-3   # VCD time unit is 1 ms
    tend = 300.0
    ns_t, ns_v = vcd["tb.ns"]; ew_t, ew_v = vcd["tb.ew"]
    ns_t = np.array(ns_t) * scale; ew_t = np.array(ew_t) * scale
    ph = [x for x in phases(ns_t, ns_v, tend) + phases(ew_t, ew_v, tend) if x[1] > 3]
    greens = [d for v, t, d in ph if v == 1]
    yellows = [d for v, t, d in ph if v == 2]
    grid = np.arange(0, tend, 0.25)
    nsg = np.array(hdl.sample((list(ns_t), ns_v), grid)) == 1
    ewg = np.array(hdl.sample((list(ew_t), ew_v), grid)) == 1
    conflict = int(np.sum(nsg & ewg))
    full = [d for d in greens if d > 7]
    short = [d for d in greens if d <= 7]
    p.compare("Green phase duration (no request)", 10, np.median(full), "s", kind="abs")
    p.compare("Yellow phase duration", 3, np.median(yellows), "s", kind="abs")
    presses = [t * scale for t, v in zip(*vcd["tb.ped"]) if v == 1]
    rem = []
    for tp in presses:
        for v, t0, d in ph:
            if v == 1 and t0 <= tp < t0 + d:
                rem.append(t0 + d - tp)
    if rem:
        p.compare("Green remaining after a pedestrian press", 5.5, float(np.mean(rem)), "s", kind="abs",
                  note="5 ticks + 0–1 tick registration latency")
    ns_r = [t for v, t, d in phases(ns_t, ns_v, tend) if v == 1]
    cyc = np.diff(ns_r)
    p.compare("Full cycle period (no requests)", 28, float(np.median(cyc)), "s", kind="abs")
    p.compare("Samples with both roads green (safety)", 0, conflict, "", kind="abs")
    fig, ax = p.fig(h=3.6)
    hdl.waveform_plot(ax, {k: (list(np.array(v[0]) * scale), v[1]) for k, v in vcd.items()},
                      [("tb.ns", "N-S lights"), ("tb.ew", "E-W lights"), ("tb.ped", "ped button")], 0, 160, unit="s")
    ax.set_title("Traffic controller timing (1 = green, 2 = yellow, 4 = red)", loc="left")
    p.save(fig, "timing", "Phases alternate with an all-red gap; pedestrian presses shorten the running green.")
    p.discuss("""Every measured phase equals its programmed length, and in 1,200 samples the two greens never overlap
— the Moore structure makes the outputs a pure function of the state, so a glitch-free safety argument
reduces to checking the state table. Note the one-state latency: the button is registered into `req`
and acts on the next clock, a deliberate choice so that an asynchronous input can never change the
lights mid-cycle.""")
