# confirm.py/jobs.py：clean_work 種類、7 天到期、回覆處理 progress ledger

- [x] RED: `platform/tests/test_cleanup_confirm.py` (63 條，TC-001..TC-081 中自動的部分；TC-072/073/074/079 為閱卷手動) — 52 條紅。
- [x] GREEN: `confirm.py`（`JOB_KIND`、`CLEAN_PENDING_SECONDS`、`MAX_OPEN_CLEAN`、`create_pending` 依種類給期限與名額、`facts`、`FORGOTTEN_JOB_KINDS`、`open_clean_requests`）；`jobs.py`（期限 600／`ABF_PLATFORM_DEADLINE_CLEAN`、`CONFIRMED`、Google Batch 放行、`_check_clean` 四項核對、`clean_result`、`_apply_handover` 記 `work_cleaned_at`）。
- [x] 三處既有斷言加入 `clean_work`（以前／以後／理由）：
  - `test_resume_scope.py` 三通道測試：以前 JOB_KIND／CONFIRMED 各兩筆、KINDS 六種；以後各加 `clean_work`（KINDS 第七個）、函式名 two→three；理由：新種類。
  - `test_keep_submissions.py` TC-083：`set(JOB_KIND)` 加 `clean_work`；`forget not in approve` 未動。
  - `test_launch_platform.py` TC-018：`set(KINDS)` 加 `clean_work`。
- 附帶：`forget_content` 的 `kind IN (?, ?)` 改成依 `FORGOTTEN_JOB_KINDS` 長度產生占位符（沒改邏輯，只是讓第三種種類查得到）。
- 未動：`test_launch_platform.py:122-134` 迴圈（未加 `clean_work`）。
- 注意：計畫寫 MCP 工具數 12，但現行 `test_pat.py`／`test_oauth_mcp.py` 是 13；本片未碰 MCP，TC-067 改查「這些檔案不含 `clean_work`」。
- 卡住（全套 123/124 shard、994 passed、2 failed，HEAD 為 GREEN commit）：
  1. `test_cleanup_store.py::test_nothing_writes_clean_work_or_work_cleaned_at`（a 片 TC-030）斷言「`store.py` 以外的 `abf_platform/*.py` 都不含 `clean_work`」，與本片必改的 `confirm.py`／`jobs.py` 直接衝突；計畫沒把這條列為可更新的既有斷言，executor 不得自行改。需要 developer-agent 在計畫補上這條（把掃描改成排除 `confirm.py`／`jobs.py`，或改成「只有 store／confirm／jobs 含」）。
  2. `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched`：與本片無關，`docs/PLATFORM.md` 自 `BASE=6061925` 起就被別的片改過（`git diff 6061925 3278601 -- docs/PLATFORM.md` 非空），本分支沒碰 docs。
