#!/bin/bash
# docs/PLATFORM.md says what the platform stores, where, and for how long
# (issue #119 item 1; specs/platform-doc-storage). Document checks only. Every
# assertion carries its TC id (specs/platform-doc-storage/test-case.md).
# Everything is read live from platform/ and extensions/claude-code-kit/settings.json,
# so a change there without a change in the document fails here.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT" || exit 1

PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys' 2>/dev/null; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "FAIL: no python"; exit 1; }

CHECK="$(mktemp)"; WORK="$(mktemp -d)"
trap 'rm -rf "$CHECK" "$WORK"' EXIT
cat > "$CHECK" <<'PYEOF'
import json, re, sys, glob
doc_path, settings_path, only = sys.argv[1], sys.argv[2], sys.argv[3]
fails = []
def bad(tc, msg): fails.append("%s: %s" % (tc, msg))
text = open(doc_path, encoding="utf-8").read()
lines = text.split("\n")

code = ""
for f in glob.glob("platform/**/*.py", recursive=True):
    if "/tests/" in f.replace("\\", "/"): continue
    code += open(f, encoding="utf-8", errors="replace").read() + "\n"
mcp = open("platform/abf_platform/mcp_server.py", encoding="utf-8").read()
writes = set(re.findall(r'name="(\w+)", annotations=_(?:WRITES|STOPS)', mcp))
settings = json.load(open(settings_path))
ask = {a.replace("mcp__abf-platform__", "") for a in settings["permissions"]["ask"]}

def mentioned(par):
    names = set(re.findall(r"`(?:mcp__abf-platform__)?(\w+)`", par))
    return {w for w in writes if w in names}
def mcp_names(par):
    return set(re.findall(r"mcp__abf-platform__(\w+)", par))
def paragraph(anchor):
    for p in re.split(r"\n\s*\n", text):
        if anchor in p: return p
    return None

H = "## What the platform stores"
heads = [i for i, l in enumerate(lines) if l.rstrip() == H]
if only in ("all", "table") and len(heads) != 1:
    bad("TC-001", "heading %r found %d times" % (H, len(heads)))
sec = ""
if heads:
    end = next((j for j in range(heads[0] + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
    sec = "\n".join(lines[heads[0] + 1:end])
rows = []; header = None
for l in sec.split("\n"):
    if l.startswith("|"):
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if header is None: header = cells
        elif not set(l.replace("|", "").strip()) <= set("-: "): rows.append(cells)

if only in ("all", "table"):
    if header != ["What", "Where", "How long"]: bad("TC-002", "header is %r" % (header,))
    if any(len(r) != 3 for r in rows): bad("TC-002", "a row does not have three columns")
    rows = [r for r in rows if len(r) == 3]
    kinds = {"run index": r"run index", "bundle": r"bundle", "job rows": r"job rows",
             "tokens/users/OAuth": r"tokens", "web sessions": r"web sessions",
             "uploads": r"uploads", "fetched records": r"fetched records"}
    found = {}
    for k, pat in kinds.items():
        m = [r for r in rows if re.search(pat, r[0], re.I)]
        if not m: bad("TC-003", "no row for %s" % k)
        else: found[k] = m[0]
    wherecol = " ".join(r[1] for r in rows)
    for name in sorted(set(re.findall(r"`([^`]+)`", wherecol))):
        n = name.rstrip("/").split("/")[-1]
        if n not in code: bad("TC-004", "%r is not in platform/ code" % name)
    for f in ("index.db", "tokens.db", "platform.db", "web_signing.key", "uploads", "records"):
        if ("`%s`" % f) not in wherecol and ("`%s/`" % f) not in wherecol:
            bad("TC-005", "OPERATIONS section 4 file %s is not in a Where cell" % f)
    ri = found.get("run index")
    if ri:
        if "`abf-platform rebuild`" not in ri[2] or not re.search(r"rebuildable", ri[2], re.I):
            bad("TC-006", "run index row: no 'rebuildable' + `abf-platform rebuild`")
        if re.search(r"source of truth", " ".join(ri), re.I): bad("TC-025", "run index called a source of truth")
        if re.search(r"deleted after|removed after|expires", ri[2], re.I): bad("TC-006", "run index given a lifetime")
    b = found.get("bundle")
    if b and (not re.search(r"until the owner forgets", b[2], re.I) or "`abf-platform forget`" not in b[2]):
        bad("TC-007", "bundle row: no 'until the owner forgets' + `abf-platform forget`")
    j = found.get("job rows")
    if j:
        m = re.search(r"PRUNE_AFTER_SECONDS = (\d+) \* 86400", open("platform/abf_platform/jobs.py").read())
        days = int(m.group(1)) if m else -1
        if not re.search(r"\b%d days after the job ends" % days, j[2]):
            bad("TC-008", "job rows row does not say '%s days after the job ends'" % days)
    for k in ("uploads", "fetched records"):
        if k in found and "no automatic deletion" not in found[k][2]:
            bad("TC-010", "%s row does not say 'no automatic deletion'" % k)
    secs = set()
    for f in glob.glob("platform/abf_platform/*.py"):
        for m in re.finditer(r"^\s*[A-Z_]+\s*=\s*(\d+(?:\s*\*\s*\d+)*)\s*(?:#.*)?$", open(f, encoding="utf-8").read(), re.M):
            v = 1
            for x in m.group(1).split("*"): v *= int(x)
            secs.add(v)
    for r in rows:
        for n, unit in re.findall(r"(\d+)\s*(day|hour|minute)s?\b", r[2]):
            v = int(n) * {"day": 86400, "hour": 3600, "minute": 60}[unit]
            if v not in secs: bad("TC-009", "%s %s(s) in row %r has no constant in platform/abf_platform" % (n, unit, r[0]))
    for r in rows:
        h = r[2]
        if not h or re.search(r"\b(TBD|unknown)\b|\?", h) or re.search(r"7d04|59276982|901a5e38|\b(approximately|roughly|usually|about|typically)\b", h, re.I):
            bad("TC-011", "placeholder or guessed period in row %r" % r[0])
        elif not (re.search(r"\d+\s*(day|hour)", h) or re.search(r"\buntil\b", h, re.I) or "no automatic deletion" in h):
            bad("TC-011", "row %r: neither a period, 'until', nor 'no automatic deletion'" % r[0])
    for k in ("tokens/users/OAuth", "web sessions"):
        if k in found and not re.search(r"hash|signed|sha256", " ".join(found[k]), re.I):
            bad("TC-026", "%s row does not say hash/signature" % k)

if only in ("all", "disclosure"):
    paras = [p for p in re.split(r"\n\s*\n", sec) if "`abf-platform forget`" in p and not p.lstrip().startswith("|")]
    if len(paras) != 1:
        bad("TC-013", "%d disclosure paragraphs in the section (want 1)" % len(paras))
    else:
        p = " ".join(paras[0].split())
        n = len([s for s in re.split(r"(?<=[.!?])\s+", p) if s.strip()])
        if n > 3: bad("TC-013", "disclosure has %d sentences (max 3)" % n)
        if not (re.search(r"bundle", p) and re.search(r"screen text", p)): bad("TC-014", "disclosure does not name bundle and screen text")
        if not re.search(r"""add_parser\(\s*["']forget["']""", code): bad("TC-014", "no `forget` subcommand in platform/ code")
        if not re.search(r"not (been )?built yet", p) or not re.search(r"web", p):
            bad("TC-015", "disclosure does not say that showing it in the web/clients is not built yet")

if only in ("all", "lists"):
    s = paragraph("permission `ask` rule for")
    if s is None: bad("TC-016", "no ask-rule sentence")
    else:
        got = mcp_names(s)
        if got != ask: bad("TC-016", "ask sentence names %s, settings.json asks %s; differ: %s" % (sorted(got), sorted(ask), sorted(got ^ ask)))
    if "Two more tools" in text: bad("TC-018", "'Two more tools' is still in the document")
    item2 = next((l for l in lines if l.startswith("2. It **answers questions**")), "")
    if "seven read-only tools" not in item2: bad("TC-018", "item 2 does not say seven read-only tools")
    if not writes: bad("TC-020", "found no write tools in mcp_server.py")
    for tc, anchor in (("TC-018", "2. It **answers questions**"), ("TC-020", "Twelve tools."), ("TC-020", "permission `ask` rule for"),
                       ("TC-019", "The platform's actions live in one place"), ("TC-020", "- **Instructions.**")):
        p = paragraph(anchor)
        if p is None: bad(tc, "no paragraph with %r" % anchor); continue
        miss = writes - mentioned(p)
        if miss: bad(tc, "%r lists the write tools without %s" % (anchor, sorted(miss)))
    if len(re.findall(r"`abf-platform launch\|cancel`", text)) < 3: bad("TC-021", "fewer than three `abf-platform launch|cancel`")

print("\n".join(fails)); sys.exit(1 if fails else 0)
PYEOF

fails=0
ok()  { printf '%-80s ok\n' "$1"; }
bad() { printf '%-80s FAIL\n' "$1"; fails=$((fails+1)); }
run() { "$PY" "$CHECK" "$1" "$2" "$3"; }
DOC=docs/PLATFORM.md; SET=extensions/claude-code-kit/settings.json

if out=$(run "$DOC" "$SET" all); then ok "PLATFORM.md: storage table, disclosure, tool lists (TC-001..021, 025, 026)"
else bad "PLATFORM.md checks"; printf '%s\n' "$out" | sed 's/^/    /'; fi

# TC-012: the table check fails on a name that is not in the code, and says which
sed 's/`index\.db`/`ghost.db`/' "$DOC" > "$WORK/doc1.md"
if out=$(run "$WORK/doc1.md" "$SET" table); then bad "TC-012 a ghost file name passes"
elif grep -q "ghost.db" <<<"$out"; then ok "TC-012 a ghost file name fails and is named"
else bad "TC-012 failed without naming ghost.db"; fi

# TC-017: the ask check reads settings.json live
"$PY" - "$SET" "$WORK/s_extra.json" "$WORK/s_less.json" <<'P'
import json, sys
s = json.load(open(sys.argv[1]))
a = json.loads(json.dumps(s)); a["permissions"]["ask"].append("mcp__abf-platform__foo"); json.dump(a, open(sys.argv[2], "w"))
b = json.loads(json.dumps(s)); b["permissions"]["ask"] = [x for x in b["permissions"]["ask"] if not x.endswith("__forget")]; json.dump(b, open(sys.argv[3], "w"))
P
if out=$(run "$DOC" "$WORK/s_extra.json" lists); then bad "TC-017 a sixth ask tool passes"
elif grep -q "foo" <<<"$out"; then ok "TC-017 a sixth ask tool fails and is named"
else bad "TC-017 failed without naming foo"; fi
if out=$(run "$DOC" "$WORK/s_less.json" lists); then bad "TC-017 a missing forget passes"
elif grep -q "forget" <<<"$out"; then ok "TC-017 a missing forget fails and is named"
else bad "TC-017 failed without naming forget"; fi

# P4: the old absolute sentence contradicted the storage table
if grep -q "It does not delete anything" "$DOC"; then bad "P4 old phrase still present"; else ok "P4 old phrase It does not delete anything is gone"; fi

# TC-026: paths in the document are covered by tests/no_hardcoded_paths.sh (run by run_all.sh)
if [ -f tests/no_hardcoded_paths.sh ]; then ok "TC-026 tests/no_hardcoded_paths.sh exists"; else bad "TC-026 no_hardcoded_paths.sh"; fi

if [ "$fails" -eq 0 ]; then echo "platform_storage_doc_test: all passed"; exit 0; fi
echo "platform_storage_doc_test: $fails FAILED"; exit 1
