---
id: t3-scripts-tagged
title: 四支 Taiwania-3 專用腳本標註「v2 only；nano4 用 $NFCORE_SITE_CONFIG」
tier: A
kinds: docs
lane: L3
base: v3
---

# t3-scripts-tagged（M1-10）

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/t3-scripts-tagged/plan.md`。**只處理本任務**。

## 目標
避免同事在 nano4 上誤用只適用 Taiwania-3 的資源腳本。

## 維護者原話（verifier 出題用）
- 「台灣杉三新功能（只修 bug 到 2027）」（不做清單）。

## 範圍：檔案
- `scripts/utils/boxes.sh`、`scripts/check_resource_contract.sh`、`scripts/tune_resources.sh`、`scripts/why_pending.sh`

## 作法
- 四支腳本頂部註解各加一行：`# Taiwania-3 only (v2); nano4 uses $NFCORE_SITE_CONFIG — see docs/SITE_ADAPTER.md`。不改行為。

## 失敗先行測試
- 新增 `tests/t3_scripts_are_tagged.sh`：四支檔案各 grep 到該行；先寫、現在會紅。既有 `tests/command_layer_is_site_neutral.sh` 仍須過。

## 完成標準
四行註解在；新測試綠；全套綠。

## 不做
- 不改腳本行為、不刪任何 T3 功能。

## 專長守則（docs）

（工作區沒有 `.claude/dev-profiles/docs.md`；本任務無專長守則。）
