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
| I.2 no second copy of run state | `tests/no_second_run_state_test.sh` | 14 self-tests: sbatch / `nextflow run` / `tw launch` (also after `&&`, quoted, in Python), `nohup`, a polling loop, a run-state file, sqlite, an invented `tw` noun; quoted prose passes |
| II.5 works without the host | `tests/works_without_host_test.sh` | 7 self-tests on mutated copies: sourcing a hook, running one with bash, reading `.claude-plugin/`, a script that does not parse, a doc citing a missing script; a comment naming a hook passes |
| Credentials (git, printing, params) | `tests/credentials_stay_in_settings_test.sh` | 20 self-tests for the static scans; 9 hook cases for the params gate |
| III.7 nobody needs the maintainer | Procedure P1, `docs/TESTING.md` Half 3 | manual; needs a person who is not the maintainer |
| IV.8 evidence before claims | Procedure P2, `docs/TESTING.md` Half 3 | manual; no automation on purpose (a lint for "has a date" is green for every entry and proves nothing) |

### The two drafts left by the interrupted agent (commit `23335df`)

Reviewed critically. Both were close and neither found a defect in the code.

- `no_second_run_state_test.sh`: logic sound, 14 self-tests already there and all pass. Kept as is.
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
