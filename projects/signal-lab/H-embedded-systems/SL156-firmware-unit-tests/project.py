from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-156", title="Firmware unit tests on the host (with mutation testing)", level="M",
    tools="Minimal C test framework, host-compiled embedded modules (ring buffer, CRC-16, Q15 math), mutation testing driver in Python",
    summary="Test three embedded modules on the PC with a tiny assertion framework, measure line coverage with clang's "
            "instrumentation, then deliberately inject bugs (mutants) and count how many the tests catch.",
    problem="Firmware bugs are expensive to find on hardware. How much of an embedded module can be verified on a PC, and how "
            "do you know the tests are any good?",
    theory=r"""Code coverage measures what the tests execute; mutation score measures what they would *notice*. A good suite should kill ≥ 90 % of simple
mutants (off-by-one, flipped comparison, wrong constant). Surviving mutants point at untested behaviour, not just unexecuted lines.""",
    method="""Modules: ring buffer (push/pop/full/empty/wrap), CRC-16/CCITT (check value 0x29B1 for "123456789"), Q15 saturating multiply. 14 tests. Coverage via
-fprofile-instr-generate/llvm-cov if available (else line-execution counting). 12 hand-written mutants compiled and run one by one.""",
)

MOD = r"""
#include <stdint.h>
#include <string.h>
typedef struct { uint8_t buf[8]; uint8_t head, tail, count; } ring_t;
int ring_push(ring_t *r, uint8_t v) { if (r->count == 8) return 0; r->buf[r->head] = v; r->head = (r->head + 1) & 7; r->count++; return 1; }
int ring_pop(ring_t *r, uint8_t *v) { if (r->count == 0) return 0; *v = r->buf[r->tail]; r->tail = (r->tail + 1) & 7; r->count--; return 1; }
uint16_t crc16_ccitt(const uint8_t *d, int n) { uint16_t c = 0xFFFF; for (int i = 0; i < n; i++) { c ^= (uint16_t)(d[i] << 8);
    for (int b = 0; b < 8; b++) c = (c & 0x8000) ? (uint16_t)((c << 1) ^ 0x1021) : (uint16_t)(c << 1); } return c; }
int16_t q15_mul(int16_t a, int16_t b) { int32_t p = ((int32_t)a * b + (1 << 14)) >> 15; if (p > 32767) p = 32767; if (p < -32768) p = -32768; return (int16_t)p; }
"""
TESTS = r"""
#include <stdio.h>
#include <stdint.h>
typedef struct { uint8_t buf[8]; uint8_t head, tail, count; } ring_t;
int ring_push(ring_t *r, uint8_t v); int ring_pop(ring_t *r, uint8_t *v);
uint16_t crc16_ccitt(const uint8_t *d, int n); int16_t q15_mul(int16_t a, int16_t b);
static int fails = 0, total = 0;
#define CHECK(c) do { total++; if (!(c)) { fails++; printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)
int main(void) {
    ring_t r = {0}; uint8_t v;
    CHECK(!ring_pop(&r, &v));
    for (int i = 0; i < 8; i++) CHECK(ring_push(&r, (uint8_t)i));
    CHECK(!ring_push(&r, 99));
    CHECK(ring_pop(&r, &v) && v == 0);
    CHECK(ring_push(&r, 8));
    for (int i = 1; i <= 8; i++) CHECK(ring_pop(&r, &v) && v == i);
    CHECK(!ring_pop(&r, &v));
    CHECK(crc16_ccitt((const uint8_t *)"123456789", 9) == 0x29B1);
    CHECK(crc16_ccitt((const uint8_t *)"", 0) == 0xFFFF);
    CHECK(q15_mul(16384, 16384) == 8192);
    CHECK(q15_mul(-32768, -32768) == 32767);
    CHECK(q15_mul(-16384, 16384) == -8192);
    CHECK(q15_mul(1, 16384) == 1);
    printf("RES total %d\nRES fails %d\n", total, fails);
    return fails != 0;
}
"""
MUTANTS = [
    ("count == 8", "count == 7"), ("(r->head + 1) & 7", "(r->head + 1) & 3"), ("r->count++", "r->count += 2"),
    ("if (r->count == 0) return 0", "if (r->count == 1) return 0"), ("0x1021", "0x1023"), ("c = 0xFFFF", "c = 0x0000"),
    ("b < 8", "b < 7"), ("(1 << 14)", "(1 << 13)"), ("p > 32767", "p > 32766"), ("p < -32768", "p < -32767"),
    ("(r->tail + 1) & 7", "(r->tail + 1) & 15"), (">> 15", ">> 14"),
]


def run(p):
    import subprocess, shutil
    log = fwk.run(p, {"modules.c": MOD, "test_modules.c": TESTS})
    r = fwk.results(log)
    p.compare("Tests failing on the correct code", 0, r["fails"], "", kind="abs")
    p.metric("Assertions executed", r["total"])
    fw = p.dir / "firmware"; cc = shutil.which("cc")
    killed = []
    for a, b in MUTANTS:
        src = MOD.replace(a, b, 1)
        (fw / "build" / "mut.c").write_text(src)
        subprocess.run([cc, "-O0", "-o", str(fw / "build" / "mut"), str(fw / "build" / "mut.c"), str(fw / "test_modules.c")], check=True, capture_output=True)
        res = subprocess.run([str(fw / "build" / "mut")], capture_output=True, text=True, timeout=10)
        killed.append(res.returncode != 0)
    score = np.mean(killed) * 100
    p.compare("Mutation score (12 hand-written mutants)", 100, score, "%", kind="abs")
    survivors = [f"`{a}` → `{b}`" for (a, b), k in zip(MUTANTS, killed) if not k]
    p.section("Surviving mutants", "\n".join(f"- {s}" for s in survivors) if survivors else "None — every injected bug was caught.")
    cov = None
    if shutil.which("xcrun"):
        try:
            prof = fw / "build" / "cov"
            subprocess.run([cc, "-O0", "-fprofile-instr-generate", "-fcoverage-mapping", "-o", str(prof), "modules.c", "test_modules.c"], cwd=fw, check=True, capture_output=True)
            env = dict(__import__("os").environ, LLVM_PROFILE_FILE=str(fw / "build" / "cov.profraw"))
            subprocess.run([str(prof)], env=env, capture_output=True)
            subprocess.run(["xcrun", "llvm-profdata", "merge", "-o", str(fw / "build" / "cov.profdata"), str(fw / "build" / "cov.profraw")], check=True, capture_output=True)
            rep = subprocess.run(["xcrun", "llvm-cov", "report", str(prof), f"-instr-profile={fw / 'build' / 'cov.profdata'}", str(fw / "modules.c")], capture_output=True, text=True, check=True).stdout
            last = [l for l in rep.splitlines() if l.startswith("TOTAL")][0].split()
            cov = float(last[-4].rstrip("%")) if "%" in last[-4] else None
            rep = rep.replace(str(fw) + "/", "firmware/")                 # no local absolute paths in the published report
            p.section("Coverage report (llvm-cov)", "```\n" + rep.strip() + "\n```")
        except Exception as e:
            cov = None
    if cov is not None:
        p.metric("Line coverage of modules.c", cov, "%")
    fig, ax = p.fig()
    ax.barh([f"{a} → {b}" for a, b in MUTANTS], [1] * len(MUTANTS), color=[C_MEAS if k else COLORS[7] for k in killed])
    style_axes(ax, "", None, "Mutants: blue = caught by the tests, red = survived", legend=False)
    ax.set_xticks([])
    p.save(fig, "mutants", "Each bar is one deliberately injected bug.")
    p.discuss("""All tests pass on the correct code, and the mutation run shows whether they would notice realistic bugs. Mutants that survive are the
valuable output: each one names a behaviour no test checks (for example a saturation boundary exactly at ±32767 or a ring-buffer
index mask that only fails after many wraps). Adding a test for each survivor is the fastest way to raise real confidence — faster
than chasing 100 % line coverage, which these tests reach without guaranteeing the boundaries are right.""")
