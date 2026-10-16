# Plan 095: make the hooks' one-call jq fast path compile on jq 1.6 (behaviour unchanged)

- **Slug**: 095-jq16-fast-path
- **Branch**: `fix/095-jq16-fast-path`, base **`main`** (v2 line)
- **Created**: 2026-10-16 by the developer-agent
- **Issue**: #95
- **Tier**: A (performance/portability; no decision or message changes). Same lane as 078 (both edit `hooks/confirm_cleanup.sh`); this task starts after 078 is merged — rebase/merge `origin/main` first.

## 給維護者

1. 這次只修速度：在 jq 1.6（Ubuntu 22.04／WSL 預設）上，每次 Bash 呼叫都多跑 3 次 jq，因為「一次讀完」的捷徑在舊版編譯失敗。
2. 所有關卡的判斷和訊息一字不變；舊測試不改，只新增「用 jq 1.6 再跑一遍」的測試。
3. 改 CI 設定要你同意，所以這支 PR 不動 CI；要不要在 CI 加 jq 1.6 另外問你。

## Facts (origin/main, 2026-10-16)

- Four hooks carry the same one-call fast path (own copy each, no shared lib); the 1.7-only construct is `sub("\\n+\\z"; "")` (strip trailing newlines to match `$(jq)`), which jq 1.6 rejects:
  - `hooks/confirm_cleanup.sh:194` (also prefixes `"abf-" + "jq-ok\u001f"`, checked at :197-208)
  - `hooks/confirm_launch.sh:170`
  - `hooks/confirm_walkthrough.sh:127`
  - `hooks/guard_plugin_files.sh:209`
- On failure the hooks fall through to `abf_jq_works` / `jq_works` plus one jq per field (`confirm_cleanup.sh:211-218`, `confirm_launch.sh:177`, `confirm_walkthrough.sh:141`, `guard_plugin_files.sh:222,296,322`): same verdicts, slower.
- `tests/gate_process_count_test.sh` (budget: jq 1 + at most 2 awk) measured on WSL: jq 1.6 at `/usr/bin/jq` → 21 failed ("started: jq jq jq jq awk"); jq 1.7.1 at `/usr/local/bin/jq` → all passed.
- Decision-pinning tests (must stay green and unedited on both versions): `confirm_launch_test.sh`, `confirm_cleanup_test.sh`, `confirm_cleanup_behind_heredoc_test.sh`, `confirm_cleanup_candidates_timing_test.sh`, `confirm_walkthrough_test.sh`, `guard_plugin_files_test.sh`, `in_use_test.sh`, `in_use_speed_test.sh`, `conditions_matrix_test.sh`, `gate_big_input_test.sh`, `gate_exit_contract_test.sh`, `gate_output_failclosed_test.sh`, `hooks_fail_closed_test.sh`, `principle_13_test.sh`, `gates_without_jq_test.sh`.
- `.github/workflows/tests.yml`: `ubuntu-latest`, `apt-get install -y jq` (1.7.x), one `bash tests/run_all.sh`.

## Design decisions (developer-agent)

1. Replace the regex with a regex-free trailing-newline strip, identical on 1.6 and 1.7: define once in each program `def t: if endswith("\n") then .[:-1] | t else . end;` and apply `map(t + "\u001f")` where `sub("\\n+\\z"; "")` was. (Not `sub("\\n+$";"")`: Oniguruma `$` semantics vary.) A trailing `\r` is not stripped, matching today's `\n+`.
2. Keep the four duplicated program texts; do not touch the `abf-jq-ok` token logic or field lists.
3. Prove equivalence: a test feeds identical inputs to the old program (`\z` form, run on 1.7.1 only) and the new program (run on every jq found) and compares output: no trailing newline, one, many, only newlines, interior newlines, CRLF, unicode, a 100 KB body, a body ending in 5,000 newlines.
4. New `tests/jq_versions_test.sh`: finds jq 1.6 via `ABF_JQ16` or `/usr/bin/jq` and 1.7 via `ABF_JQ17` or `/usr/local/bin/jq` (checks `--version`), puts a shim dir first on `PATH` per binary, runs `gate_process_count_test.sh` and the equivalence cases; prints SKIP (not PASS) for a version it cannot find. In CI today only 1.7 is present, so the 1.6 half SKIPs visibly.
5. `gate_process_count_test.sh`: one added line printing the jq version in use; budgets unchanged.

## Changes, in order (red first)

1. Red: add `tests/jq_versions_test.sh` with the equivalence cases; run on WSL → FAIL under jq 1.6 (process count), PASS under 1.7.1; save both outputs in the ledger.
2. Green: swap the `sub` call for `t` in the four hooks; nothing else on those lines changes.
3. WSL `bash tests/run_all.sh` twice (jq 1.6 first on `PATH`, then 1.7.1), plus `bash tests/jq_versions_test.sh`; every pinned test passes with zero test edits; record both runs.
4. Docs: `docs/PITFALLS.md` one short entry (regex anchors in hook jq programs must work on 1.6 and 1.7, the `\z` example); `CHANGELOG.md` one line. Hook message texts unchanged.

## Not in this PR

- No change to `.github/` (CI setting changes need the maintainer's OK; the developer-agent asks separately whether to add a jq 1.6 CI step).
- No change to any verdict, reason text, field list or process-count budget; no shared-lib refactor; no runtime jq version check.
- No change to the `v3` line (ported after merge if wanted).

## Constitution Check

- Principle 13 (fail-closed): unchanged; the token/shape/rest checks and the fall-back path stay.
- Safety Net: nothing loosened; the fast path on 1.6 goes through the same validation as on 1.7.
- Tests not edited to pass; the new test fails first.
- Protected path (`hooks/`): the developer-agent runs `/code-review` on the PR before merge.
