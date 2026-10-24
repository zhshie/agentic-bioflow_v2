# 測試案例：同事開帳號與安裝站台代理的說明頁（account-onboarding）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
這個任務沒有 spec.md；規格來源是 `specs/account-onboarding/plan.md` 的「維護者原話」「作法」「失敗先行測試 T1–T13」「完成標準」「不做」。
維護者指示：測試案例只來自計畫裡的例子與敘述，不發明計畫沒說的行為。
-->

**規格**：`specs/account-onboarding/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、不該出現的東西出現時，檢查會怎麼反應（抓到、拒絕、提示）。
- **不在範圍**：計畫「不做」的事；測試確認它真的沒做。

「自動」的測試全部放在 `platform/tests/test_onboarding_doc.py`，每條測試在註解寫它的 TC 編號。括號內的 T1–T13 是計畫「失敗先行測試」表的編號。「手動」是驗收者讀檔、讀 ledger 或跑 `git diff` 核對（本任務不准改 `docs/TESTING.md`，見總覽的疑問）。

維護者原話對照（原話放在「對應需求」欄）：

- 「試用成功標準改成：同事不問我就能跑完一次 16S（零支援）」→ TC-017、TC-018、TC-007、TC-029
- 「同事帳號申請的說明（國網帳號＋加入計畫＋站台代理安裝）」→ TC-014、TC-027、TC-029、TC-031
- 「雲端上限：管理者開帳號時設，使用者不能改；單位美元、不換算」→ TC-008、TC-009、TC-022、TC-039、TC-040
- 「國網用戶裝在個人電腦（持 2FA）；雲端用戶不裝代理」→ TC-004、TC-005、TC-027

## User Story 1 — 文件的骨架與兩種人（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 T1；作法「恰好五個 `##` 標題」 | 功能 | `docs/ONBOARDING.md` 已寫好 | 列出檔內所有以 `## ` 開頭的行 | 恰好 5 個，依序含 `Who does what`、`The operator opens the account`、`The welcome message`、`The colleague connects`、`A colleague on NCHC runs a station agent`，編號 1 到 5 | 自動：T1 |
| TC-002 | 作法「英文為主，每節開頭附一句中文要點」 | 功能 | 同上 | 讀每個 `##` 標題後的第一段 | 五節的開頭段落都含中文字（要點），其餘說明為英文 | 自動：test_onboarding_doc.py（TC-002） |
| TC-003 | 作法 §1「兩個角色；一張表：誰在哪台機器做什麼」 | 功能 | 同上 | 讀 §1 | 有「operator」與「colleague」兩個角色的說明，並有一張表（含 `\|` 分隔的表格列）寫出各角色在哪台機器做什麼 | 自動：test_onboarding_doc.py（TC-003） |
| TC-004 | 維護者原話「雲端用戶不裝代理」；T8 | 功能 | 同上 | 在 §1 或 §5 找雲端用戶的說明 | 文中同時出現 `Google Batch` 與 `no station agent` 或 `install nothing`（措辭由執行者定） | 自動：T8 |
| TC-005 | 維護者原話「國網用戶裝在個人電腦（持 2FA）」；作法 §1 | 功能 | 同上 | 讀 §1 的表 | 表中寫出國網同事在自己的電腦（WSL 或 Linux）上跑站台代理；沒有寫成跑在平台主機上 | 自動：test_onboarding_doc.py（TC-005，查表格列含 NCHC 與 station agent） |

## User Story 2 — 管理者照清單開一個同事帳號（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-006 | 作法 §2「順序固定 a–e」 | 功能 | `docs/ONBOARDING.md` 已寫好 | 在 §2 內依出現位置排列這些指令的第一次出現 | 順序為 `user add` → `user passwd` → `pat new` → `agent-token new` → `ce create` → `pat list` | 自動：test_onboarding_doc.py（TC-006） |
| TC-007 | 作法 §2a「`abf-platform user add <name> --lab <lab> --cloud-cap-usd <N>`」 | 功能 | 同上 | 讀 §2 的第一步 | 該指令以此形式出現，單獨一行，其後有一句預期結果 | 自動：T2＋T3＋test_onboarding_doc.py（TC-007） |
| TC-008 | 原話「雲端上限：管理者開帳號時設…」；作法 §2a「沒給 `--cloud-cap-usd` 時此人不能送到雲端」 | 例外 | 同上 | 讀 §2a | 明說沒給 `--cloud-cap-usd` 的人不能送到雲端，之後要用 `abf-platform user cloud-cap <name> <N>` 補 | 自動：test_onboarding_doc.py（TC-008，查 `user cloud-cap` 與「不能送雲端」的英文句） |
| TC-009 | 原話「單位美元、不換算」；作法 §2a「範圍 0 到 1,000,000；國網不設上限」 | 功能 | 同上 | 讀 §2a | 寫明單位是美元、範圍 0 到 1,000,000（`store.py:732` 的 `CLOUD_CAP_MAX_USD`），國網（NCHC）不設上限 | 自動：test_onboarding_doc.py（TC-009，查 `1,000,000` 與 NCHC 句） |
| TC-010 | 作法 §2b「只能在真的終端機由本人輸入兩次，沒有旗標或檔案可以代填」 | 例外 | 同上 | 讀 §2b | 寫明：由本人在真的終端機輸入、輸入兩次；沒有任何旗標或檔案可代填。文中 `user passwd` 那一行後面沒有 `--password`、`--file` 之類的參數 | 自動：test_onboarding_doc.py（TC-010） |
| TC-011 | 作法 §2c「Claude Desktop 只要網頁密碼；Claude Code 要 `pat new --user <name>`」 | 功能 | 同上 | 讀 §2c | 兩條路分開寫：Claude Desktop 只要網頁密碼（OAuth）；Claude Code 用 `abf-platform pat new --user <name>` | 自動：test_onboarding_doc.py（TC-011） |
| TC-012 | 作法 §2c「PAT 只顯示一次」 | 功能 | 同上 | 讀 §2c | 明說 PAT 只顯示一次（弄丟要重發） | 自動：test_onboarding_doc.py（TC-012，查 `once`） |
| TC-013 | 作法 §2c「PAT 要在對方自己的終端機貼，不貼進聊天」 | 例外 | 同上 | 讀 §2c | 明說 PAT 在對方自己的終端機貼，不可貼進與 AI 的聊天 | 自動：test_onboarding_doc.py（TC-013，查 `chat` 與 `terminal`） |
| TC-014 | 原話「同事帳號申請的說明（國網帳號＋加入計畫＋站台代理安裝）」；作法 §2d | 功能 | 同上 | 讀 §2d | 國網同事的兩個指令各占一行：`abf-platform agent-token new <agent-name> --user <name>`，接著 `abf-platform ce create --owner <name> --agent <agent-name> …` | 自動：T2＋T3＋test_onboarding_doc.py（TC-014） |
| TC-015 | 作法 §2d「其餘欄位指向 `docs/PLATFORM.md` 的對應節，不重抄」 | 功能 | 同上 | 讀 §2d 的 `ce create` 之後 | 有指向 `docs/PLATFORM.md` 的一句話；沒有把 PLATFORM.md 的環境欄位表（如 `Key`／`Rule` 表頭）整段抄進來 | 自動：test_onboarding_doc.py（TC-015） |
| TC-016 | 作法 §2e「驗證：INSTALL.md §5；`abf-platform pat list` 看得到 token（不顯示值）」 | 功能 | 同上 | 讀 §2e | 請對方照 `docs/INSTALL.md` 的 §5 檢查；管理者端 `abf-platform pat list`，並說明不顯示 token 的值 | 自動：test_onboarding_doc.py（TC-016） |
| TC-017 | 原話「同事不問我就能跑完一次 16S（零支援）」；作法 §2「每步一個指令、一句預期結果」 | 功能 | 同上 | 驗收者逐步讀 §2 的 a–e | 每一步都有一個具體指令與一句預期會看到什麼；沒有只寫「請洽管理者」「請聯絡我」就結束的步驟 | 手動：驗收者讀檔核對 |
| TC-018 | 完成標準「文件裡每個指令一行一個，沒有『略』『同上』」 | 功能 | 同上 | 掃全文與所有 fenced 區塊 | 全文不含「略」「同上」；任一程式區塊的任一行最多只有一個 `abf-platform` 或 `abf-station` 指令（不用 `&&`、`;` 串兩個） | 自動：test_onboarding_doc.py（TC-018） |

## User Story 3 — 可原樣寄出的歡迎信（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 計畫 T6；作法 §3「一個 fenced 區塊，四個佔位符」 | 功能 | 同上 | 取出 §3 的 fenced 區塊 | §3 恰有一個 fenced 區塊，內含 `<platform-URL>`、`<name>`、`<lab>`、`<operator>` 四個佔位符 | 自動：T6 |
| TC-020 | 計畫 T6「含 §2、§4、§5 的指向」 | 功能 | 同上 | 讀區塊內文 | 區塊內有指向 §2、§4、§5 的字樣（寫成 `§N` 或 `section N` 皆可），並指向 `docs/INSTALL.md` | 自動：T6 |
| TC-021 | 作法 §3 內容清單 | 功能 | 同上 | 讀區塊內文 | 含：平台網址、登入方式兩條（網頁密碼、PAT）、下一步（§4 與 `docs/INSTALL.md`）、國網用戶指向 §5、遇到問題先看哪份文件 | 自動：test_onboarding_doc.py（TC-021） |
| TC-022 | 原話「單位美元」；作法 §3「雲端上限一句（美元、由管理者設）」 | 功能 | 同上 | 讀區塊內文 | 有一句講雲端月上限：單位美元（`US$` 或 `US dollars`）、由管理者設定 | 自動：test_onboarding_doc.py（TC-022） |
| TC-023 | 作法 §3「不含任何真實 token、密碼、國網帳號或計畫號」；T10 | 例外 | 同上 | 掃歡迎信區塊 | 無 `abf_pat_` 後接 8 個以上英數字、無 `mst1` 後接 5 位數、無 `u9` 後接 7 位數 | 自動：T10 |
| TC-024 | 作法 §3「計畫號用 `<your NSTC project>` 佔位」 | 例外 | 同上 | 讀區塊內文 | 凡講到計畫號，只出現 `<your NSTC project>`，沒有任何真實計畫號 | 自動：test_onboarding_doc.py（TC-024） |

## User Story 4 — 同事連上平台，國網同事裝站台代理（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 作法 §4「指向 `docs/INSTALL.md` 的三個 app 小節（不重抄）」 | 功能 | 同上 | 讀 §4 | 指向 `docs/INSTALL.md`，並點名 Claude Code、Claude Desktop、Codex 三個 app；全文沒有抄入 `claude mcp add` 指令 | 自動：test_onboarding_doc.py（TC-025） |
| TC-026 | 作法 §4「怎麼確認連上了：問 `list_runs`」 | 功能 | 同上 | 讀 §4 | 寫明請 Claude 端問 `list_runs`（唯讀）；`list_runs` 確實是 `mcp_server.py` 的工具名，也是 `docs/INSTALL.md` §5 用的那個名字 | 自動：test_onboarding_doc.py（TC-026） |
| TC-027 | 原話「同事帳號申請…（國網帳號＋加入計畫＋站台代理安裝）」；作法 §5 先決條件 | 功能 | 同上 | 讀 §5 開頭 | 先決條件寫三件：有國網帳號、已加入計畫、有 WSL 或 Linux bash | 自動：test_onboarding_doc.py（TC-027） |
| TC-028 | 作法 §5「原生 Windows／Git Bash 會被拒」 | 例外 | 同上 | 讀 §5 先決條件 | 明說原生 Windows 或 Git Bash 會被站台代理拒絕，要用 WSL | 自動：test_onboarding_doc.py（TC-028） |
| TC-029 | 原話「零支援」；作法 §5「步驟照 PLATFORM.md:140-171 的順序」 | 功能 | 同上 | 讀 §5 的步驟 | 順序為：token 檔放 WSL 自己的 home → `chmod 600` → `scripts/on_site.sh --check-reach` 印出的那行開共用連線 → `abf-station run` | 自動：test_onboarding_doc.py（TC-029，查出現順序） |
| TC-030 | 計畫 T7；作法 §5「token 檔放 WSL 自己的 home、`chmod 600`」 | 功能 | 同上 | 讀 §5 | 含 `chmod 600` 與 `--check-reach`，並說明 token 檔放在 WSL 自己的 home 而不是 Windows 磁碟 | 自動：T7 |
| TC-031 | 計畫 T4；作法 §5「`abf-station run --platform <platform-URL> --token-file ~/.config/abf/agent.token --deployment <root>`」 | 功能 | 同上 | 讀 §5 的 `abf-station` 指令 | 指令以 `run` 為子指令，三個旗標 `--platform`、`--token-file`、`--deployment` 都在 `abf_station/cli.py` 的 `run` 解析器裡 | 自動：T4 |
| TC-032 | 計畫 T7；作法 §5「平台網址除了 `localhost`／`127.0.0.1` 必須是 https」 | 例外 | 同上 | 讀 §5 | 含 `https`，並寫明只有 `localhost`、`127.0.0.1` 可用 http，其他網址用 http 會被拒 | 自動：T7 |
| TC-033 | 計畫 T7；作法 §5「怎麼知道它活著：問 `list_agents`」 | 功能 | 同上 | 讀 §5 | 含 `list_agents`，且它是 `mcp_server.py` 裡真的存在的工具名 | 自動：T7 |
| TC-034 | 作法 §5「出錯對照表只連到 PLATFORM.md 的『What it tells you』，不重抄」 | 功能 | 同上 | 讀 §5 結尾 | 有指向 `docs/PLATFORM.md` 「What it tells you」的一句話；沒有自己再列一份出錯對照表 | 自動：test_onboarding_doc.py（TC-034） |

## User Story 5 — 文件裡的指令、旗標、路徑都真的存在，也沒有洩漏（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-035 | 計畫 T2 | 功能 | 文件已寫好 | 抓出文中每個 `abf-platform <w1> [<w2>]` | 每個 `w1` 都是 `abf_platform/cli.py` 中 `sub.add_parser("<w1>"` 之一；`w1` 為 `user`、`pat`、`agent-token`、`ce` 時 `w2` 也是該組的子指令 | 自動：T2 |
| TC-036 | 計畫 T3 | 功能 | 同上 | 找文中的 `--lab`、`--cloud-cap-usd`、`--user`、`--owner`、`--agent` | 五個旗標都在 `abf_platform/cli.py` 的 `add_argument` 中 | 自動：T3 |
| TC-037 | 計畫 T4 | 功能 | 同上 | 抓出文中每個 `abf-station <w>` | 每個 `w` 都是 `abf_station/cli.py` 的子指令（`run`、`unforward`） | 自動：T4 |
| TC-038 | 計畫 T5 | 功能 | 同上 | 抓出文中反引號包住、以 `docs/`、`scripts/`、`platform/`、`deploy/` 開頭且有副檔名的路徑 | 每一個路徑在 repo 裡都存在 | 自動：T5 |
| TC-039 | 原話「單位美元、不換算」；T9 | 例外 | 同上 | 掃全文 | 不含 `NT$`、`台幣`、`匯率` | 自動：T9 |
| TC-040 | 同上；T9 | 功能 | 同上 | 掃全文 | 含 `US$` 或 `US dollars` | 自動：T9 |
| TC-041 | 計畫 T10 | 例外 | 同上 | 掃全文（不只歡迎信） | 沒有 `abf_pat_[A-Za-z0-9]{8,}`、`mst1\d{5}`、`u9\d{7}` | 自動：T10 |
| TC-042 | 計畫 T12（子指令變異） | 例外 | 複製一份文件，把其中 `user cloud-cap` 改成 `user cloudcap` | 用 T2 同一個檢查函式跑這份變異文件 | 檢查回報不存在（抓到）；原文件仍通過 | 自動：T12 |
| TC-043 | 計畫 T12（旗標變異） | 例外 | 複製一份文件，把 `--cloud-cap-usd` 全部改成 `--cloud-cap` | 用 T3 同一個檢查函式跑這份變異文件 | 檢查回報 `--cloud-cap` 不存在（抓到）。注意 `--cloud-cap` 是 `--cloud-cap-usd` 的前綴，旗標比對必須是整詞（後面不能再接字母、數字或連字號），否則抓不到 | 自動：T12 |
| TC-044 | 計畫「失敗先行測試」現況欄「紅」 | 例外 | 實作前（還沒有 `docs/ONBOARDING.md`） | 跑 `test_onboarding_doc.py` | T1 到 T12 失敗（不是被略過、不是通過）；ledger 貼出這次紅燈輸出 | 手動：驗收者讀 `specs/account-onboarding/ledger.md` |

## User Story 6 — README 指標與既有文件不動（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-045 | 計畫 T11；作法 6 | 功能 | README 已改 | 找 README 中指向 `docs/ONBOARDING.md` 的行 | 有一行含 `docs/ONBOARDING.md`，位置在 `docs/PITFALLS.md` 那一段之前，前後各空一行 | 自動：T11 |
| TC-046 | 計畫 T11「其他行與 base 逐字相同」；完成標準「README.md 只多出一段」 | 功能 | 同上 | 驗收者執行 `git diff <base>...HEAD -- README.md` | 只有新增行（那一段加前後空行），沒有任何刪除或改動的行 | 手動：驗收者跑 git diff；測試端另查 README 去掉該段後與 base 一致 |
| TC-047 | 計畫 T13 | 功能 | 同上 | 驗收者執行 `git diff <base>...HEAD -- docs/INSTALL.md docs/OPERATIONS.md`；再跑 `bash tests/install_doc_test.sh`、`bash tests/operations_doc_test.sh` | 兩份文件零差異，兩個既有 doc 測試仍通過 | 自動：T13 |
| TC-048 | 完成標準「`git diff --name-only` 只含上列 4 個檔」 | 功能 | 同上 | 驗收者執行 `git diff --name-only <base>...HEAD` | 只有 `docs/ONBOARDING.md`、`README.md`、`platform/tests/test_onboarding_doc.py`、`specs/account-onboarding/ledger.md`（`specs/account-onboarding/plan.md` 是計畫階段已提交，不算實作變動） | 手動：驗收者跑 git diff |
| TC-049 | 完成標準「`bash tests/run_all.sh`（WSL）綠」 | 功能 | 同上 | 在 WSL 跑完整測試 | 全部通過 | 自動：`tests/run_all.sh` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 不做「不改任何程式（歡迎信不印在 `user add`）」 | 不在範圍 | 實作完成 | 驗收者看 `git diff --name-only <base>...HEAD` 與 `abf_platform/cli.py` | `platform/abf_platform/`、`platform/abf_station/`、`scripts/`、`hooks/` 都沒有變動；`user add` 的提示字串仍是 `issue a token with: abf-platform pat new --user …`，沒有歡迎信 | 手動：驗收者跑 git diff |
| TC-051 | 不做「不改 `INSTALL.md`、`OPERATIONS.md`、`PLATFORM.md`、`TESTING.md`」 | 不在範圍 | 同上 | 驗收者執行 `git diff <base>...HEAD -- docs/PLATFORM.md docs/TESTING.md docs/INSTALL.md docs/OPERATIONS.md` | 四份零差異 | 手動：驗收者跑 git diff（INSTALL／OPERATIONS 另有 TC-047） |
| TC-052 | 不做「不寫國網帳號申請的外部流程細節」 | 不在範圍 | 同上 | 驗收者讀 §5 先決條件 | 只說「要有國網帳號、已加入計畫」，沒有教人怎麼向國網申請帳號或計畫的步驟 | 手動：驗收者讀檔 |
| TC-053 | 不做「不寫計畫號、帳號、token、密碼的任何真值」 | 不在範圍 | 同上 | 掃 `docs/ONBOARDING.md` 與 `README.md` 新增的那一段 | 無任何真實 token、密碼、國網帳號、計畫號；只有 `<name>`、`<your NSTC project>` 之類的佔位符 | 自動：T10＋test_onboarding_doc.py（TC-053，另掃 README 新增行） |

## 憲法與安全網

<!-- 本任務只動文件與一支測試；以下是計畫「必須仍綠」清單中，會被新文件或新測試碰到的規則。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-054 | 原則 I.1（新程式要說明為何不用現成的；計畫指名 `platform/tests/test_scope.py:76`） | 功能 | 新測試檔已加 | 跑 `test_scope.py` | `test_onboarding_doc.py` 檔首有 `# Nothing existing: …` 且說明至少 15 字，`test_scope.py` 通過 | 自動：`platform/tests/test_scope.py` |
| TC-055 | 安全網範圍（Constitution 2.0.0；計畫指名 `tests/constitution_scope_test.sh:67,73`） | 功能 | README 已改 | 跑 `bash tests/constitution_scope_test.sh` | README 仍含 `Constitution 2.0.0`；README 與新文件都沒有「safety net … every session」之類的無條件字樣 | 自動：`tests/constitution_scope_test.sh` |
| TC-056 | 原則 II（路徑不寫死；檢查 `tests/no_hardcoded_paths.sh`） | 功能 | README 已改 | 跑 `bash tests/no_hardcoded_paths.sh` | README 沒有 `/home/<名>/` 形狀的路徑 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-057 | 計畫指名 `tests/works_without_host_test.sh:92` | 功能 | 新文件已加 | 跑 `bash tests/works_without_host_test.sh` | 新文件中每個反引號包的 `scripts/…` 路徑都存在 | 自動：`tests/works_without_host_test.sh` |
| TC-058 | 計畫指名 `platform/tests/test_cloud_wire.py:411` | 功能 | 新文件與 README 已改 | 跑 `test_cloud_wire.py` | `docs/` 與 `README.md` 不含「還沒有費用預估與上限」「接線之前確認畫面仍寫」 | 自動：`platform/tests/test_cloud_wire.py` |
| TC-059 | 計畫指名 `tests/platform_direction_docs_test.sh:386-392,537` | 功能 | README 已改 | 跑 `bash tests/platform_direction_docs_test.sh` | README 既有被鎖字串都還在，測試通過 | 自動：`tests/platform_direction_docs_test.sh` |

<!--
- 編號核准後不重編；刪除的案例保留該列並加刪除線。
- 每個「自動」案例在 test_onboarding_doc.py 的測試註解寫上 TC 編號，驗收者靠它找對應。
-->
