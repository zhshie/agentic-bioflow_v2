# estimate-su: the SU formula

Source: issue #119 'SU cost formula': `estimate_su` is in ROADMAP (stage 2, 009 tool list); rates appear only in docs/POSITIONING.md (line ~82: 國科會計畫 0.08 元/SU、學界 0.24, source lions.nchc.org.tw). Proposal (maintainer-reviewed issue): sum of cpus x realtime x partition factor from the trace, rates in `configs/sites/`, monthly total computed on read; cloud bills on the agent side, shown as '—' until Stage 4. B tier: a number users will see.

NOTE: PR #133 (keep-submissions) also edits platform/abf_platform/actions/__init__.py. This task only ADDS one function there (append near the other read actions); a later merge conflict is expected and is resolved by keeping both.

## Build
1. `configs/sites/su_rates.json`: per site, per partition: `factor` (SU per cpu-hour) and money rates (`nstc_twd_per_su`: 0.08, `academic_twd_per_su`: 0.24, with `source`: the lions.nchc.org.tw URL from POSITIONING.md). Partition factors: do NOT invent numbers. Look for NCHC partition SU factors in the repo (configs/sites/nchc.config, docs/SITE_ADAPTER.md, docs/LAB_AGENTS.md, docs/PITFALLS.md). If none is recorded, set every factor to null and make the code report SU as unknown ('—') for that partition, with the gap logged in the ledger as owed (maintainer/lab-agent to fill from NCHC).
2. `platform/abf_platform/su.py` (stdlib only): `su_of_tasks(tasks, site, rates)` = sum over tasks of cpus x realtime_hours x factor(partition); a task whose partition has no factor, or no cpus/realtime, makes the total `None` and lists why; never guess. `month_total(user, month)` computed on read from the run index (no stored totals: tests/no_second_run_state_test.sh must stay green).
3. Action `estimate_su(caller, run_name)` in actions/__init__.py: owner-only like get_run (another user's run = not found); returns {su, twd_nstc, twd_academic, unknown_reasons}. Read the trace fields the receiver already stores (receiver.py / records.py); if the needed per-task fields (cpus, realtime, queue/partition) are not stored, say so in the ledger and return unknown - do not change the receiver in this task.
4. NOT in this task: the MCP tool and the web display (they come with 012d / the parity work); list them in the ledger as owed.

## Tests (write first)
platform/tests/test_estimate_su.py: formula on a hand-made trace (2 tasks, known cpus/realtime/factor -> exact SU and TWD); missing factor -> None with a reason; another user's run -> not found; month_total sums only that user's runs of that month; no new table/column is created.

## Out of scope
receiver changes, MCP/web, CHANGELOG.md, docs/PLATFORM.md (another task).

## Rulings after acceptance (developer-agent, 2026-10-18; maintainer: 「都照你的建議」)
- E1 First `git merge origin/v3` (plain merge; #133 keep-submissions landed and also edits actions/__init__.py — keep both sides).
- E2 Month total uses Asia/Taipei (UTC+8), by run start time. A month with any unknown run is unknown (keep current rule). A month with no runs is 0.
- E3 Rates stay 0.08 / 0.24 TWD per SU with their source; factors stay null until NCHC confirms (owed, lab-agent).
