# Bug Assessment: Tests that pass without checking (false green)

- **Slug**: false-green-tests
- **Created**: 2026-09-29
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/30 (constitution audit batch B)
- **Verdict**: valid
- **Severity**: high
- **Drafted by**: a read-only Sonnet reviewer (Windows Git Bash repro); spot-checked by developer, who added `tests/column_output_relay_rule.sh:35` (same `grep -P … 2>/dev/null` shape, missed by the draft).

## 給維護者

1. 「指令層不能點名特定叢集」那支測試在 Windows 上永遠顯示通過：它用的搜尋寫法在這台的語系設定下會出錯，出錯被當成「沒找到」。實測重現。
2. 同樣寫法的測試還有 3 支（`launch_provenance_test.sh`、`intro_test.sh`、`column_output_relay_rule.sh`），一併修。
3. 修好之後會冒出 4 處真的違規（文件裡點名 SLURM、QOSMin、partition），要在同一次修掉，否則測試會變紅。改成不分大小寫時，英文動詞「relay（轉述）」會被誤判，要特別排除。
4. 刪除確認的測試在 Windows 有 4 個紅燈，是測試讀中文的編碼問題，不是安全網壞了；一併修，免得蓋掉真正的問題。
5. 「拿掉 hooks 仍可用」（第 5 條）和「拒絕要說明原因類型」（第 11 條）沒有測試，但那是設計新測試，要走新功能流程，建議拆出去另開。

## Symptom

Several `tests/*.sh` print `ok`/`OK` when the condition they check is violated, because a `grep -P` error (exit 2) is indistinguishable from "no match" (exit 1) in how they are called.

## Reproduction (Windows Git Bash, LC_CTYPE=C.UTF-8, LC_ALL unset)

1. `bash tests/command_layer_is_site_neutral.sh` → `OK`, although `commands/downstream.md:85` (SLURM), `commands/runs.md:178` (QOSMin), `commands/setup.md:509` (Slurm) and `skills/operational/SKILL.md:152` (partition) name scheduler terms. ✔
2. `echo x | grep -P x` → `grep: -P supports only unibyte and UTF-8 locales`, rc=2. ✔
3. `bash tests/confirm_cleanup_test.sh` → 4 FAIL, all `JSONDecodeError` from `python3 -c … json.load(sys.stdin)` decoding the hook's Chinese text under the Windows code page. ✔ (loud, but test-caused)
4. `bash tests/confirm_launch_test.sh` → 1 FAIL in D3 ("D3 fired off MSYS"): the "not on MSYS" case cannot fake the real MSYS environment. ✔ (loud, test-caused)

## Suspected Code Paths

- `tests/command_layer_is_site_neutral.sh:32,34` — lowercase-only `TERMS`, no `-i`; `grep -rInP … 2>/dev/null … || true` swallows rc=2; scans `commands/` only, never `skills/`.
- `tests/launch_provenance_test.sh:78-84` — same `TERMS` duplicated; `if grep -qP …` treats rc=2 as "no match" → prints ok.
- `tests/intro_test.sh:104-106` — `if grep -qP '\S {3,}'` → same.
- `tests/column_output_relay_rule.sh:35` — `grep -rlP … 2>/dev/null` → same class (developer addition).
- `tests/confirm_cleanup_test.sh:17,19` and the `askcheck`/`denycheck` helpers — `python3 -c` reading stdin without UTF-8 mode.
- `tests/confirm_launch_test.sh` D3 block — depends on real `$OSTYPE`/`$MSYSTEM`.
- `tests/no_hardcoded_paths.sh:28,35` — five root prefixes only; scans `scripts commands configs`; not `skills hooks README.md CLAUDE.md` (no current hit there — latent gap).
- `tests/scripts_name_their_alternative.sh:26` — any `# Not X:` passes; `find` covers `scripts/` only, not `hooks/`. Seven headers name the script itself or an in-repo sibling rather than a maintained external tool (`scripts/env.sh:14`, `detect_conditions.sh:11`, `record_adapter.sh:4`, `utils/wsl_ssh.sh:5`, `intro.sh:38`, `setup_verify.sh:8`, `runs_board_site_probe.sh:8`).
- `tests/portable_userland.sh:29` flags `grep -P` as unportable for scripts/hooks but never scans `tests/` — why these went unnoticed.

## Root Cause Hypothesis (high confidence)

(a) `grep -P` is unavailable under this locale and exits 2; callers that wrap it in `2>/dev/null … || true` or test it with `if grep -qP` cannot tell an error from "no match", so negative assertions pass regardless of content. (b) `python3 -c` reading hook JSON without forced UTF-8 fails on Windows — loud, but it is test-harness noise that will hide a real regression.

## Proposed Remediation

**Preferred**:
1. Replace `grep -P` in tests with `grep -E` (restructure the one lookbehind, `(?<!reach: )`, as a second `grep -v 'reach:'`), and make any grep error fail the test (`rc -ge 2` → FAIL). One shared term list sourced by both `command_layer_is_site_neutral.sh` and `launch_provenance_test.sh` so they cannot drift.
2. Add `-i` and scan `skills/`; exclude the verb "Relay what they …" (`commands/*.md:10-12`, five files) explicitly; re-scan all of `commands/` + `skills/` after the change. Fix the four real hits in the same change (reword to site-neutral language or move the site detail into `docs/SITE_ADAPTER.md` / the site adapter).
3. `PYTHONIOENCODING=utf-8` (or `python3 -X utf8`) on every `python3 -c` in `confirm_cleanup_test.sh`.
4. Extend `tests/portable_userland.sh` to scan `tests/` for `grep -P` so the class cannot return.
5. `no_hardcoded_paths.sh`: add `skills/`, `hooks/`, `README.md`, `CLAUDE.md` to the scan roots (no current hits expected). Repo-coordinate/hostname checks belong with batch E's `report.sh` fix.

**Split out** (feature path, not this bug): tests for invariant 5 (usable with `hooks/` removed) and invariant 11's refusal classification; the D3 MSYS test design; tightening what counts as a valid `# Not X:` (a judgement call for the maintainer).

**Files likely to change**: `tests/command_layer_is_site_neutral.sh`, `tests/launch_provenance_test.sh`, `tests/intro_test.sh`, `tests/column_output_relay_rule.sh`, `tests/confirm_cleanup_test.sh`, `tests/portable_userland.sh`, `tests/no_hardcoded_paths.sh`, possibly a new `tests/lib/site_terms.sh`; `commands/downstream.md`, `commands/runs.md`, `commands/setup.md`, `skills/operational/SKILL.md` (the four real hits → manual half of `docs/TESTING.md` applies).

**Tests to add**: a fixture proving each fixed test now FAILs on a planted violation (uppercase SLURM in commands/, "partition" in skills/, a `grep` error) — written first, red on `main`.

## Risks & Considerations

- `-i` may surface more false positives than "Relay"; review every new hit, do not bulk-whitelist.
- Batch A (#29) also edits `tests/confirm_cleanup_test.sh`; B must start from `main` after A merges.
- Windows-only D3 red remains until its split-out fix; say so in the PR so it is not mistaken for a regression.

## Open Questions

- `grep -E` rewrite vs. a locale-forcing helper for `-P` — recommendation: `-E`, because `-P` is also unavailable on BSD grep (`portable_userland.sh:29`), i.e. on the maintainer's Mac.
- The seven self-referential `# Not X:` headers: accept, or require a named external tool? (Split out; maintainer's call.)

## Decisions (maintainer, 2026-09-30: 「B 評估照建議」)

- `grep -P` in tests is replaced by `grep -E` (also what the Mac's BSD grep supports), and a grep error (exit ≥ 2) fails the test.
- Invariant 5 / invariant 11 tests, the D3 MSYS test design, and tightening what counts as a valid `# Not X:` header are split out (feature flow / later), not done here.

## Notes after #29 (merged e392348)

- `tests/confirm_cleanup_test.sh` now exports `MSYS2_ARG_CONV_EXCL='*'`; its python calls still read hook JSON without forcing UTF-8.
- `tests/confirm_launch_test.sh` matcher checks already strip `\r` from jq.exe output.
