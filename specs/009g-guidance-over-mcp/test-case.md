# 測試案例：009g 指引經由網址送達（MCP instructions、prompts、skills 當 resources、打包副本）

**規格**：無 `spec.md`（依維護者指示一律以 `specs/009g-guidance-over-mcp/plan.md` 為準；計畫的「給維護者」三句是他看得懂的承諾）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、有人想繞過時，系統怎麼反應（拒絕、丟錯）。
- **不在範圍**：計畫「Not in this PR」明講這次不做的事；測試確認它真的沒做。

維護者的話（計畫「給維護者」，逐字）：

1. 「使用者只要貼上伺服器網址，就會拿到「怎麼用」：連線時自動讀到路由表（想跑 RNA-seq 該走哪個流程），每個流程另有一個 MCP prompt 放完整 SKILL.md。」
2. 「這一步沒有新的寫入工具、沒有登入；六個唯讀工具一個字都沒變。」
3. 「技能文字只有一份（repo 的 `skills/`）；打包時複製進 `abf-platform`，測試保證複製品與 repo 相同。」

另有 ADR 0006 的例句：「"I want to run RNA-seq" is routed without anyone picking anything」。下面 TC-102、TC-201、TC-204、TC-301、TC-303、TC-401、TC-404、TC-405、TC-501、TC-502、TC-503 直接用這些話當輸入與預期結果。

名詞：**instructions**＝MCP 伺服器在使用者連線時自動交給模型的一段說明文字；**prompt**＝MCP 伺服器提供的、客戶端會列成指令讓使用者選的一段文字範本；**resource**＝MCP 伺服器提供的、可用網址式名稱（URI）讀取的一份文件；**路由表**＝`skills/operational/SKILL.md` 裡「The five commands」那張表，告訴模型哪種需求該走哪個流程；**流程技能**＝`skills/` 裡的 `setup`、`launch`、`runs`、`downstream`、`finish` 五個（`operational` 是路由本身，不算流程）；**SDK 用戶端**＝測試裡用官方 `mcp` 套件寫的一個連線程式，模擬真實的 MCP 客戶端；**GuidanceError**＝`guidance.py` 在讀不到路由表時丟的錯誤；**打包副本**＝建出 wheel（安裝包）時複製進 `abf_platform/skills/` 的那份技能文字。

「前後一樣」的基準＝計畫起點 `v3`（目前的 `d92faa0` 之前，009b 合併後的行為）。

編號規則：本合約用 TC-1xx 至 TC-8xx，避免和 009b 的 TC-A10、TC-E07 等既有測試編號混淆；文中「009b 的 TC-A10」指 `test_actions_layer.py` 裡既有的那條測試。

## User Story 1 — 連線時自動讀到路由表（instructions）（優先度 P1）

維護者原話：「連線時自動讀到路由表（想跑 RNA-seq 該走哪個流程）」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-101 | 計畫·設計 2；給維護者 第 1 句 | 功能 | 讀 `skills/operational/SKILL.md` 的 `## The five commands` 表（測試自己獨立解析，不呼叫 `guidance`） | 呼叫 `guidance.routing_instructions()` | 表裡每一列（`setup`、`launch`、`runs`、`downstream`、`finish`）的指令名與「When」欄文字都出現在結果裡，共五列，一列不少 | 自動：`platform/tests/test_guidance.py` |
| TC-102 | 計畫·設計 2；ADR 0006「I want to run RNA-seq is routed」 | 功能 | 同上 | 呼叫 `guidance.routing_instructions()` | 結果含「user does not have to name a command」那一段，且其中 "I want to run RNA-seq" 對到 `launch`（同一段文字裡兩者並列） | 自動：`test_guidance.py` |
| TC-103 | 計畫·設計 2 固定句（六個工具唯讀）；修改 (i) | 功能 | 同上 | 檢查結果文字 | 含 `read-only`，並說明六個工具是唯讀 | 自動：`test_guidance.py` |
| TC-104 | 計畫·設計 2 固定句（只在終端機）；測試 (i)；給維護者 第 2 句 | 功能 | 同上 | 檢查結果文字 | 說明送出（launch）與取消（cancel）只在 `terminal`（終端機）進行 | 自動：`test_guidance.py` |
| TC-105 | 計畫·設計 2 固定句（完整流程在 MCP prompts） | 功能 | 同上 | 檢查結果文字 | 說明完整流程在 MCP prompts 裡（出現 `prompt` 字樣） | 自動：`test_guidance.py` |
| TC-106 | 計畫·設計 2（上限約 2 KB） | 功能 | 用 repo 真實的 `skills/` | 取 `routing_instructions()` 的 UTF-8 位元組數 | 不超過 2,048 位元組 | 自動：`test_guidance.py` |
| TC-107 | 計畫·設計 2（生成的，不是手抄）；測試 (a) | 功能 | 把 `skills/` 複製到暫存資料夾，改掉路由表某一列的「When」文字並另加一列 | 讓 `guidance` 讀這個暫存資料夾後取 `routing_instructions()` | 結果含改過的文字與新增的那列，不含被改掉的舊文字；證明 instructions 跟著檔案走、不是寫死在程式裡 | 自動：`test_guidance.py` |
| TC-108 | 計畫·設計 2「raises GuidanceError if the heading or table is missing」；測試 (b) | 例外 | 暫存的技能資料夾裡，`operational/SKILL.md` 沒有 `## The five commands` 標題 | 呼叫 `routing_instructions()` | 丟 `GuidanceError`（不是回空字串、不是別種錯誤） | 自動：`test_guidance.py` |
| TC-109 | 同 TC-108；測試 (b) | 例外 | 暫存資料夾裡標題還在，但標題底下的表整個被刪掉 | 呼叫 `routing_instructions()` | 丟 `GuidanceError` | 自動：`test_guidance.py` |
| TC-110 | 計畫·設計 2（`mcp_server.py` 呼叫 `guidance.routing_instructions()`） | 功能 | `build_server(...)` 建好一台伺服器 | 讀 `server.instructions` | 逐字等於 `guidance.routing_instructions()` | 自動：`test_guidance.py` |
| TC-111 | 計畫·測試 (f)；給維護者 第 1 句 | 功能 | 用 stdio 啟動伺服器，SDK 用戶端連上 | 用戶端讀連線時收到的 instructions | 等於 `guidance.routing_instructions()`，含五個流程名 | 自動：`test_guidance.py` |
| TC-112 | 計畫·測試 (f)；給維護者 第 2 句「沒有登入」 | 功能 | 用 streamable HTTP 啟動伺服器，SDK 用戶端**不帶任何憑證**連上 | 用戶端讀 instructions | 連得上，內容與 stdio 時相同 | 自動：`test_guidance.py` |

## User Story 2 — 每個流程一個 MCP prompt，放完整 SKILL.md（優先度 P1）

維護者原話：「每個流程另有一個 MCP prompt 放完整 SKILL.md。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-201 | 計畫·設計 4；測試 (c)；給維護者 第 1 句 | 功能 | `build_server(...)` 建好 | 列出伺服器上所有 prompt 名 | 正好五個：`setup`、`launch`、`runs`、`downstream`、`finish`（以名稱命名，等於 `skills/` 裡五個流程技能資料夾名），不多不少 | 自動：`test_guidance.py` |
| TC-202 | 計畫·設計 4（「not `operational`」） | 功能 | 同上 | 檢查 prompt 名單 | 沒有名為 `operational`（或 `agentic-bioflow-operational`）的 prompt | 自動：`test_guidance.py` |
| TC-203 | 計畫·設計 4（no arguments） | 功能 | 同上 | 看五個 prompt 各自宣告的參數 | 每個都沒有任何參數（沒有路徑或名稱可以傳進去） | 自動：`test_guidance.py` |
| TC-204 | 計畫·設計 4（frontmatter stripped, byte-equal；as one user message）；給維護者 第 1 句「完整 SKILL.md」 | 功能 | 測試獨立讀 `skills/<名>/SKILL.md`，以關閉 `---` 那行之後的全部位元組當期望 | 對五個 prompt 各取一次內容 | 每個都恰好一則 `user` 訊息，文字逐位元組等於該 SKILL.md 去掉 frontmatter 後的本文，不增不減 | 自動：`test_guidance.py` |
| TC-205 | 計畫·設計 4（frontmatter stripped） | 功能 | 同上 | 檢查五個 prompt 的文字 | 都不以 `---` 開頭，也不含 frontmatter 裡的 `name:` 那一行 | 自動：`test_guidance.py` |
| TC-206 | 計畫·測試 (f) | 功能 | stdio 的 SDK 用戶端 | 列出 prompts 並各取一次 | 名單與文字和直接呼叫伺服器時相同 | 自動：`test_guidance.py` |
| TC-207 | 計畫·測試 (f) | 功能 | streamable HTTP 的 SDK 用戶端，不帶憑證 | 列出 prompts 並各取一次 | 名單與文字和 stdio 時相同 | 自動：`test_guidance.py` |
| TC-208 | 計畫·Changes 4（TESTING.md 手動檢查）；ADR「how Claude Desktop shows them is not documented」 | 功能 | `docs/TESTING.md` 手動部分 | 照做：把伺服器網址加進 Claude Code 與 Claude Desktop，看五個 prompt 怎麼出現 | TESTING.md 有一段步驟，寫明在 Claude Code 看到 `/server:prompt` 形式的指令、Claude Desktop 怎麼看，以及看到什麼才算過；寫得具體到非工程師能照做 | 手動：`docs/TESTING.md`（驗收審查者確認該步驟存在且具體） |
| TC-209 | 計畫·設計 4（五個，不是六個） | 例外 | 同 TC-201 | 向伺服器取名為 `operational` 與 `nope` 的 prompt | 都被拒絕（回錯誤），不回任何技能文字 | 自動：`test_guidance.py` |

## User Story 3 — 技能也以 resources 提供，固定六個，不能帶路徑進來（優先度 P2）

計畫設計 3：SEP-2640（MCP 的 Skills 擴充）不在釘住的 SDK 裡，所以退而用一個固定 resource 對一個檔案。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-301 | 計畫·設計 3；測試 (d) | 功能 | `build_server(...)` 建好 | 列出所有 resource | 正好六個，URI 為 `skill://setup/SKILL.md`、`skill://launch/SKILL.md`、`skill://runs/SKILL.md`、`skill://downstream/SKILL.md`、`skill://finish/SKILL.md`、`skill://operational/SKILL.md`（六個資料夾各一，含 `operational`），不多不少 | 自動：`test_guidance.py` |
| TC-302 | 計畫·設計 3（mime `text/markdown`） | 功能 | 同上 | 看六個 resource 的 mime 型別 | 全是 `text/markdown` | 自動：`test_guidance.py` |
| TC-303 | 計畫·設計 3；測試 (d)（each read equals the file） | 功能 | 測試獨立讀 `skills/<名>/SKILL.md` | 讀六個 resource | 每個回傳的文字逐位元組等於對應的 SKILL.md 全檔（含 frontmatter） | 自動：`test_guidance.py` |
| TC-304 | 計畫·設計 3（no path template） | 功能 | 同上 | 列出 resource 範本（templates） | 空的：沒有任何帶變數的路徑範本，所以沒有地方可以把路徑傳進來 | 自動：`test_guidance.py` |
| TC-305 | 計畫·測試 (f) | 功能 | stdio 的 SDK 用戶端 | 列出 resources 並各讀一次 | 名單與內容和直接呼叫伺服器時相同 | 自動：`test_guidance.py` |
| TC-306 | 計畫·測試 (f) | 功能 | streamable HTTP 的 SDK 用戶端，不帶憑證 | 列出 resources 並各讀一次 | 名單與內容和 stdio 時相同 | 自動：`test_guidance.py` |
| TC-307 | 計畫·測試 (d)（unknown URIs refused） | 例外 | 同 TC-301 | 讀 `skill://nope/SKILL.md` 與 `skill://abf/SKILL.md` | 被拒絕（回錯誤），不回任何檔案內容 | 自動：`test_guidance.py` |
| TC-308 | 計畫·測試 (d)（`..` refused） | 例外 | 同 TC-301 | 讀 `skill://launch/../operational/SKILL.md`、`skill://../pyproject.toml`、`skill://launch/../../pyproject.toml` | 全部被拒絕，回傳裡沒有 `pyproject.toml` 或任何 repo 檔案的內容 | 自動：`test_guidance.py` |
| TC-309 | 計畫·設計 3（one fixed resource per file） | 例外 | 同 TC-301 | 讀 `skill://launch/OTHER.md`、`skill://launch/`（同一個技能資料夾裡別的檔名或目錄） | 被拒絕，不回任何內容 | 自動：`test_guidance.py` |

## User Story 4 — 技能文字只有一份，打包副本與 repo 相同（優先度 P1）

維護者原話：「技能文字只有一份（repo 的 `skills/`）；打包時複製進 `abf-platform`，測試保證複製品與 repo 相同。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-401 | 計畫·設計 1；設計 6 純 Python 那一半 | 功能 | repo 真實的 `skills/`，無打包副本 | 呼叫 `guidance.load_skills()` | 剛好六個鍵：`setup`、`launch`、`runs`、`downstream`、`finish`、`operational`；每個的 `name`、`description` 與該 SKILL.md frontmatter 相同（例如 `launch` 的 name 是 `launch`，`operational` 的 name 是 `agentic-bioflow-operational`）；本文等於去掉 frontmatter 後的檔案 | 自動：`test_guidance.py` |
| TC-402 | 計畫·設計 1（skills_dir 退回 repo） | 功能 | `abf_platform/skills/` 不存在（可編輯安裝與測試的情形） | 呼叫 `guidance.skills_dir()` | 回傳 repo 的 `<repo>/skills` | 自動：`test_guidance.py` |
| TC-403 | 計畫·設計 1（skills_dir 優先用打包副本） | 功能 | 在暫存的套件資料夾放一個 `abf_platform/skills/` | 呼叫 `skills_dir()` | 回傳這個打包副本，不是 repo 的 `skills/` | 自動：`test_guidance.py` |
| TC-404 | 計畫·設計 6；測試 (g)；給維護者 第 3 句 | 功能 | 離線環境有建置後端；用 `pip wheel --no-deps` 建 wheel 到暫存資料夾 | 解開 wheel，逐檔比對 `abf_platform/skills/**` 與 `<repo>/skills` | 檔案集合完全相同（不多不少，含六個資料夾的 SKILL.md），每個檔案逐位元組相同 | 自動：`test_guidance.py` |
| TC-405 | 計畫·設計 6（跳過條件） | 功能 | 沒有可離線用的建置後端 | 跑 TC-404 那條測試 | 只有這種情況可以跳過，且必須印出原因；其他情況跳過一律算不通過；若實際被跳過，驗收判「未驗證」而非通過 | 手動：驗收審查者讀測試與 ledger |
| TC-406 | 計畫·設計 5；測試 (h) | 功能 | 讀 `platform/pyproject.toml` | 檢查打包設定 | 有 `package-data = {"abf_platform" = ["skills/*/SKILL.md"]}`（等價寫法亦可，涵蓋六個資料夾的 SKILL.md） | 自動：`test_guidance.py` |
| TC-407 | 計畫·設計 5（`packages` is not extended）；測試 (h) | 功能 | 同上 | 比對 `packages` 清單，並找 `abf_platform` 底下所有 `__init__.py` | `packages` 仍是原本四項（`abf_platform`、`abf_platform.actions`、`abf_station`、`abf_launch`）；每個 `__init__.py` 的點式路徑都在清單裡，沒有漏列 | 自動：`test_guidance.py` ＋ 既有 009b 的 TC-D01 不改動全綠 |
| TC-408 | 計畫·設計 5（never committed） | 功能 | git 工作樹 | 檢查 `.gitignore` 與已追蹤檔案 | `.gitignore` 含 `platform/abf_platform/skills/`；`git ls-files platform/abf_platform/skills` 為空 | 自動：`test_guidance.py` |
| TC-409 | 給維護者 第 3 句；憲法 I.1「no hand-copied second text」 | 功能 | 讀 repo 所有被追蹤檔 | 找 `platform/` 底下的 `SKILL.md`，並在 `guidance.py`、`mcp_server.py` 與打包掛鉤檔裡找路由表的句子（例如 `pipelines → datasets → launch`、`outside Seqera's model`） | `platform/` 底下沒有被追蹤的 SKILL.md；三個 .py 檔都沒有內嵌路由表或技能文字的副本 | 自動：`test_guidance.py` |
| TC-410 | 計畫·設計 5「both new .py files carry a tc070 header」 | 功能 | 打包掛鉤檔（`pyproject.toml` 旁的新 .py）與 `guidance.py` | 對兩個檔案各跑 `test_scope.py` 的 `judge()` 規則（前 40 行要有 `# Not …:` 或 `# Nothing existing:`，理由 ≥15 字，且不被判成 IN-REPO）；`test_guidance.py` 本身也要有 | 三個檔案都通過（既有的 tc070 只掃 `abf_platform/`、`abf_station/` 與 `tests/`，**不會自動掃到掛鉤檔**，所以要有一條測試直接讀它） | 自動：`test_guidance.py` ＋ 既有 `test_scope.py` tc070 |
| TC-411 | 計畫·設計 1（Stdlib-only frontmatter parsing） | 功能 | 讀 `guidance.py`（AST） | 檢查它匯入的模組 | 只有標準函式庫與（若有）同套件模組，沒有 `yaml`、`frontmatter` 之類的第三方套件 | 自動：`test_guidance.py` |

## User Story 5 — 六個唯讀工具一個字都沒變，沒有登入，仍然只能在終端機送出（優先度 P1）

維護者原話：「這一步沒有新的寫入工具、沒有登入；六個唯讀工具一個字都沒變。」；另沿用 009b 的承諾：「送出與取消仍然只能在終端機按 y。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-501 | 給維護者 第 2 句；計畫「tc024 holds」 | 功能 | 伺服器建好（已掛上 prompts 與 resources） | 列出工具 | 正好六個：`get_compute_env`、`get_run`、`list_agents`、`list_compute_envs`、`list_runs`、`list_site_files`；每個 `read_only_hint` 為 True，`destructive_hint` 不是 True | 自動：既有 `platform/tests/test_mcp.py::test_tc024_exactly_six_read_only_tools`，不得改動斷言 |
| TC-502 | 給維護者 第 2 句「一個字都沒變」 | 功能 | 取 `v3` 起點的基準資料（009b 的 `BASELINE` 裡 tools 那一半） | 對新的 `build_server(...)` 取每個工具的名稱、說明文字、annotations、輸入 schema | 與基準逐字相同 | 自動：`test_actions_layer.py` 的 009b TC-A10（工具那一半，斷言不改動） |
| TC-503 | 給維護者 第 2 句「沒有新的寫入工具」；計畫「Prompts add no tool」 | 功能 | 一個有資料的平台（run、環境、確認、工作紀錄），記下 jobs／confirmations／launches 與索引的筆數 | 讀遍所有 instructions、五個 prompt、六個 resource | 沒寫入任何 run 狀態、沒排任何工作、沒新增任何確認紀錄；筆數不變 | 自動：`test_guidance.py` |
| TC-504 | 計畫·設計 2（import 規則加一個名字） | 功能 | 讀 `mcp_server.py` | 找它匯入的平台內部模組 | 剛好 `{actions, guidance}`，沒有別的 | 自動：`test_actions_layer.py` 的 009b TC-C01（允許集合改為 `{actions, guidance}`） |
| TC-505 | 計畫「009b's text scans」 | 功能 | 讀 `mcp_server.py` 原始碼（AST） | 找 `launch`、`cancel`、`TERMINAL`、`confirm` 的引用 | 沒有（生成的 instructions 文字在 `guidance.py` 裡，不在 `mcp_server.py`） | 自動：既有 009b 的 TC-C02，不改動全綠 |
| TC-506 | 沿用 009b 承諾「送出與取消仍然只能在終端機按 y」 | 功能 | 既有終端機送出與取消測試 | 跑 `test_launch_cli.py`、`test_launch_platform.py`（含 TC-061）、`test_launch_e2e.py`、`test_launch_followup.py` | 全綠，且這些檔案與 `v3` 相比沒有改動斷言 | 自動：既有測試 ＋ 手動：驗收審查者看 `git diff v3 -- platform/tests` |

## User Story 6 — 既有釘死斷言的改動範圍、文件、紀錄（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-601 | 計畫「Pinned assertions that legitimately change (only these)」 | 功能 | `git diff v3...HEAD -- platform/tests/` | 逐個看被改到的既有測試 | 既有測試只有三處被改：009b 的 TC-A10 的 `instructions` 比對、TC-E07、TC-C01 的允許集合；其餘既有測試函式（含 tc024、TC-D01、tc070、TC-010、TC-061、TC-C02 文字掃描）本體與 `v3` 逐字相同，沒有被刪的斷言、被放寬的比對、被加上的跳過 | 手動：驗收審查者讀 diff |
| TC-602 | 計畫·Pinned assertions TC-A10 | 功能 | 改過的 009b TC-A10 | 看它的 `instructions` 部分 | 斷言 `server.instructions == guidance.routing_instructions()`，**另外獨立**斷言文字含五個流程名、`read-only`、`terminal`；工具那一半（名稱、說明、annotations、schema）與 `v3` 相同 | 自動：`test_actions_layer.py` |
| TC-603 | 計畫·Pinned assertions TC-E07 | 功能 | 改過的 009b TC-E07 | 看它的斷言 | 斷言「正好五個流程 prompt、名稱等於流程技能資料夾名、每個文字等於其 SKILL.md 本文」，不是弱化成只看有沒有 prompt | 自動：`test_actions_layer.py` |
| TC-604 | 計畫「Nothing else is edited」 | 功能 | 既有釘死的測試 | 跑 tc024、TC-D01、tc070、TC-010、TC-061 與 009b 文字掃描 | 全綠，斷言本體與 `v3` 相同 | 自動：`cd platform && python -m pytest -q` |
| TC-605 | 計畫·Facts（`platform_direction_docs_test.sh` ~466） | 功能 | 文件與 `tests/platform_direction_docs_test.sh` | 跑該測試 | 全綠；文件「instructions and one prompt per skill mirroring `skills/`」這句現在是真的（TC-201、TC-204 成立） | 自動：`tests/platform_direction_docs_test.sh`（WSL） |
| TC-606 | 計畫·Changes 4（PLATFORM.md） | 功能 | `docs/PLATFORM.md` | 讀「Guidance over the URL」一節 | 有此節，說明 instructions、prompts、resources 各是什麼、resource 退路與為什麼要退路（釘住的 SDK 沒有 Skills 擴充 API）；字眼是「skills as resources」 | 手動：驗收審查者讀 diff |
| TC-607 | 計畫·Changes 4（TESTING.md） | 功能 | `docs/TESTING.md` | 讀手動部分 | 有 Claude Desktop 與 Claude Code 如何顯示 prompts 的檢查步驟（同 TC-208） | 手動：`docs/TESTING.md` |
| TC-608 | 計畫·Changes 4（CHANGELOG） | 功能 | `CHANGELOG.md` | 讀 3.0.0-dev 一節 | 該節新增一行說明指引經由網址送達（instructions、prompts、resources），只有一行 | 手動：驗收審查者讀 diff |
| TC-609 | 計畫·Changes 1、5（紅燈先行、ledger） | 功能 | `specs/009g-guidance-over-mcp/ledger.md` | 讀紀錄 | 有「寫完測試先跑到失敗」的紅燈證據、「做完全綠」的證據，以及被改動的既有斷言清單（與 TC-601 一致） | 手動：驗收審查者讀 ledger |
| TC-610 | 計畫·Changes 5 | 功能 | 做完全部變更 | 跑 `cd platform && python -m pytest -q`；在 WSL 跑 `bash tests/run_all.sh` | 兩者都全綠 | 自動：pytest；`tests/run_all.sh`（WSL／CI） |

## 不在範圍（計畫「Not in this PR」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-701 | 不在範圍：no write tool, no launch/cancel route | 不在範圍 | 讀 `guidance.py`、打包掛鉤檔與伺服器 | 檢查工具清單，並用 AST 找 `actions.launch`、`actions.cancel`、`TERMINAL` 的引用與對 `confirm`、`jobs`、`terminal`、`abf_launch` 的匯入；比對 HTTP 路由 | 工具仍是六個唯讀；兩個新檔案沒有這些引用；HTTP 路由集合與 `v3` 相同，沒有多出 launch／cancel／confirm 路徑 | 自動：`test_guidance.py` |
| TC-702 | 不在範圍：no confirmation page (009c) | 不在範圍 | `git diff v3...HEAD --name-only` | 找新增的網頁、範本、路由檔 | 沒有確認頁面相關檔案 | 手動：驗收審查者讀 diff |
| TC-703 | 不在範圍：no auth/identity (009d) | 不在範圍 | 讀 `guidance.py`、打包掛鉤檔與 `mcp_server.py` 的 diff | 找 `environ`、`getenv`、token、身分相關程式 | 沒有新增；不帶憑證的用戶端可以用（同 TC-112） | 自動：`test_guidance.py` |
| TC-704 | 不在範圍：no resume (009e) | 不在範圍 | `abf_platform.actions` | 列出名稱 | 沒有任何名稱含 `resume` 或 `retry` | 自動：既有 009b 的 TC-E05，不改動全綠 |
| TC-705 | 不在範圍：no dev mode (009f) | 不在範圍 | 設好 `ABF_DEV`、`ABF_PLATFORM_DEV`、`ABF_PLATFORM_YES`、`ABF_YES` 環境變數 | 取 instructions、prompts、resources，並檢查新檔案是否讀環境變數 | 內容與沒設時相同；`guidance.py` 與打包掛鉤檔不讀這些變數 | 自動：`test_guidance.py` |
| TC-706 | 不在範圍：no real SEP-2640 endpoint | 不在範圍 | 伺服器建好 | 列出 resources、範本 | 只有 TC-301 那六個固定 `skill://` resource，沒有索引檔、沒有範本，沒有第七個 | 自動：`test_guidance.py` |
| TC-707 | 不在範圍：no `mcp` pin change | 不在範圍 | `platform/pyproject.toml`、`platform/constraints.txt` | 讀依賴與釘版 | `dependencies = ["mcp>=2.3,<3"]` 與 `mcp==2.3.0` 都與 `v3` 相同 | 自動：`test_guidance.py` |
| TC-708 | 不在範圍：no harness kit | 不在範圍 | `git diff v3...HEAD --name-only` | 找安裝技能到本機的工具或安裝腳本 | 沒有新增 | 手動：驗收審查者讀 diff |
| TC-709 | 不在範圍：no change to the six tools' names, descriptions, annotations or schemas | 不在範圍 | `git diff v3...HEAD -- platform/abf_platform/mcp_server.py` | 看六個 `@server.tool(...)` 的 name、description、annotations 與函式簽名 | 這些行沒有任何變動（`mcp_server.py` 的變動只在 `instructions=`、匯入 `guidance` 與新增 prompt／resource 註冊） | 手動：驗收審查者讀 diff（資料面由 TC-502 自動把關） |
| TC-710 | 不在範圍：no hooks, constitution or `.github/` | 不在範圍 | `git diff v3...HEAD --name-only` | 找 `hooks/`、`.specify/memory/constitution.md`、`.github/` 底下的檔案 | 沒有任何一個被改 | 手動：驗收審查者讀 diff |
| TC-711 | 不在範圍：never claim SEP-2640 conformance（計畫·設計 3） | 不在範圍 | `docs/PLATFORM.md` 新一節、`CHANGELOG.md`、`docs/TESTING.md` 與程式註解的新增文字 | 找 SEP-2640 的提法 | 沒有任何一處宣稱「符合／實作／支援 SEP-2640」；只說 skills as resources，以及之後換 SDK 才換註冊方式 | 手動：驗收審查者讀 diff |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-801 | I.1：先說明為何不用現成的；唯一來源 | 功能 | 新增 `guidance.py`、打包掛鉤檔、`test_guidance.py` | 跑既有 `test_scope.py` 的 tc070 | 全綠（標頭要能通過規則，計畫那句 `# Not a second copy of the skills:…` 會被判 IN-REPO，需改寫） | 自動：既有 `test_scope.py::test_tc070_every_python_source_names_its_alternative` |
| TC-802 | I.1：`skills/` 是唯一一份指引文字 | 功能 | `git diff v3...HEAD -- skills/` | 看輸出 | 為空：這次只讀取並提供 `skills/`，沒有改它（送出的文字就是 009a 已審過的那份） | 手動：驗收審查者讀 diff |
| TC-803 | I.2：不新增送出路徑、不留第二份 run 狀態 | 功能 | 新增的 `platform/` 檔案 | 跑 `tests/no_second_run_state_test.sh` 與 `test_scope.py` 的 tc071 | 全綠：沒有新的送出程式、沒有常駐迴圈、沒有被提交的資料庫 | 自動：`tests/no_second_run_state_test.sh`（WSL）；`test_scope.py` tc071 |
| TC-804 | 安全網：送出須經使用者確認；`hooks/` 不動 | 功能 | hooks 沒被改 | 跑 `tests/confirm_launch_test.sh` | 全綠，沒有任何放寬 | 自動：`tests/confirm_launch_test.sh`（WSL） |
| TC-805 | II.3：不寫死路徑 | 功能 | 新增的 `guidance.py` 與打包掛鉤檔 | 看路徑來源，並跑 `tests/no_hardcoded_paths.sh` | `skills/` 的位置由檔案自身位置（`__file__`）推導，沒有個人路徑或叢集路徑；檢查全綠 | 自動：`tests/no_hardcoded_paths.sh`（WSL）＋ `test_guidance.py` |
