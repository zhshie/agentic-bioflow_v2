# Bug Assessment: an aborted run logs "Report file already exists"

- **Slug**: abort-report-overwrite
- **Created**: 2026-10-15
- **Source**: NCHC recheck 2026-10-15, run fu3-cancel (.nextflow.log lines 1135, 1161): `AbortOperationException: Report file already exists: .../results/pipeline_info/execution_report_<stamp>.html -- enable the 'report.overwrite' option`; same for timeline. Recorded in specs/007b-launch/acceptance-nchc.md.
- **Verdict**: valid  **Severity**: low (results not affected; a scary ERROR in the log of every cancelled run)

## 給維護者

1. 取消分析時，Nextflow 會把「寫報告」做兩次，第二次因為檔案已經在了就報錯。結果不受影響，但每次取消都多一條嚇人的錯誤。
2. 修法：平台產生的 `nextflow.config` 末尾一律加上允許覆寫報告與時間軸（同一次 run 自己的檔，不影響別的 run）。

## 維護者的例子（原文）

- 「取消的分析，記錄裡不要再出現 Report file already exists。」
- 「正常跑完的分析，報告照舊產生。」

## Root Cause (high confidence)

Nextflow 26.04.7 on abort runs the workflow-complete observers twice (`Session.destroy()` calls `shutdown0()` again; same cause as the double `complete` in PITFALLS 42-44). ReportObserver/TimelineObserver refuse to overwrite unless `report.overwrite`/`timeline.overwrite` is true.

## Proposed Remediation

- First search upstream (nextflow-io/nextflow issues/PRs) for this double render; cite what you find in the ledger. If a released Nextflow fixes it, say so; still apply the config fix for the pinned 26.04.7.
- In `platform/abf_station/launch.py` (the single file allowed to render the bundle), append to the rendered `nextflow.config` a clearly commented block setting `report.overwrite = true` and `timeline.overwrite = true` (only these two; not trace/dag). The user's own config text stays first and unchanged; the block is part of the shown bundle and its hash.
- Red first: a test in `platform/tests/test_station_launch.py` asserting the rendered config ends with both settings and that the user's config text is kept verbatim before it. Update any hash/golden expectations only where the new block is the sole difference, and list each in the ledger.
- If feasible offline, a test with the pinned real Nextflow (as test_nextflow_e2e.py does) that aborts a run and asserts no "already exists" in .nextflow.log; if not feasible, mark it for the maintainer's NCHC recheck.
- Docs: PITFALLS entry; note in docs/PLATFORM.md where the rendered config is described.
- Out of scope: trace/dag overwrite, the double `complete` itself, CI config, plugin/.
