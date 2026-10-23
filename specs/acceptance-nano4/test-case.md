# 測試案例：nano4 實機驗收文件（TC-047n～051n 與驗收表）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
Reader: the maintainer, who is not an engineer.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/acceptance-nano4/plan.md`（本任務沒有 spec.md，計畫即規格；「維護者原話」與「裁決」兩節是依據）　**總覽**：`test-case-overview.md`

本任務只寫文件（`docs/TESTING.md` 的五條手動案例、`specs/007b-launch/acceptance-nano4.md` 驗收表、`tests/docs_nano4_acceptance.sh` 文件檢查）。真機填表是維護者的事，本任務不跑真機、不改程式。

文中「手動（閱卷）」＝閱卷者讀 `docs/TESTING.md` 的「nano4 acceptance」一節或驗收表本身，逐句對照預期結果。

類型只有三種：

- **功能**：計畫說要做到的事，做到了。
- **例外**：缺東西或文件被改壞時，檢查要變紅。
- **不在範圍**：計畫明講不做的事，確認真的沒做。

## 維護者原話對照

| 維護者原話（計畫「維護者原話」節） | 對應 TC |
|---|---|
| 「第一里程碑＝16S（nf-core/ampliseq 2.18.0）在 nano4 端到端：Claude Desktop 或網頁 → 不經 Seqera → 啟動 → 結果頁。」 | TC-004、TC-005、TC-008、TC-020 |
| 「每次先估 SU、記帳。」 | TC-003、TC-017 |
| 「nano4 若週四跑不通 → 先在 `/work/u9613010` 自裝 Nextflow＋插件跑通」→ 驗收表要有「走哪條路」欄 | TC-014 |

## User Story 1 — `docs/TESTING.md` 有五條照著做的 nano4 手動案例（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法「TESTING.md 手動案例加」；失敗先行測試；裁決 3 | 功能 | 實作完成 | 打開 `docs/TESTING.md`，找「nano4 acceptance」一節 | 檔內恰好有一節標題含 `nano4 acceptance`；該節內 `TC-047n`、`TC-048n`、`TC-049n`、`TC-050n`、`TC-051n` 五個 ID 各出現至少一次；原有的 `TC-047`～`TC-053`（沒有 n）仍在 | 自動：`tests/docs_nano4_acceptance.sh` |
| TC-002 | 作法 TC-047n；裁決 5 | 功能 | 同上 | 讀 TC-047n | 標題是「nano4 preflight 全項通過」；逐項列出 `docs/PLATFORM.md` Preflight 表的 8 個名稱：`connect`、`work_dir`、`sbatch`、`squeue`、`sinfo`、`java`、`nextflow`、`head_queue`；另列 `modules`、`site_pipeline`、`library` 三項，且這三項旁標「（preflight-nano4 合併後）」；每項寫出怎麼算通過（`pass`），不是只列名字 | 手動（閱卷） |
| TC-003 | 作法 TC-048n；裁決 1；維護者原話「每次先估 SU、記帳」 | 功能 | 同上 | 讀 TC-048n 的第一步 | 第一步就是「launch 前先估 SU」，且排在 launch 那一步之前；寫出估算用的完整呼叫（`estimate_su`／`abf-platform` 的估算，閱卷者對照 `platform/abf_platform/actions/__init__.py` 確認這個呼叫真的存在）、預期輸出長什麼樣（只寫欄位或格式，不編造數字）、以及「把預估值填進驗收表『launch 前預估 SU』欄」 | 手動（閱卷） |
| TC-004 | 作法 TC-048n；維護者原話「Claude Desktop … 不經 Seqera → 啟動」；裁決 6 | 功能 | 同上 | 讀 TC-048n 啟動那一步 | 從 Claude Desktop 說 `launch nf-core/ampliseq 2.18.0`（用這句字面）；接著寫「開 `/c/<rid>` 頁面由本人確認」；整條 TC 與整節都沒有任何 Seqera／`tw` 的步驟（網頁路徑不在這條 TC 裡） | 手動（閱卷） |
| TC-005 | 作法 TC-048n | 功能 | 同上 | 讀 TC-048n 的 `squeue` 那一步 | 寫出完整 `squeue` 指令；預期輸出寫明：head 作業在 `ngsconsole` 分區，子作業在 ngs 分區；寫出「看到什麼算對、看到什麼算不對」 | 手動（閱卷） |
| TC-006 | 作法 TC-049n；裁決 7 | 功能 | 同上 | 讀 TC-049n 的 curl 那一步 | 用 `srun -p ngstest -A mst109178 -N1 -c1 -t 00:05:00 curl …` 從計算節點打 `https://<public>/user-info`（以「作法」為準是 `/user-info`）；指令要能同時看到狀態碼與回應標頭；預期：狀態碼 `401`，且標頭有 `X-ABF-Platform`；寫出缺任一項時代表什麼 | 手動（閱卷） |
| TC-007 | 作法 TC-049n「relay 未啟動（取代 T3 的 relay 檢查）」；裁決 7 | 功能 | 同上 | 讀 TC-049n 的 relay 那一步 | 兩個檢查都寫出完整指令與預期：`abf-platform launches` 顯示 `way_back: direct`；站台上 `ss -ltnp \| grep -c <relay port>` 輸出 `0`；並說明這條取代原 T3 的 relay 檢查 | 手動（閱卷） |
| TC-008 | 作法 TC-050n；裁決 7 | 功能 | 同上 | 讀 TC-050n | 寫出數 run 資料夾 `trace.txt` 行數（扣表頭）的完整指令；寫出「平台收到 trace」與「結果頁看得到」各是什麼畫面或輸出；寫出要把行數與截圖檔名填進驗收表哪一欄（不要求行數必須等於某數，計畫沒說） | 手動（閱卷） |
| TC-009 | 作法 TC-051n | 功能 | 同上 | 讀 TC-051n | 指定一個具體的 revision，並寫出如何確認它不在 `sitePipelines`（指令或要看哪個檔）；預期：模組缺席時啟動退回 `owner/name -r rev` 這種形式（讓人在 `head.sh` 看得到這一行）；寫出沒退回時看到什麼 | 手動（閱卷） |
| TC-010 | 作法「每條手動 TC 都寫到非工程師照著做的粒度」 | 功能 | 同上 | 逐條讀 TC-047n～051n | 每條都有：開始前的狀態、編號步驟、每步完整可貼上的指令（不是「執行 preflight」這種描述）、每步預期輸出寫出來；沒有「視情況」「適當」「略」這類留白；用到的縮寫（如 SU、head、`ngsconsole`）第一次出現有一句白話 | 手動（閱卷） |
| TC-011 | 範圍：不改既有案例 | 不在範圍 | 實作完成 | `git diff <base>...HEAD -- docs/TESTING.md` | 只有新增行；原有 TC-047～053 等既有段落沒有被刪、改、縮短（新案例不是改寫舊案例） | 手動（閱卷） |

## User Story 2 — 驗收表 `specs/007b-launch/acceptance-nano4.md`（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 作法「acceptance-nano4.md」；失敗先行測試 | 功能 | 實作完成 | 檢查檔案 | `specs/007b-launch/acceptance-nano4.md` 存在，且內文含 `wallet`、`squeue`、`X-ABF-Platform` 三個字串 | 自動：`tests/docs_nano4_acceptance.sh` |
| TC-013 | 作法欄位清單；裁決 1、2 | 功能 | 同上 | 讀表的欄位 | 欄位齊全且名稱可辨識：日期、走哪條路、launch 前預估 SU、preflight 每項結果、`head.sh` 全文、`squeue` 輸出、trace 行數、`grep -c token`（見 TC-016）、`wallet` 前 SU、`wallet` 後 SU、差額、結果頁截圖檔名、備註 | 自動：`tests/docs_nano4_acceptance.sh` |
| TC-014 | 維護者原話裁示 17 | 功能 | 同上 | 讀「走哪條路」欄 | 欄位的選項恰為兩個：「國網模組」與「自裝 Nextflow」；並註明自裝是在 `/work/u9613010` 自裝 Nextflow＋插件（週四國網路徑跑不通時才走） | 手動（閱卷） |
| TC-015 | 作法「preflight 每項結果」；裁決 5 | 功能 | 同上 | 讀 preflight 部分 | 一項一格，共 11 格（`connect`、`work_dir`、`sbatch`、`squeue`、`sinfo`、`java`、`nextflow`、`head_queue`，加 `modules`、`site_pipeline`、`library`）；後三項標「（preflight-nano4 合併後）」；每格是空白待填，旁邊寫填 `pass`／`fail`／`unchecked` | 手動（閱卷） |
| TC-016 | 作法「`grep -c token` 必須為 0」；裁決 2 | 功能 | 同上 | 讀 token 檢查部分 | 兩條完整指令各一：對 run 資料夾的 `head.sh`、對 `slurm-<jobid>.out`，各做 `grep -c token`；預期兩者輸出都是 `0`；明寫 `tower.token` 檔本身不在掃描範圍（它本來就放 token） | 手動（閱卷） |
| TC-017 | 作法「`wallet` 前後 SU 與差額」；裁決 1；維護者原話「每次先估 SU、記帳」 | 功能 | 同上 | 讀 SU 部分 | 「launch 前預估 SU」「wallet 前」「wallet 後」「差額」四格並列；`wallet` 指令寫完整並說明它是國網查 SU 餘額的指令；寫出差額怎麼算（前減後或後減前，擇一寫清楚） | 手動（閱卷） |
| TC-018 | 裁決 4 | 功能 | 同上 | 讀表頂部 | 表頂部有一句註明：依 2026-10-22 計畫撰寫；實機跑時以當時 v3 為準 | 手動（閱卷） |
| TC-019 | 目標「照著填」「之後同事試用也用同一張」 | 功能 | 同上 | 讀表的使用說明與版面 | 表是可重複使用的空白範本，說明每跑一次複製一份填；不需要維護者本人在場才看得懂（沒有只有維護者知道的暗語） | 手動（閱卷） |
| TC-020 | 裁決 6 | 不在範圍 | 同上 | 讀表中「網頁路徑」列 | 表中有一列「網頁路徑：M2」，標明留給 M2 網頁全流程時再驗，本次不驗；首次驗收只走 Claude Desktop；沒有網頁路徑的操作步驟被寫進 TC-047n～051n | 手動（閱卷） |
| TC-021 | 範圍：「真機填表是維護者的事」；不做「不跑真機」 | 不在範圍 | 同上 | 讀表的結果欄，並檢查 commit 內容 | 所有結果格都是空白待填：沒有預先填好的 PASS、日期、SU 數字、截圖檔名、`squeue` 輸出；也沒有任何一份「已在 nano4 跑過」的紀錄被寫進 repo | 手動（閱卷） |

## User Story 3 — 文件檢查接進測試（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 裁決 3；完成標準「docs 測試綠」 | 功能 | 實作完成 | `bash tests/docs_nano4_acceptance.sh` | 檔案存在、結束碼 0；它檢查的內容至少含 TC-001、TC-012、TC-013 的項目 | 自動：`tests/docs_nano4_acceptance.sh` |
| TC-023 | 失敗先行測試「先寫、現在會紅」 | 例外 | 拿 base（沒有新文件）的 `docs/TESTING.md`，或把本分支 `TESTING.md` 複製一份刪掉 `TC-049n` | 對那份文件跑檢查 | 檢查失敗（結束碼非 0），輸出點名缺的是哪個 ID 或哪一節；本分支真文件上則通過。代表這個檢查會變紅，不是永遠綠 | 自動：`tests/docs_nano4_acceptance.sh` |
| TC-024 | 失敗先行測試；裁決 3 | 例外 | 把驗收表複製一份，分別拿掉 `wallet`、`squeue`、`X-ABF-Platform`、其中一個必要欄位 | 對各份複本跑檢查 | 每一份都失敗，輸出點名缺哪個字串或欄位；真表通過 | 自動：`tests/docs_nano4_acceptance.sh` |
| TC-025 | 裁決 3「run_all 自動收進去」 | 功能 | 實作完成 | `bash tests/run_all.sh --list` | 清單含 `docs_nano4_acceptance.sh`；`bash tests/run_all_count_test.sh` 仍通過 | 自動：`tests/run_all_count_test.sh` |
| TC-026 | 完成標準「全套綠」 | 功能 | 實作完成 | 在 WSL 跑整套 `tests/run_all.sh` | 全綠 | 自動：`tests/run_all.sh` |

## 範圍界線（不在範圍）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-027 | 計畫「不做：不跑真機、不改程式」；檔案範圍 | 不在範圍 | 實作完成 | `git diff <base>...HEAD --stat` | 只出現 `docs/TESTING.md`、`specs/007b-launch/acceptance-nano4.md`、`tests/docs_nano4_acceptance.sh`、`specs/acceptance-nano4/` 底下的檔；`platform/`、`scripts/`、`hooks/`、`skills/`、`.claude-plugin/`、`.github/`、`.specify/memory/constitution.md`、`docs/ROADMAP.md`、`docs/PLATFORM.md`、`specs/acceptance-nano4/` 的 spec／`test-case*.md` 都沒有被動 | 手動（閱卷） |
| TC-028 | 驗收規則：不放水既有測試 | 不在範圍 | 同上 | `git diff <base>...HEAD -- tests platform/tests` | `tests/` 下只多一個新檔 `docs_nano4_acceptance.sh`；沒有任何既有測試被刪斷言、放寬、跳過或改預期值 | 手動（閱卷） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | 第 3 條（不寫個人／叢集路徑，檢查 `tests/no_hardcoded_paths.sh`）、第 4 條（指令層不點名排程器／分區，檢查 `tests/command_layer_is_site_neutral.sh`） | 功能 | 文件含 `mst109178`、`ngsconsole`、`/work/u9613010` 等站台字樣（只在 `docs/` 與 `specs/`） | 跑這兩個測試檔 | 兩個都通過；站台字樣沒有跑進 `scripts/`、`skills/`、`hooks/`、`commands/`、`README.md`、`CLAUDE.md` | 自動：`tests/no_hardcoded_paths.sh`、`tests/command_layer_is_site_neutral.sh` |
