# Bug Assessment: constitution principles with no real Check

- **Slug**: constitution-checks
- **Created**: 2026-10-05
- **Source**: constitution audit of 2026-09-29 (issue #30, "B 批"), re-run fresh against constitution 2.0.0
- **Verdict**: valid
- **Severity**: medium (nothing is broken at runtime; the rules that "name their check" do not all have one, so a violation would pass silently)

## 給維護者

1. 憲章說每條原則都「點名一個 Check」，但有七處名不副實：第 1 條的檢查放過了「指向自己 repo 內東西」的標頭、也沒掃 hooks/；第 2、5 條、Safety Net 的憑證條、第 7、8 條根本沒有 Check。
2. 本次補上：第 1 條收緊並擴到 hooks/；第 2、5 條與憑證條各寫一支自動測試；第 7 條寫一支自動 lint ＋ 一份人工程序；第 8 條寫人工程序（自動化只會是裝飾，見下）。
3. 第 4 條：命令層點名 `egress_ctl.sh` 等腳本**不**違反「不得點名 relay」（理由見下），但 `configs/sites/nchc.config` 點名了特定站點的實作，違反；檢查收緊後改寫。
4. 憲章只做 PATCH（2.0.1）：只是把 Check 點名進去，沒有改任何規則的意思。**兩個檔案的標頭（detect_conditions.sh、methods_text.py）與 hooks/ 的標頭等其他 agent 合併後再補**，測試裡有一份明列、會自己報過期的暫時白名單。

## Findings

### 1. Invariant 1 Check accepts anything shaped like `# Not X:`

`tests/scripts_name_their_alternative.sh` only checked the line exists and the reason is 15+ characters. It did not look at X, and did not scan `hooks/`. Eight headers name something in this repo, not a maintained tool:

| File | Says "Not ..." |
|---|---|
| `scripts/intro.sh` | `settings.sh` |
| `scripts/env.sh` | a hook |
| `scripts/detect_conditions.sh` | a second interface detector |
| `scripts/record_adapter.sh` | a real ELN implementation written speculatively |
| `scripts/utils/wsl_ssh.sh` | a shell function |
| `scripts/setup_verify.sh` | `scripts/preflight.sh` |
| `scripts/runs_board_site_probe.sh` | `task_health.sh` |
| `scripts/methods_text.py` | writing a new methods paragraph |

`hooks/` has eleven files and not one carries a header. #30 deferred this as the maintainer's call; the constitution (I.1) says the header "MUST state its answer", and "Not our own other script" is not an answer to "what does somebody else already maintain".

### 2. Principles with no Check named

| Rule | State on main |
|---|---|
| I.2 (backend owns run state; no submission script, state machine, monitoring daemon; Seqera's nouns) | no Check named. Automatable: scan `scripts/` for submission commands, daemon markers, run-state stores; scan the command layer for `tw` nouns |
| II.5 (works without `hooks/` and `.claude-plugin/`, degraded) | "Check:" is a sentence, not a test or procedure. Automatable: copy the tree without them, run key scripts |
| Safety Net, credentials | tests cover "never printed" in places (`inspect_sides_test.sh`, `bsd_userland_test.sh`, `settings_test.sh` for mode 600) but no Check is named for the rule as a whole (never in git, never in a params file) |
| III.7 (nobody needs the maintainer) | "Check:" is a sentence. Partly automatable (no user-facing text tells the user to read PITFALLS or ask the maintainer); the rest needs a person |
| IV.8 (evidence before claims) | "Check:" is a sentence. Not automatable: whether a PITFALLS entry rests on a real failure needs a person. A lint for "has a date or a code block" would be green for every entry and prove nothing, so it is not written |

### 3. Invariant 4 Check is a vocabulary check for the word "relay" only

Rule: "The command layer MUST NOT name a scheduler, partition, queue or relay."

- `commands/downstream.md:85` names `configs/sites/nchc.config`: a specific site's implementation file, and a site name. **Violation**: a second site would have no such file, and the sentence is about "this site's resource-floor config", which the adapter contract (`docs/SITE_ADAPTER.md` §1) already names without a path.
- Commands name `scripts/egress_ctl.sh`, `scripts/egress_allow.sh`, `scripts/check_egress.py`. **Not a violation**: the rule bans naming the *relay* (the CONNECT proxy, `nf_relay.py`, its port and log), and these scripts are named for the contract's noun, egress (`docs/SITE_ADAPTER.md` §2), are reached only through `scripts/on_site.sh --script` (the adapter's one sanctioned transport), and the surrounding prose already says "the outbound channel" and "a site with unrestricted egress prints nothing". The same holds for `why_pending.sh` and `agent_ctl.sh` (contract 5, contract 3). What would be a violation is naming the proxy's own files and settings, so the check is tightened to ban `nf_relay`, `relay_denied`, `relay_port`, `nchc`, `taiwania`, `configs/sites` and login-node host names in the command layer.

## Reproduction (WSL, main 2dfedd1)

1. `bash tests/scripts_name_their_alternative.sh` on main: prints `OK: all 53 scripts under scripts/ name their alternative`, while the table above is true.
2. Rule 5: `grep -n "Check:" .specify/memory/constitution.md` for invariants 2, 5, 7, 8 and the credentials rule: no test file or doc section is named.
3. `grep -n "nchc" commands/*.md`: one hit, `downstream.md:85`; `bash tests/command_layer_is_site_neutral.sh` prints OK.

## Proposed Remediation

Per item, red first (the tightened or new check failing, or shown failing under a mutation), then the fix, then green:

1. Tighten I.1's check (external alternative, hooks/ scanned, explicit "Nothing existing" form); fix six headers; two scripts plus eleven hooks files on a commented temporary allow-list that reports them and fails when an entry goes stale.
2. New `tests/no_second_run_state_test.sh` (I.2), `tests/works_without_host_test.sh` (II.5), `tests/credentials_stay_in_settings_test.sh` (Safety Net, credentials), `tests/onboarding_self_contained_test.sh` (III.7 lint); manual procedures for III.7 and IV.8 in `docs/TESTING.md`.
3. Tighten `tests/command_layer_is_site_neutral.sh`; reword `commands/downstream.md:85`.
4. Constitution 2.0.1 (PATCH): name each Check, short amendment note, update citing documents. Any change beyond naming goes to the maintainer instead.

Out of scope: edits to `hooks/`, `scripts/on_site.sh`, `scripts/settings.sh`, `scripts/detect_conditions.sh`, `scripts/methods_text.py` (another agent); CI; merging.
