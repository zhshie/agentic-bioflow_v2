# 測試案例：harness-kits（給 Claude Code 與 Codex 的「複製就能用」平台連線設定檔，issue #93 第 7 項的程式部分）

**規格**：`specs/harness-kits/plan.md`（此功能沒有 spec.md，計畫即依據；維護者指示：測試案例只能來自計畫裡寫的事，不替它發明預期行為）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

說明：這次只交付兩個設定檔（套件，kit）、改一份文件（`docs/INSTALL.md`）、加一支測試（`tests/harness_kits_test.sh`），沒有 User Story。下面依計畫的「Files to add」「docs/INSTALL.md changes」「Test」「Out of scope」分區。TC-001 到 TC-007 沿用計畫「Test」段自己的編號與內容，TC-008 起是把計畫其餘句子逐條對應出來的案例。

名詞：「PAT」是個人存取權杖（等同密碼的一長串字，由管理平台的人用 `abf-platform pat new` 發出，只顯示一次）；「MCP」是 AI 程式和平台講話的規格；「環境變數」是在你自己的終端機設定的名字加值（例如 `ABF_PAT`），設定檔裡只寫名字、不寫值；「套件」（kit）指放在倉庫裡、讓使用者複製去用的設定檔；「倉庫根目錄」就是 `C:/Users/marvi/Desktop/agentic-bioflow/wt/harness-kits` 這一層（正式倉庫的最上層）。

契約階段查過的事實（驗收者要重查）：
- 倉庫根目錄現在沒有 `.mcp.json`、`plugin.json`、`mcp.json`；`.claude-plugin/marketplace.json` 的 `source` 是 `"."`，所以倉庫根目錄就是 Claude Code 外掛的根目錄（計畫不放根目錄 `.mcp.json` 的理由）。
- `extensions/claude-code-kit/` 現在只有 `settings.json`；`extensions/codex-kit/` 不存在。
- `docs/INSTALL.md` 現況：第 4 節是「Not built yet」，第 6 節有三條「尚未做好」的項目，六個 `## ` 標題順序為 What you need、Claude Code、Claude Desktop、Codex、Check it works、Not built yet。
- 既有的 `tests/install_doc_test.sh` 會檢查：反引號裡長得像 MCP 工具名（小寫字加底線，如 `a_b`）的字必須是 `mcp_server.py` 裡的工具；反引號裡帶斜線且有副檔名的路徑必須存在於倉庫。實作者寫新文件時要避開這兩個陷阱（見 TC-016）。
- Claude Code 官方文件（code.claude.com/docs/en/mcp）說明：`.mcp.json` 的 `url` 與 `headers` 可用 `${VAR}`；變數沒設又沒預設值時，設定仍會載入，Claude Code 會顯示缺變數警告，並把 `${VAR}` 原文照送。這與計畫「`ABF_PAT` 沒設就送出原文、平台回 401」一致。

## 區 A — 兩個套件檔本身（計畫「Files to add」與「Test」1–3、7）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 Test TC-001；Files to add 1 | 功能 | 實作完成 | 跑 `bash tests/harness_kits_test.sh`，它讀 `extensions/claude-code-kit/mcp.json` | 該檔是合法 JSON；裡面有名為 `abf-platform` 的伺服器，`type` 等於 `http`；`url` 含 `${ABF_PLATFORM_URL}` 且以 `/mcp` 結尾；`headers.Authorization` 逐字等於 `Bearer ${ABF_PAT}`。任一項不符就失敗並說是哪一項 | 自動：`tests/harness_kits_test.sh` |
| TC-002 | 計畫 Test TC-002；Files to add 2 | 功能 | 實作完成 | 同一支測試讀 `extensions/codex-kit/config.toml` | 檔裡有 `[mcp_servers.abf-platform]` 區段；`url` 以 `/mcp` 結尾；有一行 `bearer_token_env_var = "ABF_PAT"`；沒有任何以 `bearer_token =` 開頭的行（那會是把權杖值直接寫進檔案）；沒有寫死內容的 `http_headers`。任一項不符就失敗並說是哪一項 | 自動：`tests/harness_kits_test.sh` |
| TC-003 | 計畫 Test TC-003（權杖永遠來自環境變數，不寫死） | 例外 | 兩個套件檔都在 | 同一支測試掃兩個套件檔 | 兩檔都沒有符合 `abf_pat_[A-Za-z0-9]{8,}` 的字串（沒有真權杖）；兩檔裡的網址主機要嘛是 `${ABF_PLATFORM_URL}`、要嘛以 `.example` 結尾（沒有真實主機）。有任何真權杖或真主機就失敗並點名是哪個檔 | 自動：`tests/harness_kits_test.sh` |
| TC-007 | 計畫 Test TC-007（防止檢查形同虛設） | 例外 | 測試腳本支援用環境變數 `KIT_DIR`、`INSTALL_DOC`、`ROOT_DIR` 指向別處 | 測試自己在暫存位置做一份「動過手腳的副本」：套件檔裡放一個 `abf_pat_abcdefgh12`，並在副本的根目錄放一個 `.mcp.json`；用上述環境變數指向副本，再跑同一組檢查 | 對副本跑時檢查會失敗（至少 TC-003 與 TC-004 那兩類檢查各自抓到），而對真倉庫跑是通過的；若副本也能通過，表示這支測試擋不住壞檔，整支測試無效。暫存副本用完清掉，不改倉庫裡任何檔案 | 自動：`tests/harness_kits_test.sh` |
| TC-008 | 計畫 Files to add 1（檔名 `mcp.json`、「no leading dot」） | 功能 | 實作完成 | 列出 `extensions/claude-code-kit/` | 套件檔名是 `mcp.json`（沒有開頭的點）；該資料夾裡沒有 `.mcp.json`；`extensions/codex-kit/config.toml` 存在 | 自動：`tests/harness_kits_test.sh` |
| TC-009 | 計畫 Files to add 2（檔頭註解告訴使用者怎麼用） | 功能 | 實作完成 | 讀 `extensions/codex-kit/config.toml` 開頭 | 開頭有一行以 `#` 開頭的註解，白話說明三件事：把這段附加到 `~/.codex/config.toml`、把網址換成自己平台的、在自己的終端機 `export ABF_PAT`（與計畫給的註解一致）；註解裡沒有任何權杖值 | 手動：驗收者讀該檔 |

## 區 B — `docs/INSTALL.md`（計畫「docs/INSTALL.md changes」與「Test」5、6）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-005 | 計畫 Test TC-005；INSTALL 第 4 節（Codex） | 功能 | 實作完成 | 測試取出 `docs/INSTALL.md` 中 `## 4.` 到 `## 5.` 之間的文字 | 這段不再含「Not built yet」；有寫出 `extensions/codex-kit/config.toml`；有寫出 `bearer_token_env_var`。三項缺任何一項就失敗並說缺哪項 | 自動：`tests/harness_kits_test.sh` |
| TC-006 | 計畫 Test TC-006；INSTALL 第 2、6 節 | 功能 | 實作完成 | 測試讀整份 `docs/INSTALL.md` 與其中 `## 6.` 以後的文字 | 全文有寫出 `extensions/claude-code-kit/mcp.json`；第 6 節（`## 6.` 之後到檔尾）不再列出「Codex 套件」，也不再列出「Claude Desktop 連接器套件」。任一項不符就失敗並說是哪一項 | 自動：`tests/harness_kits_test.sh` |
| TC-010 | 計畫 INSTALL 第 2 節（「keep the `claude mcp add` line」） | 功能 | 實作完成 | 讀第 2 節 | 原本那條指令一字不差還在：`claude mcp add --transport http abf-platform <platform-URL>/mcp --header "Authorization: Bearer <PAT>"`；測試以整行比對 | 自動：`tests/harness_kits_test.sh` |
| TC-011 | 計畫 INSTALL 第 2 節（新增的替代做法） | 功能 | 實作完成 | 讀第 2 節 | 除了上面那條指令，另有「替代做法」：把 `extensions/claude-code-kit/mcp.json` 複製成使用者自己專案資料夾裡的 `.mcp.json`（明說是自己的專案資料夾、不是本倉庫）；在自己的終端機設定 `ABF_PLATFORM_URL` 與 `ABF_PAT`；說明 Claude Code 第一次會問你是否核准這個專案伺服器。測試自動確認第 2 節同時出現 `.mcp.json`、`ABF_PLATFORM_URL`、`ABF_PAT`；其餘文字由人讀 | 自動（三個名字都出現）：`tests/harness_kits_test.sh`；其餘手動：驗收者讀第 2 節 |
| TC-012 | 計畫 INSTALL 第 2 節（「Say plainly」） | 例外 | 實作完成；使用者忘了設 `ABF_PAT` | 讀第 2 節 | 文件白話寫明：若 `ABF_PAT` 沒有設，Claude Code 會把字面文字（`${ABF_PAT}` 原樣）送出，平台會回 401（拒絕）。測試自動確認第 2 節出現 `401` 與 `ABF_PAT`；「送出字面文字」的說法由人讀 | 自動（`401` 與 `ABF_PAT` 出現）：`tests/harness_kits_test.sh`；其餘手動：驗收者讀第 2 節 |
| TC-013 | 計畫 INSTALL 第 4 節（真的步驟） | 功能 | 實作完成 | 讀第 4 節 | 有三步：把 `extensions/codex-kit/config.toml` 附加到 `~/.codex/config.toml`；把檔裡的網址換成自己平台的；在自己的終端機執行 `export ABF_PAT=<PAT>`，並明說不要把它寫進交給 git 管的檔案。測試自動確認第 4 節出現 `~/.codex/config.toml` 與 `export ABF_PAT=`；「不寫進 git 管的檔案」的說法由人讀 | 自動（兩個字串出現）：`tests/harness_kits_test.sh`；其餘手動：驗收者讀第 4 節 |
| TC-014 | 計畫 INSTALL 第 3 節（Claude Desktop） | 功能 | 實作完成 | 拿 `docs/INSTALL.md` 第 3 節與 `main` 上的同一節比對 | 第 3 節只多了一句話，意思是「沒有檔案要安裝；連接器是在 App 裡加的」；其餘原有句子與步驟一字未動 | 手動：驗收者以 `git diff main...HEAD -- docs/INSTALL.md` 比對該節 |
| TC-015 | 計畫 INSTALL 第 6 節與「keep all six `## ` headings and their order」 | 功能 | 實作完成 | 讀第 6 節與全部 `## ` 標題 | 第 6 節標題仍在、六個標題順序不變；三條舊的套件項目（根目錄 `.mcp.json` 會「零指令加平台」、Codex 套件、Claude Desktop 連接器套件）都移除，換成剛好一條：根目錄 `.mcp.json` 是刻意不提供，因為倉庫根目錄就是外掛根目錄，每個安裝外掛的人都會載入它。測試自動確認：六個標題與順序（沿用 `install_doc_test.sh` 的檢查）、第 6 節剛好一條項目且含 `.mcp.json`；理由的措辭由人讀 | 自動（標題、條數、`.mcp.json`）：`tests/harness_kits_test.sh` 與 `tests/install_doc_test.sh`；其餘手動：驗收者讀第 6 節 |
| TC-016 | 計畫 INSTALL 段（「`tests/install_doc_test.sh` must stay green」）與新增測試檔 | 功能 | 實作完成 | 分別跑 `bash tests/install_doc_test.sh`、`bash tests/run_all_count_test.sh`、`bash tests/harness_kits_test.sh` | 三支都通過（`install_doc_test.sh` 每項 `ok`、最後 `all ok`、結束碼 0；`run_all_count_test.sh` 印 `ok`，表示新測試檔有被 `run_all.sh --list` 列出；`harness_kits_test.sh` 全部 `ok`、結束碼 0）。測試以結束碼判定，不得為了通過而改寫或放寬 `tests/install_doc_test.sh` | 自動：`tests/install_doc_test.sh`、`tests/run_all_count_test.sh`、`tests/harness_kits_test.sh` |

## 區 C — 不在範圍（計畫「Design decision」與「Out of scope」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-004 | 計畫 Test TC-004；Design decision（不建根目錄檔案） | 不在範圍 | 實作完成 | 測試檢查倉庫根目錄 | 根目錄沒有 `.mcp.json`、沒有 `plugin.json`、沒有 `mcp.json`（三個都要檢查；有任何一個就失敗並點名）。理由：倉庫根目錄就是外掛根目錄，放了會讓每個安裝外掛的人都載入一個佔位伺服器 | 自動：`tests/harness_kits_test.sh` |
| TC-017 | 計畫 Files to add 末句；Out of scope（不碰 `extensions/claude-code-kit/settings.json`，PR #133 正在改它） | 不在範圍 | 實作完成 | 列出本次相對 `main` 的改動檔案：`git diff --name-only main...HEAD`，並看有無未提交改動 | `extensions/claude-code-kit/settings.json` 不在清單裡（沒被改） | 手動：驗收者執行該指令核對 |
| TC-018 | 計畫 Out of scope（不碰 `.claude-plugin/*`、不升版號） | 不在範圍 | 實作完成 | 同上列出改動檔案 | `.claude-plugin/` 底下沒有任何檔案被改（含 `plugin.json`、`marketplace.json`，所以版號也沒動） | 手動：驗收者執行該指令核對 |
| TC-019 | 計畫 Out of scope（不改 `CHANGELOG.md`） | 不在範圍 | 實作完成 | 同上列出改動檔案 | `CHANGELOG.md` 不在清單裡 | 手動：驗收者執行該指令核對 |
| TC-020 | 計畫 Out of scope（不改平台程式） | 不在範圍 | 實作完成 | 同上列出改動檔案 | `platform/` 底下沒有任何檔案被改 | 手動：驗收者執行該指令核對 |
| TC-021 | 計畫 Out of scope（不改 `docs/PLATFORM.md`） | 不在範圍 | 實作完成 | 同上列出改動檔案 | `docs/PLATFORM.md` 不在清單裡 | 手動：驗收者執行該指令核對 |
| TC-022 | 計畫 Design decision（Claude Desktop 沒有檔案可附，連接器在 App 裡加） | 不在範圍 | 實作完成 | 同上列出改動檔案，找 Claude Desktop 相關的新檔 | 沒有新增任何 Claude Desktop 專用的設定檔或套件；本次新增的檔案只有 `extensions/claude-code-kit/mcp.json`、`extensions/codex-kit/config.toml`、`tests/harness_kits_test.sh`，以及 `specs/harness-kits/` 底下的文件；`docs/INSTALL.md` 為修改 | 手動：驗收者執行該指令核對 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 安全網「憑證只放在部署自己的設定區，絕不進 git」（`tests/credentials_stay_in_settings_test.sh` 是既有的保護，本次新增檔案也要守住） | 例外 | 實作完成 | 掃兩個套件檔與 `docs/INSTALL.md` 有沒有 PAT 形狀的字串 | 兩個套件檔與 `docs/INSTALL.md` 都沒有符合 `abf_pat_[A-Za-z0-9]{8,}` 的字串；套件檔裡權杖只以 `${ABF_PAT}`（Claude Code）或環境變數名 `ABF_PAT`（Codex）出現 | 自動：`tests/harness_kits_test.sh`（TC-003）與 `tests/install_doc_test.sh`（其 TC-009） |
| TC-024 | 憲法第 2 條「人的確認不能被權杖或規則取代」（INSTALL 第 2 節既有段落：PAT、`ask` 規則、登入點擊都不是確認，真正的關卡是使用者自己按送出） | 例外 | 實作完成 | 拿第 2 節與 `main` 上的第 2 節比對 | 第 2 節相對 `main` 只有新增文字，原本關於 `ask` 規則「是第二層、不是關卡」「平台在使用者自己按 送出 前拒絕 launch／cancel」的段落一字未刪、意思未被新增的「替代做法」文字改變（新文字沒有說用 `.mcp.json` 就可以省掉確認） | 手動：驗收者以 `git diff main...HEAD -- docs/INSTALL.md` 比對該節 |
