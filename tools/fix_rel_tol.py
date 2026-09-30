"""One-off maintenance script: Project.compare(kind='rel') takes its tolerance in PERCENT. A batch of projects was written
with fractional tolerances (0.05 meaning 5 %), which made the README 'within tolerance' column read 'no' for rows that were
fine. This rewrites `tol=<number>` → percent for relative comparisons in the given project files (idempotence is guarded by a
marker comment at the end of each converted file)."""
import ast, sys

MARK = "# tol-convention: relative tolerances are in percent\n"


def convert(path):
    src = open(path).read()
    if MARK in src:
        return 0
    lines = src.split("\n"); edits = []
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "compare":
            kw = {k.arg: k.value for k in n.keywords}
            kind = kw.get("kind")
            if kind is not None and not (isinstance(kind, ast.Constant) and kind.value == "rel"):
                continue
            tol = kw.get("tol")
            if not (isinstance(tol, ast.Constant) and isinstance(tol.value, (int, float))):
                continue
            pred = n.args[1] if len(n.args) > 1 else None
            if isinstance(pred, ast.Constant) and pred.value == 0:
                continue                                   # predicted 0 ⇒ the comparison is absolute anyway
            assert tol.lineno == tol.end_lineno
            edits.append((tol.lineno - 1, tol.col_offset, tol.end_col_offset, f"{tol.value * 100:g}"))
    # ast column offsets are in UTF-8 bytes
    for ln, c0, c1, new in sorted(edits, reverse=True):
        b = lines[ln].encode("utf-8")
        lines[ln] = (b[:c0] + new.encode() + b[c1:]).decode("utf-8")
    out = "\n".join(lines)
    if not out.endswith("\n"):
        out += "\n"
    open(path, "w").write(out + MARK)
    return len(edits)


if __name__ == "__main__":
    total = 0
    for f in sys.argv[1:]:
        total += convert(f)
    print(f"{len(sys.argv) - 1} files, {total} tolerances converted")
