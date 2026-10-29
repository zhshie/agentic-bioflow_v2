---
id: regex-dollar-newline
title: 四個名稱檢查的正規式結尾從 `$` 改成 `\Z`，不再接受結尾多一個換行的名字
tier: A
kinds: backend
lane: L24-regex-anchor
branch: fix/regex-dollar-newline
base: origin/v3@7bc7e15（2026-10-29 量；行號取自此，executor 開工前用 `git show origin/v3:<檔>` 重查，不對以實際內容為準）
source: 2026-10-29 Sonnet 掃描（developer-agent 已在 origin/v3 逐行核對）
---

# regex-dollar-newline

> 只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
Python 的 `re.match` 遇到以 `$` 結尾的樣式時，會放過「結尾多一個換行」的字串（`"abc\n"` 符合 `^[a-z]+$`）。專案較新的規則已經改用 `\Z`（只認字串真正的結尾），但還有四個名稱檢查用 `$`。結果：管線名 `"abc\n"` 會被收下，`compose.render` 產生 `main.nf` 時把換行後半段寫成獨立一行程式碼，產出的管線壞掉；資料集名稱可以多一個字元超過文件寫的 64 字上限。把四處改成 `\Z`，合法名字的結果完全不變。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。
- 既有拒絕訊息已寫明規則（例：`actions/pipelines.py` 拒絕名稱時說 lowercase、1 to 40）；本件只讓程式真的照訊息做。
- A 級的前提：只更嚴、合法輸入行為不變；若發現需要改動合法輸入的行為，停下回報 BLOCKED。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/compose.py`（只動第 21–22 行 `_ID`、`_NAME`；第 23–24 行 `_KEY`、`_IDENT` 也是 `$` 結尾，一併改成 `\Z`，理由相同）
- `platform/abf_platform/actions/pipelines.py`（只動第 16 行 `_NAME`）
- `platform/abf_platform/actions/datasets.py`（只動第 24 行 `_NAME`；第 25–29 行 `_SCHEME`、`_EXT`、`_TAG`、`_NUM`、`_LANE` 是拿來切檔名或比對開頭／副檔名的，**不准動**）
- `platform/abf_launch/build.py`（只動第 208 行 `OWNER_NAME`）
- 測試：加進既有 `platform/tests/test_compose.py`、`platform/tests/test_pipelines_validation.py`、`platform/tests/test_datasets.py`；build.py 的案例若找不到合適的既有檔，新建 `platform/tests/test_name_anchors.py`（檔頭前 40 行內要有 `# Nothing existing: …` 至少 15 個字說明原因）。
- **不准碰**：`fetch.py`、`records.py`、`cloud_store.py`、`launch.py`、`mcp_server.py`、`handlers.py`、`rules.py`（另有車道在改）、`web/`、任何既有測試的既有斷言。

## 作法
- **證據**（origin/v3@7bc7e15）：
  - `compose.py:21` `_ID = re.compile(r"^[a-z][a-z0-9_]{0,31}$")`；`compose.py:22` `_NAME = re.compile(r"^[a-z][a-z0-9-]{0,39}$")`
  - `actions/pipelines.py:16` `_NAME = re.compile(r"^[a-z][a-z0-9-]{0,39}$")`
  - `actions/datasets.py:24` `_NAME = re.compile(r"^[A-Za-z0-9._-]{1,64}$")`，於第 291 行使用
  - `abf_launch/build.py:208` `OWNER_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")`，於第 226 行使用
  - 對照：`compute_envs.py:63` `_QUEUE`、`rules.py:13–14` 已用 `\Z`。
- **決定**：上述正規式結尾 `$` → `\Z`，樣式其餘字元一字不改；不新增拒絕訊息，走各處既有的拒絕路徑與文字。

## 失敗先行測試
先寫、改程式前跑一次確認紅，紅的輸出貼進 ledger。
- compose：`compose.normalize`（或該檔既有測試用的入口）收到節點 id `"a\n"` 要回報問題；管線名 `"abc\n"` 要被拒。**現在紅**。
- pipelines：`create_pipeline(name="abc\n", …合法 graph…)` 被拒，且資料庫／儲存沒有新增。**現在紅**。
- datasets：名稱 `"a"*64 + "\n"` 被拒；`"a"*64` 仍被接受。**現在紅**（前者）。
- build：`OWNER_NAME` 的使用處收到 `"nf-core/rnaseq\n"` 被拒；`"nf-core/rnaseq"` 仍通過。**現在紅**（前者）。
- 對照組（必須一直綠）：每個檢查各舉兩個合法名字（含最長合法長度）仍通過；`render` 合法管線的輸出與改前逐位元組相同（用既有的 golden 或在兩分支各產一次比對）。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」：動閘門要在兩個分支跑同一份測試檔）：在 `origin/v3` 與本分支各跑上述測試檔，貼輸出。

## 完成標準（done when）
- 新測試改前紅、改後綠；對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含「範圍」列的檔；每個程式檔只動正規式那幾行；沒有既有測試被改弱；兩分支輸出比對貼上。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_compose.py bash tests/platform_test.sh`（相對於 `platform/`；`ABF_PYTEST_ARGS` 可加 `-k`）。
  - 全套：`tests/run_all.sh` 不接受原生 Git Bash，要在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII（例如 `$HOME`）：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 Bash 的 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束；測試還在背景跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不改任何樣式的允許字元或長度；不改拒絕訊息；不動 datasets.py 的檔名切割正規式。
- 不掃全 repo 其他 `$` 結尾的正規式（多數是切字用，不是閘門）；有看到疑似閘門的，寫進 ledger 的「後續」，不在本件改。
- 不需要 migration（沒有資料結構或資料內容變動；已存的名字都不含換行）。

## 裁決
1. **`_KEY`、`_IDENT` 要不要一起改？** 它們也是 compose 的輸入閘門（設定鍵、識別字），同樣會被換行繞過寫進 `main.nf`。**定案：一起改。**
2. **datasets.py 其餘正規式？** `_EXT`、`_TAG`、`_NUM`、`_LANE` 是對檔名做切割，結尾換行不會出現在 FASTQ 檔名比對的合法輸入裡，改了反而可能動到切割結果。**定案：不動。**
3. **紅測試入口（預檢 10-29）**：`compose.normalize(graph, data)` 沒有名稱參數，管線名檢查在 `compose.render`（compose.py:258，檢查在 263）。**定案**：管線名 `"abc\n"` 由 `compose.render(canonical, name, version)` 測；`compose.normalize` 只測節點 id `"a\n"`、參數鍵 `ext.args\n`、輸出名 `"x\n"`。build 測 build.py:226 所在的 `_param_path`；pipelines 測 `create_pipeline(platform_path, *, name, graph)`；datasets 測 `register_dataset(platform_path, *, name, version, samplesheet, files)`。開工前用 `git show origin/v3:<檔>` 重查簽名。
4. **`_KEY`、`_IDENT` 紅測試（預檢 10-29）**：裁決 1 加了它們，失敗先行測試也要涵蓋。**定案**：經 `normalize` 送入參數鍵 `ext.args\n` 與輸出名 `x\n`；改前應被接受（測試紅），改後被拒。
5. **`_IDENT` 的入口（verifier 出題 10-29）**：`normalize` 在檢查 `_IDENT` 前先擋「沒有這個輸出通道」，`x\n` 改前就被拒，紅不了。**定案：(a)**：用手工組出的 canonical 圖直接呼叫 `compose.render`（compose.py:279 也檢查 `_IDENT`，檢查跑兩次是刻意的）。裁決 4 的 `_IDENT` 部分以本條為準；`_KEY` 仍經 `normalize` 測，若同樣被前一道檢查擋住，也改走 `render`。
6. **build 的意思（確認）**：對，`_param_path` 改後把 `nf-core/rnaseq\n` 當成路徑回傳、不再回 None，真正的拒絕在 `_confine`。TC-030／TC-031 照這樣寫即可；要求的是「從外面送進來最後被拒」，不在乎是哪一層拒。
7. **datasets 的 `version`**：共用同一個 `_NAME`，改後一併變嚴。**定案：加一條**：版本 `"v1\n"` 被拒、`"v1"` 仍收下。
8. **手動 TC**：本件的「手動」項都是 `git diff origin/v3...HEAD` 檢查，不需要 TESTING.md 步驟；ledger 貼 diff 統計即可。

### developer-agent 確認（2026-10-29）
證據已在 origin/v3@7bc7e15 逐行核對屬實；裁決如上。A 級：只收緊，不放寬任何安全網、不改使用者看得到的文字。

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
