# 測試案例：四支 Taiwania-3 專用腳本標註「v2 only；nano4 用 $NFCORE_SITE_CONFIG」

<!--
Written by the verifier (CONTRACT mode). 本任務沒有 spec.md，依據是 `specs/t3-scripts-tagged/plan.md`。
維護者原話只有一句，且屬「不做清單」：「台灣杉三新功能（只修 bug 到 2027）」。
-->

**規格**：`specs/t3-scripts-tagged/plan.md`（本任務無 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應（測試變紅、點名是哪個檔案）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

標註那一行的完整內容（下稱「標註行」，一個字都不能差）：

`# Taiwania-3 only (v2); nano4 uses $NFCORE_SITE_CONFIG — see docs/SITE_ADAPTER.md`

四支腳本：`scripts/utils/boxes.sh`、`scripts/check_resource_contract.sh`、`scripts/tune_resources.sh`、`scripts/why_pending.sh`。

## User Story 1 — 同事一打開腳本就看到「只適用台灣杉三」的提醒（優先度 P1）

目標（計畫）：避免同事在 nano4 上誤用只適用 Taiwania-3 的資源腳本。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法：頂部註解加標註行（boxes.sh） | 功能 | 實作完成 | 在 `scripts/utils/boxes.sh` 找標註行 | 檔案中有且恰有一行與標註行完全相同（逐字比對，不是只比對關鍵字） | 自動：`tests/t3_scripts_are_tagged.sh` |
| TC-002 | 作法（check_resource_contract.sh） | 功能 | 實作完成 | 在 `scripts/check_resource_contract.sh` 找標註行 | 有且恰有一行與標註行完全相同 | 自動：`tests/t3_scripts_are_tagged.sh` |
| TC-003 | 作法（tune_resources.sh） | 功能 | 實作完成 | 在 `scripts/tune_resources.sh` 找標註行 | 有且恰有一行與標註行完全相同 | 自動：`tests/t3_scripts_are_tagged.sh` |
| TC-004 | 作法（why_pending.sh） | 功能 | 實作完成 | 在 `scripts/why_pending.sh` 找標註行 | 有且恰有一行與標註行完全相同（該檔原本第 2 行已有「see docs/SITE_ADAPTER.md」字樣，不能拿它充數；必須是標註行本身） | 自動：`tests/t3_scripts_are_tagged.sh` |
| TC-005 | 作法：「頂部註解」 | 功能 | 實作完成 | 逐支檢查標註行的位置 | 四支都是：標註行出現在檔案開頭那一段連續的 `#` 註解之內，在第一行可執行程式碼之前 | 自動：`tests/t3_scripts_are_tagged.sh` |
| TC-006 | 作法：不改行為（shebang 不能被擠走） | 功能 | 實作完成 | 看 `check_resource_contract.sh`、`tune_resources.sh`、`why_pending.sh` 的第 1 行 | 三支的第 1 行仍是 `#!/bin/bash`；`boxes.sh` 原本沒有 shebang，仍然沒有 | 自動：`tests/t3_scripts_are_tagged.sh` |
| TC-007 | 失敗先行測試：新增 `tests/t3_scripts_are_tagged.sh` | 功能 | 實作完成；在 Git Bash 或 WSL 單獨執行該檔 | `bash tests/t3_scripts_are_tagged.sh` | 結束碼 0；輸出能看出四支檔案各自檢查過，不是「整體掃過就算」 | 自動：`tests/t3_scripts_are_tagged.sh` |
| TC-008 | 失敗先行測試：「先寫、現在會紅」 | 例外 | 把新測試檔放在尚未改動四支腳本的 base 上 | 在 base 上執行 `bash tests/t3_scripts_are_tagged.sh` | 結束碼非 0，且輸出點名四支檔案都缺標註行（證明這個測試真的能失敗，不是空殼） | 自動：`tests/t3_scripts_are_tagged.sh` |
| TC-009 | 失敗先行測試：「四支檔案各 grep 到該行」 | 例外 | 實作完成後，在一份暫時副本裡只刪掉其中一支腳本的標註行（四支輪流各試一次） | 在副本上執行新測試 | 每一次都是結束碼非 0，並點名被刪的那一支；不會因為另外三支有就放行 | 自動：`tests/t3_scripts_are_tagged.sh` |

## User Story 2 — 只加註解，不改任何行為（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 作法：「不改行為」；不做：「不改腳本行為」 | 功能 | 實作完成 | 驗收者對四支腳本做 `git diff <base>...HEAD`；並跑依賴這些腳本的既有測試（`tests/relaunch_override_test.sh`、`tests/site_scripts_via_on_site.sh`、`tests/site_report_test.sh`、`tests/bsd_userland_test.sh`） | 四支腳本的差異只有新增的 `#` 註解行（可含一個空白行），沒有任何刪除或修改的非註解行；上述既有測試結果與 base 相同（綠） | 自動：既有測試；差異內容由驗收者逐行核對 |
| TC-011 | 不做：「不刪任何 T3 功能」 | 不在範圍 | 實作完成 | 比對 base 與 HEAD 四支腳本的函式定義、命令列選項（例如 `tune_resources.sh` 的 `--json`、`--trace`、`--config`）與檔案權限（`boxes.sh` 為 644，其餘三支為 755） | 函式、選項、權限與 base 完全相同；沒有任何 T3 功能被移除或停用 | 自動：既有測試；差異內容由驗收者逐行核對 |
| TC-012 | 原話：「台灣杉三新功能（只修 bug 到 2027）」（不做清單） | 不在範圍 | 實作完成 | 看 `git diff --stat <base>...HEAD` | 變動的檔案只有：四支腳本、`tests/t3_scripts_are_tagged.sh`、`specs/t3-scripts-tagged/` 底下的檔案；沒有新增任何台灣杉三新功能，也沒有動 `docs/SITE_ADAPTER.md`、`configs/` 或其他腳本 | 自動：既有測試；差異範圍由驗收者核對 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 不變式 4（一個叢集不等於全世界）；計畫：「既有 `tests/command_layer_is_site_neutral.sh` 仍須過」 | 功能 | 實作完成 | `bash tests/command_layer_is_site_neutral.sh` | 結束碼 0，輸出與 base 相同的通過結果；新增的標註沒有讓指令層出現站點專用字眼 | 自動：`tests/command_layer_is_site_neutral.sh` |
| TC-014 | 計畫「完成標準」：新測試綠；全套綠 | 功能 | 實作完成；工作樹乾淨 | 在 WSL 跑 `tests/run_all.sh`（見 CLAUDE.md「For the executor and verifier」） | 全部測試檔通過，統計行包含新增的 `t3_scripts_are_tagged.sh`；沒有任何既有測試被刪除、略過或放寬 | 自動：`tests/run_all.sh` |

<!--
IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
