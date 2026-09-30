// Battery life from a periodic current profile with sleep modelling.
// profile: [{mA, ms}] repeated forever. Returns average current and runtime including self-discharge and a usable-capacity derating.
function averageCurrent(profile) {
  const T = profile.reduce((s, p) => s + p.ms, 0);
  return profile.reduce((s, p) => s + p.mA * p.ms, 0) / T;         // mA
}
// capacity mAh, derate = usable fraction (cut-off voltage, temperature, ageing), selfPctPerMonth = self-discharge
function runtimeHours(capacity_mAh, profile, derate = 0.85, selfPctPerMonth = 0) {
  const I = averageCurrent(profile);
  const Iself = capacity_mAh * selfPctPerMonth / 100 / (30 * 24);   // self-discharge as an equivalent current (mA)
  return capacity_mAh * derate / (I + Iself);
}
// IoT duty cycle helper: wake every period_s for active_ms at active_mA, plus a tx burst; sleep_uA otherwise
function dutyProfile(period_s, active_ms, active_mA, tx_ms, tx_mA, sleep_uA) {
  return [{ mA: active_mA, ms: active_ms }, { mA: tx_mA, ms: tx_ms }, { mA: sleep_uA / 1000, ms: period_s * 1000 - active_ms - tx_ms }];
}
// which part of the profile dominates the charge budget
function breakdown(profile) {
  const q = profile.map(p => p.mA * p.ms), tot = q.reduce((a, b) => a + b, 0);
  return q.map(x => x / tot);
}
if (typeof module !== "undefined") module.exports = { averageCurrent, runtimeHours, dutyProfile, breakdown };
