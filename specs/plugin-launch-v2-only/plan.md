---
id: plugin-launch-v2-only
title: plugin 的 launch／setup skill 標明「tw 流程只適用 v2；v3 用 abf-platform launch／MCP launch」
tier: B
kinds: docs
lane: L4
base: v3
---

# plugin-launch-v2-only（M1-09）

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/plugin-launch-v2-only/plan.md`。**只處理本任務**。

## 目標
用 Claude Code plugin 的人一打開 launch／setup skill 就知道：v3 的啟動走平台（`abf-platform launch` 或 MCP `launch`），下面那套 `tw`（Seqera CLI）流程只給 v2。使用者看得到的說明改變 → B 級，但不是網頁畫面 → verifier 通過＋CI 綠即可自合（維護者 10-21 裁示 14）。

## 維護者原話（verifier 出題用）
- 「自建平台、不依賴 Seqera；剩下是把還走 Seqera 的送出路徑換掉。」（裁示 2）
- 「v2/main 的 Seqera 路徑支援到 2027」（M1-08 的 README 措辭，供對齊）。

## 範圍：檔案
- `skills/launch/SKILL.md`、`skills/setup/SKILL.md`、`scripts/ce_apply.sh`（只動頂部註解）、`docs/MIGRATION.md`

## 作法
- 兩個 SKILL.md 開頭加一段「版本分流」：v3 → `abf-platform launch`／MCP `launch`（連到 `docs/PLATFORM.md`）；以下 `tw` 流程只適用 v2。不刪 v2 內容。
- `ce_apply.sh` 頂部註解加一行同樣意思。
- `MIGRATION.md` 加「從 v2 的 tw 流程到 v3 平台啟動」一節：對照表（v2 指令 → v3 做法）。

## 失敗先行測試
- 新增 `tests/skills_name_the_v3_launch_path.sh`：兩個 SKILL.md 與 `MIGRATION.md` 各 grep 到 `abf-platform launch`；先寫、現在會紅。
- `tests/command_layer_is_site_neutral.sh`、`tests/commands_scope_tw_to_the_workspace.sh` 仍須過（不得弱化）。

## 完成標準
三處有分流說明；新舊測試全綠。

## 不做
- 不刪 v2 流程、不改 plugin 版號、不改 `README.md`（M1-08）。

## 專長守則（docs）

（工作區沒有 `.claude/dev-profiles/docs.md`；本任務無專長守則。）

## 裁決（2026-10-22，developer-agent，回應 executor BLOCKED）
- 授權修改既有測試 `tests/migration_doc_test.sh`，**只改兩處、每處寫進 ledger（old／new／理由）**：
  1. TC-002 的 `## ` 標題數 6 → 7（因為本任務依計畫新增第 7 節「From the v2 `tw` flow to starting on the v3 platform」）。
  2. TC-005 的「每個 `abf-platform <子命令>` 都要在 cli.py 有 `add_parser`」：來源檔從只看 `platform/abf_platform/cli.py` 擴成同時看 `platform/abf_platform/cli.py` 與 `platform/abf_launch/cli.py`（`launch` 子命令的實作在後者）。檢查本身不放寬：子命令仍必須在其中一個檔案真的有 `add_parser("…")`。
- 其餘不動；不改 TC-016／017／019。範圍檔新增 `tests/migration_doc_test.sh`。
- 合約（verifier）對「開頭」「英文節名」「不只 grep 一個字串」的四條非阻擋決定，照合約。
