# 測試案例：docs/INSTALL.md（實驗室成員把 Claude Code、Claude Desktop、Codex 接上 abf 平台的說明文件，issue #93 第 7 項的文件部分）

**規格**：`specs/install-doc/plan.md`（此功能沒有 spec.md，計畫即依據；維護者指示：測試案例只能來自計畫裡寫的事，不替它發明預期行為）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

說明：這次只交付一份文件加一支文件測試，沒有 User Story。下面依計畫的「Test」「Content」「Out of scope」分區。名詞：「PAT」是個人存取權杖（等同密碼的一長串字，由管理平台的人用 `abf-platform pat new` 發出，只顯示一次）；「MCP」是 AI 程式和平台講話的規格；「子指令」指 `abf-platform` 後面接的字（例如 `pat new`）；「套件」（kit）指放在倉庫裡、讓某個 AI 程式一鍵接上的設定檔。

契約階段查過的事實（驗收者要重查）：倉庫根目錄沒有 `.mcp.json`；倉庫裡沒有任何 Codex 專用檔案；沒有 Claude Desktop 連接器的檔案；但 `extensions/claude-code-kit/settings.json` 存在，內含 `launch`、`cancel`、`resume`、`relaunch` 四個工具的 `ask` 權限規則（`docs/PLATFORM.md` 第 398 行也這樣寫）。所以依計畫第 2 點的條件句，`ask` 規則屬於「已經有」，要寫在 Claude Code 一節，不能列進 Not built yet。

## 區 A — 文件測試本身（計畫「Test (write first)」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 Test（`tests/install_doc_test.sh`，仿 `tests/migration_doc_test.sh`） | 功能 | 實作完成 | 跑 `bash tests/install_doc_test.sh` | `docs/INSTALL.md` 存在才往下檢查；檔案不存在時測試失敗並說明檔案不在，且不會假裝通過 | 自動：`tests/install_doc_test.sh` |
| TC-002 | 計畫 Test 第 1 點；Content 1–6 | 功能 | `docs/INSTALL.md` 存在 | 跑同一支測試 | 文件有剛好六個 `## ` 標題，順序為：What you need、Claude Code、Claude Desktop、Codex、Check it works、Not built yet（標題可帶編號，比對看開頭文字）；少一個、多一個或順序錯就失敗 | 自動：`tests/install_doc_test.sh` |
| TC-003 | 計畫 Test 第 2 點 | 功能 | 文件裡寫了 `abf-platform <子指令>` | 跑同一支測試 | 文件中出現的每一個 `abf-platform` 子指令（遇到 `pat`、`user`、`oauth` 這種指令群組時連第二個字一起）都存在於 `platform/abf_platform/cli.py`；不存在的會被點名並失敗；文件完全沒寫任何 `abf-platform` 指令也算失敗 | 自動：`tests/install_doc_test.sh` |
| TC-004 | 計畫 Test 第 2 點（防止捏造指令） | 例外 | 在暫存副本加一行 `abf-platform frobnicate`（cli.py 沒有） | 對這份副本跑檢查 | 檢查失敗並點名 `frobnicate`；若通過，表示這個檢查擋不住捏造的指令，整支測試無效 | 手動：驗收者在暫存副本上執行，不改倉庫檔案 |
| TC-005 | 計畫 Test 第 3 點 | 功能 | 文件用反引號寫了 MCP 工具名（至少 `list_runs`） | 跑同一支測試 | 文件反引號裡當作 MCP 工具名的每一個名字，都在 `platform/abf_platform/mcp_server.py` 以工具形式存在（例如 `list_runs`、`get_run`、`launch`、`cancel`、`resume`、`relaunch`）；不存在的會被點名並失敗 | 自動：`tests/install_doc_test.sh` |
| TC-006 | 計畫 Test 第 3 點（防止捏造工具） | 例外 | 在暫存副本加反引號的 `list_runz`（mcp_server.py 沒有這個工具） | 對這份副本跑檢查 | 檢查失敗並點名 `list_runz`；若通過，表示這個檢查擋不住捏造的工具 | 手動：驗收者在暫存副本上執行，不改倉庫檔案 |
| TC-007 | 計畫 Test 第 4 點 | 功能 | 文件用反引號寫了倉庫路徑（例如 `extensions/claude-code-kit/settings.json`） | 跑同一支測試 | 每一個看起來像檔案的反引號倉庫路徑，在倉庫裡都真的存在；不存在的會被點名並失敗 | 自動：`tests/install_doc_test.sh` |
| TC-008 | 計畫 Test 第 4 點（防止捏造路徑） | 例外 | 在暫存副本加反引號的 `extensions/codex-kit/mcp.json`（倉庫裡沒有） | 對這份副本跑檢查 | 檢查失敗並點名該路徑；若通過，表示擋不住捏造的檔案 | 手動：驗收者在暫存副本上執行，不改倉庫檔案 |
| TC-009 | 計畫 Test 第 5 點 | 功能 | 文件存在 | 跑同一支測試 | 文件裡沒有任何符合 `abf_pat_[A-Za-z0-9]{8,}` 的字串；有就失敗 | 自動：`tests/install_doc_test.sh` |
| TC-010 | 計畫 Test 第 5 點（防止真權杖外洩） | 例外 | 在暫存副本加一個 `abf_pat_abcdefgh12345678` | 對這份副本跑檢查 | 檢查失敗；若通過，表示這個檢查擋不住真權杖，整支測試無效 | 手動：驗收者在暫存副本上執行，不改倉庫檔案 |
| TC-011 | 計畫 Test（新增測試檔不能弄壞既有的計數檢查） | 功能 | 實作完成 | 跑 `bash tests/run_all_count_test.sh`，並直接跑 `bash tests/install_doc_test.sh` | `run_all_count_test.sh` 仍印 `ok`（新測試檔有被 `run_all.sh --list` 列出）；`install_doc_test.sh` 單獨執行時每項印 `ok`、最後 `all ok` 且結束碼 0 | 自動：`tests/run_all_count_test.sh` 與 `tests/install_doc_test.sh` |

## 區 B — 文件內容（計畫「Content」1–6）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | Content 1（平台網址由管理者給） | 功能 | 文件存在 | 讀「What you need」 | 寫明使用者需要「平台的網址」，而且這個網址是向管理平台的人（operator）要的；文中的網址用佔位寫法（如 `<platform-URL>`），不寫死某個實際網址 | 手動：驗收者讀該節 |
| TC-013 | Content 1（怎麼驗證身分：Desktop 走 OAuth 登入；其他走 PAT，由管理者執行 `abf-platform pat new`） | 功能 | 文件存在 | 讀「What you need」 | 寫明兩種方式：Claude Desktop 的連接器用 OAuth 登入（瀏覽器登入，不貼權杖）；Claude Code 與其他用戶端用 PAT，PAT 由管理者用 `abf-platform pat new` 發出；文件有出現 `abf-platform pat new` 這串字，且該指令在 `cli.py` 存在（見 TC-003）。內容與 `platform/abf_platform/oauth.py`、`http_auth.py`、`docs/PLATFORM.md`、`docs/MIGRATION.md`、`docs/OPERATIONS.md` 一致，沒有這些來源以外的流程 | 自動（出現 `abf-platform pat new`）：`tests/install_doc_test.sh`；其餘手動：驗收者對照五份來源 |
| TC-014 | Content 2（Claude Code：`claude mcp add` 加 HTTP 網址與 PAT header，照 MIGRATION／PLATFORM 現有寫法） | 功能 | 文件存在 | 讀「Claude Code」 | 有一條 `claude mcp add --transport http abf-platform <platform-URL>/mcp --header "Authorization: Bearer <PAT>"`，與 `docs/MIGRATION.md` 第 38 行、`docs/PLATFORM.md` 第 107 行的寫法一致（網址與 PAT 都是佔位）；沒有另造的旗標或選項 | 手動：驗收者逐字對照兩份來源 |
| TC-015 | Content 2（`ask` 權限規則「只有倉庫真的有才寫」；契約階段查得 `extensions/claude-code-kit/settings.json` 有） | 功能 | 文件存在；`extensions/claude-code-kit/settings.json` 存在 | 讀「Claude Code」 | 寫出這份套件檔 `extensions/claude-code-kit/settings.json`，說它對 `launch`、`cancel`、`resume`、`relaunch` 四個工具設了「先問」規則（與該檔內容一致），並說明它只是第二層、不是真正的關卡（與 `docs/PLATFORM.md` 第 398 行一致）；不說它是唯一保護，也不說沒裝它就會讓 AI 自行送出 | 手動：驗收者對照 `extensions/claude-code-kit/settings.json` 與 PLATFORM.md |
| TC-016 | Content 2 與 Content 6 的一致性 | 例外 | 文件存在 | 讀「Not built yet」 | `ask` 規則沒有被列為「尚未做好」（它已存在）；也沒有把 `extensions/claude-code-kit/settings.json` 說成不存在 | 手動：驗收者讀該節 |
| TC-017 | Content 3（Claude Desktop：加自訂連接器、填網址、OAuth 登入） | 功能 | 文件存在 | 讀「Claude Desktop」 | 寫明在 Claude Desktop 新增自訂連接器（custom connector），只填 MCP 網址（`<platform-URL>/mcp` 形式），不貼 PAT、不裝別的東西；登入走 OAuth | 手動：驗收者讀該節並對照 `docs/PLATFORM.md`「Claude Desktop's custom connector」段 |
| TC-018 | Content 3（「what the person sees on first use」） | 功能 | 文件存在 | 讀「Claude Desktop」 | 描述第一次使用時看到的畫面順序，且每一步都能在 `docs/PLATFORM.md` 該段或 `platform/abf_platform/oauth.py` 找到依據：瀏覽器打開登入頁，用「名字加網頁密碼」登入（網頁密碼由管理者用 `abf-platform user passwd <name>` 設定，PAT 不能用來登入）；看到同意頁，顯示連接器名稱、會回到的主機、它能做什麼；按允許（Allow）或拒絕（Deny）；同意不會被記住，每次都再問。沒有依據的畫面描述算失敗 | 手動：驗收者逐句對照 PLATFORM.md 與 oauth.py |
| TC-019 | Content 3 + 「use only what exists」（PLATFORM.md 與 TESTING.md 寫明 Desktop 需要公開的 https 網址，端對端尚未實測） | 例外 | 文件存在 | 讀「Claude Desktop」 | 如實說明：Claude Desktop 從雲端連線，所以平台需要一個公開的 https 網址（由管理者以 `--public-url` 啟動）；不宣稱這條路已經在真實 Claude Desktop 上測過；若文件說「已測試通過」，必須能指到記錄，否則失敗 | 手動：驗收者對照 `docs/PLATFORM.md`（Claude Desktop 段末）與 `docs/TESTING.md` 第 325 行 |
| TC-020 | Content 4（Codex：倉庫沒有支援就只寫一段「Not built yet」指引） | 功能 | 文件存在；契約階段查得倉庫沒有任何 Codex 專用檔案（只有 ADR 提到 Codex 是第一批要支援的用戶端） | 讀「Codex」 | 這一節只有一段（一個段落）話，明說 Codex 的接法目前還沒做好（Not built yet），指向「Not built yet」一節；沒有寫任何 Codex 指令、設定檔內容或步驟（例如 `codex mcp add ...`），因為倉庫裡沒有依據。若撰寫時發現倉庫確有 Codex 檔案，這一節才可改寫成該檔案真有的內容 | 手動：驗收者重跑 `grep -ril codex` 查倉庫並對照該節 |
| TC-021 | Content 5（一次唯讀的工具呼叫，例如 `list_runs`） | 功能 | 文件存在 | 讀「Check it works」 | 教使用者在接好之後請 AI 呼叫 `list_runs`（例如問「我的 run 狀態是什麼？」）；說明這是唯讀、不會啟動任何東西；`list_runs` 是 `mcp_server.py` 真有的工具（見 TC-005） | 手動：驗收者讀該節 |
| TC-022 | Content 5（「what a correct empty answer looks like」） | 功能 | 文件存在；契約階段查得 `platform/abf_platform/actions/__init__.py:72-76`：經 HTTP 以使用者身分呼叫時，`list_runs` 只回該使用者自己經 MCP 發起的 run，沒有時回 `{"runs": []}` | 讀「Check it works」 | 明說「一個空的 run 清單（沒有任何 run）是正確的答案」，形狀與 `{"runs": []}` 相符（或等價的白話：runs 是空的），並說明剛接上、還沒發起過 run 的人看到空清單是正常的；不把空清單說成連線失敗。另外有告訴使用者連不上時會看到什麼（未授權 401 之類）時，必須是 PLATFORM.md 真有的行為 | 手動：驗收者對照 `actions/__init__.py` 與 `status.py:74-79` |
| TC-023 | Content 6（Not built yet：套件檔尚未存在） | 功能 | 文件存在；契約階段查得根目錄 `.mcp.json`、Codex 的 plugin.json／mcp.json、Claude Desktop 連接器套件都不在倉庫裡 | 讀「Not built yet」，並在倉庫搜尋這些檔案 | 列出：根目錄 `.mcp.json`、Codex 套件（root plugin.json／mcp.json）、Claude Desktop 連接器套件為尚未做好；列出的每一項在倉庫裡確實不存在；若驗收時發現其中一項其實已存在，那一項不能列在這裡 | 手動：驗收者讀該節並用 `ls`／`grep` 核對 |
| TC-024 | Content 6（不把已有的說成沒有、沒有的說成有） | 例外 | 文件存在 | 通讀全文，對照倉庫 | 全文沒有說某個倉庫裡不存在的檔案、指令或功能「已經可用」；「Not built yet」也沒列倉庫裡已存在的東西（`ask` 規則見 TC-016） | 手動：驗收者通讀並抽查每個名詞 |

## 區 C — 不在範圍（計畫「Out of scope」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 計畫「No code」 | 不在範圍 | 實作完成 | `git diff main...HEAD --stat` | 只新增 `docs/INSTALL.md`、`tests/install_doc_test.sh` 與 `specs/install-doc/` 底下的檔案；沒有改動 `scripts/`、`platform/`、`hooks/`、`skills/`、`extensions/` 等程式或設定 | 手動：驗收者看 diff |
| TC-026 | 計畫「no kit files」 | 不在範圍 | 實作完成 | `git diff main...HEAD --stat`，並找根目錄 `.mcp.json`、Codex plugin.json／mcp.json、Claude Desktop 連接器檔 | 這些套件檔一個都沒有被建立 | 手動：驗收者看 diff 與檔案清單 |
| TC-027 | 計畫「do not edit CHANGELOG.md」 | 不在範圍 | 實作完成 | `git diff main...HEAD -- CHANGELOG.md` | 無任何差異 | 手動：驗收者看 diff |
| TC-028 | 計畫「do not edit docs/PLATFORM.md」 | 不在範圍 | 實作完成 | `git diff main...HEAD -- docs/PLATFORM.md` | 無任何差異 | 手動：驗收者看 diff |
| TC-029 | 計畫「do not edit docs/MIGRATION.md」 | 不在範圍 | 實作完成 | `git diff main...HEAD -- docs/MIGRATION.md` | 無任何差異 | 手動：驗收者看 diff |
| TC-030 | 計畫「do not edit docs/TESTING.md」 | 不在範圍 | 實作完成 | `git diff main...HEAD -- docs/TESTING.md` | 無任何差異 | 手動：驗收者看 diff |
| TC-031 | 計畫「do not edit README」 | 不在範圍 | 實作完成 | `git diff main...HEAD -- README.md` | 無任何差異 | 手動：驗收者看 diff |

## 憲法與安全網

這份文件會教人處理 PAT 與登入，所以碰到 Safety Net 的憑證規則（憑證不進 git、不被印出）、第 I 條第 2 項（確認通道只有三個，權杖與同意點擊都不是確認）、第 II 條第 3 項（沒有個人路徑或寫死的位置）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | Safety Net 憑證規則；第 I 條第 2 項（權杖要放在 AI 讀不到之處） | 例外 | 文件存在 | 讀文件中所有談到 PAT 的地方 | 明說 PAT 只顯示一次、遺失要請管理者重發（與 `docs/MIGRATION.md` 一致）；叫使用者在自己的終端機輸入含 PAT 的指令；沒有叫使用者把 PAT 貼進與 AI 的對話、寫進會進 git 的檔案或 params 檔 | 手動：驗收者讀文件 |
| TC-033 | Safety Net 憑證規則（不印出） | 例外 | 文件存在 | 在 `docs/INSTALL.md` 搜尋 `abf_pat_` 與任何長字串 | 只出現佔位寫法（如 `<PAT>`、`abf_pat_...`），沒有任何看起來像真權杖的字串（對應 TC-009 的自動檢查，這條再人工複核整份文件，含範例輸出） | 手動：驗收者搜尋文件 |
| TC-034 | 第 I 條第 2 項（人的確認通道：終端機、用戶端表單、確認頁；權杖、待決請求、模型自己的答覆都不是） | 例外 | 文件存在 | 讀文件中提到 `launch`、`cancel`、`resume`、`relaunch` 或登入／同意的地方 | 文件若提到這些，必須說明發出或取消仍需要使用者本人按「送出」（在用戶端表單或確認頁）；不能把 OAuth 同意點擊、PAT、或 `ask` 規則說成就是確認；沒提到這些則本條視為通過 | 手動：驗收者對照 `docs/PLATFORM.md`「The honest boundary」兩段 |
| TC-035 | 第 II 條第 3 項（沒有個人路徑、寫死位置）；Content 1（網址由管理者給） | 例外 | 文件存在 | 搜尋文件中的路徑與網址 | 沒有個人電腦路徑（如 `C:\Users\...`、`/home/<人名>/`）、沒有某個真實實驗室或叢集的主機名；網址與使用者名稱都是佔位 | 手動：驗收者搜尋文件 |
