---
id: cloud-cap-empty-rates-doc
title: docs/CLOUD.md 說「上限擋得住本月已用滿」，但價目表是空的時候這句不成立；改文件並用測試釘住
tier: A
kinds: backend
lane: L47-cloud-doc-truth
branch: fix/cloud-cap-empty-rates-doc
base: origin/v3@82a49e17
source: 2026-10-30 清理掃描（人工讀 cloud_cost.py 與 docs/CLOUD.md 對照）
---

# cloud-cap-empty-rates-doc

> 只有計畫、沒有程式。A 級（文件＋測試，不改任何執行期行為）→ verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
`docs/CLOUD.md` 告訴管理者「價目表目前是空的……上限只擋得住『沒設上限』『上限 0』『本月已用滿』」。照 `cloud_cost.py` 的寫法，價目表是空的時候，每一個 run 的花費都算不出來，「本月已用」永遠是 0 美元，所以「本月已用滿」這一條根本不會觸發。管理者照文件把上限設成 5 美元，會以為累積到 5 美元就會被擋，實際上永遠不會。把文件改成實話，並用一支測試讓「文件說的」和「程式做的」不能再分家。**這片只改文件與測試，不改 `cloud_cost.py` 的任何行為。**

## 維護者原話（verifier 出題用）
- 沒有可引用的逐字原話（本片來自清理掃描，不是維護者新提的需求）。
- 本次派工指示（2026-10-30）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。
- 既有、可引用的文字依據（verifier 用它出題，不是原話）：`docs/CLOUD.md:43`「價目表目前是空的，所以今天每一次預估都是『無法預估』」；`platform/tests/test_cloud_cost.py:425`（TC-136）的註解「裁決四 10, 13」。

## 範圍：檔案（只准改這些）
- `docs/CLOUD.md`（只動第 19 行與第 43 行附近兩句，其餘一字不動）
- `platform/tests/test_cloud_cost.py`（只新增測試；不刪不改既有斷言）
- **不准碰**：`platform/abf_platform/cloud_cost.py` 及其他程式、`platform/abf_platform/data/cloud_rates.json`（價目表本身，由 `cloud-rates-fill` 另案處理）、`specs/`（歷史紀錄，雖然 `specs/cloud-cost-wire/plan.md:23,162` 與 `specs/cloud-cost/test-case-overview.md:28` 有同樣說法，不改）、`web.py`、`mcp_server.py`、`jobs.py`、`build.py`、`launch.py`、`compute_envs.py`、`tests/platform_upgrade_test.sh`。

## 作法
- **證據（origin/v3@82a49e17）**：
  - `docs/CLOUD.md:19`：「上限只擋得住『本月已用滿』，**擋不住『這一次太貴』**。」
  - `docs/CLOUD.md:43`：「價目表目前是空的，所以今天每一次預估都是『無法預估』；上限只擋得住『沒設上限』『上限 0』『本月已用滿』。」
  - `platform/abf_platform/cloud_cost.py:85` 算出 `empty`（價目表沒有任何區域），`:104` 把它記成未知原因「尚未填入價目」，所以每個 task 都沒有金額。
  - `cloud_cost.py:195-205` `month_used`：沒有金額的 run 只計入 `unknown_runs`，不加進 usd，所以 `spent` 在價目表為空時恆為 0。
  - `cloud_cost.py:249-293` `cap_problem`：判斷「已用滿」是 `round(spent, 6) >= round(cap, 6)`；`spent` 恆為 0 時，只有 `cap == 0` 會成立。
  - 既有測試 `platform/tests/test_cloud_cost.py:425` `test_with_the_empty_shipped_rates_the_cap_still_works` 只證明「上限 5 美元時放行、上限 0 時擋」，沒有證明「累積用量會擋」；`:150` `test_the_shipped_rates_file_is_valid_and_empty` 釘住價目表現在是空的（`entries == []`）。
  - 文件測試 `test_the_cloud_document_says_what_it_must`（約 `:772`）要求文件含「第一次」「擋不住」「只含運算」「同一個 pipeline」「最近一次成功」「不會自動停止正在跑的雲端工作」「只會擋下新的送出」「cloud_rates.json」等字，改文件時全部要保留。
  - 以上是讀程式得到的推論；**executor 必須先用特徵化測試（見下）在 v3 上親眼跑出結果**。若實際行為與上述不同（例如空價目表時用量其實有被累計），停下來回報，不要硬改文件。
- **決定**：
  1. 第 19 行改成：上限擋不住「這一次太貴」；並補一句「價目表填入之前，連『本月已用滿』也擋不住（見下方價目表一節）」。「第一次」「擋不住」兩個詞保留。
  2. 第 43 行改成：價目表目前是空的，所以今天每一次預估都是「無法預估」，而且每個 run 的實際花費也算不出來，「本月已用」一律當 0 美元（有未計價的 run 時只會標「至少」）；因此上限今天只擋得住「沒設上限」「上限 0」，**「本月已用滿」要等價目表填入後才會生效**。
  3. 不新增、不刪除其他任何文件句子。
  4. 新測試的判斷依據是 `data/cloud_rates.json` 的 `regions` 是否為空：空 → 文件必須含第 2 點的新句子，且不得把「本月已用滿」列為今天擋得住的項目；非空（將來 `cloud-rates-fill` 填了價）→ 這條文件斷言不成立也不報錯，改由特徵化測試自己的前提檢查決定（見下），避免日後填價目表時被這支測試誤擋。

## 失敗先行測試
先寫、先紅，輸出貼 ledger：
1. `test_empty_rates_never_count_used_money_so_the_monthly_cap_cannot_fill`（特徵化，進 repo）：沿用檔內 `_scene`／`w.ask`／`w.cap`／`w.used` 與 `_cc().load_rates(SHIPPED)`。情境：上限 5.0；替使用者放兩筆已結束的 Google Batch run（用檔內既有輔助方式，讓它們在空價目表下是未計價）；斷言 `w.used(...)` 的金額為 0、`unknown_runs >= 1`，且 `w.ask(w.alice, rates=rates) is None`。前提檢查：先斷言 `rates` 確實沒有任何區域，否則 `pytest.skip("price list is filled; this pins the empty-list behaviour")`。這條在 v3 上應該**直接綠**（它描述現況）；若紅，代表我的推論錯，回報。
2. `test_cloud_doc_does_not_claim_the_monthly_cap_works_while_the_price_list_is_empty`（進 repo）：價目表為空時，找出含「價目表」與「空的」的那一行，斷言它不再把「本月已用滿」列為今天擋得住的項目，並含「要等價目表填入後才會生效」（或第 2 點定稿的同義固定片語，executor 取一個固定字串、測試與文件逐字相同）。這條在 v3 上**必紅**（文件現在就是列出「本月已用滿」），紅輸出貼 ledger。
3. 改文件後第 2 條轉綠；第 1 條維持綠；`test_the_cloud_document_says_what_it_must` 與 `test_the_shipped_rates_file_is_valid_and_empty` 維持綠。
- **突變證明（一次性、貼 ledger，不進 repo）**：在 worktree 暫時把 `docs/CLOUD.md:43` 還原成舊句子，確認第 2 條紅；再還原，確認綠。最終 diff 不得含 `cloud_cost.py`。

## 完成標準（done when）
- 兩條新測試綠；第 2 條改文件前的紅輸出與第 1 條的綠輸出已貼 ledger。
- `py -3 -m pytest platform/tests/test_cloud_cost.py` 全綠；全套綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含 `docs/CLOUD.md` 與 `platform/tests/test_cloud_cost.py`；文件只動兩處；既有斷言沒有被刪改。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」。
- 這些測試在行程內跑、不連網、不花錢、不碰任何雲端或 HPC；Windows 用 `py -3 -m pytest platform/tests/test_cloud_cost.py`，或依專案慣例在 WSL。
- 全套：從 Git Bash 且工作目錄為純 ASCII：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`；超過 10 分鐘一律 `run_in_background`，用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 等；背景還在跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不改 `cloud_cost.py` 的行為（不讓 `cap_problem` 在價目表為空時改成擋）。
- 不填價目表（`cloud-rates-fill`）。
- 不改 `specs/` 裡的歷史說法。
- 不新增依賴、不新增 CLI 旗標。

## 裁決
1. **文件改實話，還是讓程式在價目表為空時「寧可擋」？** 後者會改使用者看得到的行為（本來放行的送出會被擋），不是 A 級，且牽涉管理者要不要接受「價目表填好前雲端幾乎送不出去」。**建議：這片只改文件；另開 C 級任務請維護者裁決是否 fail closed。** 此為提議，未經維護者定案。
2. **要不要順手補 `specs/` 的同樣說法？** specs 是當時的規格紀錄，改了會讓歷史和程式對不上。**建議：不改。**
3. **新測試依賴「價目表為空」會不會在填價目表後造成誤擋？** 已設計成價目表非空時略過（skip），不擋 `cloud-rates-fill`。**建議：照此設計。**
4. （2026-10-30 預檢第 2 條）**範圍加兩處**：`docs/CLOUD.md` 第 66 行（「目前出貨的價目表是空的…上限只擋得住…『已用滿』這幾種」）與 `docs/TESTING.md` 第 621 行（"with the empty price list only 0 or 'already used up' can bite"）是同一句錯話的副本，一併改成實話；「其餘一字不動」改為「除這四處外一字不動」。cap_problem 的行號以實際內容為準（約 249–282）。
5. （預檢第 5 條；10-30 08:5x 因 BLOCKED(contract) 改寫，取代原文）固定字串**唯一**定為「要等價目表填入後才會生效」，刪掉「或第 2 點定稿的同義固定片語」。決定 2 的第 43 行定稿照原文保留。機器斷言改成：`docs/CLOUD.md` 中每一行同時含「價目表」與「空的」者，**若含「已用滿」，就必須同一行也含「要等價目表填入後才會生效」**；且全文至少一處含該固定字串。`docs/TESTING.md` 第 621 行改成英文同義句，必含固定片語 "only takes effect once the price list is filled in"；斷言：該檔中每一行同時含 "empty price list" 與 "used up" 者，必須同一行也含這個固定片語。
6. （預檢第 10 條）失敗先行 #1 與 #2 一律同一個守衛：**若** `cloud_rates.json` 含任何區域 → `pytest.skip`（價目表填好後這幾句本來就該改寫）；**否則**才執行斷言。不准「先斷言再 skip」。
7. （10-30 08:5x）**範圍與完成標準以裁決 4 為準**：可改的檔＝`docs/CLOUD.md`（第 19、43、66 行三處）、`docs/TESTING.md`（第 621 行一處）、`platform/tests/test_cloud_cost.py`（只新增）；`git diff --stat` 應只含這三個檔。前文「範圍」與「完成標準」兩節若寫兩個檔，以本條為準。第 66 行定稿：若提到「已用滿」，句中必含「要等價目表填入後才會生效」，其餘措辭由 executor 決定、對齊第 43 行。第 19 行不加機器斷言，由驗收者讀文件判斷。

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
