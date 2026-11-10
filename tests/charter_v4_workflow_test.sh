#!/bin/bash
# Constitution 6.2.0 (charter-v4-workflow): who merges, the v3 base, the protected-path
# review, and the PRODUCT.md / DESIGN.md sync. Checks the words that make the rule a rule.
# TC numbers refer to specs/charter-v4-workflow/test-case.md.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
fails=0

has() { printf '%-70s ' "$1"; if [ -r "$2" ] && grep -qF -- "$3" "$2"; then echo ok; else echo "FAIL: $2 lacks '$3'"; fails=$((fails+1)); fi; }
hasi() { printf '%-70s ' "$1"; if [ -r "$2" ] && grep -qiF -- "$3" "$2"; then echo ok; else echo "FAIL: $2 lacks '$3'"; fails=$((fails+1)); fi; }
lacks() { printf '%-70s ' "$1"; if [ -r "$2" ] && ! grep -qiE -- "$3" "$2"; then echo ok; else echo "FAIL: $2 matches '$3' (or is missing)"; fails=$((fails+1)); fi; }

CO="$ROOT/.specify/memory/constitution.md"
PR="$ROOT/PRODUCT.md"
DE="$ROOT/DESIGN.md"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

# the 6.2.0 entry, the Workflow's last bullet, the Governance section (newlines folded)
awk '/^### 6\.2\.0 \(2026-11-03\)/{f=1} /^## Governance/{f=0} /^### 7\.0\.0 /{f=0} f' "$CO" | tr '\n' ' ' | sed 's/  */ /g' > "$T/entry"
awk '/^- \*\*One change at a time, on a branch\.\*\*/{f=1;print;next} f&&/^$/{f=0} f' "$CO" | tr '\n' ' ' | sed 's/  */ /g' > "$T/wf"
awk '/^## Governance/{f=1} f' "$CO" | tr '\n' ' ' | sed 's/  */ /g' > "$T/gov"
grep '^\*\*Not\*\*' "$PR" > "$T/not"
grep '^\*\*Principles\*\*' "$PR" > "$T/prin"
grep '^\*\*Who\*\*' "$PR" > "$T/who"

echo "== US1: the 6.2.0 entry =="
if [ -s "$T/entry" ]; then echo "TC-001 entry exists                                                    ok"; else echo "FAIL: TC-001 no 6.2.0 entry"; fails=$((fails+1)); fi
has "TC-001 title is English, under the date" "$T/entry" '### 6.2.0 (2026-11-03): '
l61=$(grep -n '^### 6\.1\.0 ' "$CO" | cut -d: -f1); l62=$(grep -n '^### 6\.2\.0 ' "$CO" | cut -d: -f1); lg=$(grep -n '^## Governance' "$CO" | cut -d: -f1)
if [ -n "$l61" ] && [ -n "$l62" ] && [ "$l61" -lt "$l62" ] && [ "$l62" -lt "$lg" ]; then echo "TC-001 order 6.1.0 < 6.2.0 < Governance                                ok"; else echo "FAIL: TC-001 order"; fails=$((fails+1)); fi
order=$(grep -o '\*\*\(Rationale\|What changes\|Sync Impact Report\|Impact on existing deployments\|Version\|Approval\)\.\*\*' "$T/entry" | tr '\n' ' ')
if [ "$order" = '**Rationale.** **What changes.** **Sync Impact Report.** **Impact on existing deployments.** **Version.** **Approval.** ' ]; then echo "TC-002 six labels in order                                             ok"; else echo "FAIL: TC-002 labels: $order"; fails=$((fails+1)); fi
has "TC-003 quote 2026-10-24" "$T/entry" '「以後你都自己合併」'
has "TC-004 quote 2026-11-03" "$T/entry" '「合併規則同意」'
has "TC-005 mentions 2.1.0" "$T/entry" '2.1.0'
has "TC-005 mentions 2026-10-24" "$T/entry" '2026-10-24'
has "TC-005 mentions v3" "$T/entry" '`v3`'
has "TC-005 mentions main" "$T/entry" '`main`'
has "TC-006 development lead merges" "$T/entry" 'development lead merges every pull request'
hasi "TC-007 modified or removed requirement (entry)" "$T/entry" 'modified or removed requirement'
hasi "TC-008 amendments" "$T/entry" 'Amendments'
hasi "TC-008 releases" "$T/entry" 'releases'
hasi "TC-008 loosens the Safety Net" "$T/entry" 'loosens the Safety Net'
has "TC-009 listed for the maintainer" "$T/entry" 'listed for the maintainer'
has "TC-010 base v3" "$T/entry" 'The development branch is named: `v3`'
has "TC-010 main is v2 line" "$T/entry" '`main` carries the v2 line'
for p in '`.github/`' 'hooks' 'this constitution' '`plugin.json`' '`platform/abf_station/`' 'adversarial'; do has "TC-011 entry protected-path: $p" "$T/entry" "$p"; done
has "TC-012 no principle removed" "$T/entry" 'No principle or Safety Net rule is removed or redefined'
for f in PRODUCT.md DESIGN.md tests/constitution_scope_test.sh tests/platform_direction_docs_test.sh; do has "TC-013 sync lists $f" "$T/entry" "$f"; done
has "TC-014 Impact None" "$T/entry" '**Impact on existing deployments.** None'
has "TC-014 Version MINOR" "$T/entry" '**Version.** MINOR'
has "TC-015 Approval quote" "$T/entry" '「合併規則同意」'
has "TC-015 Approval date" "$T/entry" 'approved this change in his own words on 2026-11-03'
has "TC-015 development lead merges the PR" "$T/entry" 'the development lead merges the pull request'

echo "== Workflow last bullet =="
has "TC-016 v3" "$T/wf" '`v3`'
has "TC-016 main carries v2 line" "$T/wf" '`main` carries the v2 line'
lacks "TC-017 old sentence gone" "$T/wf" 'main. receives merges only'
has "TC-018 CI workflow" "$T/wf" '.github/workflows/tests.yml'
has "TC-018 acceptance" "$T/wf" 'independent acceptance'
has "TC-018 development lead merges" "$T/wf" 'development lead merge'
hasi "TC-019 amendments" "$T/wf" 'Amendments'
hasi "TC-019 releases" "$T/wf" 'releases'
hasi "TC-019 loosens the Safety Net" "$T/wf" 'loosens the Safety Net'
has "TC-019 explicit yes in his own words" "$T/wf" "explicit yes, in his own words"
hasi "TC-020 modified or removed (workflow)" "$T/wf" 'modified or removed'
for w in fixes tests docs refactors 'only make the Safety Net stricter'; do has "TC-021 tier word: $w" "$T/wf" "$w"; done
has "TC-022 what a user sees" "$T/wf" 'what a user'
has "TC-022 listed for the maintainer" "$T/wf" 'listed for the maintainer'
for p in '`.github/`' 'hooks' 'this constitution' '`plugin.json`' '`platform/abf_station/`' 'adversarial'; do has "TC-023 workflow protected-path: $p" "$T/wf" "$p"; done
n_now=$(awk '/^## Development Workflow/{f=1;next} /^## /{f=0} f&&/^- \*\*/' "$CO" | wc -l)
n_base=$(git -C "$ROOT" show origin/v3:.specify/memory/constitution.md 2>/dev/null | awk '/^## Development Workflow/{f=1;next} /^## /{f=0} f&&/^- \*\*/' | wc -l)
if [ "$n_base" -eq 0 ] || [ "$n_now" -eq "$n_base" ]; then echo "TC-024 same number of workflow bullets                                 ok"; else echo "FAIL: TC-024 bullets $n_now vs $n_base"; fails=$((fails+1)); fi
has "TC-024 risk sentence inside the bullet" "$T/wf" 'adversarial review'

echo "== US2: Governance and version line =="
lacks "TC-025 old Governance sentence gone" "$T/gov" 'Only the maintainer approves and merges it'
has "TC-026 development lead merges after the maintainer's yes" "$T/gov" 'development lead'
has "TC-027 supersedes" "$T/gov" 'supersedes all other practices'
has "TC-027 MUST NOT restate" "$T/gov" 'MUST NOT restate'
last=$(grep -v '^[[:space:]]*$' "$CO" | tail -1)
if [ "$last" = '**Version**: 7.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-11-05' ]; then echo "TC-028 version line                                                    ok"; else echo "FAIL: TC-028 got: $last"; fails=$((fails+1)); fi

echo "== US3: PRODUCT.md =="
has "TC-030 nano4" "$T/who" 'NCHC nano4'
lacks "TC-031 no Taiwania3" "$PR" 'Taiwania3'
# the Not line, cut into clauses at ';'
sed 's/^\*\*Not\*\*: *//' "$T/not" | tr ';' '\n' > "$T/clauses"
bad=$(grep -i 'web terminal' "$T/clauses" | grep -vic 'later')
if [ "$bad" -eq 0 ]; then echo "TC-032 no non-later clause mentions web terminal                       ok"; else echo "FAIL: TC-032"; fails=$((fails+1)); fi
lacks "TC-032 old 'a web terminal;' item gone" "$T/not" 'a web terminal;'
cnt=$(grep -ci 'web terminal' "$T/clauses")
if [ "$cnt" -eq 1 ]; then echo "TC-033 exactly one web terminal clause                                 ok"; else echo "FAIL: TC-033 count $cnt"; fails=$((fails+1)); fi
grep -i 'web terminal' "$T/clauses" > "$T/wt"
hasi "TC-033 clause has later" "$T/wt" 'later'
hasi "TC-033 clause has constitution amendment" "$T/wt" 'constitution amendment'
for w in roles 'Data Explorer' Dashboard; do has "TC-033 same later list: $w" "$T/not" "$w"; done
lacks "TC-034 not declared approved" "$T/wt" 'approved|已核可'
for w in 'Seqera clone with many top-level pages' 'chatty AI text' roles 'Data Explorer' Dashboard; do has "TC-035 Not keeps: $w" "$T/not" "$w"; done
has "TC-036 Seqera Platform" "$T/prin" 'Seqera Platform'
has "TC-036 Galaxy" "$T/prin" 'Galaxy'
has "TC-037 top-level pages" "$T/prin" 'top-level pages'
for w in 'ADR 0006' 'works without AI' 'ADR 0004' 'only their own runs'; do has "TC-038 Principles keeps: $w" "$T/prin" "$w"; done

echo "== US4: DESIGN.md =="
has "TC-040 row 23" "$DE" '23. 「一樣要注意中文的顯示不能口語(e.g. "選用這個樣本", "用過的")」 (10-27)'
has "TC-041 row 24" "$DE" '24. 「介面還是不好，AWS, Azure介面就不能跟國網一樣，請你去參考Seqera platform的介面，不要都自己腦補」 (10-30)'
has "TC-042 row 25" "$DE" '25. 「我的意思是介面設計多去參考Seqera, galaxy等」 (11-03)'
seq=$(awk '/^22\. /{f=1} /^## Skeleton/{f=0} f&&/^2[2-5]\. /{printf "%s ", substr($0,1,3)}' "$DE")
if [ "$seq" = '22. 23. 24. 25. ' ]; then echo "TC-043 rows 22..25 in order before Skeleton                           ok"; else echo "FAIL: TC-043 got: $seq"; fails=$((fails+1)); fi
has "TC-044 row 19 intact" "$DE" '19. 「是中欄有個可以切換主視窗跟終端機的按鈕。終端機能否直接使用? 我要在AI幫我跑時同時看到終端機的輸入指令變化，但我同時也可以自己打。下游的中欄主視窗是R studio，但切換成終端機就是跑在我的電腦。」 (10-23)'
has "TC-044 row 22 intact" "$DE" '22. 「分成四類 改成 跟Seqera platform一樣的模式，不要自己定義」 (10-23 20:15)'

echo "== US6: out of scope =="
lacks "TC-069 no OTP in the 6.2.0 entry" "$T/entry" 'OTP'

echo
if [ "$fails" -eq 0 ]; then echo "charter_v4_workflow_test: all ok"; exit 0; else echo "charter_v4_workflow_test: $fails FAIL"; exit 1; fi
