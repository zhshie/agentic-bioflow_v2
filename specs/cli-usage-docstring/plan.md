---
id: cli-usage-docstring
title: abf_platform/cli.py 第 2 行的指令清單漏了 oauth、dataset、runs offer-cleanup；補齊並加一則防再過期的測試
tier: B
kinds: backend
lane: L28-cli-doc
branch: docs/cli-usage-docstring
base: origin/v3@68de6de（2026-10-29 量；行號取自此，executor 開工前用 `git show origin/v3:<檔>` 重查，不對以實際內容為準）
source: 2026-10-29 Sonnet 掃描（找「清單／數字漂移」類 A 級；原指定的 handlers 候選已有計畫 handlers-header-comment，且檔在 abf_station 不在 abf_platform）
---

# cli-usage-docstring

> 只有計畫、沒有程式。B 級（網頁外）→ verifier 通過＋CI 綠由 developer-agent 自合，每日清單附一行前後對照。

## 目標
`abf-platform` 的模組說明（第 2 行，也是 `--help` 開頭那段描述）列出所有指令，但少了三組實際存在的：`oauth revoke`、`dataset register|list|show`、`runs offer-cleanup`；結尾「the four commands of the hand-off record」也沒有任何可對的實體。把清單補齊，並加一則測試：以後新增子指令卻沒改說明就會紅。任何指令的行為、旗標、輸出一概不變。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「過期文件與程式矛盾」要附 `file:line` 證據，且要能描述一則現在會紅的測試。
- A 級的前提：合法輸入的行為不變；若發現需要改動指令行為，停下回報 BLOCKED。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/cli.py`（**只改第 2 行的模組說明字串**；不動第 1 行註解、不動任何 `add_parser`／`help=`／函式）
- 測試：**新建** `platform/tests/test_cli_usage_doc.py`（檔頭前 40 行內要有 `# Nothing existing: …` 至少 15 個字，內容：既有 test_cli.py、test_dataset_cli.py 驗各指令的行為，沒有任何測試檢查模組說明有沒有列出 build_parser 裡的子指令）
- **不准碰**：`compose.py`、`actions/pipelines.py`、`actions/datasets.py`、`abf_launch/build.py`、`abf_station/rules.py`、`records.py`、`web.py`、`web_upload.py`、web 模板、`confirm.py`、`compute_envs.py`、`jobs.py`、`store.py`、任何 k8s 相關檔、任何既有測試的既有斷言、`docs/`。

## 作法
### 證據（origin/v3@68de6de）
- 說明：`platform/abf_platform/cli.py:2`「abf-platform: serve | web | token new | agent-token new|revoke | user add|cloud-cap|passwd [--temporary]|welcome | pat new|list|revoke | ce ... | mcp [--http] | runs assign RUN --user NAME | rebuild [<folder>...] | the four commands of the hand-off record (see their own --help)」。
- 程式：`build_parser()`（cli.py:708 起，`description=__doc__` 在 :709）實際註冊 `oauth`（:781，`oauth revoke` :783）、`dataset`（:841，`register` :843／`list` :851／`show` :854）、`runs offer-cleanup`（:833）。這三組在第 2 行完全沒出現。
- 「the four commands of the hand-off record」：同一說明沒有任何一處能對到「四個」；`runs` 底下現在是 `assign`、`offer-cleanup` 兩個，`rebuild` 另外列了。數字無法自圓，視為過期。

### 決定
- 第 2 行改成：沿用現有各項的寫法，補上 `oauth revoke USER`（看 :783 的實際參數名）、`dataset register|list|show`、`runs assign|offer-cleanup`；刪掉「the four commands of the hand-off record …」整句。**不放任何新的數量詞**，避免再次過期。
- 這段說明同時是 `--help` 的描述文字，所以 `abf-platform --help` 開頭那行會變長；這是唯一可見差異，屬文件。其餘輸出不變。
- 新增文字避開站台掃描禁字與 constitution 的 grep 掃描（見 `tests/no_second_run_state_test.sh`）；改完跑相關掃描測試。

## 失敗先行測試
新檔 `platform/tests/test_cli_usage_doc.py`，先寫、改字前跑一次確認紅，紅輸出貼進 ledger。不連網、不開資料庫、不執行任何子指令。
- `test_every_top_level_command_is_named_in_the_doc`：`cli.build_parser()` 取頂層子指令名（從 `parser._subparsers._group_actions[0].choices`），逐一斷言在 `cli.__doc__` 有自己的一段（比對規則見裁決 5）。**現在紅**（缺 `oauth`、`dataset`）。
- `test_every_nested_command_is_named_in_the_doc`：同法遞迴取第二層名稱（`token new`、`ce create`、`runs offer-cleanup` …），依裁決 5 以群組段落比對、排除 ce（裁決 4）。**現在紅**（至少缺 `offer-cleanup`、`register`、`show`）。
- `test_doc_has_no_dangling_count`：說明不得含 `four commands`。**現在紅**。
- 對照組（必須一直綠）：`serve`、`web`、`token`、`mcp`、`rebuild` 仍在說明；既有 `test_cli.py`、`test_dataset_cli.py` 不改、保持綠。
- 手動檢查（記 ledger，verifier 重跑）：`git diff -U0 origin/v3 -- platform/abf_platform/cli.py` 只有第 2 行；兩分支 `ast.parse` 後只有該字串常數不同，其他 AST 節點相等。

## 完成標準（done when）
- 前三則新測試改前紅、改後綠；對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含 `cli.py` 一行與新測試檔；AST 比對輸出貼上。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：單檔 `ABF_PYTEST_TARGETS=tests/test_cli_usage_doc.py bash tests/platform_test.sh`（相對於 `platform/`）；全套在 WSL 跑 `tests/run_all.sh`，超過 10 分鐘上限，用 `run_in_background` 等。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- cli.py 同時是多份其他計畫的目標檔（dataset-cli-launch、temp-password 等），合併時只會在第 2 行相撞；若撞到，以對方為準重做第 2 行。

## 不做
- 不改任何子指令的行為、旗標、help 文字（`help=` 部分）。
- 不把說明改成自動從 parser 生成（那是行為改動，另件）。
- 不需要 migration（沒有資料變動）。

## 裁決
1. **「the four commands of the hand-off record」要補成正確數字，還是刪？** **定案：刪。**數字再寫一次只會再過期，測試以名稱比對取代數量。
2. **`--help` 開頭變長算不算可見行為變動？** **定案（developer-agent 10-29 預檢改判）：算，`--help` 是使用者看得到的 CLI 文字，所以本件列 B 級（網頁外），流程照舊、自合。** 除了第 2 行字串，任何指令行為不變。
3. **專長守則**：專案沒有 docs 守則，用 backend 守則；其中對等性／跨使用者／確認管道 TC 對純說明文字不適用，verifier 寫「不適用＋理由」即可，不必硬湊。
4. **（合約退回 10-29）`ce ...` 怎麼辦？** **定案 (b)**：第 2 行的 `ce ...` 原樣保留（它是刻意的「看 `ce --help`」），第二層測試**明確排除 ce**，測試內寫一行理由註解。
5. **（合約退回 10-29）比對規則**：以「群組段落」為單位。把 `__doc__` 去掉開頭 `abf-platform:` 後用 ` | ` 切成段；每段第一個字是群組名，其餘部分取第一個空白前的 `a|b|c` 清單、去掉 `[...]` 方括號內容後用 `|` 切成名稱集合（例：`user add|cloud-cap|passwd [--temporary]|welcome` → {add, cloud-cap, passwd, welcome}）。斷言：每個頂層指令都有一段；每個有子指令的群組（ce 除外），其 parser 的每個第二層名稱都在該段的名稱集合裡。所以 `dataset list` 漏寫不會因 `pat list` 而誤綠。第 2 行的新寫法必須符合此格式（例：`oauth revoke USER`、`dataset register|list|show`、`runs assign|offer-cleanup`）；`runs assign RUN --user NAME` 這種帶參數寫法改成 `runs assign|offer-cleanup`（參數看各自 --help）。
6. **（合約退回 10-29）手動項**：git diff／AST 比對由 verifier 驗收時重跑計畫所列指令即可，不需 docs/TESTING.md 步驟。可接受。

### developer-agent 確認（2026-10-29）
證據已在 origin/v3@68de6de 抽查屬實（cli.py:2、:781–784、:833、:841–855）。

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
