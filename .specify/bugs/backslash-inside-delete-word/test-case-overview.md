# 測試案例總覽：夾在刪除指令名字中間的反斜線（issue #66）

狀態：合約已確認（2026-10-10，verifier）

**規格**：`.specify/bugs/backslash-inside-delete-word/assessment.md`　**明細**：`test-case.md`

## 一眼看完

| 區塊 | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| 修復 1 — 有 jq：中間夾反斜線也被判到（TC-001..012） | 12 | 0 | 0 | 12 |
| 修復 2 — 有 jq：正常指令不誤問（TC-013..020） | 8 | 0 | 0 | 8 |
| 修復 3 — 沒有 jq：不無聲放行（TC-021..030） | 5 | 5 | 0 | 10 |
| 修復 4 — 大輸入與速度（TC-031..034） | 4 | 0 | 0 | 4 |
| 憲法與安全網（TC-035..038） | 3 | 1 | 0 | 4 |
| 不在範圍（TC-039..041） | 0 | 0 | 3 | 3 |
| **合計** | 32 | 6 | 3 | 41 |

自動驗證 38 條、手動驗證 3 條（TC-039、TC-040、TC-041，需在 `docs/TESTING.md` 補上具體步驟）。

## 計畫補強（verifier 審查，必過）

1. 沒有 jq 的備援：在原樣文字之外**再多比對一份**去掉反斜線的文字，涵蓋 `looks_delete_shaped`（`hooks/confirm_cleanup.sh:102-117`）的所有字樣，含 ` nextflow ... clean `；不能取代原樣。main 上 `t\ar --remove-files` 已被擋（TC-025 防退步），`r\m`、`remo\ve`、`cl\ean`、`\rm` 放行（TC-021..024 真修復）。
2. 現有 300 KB 計時測試沒有反斜線，碰不到新程式碼；要新增每行含反斜線的 300 KB 內容（TC-033、034）。
3. 每個片段有三欄（原文、去引號版、指令字，`hooks/confirm_cleanup.sh:296-299`、`:724-733`）；去反斜線要整行處理三欄，並在大輸入過濾之前做。
4. `tests/confirm_cleanup_behind_heredoc_test.sh:34-41` 斷言沒有反斜線的大輸入恰好 3 次 awk；新增的一次只在有反斜線時才跑（TC-032）。

## 覆蓋檢查

- issue #66 的四條指令：TC-001（`r\m`）、TC-002（`t\ar`）、TC-003（`remo\ve`）、TC-004（`cl\ean`）。是
- issue 的對照組（`printf 'a\nb'`、grep 正規式、sed 正規式、Windows 路徑）：TC-013..017，沒有 jq 的版本 TC-026..030。是
- issue 的「300 KB 約 3 秒」：TC-033、TC-034。是
- 計畫三項修改：第 1 項 TC-001..012；第 2 項 TC-031、TC-032；第 3 項 TC-021..025。是
- 計畫「不在範圍」共 3 條，全部都有「不在範圍」測試案例：是（TC-039、TC-040、TC-041）
- 驗證過的基準（main bec2ea5，WSL，jq 1.7.1）：有 jq 四條全部無聲放行；沒有 jq 時 `r\m`、`remo\ve`、`cl\ean`、`\rm` 放行（exit 0），`t\ar --remove-files` 已被擋。

## 撰寫者不確定的地方（developer-agent 已裁定，2026-10-10）

- TC-018：預期改為「與 `echo rm -rf <results 路徑>` 在 main 上的判定相同」，執行者先在 main 量出該判定再寫進測試。
- TC-033 的 3 秒只適用 Linux/WSL；原生 Git Bash 沿用現有測試的 20 秒上限。

## 核可紀錄

無（verifier 合約確認；A 級，維護者未另行核可）。
