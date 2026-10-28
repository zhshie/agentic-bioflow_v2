---
id: account-welcome-cli
title: 管理者開完帳號後，用一個指令印出（或存成檔）可寄出的歡迎信，帶入該同事的名字、實驗室與雲端月上限
tier: B
kinds: backend, docs
lane: L11-onboarding
branch: feat/account-welcome-cli
base: v3（`origin/v3` @ 9f6c8d2；查證日 2026-10-28；所有行號都是該版本）
source: memory/PLAN-abf-v3-replan-2026-10.md 第 187 行 H-2 的殘餘。H-2 `account-onboarding` 已在 PR #211 合併（10-25）；它的裁決 1 明說「歡迎信只在文件，不由 `user add` 印出；若要自動印，另開小任務 `after: cloud-cleanup-backfill`」。`cloud-cleanup-backfill` 已合併（PR #242），條件成熟，本檔就是那個小任務。
---

# account-welcome-cli

> 本檔由 developer-agent 助手起草（2026-10-28）。**先讀「查證結果」**：下達的任務 H-2 `account-onboarding` 大半已經完成，**本檔只規劃剩下的那一塊**，沒有覆蓋既有的 `memory/dev-plans/account-onboarding.md`（該任務已進 done，PR #211）。要不要做、id 要不要沿用，見「不確定的地方」。

## 目標
新增管理者指令 `abf-platform user welcome <name>`：從平台資料庫讀出這位同事的名字、實驗室與雲端月上限，**印出一封可直接複製寄出的歡迎信**（或用 `--out` 存成檔案）。對維護者的意義：開帳號之後不用再手動把 `docs/ONBOARDING.md` 第 3 節的範本四個佔位符換掉，也不會把「月上限」寫錯數字；信的內容和文件範本是同一份，不會各說各話。**程式不寄信**：只印出或存檔，寄不寄、用什麼寄由管理者決定。

### 查證結果（動手前的事實，全在 `origin/v3`）
H-2 原文三件事，逐項現況：
1. **「開帳號時設雲端月上限」＝已完成。** `abf-platform user add <name> --lab <lab> --cloud-cap-usd <N>`：`platform/abf_platform/cli.py:111-128`（`cmd_user_add`；先用 `store.parse_cloud_cap` 判斷、壞數字不建帳號 `:113-118`；建完 `store.set_cloud_cap` `:125-126`）；旗標宣告 `cli.py:690-695`；事後改用 `abf-platform user cloud-cap <name> <usd>` `cli.py:131-145`、`:696-699`。儲存：`tokens.db` 的 `cloud_caps(user_id, cap_usd, set_at)`，`store.py:147-150`；`parse_cloud_cap` 範圍 0～1,000,000 `store.py:810-823`；`set_cloud_cap` `:825`；`cloud_cap` 讀取（沒設回 `None`，沒有預設值）`:839-848`。測試：`platform/tests/test_cloud_cost.py:545-585`（`test_the_admin_commands_set_and_change_a_cap`、`test_a_bad_cap_is_refused_…`、`test_a_bad_cap_at_user_add_creates_no_account`）。
2. **「同事安裝站台代理的一頁說明」＝已完成，但檔名不是 `docs/INSTALL.md`。** 實作放在新檔 `docs/ONBOARDING.md`（第 5 節「A colleague on NCHC runs a station agent」，`ONBOARDING.md:119-161`）；原因寫在 `memory/dev-plans/account-onboarding.md` 裁決段 3：`tests/install_doc_test.sh:42-59` 把 `docs/INSTALL.md` 鎖成六個 `##`、且反引號詞必須是 MCP 工具名，改它要動既有測試。`docs/INSTALL.md` 現況是「同事把 AI app 接上平台」的說明（Claude Code／Desktop／Codex 三節），並沒有站台代理的內容。
3. **「歡迎信文字」＝只做了文件範本，沒有程式。** `docs/ONBOARDING.md:83-109`（第 3 節，一個 `text` 區塊，四個佔位符 `<platform-URL>`、`<name>`、`<lab>`、`<operator>`；雲端上限那句是通用文字，**不含此人的實際數字**，`:104`）。`user add` 結束時只印「added user … issue a token with: abf-platform pat new --user …」（`cli.py:127`），**沒有任何歡迎信輸出**；`cmd_user_passwd`（`cli.py:148-195`）與 `cmd_pat_new`（`cli.py:198` 起）也沒有。平台 CLI 沒有「列出／顯示單一使用者」的指令（`cli.py:689-711` 的 `user` 子命令只有 `add`、`cloud-cap`、`passwd`）；但 store 有 `user_by_name`（`store.py:883-891`，回 `{'user_id','name','lab'}`，只認未停用的人）與 `user_names`（`:872`）可用。
4. **平台對外網址不存在於資料庫或設定檔**：它只是 `abf-platform web --public-url`／`mcp --http --public-url` 的啟動旗標（`cli.py:53-62`、`:453-461`、`:669`、`:756`），沒有被持久化。所以歡迎信的 `<platform-URL>` 要由管理者在指令列給（見作法 2）；驗證網址的現成函式是 `abf_platform/common.py:188-199`（`public_url()`：https，或 http 只限 127.0.0.1／localhost；否則回 `None`）。
5. 搜過：`git grep -n "welcome\|歡迎" origin/v3 -- platform/abf_platform` → 沒有任何程式碼產生歡迎信；`git grep -n "ONBOARDING" origin/v3` → 只有 README 第 47 行指標與 `platform/tests/test_onboarding_doc.py`。沒有可套用的現成工具，自己寫（輸出是一段純文字模板，不需要模板引擎相依；平台刻意只依賴 `mcp`，`platform/pyproject.toml` 的 `[project.scripts]` 與依賴不動）。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md`：
- 「**H-2 `account-onboarding`**（B／backend+docs）：管理者開帳號指令（已有：終端建帳號）補「開帳號時設雲端月上限」、歡迎信文字、同事安裝站台代理的一頁說明（`docs/INSTALL.md`）。」（第 187 行）→ 三個名詞各一組測試：①「開帳號時設雲端月上限」＝既有，本任務加一條鎖住「不重做、不改」的回歸測試（W9）；②「歡迎信文字」＝本任務主體（W1～W8）；③「站台代理的一頁說明」＝既有 `docs/ONBOARDING.md` 第 5 節，歡迎信必須指向它（W6）。
- 「年底標準＝『能收費』：除了能用，還要託管部署腳本、帳號開通流程、律師問過……」（第 54 行，裁決 14）→ 「帳號開通流程」要能被管理者無痛重複做，歡迎信由指令產生而不是手改。
- 「試用成功標準改成：同事不問我就能跑完一次 16S（零支援）」（`dev-plans/account-onboarding.md` 維護者原話引 replan 第 17 條）→ 歡迎信必須自足：登入方式、下一步、遇到問題先看哪份文件，都在信裡（W6）。
- 「雲端上限：管理者開帳號時設，使用者不能改；單位美元、不換算」（`dev-plans/account-onboarding.md` 引 replan C-3）→ 信裡的數字是**美元**、不出現 `NT$`／台幣／匯率；信說明「由管理者設、你不能改」；沒設上限的人，信要誠實說「還沒設，目前不能送到雲端」，不能印出 `None` 或 0（W3、W4、W5）。
- 「國網用戶裝在個人電腦（持 2FA）；雲端用戶不裝代理」（`dev-plans/account-onboarding.md` 引 replan 第 13 條）→ 信對雲端用戶不要求裝代理，只對國網用戶指向第 5 節（W6）。
- 護欄（工作區總綱 §3.4）：「對外送出任何訊息（email／貼文／訊息一律先給草稿等他按送出）」→ 本指令**絕不寄信、不連網**（W10）。

## 範圍：檔案（只准改這些）
新增：
- `platform/tests/test_user_welcome.py`（檔首第一行須為 `# Nothing existing: …` 且 ≥15 字；`test_scope.py:76` 檢查，比照 `test_onboarding_doc.py:1`）
- `specs/account-welcome-cli/ledger.md`

修改（範圍內才准動）：
- `platform/abf_platform/cli.py`：只新增 `cmd_user_welcome`、一個純函式 `welcome_text(...)`（可放在 `cli.py` 或同套件新檔，見下）、在 `user` 子命令群加 `welcome` 一個 parser（靠近 `cli.py:696-699` 的 `cloud-cap`）；第 2 行 docstring 的子命令清單加 `welcome`。**不動** `cmd_user_add`／`cmd_user_cloud_cap`／`cmd_user_passwd` 的行為與輸出。
- `docs/ONBOARDING.md`：第 2 節步驟 1 與第 3 節各加一小段「也可以用 `abf-platform user welcome <name> --platform-url <platform-URL> --operator <operator>` 產生這封信」；**不新增 `##` 標題**（`test_onboarding_doc.py` 的 `test_tc001_five_headings` 釘住恰好五個）。第 3 節那個 fenced 區塊仍恰好一個，且四個佔位符、`PAT`、`password`、`NCHC`、`separately`、`must change` 等字仍在（`test_tc019`～`test_tc024`、`test_tc086`）。

可選新增（若 `cli.py` 因此太肥）：`platform/abf_platform/welcome.py`（只放純函式 `welcome_text`；無 I/O、無網路）。選哪個見「不確定的地方」1。

**不准動（硬規則）**：
- `docs/INSTALL.md`（`tests/install_doc_test.sh` 釘住六節；`docs/OPERATIONS.md`／`docs/PLATFORM.md`／`docs/TESTING.md`／`docs/CLOUD.md` 也不動）。
- `platform/abf_platform/store.py`（只用既有的 `user_by_name`、`cloud_cap`；不加表、不加欄、**不需要 migration**——不讀寫任何新資料）。
- web 介面檔案：`web.py`、`web_board.py`、`static/*`、模板、`DESIGN.md`、`test_web_*`（另一個 session 擁有）。
- 閘門檔：`spec.md`、`test-case*.md`、`.specify/memory/constitution.md`、`docs/ROADMAP.md`、`.github/`、`platform/pyproject.toml`、既有測試檔（`test_cloud_cost.py`、`test_onboarding_doc.py`、`test_temp_password.py` 不改；它們必須原樣綠）。
- `platform/abf_platform/`、`abf_station/`、`abf_launch/` 底下除 `cli.py`（與可選的 `welcome.py`）外的檔案。

## 作法
1. **指令簽章**：`abf-platform user welcome <name> --platform-url <URL> [--operator <text>] [--out <file>] [--lang en]`（`allow_abbrev=False`，同 `cloud-cap`）。
   - `<name>`：必須是現有、未停用的使用者；用 `store.user_by_name(store.default_tokens_path(), name)`（`store.py:883`）。沒有 → 非零結束，訊息仿 `cmd_user_cloud_cap`：`rejected: 沒有這個使用者 (no such user): <name>; add one with: abf-platform user add`（`cli.py:139`），不建立任何東西。
   - `--platform-url`：必填；經 `common.public_url()`（`common.py:188`）檢查，回 `None` 就拒絕並用白話說「要 https://主機，或 http 只限本機」（比照 `cli.py:58-62` 的措辭，中英並列）。不連網驗證網址。
   - `--operator`：選填，信末簽名；預設留 `<operator>` 佔位符原樣印出（管理者自己填）。
   - `--out <file>`：選填。給了就把信寫進該檔（UTF-8、檔案權限 600 在支援的系統上），stdout 只印一行「已存到 <path>」。檔案已存在 → 拒絕，不覆蓋（沒有 `--force`；管理者自己刪）。不給 `--out` 就印到 stdout。
2. **信的內容**由純函式 `welcome_text(name, lab, cap_usd, platform_url, operator)` 產生，**以 `docs/ONBOARDING.md` 第 3 節那封信為母本**（同樣的段落順序、同樣的關鍵字：temporary、PAT、password、NCHC、separately、must change、`docs/INSTALL.md`、section 2／4／5、`<your NSTC project>`），差別只有：`<name>`、`<lab>`、`<platform-URL>`、`<operator>` 換成真值，以及「Cloud cap」那句依此人實際狀態而定：
   - 有設且 > 0：`Cloud cap: your monthly cloud spending cap is US$<金額，兩位小數>. It is set by me; you cannot change it. Ask me if you need more.`
   - 有設且 = 0：`Cloud cap: your monthly cloud cap is US$0.00, so you cannot send runs to the cloud. Ask me if you need to.`
   - 沒設（`cloud_cap` 回 `None`）：`Cloud cap: I have not set your monthly cloud cap yet, so for now you cannot send runs to the cloud. NCHC runs are not affected.`（照 `user add --help` 的既有說法，`cli.py:693-694`）
   - 金額格式與 `cmd_user_add` 的 `US$%.2f`（`cli.py:126`）一致。
3. **不含任何祕密**：信裡永遠沒有 PAT、密碼、臨時密碼、agent token、國網帳號、計畫號（計畫號維持 `<your NSTC project>` 佔位）。指令**不產生**任何 token 或密碼，也不呼叫 `create_token`／`issue_temporary_password`；信只說「PAT／密碼我另外私下給你」。
4. **輸出分離**：指令不改資料庫（唯讀）。正文印到 stdout；錯誤印 stderr（`_err`，`cli.py:20`）。錯誤訊息不露堆疊、SQL、內部路徑（專長守則 backend）。
5. **人格化的名字只放進信裡，不放進日誌**：指令不寫任何 log 檔。
6. **文件**：`docs/ONBOARDING.md` 第 2 節步驟 1 後加一句「After the account exists, `abf-platform user welcome <name> --platform-url <platform-URL>` prints the letter of section 3 with this person's name, lab and cap filled in」；第 3 節範本保留（沒有指令可用時仍可手動換佔位符）。所有 `abf-platform <word>` 的 `<word>` 都須存在於 `cli.py`（`test_onboarding_doc.py` 的 `test_tc035_subcommands_exist` 會檢查，所以**程式必須先有 `welcome` 子命令文件才能寫**）；新出現的旗標 `--platform-url`、`--operator`、`--out` 要被 `test_tc036_flags_exist`／`test_tc084_tc085_the_flag_check_knows_temporary` 的旗標清單接受——**這兩個既有測試的旗標白名單是寫死的（`test_onboarding_doc.py:45` 的 `--(?:lab|user|owner|agent|temporary|cloud-cap[a-z-]*)`、`:263` 的清單）**，所以文件要避免出現白名單之外的旗標，否則測試會紅。處理方式：文件那句只寫 `abf-platform user welcome <name> --platform-url <platform-URL>`，而 `--platform-url` 恰是 `abf-station run` 也用的旗標（`ONBOARDING.md:156`），executor 先跑 `test_onboarding_doc.py` 確認；若紅，改為文件只寫 `abf-platform user welcome --help`。見「不確定的地方」3。
7. **不需要 migration**：沒有新表、沒有新欄、沒有寫入。

## 失敗先行測試（`platform/tests/test_user_welcome.py`；現在都會紅，因為 `welcome` 子命令不存在）
搭法：沿用 `test_cloud_cost.py:534-585` 的 `_env(tmp_path)`、`run_cli(...)`、`_cap_of`（`pkg_env`／`run_cli` 的來源看該檔 import）；資料庫在 `tmp_path/"data"`，不碰真實資料夾；不連網、不花錢。
| # | 案例 | 期望 |
|---|---|---|
| W1 | `user add alice --lab lab-x --cloud-cap-usd 20` 後 `user welcome alice --platform-url https://abf.example.org` | 結束碼 0；stdout 含 `alice`、`lab-x`、`https://abf.example.org`；不含任何殘留的 `<name>`、`<lab>`、`<platform-URL>` 佔位符；`<operator>` 在沒給 `--operator` 時仍原樣保留 |
| W2 | 加 `--operator Marvin` | stdout 末尾簽名為 `Marvin`，不再含 `<operator>` |
| W3 | cap=20 | 含 `US$20.00`、含「cannot change」；不含 `NT$`、`台幣`、`匯率`、`TWD` |
| W4 | `user add carol --lab x`（沒設上限）後 `welcome carol` | 含「not set」與「cannot send runs to the cloud」；**不含** `None`、`US$0`；結束碼 0 |
| W5 | `user add bob --lab x --cloud-cap-usd 0` | 含 `US$0.00` 與「cannot send runs to the cloud」；與 W4 的信不同（兩種狀態不能混） |
| W6 | 任一正常案例 | 信含 `temporary`、`PAT`、`password`、`NCHC`、`separately`、`must change`、`docs/INSTALL.md`、`docs/ONBOARDING.md`，且含對第 2／4／5 節的指向（正則比照 `test_onboarding_doc.py:176-179`）、含 `<your NSTC project>`；不要求雲端用戶裝站台代理（含 `Google Batch` 的區段不得叫人 `abf-station run`，或信中 `abf-station` 只出現在國網段落——executor 擇一寫死並註明） |
| W7 | 信與文件範本一致 | 把 `docs/ONBOARDING.md` 第 3 節 fenced 區塊的四個佔位符換成 W1 的值、再把 cap 句換成 W3 的句子後，與 W1 stdout **逐字相同**（鎖住「同一份文字」；改文件而不改程式或反之都會紅） |
| W8 | 沒有這個人（`welcome ghost --platform-url https://abf.example.org`） | 結束碼非零；stderr 含 `沒有這個使用者` 與 `abf-platform user add`；stdout 空；沒建立任何使用者（`store.user_id_of` 仍為 `None`） |
| W9 | 壞網址：`--platform-url http://abf.example.org`（非 loopback 的 http）、`abf.example.org`（沒 scheme）、含空白的網址 | 結束碼非零；stderr 含 `https`；stdout 空 |
| W10 | `--out` | 給 `--out <tmp>/letter.txt`：結束碼 0、檔案內容＝不加 `--out` 時的 stdout、stdout 只有一行含路徑；再跑一次同一指令 → 非零、檔案內容不變（不覆蓋）；`--out` 指到不存在的資料夾 → 非零、白話訊息 |
| W11 | 唯讀與不連網 | 跑前後 `tokens.db` 的 `users`、`tokens`、`cloud_caps` 三表內容相同（用 sqlite 取全表比對）；程式碼層面：monkeypatch `socket.socket`／`smtplib` 為遇到呼叫即失敗，指令仍成功；原始碼（`cli.py` 的 `cmd_user_welcome` 與 `welcome_text`）不 import `smtplib`／`urllib`／`http.client`／`subprocess` |
| W12 | 沒有祕密 | 對 W1、W4 的輸出：不含 `abf_pat_` 後接 8 個以上英數字（比照 `test_onboarding_doc.py` 的 `test_tc041_tc023_no_secrets`）、不含 `mst1\d{5}`、不含 `u9\d{7}`、不含 16 字元的混合英數字串（`test_tc086…` 那條正則）；指令執行前後 `tokens` 表筆數不變（沒有偷發 token） |
| W13 | 既有行為不變（回歸） | `user add` 的輸出逐字不變（至少仍含 `added user alice (lab lab-x)` 與 `issue a token with: abf-platform pat new --user alice`）；`user cloud-cap` 的訊息不變；`--cloud-cap-usd abc` 仍不建帳號（即 `test_cloud_cost.py:545-585` 原樣綠，本檔另加一條只確認 `user add` 的 stdout 沒有出現歡迎信字樣） |
| W14 | 說明文字 | `abf-platform user welcome --help` 含 `--platform-url`、`--operator`、`--out`，且說明「prints only; sends nothing（只印出，不寄信）」；`cli.py` 第 2 行 docstring 含 `welcome`（比照 `test_temp_password.py:745-747` 的做法） |
| W15 | 文件對得上程式 | 文件新增的那句裡每個 `abf-platform <word>` 都存在於 `cli.py`；`docs/ONBOARDING.md` 仍恰好五個 `##`；`test_onboarding_doc.py` 與 `tests/install_doc_test.sh`、`tests/operations_doc_test.sh` 原樣綠 |

**現在會紅的原因**：`welcome` 子命令不存在 → W1～W14 全部因 argparse 錯誤（結束碼 2）而紅；W13 的「stdout 沒有歡迎信字樣」在 base 上本來就綠，是守門員。executor 先跑一次貼紅綠分佈進 ledger。

## 完成標準（done when）
- `python -m pytest platform/tests/test_user_welcome.py` 全綠；`platform/tests/test_onboarding_doc.py`、`test_cloud_cost.py`、`test_temp_password.py`、`tests/install_doc_test.sh`、`tests/operations_doc_test.sh` **原樣**綠（零修改）；完整套件（`abf-fast-suite`／`tests/run_all.sh`，WSL）綠。
- `git diff --name-only origin/v3...HEAD` 只含「範圍：檔案」所列；web 檔案與 `store.py`、`INSTALL.md`、`pyproject.toml` 零差異（閱卷者看 diff，證據貼 ledger）。
- 已知環境紅（`dev-plans/README.md` 通例）：`test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 在完整 clone 上依 README 通例視同綠；若本任務動 `docs/ONBOARDING.md` 使它的比對基準改變，executor 在 ledger 說明，不改該測試。
- 沒有真的寄信、沒有網路呼叫、沒有花錢（W11）。
- 手動驗收（維護者，不擋合併）：在自己的平台資料夾 `abf-platform user add test-colleague --lab <lab> --cloud-cap-usd 5`，再 `abf-platform user welcome test-colleague --platform-url https://<your-domain> --operator <你的名字>`，把輸出貼到信箱草稿，確認讀得通、數字是 US$5.00。

## 環境事實
- 本檔所有行號為 2026-10-28 讀 `origin/v3`（9f6c8d2）。
- `cli.py` 是熱點檔：`dev-queue.json` 內其他任務可能同時在改它；開工前 `git fetch` 並確認 `origin/v3` 上沒有別的開著的 PR 動 `platform/abf_platform/cli.py`（H-2 的裁決 1 就是因此延後）。目前合併清單最後是 #245。
- 密碼與 PAT 一律只在管理者的真終端機顯示一次（`cli.py:148-195`、`:198`）；歡迎信**不是**發放祕密的管道，信裡明寫「另外私下給你」。
- `user_by_name` 只回未停用的人（`store.py:883-891`）；停用的人 `welcome` 視同「沒有這個使用者」。
- NCHC 沒有雲端上限（`ONBOARDING.md:35`），信不對國網做任何額度承諾。
- 外部寄信禁止（工作區護欄）；指令不得出現任何寄送能力。

## 不做
- 不自動寄信、不連網、不呼叫 Gmail／SMTP。
- 不在 `user add` 結束時自動印信（避免改動既有輸出與既有測試；見「不確定的地方」2）。
- 不產生或顯示 token／密碼／臨時密碼；不改 `passwd`、`pat new`。
- 不持久化平台網址（不加設定鍵、不加資料表）。
- 不做多語言信（只英文，與 `ONBOARDING.md` 一致；中文要點留在文件）。
- 不改 `docs/INSTALL.md`、不新增站台代理文件（已在 `ONBOARDING.md` 第 5 節）。
- 不碰網頁介面與 `store.py`；不加 migration。
- 不處理「遠端同事沒有平台主機 shell 時怎麼設密碼」——已由 `user passwd --temporary` 解決（PR 隨 `temp-password` 合併）。

## 不確定的地方（請 developer-agent 裁決）
1. **歸屬與 id**：下達的任務（H-2 `account-onboarding`）已經合併（`dev-queue.json` done 列 PR #211；`origin/v3` 有 `docs/ONBOARDING.md`、`specs/account-onboarding/`）。既有計畫檔 `memory/dev-plans/account-onboarding.md` 內容是那個已完成任務，我**沒有覆蓋它**。本檔用新 id `account-welcome-cli`（分支 `feat/account-welcome-cli`、車道 `L11-onboarding`）。若你要沿用 `account-onboarding` 這個 id，需先決定怎麼處理已 done 的舊檔（改名成 `account-onboarding-v1.md`？）。另需在 `dev-queue.json` 補一筆這個任務。
2. **要不要真的做**：H-2 的三件事實質都已有（月上限＝`user add --cloud-cap-usd`；站台代理說明＝`ONBOARDING.md` §5；歡迎信＝文件範本）。唯一缺口是「歡迎信由程式填值」，屬於「方便」而非「缺功能」。若維護者覺得手動換四個佔位符可接受，本任務可以不開。我的建議：開（約 0.5～1 agent 天），理由是數字寫錯（上限）比省工更貴，而且 W7 能把文件與信鎖成同一份。
3. **文件測試的旗標白名單**：`test_onboarding_doc.py:45`、`:263` 是寫死的旗標清單；文件若新增 `--operator`、`--out` 會紅，而該測試檔我列為「不改」。預設作法見作法 6（文件只寫 `--platform-url`，其餘讓 `--help` 說明）。若 executor 實測仍紅，兩個選擇：(a) 文件只寫 `abf-platform user welcome --help`；(b) 把 `test_onboarding_doc.py` 的白名單加旗標——這是「放寬安全網」，依總綱屬 C 級，**不要自己做，回報 BLOCKED**。
4. **子命令名稱**：`welcome` 還是 `letter`／`invite`？我選 `welcome` 因為與文件章節名「The welcome message」一致。
5. **`welcome_text` 放哪**：`cli.py` 內（現有風格，檔案已大）或新檔 `welcome.py`（較易單測、純函式）。預設新檔；若選 `cli.py` 就把 `welcome.py` 從範圍刪掉。
6. **`user add` 要不要在結尾多印一行提示**「想印歡迎信：abf-platform user welcome …」？這會改 `user add` 的輸出，雖然多一行不會讓 `test_cloud_cost.py` 紅（它只查結束碼與 cap），但 `test_temp_password.py` 與文件測試沒檢查這行，風險低。預設**不加**（W13 鎖住），文件講清楚即可。
7. **B 級合併規則**：依總表裁決 14，B 級（後端行為改變、非網頁畫面）verifier 通過＋CI 綠由 developer-agent 自合，事後列入每日清單。本檔照此。若認為歡迎信措辭會被維護者拿去對外使用而要他看過，改成 A 級（他驗收）；信文字本身來自他已驗收的 `ONBOARDING.md` 範本，故預設仍 B。
8. **信的語言**：維持純英文（母本如此）。若維護者要同事收到純中文信，另開任務，本檔不處理。

## 裁決

（developer-agent 2026-10-28 裁決，executor 與 verifier 照此辦）
1. id 定為 `account-welcome-cli`；舊檔 `account-onboarding.md` 不動（已 done）。佇列由 developer-agent 登記。
2. 做。理由同計畫：上限數字手抄易錯，W7 把信與文件鎖成同一份。
3. 文件只寫 `abf-platform user welcome <name> --platform-url <URL>`，`--operator`／`--out` 交給 `--help`。`test_onboarding_doc.py` 一律不改；若仍紅，回報 BLOCKED，不得放寬白名單。
4. 子命令名稱 `welcome`。
5. 純函式放新檔 `platform/abf_platform/welcome.py`；`cli.py` 只加子命令接線。
6. `user add` 輸出不變，不加提示行（W13 鎖住）。
7. B 級：verifier 通過＋CI 綠由 developer-agent 自合，事後列每日清單。
8. 信只做英文，與 `ONBOARDING.md` §3 一致。
9. `cli.py` 熱點：開工時 PR #246（aws-ce-type）也動 `cli.py`、即將合併。executor 只在 `user` 子命令群附近新增，不重排、不改其他子命令；合併衝突由 developer-agent 在 PR 階段解。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。

## 專長守則（docs）

（工作區沒有 `.claude/dev-profiles/docs.md`；本任務無專長守則。）


## 裁決（2026-10-28 13:10，BLOCKED(executor) 之後）
A1. 完整套件逾時是環境負載，不是斷言失敗：developer-agent 13:02 在 df7f53b 單獨重跑 `tests/platform_shard_3_test.sh`（417 秒，exit 0）與 `tests/platform_test.sh`（370 秒，exit 0），兩支都超過預設 300 秒上限。本任務的完整套件一律用 `bash tests/run_all.sh --timeout 900`（或 abf-fast-suite 加同樣的 900 秒上限）判定全綠；仍逾時才算 BLOCKED。程式不用改。
A2. `--lang` 旗標不做（照「不做」段）；手動驗收只留 ledger。
