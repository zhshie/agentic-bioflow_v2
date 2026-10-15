# 測試案例：憲法 4.1.0——`skills/` 是判斷與流程的家；ADR 0006；v3 路線圖

**規格**：`.specify/amendments/4.1.0-skills-home/plan.md`（修憲沒有 spec.md；計畫的「維護者的例子」一節是他的原話）與 `docs/adr/0006-four-entries-one-action-layer.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應。這次修憲只改文件與釘字，沒有執行期的出錯情境，所以沒有這一類。
- **不在範圍**：計畫「Not in this PR」明講不做的事；測試確認真的沒做。

他的五個例子（原文，2026-10-15）與去向：

| 例子 | 原話 | 對應的 TC |
|---|---|---|
| E1 | 「只加 MCP 網址就能用」 | TC-008、016、027、036 |
| E2 | 「平台純粹靠GUI介面也要能使用」 | TC-009、020、027、029、037 |
| E3 | 「平台也要有對話介面，若使用者不需要使用claude code等harness介面的話也可以直接對話使用」 | TC-010、019、027、038 |
| E4 | 接受「setup→launch→runs→看報告→打包；畫圖走聊天」 | TC-011、020、021、039 |
| E5 | 「好，加 v3 分支觸發」 | TC-011、022、040 |

E5 的做法：觸發設定在 `v3` 分支自己的 `tests.yml`（push 觸發讀被推送分支的檔案），不在這支 PR。這支 PR 只負責把這個決定寫進憲法紀錄、ROADMAP 與 ADR，並確認沒有碰 `.github/`（TC-060）。

驗證方式說明：「自動」是 `tests/` 底下的測試檔；「手動」是獨立驗收者在 ACCEPTANCE 模式執行並把證據寫進驗收報告的步驟（`git diff main...HEAD`、在 `main` 的文件上跑新版測試檔），不加進 `docs/TESTING.md`（計畫「Test-case conventions for this amendment」）。

## 區塊 A — 憲法本文與 4.1.0 修正紀錄（`.specify/memory/constitution.md`）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 §1 版本行 | 功能 | 修憲完成 | 取憲法檔最後一個非空行 | 逐字等於 `**Version**: 4.1.0 \| **Ratified**: 2026-09-28 \| **Last Amended**: 2026-10-15` | 自動：`tests/platform_direction_docs_test.sh`（TC-001 斷言改成這一行） |
| TC-002 | 計畫 §6 | 功能 | 同上 | 讀憲法全文 | 含 `**Version**: 4.1.0`、`**Last Amended**: 2026-10-15`、`**Ratified**: 2026-09-28`，且 `### 2.0.0 (2026-10-02)` 紀錄仍在；測試標籤文字提到 4.1.0 | 自動：`tests/constitution_scope_test.sh` |
| TC-003 | 計畫 §1 II.5 新文 | 功能 | 同上 | 讀 II.5（把換行壓成空白後比對） | 含：`**5.** Judgment, procedure and site operations live in `skills/`, `docs/` and `scripts/`, readable and runnable by a person or another model.`（只多了 `skills/`，其餘與舊句同義） | 自動：`tests/platform_direction_docs_test.sh` |
| TC-004 | 計畫 §1 II.5 檢查行 | 功能 | 同上 | 讀 II.5 的 *Check:* 行 | 含 `*Check:* `tests/works_without_host_test.sh`: with `hooks/` and `.claude-plugin/` removed, the system still works from `skills/`, `docs/` and `scripts/`: degraded, not equivalent, but usable.` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-005 | 計畫 §1 | 功能 | 同上 | 讀 II.5 的第二句 | 仍含 `Whatever AI host runs the tool, its own capabilities (hooks, skills, commands or their equivalents) MUST be used fully.`，一個字沒變 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-006 | 計畫 §1 紀錄位置 | 功能 | 同上 | 找標題與順序 | 標題逐字為 `### 4.1.0 (2026-10-15): skills are a home of judgment; the platform has four entries`；位置在 `### 4.0.0 (2026-10-11)` 之後、`## Governance` 之前 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-007 | Governance；3.0.0 紀錄的形狀 | 功能 | 同上 | 讀 4.1.0 紀錄 | 依序有五段：`**Rationale.**`、`**What changes.**`、`**Impact on existing deployments.**`、`**Version.**`、`**Approval.**` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-008 | E1 | 功能 | 同上 | 讀 4.1.0 紀錄的 Rationale | 逐字含「只加 MCP 網址就能用」，並引用 `docs/adr/0006` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-009 | E2 | 功能 | 同上 | 讀 Rationale | 逐字含「平台純粹靠GUI介面也要能使用」 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-010 | E3 | 功能 | 同上 | 讀 Rationale | 逐字含「平台也要有對話介面，若使用者不需要使用claude code等harness介面的話也可以直接對話使用」 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-011 | E4、E5 | 功能 | 同上 | 讀 Rationale | 含網頁範圍（`setup → launch → runs → rendered reports → the package`，圖表由聊天或 harness 做）與 v3 分支（`v3`，CI 觸發設在 v3 分支）兩件事的說明 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-012 | 計畫 §1 What changes | 功能 | 同上 | 讀 What changes | 說 II.5 點名 `skills/`（其檢查本來就打包 `skills/`）；四條 v3 新原則排在 `docs/ROADMAP.md` 的「Principles waiting for a check」，隨 feature 009 的那次 MAJOR 修正案加入（不承諾版本號）；Safety Net 逐字不變 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-013 | 計畫 §1 Impact | 功能 | 同上 | 讀 Impact | 寫明「None」，並說明沒有 hook、script、command、skill 變動（真實性由 TC-055 到 TC-058 驗證） | 自動：`tests/platform_direction_docs_test.sh` |
| TC-014 | Governance 版本規則 | 功能 | 同上 | 讀 Version 與 Approval | Version 寫 `MINOR, under Governance`，理由是擴充一條原則、沒有移除或重新定義；Approval 寫維護者核准並合併 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-015 | 既有 TC-006 與計畫 §1 | 功能 | 同上 | (1) 在整份憲法搜 `run index`（不分大小寫）；(2) 在「Core Principles 到 Development Workflow」區段搜 `tool layer` 與 `action layer` | 兩者皆搜不到（4.1.0 紀錄不能引進這些詞；原則與 Safety Net 不載「動作層」） | 自動：`tests/platform_direction_docs_test.sh`（TC-006 維持；TC-008 旁新增 `action layer` 的同款斷言） |

## 區塊 B — `docs/ROADMAP.md`

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | E1；計畫 §2 第 009 格 | 功能 | 修憲完成 | 讀 Stage 2 列的 009 | 含：`the action layer (one function per action, called by the MCP tools, the web pages and the chat)`；`every write action's gate answered on a human channel (elicitation form or a confirmation page)`；`OAuth 2.1 / personal-access-token authorization and the identity each token carries`；`the server's `instructions` and one prompt per skill mirroring `skills/``；`the Skills over MCP endpoint`；``skills/` copied into the package`；`the relay sending events to a public address`；以及 `run_downstream`、`build_package` 等工具名 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-017 | 計畫 §2「rest of the row stays」 | 功能 | 同上 | 讀 Stage 2 列其餘部分 | 008、010 的敘述與 Done-when（`A student in Claude Desktop runs a 16S analysis end to end from conversation, the PI sees it on the web, and nothing goes through Seqera`）原封不動；舊句 `every write tool carries its own confirmation` 不再出現 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-018 | 計畫 §2 Stage 3 | 功能 | 同上 | 讀 Stage 3 列的 011、012、013 | 011–013 的敘述後加上 `, matching the actions one to one (parity test)` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-019 | E3 | 功能 | 同上 | 讀 Stage 3 列的 014 | 逐字仍為 `014: the platform's chat, connecting to the model the user chooses (their own API key or a local model) and calling only the MCP tools of 009` | 自動：`tests/platform_direction_docs_test.sh`（既有 TC-022、TC-060c 維持） |
| TC-020 | E2、E4 | 功能 | 同上 | 讀 Stage 3 列的 Done-when | 開頭是 `A lab member with no AI tool completes setup → launch → runs → rendered reports → the package from the web pages alone (figures from scripts are made in the platform's chat or in a harness); `，其後接原本的 `Two members of the trial lab…` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-021 | E4「畫圖走聊天」 | 功能 | 同上 | 讀同一句 Done-when 的括號 | 括號 `(figures from scripts are made in the platform's chat or in a harness)` 存在；整個 Stage 3 列沒有任何一句把「畫圖」歸給網頁 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-022 | E5；計畫 §2 新段落 | 功能 | 同上 | 讀 "Dropped on 2026-10-08" 段之後 | 緊接新段，逐字含 `v2 and v3 (2026-10-15, ADR 0006): `main` is the v2 line until v3.0.0; v3 is built on the branch `v3`. v2 takes bug fixes and changes that make the Safety Net stricter, released as 2.17.x only when a fix affects a user.`；`Line A is unchanged:` 那句仍在其後 | 自動：`tests/platform_direction_docs_test.sh`（既有 TC-032 維持） |
| TC-023 | 計畫 §2 等待表 | 功能 | 同上 | 讀「Principles waiting for a check」表 | 舊列 `Gates live in the platform's tool layer…` 已被換成 `Gates live in the platform's action layer, which the MCP tools and the web pages both call, and a person answers each gate on a human channel; the plugin's hooks become callers`，檢查欄為 `An unconfirmed launch is refused through the MCP tool and through the web route`；舊句不再出現在表中 | 自動：`tests/platform_direction_docs_test.sh`（TC-023 該斷言改成新句） |
| TC-024 | 計畫 §2 三個新列 | 功能 | 同上 | 讀同一個表 | 三個新列各自存在：(1) `Every entry (MCP client, web page, platform chat, shell) reaches the same action` / `A parity test: every action has an MCP tool and a web route, and `mcp_server` and the web import only `actions``（階段 2–3）；(2) `A call to the platform's own tools counts as a session in use` / `The Safety Net's scope test covers the platform's tools`（階段 2）；(3) `The web pages and the tools match one to one` / 同一個 parity test（階段 3） | 自動：`tests/platform_direction_docs_test.sh`（TC-023 每列一條新斷言） |
| TC-025 | 既有 TC-023 | 功能 | 同上 | 數等待表的資料列與全部 `\| ` 開頭行 | 資料列共 14 條（原 11 條，換 1 條、增 3 條）、含表頭與分隔線共 16 行；原有的其他 10 條逐字不變（run index、metadata only、write tool、roles、approved spec、own credentials、model-neutral、`A host reaches launch and delete only through tools that carry their own gate`、data stays local、money）；沒有列等在階段 6 或 7 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-026 | 不退步 | 功能 | 同上 | 跑 ROADMAP 相關既有斷言 | TC-022（階段 0 到 5 各有 done-when、Dropped 句）、TC-032、TC-038、TC-060c 全部仍過；`platform/tests/test_station_docs.py` 的 `test_tc077_…` 仍過 | 自動：`tests/platform_direction_docs_test.sh`、`platform/tests/test_station_docs.py` |

## 區塊 C — `docs/POSITIONING.md` 第 2 點

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-027 | E1、E2、E3；計畫 §3 | 功能 | 修憲完成 | 讀核心特點第 2 點的粗體開頭 | 逐字為 `平台有四個入口：你自己的 AI（接 MCP 網址）、平台網頁、平台自己的聊天介面、命令列。`（三個入口各對到他的一句話：MCP 網址、GUI、聊天） | 自動：`tests/platform_direction_docs_test.sh` |
| TC-028 | 計畫 §3 末句 | 功能 | 同上 | 讀第 2 點末句 | 逐字為 `判斷留在 skill，工具只做動作，每個寫入動作都要你本人確認——按 yes 的是人，不是模型（`docs/adr/0006`）。`；舊句 `每個寫入動作都要你確認（`docs/adr/0003`）` 不再出現 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-029 | E2（GUI 才能不靠 AI） | 功能 | 同上 | 讀第 2 點中間那句 | 逐字為 `沒有 AI 工具的成員直接用平台網頁點選，不需要任何模型；想用對話的，用平台自己的聊天介面，接自己選的模型（自己的 API key 或本地模型），它走的是同一組 MCP 工具（2026-10-09 加入，`docs/adr/0004`；2026-10-15 四個入口，`docs/adr/0006`）。`；舊的「沒有 AI 工具的成員，用平台網頁上的聊天介面」不再出現 | 自動：`tests/platform_direction_docs_test.sh`（新增 `has` 新句、`hasnt` 舊句；既有 `接自己選的模型（自己的 API key 或本地模型），它走的是同一組 MCP 工具` 斷言仍過） |
| TC-030 | 計畫 §6（TC-026 的釘字） | 功能 | 同上 | 讀測試檔 `tests/platform_direction_docs_test.sh` 的 TC-026 區（約第 286 行） | 舊的 `平台只開 MCP，對話用你自己的 AI，或平台自己的聊天介面` 斷言已改成釘 `平台有四個入口：你自己的 AI（接 MCP 網址）、平台網頁、平台自己的聊天介面、命令列`，並新增 `hasnt "TC-026: the old 'MCP only' lead is gone" "$POS" '平台只開 MCP'`；一句話定位那行（`平台有自己的聊天介面，可接你選的模型；也可以用你已經在用的 AI（Claude Desktop 等）透過 MCP 接上`）原斷言不動 | 自動：`tests/platform_direction_docs_test.sh` |

## 區塊 D — `CONTEXT.md`

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-031 | 計畫 §4 第一條 | 功能 | 修憲完成 | 讀 `**MCP tool layer**` 條目 | 原三句仍在（含 `each write tool carries its own confirmation gate`、`Planned (Stage 2).`），並新增一句 `Since ADR 0006 the tools call the action layer; the gate lives there.` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-032 | 計畫 §4 第二條 | 功能 | 同上 | 讀新條目 `**action layer** (動作層)` | 與 MCP tool layer 在同一個詞彙區段；內容含 `one function per platform action`、`called by the MCP tools, the web pages and the chat alike`、`the gate of a write action lives here`、`Planned (Stage 2, feature 009)`、`_Avoid_: API, backend` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-033 | 計畫 §4 第三條；ADR「按 yes 的是人」 | 功能 | 同上 | 讀新條目 `**human channel** (人通道)` | 同區段；含 `the way a person, not the model, answers a gate`、`an elicitation form in the harness, or a confirmation page on the platform`、`The token is the record of that answer, not the answer.`、`Planned (Stage 2).`、`_Avoid_: confirmation token (when the act is meant)` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-034 | 既有 TC-029、TC-034 | 功能 | 同上 | 檢查 CONTEXT.md | 既有 15 個釘住的詞仍都有定義，兩個新詞的粗體條目都是一行定義開頭（與 TC-029 同形）；沒有任何舊詞被刪或改名 | 自動：`tests/platform_direction_docs_test.sh` |

## 區塊 E — ADR 0006、ADR 0003、ADR 0004

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-035 | ADR 0006 檔頭 | 功能 | 修憲完成 | 讀 `docs/adr/0006-four-entries-one-action-layer.md` | 檔案存在；標題為 `Four entries, one action layer…`；含 `Amends ADR 0003 and ADR 0004 (2026-10-15)` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-036 | E1 | 功能 | 同上 | 讀 ADR「The problem this record answers」 | 含 `Install cost: 「只加 MCP 網址就能用」 — a user adds one MCP URL to the harness they already have; nothing else is required.` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-037 | E2 | 功能 | 同上 | 同一節 | 含 `「平台純粹靠GUI介面也要能使用」 — the platform's web pages are a complete entry for a person with no AI tool.` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-038 | E3 | 功能 | 同上 | 同一節 | 含 `「平台也要有對話介面，若使用者不需要使用claude code等harness介面的話也可以直接對話使用」 — the platform's own chat is a full entry too, not a later extra.` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-039 | E4 | 功能 | 同上 | 讀 ADR「What the web pages must do without AI」 | 含 `the web pages complete **setup → launch → runs → rendered reports → the package of the pipeline's outputs**; figures from scripts are made in the platform's chat or in a harness.` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-040 | E5 | 功能 | 同上 | 讀 ADR「v2 and v3」 | 含 `v3 is built on the long-lived branch `v3``；含 `the CI trigger for `v3` is configured on the `v3` branch itself, not in this record's pull request`；含 `the maintainer approved the CI change on 2026-10-15`；`main` 在 v3.0.0 前維持 v2 線 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-041 | ADR 結構 | 功能 | 同上 | 列出 ADR 的小節標題 | 有：`### Four entries, one action layer`、`### The "yes" must come from a person`、`### Where the platform runs, and who is calling`、`### Hooks and the gates they carry`、`### What the web pages must do without AI`、`### v2 and v3`、`### The constitution`，以及 `## Considered Options`、`## Consequences` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-042 | ADR 的 hook 對照 | 功能 | 同上 | 讀「Hooks and the gates they carry」的表 | 四列：`hooks/confirm_launch.sh`（隨 feature 009 的那次 MAJOR 修憲）、`hooks/confirm_cleanup.sh`（`kept for good`）、`hooks/confirm_walkthrough.sh`（G7）、`hooks/guard_plugin_files.sh`（`kept`）；並說移除閘門 hook 是維護者的決定、屬 MAJOR | 自動：`tests/platform_direction_docs_test.sh` |
| TC-043 | ADR 與憲法一致 | 功能 | 同上 | 比較 ADR「The constitution」一節與憲法 4.1.0 紀錄 | 兩者都說：4.1.0（MINOR）、II.5 點名 `skills/`、四條新原則排在 ROADMAP 等待表 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-044 | 計畫 §5 | 功能 | 同上 | 讀 `docs/adr/0003-host-strategy.md` 標題下 | 新增一行 `Amended 2026-10-15 by ADR 0006: gates live in the action layer the tools and the web pages call; a harness kit is not an adapter`；原文一句不改（含 `move into the platform's tool layer`，既有 TC-016 全過） | 自動：`tests/platform_direction_docs_test.sh` |
| TC-045 | 計畫 §5 | 功能 | 同上 | 讀 `docs/adr/0004-self-hosted-platform-mcp-first.md` 標題下 | 新增一行 `Amended 2026-10-15 by ADR 0006: the web pages are a non-AI entry to the same actions; the confirmation is a person's act on a human channel`；原文一句不改（既有 TC-011、TC-012、TC-013 全過） | 自動：`tests/platform_direction_docs_test.sh` |
| TC-046 | 計畫 §1 版本號不承諾 | 功能 | 同上 | 在 ADR 0006 與憲法 4.1.0 紀錄裡搜 `6.0.0` | 搜不到；ADR 與紀錄都改說「the MAJOR amendment that ships with feature 009」。（v3.0.0 是產品版本，不受此限） | 自動：`tests/platform_direction_docs_test.sh`（新增 `hasnt`，樣式用 `(^|[^0-9.])6\.0\.0`，避免誤傷 `v3.0.0`） |

## 區塊 F — 釘字、引用文件與紅燈先行

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-047 | 計畫 §6 | 功能 | 修憲完成 | 讀 `CLAUDE.md` 第 11 行與 `README.md` 第 56、58 行 | 這些行裡原本的 `constitution 4.0.0` 都已改為 `constitution 4.1.0`；兩份文件裡不再有 `constitution 4.0.0` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-048 | 計畫 §6 TC-059 | 功能 | 同上 | 讀測試檔的 TC-059 區 | 斷言改為 `CLAUDE.md` 含 `constitution 4.1.0`、`README.md` 含 `Nextflow's own records, the truth under constitution 4.1.0`；同區其他斷言不動 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-049 | Governance：引用文件同一支 PR 更新；計畫 §4b | 功能 | 同上 | 讀 `docs/PRINCIPLES.md` 第 5 條段落（約第 67 行） | 含 `Judgment, procedure and site operations live in `skills/`, `docs/` and `scripts/`, which a person or another model can read and run directly.`；舊句（只列 `docs/` 與 `scripts/`）不再出現；同段其餘文字不動 | 自動：`tests/platform_direction_docs_test.sh`（新增一條 `has`、一條 `hasnt`） |
| TC-050 | 計畫 §6 TC-008 | 功能 | 同上 | 讀測試檔的 TC-008 區 | 原 `nin "$RULES" 'tool layer'` 保留，旁邊新增 `nin "$RULES" 'action layer'` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-051 | 計畫「Red first」 | 功能 | 取得新版 `tests/constitution_scope_test.sh`，放在未修改文件的 `main` 上 | 在 `main` 的文件上跑新版測試檔 | 失敗，且點名版本行與 `Last Amended`；放回 PR 分支後全過 | 手動：驗收者在暫時工作樹執行並記錄 |
| TC-052 | 計畫「Red first」 | 功能 | 取得新版 `tests/platform_direction_docs_test.sh`，放在 `main` 上 | 在 `main` 的文件上跑 | 失敗，且至少點名：TC-001 版本行、TC-016 到 TC-024 的新句、TC-026（新開頭）、TC-027 到 TC-033、TC-049；放回 PR 分支後全過 | 手動：驗收者在暫時工作樹執行並記錄 |
| TC-053 | 計畫「Red first」結尾 | 功能 | PR 分支 | 在 WSL 或 CI 跑 `bash tests/run_all.sh` | 全綠 | 自動：`tests/run_all.sh`（CI：`.github/workflows/tests.yml`） |
| TC-054 | 計畫 §6 最後一條 | 功能 | PR 分支 | 讀 `tests/works_without_host_test.sh` 第 94 行並跑該檔 | 第 94 行仍是 `for need in docs/PITFALLS.md … skills/operational/SKILL.md commands/setup.md commands/launch.md commands/runs.md; do`（一字未改）；該檔仍過 | 自動：`tests/works_without_host_test.sh` |

## 區塊 G — 不在範圍（計畫 §7）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-055 | §7「No change to `commands/`」 | 不在範圍 | PR 分支 | `git diff --name-only main...HEAD` | 沒有任何 `commands/` 路徑 | 手動：驗收者執行並記錄 |
| TC-056 | §7「No change to `skills/`」 | 不在範圍 | 同上 | 同上 | 沒有任何 `skills/` 路徑（五個 command 檔還沒搬成 skill；那是 `v3` 分支的事） | 手動：同上 |
| TC-057 | §7「No change to `hooks/`」 | 不在範圍 | 同上 | 同上 | 沒有任何 `hooks/` 路徑 | 手動：同上 |
| TC-058 | §7「No change to `scripts/`」 | 不在範圍 | 同上 | 同上 | 沒有任何 `scripts/` 路徑 | 手動：同上 |
| TC-059 | §7「No change to `platform/`」 | 不在範圍 | 同上 | 同上 | 沒有任何 `platform/` 路徑；`platform/abf_platform/actions/` 不存在（動作層只在文件裡，沒被偷偷實作） | 手動：同上 |
| TC-060 | §7「this PR does not touch `.github/`」；E5 在 `v3` 分支上交付 | 不在範圍 | 同上 | `git diff --name-only main...HEAD` | 沒有任何 `.github/` 路徑（`tests.yml` 一個字都沒動；v3 的 CI 觸發由 `v3` 分支自己的 `tests.yml` 負責，不在這支 PR） | 手動：同上 |
| TC-061 | §7「No change to `docs/LAB_AGENTS.md`, `docs/CONDITIONS.md`」 | 不在範圍 | 同上 | 同上 | 這兩個檔不在清單內 | 手動：同上 |
| TC-062 | §7「No change to `scripts/detect_conditions.sh`」 | 不在範圍 | 同上 | 同上 | 該檔不在清單內 | 手動：同上 |
| TC-063 | §7「No CHANGELOG」 | 不在範圍 | 同上 | 同上 | 沒有新增或修改任何 `CHANGELOG*` | 手動：同上 |
| TC-064 | ADR 的 Consequences（動作層屬 feature 009） | 不在範圍 | 修憲完成 | 讀 CONTEXT 與 ROADMAP 對動作層、人通道的說法 | 一律寫成計畫中：CONTEXT 兩個新條目含 `Planned`；ROADMAP 把它們放在 Stage 2 的 009 與等待表；沒有任何文件說「平台現在已有動作層」 | 自動：`tests/platform_direction_docs_test.sh`（與 TC-032、TC-033 同一組斷言） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-065 | Safety Net（整節） | 功能 | PR 分支 | 取憲法 `## Safety Net` 到 `## Development Workflow` 之間的文字，與 `main` 同一段逐位元組比對 | 完全相同，零差異（含 Scope、三個「in use」條件、四條規則、*Check:* 行） | 手動：驗收者以 `git show main:.specify/memory/constitution.md` 比對並記錄 |
| TC-066 | Safety Net 的既有檢查 | 功能 | 同上 | 跑 `tests/constitution_scope_test.sh` | 全部 `sn_has` 斷言與 TC-021 版本斷言通過 | 自動：`tests/constitution_scope_test.sh` |
| TC-067 | II.5 的檢查還有效 | 功能 | 同上 | (1) 確認 `tests/works_without_host_test.sh` 存在；(2) 讀它打包的內容 | II.5 仍點名這支測試，檔案存在，其打包指令仍含 `skills`（第 40 行 `tar -c scripts docs commands skills …`），使「只靠 `skills/`、`docs/`、`scripts/` 仍可用」這句話有測試撐腰 | 自動：`tests/works_without_host_test.sh` |
| TC-068 | Governance：修憲範圍 | 功能 | 同上 | `git diff main...HEAD -- .specify/memory/constitution.md` | 變動只有三處：II.5 的第一句（加 `skills/`，連同 Check 行）、新增的 4.1.0 紀錄、最後一行版本行；原則 I、III、IV、V、VI 與 Development Workflow、Governance 一字未動 | 手動：驗收者逐 hunk 核對並記錄 |
| TC-069 | 2.0.0 到 4.0.0 的紀錄 | 功能 | 同上 | 同一個 diff | 2.0.0、2.0.1、2.1.0、3.0.0、4.0.0 五段紀錄沒有任何字被改（只在其後新增） | 手動：同上 |
| TC-070 | 原則 I.2 與它的檢查 | 功能 | 同上 | 跑 `tests/no_second_run_state_test.sh` | 全過；I.2 文字與 *Check:* 行不變 | 自動：`tests/no_second_run_state_test.sh` |
| TC-071 | 2.0.1：每條規則都有存在的檢查 | 功能 | 同上 | 跑 `tests/constitution_checks_exist_test.sh` | 全過（II.5 的 *Check:* 仍指向存在的檔案） | 自動：`tests/constitution_checks_exist_test.sh` |
| TC-072 | Governance 節 | 功能 | 同上 | 比對 `## Governance` 節與 `main` | 一字未改 | 手動：驗收者比對並記錄 |
