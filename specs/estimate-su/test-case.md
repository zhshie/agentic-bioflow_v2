# 測試案例：estimate_su（用 run 的 trace 算用掉多少國網 SU）

<!--
Written by the verifier (CONTRACT mode). Source: specs/estimate-su/plan.md (no spec.md exists for this task; issue #119 is quoted in the plan). Reader: the maintainer, who is not an engineer.
Language: 繁體中文; identifiers and file paths stay as they are.
Reopened 2026-10-18 for the plan's "Rulings after acceptance" E1-E3 (maintainer: 「都照你的建議」). TC-001..TC-033 and TC-C01..TC-C07 keep their IDs and meaning; TC-034..TC-042 are new.
-->

**規格**：`specs/estimate-su/plan.md`（本任務沒有 spec.md；公式與費率來自計畫引用的 issue #119 與 `docs/POSITIONING.md` 第 82 行；月合計規則來自計畫「Rulings after acceptance」E1 至 E3）　**總覽**：`test-case-overview.md`

名詞：SU＝國網的計算點數；「係數」＝每個 CPU 小時換算成多少 SU，每個分區（partition，即國網的佇列，例如 ngs7G）各有一個；「未知」＝畫面上顯示「—」，不是 0；「台北時間」＝UTC+8，月份一律以台北時間的日曆月為準。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：缺資料、查不到、不是自己的 run 時，系統怎麼反應（說不知道並講原因，而不是亂猜）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

以下「測試檔」一律指 `platform/tests/test_estimate_su.py`（執行者撰寫，每個自動 TC 在註解寫上 TC 編號）。除非另註，輸入的費率表是測試自己做的假站點 `testsite`：分區 `p1` 係數 1.5、分區 `p2` 係數 2，金額費率 國科會 0.08 元/SU、學界 0.24 元/SU。

## User Story 1 — 用公式從 trace 算出 SU 與金額（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 Build 2；Tests「formula on a hand-made trace」 | 功能 | 手做的 trace 有 2 個 task：A 在 p1、4 核、跑了 2 小時；B 在 p2、2 核、跑了 30 分鐘 | 呼叫 `su_of_tasks(tasks, 'testsite', rates)` | SU 正好是 14（A＝4×2×1.5＝12，B＝2×0.5×2＝2），沒有未知原因 | 自動：測試檔 |
| TC-002 | 計畫 Build 2；Tests「exact SU and TWD」 | 功能 | 同 TC-001，SU＝14 | 由這個 SU 算金額 | 國科會價 1.12 元（14×0.08），學界價 3.36 元（14×0.24）；浮點誤差小於 1e-9 | 自動：測試檔 |
| TC-003 | 計畫 Build 1「factor（SU per cpu-hour）」放在費率資料，不在程式裡 | 功能 | 同 TC-001，但費率表把 p1 係數改成 3 | 同一份 trace 再算一次 | SU 變成 26（4×2×3＋2）；程式碼不用改，結果隨費率表變 | 自動：測試檔 |
| TC-004 | 計畫 Build 2「cpus x realtime_hours」；憲法 IV.9（數字來自檔案） | 功能 | 一個 task：1 核、p1，`realtime` 欄位用 Nextflow 實際記錄的單位（毫秒，見 `platform/tests/fixtures/payloads/*.json`）寫 3600000 | 算 SU | 視為 1 小時：SU＝1×1×1.5＝1.5。程式假設的單位與 fixtures 實際單位一致，不是自創單位 | 自動：測試檔 |

## User Story 2 — 缺資料就說不知道，絕不猜（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-005 | 計畫 Build 2「no factor → None and lists why」；Tests「missing factor -> None with a reason」 | 例外 | 費率表中 p1 的係數是 null；一個 task 在 p1，4 核跑 2 小時 | 算 SU | SU 是 None（不是 0）；金額也是 None；未知原因的文字裡點名分區 p1 | 自動：測試檔 |
| TC-006 | 計畫 Build 2「a task whose partition has no factor」 | 例外 | 一個 task 的分區 `p9` 根本不在費率表裡 | 算 SU | SU 是 None；原因點名 p9；不套用其他分區的係數 | 自動：測試檔 |
| TC-007 | 計畫 Build 2「makes the total None」 | 例外 | 兩個 task：A 同 TC-001（可算出 12），B 的分區係數是 null | 算 SU | 整體 SU 是 None，不是只加 A 得到的 12；原因點名 B 的分區 | 自動：測試檔 |
| TC-008 | 計畫 Build 2「or no cpus/realtime」 | 例外 | 一個 task 沒有 cpus（欄位缺或空）、分區有係數 | 算 SU | SU 是 None；原因說這個 task 缺 cpus | 自動：測試檔 |
| TC-009 | 計畫 Build 2「or no cpus/realtime」 | 例外 | 一個 task 沒有 realtime（例如還沒跑完）、分區有係數 | 算 SU | SU 是 None；原因說這個 task 缺 realtime | 自動：測試檔 |
| TC-010 | 計畫 Build 2「lists why」 | 例外 | 兩個壞 task：一個缺 cpus，一個分區係數 null | 算 SU | SU 是 None；未知原因有兩條，各自對應一個壞 task（講完整，不只講第一個） | 自動：測試檔 |
| TC-011 | 計畫 Build 2「never guess」 | 例外 | 站點名稱 `nosuchsite` 不在費率檔裡 | 算 SU | SU 是 None；原因說找不到這個站點的費率 | 自動：測試檔 |
| TC-012 | 計畫 Build 2「never guess」；憲法 IV.9「缺口要明白寫出來」 | 例外 | 費率檔不存在或內容不是合法 JSON | 算 SU（或呼叫 estimate_su） | 不崩潰、不用內建數字湊；SU 是 None，原因說費率檔讀不到 | 自動：測試檔 |
| TC-013 | 計畫 Build 1「set every factor to null … report SU as unknown ('—')」 | 例外 | 用 repo 真正的 `configs/sites/su_rates.json`；一個 task 在 `ngs7G`（`configs/sites/nchc.config` 的佇列）、1 核跑 1 小時 | 算 SU | SU 是 None，原因點名 ngs7G 沒有係數；沒有任何數字被猜出來 | 自動：測試檔 |

## User Story 3 — action `estimate_su`：只看得到自己的 run（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 計畫 Build 3「if the needed per-task fields are not stored … return unknown」 | 例外 | 索引裡有使用者 A 自己的 run（receiver 實際存的欄位：只有計數與失敗 task，沒有每個 task 的 cpus／realtime／分區） | 以 A 的身分呼叫 `estimate_su` | 回答 su、twd_nstc、twd_academic 都是 None；unknown_reasons 非空，並說明這個 run 的紀錄沒有保存每個 task 的 cpus／realtime／分區（不是回 0，也不是假裝算得出） | 自動：測試檔 |
| TC-015 | 計畫 Build 3「returns {su, twd_nstc, twd_academic, unknown_reasons}」 | 功能 | 同 TC-014 | 檢查回答的欄位 | 欄位恰好是 su、twd_nstc、twd_academic、unknown_reasons 四個（沒有多出別的金額欄） | 自動：測試檔 |
| TC-016 | 計畫 Build 3（action 真的接到公式，不是空殼） | 功能 | 把「讀某個 run 的每個 task 紀錄」換成手做的資料（TC-001 的兩個 task），並提供 TC-001 的費率表；run 屬於 A | 以 A 的身分呼叫 `estimate_su` | su＝14、twd_nstc＝1.12、twd_academic＝3.36、unknown_reasons 為空；數字與直接呼叫 `su_of_tasks` 完全相同 | 自動：測試檔 |
| TC-017 | 計畫 Build 3「another user's run = not found」；Tests「another user's run -> not found」 | 例外 | 使用者 B 的 run `run-b`；A 與 B 是不同使用者 | 以 A 的身分對 `run-b` 呼叫 `estimate_su` | 回答 found 為 False，並有 `get_run` 同款的「找不到這個 run」訊息；不含任何 SU 或金額 | 自動：測試檔 |
| TC-018 | 計畫 Build 3「owner-only like get_run」 | 例外 | 一個根本不存在的 run 名稱 | 以 A 的身分呼叫 `estimate_su` | 回答與 TC-017 完全同一形狀、同一句話（看不出「別人的」與「不存在」的差別） | 自動：測試檔 |
| TC-019 | 計畫 Build 3「like get_run」（`Caller` 說明：caller 為 None＝本機終端機或 stdio，看得到全部） | 功能 | 使用者 B 的 run，無 caller（None） | 不帶 caller 呼叫 `estimate_su` | 找得到這個 run（found 不是 False），回答仍是四個欄位 | 自動：測試檔 |

## User Story 4 — 某使用者某月的總計，讀的當下現算，月份以台北時間為準（優先度 P2）

下列 TC-034 至 TC-040 來自計畫 E2：月份用台北時間（UTC+8）、依 run 的開始時間歸月；該月只要有一個 run 的 SU 未知，整月就是未知；沒有任何 run 的月份是 0。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 計畫 Build 2「month_total(user, month)」；Tests「sums only that user's runs of that month」 | 功能 | A 在 10 月有兩個 run（SU 各為 10 與 5），在 9 月有一個 run（SU 100）；B 在 10 月有一個 run（SU 50）；所有 run 的開始時間都落在台北時間的月中，避開月初月底；每個 run 的 SU 都已知 | 算 A 的 10 月總計 | 15（只有 A 的 10 月兩個 run；不含 A 的 9 月 100，不含 B 的 50） | 自動：測試檔 |
| TC-021 | 計畫 Tests「only that user's runs」 | 功能 | 同 TC-020 | 算 B 的 10 月總計 | 50（A 的任何 run 都不混進來） | 自動：測試檔 |
| TC-022 | 計畫 Build 2「computed on read … no stored totals」 | 功能 | 同 TC-020，已先算過一次 A 的 10 月總計（15） | 再替 A 加一個 10 月的 run（SU 7），不做任何「重算」「刷新」動作，直接再算一次 | 22；表示是讀的當下從索引現算，沒有存起來的舊總數 | 自動：測試檔 |
| TC-034 | 計畫 E2「Asia/Taipei (UTC+8)」 | 功能 | A 有一個 run，開始時間是 UTC 2026-09-30 16:00:00（＝台北 2026-10-01 00:00:00）；SU 已知為 8 | 算 A 的 2026-10 總計 | 8（這個 run 算在 10 月；若用 UTC 判月會誤算進 9 月） | 自動：測試檔 |
| TC-035 | 計畫 E2「Asia/Taipei (UTC+8)」 | 功能 | A 有一個 run，開始時間是 UTC 2026-09-30 15:59:59（＝台北 2026-09-30 23:59:59）；SU 已知為 8 | 算 A 的 2026-10 總計，再算 2026-09 總計 | 10 月是 0（沒有這個 run）；9 月是 8 | 自動：測試檔 |
| TC-036 | 計畫 E2「Asia/Taipei (UTC+8)」 | 功能 | A 有一個 run，開始時間是 UTC 2026-10-31 16:00:00（＝台北 2026-11-01 00:00:00）；SU 已知為 8 | 算 A 的 2026-10 總計，再算 2026-11 總計 | 10 月是 0；11 月是 8（UTC 還在 10 月，但台北已經是 11 月） | 自動：測試檔 |
| TC-037 | 計畫 E2「by run start time」 | 功能 | A 有一個 run，台北時間 2026-09-30 22:00 開始，跨過午夜在 10 月才結束（若索引有結束時間就設成 10 月）；SU 已知為 8 | 算 A 的 2026-09 總計，再算 2026-10 總計 | 9 月是 8；10 月是 0（依開始時間歸月，不依結束時間） | 自動：測試檔 |
| TC-038 | 計畫 E2「A month with any unknown run is unknown」 | 例外 | A 在 2026-10 有兩個 run：一個 SU 已知（10），一個 SU 未知（例如係數是 null） | 算 A 的 2026-10 總計 | None（未知，顯示「—」）；不是只加已知部分的 10，也不是 0 | 自動：測試檔 |
| TC-039 | 計畫 E2「A month with no runs is 0」 | 功能 | A 只在 2026-09 有 run；2026-10 沒有任何 run | 算 A 的 2026-10 總計 | 0（是數字 0，不是 None） | 自動：測試檔 |
| TC-040 | 計畫 E2 與 Build 2「only that user's runs」 | 功能 | B 在 2026-10 有一個 SU 未知的 run；A 在 2026-10 只有一個 SU 已知（10）的 run | 算 A 的 2026-10 總計 | 10（B 的未知 run 不影響 A 的月總計） | 自動：測試檔 |

## User Story 5 — 費率檔與工作紀錄（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 計畫 Build 1「nstc_twd_per_su: 0.08, academic_twd_per_su: 0.24, with source」；E3「Rates stay 0.08 / 0.24 TWD per SU with their source」 | 功能 | repo 的 `configs/sites/su_rates.json` | 讀這個 JSON | 是合法 JSON；其中 `nstc_twd_per_su` 是 0.08、`academic_twd_per_su` 是 0.24；有 `source` 欄，內容是 `https://lions.nchc.org.tw/ngs.jsp`（與 `docs/POSITIONING.md` 第 82 行相同） | 自動：測試檔 |
| TC-024 | 計畫 Build 1「do NOT invent numbers … set every factor to null」；E3「factors stay null until NCHC confirms」 | 功能 | 同 TC-023 | 讀每個分區的 `factor` | 每個 `factor` 都是 null；唯一例外：若某個係數有數字，`specs/estimate-su/ledger.md` 必須寫出它在 repo 哪個檔案哪一行（沒有出處的數字就不算數） | 自動：測試檔 |
| TC-025 | 計畫 Build 1「per site, per partition」 | 功能 | 同 TC-023；`configs/sites/nchc.config` 第 31–37 行的七個佇列 | 比對分區清單 | 國網站點底下列出 ngs7G、ngs13G、ngs26G、ngs53G、ngs92G、ngs186G、ngs372G 七個分區，一個不多一個不少 | 自動：測試檔 |
| TC-026 | 計畫 Build 1「gap logged in the ledger as owed (maintainer/lab-agent to fill from NCHC)」；E3「(owed, lab-agent)」 | 功能 | 實作完成後的 `specs/estimate-su/ledger.md` | 讀它 | 明寫「各分區 SU 係數 repo 內查不到，欠：維護者或 lab-agent 向國網取得後填入 su_rates.json」 | 自動：測試檔 |
| TC-027 | 計畫 Build 3「say so in the ledger」 | 功能 | 同 TC-026 | 讀它 | 明寫「receiver／索引沒有保存每個 task 的 cpus、realtime、分區，所以 estimate_su 對真實 run 回未知；未改 receiver」 | 自動：測試檔 |
| TC-028 | 計畫 Build 4「list them in the ledger as owed」 | 功能 | 同 TC-026 | 讀它 | 明寫「MCP 工具」與「網頁顯示」兩項尚欠，分別隨 012d／同位對照（parity）工作完成 | 自動：測試檔 |

## User Story 6 — 範圍邊界（不在範圍）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | 計畫 Build 4「NOT in this task: the MCP tool」 | 不在範圍 | 啟動 MCP server 的 `build_server` | 列出所有工具名稱 | 名單與合併 origin/v3 之後既有的一致，沒有 `estimate_su` | 自動：測試檔 |
| TC-030 | 計畫 Build 4「NOT in this task: … the web display」 | 不在範圍 | 網頁應用程式的路由表 | 找名稱或路徑含 su／estimate 的路由 | 沒有；網頁沒有新增任何顯示 SU 的頁面或路由 | 自動：測試檔 |
| TC-031 | 計畫 Out of scope「receiver changes」 | 不在範圍 | 本任務的差異（git diff） | 看 `platform/abf_platform/receiver.py`、`store.py`、`records.py` | 三個檔都沒有改動 | 手動：驗收者讀 git diff（`docs/TESTING.md` 沒有對應步驟，見總覽疑問 5） |
| TC-032 | 計畫 Out of scope「CHANGELOG.md, docs/PLATFORM.md (another task)」 | 不在範圍 | 本任務的差異 | 看 `CHANGELOG.md`、`docs/PLATFORM.md` | 兩個檔都沒有改動 | 手動：驗收者讀 git diff（同上） |
| TC-033 | 計畫「cloud bills on the agent side, shown as '—' until Stage 4」 | 不在範圍 | 任一 `estimate_su` 回答 | 找雲端金額 | 回答裡沒有任何雲端費用欄位或數字；雲端費用這次不算、不顯示 | 自動：測試檔 |

## User Story 7 — 先和 origin/v3 合併，保留兩邊（優先度 P1）

來自計畫 E1：先做一次普通的 `git merge origin/v3`（#133 keep-submissions 已併入，它也改 `platform/abf_platform/actions/__init__.py`，兩邊都要留）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 | 計畫 E1「First git merge origin/v3 (plain merge)」 | 功能 | 實作完成的分支 | 執行 `git merge-base --is-ancestor origin/v3 HEAD` | 成功（結束碼 0）：origin/v3 的所有提交都已在這個分支裡；而且是合併，不是把 v3 的內容重抄一份 | 手動：驗收者執行此 git 指令並讀歷史（`docs/TESTING.md` 沒有對應步驟，見總覽疑問 5） |
| TC-042 | 計畫 E1「keep both sides」；開頭 NOTE「This task only ADDS one function there」 | 功能 | 同 TC-041 | 看 `git diff origin/v3...HEAD -- platform/abf_platform/actions/__init__.py` | 只有新增 `estimate_su`（與其必要的 import）；沒有任何一行 #133 的內容被刪或改 | 手動：驗收者讀 git diff（同上） |

## 憲法與安全網

本任務新增資料與讀取動作，不改 hooks，不碰安全網四條（刪除保護、確認後才送出、憑證）。可能碰到的是下列憲法條目。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-C01 | 第 2 條：沒有第二份 run 狀態 | 功能 | 實作完成 | 執行 `bash tests/no_second_run_state_test.sh` | 全綠 | 自動：`tests/no_second_run_state_test.sh` |
| TC-C02 | 第 2 條：沒有存起來的總數 | 功能 | 一份有 run 的索引與平台資料夾，記下算之前的資料表與欄位清單、資料夾檔案清單 | 呼叫 `estimate_su` 與 `month_total` 數次 | 資料表與欄位清單完全沒變（沒有新表、新欄）；平台資料夾沒有多出任何檔案（沒有快取的總數） | 自動：測試檔 |
| TC-C03 | 第 4 條：指令層不寫死排程器或分區名 | 功能 | `platform/abf_platform/su.py` 與 actions 新增的函式 | 掃描原始碼 | 不含分區名（如 `ngs7G`）、`taiwania`、`slurm`、`sbatch`、`squeue`；分區與係數只來自費率資料（TC-001 的假站點 testsite 能算也證明這點） | 自動：測試檔 |
| TC-C04 | 第 1 條：先說明現成工具 | 功能 | `platform/abf_platform/su.py` | 讀前 40 行 | 有一行 `# Nothing existing: …` 或 `# Not <外部工具>: …`，理由說明 Seqera 只估雲端成本、不估國網 SU（`docs/POSITIONING.md` 第 32 列） | 自動：測試檔 |
| TC-C05 | 第 9 條：數字出自檔案 | 功能 | `su.py` 原始碼 | 搜 0.08 與 0.24 | 這兩個費率在程式裡沒有寫成字面數字，只出現在 `configs/sites/su_rates.json` | 自動：測試檔 |
| TC-C06 | 第 3 條：沒有個人或叢集路徑 | 功能 | 實作完成 | 執行 `bash tests/no_hardcoded_paths.sh` | 全綠 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-C07 | 開發流程「每階段全綠」 | 功能 | 實作完成；合併 origin/v3 後，既有測試檔（尤其 `platform/tests/test_actions_layer.py`、`test_pat.py`，以及 #133 keep-submissions 的測試）相對 origin/v3 沒被修改 | 在 WSL 或 Linux 跑 `bash tests/run_all.sh`（或 CI） | 全綠；既有測試一字未改（diff 對照 origin/v3 與 main 沒有被放寬的斷言） | 自動：`tests/run_all.sh` |
