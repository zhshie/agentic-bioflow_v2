# 測試案例：013a 交付包裡的「事實報告」範本（不含 AI 文字）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Write every row so that it can be
judged without reading code: what is set up, what the person or the system does,
what must be seen. No internal jargon without a one-line explanation.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/013a-report-facts/plan.md`（本功能沒有 spec.md；依維護者指示，案例只從計畫的內容與「Rulings after contract round 1」R1–R7 推出，計畫沒寫的行為不出題）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

名詞說明（計畫原文用語）：

- **事實報告**：`report.md`，只由「檔案」填出來的報告，不是模型寫的。
- **provenance.json**：`scripts/collect_provenance.py` 從每次執行（run）的輸出檔整理出的紀錄（版本、參數、指令）。
- **methods.md**：`scripts/methods_text.py` 產生的「方法」段落。
- **not recorded**：欄位在檔案裡找不到時，報告固定寫的字樣（絕不猜）。
- **帶測試資料夾的建置**：測試自己在暫存資料夾組一個專案（做法同 `tests/build_package_test.sh`），然後跑 `scripts/build_package.sh`。下文簡稱「標準夾具」：兩次執行 `demo_20260101`（有 MultiQC 報告、`params_*.json` 內 `input` 為 `/data/lab/private/samples_v2.csv`）與 `demo_20260102`（沒有 MultiQC、沒有 `input` 參數），版本檔皆為 `Workflow: nf-core/demo: v1.0.0`、`Nextflow: 25.10.4`。
- **手工 JSON**：測試直接用手寫的 provenance JSON 與 methods.md 呼叫 `scripts/report_facts.py --provenance <檔> --methods <檔> --out <檔>`（計畫 R5 的介面）。

## User Story 1 — 事實報告 report.md 只用檔案填寫、缺的就寫 not recorded（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 Build 1（五個小節） | 功能 | 標準夾具，已建置出 `submission/report.md` | 讀 `report.md` 的標題 | 依序出現五個標題：Runs、Inputs、Methods、Quality control、Interpretation，各出現一次，沒有別的一級／二級小節 | 自動：`tests/report_facts_test.sh` |
| TC-002 | 計畫 Build 1（Runs）；R3 | 功能 | 標準夾具 | 讀 `report.md` 的 Runs 小節，對照 `submission/provenance.json` | 兩次執行各有一段；pipeline 顯示 `nf-core/demo`、版本顯示 `v1.0.0`、run name 分別是 `demo_20260101` 與 `demo_20260102`（`run_dir` 的最後一段）；順序與 provenance.json 內相同 | 自動：`tests/report_facts_test.sh` |
| TC-003 | R3（run id） | 功能 | 手工 JSON：某次執行帶 `platform_run_id` 為 `abc123` | 呼叫 `report_facts.py` | 該次執行的 run id 欄顯示 `abc123` | 自動：`tests/report_facts_test.sh` |
| TC-004 | R3（run id）；計畫「缺的值寫 not recorded」 | 例外 | 標準夾具（建置時沒有給 run id，所以 provenance.json 沒有 `platform_run_id`） | 讀 Runs 小節的 run id 欄 | 兩次執行的 run id 欄都是 `not recorded`，沒有出現任何自編的編號 | 自動：`tests/report_facts_test.sh` |
| TC-005 | R3（start/end/status）；計畫 Build 1 | 例外 | 標準夾具（provenance.json 沒有開始／結束／狀態欄位） | 讀每次執行的 start、end、status 三行 | 這三行（標籤不分大小寫，以 start／end／status 開頭）各自的值都是 `not recorded`；沒有任何日期時間，也沒有 completed、success、failed 之類猜出來的狀態字 | 自動：`tests/report_facts_test.sh` |
| TC-006 | 計畫 Build 1「缺值寫 not recorded」；R3 | 例外 | 手工 JSON：某次執行沒有 `workflow` 欄位（沒有 pipeline 名稱與版本） | 呼叫 `report_facts.py` | 該次執行的 pipeline 與 version 兩欄都是 `not recorded`；不出現 `unknown`、空白或猜的名稱 | 自動：`tests/report_facts_test.sh` |
| TC-007 | R1（Inputs） | 功能 | 標準夾具：`demo_20260101` 的參數檔 `input` 為 `/data/lab/private/samples_v2.csv` | 讀 Inputs 小節 | `demo_20260101` 那一項顯示 `samples_v2.csv`（只有檔名）；整份 `report.md` 找不到 `/data/lab/private` | 自動：`tests/report_facts_test.sh` |
| TC-008 | R1（Inputs 缺值） | 例外 | 標準夾具：`demo_20260102` 沒有 `input` 參數 | 讀 Inputs 小節 | `demo_20260102` 那一項是 `not recorded` | 自動：`tests/report_facts_test.sh` |
| TC-009 | 計畫 Build 1（Methods 逐字）；R5 | 功能 | 標準夾具 | 取出 `report.md` 的 Methods 小節內容，與 `submission/methods.md` 比對 | 小節內容與 methods.md 逐字相同（一個字都沒改、沒刪、沒加） | 自動：`tests/report_facts_test.sh` |
| TC-010 | 計畫 Tests（Methods 等於 methods_text.py 的輸出） | 功能 | 標準夾具（網路抓取關閉，同 build_package_test.sh） | 另外直接執行 `scripts/methods_text.py` 對同一批 results，得到輸出 | `report.md` 的 Methods 小節與該輸出逐字相同 | 自動：`tests/report_facts_test.sh` |
| TC-011 | R4（有 MultiQC） | 功能 | 標準夾具：`demo_20260101` 的 `results/multiqc/multiqc_report.html` 存在 | 讀該次執行在 Quality control 小節的項目 | 有一個指向 `../runs/demo_20260101/results/multiqc/multiqc_report.html` 的連結（以 `submission/` 為起點的相對路徑，不是絕對路徑），連結後面接 ` (outside this package)`；且從 `submission/` 照這個相對路徑真的找得到那個檔 | 自動：`tests/report_facts_test.sh` |
| TC-012 | 計畫 Build 1「MultiQC report not found」 | 例外 | 標準夾具：`demo_20260102` 沒有任何 MultiQC 報告 | 讀該次執行在 Quality control 小節的項目 | 該項寫 `MultiQC report not found`，沒有任何連結；`demo_20260101` 的連結照常存在（兩次執行互不影響） | 自動：`tests/report_facts_test.sh` |
| TC-013 | 計畫 Build 1「if it exists … never invent」；R4 | 例外 | 手工 JSON：`quality_report` 指向一個已被刪掉的檔案 | 呼叫 `report_facts.py` | 該次執行寫 `MultiQC report not found`，不輸出指向不存在檔案的連結 | 自動：`tests/report_facts_test.sh` |
| TC-014 | R4（JSON 沒帶路徑時自己找） | 功能 | 手工 JSON：沒有 `quality_report` 欄位，但該次執行的 `results/` 底下確實有 `multiqc_report.html` | 呼叫 `report_facts.py`，`--out` 放在與 `runs/` 同層的 `submission/` | 該次執行出現指向那個 html 的相對連結（後接 ` (outside this package)`） | 自動：`tests/report_facts_test.sh` |
| TC-015 | 計畫 Build 1（Interpretation 留白）；Decision | 功能 | 標準夾具 | 讀 Interpretation 小節 | 標題之後恰好只有一行非空白的文字，內容是告訴人「這一節由你自己來寫」；沒有任何解讀、結論或結果描述（措辭由驗收者閱讀確認） | 自動：`tests/report_facts_test.sh` |
| TC-016 | R2（可重現、無時間戳記） | 功能 | 標準夾具的 provenance.json 與 methods.md | 用 `report_facts.py` 對同樣輸入連跑兩次，輸出到兩個檔 | 兩個檔逐位元組相同；內容沒有時間戳記、主機名稱 | 自動：`tests/report_facts_test.sh` |
| TC-017 | R1、R4；憲法第 3 條精神 | 功能 | 標準夾具（暫存資料夾路徑已知） | 在 `report.md` 搜尋暫存資料夾的絕對路徑與家目錄路徑 | 找不到任何絕對路徑；所有檔案參照都是檔名或 `../` 開頭的相對路徑 | 自動：`tests/report_facts_test.sh` |
| TC-018 | R5（只讀已產生的檔，不重跑） | 功能 | 手工 JSON 與一份手寫的 methods.md（內含獨特字串 `HAND-WRITTEN-MARKER-7`，這是 methods_text.py 不可能產生的） | 呼叫 `report_facts.py` | `report.md` 的 Methods 小節含 `HAND-WRITTEN-MARKER-7`；Runs 的值等於手工 JSON 裡寫的值（證明它讀你給的檔，沒有重新跑 collect_provenance.py 或 methods_text.py） | 自動：`tests/report_facts_test.sh` |
| TC-019 | 計畫 Tests（缺欄位 → not recorded） | 例外 | 手工 JSON：某次執行只有 `results` 與 `run_dir`，其餘欄位全無 | 呼叫 `report_facts.py` | 程式正常結束並寫出報告；該次執行除 run name 外的每個事實欄位都是 `not recorded`；沒有報錯堆疊 | 自動：`tests/report_facts_test.sh` |
| TC-020 | 計畫 Out of scope「No AI call of any kind」 | 不在範圍 | `scripts/report_facts.py` 原始碼；一個沒有網路、沒有任何模型金鑰環境變數的環境 | 檢查原始碼的 import 與字串；在無網路環境執行一次 | 原始碼只 import Python 標準函式庫，沒有任何網路／HTTP／模型服務相關模組或字樣（如 urllib、http.client、socket、requests、anthropic、openai）；離線也能照常產出報告 | 自動：`tests/report_facts_test.sh` |
| TC-021 | R1（013a 不做 checksum） | 不在範圍 | 標準夾具，並在專案內放一個看似 input_checksums 輸出的檔案 | 讀 `report.md` | 沒有任何 64 位十六進位的雜湊字串，也沒有 `checksum`／`sha256` 字樣出現在 Inputs 小節（雜湊留給 013b） | 自動：`tests/report_facts_test.sh` |

## User Story 2 — 組包時把 report.md 放進交付包，且不蓋掉人改過的版本（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 計畫 Build 2（放進交付包） | 功能 | 標準夾具，第一次執行 `scripts/build_package.sh <專案>` | 看 `submission/` | `report.md` 存在、非空，與 `provenance.json`、`methods.md` 在同一層，且有 TC-001 的五個標題；建置結束碼為 0 | 自動：`tests/build_package_test.sh` |
| TC-031 | R2（雜湊檔） | 功能 | 同 TC-030 | 讀 `submission/.report.md.sha256` | 檔案存在，裡面的 sha256 等於剛產生的 `report.md` 的 sha256 | 自動：`tests/build_package_test.sh` |
| TC-032 | R2（沒人改過 → 原地覆蓋） | 功能 | 已建置過一次，`report.md` 沒被動過，專案資料也沒變 | 再執行一次 `build_package.sh` | `report.md` 與上一次逐位元組相同；`submission/` 沒有 `report.facts.md`；stderr 沒有提到 `report.facts.md` | 自動：`tests/build_package_test.sh` |
| TC-033 | R2（沒人改過 → 內容更新） | 功能 | 已建置過一次，`report.md` 沒被動過；然後把 `demo_20260101` 參數檔的 `input` 改成 `/data/lab/private/samples_v3.csv` | 再執行一次 `build_package.sh` | `report.md` 的 Inputs 變成 `samples_v3.csv`；沒有 `report.facts.md`；`.report.md.sha256` 已更新為新 `report.md` 的雜湊 | 自動：`tests/build_package_test.sh` |
| TC-034 | R2（report.md 不見了 → 重寫） | 功能 | 已建置過一次，然後刪掉 `submission/report.md`（雜湊檔還在） | 再執行一次 `build_package.sh` | `report.md` 重新出現；沒有 `report.facts.md` | 自動：`tests/build_package_test.sh` |
| TC-035 | 計畫 Build 2；R2（人改過 → 不蓋掉） | 例外 | 已建置過一次；人在 `report.md` 的 Interpretation 下面加了一句「樣本 A 的豐富度較高」 | 再執行一次 `build_package.sh` | `report.md` 與人改完的版本逐位元組相同（那句話還在，其餘沒被動） | 自動：`tests/build_package_test.sh` |
| TC-036 | 計畫 Build 2；R2 | 例外 | 同 TC-035，且此時專案資料已改成 `samples_v3.csv` | 再執行一次 `build_package.sh` | `submission/report.facts.md` 出現，內容是以最新資料新產生的報告（Inputs 顯示 `samples_v3.csv`、Interpretation 為空） | 自動：`tests/build_package_test.sh` |
| TC-037 | 計畫 Build 2「say so on stderr」；R2 | 例外 | 同 TC-035 | 再執行 `build_package.sh`，把 stderr 單獨存起來 | stderr 裡關於這件事的訊息恰好一行，同一行同時寫出 `report.md` 與 `report.facts.md` 兩個檔名 | 自動：`tests/build_package_test.sh` |
| TC-038 | R2（有 report.md 但沒有雜湊檔） | 例外 | `submission/report.md` 存在（內容隨意），但 `submission/.report.md.sha256` 不存在 | 執行 `build_package.sh` | 視為被人改過：`report.md` 原封不動，新報告寫到 `report.facts.md`，stderr 照 TC-037 的方式說明 | 自動：`tests/build_package_test.sh` |
| TC-039 | R2（舊的 report.facts.md 被覆蓋） | 例外 | 已有一份舊的 `report.facts.md`（內容為 `OLD`），`report.md` 是人改過的 | 再執行 `build_package.sh` | `report.facts.md` 變成新內容（不含 `OLD`）；`submission/` 裡沒有 `report.facts.md.1`、`report.facts.md.bak` 之類累積的檔案 | 自動：`tests/build_package_test.sh` |
| TC-040 | 計畫 Build 2「update the header comment list」 | 功能 | `scripts/build_package.sh` 開頭那段說明註解 | 讀「What it assembles」清單 | 清單裡有 `report.md` 一項，並寫明它由 `scripts/report_facts.py` 產生（此測試只能確認字樣存在，措辭由驗收者閱讀確認） | 自動：`tests/build_package_test.sh` |
| TC-041 | R4（MultiQC 不複製進包，留給 013b） | 不在範圍 | 標準夾具，建置完成 | 在 `submission/` 底下找 `multiqc_report.html` | 找不到任何 MultiQC html；報告只連到包外原位置並標明 ` (outside this package)` | 自動：`tests/build_package_test.sh` |
| TC-042 | 計畫 Out of scope（不做網頁、不動 platform/、docs/PLATFORM.md、CHANGELOG.md）；R7 | 不在範圍 | 本功能的分支 | 驗收者讀 `git diff main...HEAD --stat` 與內容 | 變動檔案裡沒有 `platform/` 底下的任何檔、沒有 `docs/PLATFORM.md`、沒有 `CHANGELOG.md`；也沒有新增任何網頁、路由或 html 產出；沒有任何 AI／模型呼叫被加進去 | 手動：驗收者讀 diff（依計畫 R7；`docs/TESTING.md` 目前沒有對應步驟） |

## 憲法與安全網

本功能新增一支寫進使用者交付包的腳本，碰到「憲法第 9 條（寫給人的東西要指回檔案、缺口要明寫）」「第 1 條（每支腳本寫明現成替代品）」「第 3 條（不寫死路徑）」「第 2 條（不另存一份執行狀態）」，以及計畫第 3 點點名的可攜性檢查。安全網（hooks、啟動確認、刪檔確認、憑證）本功能不碰，故不出題。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-C01 | 第 9 條：交付包內容不憑記憶 | 功能 | 實作完成 | 執行 `bash tests/principle_9_test.sh` | 全部通過（含原本檢查 `build_package.sh` 缺口標記的項目），結束碼 0 | 自動：`tests/principle_9_test.sh` |
| TC-C02 | 第 1 條：腳本開頭寫明現成替代品 | 功能 | 新檔 `scripts/report_facts.py` 已存在 | 執行 `bash tests/scripts_name_their_alternative.sh` | 通過；`report_facts.py` 前 40 行內有合格的 `# Not <工具>: <理由>` 或 `# Nothing existing: <理由>`（理由至少 15 字） | 自動：`tests/scripts_name_their_alternative.sh` |
| TC-C03 | 第 3 條：不寫死路徑 | 功能 | 實作完成 | 執行 `bash tests/no_hardcoded_paths.sh` | 通過，結束碼 0 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-C04 | 計畫 Build 3（可攜 bash） | 功能 | 實作完成 | 執行 `bash tests/bash32_arrays_test.sh` | 通過（`build_package.sh` 新增的部分沒有 bash 3.2 不支援的陣列用法） | 自動：`tests/bash32_arrays_test.sh` |
| TC-C05 | 計畫 Build 3（可攜 bash） | 功能 | 實作完成 | 執行 `bash tests/bsd_userland_test.sh` | 通過（新增的雜湊、檔案比對等指令在 macOS／BSD 工具下也成立） | 自動：`tests/bsd_userland_test.sh` |
| TC-C06 | 計畫 Build 3（require_python.sh） | 功能 | 新檔 `scripts/report_facts.py` | 讀檔案開頭 | 開頭採用與 `scripts/collect_provenance.py` 相同的做法：載入 `require_python.sh` 並呼叫 `require_python`，然後才用 python3 執行；內容只用 Python 標準函式庫（此測試只能確認寫法存在，無法證明在壞掉的 python 下的訊息，措辭由驗收者閱讀確認） | 自動：`tests/report_facts_test.sh` |
| TC-C07 | 第 2 條：不另存一份執行狀態 | 功能 | 實作完成 | 執行 `bash tests/no_second_run_state_test.sh` | 通過；`report.md` 與 `.report.md.sha256` 沒有被判成第二份執行狀態 | 自動：`tests/no_second_run_state_test.sh` |
| TC-C08 | 既有行為不退步 | 功能 | 實作完成 | 執行 `tests/build_package_test.sh`、`tests/package_crate_test.sh`、`tests/collect_provenance_test.sh`、`tests/methods_text_test.sh` | 全部通過；`package_gaps_test.sh` 與 `run_all.sh` 在 WSL／CI 全綠 | 自動：上述各檔 |
| TC-C09 | 開發流程：測試不得被放寬 | 功能 | 本功能的分支 | 驗收者比對 `tests/build_package_test.sh` 與其他被動到的測試檔相對於 main 的差異 | 只有新增斷言與新增案例；沒有刪除、放寬、跳過任何既有斷言，也沒有改期望值去配合新輸出 | 手動：驗收者讀 diff（依憲法「獨立驗收」；`docs/TESTING.md` 目前沒有對應步驟） |
