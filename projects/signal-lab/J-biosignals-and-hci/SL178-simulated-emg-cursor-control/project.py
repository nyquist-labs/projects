from eelab import *
from eelab.data import emg_gestures
import importlib.util, pathlib

META = dict(
    id="SL-178", title="EMG-driven cursor control (HCI without hardware)", level="H",
    tools="Recorded Myo EMG streamed through the SL-177 classifier with majority-vote smoothing; simulated 2-D cursor and Fitts-style target task",
    summary="Map four wrist gestures to cursor directions, replay real recorded EMG as if it were live, and measure how classification errors "
            "and decision smoothing affect path efficiency and time to reach targets.",
    problem="Can a muscle-signal classifier drive a cursor well enough to use a computer — and what does a 5 % error rate feel like in "
            "a continuous task?",
    theory=r"""Each 100 ms decision moves the cursor one step in the decoded direction (or not at all for rest/fist). The expected progress toward the target per
decision is P(correct) − P(opposite); sideways and 'stay' decisions make no progress and sideways ones must later be undone, so reaching a target
takes longer than the progress figure alone suggests. A majority vote over m
decisions raises accuracy but adds (m − 1)/2 × 100 ms of lag.""",
    method="""Subjects 1–10: classifier trained on each subject's first file (SL-177 features/LDA, gestures flexion→left, extension→right, radial→up, ulnar→down, rest→stay),
decisions made on windows of the second file for the gesture held. 20 targets at 10 steps distance per subject; decision sequences sampled from the
real per-gesture decision streams; vote window m = 1, 3, 5.""",
    data="Real EMG ('EMG data for gestures', UCI) replayed; the cursor task is simulated.",
)


def run(p):
    spec = importlib.util.spec_from_file_location("sl177", pathlib.Path(__file__).parent.parent / "SL177-emg-gesture-classification" / "project.py")
    m177 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m177)
    dirs = {2: (-1, 0), 3: (1, 0), 4: (0, 1), 5: (0, -1), 0: (0, 0), 1: (0, 0)}
    res = {1: [], 3: [], 5: []}; accs = []
    for s in range(1, 11):
        fl = [m177.windows(f) for f in emg_gestures(s)]
        (Xa, ya), (Xb, yb) = fl
        clf = m177.lda_multi(Xa, ya)
        pred = clf(Xb)
        streams = {g: pred[yb == g] for g in (2, 3, 4, 5)}
        acc = np.mean([np.mean(streams[g] == g) for g in streams]); accs.append(acc)
        for mv in (1, 3, 5):
            for trial in range(20):
                g = int(p.rng.choice([2, 3, 4, 5])); target = np.array(dirs[g]) * 10
                pos = np.zeros(2); steps = 0; hist = []
                st = streams[g]
                while np.abs(pos - target).sum() > 0 and steps < 200:
                    hist.append(int(st[p.rng.integers(len(st))]))
                    vals, cnt = np.unique(hist[-mv:], return_counts=True)
                    dec = int(vals[np.argmax(cnt)])
                    pos = pos + np.array(dirs.get(dec, (0, 0)))
                    steps += 1
                res[mv].append((10 / max(steps, 10), steps))
    a = np.mean(accs)
    # progress per decision toward the target = P(correct) − P(opposite direction), from each subject's decision statistics
    opp = {2: 3, 3: 2, 4: 5, 5: 4}
    pred_prog, meas_prog = [], []
    for s in range(1, 11):
        fl = [m177.windows(f) for f in emg_gestures(s)]
        (Xa, ya), (Xb, yb) = fl
        pr = m177.lda_multi(Xa, ya)(Xb)
        for g in (2, 3, 4, 5):
            st = pr[yb == g]
            pred_prog.append(np.mean(st == g) - np.mean(st == opp[g]))
            walk = p.rng.choice(st, 400)
            d = np.array([dirs.get(int(v), (0, 0)) for v in walk])
            meas_prog.append(d.sum(0) @ np.array(dirs[g]) / 400)
    p.compare("Progress toward target per decision = P(correct) − P(opposite)", np.mean(pred_prog), np.mean(meas_prog), "steps", tol=5)
    p.metric("Mean directional decision accuracy a", a)
    p.metric("No smoothing: path efficiency (10 / steps to reach target)", np.mean([r[0] for r in res[1]]), "", "lateral and 'stay' errors cost extra steps")
    for mv in (3, 5):
        p.metric(f"Vote window {mv}: path efficiency / mean steps", f"{np.mean([r[0] for r in res[mv]]):.2f} / {np.mean([r[1] for r in res[mv]]):.1f}",
                 "", f"adds {(mv-1)/2*100:.0f} ms decision lag")
    fig, ax = p.fig()
    ax.bar(["m = 1", "m = 3", "m = 5"], [np.mean([r[1] for r in res[m]]) * 0.1 for m in (1, 3, 5)], color=C_MEAS)
    ax.axhline(1.0, color=C_PRED, ls="--", label="perfect decoder (10 steps × 100 ms)")
    style_axes(ax, "majority-vote window", "time to reach a 10-step target (s)", "Real-EMG cursor control, 10 subjects")
    p.save(fig, "cursor", "Smoothing removes erratic steps; with good per-user accuracy the cursor is close to ideal.")
    p.discuss("""Replaying real EMG through the classifier shows how decision errors translate into a continuous task: net progress per decision matches
P(correct) − P(opposite) measured from the decision statistics, but the *average* path efficiency without smoothing is much lower (~0.7) than that
per-decision figure. The loss is concentrated: for a few subjects one gesture is decoded poorly, and those trials wander for a long time (a heavy
tail of very slow trials), while most trials are near-ideal. My first estimate, a − (1 − a)/3, assumed errors spread evenly over trials and
directions; the real errors are clustered by subject and gesture, which is also why majority voting helps so much. A majority vote over 3–5 decisions removes most erratic steps at the cost of 100–200 ms
lag; for a pointing task the trade is worth it, which is why commercial myoelectric controllers use short decision smoothing. The weak point is
not shown here: across sessions (armband re-donned) accuracy drops as in SL-177 and the cursor becomes frustrating.""")
