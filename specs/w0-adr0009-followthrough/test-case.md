# 測試案例：W0 路線圖與說明文件跟上 ADR 0009（網頁三欄）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
這次是純文件變更（tier C），沒有 spec.md；需求來源是 `specs/w0-adr0009-followthrough/plan.md`：
「給維護者」3 點、設計決定 D1–D9、第二輪裁決 R2、變更步驟 C1–C4、「Not in this PR」。
下面「對應需求」欄用這些代號。計畫沒寫死的字句，預期結果只寫計畫給的概念與錨點字串，不替它發明。
-->

**規格**：`specs/w0-adr0009-followthrough/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時系統怎麼反應。（本次是純文件，沒有此類。）
- **不在範圍**：計畫明講這次不做的事；確認真的沒做。

「自動」＝`tests/platform_direction_docs_test.sh`（本次要擴充的文件檢查，每條斷言掛 TC 編號）；「手動」＝驗收者用 `git diff v3...HEAD` 與帳本 `specs/w0-adr0009-followthrough/ledger.md` 核對（本次不新增 `docs/TESTING.md` 步驟，見總覽的疑問）。

## User Story 1 — 階段 2 與「Who」段落跟上（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | D3；維護者點 1（兩種角色延後） | 功能 | 改完的 `docs/ROADMAP.md` | 讀階段表第 2 列裡的 010 | 010 不再是「做兩種角色的實驗室」，而是標成 `postponed (ADR 0009)` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-002 | D3 | 功能 | 同上 | 讀階段 2 的「完成條件」 | 寫「the student sees it on the web」；不再有「the PI sees it on the web」；其餘「A student in Claude Desktop runs a 16S analysis end to end from conversation」與「nothing goes through Seqera」保留 | 自動 |
| TC-003 | D1；D9 | 功能 | 同上 | 讀階段 2 其餘內容 | 列標題仍是 `Platform core (features 008–010)`；008 那句與 009 的各子句（動作層、MCP 工具、人通道、OAuth/token、instructions 與 prompt、Skills over MCP、skills/ 複製、relay 公網位址）原樣保留 | 自動 |
| TC-004 | D3 | 功能 | 同上 | 讀 `Who` 段落（開頭「Who:」） | 舊句「the PI pays and sees the whole lab」不見了 | 自動 |
| TC-005 | D3；維護者點 1 | 功能 | 同上 | 讀同一段 | 說明一個人一個帳號、只看得到自己的 run（only their own runs） | 自動 |
| TC-006 | D3 | 功能 | 同上 | 讀同一段 | 說明 PI 視角隨角色一起延後（postponed，提到 ADR 0009） | 自動 |
| TC-007 | D3；D9 | 功能 | 同上 | 讀同一段其餘句子 | 「首批是大學農業／植病／微生物實驗室、從 16S 與 RNA-seq 開始」「醫院不在範圍」兩句保留 | 自動 |

## User Story 2 — 階段 3「Web」那一列跟上（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-008 | R2 Studios；C2 | 功能 | 改完的 `docs/ROADMAP.md` | 讀階段 3 那一列的標題 | 標題成為 `**Web** (features 011–014, 016)`，仍是階段 3 | 自動 |
| TC-009 | D2；維護者點 1（專案／分析成為一項功能） | 功能 | 同上 | 讀 011 | 011 寫成：網頁骨架、右欄（所有分析的進度）、專案與分析、run 詳情、失敗一句話，並以 `011a–e` 標示（五項） | 自動 |
| TC-010 | D2；維護者點 1（不再有儀表板頁） | 功能 | 同上 | 搜整份 ROADMAP | 沒有「dashboard page」；階段 3 沒有「011: dashboard and run detail」 | 自動 |
| TC-011 | D2 | 功能 | 同上 | 讀 012 | 012 寫成：設定與引導式設定、launch 階段、上傳，並以 `012a–d` 標示（四項） | 自動 |
| TC-012 | D4 | 功能 | 同上 | 讀 012 的費用句 | 費用依運算環境顯示（per compute environment）；雲端上限是每人每月（per person per month），數字在開帳號時定 | 自動 |
| TC-013 | D4 | 功能 | 同上 | 讀 012 的費用句 | 寫明開發模式（dev mode）對國網 SU 不設上限（no NCHC SU cap） | 自動 |
| TC-014 | D4；C2 | 功能 | 同上 | 搜階段 3 那一列 | 舊句「SU estimate with a cap」已改寫、不再出現 | 自動 |
| TC-015 | D2 | 功能 | 同上 | 讀 013 | 013 寫成：結果、完成與打包，並以 `013a–b` 標示（兩項） | 自動 |
| TC-016 | R2 parity sentence | 功能 | 同上 | 數階段 3 那一列裡的「matching the actions one to one (parity test)」 | 011、012、013 各保留一次，共 3 次 | 自動 |
| TC-017 | D2（014 不變） | 功能 | 同上 | 讀 014 | 原句一字不差：「014: the platform's chat, connecting to the model the user chooses (their own API key or a local model) and calling only the MCP tools of 009」 | 自動 |
| TC-018 | D2；維護者點 1（Studios 成為一項功能） | 功能 | 同上 | 讀階段 3 那一列 | Studios 有自己的編號 `016`（不是 015，015 是 Jev），且寫在階段 3 之內 | 自動 |
| TC-019 | D2 Stage 3 done-when | 功能 | 同上 | 讀階段 3 完成條件的前半 | 寫成：沒有 AI 的人只用網頁走完 設定 → launch → 執行中 → 結果 → 下游（在 Studio 裡）→ 完成（setup → launch → running → results → downstream (in a Studio) → finished） | 自動 |
| TC-020 | R2 Stage 3 done-when | 功能 | 同上 | 讀完成條件後半 | 原樣接在前半後面：「Two members of the trial lab use it for two weeks with fewer than 10 new PITFALLS; the hosted service goes live (charging waits on the open questions below)」 | 自動 |
| TC-021 | D2；D9 | 功能 | 同上 | 搜階段 3 那一列有沒有「網頁負責做圖」的句子 | 沒有「web page(s) make/draw/plot」這類句子（圖仍由腳本在聊天或外殼裡做） | 自動 |
| TC-022 | D1 | 功能 | 同上 | 看階段 0、1、2、3、4、5 與 011–014 的編號 | 階段 0、1、4、5 的列首字串不變；沒有重新編號，只增列；每個階段仍有非空的完成條件 | 自動 |

## User Story 3 — 等待清單與未決問題（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | D5 | 功能 | 改完的 `docs/ROADMAP.md` | 讀「Principles waiting for a check」裡的角色那一列 | 那一列的階段欄改為 `postponed (ADR 0009)`，仍是表格裡的一列 | 自動 |
| TC-024 | D5 | 功能 | 同上 | 讀同一個表 | 多一列「owed parity — every action has an MCP tool and a web route; the owed list only shrinks」 | 自動 |
| TC-025 | D5 | 功能 | 同上 | 讀新列的「檢查」欄 | 寫明檢查隨 011a 的 parity test 到來 | 自動 |
| TC-026 | R2 count | 功能 | 同上 | 數該表以 `\|` 開頭的行 | 17 行（原 16 加新列），不是 16 | 自動 |
| TC-027 | D5；D9 | 功能 | 同上 | 檢查表中其他列 | 其餘各列（run index、metadata only、write tool 確認、action layer、同一動作、平台工具算 in use、網頁與工具一對一、host 只經有閘門的工具等）文字不變，沒有任何列等待階段 6 或 7 | 自動 |
| TC-028 | D8；R2 Open questions | 功能 | 同上 | 讀「Open questions」章節 | 原有四題之後出現新小節，標題正是「Open questions from ADR 0009 (answered before the slice that needs them)」；原本的開頭句「Each must be answered before the hosted service charges anyone (Stage 3).」不變 | 自動 |
| TC-029 | D8 | 功能 | 同上 | 讀原有四題 | 兵役／發票、Seqera 使用條款與商標、國網 M6（login node 能否常駐、單一帳號自動化是否允許）、TWCC 四題仍在 | 自動 |
| TC-030 | D8 | 功能 | 同上 | 讀新小節 | 有一題問「託管服務如何建立帳號」 | 自動 |
| TC-031 | D8 | 功能 | 同上 | 讀新小節 | 有一題問「沒有記錄是誰跑的 run 要不要顯示」 | 自動 |
| TC-032 | D8 | 功能 | 同上 | 讀新小節 | 有一題問「上傳／下載可不可以經過託管平台」 | 自動 |
| TC-033 | D8 | 功能 | 同上 | 讀新小節 | 有一題問「每次續跑／重跑要不要再走確認頁」 | 自動 |
| TC-034 | D8 | 功能 | 同上 | 讀新小節 | 有一題問「國網上的 Studios」，並註明那是第二條送件路徑、需要修憲 | 自動 |
| TC-035 | D8 | 功能 | 同上 | 讀新小節 | 有一題問「雲端帳號與每月上限的數字」 | 自動 |

## User Story 4 — ADR 0004 指標與 POSITIONING（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-036 | D6 | 功能 | 改完的 `docs/adr/0004-self-hosted-platform-mcp-first.md` | 讀「Studios」那一項 | 底下多一行「Superseded for Studios by ADR 0008 and ADR 0009.」 | 自動 |
| TC-037 | D6 | 功能 | 同上 | 讀同一項 | 被測試釘住的句子仍在：「Studios**: rejected; the user's own IDE on the site does that job」 | 自動 |
| TC-038 | D6 | 功能 | 同上 | `git diff v3...HEAD -- docs/adr/0004-self-hosted-platform-mcp-first.md` | 只多一行，其餘不動（含「兩角色」那句） | 手動：驗收者核對 diff |
| TC-039 | D7；R2 POSITIONING | 功能 | 改完的 `docs/POSITIONING.md` | 讀核心特點 1（第 18 行）的「不做」清單 | 清單不再把 Studios 列為不做（Studios 在 v3.0.0） | 自動 |
| TC-040 | D7 | 功能 | 同上 | 讀同一行 | 仍寫 Data Explorer 不做；說明不做儀表板頁、右欄取代儀表板 | 自動 |
| TC-041 | D7；維護者點 1 | 功能 | 同上 | 讀同一行 | 不再寫「簡化成 PI／成員兩種角色」；改為角色延後並指向 ADR 0009 | 自動 |
| TC-042 | R2 POSITIONING | 功能 | 同上 | 讀突破點 1（第 31 行） | 「Data Explorer／Studios 在國網實測被拒（`docs/SITE_ADAPTER.md`）」原樣保留，這是實測事實 | 自動 |
| TC-043 | R2 POSITIONING | 功能 | 同上 | 讀突破點 9（第 39 行「PI 一頁看全部」） | 該列標為延後（postponed／延後）並指向 ADR 0009 | 自動 |
| TC-044 | D9 | 功能 | 同上 | 跑 `tests/platform_direction_docs_test.sh` 與 `tests/jev_test.sh` 的 POSITIONING 斷言 | 四個入口、聊天介面、競品表、十個突破點標題、Jev 預設關等既有斷言全部維持通過 | 自動：`tests/platform_direction_docs_test.sh`、`tests/jev_test.sh` |

## User Story 5 — 紅燈在先、釘住的舊句子逐句交代（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-045 | C1 | 功能 | 帳本 `ledger.md` | 讀帳本 | 有一筆紀錄：新加的檢查在文件還沒改時跑出紅燈（列出哪些失敗），之後才改文件 | 手動：驗收者讀帳本 |
| TC-046 | C2；維護者點 3 | 功能 | 同上 | 對照測試檔 diff 與帳本 | 每一條被改寫的舊斷言（至少 `:256`、`:392`、`:290` 的 16→17、`:471-472`、`:474-476`、`:478`；`:274` 若有改也要列）在帳本都有「舊期待／新期待／為什麼」三項 | 手動 |
| TC-047 | C2 | 功能 | 測試檔 `tests/platform_direction_docs_test.sh` | `git diff v3...HEAD -- tests/` | 被改動的舊斷言只有帳本列出的那幾條；其他斷言沒有被刪、放寬、跳過；其餘變動全是新增 | 手動 |
| TC-048 | Facts（必須保留的釘子） | 功能 | 同上 | 看 diff | 以下斷言原樣還在：ADR 0005 的 PI 文字（`:188-189`）、SEQERA_PARITY 的 `A16 B11 C1 D5 E9 F13 G2 H7 I3 J9 K7`（`:340`）與 ★ 項目含 Dashboard 與 two-role lab（`:344`）、014 聊天各釘子（`:393-400`） | 手動 |
| TC-049 | C4 | 功能 | 工作樹 | 在 WSL 跑 `bash tests/run_all.sh`（原生 Git Bash 會拒絕，見 `docs/TESTING.md`） | 全部通過 | 自動：`tests/run_all.sh`（WSL／CI） |
| TC-050 | 維護者點 3 | 功能 | 帳本 | 對照 diff 裡 ROADMAP／POSITIONING 被改掉的每句舊句子 | 每一句被測試釘住的舊句子，帳本都寫了改了什麼、為什麼 | 手動 |

## 不在範圍（計畫「Not in this PR」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-051 | Not in PR：任何程式；維護者點 2 | 不在範圍 | 整個變更 | `git diff --stat v3...HEAD` | 動到的只有 `docs/ROADMAP.md`、`docs/POSITIONING.md`、`docs/adr/0004-…md`、`tests/platform_direction_docs_test.sh`、`specs/w0-adr0009-followthrough/` 底下；沒有 `platform/`、`scripts/`、`hooks/`、`skills/` 等程式 | 手動 |
| TC-052 | Not in PR；D9：`PLATFORM.md` | 不在範圍 | 同上 | `git diff v3...HEAD -- docs/PLATFORM.md` | 無任何變動 | 手動 |
| TC-053 | Not in PR：parity test 本身 | 不在範圍 | 同上 | 檢查 diff 與新檔 | 沒有新增 parity test（它屬於 011a）；owed 清單的檢查只是列在 ROADMAP 文字裡 | 手動 |
| TC-054 | Not in PR；D9：SEQERA_PARITY 勾選與數量 | 不在範圍 | 同上 | `git diff v3...HEAD -- docs/SEQERA_PARITY.md` | 無任何變動（數量與 Done 勾選都沒動） | 手動 |
| TC-055 | Not in PR：對未決問題下決定；D8 | 不在範圍 | 新小節 | 讀六個問題 | 每題都是問句或「待回答」，沒有寫出答案或決定 | 手動 |
| TC-056 | R2：CONTEXT.md 與 ADR 0004 第 8 行 | 不在範圍 | 同上 | `git diff v3...HEAD -- CONTEXT.md` 並看 ADR 0004 第 8 行 | `CONTEXT.md` 無變動；ADR 0004 第 8 行（「simplified two-role lab (ADR 0005)」）原樣 | 手動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-057 | 憲法本文（Governance／Amendments；D9） | 功能 | 整個變更 | `git diff v3...HEAD -- .specify/memory/constitution.md` 並跑既有版本行釘子（TC-001） | 憲法無任何變動；最後一行仍是 `Version: 4.1.0` | 手動：核對 diff；版本行由 `tests/platform_direction_docs_test.sh` 把關 |
| TC-058 | 安全網（hooks 與閘門） | 功能 | 同上 | `git diff v3...HEAD -- hooks/ tests/` 中與閘門有關的測試檔 | `hooks/` 無變動；除 `platform_direction_docs_test.sh` 外沒有任何測試檔被動到 | 手動 |
| TC-059 | 憲法只收已有檢查的規則（2.0.1）；ROADMAP 等待清單 | 功能 | 新增的 owed parity 列 | 搜憲法 | 「owed parity」沒有被寫進憲法，只在 ROADMAP 等待清單（檢查未到，不得入憲） | 自動 |
