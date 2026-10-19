# 測試案例：014a 聊天後端（瀏覽器聊天可用的工具清單，與模型金鑰的拒收）

<!--
Written by the verifier (CONTRACT mode). Reader: the maintainer, who is not an engineer.
這個切片沒有獨立的 spec.md；規格就是 `specs/014a-chat-backend/plan.md`（開頭引用了他 2026-10-18 核可的原話）。
下面「對應需求」欄寫的是計畫裡的段落名，「他的例句」指計畫開頭他的原話。
-->

**規格**：`specs/014a-chat-backend/plan.md`（無獨立 spec.md）　**總覽**：`test-case-overview.md`

他的原話（逐字，來自計畫）：
- E1「設定頁貼 Claude API 金鑰」
- E2「問「我的分析跑到哪了？」→ 顯示用了哪個工具＋一句回答」
- E3「「幫我送出」→ AI 只能備好摘要頁，送出他自己按」
- E4「第一版只接 Claude API，本地模型下一版」
- E5「模型金鑰只存瀏覽器」

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者（或 AI）做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

名詞：「工具」指平台對 AI 開放的 MCP 工具（例如 list_runs、launch）。「請求工具」指 launch、cancel、resume、relaunch、forget 這五個：它們只能「提出請求」，真正的「是」要由本人按。「清單」指 `tool_specs` 回傳、要交給瀏覽器聊天頁的工具清單。

## User Story 1 — 瀏覽器聊天只拿到安全、且與平台同步的工具清單（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 Do1·tool_specs（清單由已註冊的 MCP 伺服器衍生） | 功能 | 平台伺服器目前註冊了 11 個工具：6 個唯讀（list_runs、get_run、list_compute_envs、get_compute_env、list_agents、list_site_files）與 5 個請求工具（launch、cancel、resume、relaunch、forget） | 呼叫 `tool_specs`，拿清單裡所有工具名稱，跟「伺服器自己列出的工具中，標示為唯讀、或名字在 REQUEST_TOOLS 裡的那些」比對 | 兩邊名稱集合完全相等（目前剛好是上面那 11 個）；清單沒有任何伺服器沒有的名字，也沒漏掉符合條件的工具 | 自動：`platform/tests/test_chat_tools.py` |
| TC-002 | 計畫 Do1·禁字；他的例句 E3 | 例外 | 同 TC-001 | 檢查清單裡每個工具的名稱，以及每個 input_schema 宣告的每個參數名稱 | 沒有任何一個名稱符合 approve、confirm、confirmed_by、void、yes（不分大小寫）：也就是 AI 手上沒有任何能替人說「是」的工具或參數 | 自動：`platform/tests/test_chat_tools.py` |
| TC-003 | 計畫 Do1·禁字；Architecture（不建伺服器端聊天、不收金鑰） | 例外 | `platform/abf_platform/actions/chat_tools.py` 已存在 | 用程式語法樹（AST）掃這個檔案的 import、名稱、屬性、函式與參數名稱，另對原始碼逐字找 api_key | import 與名稱裡沒有 TERMINAL、ELICITED、PAGE（大小寫須相符），沒有 approve、confirm（不分大小寫）；沒有 `import anthropic`（含 from … import）；整個檔案原始碼找不到 api_key。（掃描對象是程式識別字與 import；系統提示字串內的文字不在此列，見總覽疑問 1） | 自動：`platform/tests/test_chat_tools.py` |
| TC-004 | 他的例句 E3「幫我送出」；計畫 Do1·tool_specs（請求工具只寫待確認請求）；計畫 TC-004 | 例外 | 一個已登入的人 ann，環境 lab-a 可用，樣本表備好（沿用 `test_human_channel.py` 的 World 設備）；沒有人回應表單 | 不經過任何人，用 ann 的身分直接呼叫 `launch`（參數與 `test_tch09` 同）；再用「本機 stdio（沒有登入者）」身分呼叫一次 | ann：回覆 `sent` 為 false、`state` 為 pending，帶一個確認頁網址 `confirmation_url` 與一段摘要 `summary`（AI 只備好摘要頁）；資料庫裡只多一筆「待確認」請求、沒有任何 launch 工作（job）被排隊。stdio：`sent` 為 false，沒有任何工作被排隊 | 自動：`platform/tests/test_chat_tools.py`（照 `test_human_channel.py::test_tch09_nothing_reaches_the_queue_through_the_tools_without_a_person` 的寫法） |
| TC-005 | 計畫 Do1·CHAT_SYSTEM_PROMPT；他的例句 E3 | 功能 | `CHAT_SYSTEM_PROMPT` 存在 | 讀這段系統提示 | 它是一段非空的純文字（str），含「送出」兩字，並說明送出只在本人於確認頁按「送出」時才發生、AI 不能代按 | 自動：`platform/tests/test_chat_tools.py`（字串含「送出」）；說明的語意由驗收者讀文字判斷 |
| TC-006 | 計畫 Do1·tool_specs（forget 列在 REQUEST_TOOLS）；計畫 TC-004 | 例外 | 一個已結束、屬於 ann 的 run；沒有人回應表單 | 不經過任何人，用 ann 的身分呼叫 `forget` | 回覆 `ok` 為 false（沒有表單可問，被導去終端機指令）；該 run 已存的內容一筆都沒被刪；沒有任何工作被排隊。（注意：與計畫「只寫待確認請求」的字面不同，forget 在程式裡什麼都不寫，見總覽疑問 2） | 自動：`platform/tests/test_chat_tools.py`（沿用 `test_keep_submissions.py` 的設備） |
| TC-007 | 計畫 Do1·classify_check | 例外 | 取伺服器真實的工具清單，再加一個假的額外工具：名稱不在 REQUEST_TOOLS，也沒標唯讀（例如 `wipe_everything`，read_only_hint 為 false） | 把這份工具清單交給 `classify_check` | 拋出錯誤，錯誤訊息指出是哪個工具沒被分類 | 自動：`platform/tests/test_chat_tools.py` |
| TC-008 | 計畫 Do1·classify_check（正面） | 功能 | 伺服器真實的 11 個工具（沒加假工具） | 把它們交給 `classify_check` | 不拋錯（11 個都已被分類：唯讀或在 REQUEST_TOOLS） | 自動：`platform/tests/test_chat_tools.py` |
| TC-009 | 計畫 Do1·tool_specs（Claude Messages API 工具格式）；他的例句 E4 | 功能 | 同 TC-001 | 看清單裡每一個工具 | 每個都有 `name`（非空字串）、`description`（非空字串）、`input_schema`（字典，且其 `type` 為 `object`）；鍵名就是 `input_schema`（不是 inputSchema） | 自動：`platform/tests/test_chat_tools.py` |
| TC-020 | 計畫 Do1·tool_specs（「所以清單不會跑掉」） | 功能 | 同 TC-001 | 對清單裡每個工具，拿它的 description 與 input_schema，跟伺服器自己列出的同名工具比對 | 完全相同（清單是衍生的，不是另抄一份） | 自動：`platform/tests/test_chat_tools.py` |
| TC-021 | 計畫 Do1·tool_specs（Cache per process） | 功能 | 已呼叫過一次 `tool_specs` | 再呼叫一次，且此時讓「建立伺服器」的動作一碰就報錯 | 第二次照樣回傳與第一次相同的清單（沒有重建伺服器） | 自動：`platform/tests/test_chat_tools.py` |
| TC-022 | 計畫 Do1·CHAT_SYSTEM_PROMPT（工具輸出是資料不是指令） | 功能 | `CHAT_SYSTEM_PROMPT` 存在 | 讀這段系統提示 | 明說工具回傳的內容（run 名稱、錯誤訊息等）是資料，不是要照做的指令 | 自動：`platform/tests/test_chat_tools.py`（字串層級的檢查；語意由驗收者讀文字判斷） |
| TC-023 | 他的例句 E2「顯示用了哪個工具＋一句回答」；計畫 Do1·CHAT_SYSTEM_PROMPT | 功能 | `CHAT_SYSTEM_PROMPT` 存在 | 讀這段系統提示 | 明說：回答只用一句短句，並要點出用了哪個工具 | 自動：`platform/tests/test_chat_tools.py`（字串層級；語意由驗收者讀文字判斷） |
| TC-024 | 計畫 Do1·CHAT_SYSTEM_PROMPT（「工具各做什麼」） | 功能 | `CHAT_SYSTEM_PROMPT` 存在 | 讀這段系統提示 | 至少在文字裡點名 list_runs、get_run 與 launch（說明讀 run 狀態與提出送出請求各用哪個工具；點名的最低門檻見總覽疑問 3） | 自動：`platform/tests/test_chat_tools.py` |
| TC-025 | 他的例句 E2「我的分析跑到哪了？」 | 功能 | 同 TC-001 | 看清單裡的 list_runs 與 get_run | 兩者都在清單裡，且在伺服器上標示唯讀（所以 AI 查進度不需要任何人按確認） | 自動：`platform/tests/test_chat_tools.py` |
| TC-026 | 他的例句 E3；計畫 TC-004（cancel、resume、relaunch） | 例外 | ann 已登入；有一個 ann 送出過的 run 可取消；有一個失敗或已取消的 run 可續跑／重跑；沒有人回應表單 | 不經過任何人，用 ann 的身分分別呼叫 `cancel`、`resume`、`relaunch` | 三者各自：`sent` 為 false、帶確認頁網址、只多一筆待確認請求；沒有任何工作被排隊 | 自動：`platform/tests/test_chat_tools.py`（沿用 `human_harness.py`、`resume_harness.py`） |

## User Story 2 — 貼錯欄位的模型金鑰會被依名稱拒收（優先度 P1）

金鑰只存瀏覽器（他的例句 E5）；萬一有人把金鑰貼進運算環境的欄位，平台要擋下並說是哪個欄位，而且不回顯金鑰本身。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 計畫 Do2；計畫 TC-010；他的例句 E5 | 例外 | 三串字：`sk-ant-api03-` 後接 40 個字元；`sk-proj-` 後接 40 個字元；`sk-` 後接 40 個字元（後面的字元由字母、數字、底線、連字號組成） | 對每一串呼叫 `looks_like_credential` | 三串都回 True | 自動：`platform/tests/test_model_key_refusal.py` |
| TC-011 | 計畫 Do2；計畫 TC-011 | 功能 | 一般文字：`disk-usage`、`task-runner-42`、`ask-me`、`sk-` 後接不到 20 個字元（例如 19 個） | 對每一個呼叫 `looks_like_credential` | 四個都回 False（一般文字不被當金鑰） | 自動：`platform/tests/test_model_key_refusal.py` |
| TC-013 | 計畫 Do2；計畫 TC-010 後半 | 例外 | 一個運算環境設定，其中某個欄位的值是上述任一種模型金鑰 | 對這份設定呼叫 `credential_findings` | 回傳那個欄位的路徑（例如含 nextflowConfig 或 environment 的路徑）；回傳內容裡找不到金鑰字串本身 | 自動：`platform/tests/test_model_key_refusal.py` |
| TC-012 | 計畫 Do2；計畫 TC-012（nextflowConfig） | 例外 | 一個空的平台資料夾，沿用 `test_station_envs.py` 的 `Inproc` 設備 | 用現有的建立運算環境路徑（`create_slurm`），在 nextflowConfig 欄位放一個模型金鑰（三種形狀各試一次） | 建立失敗（回傳碼非 0）；訊息指出是 nextflowConfig 這個欄位，並帶現有的「像憑證／憑證放代理那邊」說明；金鑰字串不出現在訊息裡 | 自動：`platform/tests/test_model_key_refusal.py` |
| TC-017 | 計畫 Do2；計畫 TC-012（environment） | 例外 | 同 TC-012 | 用 `create_slurm`，在環境變數 environment 的某個值放一個模型金鑰（三種形狀各試一次） | 建立失敗（回傳碼非 0）；訊息指出是 environment 這個欄位，並帶同樣的說明；金鑰字串不出現在訊息裡 | 自動：`platform/tests/test_model_key_refusal.py` |
| TC-015 | 計畫 Do2（「不要放寬或重排現有樣式」） | 例外 | 現有六個憑證樣式（私鑰標頭、AKIA／ASIA 金鑰編號、aws_secret_access_key、abf_ 權杖、export … TOKEN=、password／token 等欄位）原樣存在 | 跑現有 `test_tc036_*`（12 種憑證形狀）；再比對 `_VALUE_PATTERNS` 最前面六個樣式的文字與順序 | `test_tc036_*` 未被修改且全過；前六個樣式的內容與順序跟 main 完全相同，兩個新樣式接在它們後面 | 自動：`platform/tests/test_station_envs.py`（原檔、不得更動）與 `platform/tests/test_model_key_refusal.py` |
| TC-016 | 計畫 Do2（「確認沒有現有測試資料或文件範例被誤判」） | 功能 | 現有的測試與文件範例 | 跑整套平台測試（含 `test_tc037_an_ordinary_slurm_config_is_not_mistaken_for_a_credential`） | 全綠；普通的 Slurm 設定（例如 `process.queue = 'normal'`、`NXF_OPTS=-Xmx2g`）仍被接受，沒有任何現有測試資料或文件範例被新樣式誤攔 | 自動：整套 `platform/tests/`（WSL 執行，見 `docs/TESTING.md`） |

## 不在範圍

計畫「Out of scope」逐項：頁面 JS、聊天路由／UI、金鑰的瀏覽器儲存、CSP、外部工具、本地模型、供應商 CORS 試驗、docs/PLATFORM.md 與 ROADMAP、CHANGELOG.md，以及「不要改 actions/__init__.py、mcp_server.py、web.py、web_board.py」；另加架構約束「不建伺服器端聊天迴圈、不加 anthropic SDK、不收 api_key」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | Architecture；他的例句 E5「模型金鑰只存瀏覽器」 | 不在範圍 | 平台套件原始碼，與伺服器註冊的所有工具 | 掃 `platform/abf_platform`、`abf_launch`、`abf_station` 所有函式參數名稱，與伺服器所有工具的 input_schema 參數名稱 | 沒有任何一個叫 api_key（或 apikey）：平台任何地方都不收模型金鑰 | 自動：`platform/tests/test_chat_tools.py` |
| TC-031 | Architecture（不加 anthropic SDK） | 不在範圍 | `platform/pyproject.toml`、`platform/constraints.txt`、平台套件原始碼 | 讀這些檔案找 anthropic | 相依套件與限制檔都沒有 anthropic；所有原始碼沒有 import anthropic | 自動：`platform/tests/test_chat_tools.py` |
| TC-032 | 計畫 Out of scope：頁面 JS、聊天 UI、瀏覽器儲存、CSP、不改的四個檔、他的例句 E1（設定頁貼金鑰屬於之後的頁面） | 不在範圍 | 實作完成的分支 | 執行 `git diff main...HEAD --stat`，看被改動的檔案 | 只出現：`platform/abf_platform/actions/chat_tools.py`、`platform/abf_platform/compute_envs.py`、`platform/tests/test_chat_tools.py`、`platform/tests/test_model_key_refusal.py`、`specs/014a-chat-backend/` 底下的檔案、`docs/TESTING.md`（加手動步驟）；`actions/__init__.py`、`mcp_server.py`、`web.py`、`web_board.py` 沒在其中；沒有任何 .js、.html、靜態檔或樣式檔被新增 | 手動：`docs/TESTING.md`（014a 一節，由實作者新增） |
| TC-033 | 計畫 Out of scope：聊天路由／UI；他的例句 E1 | 不在範圍 | 平台網頁應用程式（web app） | 列出它所有路由路徑 | 沒有任何路徑含 chat；也沒有收模型金鑰的設定頁路由 | 自動：`platform/tests/test_chat_tools.py` |
| TC-034 | 計畫 Out of scope：外部工具（PubMed 等） | 不在範圍 | 同 TC-001 | 看清單裡所有工具名稱 | 全都是平台伺服器自己的工具；沒有任何外部來源的工具（例如 PubMed、SRA、nf-core 文件） | 自動：`platform/tests/test_chat_tools.py`（與 TC-001 同一個斷言面） |
| TC-035 | 計畫 Out of scope：本地模型、供應商 CORS 試驗；Architecture（不建伺服器端聊天迴圈）；他的例句 E4 | 不在範圍 | `chat_tools.py` | 用 AST 看它 import 了什麼 | 沒有 import 任何模型供應商或網路用戶端程式庫（anthropic、openai、httpx、requests、aiohttp、urllib、socket）；沒有任何函式去呼叫模型或回覆使用者 | 自動：`platform/tests/test_chat_tools.py` |
| TC-036 | 計畫 Out of scope：docs/PLATFORM.md、ROADMAP、CHANGELOG.md | 不在範圍 | 實作完成的分支 | 執行 `git diff main...HEAD --stat -- docs/PLATFORM.md docs/ROADMAP.md CHANGELOG.md` | 空的（沒有任何改動） | 手動：`docs/TESTING.md`（014a 一節，由實作者新增） |

## 憲法與安全網

涉及：原則 I.2 的「人的『是』只能從三個通道來」（`test_tch09_*` 守著）、原則 I.1（每個程式檔要宣告「不是哪個現成工具」）、安全網的憑證規則與 ADR 0010（平台不收模型金鑰）、「每階段全綠」。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 原則 I.2（未經確認的送出被拒絕）；安全網「送出前要明確確認」 | 例外 | 現有的未確認送出檢查 | 跑 `test_human_channel.py` 的 `test_tch09_*` 與 `test_confirm_page.py` 的 `test_tch09_b_c_*`，並看 `git diff main...HEAD` 對這兩個檔案 | 全過；這兩個檔案在 diff 中沒有任何更動（沒被放寬、刪除或跳過） | 自動：`platform/tests/test_human_channel.py`、`platform/tests/test_confirm_page.py` |
| TC-041 | 原則 I.1（每個程式檔開頭宣告 `# Not <工具>：<原因>` 或 `# Nothing existing：<原因>`） | 功能 | 新檔 `chat_tools.py` 與兩個新測試檔 | 跑 `platform/tests/test_scope.py::test_tc070_every_python_source_names_its_alternative` | 全過：新檔開頭 40 行內有合格的宣告行，原因不少於 15 字 | 自動：`platform/tests/test_scope.py` |
| TC-042 | 安全網憑證規則；ADR 0010「平台不持有模型金鑰」 | 例外 | 一個放了模型金鑰的運算環境建立請求被拒絕之後 | 檢查資料庫列與平台資料夾所有檔案的位元組 | 拒絕後資料庫內容與拒絕前相同；整個平台資料夾裡（含資料庫與記錄）找不到那串金鑰（沿用 `test_tc036` 的 `ip.rows()` 與 `ip.all_bytes()` 寫法） | 自動：`platform/tests/test_model_key_refusal.py` |
| TC-043 | 開發流程「每階段全綠」；「不得弱化既有測試」 | 功能 | 實作完成的分支 | 在 WSL 跑整套測試；並執行 `git diff main...HEAD -- platform/tests tests`，列出被動到的既有測試 | 全套全綠（或 CI 全綠）；在既有測試檔裡沒有任何斷言被刪除、放寬、改期望值或跳過（新增的兩個測試檔除外） | 手動：`docs/TESTING.md`（014a 一節，由實作者新增）；機器部分為整套 `tests/run_all.sh` |

## 修訂 2026-10-19：確認視窗（計畫 Revision 2026-10-19）

計畫把新案例叫 TC-030..033，與上面已有的編號撞名，故編為 TC-050..053（TC-005 的斷言改為含「確認送出嗎」與「按」；TC-003 收窄為只放過 `confirm_dialog` 這個函式名，其餘仍不得出現 approve／confirm）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 修訂 Do1 | 功能 | 一個真的 launch 請求（無人在場），狀態 pending | 對它的結果呼叫 `confirm_dialog("launch", 結果)` | 回傳 `{question: 確認送出嗎？, tool, summary, confirmation_url, buttons: [確認, 取消]}`，摘要與網址同結果；工作佇列仍是空的、確認請求仍是 pending | 自動：`platform/tests/test_chat_tools.py` |
| TC-051 | 修訂 Do1 | 例外 | 唯讀工具名稱；或 sent 為真、state 非 pending、沒有 confirmation_url、非請求形狀的結果 | 呼叫 `confirm_dialog` | 全部回傳 None | 自動：`platform/tests/test_chat_tools.py` |
| TC-052 | 修訂 Do1、Do3 | 功能 | REQUEST_TOOLS 的每個名稱，配一個 pending 形狀的結果 | 呼叫 `confirm_dialog` | 每個都得到視窗；字典只有五個鍵，沒有 approve／yes／confirmed 之類的鍵 | 自動：`platform/tests/test_chat_tools.py` |
| TC-053 | 修訂 Do3（原 TC-033） | 例外 | 有 `confirm_dialog` 的 `chat_tools.py` | 跑收窄後的 TC-003 原始碼掃描 | 仍通過：除 `confirm_dialog` 外沒有任何名稱含 approve／confirm，也沒有 TERMINAL／ELICITED／PAGE／api_key | 自動：`platform/tests/test_chat_tools.py` |
