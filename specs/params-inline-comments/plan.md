---
id: params-inline-comments
title: 方法段「Why these parameters」認得行尾註解（`key: value  # 為什麼`）——現在這種寫法的理由整個被丟掉
tier: A
kinds: backend
lane: L-params-why
base: v3（`origin/v3` @ 50f696b；所有行號都是該版本）
source: developer-agent 讀碼查證＋實測（2026-10-25，WSL python3 對 `rationale()` 直接餵檔）；issue #23 第 7 列 `methods_text.py` / `params-yaml-comment-conv`（只有指標、沒有診斷，本任務取其中能被測試釘住的一半）
---

# params-inline-comments

> A 級 bug：`finish` 的方法段是「為什麼選這個值」唯一的出處；理由寫在行尾就消失，方法段看起來完整卻少了理由。純外掛側，不碰 `platform/`、`hooks/`。

## 目標
`scripts/methods_text.py` 的 `rationale()` 除了「key 上方的註解區塊」之外，也收「key 同一行的行尾註解」，兩者並存時合併成同一條。對使用者的意義：params.yaml 不管註解寫在上方還是行尾，方法段的「Why these parameters」都帶得到。

### 查證結果（皆 `origin/v3`；實測輸出見下）
- `scripts/methods_text.py:518-537` `rationale(path)` 逐行讀：`st.startswith("#")` 就把去掉 `#` 的文字收進 `pending`（:529-530）；遇到含 `:` 的非註解行，取 `:` 前為 key，若 `pending` 非空就產出 `(key, " ".join(pending))`，然後清空（:531-535）；空白行也清空（:536-537）。**同一行 `#` 之後的文字從來不被讀。**
- 呼叫處：`methods_text.py:662-671`（`why = rationale(run["launch_params"])`，輸出 `- \`key\` — text`，標題 `### Why these parameters`，`Source:` 行已在）。`launch_params` 由 `scripts/collect_provenance.py:465-470` 指向 run 資料夾的 `params.yaml`／`params.yml`。
- 實測（WSL python3 3.10，對 `scripts/methods_text.py`）：輸入含 `filter: true   # drop low quality on purpose` 與上方有註解的 `single_end`、`outdir`，`rationale()` 回 `[('single_end','reads are paired'), ('outdir', …)]`——**`filter` 整條消失**。
- 同一次實測另發現：被註解掉的預設值行（`#   trim_front: 5`）會被併進下一個 key 的理由（`('outdir', 'trim_front: 5 why outdir')`）。**本任務不修這一半**，見「裁決」。
- 慣例出處：本 repo 自己的設定檔用行尾註解寫理由（`tests/settings_test.sh:35` `workspace_id: 111  # the one value a lab shares`），所以兩種寫法都是人會寫的。

## 維護者原話（verifier 出題用）
本任務沒有他的逐字裁示；來源是 issue #23 與上面的實測。等價要求：
- 「理由寫在哪都不該消失」→ T1、T2、T3。
- 「既有的上方註解寫法不能壞」→ T6、T7（既有測試鎖住）。

## 範圍：檔案（只准改這些，共 3 個）
- `scripts/methods_text.py`（只改 `rationale()`；可在它上方加一個小的私有輔助函式；不改 `render()`）
- `tests/methods_text_test.sh`（只**加**案例；既有斷言一律不改）
- `specs/params-inline-comments/ledger.md`（新）

**不准動**：`scripts/collect_provenance.py`、`scripts/build_package.sh`、`hooks/`、`platform/**`、`.claude-plugin/plugin.json`、憲法、`docs/`。

## 作法（決定）
1. 新輔助函式 `_split_inline(line) -> (code, comment_or_None)`：從第一個 `:` 之後的值部分開始掃，追蹤單引號與雙引號（雙引號內的 `\"` 不結束引號）；**不在引號內**且（位於值的開頭或前一字元是空白）的 `#` 才是註解起點。`http://x/#frag`（`#` 前不是空白）與 `"a # b"`（在引號內）都不是註解。
2. `rationale()` 對每個非 `#` 開頭的行先 `_split_inline`；`code` 部分仍用現有規則（含 `:` 才算 key，key＝第一個 `:` 前去空白）。
3. 理由文字＝`pending` 區塊文字，後面接行尾註解文字（去掉 `#` 與前後空白；空註解不算），中間單一空白相連。兩者皆空則不產出。
4. 行尾註解**只**屬於它那一行的 key，不進 `pending`（不會洩到下一個 key）。
5. 沒有 `:` 的行（清單項目 `- a  # c`、裸字）行為不變：不產出，且照舊清空 `pending`。
6. 輸出形狀不變：`list[(key:str, text:str)]`，順序＝檔案順序。

## 失敗先行測試（`tests/methods_text_test.sh`，走 CLI：寫 `params.yaml` → `"$S" --assets … "$RUN/results"` → 看 `Why these parameters` 之後的行）
| # | params.yaml 內容 | 期望 | 現在 |
|---|---|---|---|
| T1 | `filter: true   # drop low quality on purpose` | 輸出含 `` - `filter` — drop low quality on purpose `` | 紅 |
| T2 | 上方 `# reads are long` ＋ `pacbio: true  # per the kit sheet` | 同一條：`` `pacbio` — reads are long per the kit sheet `` | 紅 |
| T3 | 兩個連續 key 各有行尾註解 | 兩條，各自只含自己的註解（不串） | 紅 |
| T4 | `url: http://x/y#frag` | 不產出 `url` 條目 | 綠（鎖住） |
| T5 | `msg: "a # b"` 與 `msg2: 'c # d'` | 不產出 | 綠（鎖住） |
| T6 | 只有上方註解（現有 fixture：`tests/methods_text_test.sh:41-44`） | 與現在逐字相同 | 綠（鎖住） |
| T7 | 空註解 `x: 1 #` 與 `y: 2 #   ` | 不產出 | 綠（鎖住） |
| T8 | 行尾註解之後的 key 沒有上方註解：`a: 1 # one` 緊接 `b: 2` | 只有 `a`，`b` 不帶 `one` | 紅 |
| T9 | 清單項目 `  - item  # nested` | 不產出；其後的 key 不帶它 | 綠（鎖住） |
| T10 | 引號內含 `\"` 的值：`q: "say \"hi\" # not a comment"  # real` | 理由＝`real` | 紅 |
| T11 | 被註解掉的 `#   trim_front: 5` 緊接 `outdir: results`（現況行為） | 與現在逐字相同（鎖住，不修） | 綠（鎖住） |

**現在會紅**：T1、T2、T3、T8、T10。executor 先跑並貼出紅的輸出再動手；T1 在 base 上若是綠的，回報 BLOCKED（代表推論有誤）。

**會改斷言的既有測試：無。** 已核對 `git grep -n "params.yaml" tests/`：`tests/methods_text_test.sh:99` 找 `error model differs`（上方註解，T6 同路徑）；`tests/package_gaps_test.sh:227` 找 `Why these parameters` 後三行含 `params.yaml`（`Source:` 行，不動）；`tests/build_package_test.sh:33,195`、`tests/collect_provenance_test.sh:43`、`tests/methods_text_fetch_test.sh:64` 的 params.yaml 都只有一行 `# …` 註解、沒有 key，輸出不變。

## 完成標準（done when）
- T1–T11 全綠；`tests/methods_text_test.sh`、`package_gaps_test.sh`、`build_package_test.sh`、`collect_provenance_test.sh`、`methods_text_fetch_test.sh` 不改而綠；整套 `bash tests/run_all.sh`（WSL）綠。
- `git diff --name-only` 只含上列 3 個檔。新增案例 ≤ 14 條；`rationale()` 仍只用標準函式庫（`tests/no_per_pipeline_config.sh` 會 grep 此檔，不得出現管線名或工具名表）。

## 環境事實
- `scripts/methods_text.py` 含非 ASCII 字元，原生 Windows 的 Python 2.7 讀不了；本機驗證一律用 WSL／Linux 的 `python3`。
- 全套測試只能在 WSL 跑；worktree 不可在同步磁碟（repo `CLAUDE.md`「For the executor and verifier」）。

## 不做
- 不修「被註解掉的預設值被併進下一個 key」（見裁決）；不解析多行字串或 YAML 錨點；不動 `render()` 的輸出格式；不改 `docs/`。
- 不需要 migration（無資料表、JSON 欄位）。

## 裁決
- **只修行尾註解、不修註解掉的預設值**：後者要判斷 `# note: x`（人寫的理由）和 `#   trim_front: 5`（被註解掉的設定）哪個是理由，任何規則都會誤判其中一邊；issue #23 的回報又只有指標、沒說是哪一種。T11 把現況鎖住，將來要修再開任務並先問維護者該算理由還是雜訊。
- **合併順序＝上方在前、行尾在後**：讀起來是由總到細。

## 裁決（2026-10-25 06:50，developer-agent）
1. 被註解掉的預設值行（`#   trim_front: 5`）本片不處理，只用測試鎖住現狀；之後若要分辨再另開。

## 裁決（2026-10-25 07:35，已知環境紅）
- `platform/tests/test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 在完整 clone 上本來就紅（釘舊提交 6061925），由 onboarding-test-pinned-base 修。本片把它當已知環境紅：全套只剩這一條紅時視同綠，寫 GREEN，ledger 記一行。

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
