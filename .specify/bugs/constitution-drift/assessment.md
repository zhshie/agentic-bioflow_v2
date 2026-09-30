# Bug Assessment: wording drift from the constitution, and small fixes (audit batch E)

- **Slug**: constitution-drift
- **Created**: 2026-09-30
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/33 (constitution audit batch E, plus the `mv` item added from #29)
- **Verdict**: valid
- **Severity**: medium (items E1-E4, E9), low (the rest)

## 給維護者

1. 十項小修：說明文字跟憲法講法不一致、token 存放位置寫錯、權限量不到時不吭聲、回報會寄到你的 GitHub（別人 fork 後也是）、一處泛用的「自己想辦法修」出口。
2. 兩項改行為（你已決定）：搬走 results/rawdata/analysis 時要問你；中文專業詞（定序、擴增子…）會導進正式流程。
3. 文件裡的個人路徑是佐證，不動。

## Items (each verified on main 0e83b31 by the developer unless marked)

| # | Where | Problem | Remediation |
|---|---|---|---|
| E1 | `commands/setup.md` "When a step fails" ("You may attempt to fix this step") | A catch-all that bypasses the one off-design path (invariant 10); `commands/downstream.md` and `commands/finish.md` have failure branches that point nowhere | Point each at `skills/operational/SKILL.md` "Off-design: when nothing here covers it" (record with `scripts/report.sh`, try within the safety net, offer the report). Extend `tests/off_design_single_path.sh` so "attempt to fix"-style open-ended wording is caught, not only the two literal phrases it knows today |
| E2 | `commands/setup.md` step 3 | Tells the user to save the token to `_personal/.seqera_token`; the code reads `<root>/config/.seqera_token` (`scripts/settings.sh`, `token_file`) | Name the path the code uses (or the settings.sh command that writes it), and say it is checked by reading it back, not "chmod 600" |
| E3 | `scripts/settings.sh` privacy check, the `private|unknown) return 0` branch | When privacy cannot be measured (e.g. Windows without powershell.exe) the token is written with nothing said (invariant 11: measured, never assumed; invariant 13: say so) | Keep writing, but print a visible warning that privacy could not be measured and how to check it by hand; test it |
| E4 | `scripts/report.sh` (`REPO="zhshie/agentic-bioflow_v2"`, `login = zhshie`), `skills/operational/SKILL.md` | Hard-coded repo and maintainer: a fork or another lab's deployment files its reports here (invariant 3) | Add `"repository": "https://github.com/zhshie/agentic-bioflow_v2"` to `.claude-plugin/plugin.json`; report.sh derives owner/repo from it (env `REPORT_REPO` overrides); "maintainer" = that repo's owner; SKILL.md names the repository from plugin.json, not a literal |
| E5 | `skills/operational/SKILL.md`, section "On a host without these hooks" | States "It must not touch the site, submit a run, or delete anything" as a rule; that is a ROADMAP "principle waiting for a check", deliberately not in the constitution (Governance: no restating differently) | Reword as the intended direction, not yet enforced, and keep the practical instruction (confirm by hand with the user) |
| E6 | `CLAUDE.md` (settings "mode 600"), `skills/operational/SKILL.md` safety-net paragraph, `commands/setup.md` | "mode 600" restates the constitution's "readable by the owner only", which is measured by reading back (mode on Unix, ACL on Windows) | Use the constitution's wording |
| E7 | `commands/setup.md` synced-folder paragraph vs `scripts/settings.sh` refusal text | Apparent contradiction: setup says a synced folder is what this is designed for; settings.sh calls a cloud-drive folder "no place for a token". Both are right in their case: a folder synced by a client inside the user profile holds owner-only permissions; a cloud drive mounted as its own drive letter on Windows has no ACLs and is refused | Say both cases in setup.md; no behaviour change |
| E8 | `docs/PRINCIPLES.md` invariants 2, 6, 7, 9; `docs/SITE_ADAPTER.md:27`, `skills/operational/SKILL.md` (principles citation), `commands/downstream.md:131`; `skills/operational/SKILL.md` reference to `scripts/session_start.sh` | Rule statements differ from the constitution (2 omits "Nextflow's own records where it is not"; 6 omits "never from a per-pipeline file in this repository"; 7 adds "before their first real run"; 9's title narrows the scope); citations treat PRINCIPLES as the authority; a reference to a file that does not exist (it is `hooks/session_start.sh`) | Align the four with the constitution (PRINCIPLES keeps reasoning only); cite the constitution for rules; fix the reference |
| E9 | `hooks/confirm_cleanup.sh`, `mv` | Moving `rawdata/`, `results/` or `analysis/` is not gated; moved to a scratch area and cleaned, it is deleted | **Maintainer decision 2026-09-30: ask.** When any `mv` source (every argument but the last) is or lies under a protected directory → `ask`. Moving files INTO those directories stays allowed (that is writing). Tests first, including the read-only and write-into cases staying quiet |
| E10 | `hooks/plugin_intro.sh` topic words | A Chinese request with action intent ("幫我分析這批定序資料") is not routed to the formal flow; topic words are English only (invariant 12) | **Maintainer decision 2026-09-30: add specialist Chinese terms only** — 定序, 測序, 擴增子, 轉錄體, 轉錄組, 樣本表, 總體基因體, 宏基因組 (plus their simplified forms where different). No generic words (分析, 流程, 資料) - the maintainer uses Chinese for unrelated work in the same shell. Tests: the example routes; "幫我分析職涯選項" and "定序是什麼" (a pure question) do not |
| E11 | `docs/DOWNSTREAM.md:12`, `docs/HANDOFF.md` | Personal cluster paths | Not changed: they are evidence of a real run, not paths users copy (invariant 3 concerns what the code uses) |

## Risks

- E9 and E10 change behaviour in hooks → the manual half of `docs/TESTING.md` applies.
- E4 changes where reports go; `tests/report_test.sh` must cover the derived repo and the override.
- E1 must not make any existing command's normal failure path worse; every rewired branch is read by a person reviewing the diff.
