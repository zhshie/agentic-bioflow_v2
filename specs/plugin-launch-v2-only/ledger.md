# plugin launch／setup skill 標明 tw 流程只適用 v2 progress ledger

- [x] 版本分流段加入 launch／setup SKILL.md；ce_apply.sh 頂部註解；MIGRATION.md 第 7 節對照表；新測試 tests/skills_name_the_v3_launch_path.sh 先紅後綠。
- [x] 既有測試 `tests/migration_doc_test.sh` 依 2026-10-22 裁決由 developer-agent 改兩處（executor 的修改被 auto-mode 分類器擋下，維護者 10-22 准由 developer-agent 直接改）：
  - TC-002：old＝`-ne 6`／`for i in 0 1 2 3 4 5`／expect 6 項；new＝`-ne 7`／`0 1 2 3 4 5 6`／expect 加第 7 項「From the v2 `tw` flow」。理由：本任務依計畫新增 MIGRATION.md 第 7 節，標題數的釘子要跟著動。
  - TC-005：old＝只在 `platform/abf_platform/cli.py` 找 `add_parser("<cmd>")`；new＝同時在它與 `platform/abf_launch/cli.py` 找（`launch` 子命令在後者註冊，docs/PLATFORM.md:309 本就寫 `abf-platform launch`）。檢查沒有放寬：子命令仍須在其中一檔真的有 `add_parser`。
  - 單獨重跑：`bash tests/migration_doc_test.sh` → all ok（10-22）。
