# Bug Fix: Tests that pass without checking (false green)

- **Slug**: false-green-tests
- **Fixed**: 2026-09-30
- **Assessment**: ./assessment.md
- **Status**: applied

## Summary

Replaced every `grep -P` in the affected tests with `grep -E` and made a grep
error (exit >= 2) fail the test instead of being read as "no match" — the
actual root cause, per the maintainer's decision ("B 評估照建議"). Extended
the site-neutrality and hardcoded-path scans to `skills/`, `hooks/`,
`README.md` and `CLAUDE.md`, fixed the four real site-neutrality violations
this surfaced, forced UTF-8 decoding in `confirm_cleanup_test.sh`'s JSON
reads, and taught `portable_userland.sh` to catch `grep -P` inside `tests/`
itself so the class cannot come back unnoticed.

## Changes

| File | Change | Notes |
|------|--------|-------|
| `tests/lib/site_terms.sh` | added | Shared `SITE_TERMS` list + `site_terms_grep`/`site_terms_allow`, sourced by both site-neutrality tests so they cannot drift (assessment item 1). |
| `tests/command_layer_is_site_neutral.sh` | modified | Sources the shared lib; `grep -E -i`, scans `skills/` too, treats a grep error (rc>=2) as FAIL. |
| `tests/launch_provenance_test.sh` | modified | Check 6 now uses the same shared lib/pattern instead of its own duplicated `TERMS` string; same rc>=2 handling. |
| `tests/intro_test.sh` | modified | Line ~104: `grep -qP '\S {3,}'` → `grep -nE '[^[:space:]] {3,}'` with explicit rc 0/1/≥2 handling. |
| `tests/column_output_relay_rule.sh` | modified | Line 35: `grep -rlP` → `grep -rlE`, rc>=2 now reported as its own FAIL line rather than folding into "nothing matched". |
| `tests/confirm_cleanup_test.sh` | modified | `PYTHONIOENCODING=utf-8` added to all 6 `python3 -c` calls that do `json.load(sys.stdin)` on the hook's (Chinese-bearing) JSON output. |
| `tests/portable_userland.sh` | modified | New scoped pass scanning `tests/*.sh tests/lib/*.sh` for `grep -P` only (not the full GNU-userland rule set), excluding its own `RULES` definition. |
| `tests/no_hardcoded_paths.sh` | modified | Scan roots extended from `scripts/ commands/ configs/` to also include `skills/ hooks/ README.md CLAUDE.md`; grep error now fails loud. |
| `commands/downstream.md` | modified | `SLURM` → "the site's scheduler" (real violation #1). |
| `commands/runs.md` | modified | `` `QOSMin*` `` → "a resource-floor rejection (wording is scheduler-specific — see `docs/SITE_ADAPTER.md`)" (real violation #2). |
| `commands/setup.md` | modified | "submit-through-Slurm cycle" → "submit-through-scheduler cycle" (real violation #3). |
| `skills/operational/SKILL.md` | modified | "a partition's floor" → "the site's resource floor" (real violation #4). |

No test files were added beyond `tests/lib/site_terms.sh` (a shared library,
not itself a test file picked up by `run_all.sh`'s `tests/*.sh` glob).

## Diff Highlights

`tests/command_layer_is_site_neutral.sh`, the core of the fix:

```bash
. "$HERE/lib/site_terms.sh"

raw=$(site_terms_grep "$ROOT/commands" "$ROOT/skills" 2>&1)
rc=$?
if [ "$rc" -ge 2 ]; then
    printf '%s\n' "$raw"
    echo "FAIL: the site-term scan itself errored (grep exit $rc) - a broken scan is not a clean pass."
    exit 1
fi
hits=$(printf '%s\n' "$raw" | site_terms_allow | sed "s|^$ROOT/||" | grep -v '^$')
```

`tests/lib/site_terms.sh`'s allow-list, reviewed hit-by-hit rather than
bulk-whitelisted (assessment's Risks & Considerations):

```bash
site_terms_allow() {
    grep -viE 'reach: ?ssh|reach=ssh|relay what they|relay column output|remote-ssh'
}
```

`relay column output` and `remote-ssh` are additions beyond the assessment's
own list (see Deviations below) — everything else in the allow-list is
exactly what the assessment named.

## Tests Added or Updated

No new permanent test *files* were added — the assessment's "Tests to add"
item (a fixture proving each fixed test now FAILs on a planted violation) was
run as throwaway proofs against temp copies under `/tmp`/`mktemp -d`, per the
task's red-before/green-after requirement, and is not checked in (the
assessment did not ask for a permanent mutation-test file, and none of
`docs/TESTING.md`'s existing files carry that pattern either — they are
regression tests, not meta-tests of the test suite). Every existing test file
listed above was updated in place; `dev_workflow_test.sh` (the gate-shape
check) already covers the workflow files, and `run_all.sh` picked up the new
`tests/lib/site_terms.sh` correctly as *not* a test file (its glob is
`tests/*.sh`, non-recursive).

## Local Verification

All in WSL (`bash /mnt/c/Users/ACER/wt-30 tests/...`), per `docs/TESTING.md` —
native Git Bash refuses this suite.

- `bash tests/run_all.sh` → **73/73 passed, all green** (final, after every
  change below).
- Red-before / green-after, one item at a time:
  1. **Baseline false-green (current code, no locale trick needed):**
     `bash tests/command_layer_is_site_neutral.sh` on unmodified `main` →
     `OK`, despite `SLURM`/`QOSMin`/`Slurm`/`partition` already present in
     `commands/`+`skills/` (case-sensitivity + `skills/` never scanned).
     `bash tests/launch_provenance_test.sh` → also `OK`.
  2. **Forced `grep -P` parse error (temp copy, pattern `(?<!x`, rc=2):** the
     old `2>/dev/null … || true` idiom prints `OK: commands/ names no
     scheduler…` — the exact swallow the assessment describes. Reproduced for
     both the site-neutrality tests and (generically) the `if grep -qP`
     shape used in `intro_test.sh`.
  3. **After the shared-lib/`-i`/`skills/`-scan fix, before the wording fix:**
     `bash tests/command_layer_is_site_neutral.sh` → **FAIL**, reporting
     exactly the 4 real hits (`downstream.md:85` SLURM, `runs.md:178`
     QOSMin, `setup.md:509` Slurm, `SKILL.md:152` partition) and correctly
     excluding `Remote-SSH`/`relay column output`/`reach: ssh`/"Relay what
     they". Forcing a grep error against the *fixed* code → `FAIL: the
     site-term scan itself errored (grep exit 2)`, not `OK`.
  4. **After the wording fix:** both tests green.
  5. `tests/intro_test.sh`, `tests/column_output_relay_rule.sh`: green after
     the `-E` conversion; the swallow mechanism (`if grep -qP`, rc 1 vs 2
     indistinguishable) demonstrated directly against a forced-error pattern.
  6. `tests/confirm_cleanup_test.sh`: could **not** reproduce the
     `JSONDecodeError` in WSL — this WSL's `python3` reports
     `sys.stdin.encoding == utf-8` even under `env -i LANG=C LC_ALL=C`
     (Python's UTF-8 mode default), so the encoding bug is specific to
     Windows Git Bash's code page, outside what this sandbox can force. The
     fix (`PYTHONIOENCODING=utf-8` on all 6 call sites) was applied exactly
     as specified anyway, verified to introduce no regression (still
     73/73-worthy — file passes green before and after in WSL), and left as
     a documented gap below.
  7. `tests/portable_userland.sh`: original (from `git show HEAD:...`)
     against a temp tree with a planted `grep -P` in a fake
     `tests/planted_violation_test.sh` → `all passed` (silent miss, since it
     never scanned `tests/`). Fixed version against the same tree → `FAIL
     tests/planted_violation_test.sh:2 grep -P needs PCRE; BSD grep has
     none`. Fixed version against the real, already-fixed tree → clean.
  8. `tests/no_hardcoded_paths.sh`: original against a temp tree with
     `JAVA="${TW_AGENT_JAVA:-/home/alice/bin/java}"` planted into
     `skills/operational/SKILL.md` → `OK` (silent miss). Fixed version, same
     tree → `FAIL: 1 hardcoded path(s)`, naming the exact line. Fixed
     version against the real tree → clean (no hit in `skills/`, `hooks/`,
     `README.md`, `CLAUDE.md`, matching the assessment's "latent gap, no
     current hit").

## Deviations from Assessment

- **Two additional false-positive exemptions**, beyond the assessment's own
  "exclude the verb 'Relay what they'": once `-i` and the `skills/` scan were
  both live, two more hits appeared that the assessment's manual review had
  not surfaced:
  - `skills/operational/SKILL.md:71` — "relay **column output**" (the name of
    the fenced-code-block rule `tests/column_output_relay_rule.sh` itself
    checks), same verb sense as "Relay what they", not network machinery.
  - `commands/downstream.md:234` — "Positron reaches the site through its own
    **Remote-SSH** support" — a proper noun naming a third-party editor's own
    connection feature, not the command layer spelling out an `ssh`
    invocation (nothing here forks `scripts/on_site.sh` or `preflight.sh`).
  Both were reviewed individually per the assessment's own caution against
  bulk-whitelisting once `-i` widens the net, and added to
  `tests/lib/site_terms.sh`'s `site_terms_allow`, each with its own comment.
- **`tests/confirm_cleanup_test.sh`'s red-before evidence is not reproduced**,
  only asserted from the assessment plus a targeted check of Python's
  encoding defaults in this WSL environment (see Local Verification item 6).
  The fix was still applied exactly as the assessment specified.
- Everything else matches the Proposed Remediation and the maintainer's
  Decisions section exactly. The "Split out" items (invariant 5 / invariant
  11 tests, the D3 MSYS test design, tightening `# Not X:` headers) were left
  untouched, as instructed.

## Follow-ups

- `tests/confirm_launch_test.sh` D3's Windows-only red (MSYS fakery) remains,
  per the assessment's own note — not part of this bug, split out already.
- The seven self-referential `# Not X:` headers
  (`tests/scripts_name_their_alternative.sh:26`) are an open question for the
  maintainer, explicitly deferred.
