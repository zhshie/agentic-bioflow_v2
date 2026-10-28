# 測試案例：account-welcome-cli（`abf-platform user welcome`）

**規格**：`specs/account-welcome-cli/plan.md`（這個任務沒有獨立的 spec.md，計畫檔就是規格，內含維護者原話與 W1～W15 失敗先行表）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

名詞（第一次出現就說明）：
- **歡迎信**：管理者開完帳號後寄給同事的一封英文信，母本是 `docs/ONBOARDING.md` 第 3 節那一段。
- **雲端月上限**：這個人每月最多能花在雲端執行上的美元數，由管理者設定，本人不能改。「沒設」和「設成 0」是兩種不同狀態。
- **佔位符**：信裡尚待換成真值的 `<name>`、`<lab>`、`<platform-URL>`、`<operator>`。
- **PAT**：個人存取權杖（登入用的長密碼），信裡只能說「我另外給你」，不能出現真的內容。

除另有註明外，「自動」都指新測試檔 `platform/tests/test_user_welcome.py`。測試一律用暫存資料夾，不碰真實資料、不連網、不花錢。下面的「W1」等是計畫失敗先行表的編號。

## User Story 1 — 管理者一個指令印出填好名字、實驗室、網址與上限的信（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；W1 | 功能 | 已執行 `user add alice --lab lab-x --cloud-cap-usd 20` | 執行 `user welcome alice --platform-url https://abf.example.org` | 結束碼 0；輸出（stdout）同時含 `alice`、`lab-x`、`https://abf.example.org` | 自動 |
| TC-002 | W1 | 功能 | 同 TC-001 | 同 TC-001 | 輸出裡沒有殘留的 `<name>`、`<lab>`、`<platform-URL>` | 自動 |
| TC-003 | W1 | 功能 | 同 TC-001，沒給 `--operator` | 同 TC-001 | 輸出裡 `<operator>` 仍原樣保留（管理者自己填） | 自動 |
| TC-004 | W2 | 功能 | 同 TC-001 | 加 `--operator Marvin` 執行 | 信的最後（簽名）是 `Marvin` | 自動 |
| TC-005 | W2 | 功能 | 同 TC-004 | 同 TC-004 | 輸出裡不再有 `<operator>` | 自動 |
| TC-006 | W3；維護者原話「單位美元、不換算」 | 功能 | 這個人上限設 20 | 印信 | 含 `US$20.00` | 自動 |
| TC-007 | W3；原話「管理者開帳號時設，使用者不能改」 | 功能 | 同 TC-006 | 印信 | 含「cannot change」 | 自動 |
| TC-008 | W3；原話「單位美元、不換算」 | 功能 | 同 TC-006 | 印信 | 不含 `NT$`、`台幣`、`匯率`、`TWD` | 自動 |
| TC-009 | 作法 2「兩位小數」 | 功能 | 上限設 12.5 | 印信 | 含 `US$12.50` | 自動 |
| TC-010 | 完成標準的維護者手動驗收（用他的原句） | 功能 | 執行 `user add test-colleague --lab <任一實驗室名> --cloud-cap-usd 5` | 執行 `user welcome test-colleague --platform-url https://<任一 https 網域> --operator Marvin` | 結束碼 0；信裡有 `test-colleague`、`US$5.00`、簽名 `Marvin` | 自動 |
| TC-011 | 作法 1（只讀被點名的那個人）；後端守則「擁有者規則」的對應 | 功能 | 有兩人：alice（lab-x，上限 20）、bob（lab-y，上限 7） | 對 alice 印信 | 信裡有 alice 的 `lab-x`、`US$20.00`；沒有 `bob`、`lab-y`、`US$7.00` | 自動 |

## User Story 2 — 沒設上限與上限為 0 是兩種誠實的說法（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | W4；原話「沒設上限的人，信要誠實說『還沒設』」 | 功能 | `user add carol --lab x`（沒給上限） | `user welcome carol --platform-url https://abf.example.org` | 信裡含「not set」 | 自動 |
| TC-013 | W4 | 功能 | 同 TC-012 | 同 TC-012 | 信裡含「cannot send runs to the cloud」 | 自動 |
| TC-014 | W4 | 功能 | 同 TC-012 | 同 TC-012 | 結束碼 0（沒設上限不是錯誤） | 自動 |
| TC-015 | W4；原話「不能印出 None」 | 功能 | 同 TC-012 | 同 TC-012 | 信裡不含 `None` | 自動 |
| TC-016 | W4；原話「不能印出 0」 | 功能 | 同 TC-012 | 同 TC-012 | 信裡不含 `US$0` | 自動 |
| TC-017 | 作法 2「沒設」那句；計畫環境事實「國網沒有雲端上限」 | 功能 | 同 TC-012 | 同 TC-012 | 信裡含「NCHC runs are not affected」，且沒有對國網做任何額度承諾 | 自動 |
| TC-018 | W5 | 功能 | `user add bob --lab x --cloud-cap-usd 0` | `user welcome bob --platform-url https://abf.example.org` | 信裡含 `US$0.00` | 自動 |
| TC-019 | W5 | 功能 | 同 TC-018 | 同 TC-018 | 信裡含「cannot send runs to the cloud」 | 自動 |
| TC-020 | W5 | 功能 | 同時有 carol（沒設）與 bob（設 0），網址、簽名相同 | 各印一封 | 兩封內容不相同（兩種狀態不能混） | 自動 |

## User Story 3 — 信自足、與文件範本是同一份、不含祕密（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | W6；原話「同事不問我就能跑完」 | 功能 | 任一正常案例（如 TC-001） | 印信 | 含 `temporary`、`PAT`、`password`、`NCHC`、`separately`、`must change` | 自動 |
| TC-022 | W6 | 功能 | 同 TC-021 | 印信 | 含 `docs/INSTALL.md` 與 `docs/ONBOARDING.md` | 自動 |
| TC-023 | W6 | 功能 | 同 TC-021 | 印信 | 含指向第 2、4、5 節的字樣（寫法比照 `test_onboarding_doc.py` 的 `test_tc020`：`§N` 或 `section N`） | 自動 |
| TC-024 | W6；作法 3 | 功能 | 同 TC-021 | 印信 | 含 `<your NSTC project>`（計畫號維持佔位符，不替換成真值） | 自動 |
| TC-025 | W6；原話「雲端用戶不裝代理」 | 功能 | 同 TC-021 | 印信 | 信中沒有任何地方要求執行 `abf-station run`；若出現 `abf-station` 字樣，只能在「If you run on NCHC」那一步之內 | 自動 |
| TC-026 | W7 | 功能 | TC-001 的信；`docs/ONBOARDING.md` 第 3 節的範本 | 把範本裡的 `<platform-URL>`、`<name>`、`<lab>` 換成 TC-001 的值（`<operator>` 因 TC-001 沒給所以不換），再把範本的 Cloud cap 句換成 TC-006 的那一句 | 與 TC-001 的輸出逐字相同 | 自動 |
| TC-027 | W12 | 功能 | 有上限的信（TC-001） | 掃描輸出 | 不含 `abf_pat_` 後接 8 個以上英數字、不含 `mst1` 加 5 位數字、不含 `u9` 加 7 位數字、不含 16 字元的混合英數字串 | 自動 |
| TC-028 | W12 | 功能 | 沒設上限的信（TC-012） | 掃描輸出 | 同 TC-027 的四種都不含 | 自動 |
| TC-029 | 作法 3；計畫「不做：不產生或顯示 token／密碼／臨時密碼」 | 不在範圍 | 記下 `tokens` 表筆數與 `users` 表內容 | 執行 `user welcome` | 兩者前後相同：沒有偷發 token、沒有改密碼 | 自動 |
| TC-030 | 計畫「不做：不做多語言信」 | 不在範圍 | 任一正常案例 | 印信 | 輸出沒有任何中文字（只有英文，與 `docs/ONBOARDING.md` 第 3 節一致） | 自動 |

## User Story 4 — 打錯人、打錯網址時白話拒絕（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-031 | W8 | 例外 | 沒有叫 ghost 的人 | `user welcome ghost --platform-url https://abf.example.org` | 結束碼非零 | 自動 |
| TC-032 | W8 | 例外 | 同 TC-031 | 同 TC-031 | 錯誤訊息（stderr）含「沒有這個使用者」與「abf-platform user add」 | 自動 |
| TC-033 | W8 | 例外 | 同 TC-031 | 同 TC-031 | 輸出（stdout）是空的；事後這個人仍不存在（沒有被建立） | 自動 |
| TC-034 | 計畫環境事實「停用的人視同沒有這個使用者」 | 例外 | alice 存在，但在資料庫裡被標成停用（測試直接設 `users.disabled_at`） | `user welcome alice --platform-url https://abf.example.org` | 結束碼非零，訊息同 TC-032，stdout 空 | 自動 |
| TC-035 | 作法 1「`--platform-url` 必填」 | 例外 | alice 存在 | `user welcome alice`（不給網址） | 結束碼非零；stdout 沒有信 | 自動 |
| TC-036 | W9 | 例外 | alice 存在 | `--platform-url http://abf.example.org`（非本機的 http） | 結束碼非零；stderr 含 `https`；stdout 空 | 自動 |
| TC-037 | W9 | 例外 | 同 TC-036 | `--platform-url abf.example.org`（沒有 https://） | 結束碼非零；stderr 含 `https`；stdout 空 | 自動 |
| TC-038 | W9 | 例外 | 同 TC-036 | `--platform-url` 的值中間有空白（如 `https://abf.example .org`） | 結束碼非零；stderr 含 `https`；stdout 空 | 自動 |
| TC-039 | 作法 1「http 只限本機」 | 功能 | alice 存在 | `--platform-url http://localhost:8080` | 結束碼 0；信裡含該網址 | 自動 |
| TC-040 | 後端守則「錯誤訊息」；作法 4 | 例外 | 觸發 TC-031、TC-036、TC-044、TC-045 四種錯誤 | 檢查每一種的 stderr | 都說明原因與處理方式；都不含 `Traceback`、`sqlite`、`SELECT`、`tokens.db` | 自動 |

## User Story 5 — 用 `--out` 存成檔案，不覆蓋（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 | W10 | 功能 | alice 存在；暫存資料夾內沒有 `letter.txt` | 加 `--out <暫存>/letter.txt` 執行 | 結束碼 0；檔案內容與不加 `--out` 時的輸出完全相同 | 自動 |
| TC-042 | W10 | 功能 | 同 TC-041 | 同 TC-041 | stdout 只有一行，且含該檔路徑（不印信的內文） | 自動 |
| TC-043 | 作法 1「UTF-8、權限 600」 | 功能 | 同 TC-041，在支援權限的系統（Linux／WSL）上 | 同 TC-041 | 檔案可用 UTF-8 讀回；檔案權限為 600（不支援的系統略過這一項） | 自動 |
| TC-044 | W10 | 例外 | `letter.txt` 已存在 | 用同一個 `--out` 再跑一次 | 結束碼非零；檔案內容不變（不覆蓋） | 自動 |
| TC-045 | W10 | 例外 | `--out` 指向不存在的資料夾 | 執行 | 結束碼非零；白話訊息；沒有建立那個資料夾或檔案 | 自動 |
| TC-046 | 後端守則「寫入須先通過檢查」的對應 | 例外 | 壞網址（如 TC-036）加上 `--out <暫存>/x.txt` | 執行 | 結束碼非零，且 `x.txt` 沒有被建立 | 自動 |

## User Story 6 — 唯讀、不連網、不寄信、不留日誌（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-047 | W11；原話「對外送出任何訊息一律先給草稿」 | 不在範圍 | 取出 `tokens.db` 的 `users`、`tokens`、`cloud_caps` 三表全部內容 | 執行 `user welcome`（成功的一次） | 三表前後內容完全相同 | 自動 |
| TC-048 | 作法 7「不需要 migration」；計畫「不做：不持久化平台網址」 | 不在範圍 | 取出 `tokens.db` 的結構（`sqlite_master`） | 執行 `user welcome` | 結構前後完全相同：沒有新表、沒有新欄 | 自動 |
| TC-049 | W11 | 不在範圍 | 測試把 `socket.socket`、`smtplib` 換成「一被呼叫就失敗」 | 執行 `user welcome` | 指令仍成功（沒有嘗試連網或寄信） | 自動 |
| TC-050 | W11 | 不在範圍 | 讀 `welcome.py` 原始碼，以及 `cli.py` 裡 `cmd_user_welcome` 的內容 | 檢查 import | 沒有 `smtplib`、`urllib`、`http.client`、`subprocess` | 自動 |
| TC-051 | 作法 5「指令不寫任何 log 檔」 | 不在範圍 | 記下資料夾內的檔名清單 | 執行 `user welcome`（成功與失敗各一次） | 檔名清單前後相同，沒有新增任何檔案 | 自動 |
| TC-052 | 後端守則「一個動作一個函式」；計畫裁決 5 | 功能 | 讀 `cli.py` 與 `welcome.py` | 檢查 | `user` 子命令恰好是 add、cloud-cap、passwd、welcome；`welcome.py` 有 `welcome_text`；`cmd_user_welcome` 呼叫它；信的固定句（如「Your account on the platform is ready」）只出現在 `welcome.py`，`cli.py` 沒有第二份 | 自動 |

## User Story 7 — 說明、文件對得上程式，既有行為不變（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-053 | W14 | 功能 | 無 | 執行 `user welcome --help` | 說明含 `--platform-url`、`--operator`、`--out` | 自動 |
| TC-054 | W14 | 功能 | 無 | 執行 `user welcome --help` | 說明含「prints only」與「sends nothing」 | 自動 |
| TC-055 | W14 | 功能 | 無 | 讀 `cli.py` 第 2 行 docstring | 子命令清單含 `welcome` | 自動 |
| TC-056 | W15；作法 6 | 功能 | 無 | 讀 `docs/ONBOARDING.md` | 第 2 節與第 3 節各有一句指向 `abf-platform user welcome <name> --platform-url …`；文件裡每個 `abf-platform <word>` 的 `<word>` 都存在於 `cli.py` | 自動：`platform/tests/test_user_welcome.py`、`platform/tests/test_onboarding_doc.py` |
| TC-057 | W15；作法 6 | 功能 | 無 | 讀 `docs/ONBOARDING.md` | 仍恰好五個 `##` 標題；第 3 節仍恰好一個程式碼區塊，且四個佔位符都在 | 自動 |
| TC-058 | W13 | 功能 | 無 | `user add alice --lab lab-x` | 輸出仍含 `added user alice (lab lab-x)` 與 `issue a token with: abf-platform pat new --user alice` | 自動 |
| TC-059 | W13；計畫「不做：不在 user add 結束時印信」「不加提示行」 | 不在範圍 | 無 | `user add alice --lab lab-x --cloud-cap-usd 20` | 輸出沒有信的字樣（如 `Hi alice`、`Your account on the platform is ready`），也沒有 `welcome` 提示行 | 自動 |
| TC-060 | W13 | 功能 | alice 存在 | `user cloud-cap alice 30` | 訊息仍是 `monthly cloud cap of alice is now US$30.00 (每月雲端費用上限)` | 自動 |
| TC-061 | W13；完成標準 | 功能 | 本任務完成後的程式 | 原樣執行 `test_onboarding_doc.py`、`test_cloud_cost.py`、`test_temp_password.py`（`user passwd`、`pat new` 的行為由後者守住） | 全綠，且這三個檔案本次零修改 | 自動：這三個既有測試檔 |
| TC-062 | W15；完成標準 | 功能 | 同 TC-061 | 原樣執行 `bash tests/install_doc_test.sh`、`bash tests/operations_doc_test.sh` | 全綠；`docs/INSTALL.md` 零修改 | 自動：這兩個既有 shell 測試 |
| TC-063 | 計畫「範圍：不准動」清單 | 不在範圍 | 有 `origin/v3` 可比對時 | 測試以 `git diff --name-only origin/v3...HEAD` 列出變動檔 | 只含計畫「範圍：檔案」所列；`store.py`、web 介面檔、`docs/INSTALL.md`、`platform/pyproject.toml`、`spec.md`、`test-case*.md`、既有測試檔都沒有差異（沒有 `origin/v3` 時此項略過，由閱卷者看 diff） | 自動 |

## 憲法與安全網

本任務新增 Python 檔、一個會輸出給外人看的文字、一個會寫檔的旗標，碰到下列憲法條目：

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-064 | 第 1 條（新增東西須說明為何不用現成的） | 功能 | 新測試檔 `test_user_welcome.py` 與新檔 `welcome.py` | 執行 `platform/tests/test_scope.py` 的 `test_tc070_every_python_source_names_its_alternative` | 通過；兩個新檔的檔首第一行都是 `# Nothing existing: …` 且說明至少 15 字 | 自動：`platform/tests/test_scope.py` |
| TC-065 | 第 3 條（不寫個人或叢集路徑） | 功能 | 同 TC-064 | 執行 `test_scope.py` 的 `test_tc072_no_personal_or_cluster_paths` | 通過；新檔裡沒有個人或叢集路徑 | 自動：`platform/tests/test_scope.py` |
| TC-066 | 第 2 條（不另開送出路徑、不外連） | 功能 | 同 TC-064 | 執行 `test_scope.py` 的 `test_tc061_no_ssh_no_scheduler_no_outgoing_connection_in_the_source` 與 `test_tc071_no_submission_no_resident_loop_no_committed_database` | 通過；新檔沒有外連、沒有送出工作、沒有常駐迴圈 | 自動：`platform/tests/test_scope.py` |
| TC-067 | 第 7 條（沒有維護者也能完成） | 功能 | 任一正常案例的信 | 檢查信 | 信裡寫明登入方式、下一步（INSTALL.md、ONBOARDING.md 第 5 節）、出問題先看哪份文件（INSTALL.md 第 5 節、ONBOARDING.md 第 2 節）；同事不需另外問就知道下一步 | 自動 |
