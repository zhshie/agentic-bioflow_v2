#!/bin/bash
# cb-D5 (class "regex-dollar-newline", see tests/regex_end_anchor_test.sh): in Python `$`
# also matches just before a trailing "\n", so the validators in scripts/methods_text.py
# (GITHUB_NAME_RE, REV_RE, SHA_RE, IMMUTABLE_REV_RE) accepted "owner/repo\n", "v1.0\n"
# and a 40-hex SHA plus newline, and scripts/collect_provenance.py (TIMESTAMPED, the DOI
# line match) the same. They must end with \Z. Also: methods_text.assets_dir had no caller
# and is gone. Nothing existing: tests/regex_end_anchor_test.sh only counts bare-$ literals.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || { echo "SKIP: no python"; exit 0; }
fails=0
out=$("$PY" -I - "$ROOT/scripts" <<'PYEOF'
import ast, os, sys
sys.dont_write_bytecode = True
scripts = sys.argv[1]
sys.path.insert(0, scripts)
import methods_text as m
import collect_provenance as c
bad = 0
def check(name, cond, detail=""):
    global bad
    print("%-58s %s" % (name, "ok" if cond else "FAIL" + (": " + detail if detail else "")))
    if not cond:
        bad += 1

SHA = "0123456789abcdef0123456789abcdef01234567"
rows = [
    ("GITHUB_NAME_RE", m.GITHUB_NAME_RE, ["nf-core/rnaseq", "a/b.c-d_e"], ["nf-core/rnaseq\n", "a/b\n"]),
    ("REV_RE", m.REV_RE, ["3.14.0", "v1.2.3", "feature/x+y", "dev"], ["3.14.0\n", "dev\n"]),
    ("SHA_RE", m.SHA_RE, [SHA, SHA.upper()], [SHA + "\n", SHA[:39], SHA + "0"]),
    ("IMMUTABLE_REV_RE", m.IMMUTABLE_REV_RE, ["1", "v1.2", "V3.14.0.1"], ["1.2\n", "v3\n", "1.2.3.4.5"]),
    ("TIMESTAMPED", c.TIMESTAMPED, ["params_2026-01-01.json", "execution_report_x.html",
                                     "pipeline_dag_a_b.txt"],
     ["params_2026-01-01.json\n", "execution_trace_x.txt\n", "params_x.csv"]),
]
for name, rx, good, nope in rows:
    for s in good:
        check("%s accepts %r" % (name, s), rx.match(s) is not None)
    for s in nope:
        check("%s rejects %r" % (name, s), rx.match(s) is None)

check("is_immutable rejects a newline tag", not m.is_immutable("v1.2.3\n"))
check("is_immutable accepts a SHA and a tag", m.is_immutable(SHA) and m.is_immutable("v1.2.3"))
g = c.TIMESTAMPED.match("params_run1.json")
check("TIMESTAMPED still groups kind and stamp", g and g.group(1) == "params" and g.group(2) == "run1")

check("methods_text.assets_dir is gone", not hasattr(m, "assets_dir"))

# no re.* literal in either file that starts with ^ and ends with a bare $
for fn in ("methods_text.py", "collect_provenance.py"):
    tree = ast.parse(open(os.path.join(scripts, fn), encoding="utf-8").read())
    hits = []
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "re"
                and n.func.attr in ("compile", "match", "search", "fullmatch") and n.args
                and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
            v = n.args[0].value
            if v.startswith("^") and v.endswith("$") and not v.endswith("\\$"):
                hits.append(v)
    check("%s has no ^...$ literal" % fn, not hits, repr(hits))
sys.exit(1 if bad else 0)
PYEOF
)
rc=$?
echo "$out"
[ "$rc" = 0 ] || fails=1
echo
[ "$fails" = 0 ] && echo "OK: methods_text/collect_provenance end anchors" || { echo "FAIL"; exit 1; }
