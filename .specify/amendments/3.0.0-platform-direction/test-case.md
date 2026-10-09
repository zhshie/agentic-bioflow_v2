# 測試案例：平台方向記錄（憲法 3.0.0 修訂）

**計畫**：`.specify/amendments/3.0.0-platform-direction/plan.md`（含 2026-10-09 修訂段）　**總覽**：`test-case-overview.md`

類型只有三種：功能（計畫說要改的，改了）、例外（不該變的，沒變）、不在範圍（這次不做的，真的沒做）。
本修訂只改文件，不改 hook／腳本／指令／skill。「自動」的測試檔：
`tests/constitution_scope_test.sh`（現有，更新）、`tests/constitution_checks_exist_test.sh`（現有）、
`tests/platform_direction_docs_test.sh`（新增，固定字串與段落斷言）。「手動」是驗收者讀 `git diff main...HEAD` 與文件一致性閱讀，依計畫由驗收者閱讀判定，不另加 `docs/TESTING.md` 步驟。

2026-10-09 修訂（他審查 PR #72 後）改動的案例：TC-012、TC-013、TC-022、TC-026、TC-032、TC-035、TC-057，並新增 TC-060；另配合聊天介面微調 TC-011、016、028、029、030、052、053、058。其餘案例逐字不變。

## US1 — 憲法 2.1.0 → 3.0.0（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 5 版本 | 功能 | 修訂完成 | 讀憲法最後一行 | 恰為 `**Version**: 3.0.0 \| **Ratified**: 2026-09-28 \| **Last Amended**: 2026-10-08` | 自動：`tests/constitution_scope_test.sh` |
| TC-002 | 計畫 5 修訂紀錄 | 功能 | 同上 | 讀 Amendments 區 | 有 `### 3.0.0 (2026-10-08)`，含理由（引用他的決定、ADR 0004/0005）、對現有部署的影響（含 `existing deployments`，寫明「無」）、版本 MAJOR、核准者為 maintainer；2.0.0／2.0.1／2.1.0 三則仍在 | 自動：`tests/constitution_scope_test.sh` |
| TC-003 | 計畫 5 I.1 | 功能 | 同上 | 讀 I 的標題與第 1 條 | 標題為「Build Only What Seqera Cannot or Will Not Do Here」；第 1 條仍要求「點名 Seqera／nf-core／其他維護中工具對同一件事的做法」，並要求「沿用開源部分，或說明為何不適用本實驗室（到不了站點、需 Seqera 的 Services、授權、價格）」 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-004 | 計畫 5 I.2 | 功能 | 同上 | 讀第 2 條 | Nextflow 自己的記錄（trace、report、log、其 nf-tower plugin 發出的事件）是 run 的真相，Seqera Platform 的在 plugin 仍使用它時才算；本 repo 不留第二份；無自有提交腳本、無狀態機、無監控 daemon（僅允許清單內的通道）；Seqera 的後端用 Seqera 的名詞 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-005 | 計畫 5 I.2 第二點 | 功能 | 同上 | 讀第 2 條 | 明寫 Seqera 顯示與 Nextflow 記錄不一致時，以 Nextflow 自己的記錄為準 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-006 | 計畫 5「run index 不寫成規則」 | 功能 | 同上 | 在憲法全文搜尋 `run index` | 憲法不含 `run index`（它在 ROADMAP 等待清單，見 TC-023） | 自動：`tests/platform_direction_docs_test.sh` |
| TC-007 | 計畫 5 原則 2 理由句 | 功能 | 同上 | 讀 Principle I 的 Rationale | 引用 `docs/adr/0004`，不再把「Seqera 變成可選」歸給 `docs/adr/0001` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-008 | 計畫 5 範圍條件 3 | 功能 | 同上 | 讀 3.0.0 修訂紀錄 | 寫明範圍條件 3 目前只列 Seqera／Tower 的 MCP 工具；平台自己的 MCP 工具算不算「使用中」，由將來把閘門移到平台工具的那次修憲決定；「閘門在工具層」不在憲法內 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-009 | 計畫 5「Script header forms and the Check unchanged」 | 例外 | 同上 | 讀第 1 條 | 仍規定 `# Not <tool>: <reason>`／`# Nothing existing: <why>` 兩種檔頭格式；Check 行仍是 `tests/scripts_name_their_alternative.sh`，檔案存在 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-010 | 計畫 5 I.2 Check 不變 | 例外 | 同上 | 讀第 2 條 Check 行 | 仍是 `tests/no_second_run_state_test.sh`；該測試的四項掃描與允許清單與 main 一致，只有檔頭註解改字 | 自動：`tests/constitution_checks_exist_test.sh` |

## US2 — ADR 0004／0005 新增，0001／0003 修訂（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 計畫 1 決定 | 功能 | 修訂完成 | 讀 `docs/adr/0004-self-hosted-platform-mcp-first.md` | 存在；寫明取代 0001；決定含：自架平台、Tower 相容 API 讓 nf-tower plugin（`tower.endpoint`，Apache-2.0）直接回報、所有 AI 入口都經過 MCP 工具、平台只存 metadata、站點憑證留在使用者端 station agent 且只對外連線 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-012 | 計畫 1 被否決的選項（2026-10-09 修訂） | 功能 | 同上 | 讀同檔「Considered Options」 | 逐項列出被否決：自建**通用** harness（理由：harness 由別人維護；平台的聊天只驅動平台自己的工具）、fork 已封存的 nf-tower CE（MPL-2.0）、organisation／workspace／team／SSO 層、Studios；「只開 MCP、不做聊天」列為已於 2026-10-09 被他取代（replaced），不再是現行決定；「自建 harness／聊天介面」不再整句列為被否決 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-013 | 計畫 1 後果（2026-10-09 修訂） | 功能 | 同上 | 讀同檔「Consequences」 | 提到憲法 3.0.0、ADR 0003 修訂、0001 的服務條款理由仍成立、0002 營收線新增託管服務（0002 本身不改）；有一句寫明 Seqera Platform 是參考（`reference`），功能照其公開文件、縮到本地實驗室用得到的範圍；**不含**「一個人重做公司產品的一部分」之類的成本陳述（不含 `rebuilding part of a company`、不含「重做」） | 自動：`tests/platform_direction_docs_test.sh` |
| TC-014 | 計畫 2 | 功能 | 同上 | 讀 `docs/adr/0005-single-lab-multiuser.md` | 存在；兩角色：PI（看到全實驗室、預設不花錢）、成員（跑自己的工作）；每人用自己的國網憑證在自己的 station agent；實驗室之上沒有東西；明寫無 org／workspace／team／SSO | 自動：`tests/platform_direction_docs_test.sh` |
| TC-015 | 計畫 3 | 功能 | 同上 | 讀 `docs/adr/0001-*.md` 開頭 | 頂部有 `Superseded by ADR 0004 (2026-10-08)` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-016 | 計畫 4 | 功能 | 同上 | 讀 `docs/adr/0003-host-strategy.md` | host 為任何 MCP client（Claude Desktop 優先；Claude Code、Codex 等），平台自己的聊天（ADR 0004，階段 3）是同一組工具的又一個 host；閘門移入平台工具層，沒有 hook 的 host 也跳不過；Claude Code plugin 成為薄殼；「Codex adapter」階段刪除 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-017 | 計畫 4「Licence and local-model facts kept」 | 例外 | 同上 | 讀 0003 | 仍含 Claude Code 授權事實（`LICENSE.md`、不支援經 gateway 路由到非 Claude 模型）與本地模型事實 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-018 | 計畫 3「body kept as history」 | 例外 | 同上 | 讀 0001 正文 | 除頂部狀態行外正文保留，含 Seqera Terms of Use 的那段理由 | 自動：`tests/platform_direction_docs_test.sh` |

## US3 — 其餘文件（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 計畫 6 前半 | 功能 | 修訂完成 | 讀 `docs/PRINCIPLES.md` A 節第 1、2 條 | 與憲法 3.0.0 同義，不更嚴也不更鬆；檔內仍有 `in use` 與 `Constitution 2.0.0` | 自動：`tests/constitution_scope_test.sh` |
| TC-020 | 計畫 6 後半 | 功能 | 同上 | 讀「Where each piece belongs」 | 四條「Not an MCP server」理由已移除，改為「平台是 MCP server，因為任何 harness 都必須能呼叫它；判斷留在 skill，MCP 工具只執行動作」；「工具無法承載判斷」的舊理由保留為此分工的理由；全 repo 沒有文件把「Not an MCP server」當現行規則（LAB_AGENTS 歷史段除外） | 自動：`tests/platform_direction_docs_test.sh` |
| TC-021 | 計畫 7 | 功能 | 同上 | 讀 `docs/LAB_AGENTS.md` R7 列與 §8 | R7 判定為 `Reversed by ADR 0004`；§8 改寫為同一結論 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-022 | 計畫 8 階段（2026-10-09 修訂） | 功能 | 同上 | 讀 `docs/ROADMAP.md` 階段表 | 階段 0–5（0 docs；1 station agent（007）；2 平台核心（008–010）；3 web（011–014，其中 014 是平台自己的聊天）；4 雲端算力；5 模型中立出貨），每階段有 done-when；有「dropped」行（舊本地進度頁、舊 Codex adapter） | 自動：`tests/platform_direction_docs_test.sh` |
| TC-023 | 計畫 8 等待清單 | 功能 | 同上 | 讀「Principles waiting for a check」 | 新增五列，各有所需 check 與階段：平台 run index 可重建（階段 2）、平台只存 metadata 且不存站點憑證（1–2）、平台寫入工具沒有確認步驟就拒絕（1–2）、PI／成員角色被強制（2）、閘門在平台工具層（1–2）；原有 6 列改用新階段編號；「無安全網的 host 只能查詢」已改為「host 只能經帶自己閘門的工具到達啟動與刪除」，與工具層閘門不矛盾 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-024 | 計畫 8 開放問題 | 功能 | 同上 | 讀「Open questions」 | 新增 NCHC M6：登入節點可否長駐程序、共用帳號自動化是否被允許 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-025 | 計畫 8 本地模型評估 | 功能 | 同上 | 讀 ROADMAP 評估段 | 評估段保留，標題與內文改掛階段 5（不再寫「stages 3 and 6」或「running on Codex」） | 自動：`tests/platform_direction_docs_test.sh` |
| TC-026 | 計畫 9 前半（2026-10-09 修訂） | 功能 | 同上 | 讀 `docs/POSITIONING.md` 開頭與核心功能 | 一句話定位仍為「台灣版 Seqera」；一句話與核心功能第 2 點寫明：平台有自己的聊天介面、可接使用者選的模型（自己的 API key 或本地模型），同時仍可用自己的 AI（Claude Desktop 等）經 MCP 接上；不再有「平台不自己做對話」字樣 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-027 | 計畫 9 後半 | 功能 | 同上 | 讀競品表、「十個突破點」、「宿主與本地模型」段 | 競品表含 Seqera MCP（註明其文件中無確認機制）、pynf-agent、Agent Skills 標準、MCP Apps、MadCowork（註明只找到 `madcowork-module-spec`、產品說法為口耳相傳、無公開來源）；有「十個突破點」段，推論處標「推論」；「產品的本地模型跑在 Codex 上」標為已被修訂後的 ADR 0003 取代的過去決定 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-028 | 計畫 10 | 功能 | 修訂完成 | 讀 `docs/SEQERA_PARITY.md` | 檔內明寫原始總數 84，並給出各節項目數，相加為 83 個有名字的項目（A16＋B11＋C1＋D5＋E9＋F13＋G2＋H7＋I3＋J9＋K7＝83）；並明白寫出「原始計數為 84，其中 K 節有 1 項被計入卻從未被命名，因此本表只列 83 項」，不得補編一個項目；恰有 4 項標 ★（Dashboard、Launchpad 參數表單、報告渲染、兩角色實驗室；Co-Scientist 列雖新增 Build 但不標 ★）；有來源行（2026-10-08，取自 Seqera 公開文件，不經其服務） | 自動：`tests/platform_direction_docs_test.sh`（斷言檔內同時含 `84`、`83`、各節數字，以及「被計入卻從未被命名」意思的句子；各節數字相加等於 83；★ 數恰為 4） |
| TC-029 | 計畫 11 | 功能 | 同上 | 讀 `CONTEXT.md` | 有 Platform、Station agent、Run index、MCP tool layer 四個詞，各一句白話定義；Platform 的定義寫明可經 MCP 工具從平台自己的聊天或使用者的 harness 到達 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-030 | 計畫 Done when 一致性閱讀 | 功能 | 同上 | 驗收者讀憲法、ADR 0001–0005、ROADMAP、POSITIONING、PRINCIPLES、LAB_AGENTS、CLAUDE.md、README.md | 沒有任何文件把現行規則寫得與憲法 3.0.0 不同；舊方向（含「平台不自己做對話」）只出現在標明歷史或已取代的位置 | 手動：驗收者一致性閱讀 |
| TC-031 | 計畫 8 Positioning／What is sold／Order changed | 功能 | 同上 | 讀 ROADMAP 這三處 | Positioning 與 What is sold 改寫為平台（託管服務為主、盒子在後）；2026-09-29 的 Order changed 保留為歷史，標明已被 2026-10-08 的順序取代並指向 ADR 0004 | 手動：驗收者閱讀 |
| TC-032 | 計畫 8「line A」＋2026-10-09 修訂 1（他回「保留」） | 功能 | 同上 | 讀 ROADMAP 的 A 線 | 有「Line A is unchanged: 2.17.0 goes to the trial lab first」這句，且仍講 2.17.0 交給試用實驗室、安裝步驟給他看；（前提不再是「與 main 相同」，因為這句是新增文字，他已決定保留） | 自動：`tests/platform_direction_docs_test.sh` |
| TC-033 | 計畫 7「H3 trigger paragraph kept」 | 例外 | 同上 | 讀 LAB_AGENTS §8 | H3 重新考慮觸發段仍在，標為歷史 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-034 | 計畫 11 | 例外 | 同上 | 比對 CONTEXT.md | 原有詞條一個都沒被刪 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-059 | 計畫 12 | 功能 | 同上 | 讀 `CLAUDE.md` 第 10 行附近與 `README.md` 第 57 行附近 | 各新增或改寫一句：2.17.0 以 Seqera Platform 為所用後端、Nextflow 自己的記錄為底層真相，並指向憲法 3.0.0；兩檔仍含 `Constitution 2.0.0` 與（CLAUDE.md）`hooks/in_use.sh` | 自動：`tests/platform_direction_docs_test.sh` |

## US4 — 他的例子（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-035 | 「平台只開 MCP，使用者用自己的 harness 接」＋2026-10-09「也做聊天介面 可接模型」 | 功能 | 修訂完成 | 讀 ADR 0004、ADR 0003、ROADMAP 各階段、POSITIONING | 計畫中的聊天介面有且只有一個：平台自己的網頁聊天（階段 3，014），且只經 MCP 工具碰平台；沒有任何一處計畫做通用的自有 harness（只出現在「被否決」或「dropped」）；自帶 harness 經 MCP 接入的路仍保留（Claude Desktop 等仍被列為 host）；沒有任何文件寫「平台不自己做對話」為現行決定 | 手動：驗收者閱讀 |
| TC-036 | 「簡化版多人：PI／成員兩角色」 | 功能 | 同上 | 讀 ADR 0005、ROADMAP | 沒有任何一處計畫 organisation／workspace／team／SSO 層；只出現在「被否決」 | 手動：驗收者閱讀 |
| TC-037 | 「開發與測試全程不經 Seqera 的服務／MCP／tw」（ADR） | 功能 | 同上 | 讀 ADR 0004 | 明寫開發與測試全程不經 Seqera 的 Services、MCP server、`tw` 三者 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-038 | 同上（計畫文件） | 功能 | 同上 | 讀 ROADMAP 階段 1–5 | 在 ROADMAP 明寫同一限制（一句涵蓋全部新階段即可），Services、MCP、`tw` 三者都點名 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-039 | 「平台不持有國網憑證；只存 metadata」 | 功能 | 同上 | 讀 ADR 0004、0005、ROADMAP 等待清單 | 三處皆寫平台不存站點憑證、只存 metadata；憑證在各人自己的 station agent；沒有任何設計段落提到平台儲存國網密碼或金鑰 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-060 | 他 2026-10-09 的話：「也做聊天介面 可接模型」；「不要特別寫到重做 只說參考」 | 功能 | 同上 | 讀 ADR 0004、ROADMAP 階段 3、憲法 3.0.0 修訂紀錄 | (a) ADR 0004 與 ROADMAP 都寫：平台自己的聊天是階段 3 的網頁（ROADMAP 標 014），不是獨立產品或另一套系統；(b) 模型由使用者自己選、自己付費——自己的 API key 或本地模型，平台不替使用者出模型費；(c) 聊天只經與其他 harness 相同的 MCP 工具碰平台，所以確認步驟在聊天裡和在任何 harness 裡一樣、聊天不帶自己的閘門或規則；(d) 不計畫做通用的自有 harness（ADR 0004 與 0003 仍列為被否決）；(e) 自帶 harness 經 MCP 的路仍保留；(f) 憲法 3.0.0 修訂紀錄的理由含他的話「也做聊天介面 可接模型」或其意思，且 Safety Net 與原則文字仍如 TC-040..044 不變；(g) ADR 0004 全文沒有「重做」或 `rebuilding part of a company's product` 的字樣，Seqera Platform 只被稱為參考（`reference`）；(h) ROADMAP、POSITIONING、CONTEXT 不把聊天寫成已存在（見 TC-058） | 自動：`tests/platform_direction_docs_test.sh`（固定字串斷言 a–g；(h) 由 TC-058 手動判定） |

## 憲法與安全網（不得改變的）

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | Safety Net 第 1 條（不刪使用者原始資料） | 例外 | 修訂完成 | 與固定字串比對 | 該條逐字不變（`rawdata/`、`results/`、`analysis/`、`_references/`、共用映像快取；`.nextflow/plugins/`） | 自動：`tests/constitution_scope_test.sh` |
| TC-041 | Safety Net 第 2 條（work／cache 刪除需確認） | 例外 | 同上 | 同上 | 逐字不變，仍指 `hooks/confirm_cleanup.sh` | 自動：`tests/constitution_scope_test.sh` |
| TC-042 | Safety Net 第 3 條（啟動指令完整顯示並等確認） | 例外 | 同上 | 同上 | 逐字不變，仍指 `hooks/confirm_launch.sh` | 自動：`tests/constitution_scope_test.sh` |
| TC-043 | Safety Net 第 4 條（憑證只在設定區） | 例外 | 同上 | 同上 | 整條含 Check 清單逐字不變 | 自動：`tests/constitution_scope_test.sh` |
| TC-044 | Safety Net 範圍與整段 | 例外 | 同上 | 比對 Safety Net 整段 | 範圍三條件、「不確定算使用中」、「使用中以外保持沉默」、`hooks/in_use.sh`、三個 Check 檔、「不得被放寬、只能經 MAJOR 修憲更動」那句全部逐字不變，且整段沒有新增任何段落 | 自動：`tests/constitution_scope_test.sh` |
| TC-045 | 前言「每條規則指名存在的 Check」 | 例外 | 同上 | 跑 `constitution_checks_exist_test.sh` | 結束碼 0，輸出 `all 14 rules`；新增文字沒有造成規則解析多出或遺漏；所有被引用的測試檔存在 | 自動：`tests/constitution_checks_exist_test.sh` |
| TC-046 | 原則 3–13（II–VI） | 例外 | 同上 | `git diff main...HEAD -- .specify/memory/constitution.md` | 原則 3–13 的文字與 Check 行零差異（原則 5 及 `works_without_host_test.sh` 亦在內） | 手動：驗收者 diff |
| TC-047 | 既有範圍測試 | 例外 | 同上 | 跑 `constitution_scope_test.sh` | 除版本與日期兩行外，所有既有斷言不改就綠；PRINCIPLES／CLAUDE／README 等的反向掃描（always on、unconditional 等字樣）仍通過 | 自動：`tests/constitution_scope_test.sh` |
| TC-048 | 改動只在文件 | 例外 | 同上 | `git diff --name-only main...HEAD` | 只含 `docs/`、`.specify/`、`tests/`、`CONTEXT.md`，加上 `CLAUDE.md`、`README.md`（各一句，見 TC-059） | 手動：驗收者 diff |
| TC-049 | 行為不變 | 例外 | 同上 | 比對 `hooks/`、`scripts/`、`commands/`、`skills/`、`.claude-plugin/` | 與 main 逐位元組相同 | 手動：驗收者 diff |
| TC-050 | 不弱化測試 | 例外 | 同上 | 比對 `tests/` 的差異 | 只有：版本／日期行、`no_second_run_state_test.sh` 與 `scripts_name_their_alternative.sh` 的檔頭註解、新增斷言／新檔；沒有任何斷言被刪除、放寬、跳過；允許清單內容不變 | 手動：驗收者 diff |
| TC-051 | 綠燈 | 例外 | 同上 | 在 WSL 跑 `bash tests/run_all.sh`（或看 CI） | 全綠 | 自動：`tests/run_all.sh`（CI） |
| TC-052 | 不改 spec／TC | 例外 | 實作期間 | 比對 `.specify/amendments/3.0.0-platform-direction/test-case*.md` 與已確認版本（2026-10-09 修訂版） | 實作期間零修改 | 手動：驗收者 diff |

## US5 — 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-053 | 計畫 Out of scope：平台／station agent／MCP server 程式碼 | 不在範圍 | 修訂完成 | 檢查 diff 新增檔 | 沒有任何新的原始碼、Dockerfile、套件設定、伺服器目錄；聊天介面也沒有任何程式碼或網頁檔 | 手動：驗收者 diff |
| TC-054 | 計畫 Out of scope：release | 不在範圍 | 同上 | 讀 `.claude-plugin/plugin.json` 與 diff | `version` 仍為 `2.17.0`；沒有新的 release／changelog／tag 條目 | 手動：驗收者 diff |
| TC-055 | 計畫 Out of scope：ADR 0002 | 不在範圍 | 同上 | 比對 `docs/adr/0002-*.md` | 與 main 相同 | 手動：驗收者 diff |
| TC-056 | 計畫 Out of scope：README／CLAUDE.md 其他重寫 | 不在範圍 | 同上 | 比對這兩檔 | 除 TC-059 那一句外零差異；沒有新增「平台已存在」的描述 | 手動：驗收者 diff |
| TC-057 | 階段 1–5 是路線圖，不是功能（2026-10-09 修訂） | 不在範圍 | 同上 | 列出 `specs/` | 沒有為 007–014 建立 spec／tasks 目錄（014 是聊天介面） | 手動：驗收者 diff |
| TC-058 | 不把未做的寫成現況 | 不在範圍 | 同上 | 讀 ROADMAP、POSITIONING、CONTEXT、CLAUDE.md、README | 平台、station agent、平台自己的聊天一律寫成「規劃中」；「現在」仍是 2.17.0；沒有任何文件宣稱它們可用 | 手動：驗收者閱讀 |
