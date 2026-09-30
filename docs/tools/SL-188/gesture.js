// Rule-based hand-gesture classifier on MediaPipe's 21 hand landmarks + pointer smoothing.
// Landmark indices: 0 wrist; thumb 1-4; index 5-8; middle 9-12; ring 13-16; pinky 17-20.
const FINGERS = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16], [17, 18, 19, 20]];
const RATIO = 1.1;   // a finger is "extended" if its tip is RATIO x farther from the wrist than its PIP joint

function dist(a, b) { return Math.hypot(a[0] - b[0], a[1] - b[1]); }

function extended(L) {
  const w = L[0];
  return FINGERS.map((f, i) => {
    if (i === 0) {                       // thumb: tip farther than the thumb MCP joint from the pinky base (folded thumbs cross the palm)
      return dist(L[4], L[17]) > RATIO * dist(L[2], L[17]);
    }
    return dist(L[f[3]], w) > RATIO * dist(L[f[1]], w);
  });
}

function classify(L) {
  const e = extended(L).map(Number).join("");
  const map = { "11111": "open", "00000": "fist", "01000": "point", "01100": "peace", "10000": "thumbs_up", "11000": "L" };
  return map[e] || "unknown";
}

function pinch(L) {                      // pinch distance normalised by palm size (wrist to middle MCP)
  return dist(L[4], L[8]) / dist(L[0], L[9]);
}

function ema(xs, alpha) {                // exponential smoothing of a pointer coordinate stream
  const out = []; let y = xs[0];
  for (const x of xs) { y = alpha * x + (1 - alpha) * y; out.push(y); }
  return out;
}

function classifyMany(list) { return list.map(classify); }

if (typeof module !== "undefined") module.exports = { extended, classify, classifyMany, pinch, ema };
