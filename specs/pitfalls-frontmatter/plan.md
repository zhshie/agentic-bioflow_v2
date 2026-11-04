---
id: pitfalls-frontmatter
title: PITFALLS 每一條加上固定欄位（症狀、根因、檢查、涉及模組），讓 dev-planner 能依模組或工具名 grep；順手修 PLATFORM.md 的 tier 字樣
tier: C
kinds: docs
risk: S
lane: L-pitfalls-frontmatter
branch: docs/pitfalls-frontmatter
base: v3
source: memory/dev-queue.json 的 backlog 項 pitfalls-frontmatter；2026-11-03 A／C 對調（constitution 6.2.0：開發主導者自行合併）
---

# pitfalls-frontmatter

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/pitfalls-frontmatter/plan.md`。**只處理本任務，只改文件與一支測試**。

## 目標
`docs/PITFALLS.md`（v3 上共 95 個條目標題、約 126 KB、2056 行；注意檔在 `docs/`，不在 repo 根）目前是自由敘述，dev-planner 要查「這次動到的模組或工具有沒有踩過的坑」只能全文硬讀。本任務給每個條目補上四個固定欄位：症狀、根因、檢查（能偵測它的指令或測試）、涉及的檔案／工具。計畫撰寫者就能 `grep -n '^Touches:.*agent_ctl'` 直接找到相關條目。條目原文與意思一律不動；只加。順手把 `docs/PLATFORM.md` 846 行的「one tier A PR」改成 tier C（2026-11-03 起自行合併的是 C 級）。

## 維護者原話（verifier 出題用）
backlog 項的原文（`memory/dev-queue.json`，id `pitfalls-frontmatter`，逐字）：
1. 「Give each PITFALLS.md entry structured fields: symptom, root cause, check (a command or test that detects it) so dev-planner can grep them by module or tool name.」→ 每條都有 symptom、root cause、check 三欄，且可 grep；另加 Touches 欄做模組／工具索引（見作法）。
2. 「Convert existing entries without changing meaning; add a short header explaining the format.」→ 既有文字一行不刪不改（diff 只有新增行）；檔首有一段簡短的格式說明。
3. 「Docs only.」→ 只動文件，外加一支檢查格式的測試；不動腳本、hooks、constitution、`.github/`。
4. 「順手：docs/PLATFORM.md:846「one tier A PR」依 11-03 A／C 對調改成 tier C。」→ 該句改為 tier C，不波及其他句子。

## 範圍：檔案
只准改這三個：
- `docs/PITFALLS.md`（加檔首格式說明、每條加四行）。
- `docs/PLATFORM.md`（只改 846 行那一句；v3 上該行為「- A new snapshot is one tier A PR: the changed file, plus the new sha here and in the test.」）。
- 新測試 `tests/pitfalls_format_test.sh`（bash，沿用 `tests/pitfalls_supervise_test.sh` 的簡單寫法與 `tests/docs_nano4_keys.sh` 的 `ok`／`bad`／`has` 輔助函式；executor 確認 `tests/run_all.sh` 會自動撿到 `*_test.sh`，若是白名單則在回報中說明，但**不要**為此改 run_all.sh）。

不得動：`.specify/memory/constitution.md`、`.github/`、`hooks/`、`plugin.json`、`platform/abf_station/`。

被釘住的既有檢查（`git -C <repo> grep -n "PITFALLS" origin/v3 -- tests platform/tests` 查得；本任務只加行，下列都必須仍綠）：
- `tests/pitfalls_supervise_test.sh`：`docs/PITFALLS.md` 含 `--relative-paths`、`auto mode classifier`、`UNVERIFIED`、`maxParallel`。
- `tests/docs_nano4_keys.sh`：標題行要符合 `^\*\*52\. .*read-only.*\*\*`、`^\*\*53\. .*-r.*\*\*`（所以**條目標題行與編號不可動，新欄位不可插在標題行之前或之中**）；內文含 `NXF_SINGULARITY_LIBRARYDIR`、`NXF_SINGULARITY_CACHEDIR`。
- `platform/tests/test_launch_docs.py::test_tc058_pitfalls_gets_the_two_new_entries`：含「GatewayPorts off on NCHC: reverse forward is loopback-only (measured 2026-10-11)」與「Seqera launcher scripts hold the token in a 755 file」（該測試對全文 `flat()` 後比對）。
- `platform/tests/test_onboarding_doc.py::test_tc045_tc046_readme_pointer`：只看 README，不看 PITFALLS 內容；不受影響。
- 條目編號被其他檔以「PITFALLS 35／36／16e／20c／28」引用（`tests/column_output_relay_rule.sh`、`tests/daemon_cwd_test.sh` 要求 `scripts/agent_ctl.sh`、`scripts/egress_ctl.sh` 含字串 `PITFALLS 36`）：**編號與順序不得改**。
- `tests/works_without_host_test.sh` 第 94 行：只要求檔案存在。
- 列出全部：`git -C <repo> grep -n "PITFALLS" origin/v3 -- tests platform/tests`。
- `docs/PLATFORM.md` 846 行附近沒有被測試釘住的字串（`git grep -n "tier A PR" origin/v3` 只有該行）；`test_launch_docs.py` 只讀 PLATFORM.md 第 9 節的其他句子，executor 改完跑一次確認。

## 作法
**格式（決定，不要自己另創）**。每個條目 = 以 `**<編號>. ` 開頭的標題行起，到下一個標題行、下一個 `## ` 標題、或檔尾為止。在**每個條目的最後**（條目最後一行正文之後，緊接一個空行之前）依序補四行，每行以固定標籤開頭、**單行、不折行**、標籤前無符號：

```
Symptom: <使用者或 agent 看到什麼，一句>
Root cause: <為什麼會這樣，一句>
Check: <能偵測它的指令或測試；沒有自動檢查就寫「none automated: <條目裡已有的手動核對步驟>」>
Touches: <逗號分隔的檔案路徑或工具名，例如 scripts/agent_ctl.sh, tw, ssh>
```

規則：
- 標籤使用 `Symptom:`、`Root cause:`、`Check:`、`Touches:`（大小寫固定）。條目現有文字裡若已有以這四個標籤開頭的行，executor 先 `grep -n -E '^(Symptom|Root cause|Check|Touches):' docs/PITFALLS.md` 查出並在 ledger 說明如何避開；預期 0 筆。
- 內容**只能取自條目原文**（可濃縮成一句、可用條目原有的詞），不得補寫條目沒說的事實。條目原文沒講根因時寫「not established in this entry」，不得猜。
- `Check:` 優先填條目自己或 repo 已有的測試／腳本（例如條目 2b 的 `tests/agent_ctl_connection_id_test.sh`、條目 35 的 `tests/column_output_relay_rule.sh`、條目 36 的 `tests/daemon_cwd_test.sh`、條目 58 的 `platform/tests/test_station_realpath_down.py`、條目 57 的 `tests/preflight_ssh_fold_test.sh`）。executor 要用 `ls` 確認所填的檔存在於 v3；可用 `git grep -n "PITFALLS <編號>" origin/v3 -- tests scripts` 找每條對應的測試。填的指令／測試路徑要放在反引號裡。
- `Touches:` 用條目正文出現過的路徑與工具名，小寫工具名照原樣（`tw`、`ssh`、`nextflow`、`singularity` 等），讓 `grep -n '^Touches:.*<名稱>'` 可用。
- 子條目（2b、3b、3c、4e、16e、20b～20j 等有字母後綴者）各自算一個條目，各補一組；全文 95 個標題行都要有。
- 條目原文、編號、標題行、順序、各 `##` 分章一律不動；diff 只有新增行。

**檔首格式說明**：在第 4 行（開場兩段之後）、第一個 `## Setting up the agent` 之前，新增一段 `## How an entry is written`（約 10 行，英文，與全檔同語言）：說明四個標籤的意思、每個一行、放在條目末尾；說明「grep 範例」兩行（依模組找：`grep -n '^Touches:.*prepare_launch' docs/PITFALLS.md`；找沒有自動檢查的：`grep -n '^Check: none automated' docs/PITFALLS.md`）；說明欄位是索引，條目正文是依據，兩者不一致以正文為準。這一段是唯一允許在條目區之外新增的內容。

**PLATFORM.md 846 行**：先讀該句前後（「nf-core module catalogue」小節，Source／Each input record／Regenerate 三點之後）與 `.specify/memory/constitution.md` 的 6.2.0 條（約 672～700 行）及 Development Workflow 的決策分級段（約 357 行起），確認「自行合併的一級」現在叫 C。確認後只把 `tier A PR` 改為 `tier C PR`，句子其餘照舊：「- A new snapshot is one tier C PR: the changed file, plus the new sha here and in the test.」不加註解、不擴寫。若 constitution 實際分級表與「C = 自行合併」不符，**不改**，把原文貼進 ledger 並回報。
同檔 746 行另有「*(Tier A: OAuth only adds another way to prove who the caller is...)*」：那是別的主張（OAuth 的分級），**本任務不動**；executor 在 ledger 記一行「746 行仍為 Tier A，是否也要隨 A／C 對調改，請 developer-agent 判斷」。

**工作方式建議**：95 條不必手寫腳本，但也不要讓腳本代寫欄位內容（內容需讀原文）。可用小腳本只做「把四行插在條目末尾」的機械動作，欄位內容由 executor 逐條填。完成後用 `git diff --numstat origin/v3 -- docs/PITFALLS.md` 確認刪除行數為 0。檔案內有 CRLF／LF 混用的話維持原樣（`has` 輔助函式會 `tr -d '\r'`），不要整檔轉換行尾。

## 失敗先行測試（`tests/pitfalls_format_test.sh`）
先寫、現在在 v3 上會紅的案例（標籤沿用 `TC-nnn` 即可，檔頭註明 `docs/PITFALLS.md` 與本計畫）：
1. `TC-001 header present`：檔內有 `## How an entry is written` 一行，位置在第一個 `## Setting up the agent` 之前；該段文字含 `Symptom:`、`Root cause:`、`Check:`、`Touches:` 四個標籤名。
2. `TC-002 every entry has the four fields`：逐條掃（標題行樣式 `^\*\*[0-9]+[a-z0-9]*\. `；條目到下一個標題行、`## ` 或檔尾為止），每條恰好各有一行以四標籤開頭、順序為 Symptom, Root cause, Check, Touches、標籤後有非空內容。失敗訊息要印出缺欄位的條目編號。
3. `TC-003 entry count`：標題行數 ≥ 95（v3 基準），且編號 1 到 58 每個整數至少出現一次（防止有人為了通過而刪條目）。
4. `TC-004 check field is honest`：每條的 `Check:` 內容要嘛含反引號包住的字串，要嘛以 `none automated:` 開頭；含反引號且看起來是 repo 路徑（以 `tests/`、`platform/tests/`、`scripts/` 開頭）的，檔案必須存在（相對 repo 根）。
5. `TC-005 touches is greppable`：`Touches:` 之後至少一個項目；整份檔 `grep -c '^Touches:'` 等於條目數。
6. `TC-006 pinned strings survive`：`--relative-paths`、`auto mode classifier`、`UNVERIFIED`、`maxParallel`、`NXF_SINGULARITY_LIBRARYDIR`、`NXF_SINGULARITY_CACHEDIR`、「GatewayPorts off on NCHC: reverse forward is loopback-only (measured 2026-10-11)」、「Seqera launcher scripts hold the token in a 755 file」皆在；`^\*\*52\. .*read-only.*\*\*` 與 `^\*\*53\. .*-r.*\*\*` 各一行符合。
7. `TC-007 platform tier wording`：`docs/PLATFORM.md` 不含 `one tier A PR`，且含 `A new snapshot is one tier C PR`。
8. `TC-008 no secrets or stray control text`：新增欄位文字不含 `abf_pat_`、token 樣式（沿用 `test_onboarding_doc.py` 的 `abf_pat_|mst1\d{5}|u9\d{7}` 樣式即可）。

「只新增、不刪改」由閱卷看 `git diff --numstat origin/v3 -- docs/PITFALLS.md` 的刪除欄為 0（依 README 通例，證據貼進 ledger.md，不必寫進測試）。

## 完成標準（done when）
- `tests/pitfalls_format_test.sh` 綠，且在未改文件前確實紅過（ledger 貼紅燈輸出）。
- 既有被釘住的測試仍綠：`tests/pitfalls_supervise_test.sh`、`tests/docs_nano4_keys.sh`、`tests/column_output_relay_rule.sh`、`tests/daemon_cwd_test.sh`，以及 `platform/tests/test_launch_docs.py`；完整 `tests/run_all.sh --timeout 900` 全綠（環境紅依 README 通例）。
- `git diff --numstat origin/v3 -- docs/PITFALLS.md` 刪除行 0；`git diff --stat` 只列三個允許的檔案。
- PLATFORM.md 846 行改為 tier C，其他行未動；746 行的疑問已寫進 ledger。
- 抽樣三條（建議 2b、28、57）給閱卷核對欄位內容確實取自原文。
- 專長守則檢查一行寫進報告。

## 環境事實
- repo：`C:\Users\marvi\Desktop\agentic-bioflow\agentic-bioflow_v2`，基底 `origin/v3`。`git show origin/v3:docs/PITFALLS.md`（在 Git Bash 若路徑含冒號被轉換，加 `MSYS_NO_PATHCONV=1`）。
- 檔案結構：分章為 `## Setting up the agent`（6 行起）、`Resources`（324）、`Launching`（499）、`Do not rebuild what nf-core already does`（589）、`Driving the site from a laptop`（642）、`Driving the IDE from a terminal`（1110）、`Lab agents`（1733）；條目標題都是粗體 `**<編號>. <標題>.**`，標題可能折成多行（例如 2b），正文有表格、程式碼區塊與長引文。條目 45 之後多為「What was seen／Why／Fix」格式，可直接取欄位。
- 基準規模：126,638 bytes；95 個標題行（含字母後綴）。
- constitution 6.2.0 於 2026-11-03 生效：「The development lead merges every pull request after CI is green and the independent acceptance passes」；受保護路徑另有第二次對抗審。本任務不涉及。
- `tests/*_test.sh` 用 `ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"` 取 repo 根。
- PITFALLS 已查：此任務改的就是 PITFALLS 本身；`docs/solutions/` 在 v3 不存在。repo 根與 `.claude/` 無另一份 PITFALLS。既有條目與本任務相關的只有格式（上列被釘住的標題與關鍵字）；`.specify/bugs/pitfalls-supervise/` 是舊任務紀錄，不是規則。

## 不做
- 不改任何條目的原文、編號、標題行、順序；不合併、不拆分、不刪舊條目、不重寫成較短版本。
- 不把 PITFALLS 拆成多檔或改成 YAML frontmatter 檔（「frontmatter」在此指每條的固定欄位）。
- 不新增條目；不補寫條目沒有的根因或檢查（缺就明寫 `not established in this entry` 或 `none automated:`）。
- 不改 `docs/PLATFORM.md` 的其他句子，包含 746 行的 Tier A（只在 ledger 提問）。
- 不動 constitution、`.github/`、hooks、腳本、`tests/run_all.sh`。
- 不寫「建 dev-planner 自動讀這些欄位」的程式；那是後續任務。

## 裁決
1. 整套測試一律 `run_in_background`＋等待迴圈跑 `tests/run_all.sh --timeout 900`。
2. 合約規則：計畫未明寫的細節由 verifier 依專長守則與既有慣例自訂預期值，不以「計畫未寫」退回；test-case.md 全文放進回傳值，條數 ≤ 20。
3. 欄位內容取自原文：閱卷抽樣核對，發現憑空補寫即退回。
4. worktree 用 Windows git 建，WSL 裡 `constitution_scope_test.sh` 紅＝環境問題，以 CI 為準，ledger 註明；落地前 `git merge origin/v3`。

N. 裁決（11-03，executor 回報被擋）：授權改 `platform/tests/test_catalogue.py` 第 419 行的正規式為 `tier A|tier C|A-tier|A 級|A級`（只這一處，因為 PLATFORM.md:846 改 tier C 後此測試會紅；這只是讓文字斷言接受新分級，沒有放寬任何安全檢查）。PLATFORM.md:746 的「Tier A: OAuth…」仍不動，寫進 ledger。fields/ 下的草稿檔留在 specs/pitfalls-frontmatter/fields/ 即可，不必刪。

## 專長守則（docs）

（工作區沒有 `.claude/dev-profiles/docs.md`；本任務無專長守則。）
