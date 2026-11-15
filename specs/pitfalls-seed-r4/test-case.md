# 測試案例與總覽：pitfalls-seed（往 docs/PITFALLS.md 追加 62–64）

狀態：合約已確認（2026-11-15，verifier）

**計畫**：`G:/我的雲端硬碟/謝馬爾/memory/dev-plans/pitfalls-seed.md`（含 2026-11-15 兩則裁決：格式測試計數 97 改 100；64 的 Touches 用 "synced drive (e.g. Google Drive)"）
**基準**：`origin/v3` = aebb7a59，`docs/PITFALLS.md` 共 2572 行、最後一條是 61、格式測試現計 97 條。
**類型只有三種**：功能／例外／不在範圍。
**驗證等級**：【機器可驗】= 測試或唯讀指令即可判；【實機驗】= 需要真實 Windows＋WSL 環境，由維護者或 worker 跑。

## 計畫審查（只列會讓結果錯或漏掉他要的事）

計畫無阻擋問題。以下三點不擋，但出題時已照處理：

1. 計畫「範圍」「不做」「完成標準」仍寫「不改 `tests/pitfalls_format_test.sh`、只有兩個檔」，與同檔 2026-11-15 裁決（可改，且只改 97 改 100）衝突。以裁決為準；本合約的範圍是三個檔（TC-002、TC-063）。
2. `tests/pitfalls_format_test.sh` 的 TC-006 規則：Touches 每一項必須原字出現在該條的標題或散文（不含四欄那幾行）。所以 63 的 `$HOME`、`--cd`、`Failed to translate`，與 64 的 `synced drive (e.g. Google Drive)` 都必須寫進散文，不能只放在 Touches 行。TC-022、TC-031 明列。
3. CLAUDE.md 第 222–227 行說從非 ASCII 目錄呼叫 `wsl.exe` 會 "Failed to translate"；既有 16i（`docs/PITFALLS.md` 第 1090 行起）實測卻是「只警告、呼叫仍成功」。63 若寫成無條件「會失敗」，會與 16i 互相矛盾。TC-021 要求 63 把「失敗」歸給 CLAUDE.md 的說法，且不得重述 16i 的實測。這是否要在條目裡點明兩者差異，請維護者在備註看。

## 一眼看完

| 區塊 | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 三條追加在既有檔案、格式對、不動舊內容 | 6 | 1 | 4 | 11 |
| US2 — 62：run_all.sh 拒絕 Git Bash | 3 | 1 | 0 | 4 |
| US3 — 63：非 ASCII 目錄呼叫 wsl.exe | 5 | 0 | 0 | 5 |
| US4 — 64：同一 checkout 跑兩次／同步硬碟 | 3 | 0 | 0 | 3 |
| US5 — 證據屬實與守護測試檔 | 6 | 0 | 0 | 6 |
| 憲法與安全網 | 3 | 0 | 0 | 3 |
| **合計** | 26 | 2 | 4 | 32 |

機器可驗 31 條、實機驗 1 條（TC-024）。

## 維護者原話對照

維護者 2026-11-10 的話：「卡過的坑寫進 repo PITFALLS.md」（即 developer-agent 第 8 步：「卡過的坑寫進 repo `PITFALLS.md`」）。
- 「repo PITFALLS.md」對應 TC-001、TC-003、TC-060。
- 「卡過的坑」對應 TC-040、TC-041、TC-042、TC-070（每條有 repo 內出處）。
- 「寫進」對應 TC-004、TC-005（四欄格式並過既有格式測試）。

## User Story 1 — 三條追加在既有 docs/PITFALLS.md，格式對，舊內容不動

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 【機器可驗】 | 原話「repo PITFALLS.md」；計畫 T1 | 功能 | 在完成後的 worktree | 檢查 `docs/PITFALLS.md` 與根目錄 `PITFALLS.md` | `docs/PITFALLS.md` 存在，且含標題行 `**62. `、`**63. `、`**64. ` 各一條；根目錄沒有 `PITFALLS.md` | 自動：`tests/test_pitfalls_seed.py::test_t1_no_root_pitfalls_file` |
| TC-002 【機器可驗】 | 計畫「範圍」＋裁決 (a) | 功能 | 已 commit 的分支 | `git diff --stat origin/v3...HEAD` | 只有三個檔：`docs/PITFALLS.md`、`tests/test_pitfalls_seed.py`、`tests/pitfalls_format_test.sh`；不多不少 | 自動：驗收者唯讀跑 git diff |
| TC-003 【機器可驗】 | 「只在檔尾追加；不動既有任何一行」 | 功能 | 同上 | `git diff --numstat origin/v3...HEAD -- docs/PITFALLS.md`，並比對前 2572 行 | 刪除行數 0；新檔前 2572 行與 `git show origin/v3:docs/PITFALLS.md` 逐字相同；新增內容裡沒有新的 `## ` 章節標題；檔尾有換行 | 自動：`test_t5_numbering_continues` |
| TC-004 【機器可驗】 | 「四欄格式」；計畫 T2 | 功能 | 同上 | 解析 62、63、64 三條 | 每條各有恰好一行 `Symptom:`、`Root cause:`、`Check:`、`Touches:`，各非空、依序、四行連續、位於該條最後四行；Check 有反引號或以 `none automated:` 開頭；Touches 以逗號分隔 | 自動：`test_t2_entries_62_to_64_have_four_fields` |
| TC-005 【機器可驗】 | 計畫 T4；裁決 (a) | 功能 | 同上 | `bash tests/pitfalls_format_test.sh` | 退出碼 0；輸出出現 TC-003「entry count 100」與 TC-005「Touches lines = entries = 100」皆 ok（不再是 97）；其餘既有項（含 Touches 每項都出現在該條文字內、無 secret-like 字串）仍 ok | 自動：`test_t4_existing_format_test_still_passes` 與 `tests/pitfalls_format_test.sh` |
| TC-006 【機器可驗】 | 「接續編號」 | 功能 | 同上 | 列出 `^\*\*\d+[a-z]?\. ` 標題行 | 61 之後緊接 62、63、64，依序；新增的標題只有這三條，總條目數 100 | 自動：`test_t5_numbering_continues` |
| TC-007 【機器可驗】 | 計畫作法 3（不重複） | 例外 | 基準檔前 2572 行 | 在基準檔搜尋 `Failed to translate`、`synced drive`、`two runs`、`refuses native`（不分大小寫）；比對三條新標題 | 基準檔零命中；三條標題彼此不同，也與既有任何標題不同。若開工時基準已有 62 以後條目，編號順延並在 ledger 註明 | 自動：驗收者唯讀 grep |
| TC-060 【機器可驗】 | 「不建根目錄 PITFALLS.md」 | 不在範圍 | 完成後 | `git ls-files PITFALLS.md` 與 `git diff --name-status origin/v3...HEAD` | 根目錄沒有新增 `PITFALLS.md` | 自動：同 TC-001 |
| TC-061 【機器可驗】 | 計畫作法 4、「不做」 | 不在範圍 | 完成後 | 在 diff 與三個新條目中搜尋 `other_docs_untouched`、`test_tc047` | 零命中（repo 無證據，不寫） | 自動：`git diff origin/v3...HEAD` 後 grep |
| TC-062 【機器可驗】 | 「不做」：不改 CLAUDE.md、憲法、`.github/`、CI、`tests/run_all.sh`、`dev-queue.json`、`dev-roadmap.json` | 不在範圍 | 完成後 | `git diff --name-only origin/v3...HEAD` | 清單不含這些檔；`docs/PITFALLS.md` 既有條目（含 16b、16i）文字未變 | 自動：同 TC-002、TC-003 |
| TC-063 【機器可驗】 | 裁決 (a)「只改 97 改 100」 | 不在範圍 | 完成後 | `git diff origin/v3...HEAD -- tests/pitfalls_format_test.sh` | 被改動的行只有把數字 97 換成 100（含標籤文字中的 97）；沒有新增、刪除、放寬任何其他斷言；數字 100 = 97 + 三條 | 自動：驗收者唯讀 git diff |

## User Story 2 — 條目 62：`tests/run_all.sh` 拒絕原生 Git Bash，完整測試要在 WSL 或 Linux 跑

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 【機器可驗】 | 計畫條目 62 標題與 Touches；T3 | 功能 | 62 已寫入 | 讀 62 的標題與 Touches | 標題含 `run_all` 與 `Git Bash`，並講到在 WSL 或 Linux 跑；Touches 含 `tests/run_all.sh`、`Git Bash`、`WSL`、`MSYS`、`--allow-msys`，且各項原字出現在條目標題或散文 | 自動：`test_t3_titles_and_touches_keywords`＋`tests/pitfalls_format_test.sh` |
| TC-011 【機器可驗】 | 計畫 Root cause 要求 | 功能 | 同上 | 讀 62 的 Root cause 與散文 | 寫 known MSYS gaps，並以「16b」「20c」指向既有條目而不重述其內容；16b、20c 兩條在 `docs/PITFALLS.md` 確實存在 | 自動：`test_t3_…` 加驗收者唯讀 grep |
| TC-012 【機器可驗】 | 計畫 Check 要求 | 功能 | 同上 | 讀 62 的 Check；跑 `bash tests/run_all_test.sh` | Check 引用反引號的 `tests/run_all_test.sh`（該檔現有斷言：在 MINGW64／MSYS／CYGWIN 下以 exit 3 停下並提到 WSL、20c），且該檔存在、跑出全部 ok；若改寫成 `none automated:` 則視為 FAIL，因為已有測試涵蓋 | 自動：`tests/run_all_test.sh` |
| TC-013 【機器可驗】 | 計畫「62 標題只講 run_all.sh，不寫成 Git Bash 什麼都不行」；16g | 例外 | 同上 | 讀 62 全文 | 只說「完整測試執行器 `tests/run_all.sh` 在原生 Git Bash 以 exit 3 停下、改去 WSL／Linux」；不寫成 Git Bash 其他事都不能做；不與 16g（Git Bash 呼叫 WSL 的 ssh 可行）矛盾；不說單一測試檔不能在 Git Bash 跑（CLAUDE.md 寫的是「多數可以」） | 自動：驗收者唯讀讀文＋grep |

## User Story 3 — 條目 63：從非 ASCII 目錄呼叫 `wsl.exe` 跑 suite 會失敗

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 【機器可驗】 | 計畫條目 63 標題；T3 | 功能 | 63 已寫入 | 讀 63 的標題與開頭 | 標題含 `wsl.exe` 與 `non-ASCII`；標題或散文第一句用「16i」指向既有條目（16i 存在），不複製 16i 的實測輸出（如 `tw --version`、`command not found`）、也不重述 `wsl_ssh.sh`／`bridge_kind()` 的橋接 | 自動：`test_t3_…`＋驗收者唯讀 grep |
| TC-021 【機器可驗】 | 計畫：Root cause 只寫出處講的，不推測 | 功能 | 同上 | 讀 63 的 Root cause 與散文 | 只含 CLAUDE.md 第 222–225 行講到的：從非 ASCII 目錄呼叫 `wsl.exe` 出現 "Failed to translate"、`--cd` 不可靠；不加其他原因或機制；「失敗」是歸給 CLAUDE.md 的說法，不與 16i「只警告、呼叫仍成功」的實測互相矛盾（不寫「必定失敗」之類的無條件句） | 自動：驗收者唯讀對照 CLAUDE.md |
| TC-022 【機器可驗】 | 計畫 Check／Touches 要求 | 功能 | 同上 | 讀 63 的 Check 與 Touches | Check 以 `none automated:` 開頭並說明從 `$HOME` 呼叫；Touches 含 `wsl.exe`、`--cd`、`Failed to translate`、`non-ASCII`、`tests/run_all.sh`、`$HOME`，且各項原字出現在條目標題或散文（不只在四欄行） | 自動：`tests/pitfalls_format_test.sh` 的 TC-006＋`test_t3_…` |
| TC-023 【機器可驗】 | 專長守則：每個新增指令範例與程式實況一致 | 功能 | 同上 | 若 63 引用解法指令，與 CLAUDE.md 第 223–225 行比對 | 指令與 CLAUDE.md 原文一致：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<path to the worktree> && bash tests/run_all.sh'`；佔位符 `<path to the worktree>` 不被當成實際路徑檢查 | 自動：驗收者唯讀比對 |
| TC-024 【實機驗】 | 專長守則：指令範例可直接複製執行 | 功能 | 一台 Windows 機，已裝 WSL 的 Ubuntu；有一個非 ASCII（例如中文）路徑的 repo worktree | 在 Git Bash 從該中文目錄與從 `$HOME` 各跑一次 63 的指令（把 `<path to the worktree>` 換成實際路徑），只需看到 `run_all.sh` 開始執行，不必跑完 | 從 `$HOME` 呼叫能進入 WSL 並啟動 `tests/run_all.sh`；從中文目錄呼叫的行為與條目所說的一致，若不一致就報告實際結果，不改條目 | 手動：維護者或 worker 實機跑（`docs/TESTING.md` 目前沒有此步驟，由 ledger 記錄結果） |

## User Story 4 — 條目 64：同一 checkout 同時跑兩次，或 checkout 放在同步硬碟，會弄壞 suite

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 【機器可驗】 | 計畫條目 64 標題；T3 | 功能 | 64 已寫入 | 讀 64 標題與 Root cause | 標題含 `synced drive`（或 `two runs`）；Root cause 只引 CLAUDE.md 第 226–227 行那句：repo 與 worktree 必須在本機磁碟、不可放同步硬碟，同一 checkout 同時兩次執行會互相弄壞暫存副本；不推測機制 | 自動：`test_t3_…`＋驗收者唯讀對照 CLAUDE.md |
| TC-031 【機器可驗】 | 計畫 Check／Touches；裁決 (b) | 功能 | 同上 | 讀 64 的 Check 與 Touches | Check 以 `none automated:` 開頭；Touches 含 `tests/run_all.sh`、`synced drive (e.g. Google Drive)`（整串為單一項目）、`worktree`、`temporary copies`；每項原字出現在條目標題或散文，包括整串 `synced drive (e.g. Google Drive)` | 自動：`tests/pitfalls_format_test.sh` 的 TC-006＋`test_t3_…` |
| TC-032 【機器可驗】 | 裁決 (b)：e.g. 只是舉例，不是出處原話 | 功能 | 同上 | 搜尋 64 中的 `Google Drive` | 每個 `Google Drive` 都緊接在 `e.g.` 的括號內（或明確標為舉例）；條目沒有把它寫成 CLAUDE.md 的原話或實測事實 | 自動：驗收者唯讀 grep |

## User Story 5 — 引述與行號屬實，守護測試檔存在且能抓錯

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 【機器可驗】 | 計畫「完成標準」：引述與行號已用 `git grep -n` 對過；專長守則 | 功能 | 三條已寫入 | 對三條內若引出的每個行號或引文，在 HEAD 對照 CLAUDE.md、`docs/TESTING.md`、`tests/run_all.sh` | 全部對得上（基準實況：CLAUDE.md 第 222、223–225、226–227 行；`docs/TESTING.md` 第 23–24 行；`tests/run_all.sh` 第 25、67 行）；對不上以 repo 為準，並在 ledger 註明 | 自動：驗收者抽查；上述三類各至少 3 處 |
| TC-041 【機器可驗】 | 計畫 T6；專長守則「路徑必須存在」 | 功能 | 同上 | 取三條內反引號包住、含 `/` 或以 `.md`／`.sh`／`.py` 結尾的路徑（扣掉含 `<…>` 的佔位符） | 每個路徑在 HEAD 都存在，至少包含 `tests/run_all.sh`、`tests/run_all_test.sh`、`CLAUDE.md`（若有引用） | 自動：`test_t6_evidence_paths_exist` |
| TC-042 【機器可驗】 | 原話「卡過的坑」；憲法 8 | 功能 | 同上 | 讀三條散文 | 各條指明出處（CLAUDE.md、`docs/TESTING.md` 或 `tests/run_all.sh` 的哪一段）；沒有寫「measured」「實測」之類未經本任務實際量測的說法 | 自動：驗收者唯讀 grep 與讀文 |
| TC-043 【機器可驗】 | 計畫「失敗先行測試」 | 功能 | `tests/test_pitfalls_seed.py` 已加入 | 在 `origin/v3` 版本的 `docs/PITFALLS.md` 上跑一次，再在 HEAD 跑一次 | 基準上 T2、T3、T5、T6（及 T4 的計數）為紅；HEAD 上 `python -m pytest tests/test_pitfalls_seed.py` 全綠；六個測試 `test_t1`…`test_t6` 都存在，且每個斷言能在內容被刪掉時失敗，不是只斷言檔案存在 | 自動：`python -m pytest tests/test_pitfalls_seed.py`；紅燈紀錄貼在 ledger |
| TC-044 【機器可驗】 | 計畫作法 5：找不到 bash 不 skip | 功能 | 測試檔已加入 | 讀 `test_t4_…` 的處理 | 找不到 bash 時以明確訊息失敗，不是 skip、不是靜默通過 | 自動：驗收者唯讀讀測試碼 |
| TC-045 【機器可驗】 | 計畫作法 5：標準庫＋pytest、不連網 | 功能 | 測試檔已加入 | 讀測試檔 import 與呼叫 | 只用標準庫與 pytest；用 `Path(__file__).resolve().parent.parent` 取 repo 根；不連網；不寫死使用者路徑 | 自動：驗收者唯讀讀測試碼 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 【機器可驗】 | 不變式 8（IV 先證據後主張）：每條 PITFALLS 對應真實失敗或真實讀過的原始碼；其檢查是 `docs/TESTING.md` 的 Procedure P2 | 功能 | 三條已寫入 | 依 P2 把三條逐一對回出處 | 三條都對得到 repo 內出處（TC-040、TC-042）；沒有無出處的條目、沒有推測的根因 | 自動：驗收者依 P2 唯讀對照 |
| TC-071 【機器可驗】 | 安全網：`tests/pitfalls_format_test.sh` 守格式；`tests/works_without_host_test.sh` 第 94 行釘住檔案存在 | 功能 | 同上 | `bash tests/pitfalls_format_test.sh` 與 `bash tests/works_without_host_test.sh` | 兩者都以 0 結束；格式測試的檢查仍覆蓋新條目（解析的條目數為 100） | 自動：兩個 `.sh` |
| TC-072 【機器可驗】 | 工作流程：實作期間不得改 `spec.md`、`test-case*.md`、憲法、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json` | 功能 | 已 commit 的分支 | `git diff --name-only origin/v3...HEAD` | 清單不含上述任何檔 | 自動：驗收者唯讀 git diff |

## 覆蓋檢查

- 維護者原話：一句，三個意思（寫在既有 repo 檔、卡過才寫並有出處、四欄格式寫進去），全部有 TC：是。
- 計畫的 T1–T6 都對應到 TC（T1→TC-001；T2→TC-004；T3→TC-010、020、030；T4→TC-005；T5→TC-003、006；T6→TC-041）：是。
- 計畫「不做」七項都有「不在範圍」或憲法 TC（根目錄檔 TC-060；other_docs_untouched TC-061；其餘不改的檔與既有條目 TC-062；格式測試只改計數 TC-063；不寫無出處的坑 TC-070；不手改 dev-queue／dev-roadmap 在 TC-062）：是。
- 裁決 (a) 的 100 在 TC-005、TC-006、TC-063、TC-071；裁決 (b) 在 TC-031、TC-032。
- 專長守則（docs）：每個新增指令範例一條與實況一致的 TC（TC-023、TC-024）；每個引用路徑存在（TC-041）；計畫沒有新增文件連結，不需要連結 TC。

## 給維護者的備註

1. 計畫本文與同檔裁決有衝突：本文說不改 `tests/pitfalls_format_test.sh`，裁決說可改但只改計數 97 改 100。本合約採裁決。如果你其實想維持原樣，那三條加進去後格式測試會因計數不符而紅，兩者無法同時成立。
2. 63 與既有 16i 有張力：CLAUDE.md 說從非 ASCII 目錄呼叫 `wsl.exe` 會 "Failed to translate"，16i 在你的實機量測卻是「只警告、呼叫仍成功、落在預設目錄」。TC-021 要求 63 把「失敗」歸給 CLAUDE.md 的說法、不寫成無條件。你可以決定要不要在條目裡明寫兩個說法的差異，要的話請另外告訴我，不在這次範圍。
3. TC-024 是本合約唯一需要真實 Windows＋WSL 的一條，沒有人跑過就是「未驗證」，驗收會停在「有待確認」。如果你認為 63 的指令照抄 CLAUDE.md 就夠，可以回覆把它降為不驗；我不自行降級。
4. 計畫 T5 寫「對 origin/v3 比對前 2572 行」。分支合併後 `origin/v3` 已經包含新條目，這個測試之後會失去意義；計畫允許改用寫死的雜湊。另外，`tests/` 頂層的 `.py` 不會被 `tests/run_all.sh` 自動跑，也不進 CI（計畫環境事實 3 已承認），所以這個守護測試只在本機和 ledger 有效。這是計畫已知的取捨，不是缺陷。
5. 計畫 T6 的措辭（「除 `tests/run_all.sh` 這類實際存在者外都必須存在」）有些繞，TC-041 把它簡化成「出現的路徑都必須存在」。若 executor 認為意思不同，請在 ledger 說明。
