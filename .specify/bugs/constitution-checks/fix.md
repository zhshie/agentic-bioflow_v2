# Bug Fix: constitution principles with no real Check

- **Slug**: constitution-checks
- **Branch**: `fix/constitution-checks`
- **Assessment**: `assessment.md` (this folder)
- **Result**: every one of the 13 principles and the credentials rule now names a Check that exists, and `tests/constitution_checks_exist_test.sh` keeps it that way.

## 給維護者

1. 三件都做完了。憲章 2.0.1（PATCH）只加 *Check:* 行，規則本身沒改意思。
2. 補 Check 的過程找到一個真缺口：憑證條「不進 params 檔」**沒有任何程式在擋**。我加了一道最小的關卡（`confirm_walkthrough.sh` 的 G7），這是 hook 的行為變動，請你特別看一眼。
3. 憑證條最後一句「不沿用別的成員的副本」只有**部分**覆蓋：換身分會先問、`_personal/` 是 700，但「從別人帳號複製來的設定檔」偵測不到。憲章與下面都照實寫，沒有假裝。
4. `tests/scripts_name_their_alternative.sh` 的暫時白名單（hooks/ 十一支、`detect_conditions.sh`、`methods_text.py`）**刻意沒動**，等另一條分支補完標頭、兩邊都合併後再移除；白名單裡的項目一旦變乾淨，測試會自己報「過期」。

## Item 1: invariant 1's Check accepted anything shaped like `# Not X:`

- **Red** `36502c1`: the check now has to see an alternative outside this repo, scans `hooks/`, and accepts the explicit `# Nothing existing: <why>` form.
- **Fix** `e58dbcb`: six headers rewritten (`env.sh`, `intro.sh`, `record_adapter.sh`, `runs_board_site_probe.sh`, `setup_verify.sh`, `utils/wsl_ssh.sh`).
- **Left on a temporary allow-list, on purpose**: `scripts/detect_conditions.sh` and `scripts/methods_text.py` (another branch adds those headers) and the eleven `hooks/` files. The list is commented with who applies the fix, reports each entry as PENDING, and fails with STALE when an entry is already clean. Remove it after both branches merge. `SCRIPTS_NAME_ALT_NO_ALLOWLIST=1` shows the true state: 13 pending.

## Item 3: invariant 4's Check only looked for the word "relay"

- **Red** `b34dcef`: `tests/command_layer_is_site_neutral.sh` now also bans `nf_relay`, `relay_denied`, `relay_port`, `nchc`, `taiwania`, `configs/sites` and login-node host names in the command layer. Naming `egress_ctl.sh` and friends stays allowed (reasoning in the assessment).
- **Fix** `3e75261`: `commands/downstream.md` points at the adapter's resource contract (`docs/SITE_ADAPTER.md` section 1), not at `configs/sites/nchc.config`.

## Item 2: five rules with no Check

| Rule | Check now | How it is shown to go red |
|---|---|---|
| I.2 no second copy of run state | `tests/no_second_run_state_test.sh` | 28 self-tests (24 after round 1, 4 added in the leftovers round): sbatch / `nextflow run` / `tw launch` (also after `&&`, quoted, in Python), `nohup`, a polling loop, a run-state file, sqlite, an invented `tw` noun; quoted prose passes |
| II.5 works without the host | `tests/works_without_host_test.sh` | 7 self-tests on mutated copies: sourcing a hook, running one with bash, reading `.claude-plugin/`, a script that does not parse, a doc citing a missing script; a comment naming a hook passes |
| Credentials (git, printing, params) | `tests/credentials_stay_in_settings_test.sh` | 20 self-tests for the static scans; 9 hook cases for the params gate |
| III.7 nobody needs the maintainer | Procedure P1, `docs/TESTING.md` Half 3 | manual; needs a person who is not the maintainer. The assessment also named `tests/onboarding_self_contained_test.sh` (a lint that no user-facing text sends the user to PITFALLS or the maintainer). **Dropped, not written:** a text lint cannot see whether a person got stuck, and the phrase it would grep for is exactly what a step written to dodge the lint would avoid. P1 checks the real thing. |
| IV.8 evidence before claims | Procedure P2, `docs/TESTING.md` Half 3 | manual; no automation on purpose (a lint for "has a date" is green for every entry and proves nothing) |

### The two drafts left by the interrupted agent (commit `23335df`)

Reviewed critically. Both were close and neither found a defect in the code.

- `no_second_run_state_test.sh`: logic sound, 14 self-tests already there in the draft and all passed. Kept as is. (Round 1 grew it to 24; the leftovers round to 28.)
- `works_without_host_test.sh` had four real faults, all in the test:
  1. Its static scan matched any line that mentioned `hooks/`, so a comment, an echoed message and a docstring (`scripts/report.sh`, `scripts/turn_timing.py`) failed it. It now judges only lines that execute or load something (source, `.`, bash, sh, python, exec, cat, or a variable-built path).
  2. Its section 5 reported `scripts/portable_root.sh`, which `CLAUDE.md` cites to say it is gone. Lines that say removed or gone are skipped.
  3. It had one self-test, which only ran the static scan. Now seven, and the nested run skips the sections that need real scripts.
  4. Its nested run called itself by a relative path after `cd`, so it died with 127; and the copies were slow (about 2 minutes under WSL on /mnt/c). It now keeps an absolute path to itself and copies only `scripts docs commands skills README.md CLAUDE.md`.
  It also cited a "Procedure P5" that does not exist; reworded.

### The credentials rule, part by part

| Part | Held by | State |
|---|---|---|
| owner only | `tests/settings_test.sh` (created mode 600; a filesystem that cannot hold 600 is refused; a world-readable token is called out), `tests/windows_privacy_test.sh` (ACL) | already covered, cited |
| never printed | `tests/settings_test.sh`, `tests/inspect_sides_test.sh`, `tests/status_test.sh`, `tests/windows_privacy_test.sh` (each plants a fixture token and greps the output); new static scan: no script echoes, prints or traces a token variable | cited, plus new scan (clean) |
| never in git | new: no tracked file holds a token-shaped value (JWT, GitHub, AWS, Slack, private key, a long value under a credential-named key); no credential file tracked; `.gitignore` names `.seqera_token` and `env.yaml` | **red** `b63529d`: `.gitignore` named neither. **green** `9e24068` |
| never in a params file | new: the walkthrough hook's G7 | **red** `48b3542`: 6 of 9 cases (all refusals) allowed a token. **green** `d4a863b` |
| not carried over from another member's copy | `tests/confirm_launch_test.sh` (changing `agent_connection` to another identity asks first), `tests/init_workspace_test.sh` (`_personal/` is mode 700) | **partial.** A settings file copied in from another account is not detected; `docs/SETTINGS.md` says one root belongs to one person and nothing measures it. Not invented here; needs your decision (see below) |

Four test files hold fixture tokens on purpose (a test that proves "never printed" has to plant one). They sit on a short allow-list with a reason each, in the test; a stale entry fails.

**G7 in `hooks/confirm_walkthrough.sh`.** When a call writes a params file (Write, Edit, MultiEdit, a here-doc) and the raw payload holds a credential-named key (token, secret, password, api_key, access_key, private_key, with an optional `_suffix`) followed by a value of 12 or more opaque characters, or a token shape, it is denied. Placed before the escape phrase and the transcript are read, so 略過導覽 does not lift it. It runs only after the call is already a params write, so other calls pay nothing. Controls that must pass: ordinary params, a comment mentioning a token, `tokenizer: models/bpe/tokenizer.model`, `max_tokens: 512`. `tests/confirm_walkthrough_test.sh` still passes in full.

## Constitution 2.0.1 (commit `66e8672`)

Only *Check:* lines added: I.2, II.5 (test named before the existing sentence), III.7 and IV.8 (Procedure P1 and P2 named before the existing sentence), and the credentials rule. Version line 2.0.1, Last Amended 2026-10-05, Amendments entry in the 2.0.0 format (rationale, what changes, impact, version, approval). The only document quoting the current version was `tests/constitution_scope_test.sh` (it asserted `2.0.0` and the 2.0.0 date); it now asserts 2.0.1, 2026-10-05, and that the 2.0.0 entry is still there. The other "Constitution 2.0.0" mentions (`CLAUDE.md`, `docs/PRINCIPLES.md`, `docs/SITE_ADAPTER.md`, `docs/TESTING.md`) say when the in-use scope was introduced, which stays true, so they are left alone.

## Decisions for the maintainer

1. G7 is a new refusal in a hook. It enforces a rule that already existed, but a pipeline with a parameter genuinely named like `*_token` and a long value would now be refused. The message says what to do; say if you want it narrower.
2. "Never carried over from another member's copy" has no real check. Options: a Windows/Unix owner check in `settings.sh --migrate` (refuse a token file not owned by the current user), or reword the rule to what is enforced. I did neither.
3. Remove the temporary allow-list in `tests/scripts_name_their_alternative.sh` once the other branch (`detect_conditions.sh`, `methods_text.py`) and the `hooks/` headers have merged.

## Acceptance round 1 (rejected, fixed)

| Finding | Commits | What changed |
|---|---|---|
| H1 false green in invariant 1's check | ac1f0c1 RED, 76d6ac1 GREEN | With any file waived the last line is now `PARTIAL: 51 of 64 ... 13 are waived ... and NOT checked:` plus the file names (exit 0). Hook headers not touched, as instructed. |
| M1 G7 false positives, M2 G7 false negatives | 165816f RED (13 red), f0105f5 GREEN | G7 now reads params.json, keys api-key / apikey / credential(s) / bearer / auth_token, passwords with any characters. It skips keys naming a file, path, dir, name, policy, pattern, prefix, length, url, limit, count or size, and values that are paths (/, ~, ./, drive letter), an env reference or only digits. |
| M3 G7 is a behaviour change | f0105f5, 9fc0d30 | The 2.0.1 impact now names G7 and its reach. G7 is in the hook's header table, in `CLAUDE.md`'s hook list and in `docs/PRINCIPLES.md`. 23 G7 cases (deny and allow) are in `tests/confirm_walkthrough_test.sh`, which gets one self-contained block at its end. The hook edit is one function plus one call in one place. |
| M4 invariant 2 scan misses | 8e8ac6e RED (8 red), 989b710 GREEN | Quoted submissions (ssh, python), `until` / `while` + sleep loops, `tw runs list` cached with `>` or `tee`, snapshot file names. A SUBMIT allow-list with reasons (two text-only mentions of the nextflow command line) fails when stale. |
| Credentials Check wording | 9fc0d30 | The constitution no longer cites `confirm_launch_test.sh` and `init_workspace_test.sh` for "never carried over from another member's copy" (they test other things). It says that clause has no automated check yet, pending the maintainer's choice between an owner check in `settings.sh --migrate` and rewording the rule. |

## The real reach of the nets (stated, not chased)

- **G7** (stated in the hook header and the 2.0.1 Amendments entry): it sees a Write, Edit, MultiEdit or here-doc to a params file (yaml, yml, json) holding a credential-named key with a 12+ character value on the same line, or a token shape. It does not see `tee`, `sed -i`, a python `open()`, the PowerShell tool, values under 12 characters, a value on the next line or in a block scalar, or a key without such a word in its name (for example `pat`).
- **Invariant 2 scan** is a static net over scripts/: it finds the shapes listed in its header. A script that keeps state under a name nobody listed passes.
- **Credentials static scan** finds the token shapes it knows plus long values under credential-named keys.
- **Invariant 1** reports PARTIAL while the allow-list is non-empty.
- LOW items L1-L3 from the acceptance review stay as known limits (below).

## Known limits

- L1: `works_without_host_test.sh` runs only a few scripts, not all of them. A script it does not run could still need the host.
- L2: the heuristic in `scripts_name_their_alternative.sh` accepts any `# Not preflight:` line. It does not check that the line names a real alternative.
- L3: the never-printed-credentials scan misses `curl -v`, `declare -p` and `env | grep`. Each can print a token without an `echo`.

## Leftovers round (test gaps)

Cases added; each was shown to fail when the code it covers is mutated, on a /tmp copy.

- `tests/confirm_walkthrough_test.sh`: G7 denies a GitHub token shape (`ghp_...`) under a non-credential key; G7 allows an all-digits value under a credential key; G7 denies a letters-and-digits value there. Removing the `gh[pousr]_` shape, or the all-digits skip, turns them red.
- `tests/no_second_run_state_test.sh`: an `until` loop with no `sleep`, line-leading and after `&&` (one case per branch of the pattern); `tw runs list > out.txt` and `tw runs view x >> out.txt` (a plain name, so the snapshot-name scan does not mask the `>` branch). Removing either `until` branch, or the `>` branch, turns them red.
- Skipped: a ghp_ case in `credentials_stay_in_settings_test.sh`. It already has "a GitHub token fails".
