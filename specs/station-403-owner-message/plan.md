---
id: station-403-owner-message
title: 站台代理收到平台的 403 時，依平台實際回的訊息分辨「token 對不上代理名稱」與「這個代理屬於另一位使用者」，不再一律叫他去查名稱
tier: A
kinds: backend
lane: L31-station-403
branch: fix/station-403-owner-message
base: origin/v3（行號取自 origin/v3@d1fa55e，executor 開工前先 `git fetch origin v3`，再用 `git show origin/v3:<檔>` 重查）
source: PR #248（owner-binding）新增了平台端第二種 403「This agent belongs to another user」，站台端的錯誤訊息沒跟著改；2026-10-29 清理掃描列出
---

# station-403-owner-message

> 只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
站台代理（`abf-station`）被平台回 403 時，目前一律印「the token was made for another agent name」。但平台有兩種 403：token 做給別的代理名稱，和這個代理名稱已經屬於另一位使用者（#248 加的）。第二種情況下，使用者照訊息去改代理名稱或重做 token 是走錯方向。改成依平台回的訊息分辨，各給一句說清楚「發生什麼事、該怎麼辦」的白話；分辨不出時給一句涵蓋兩種原因的誠實說法。401 的訊息不變。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」。（這件只改錯誤文字，不改任何流程、狀態碼或停止行為。）
- 專長守則（backend）：「錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL」；「密鑰、token、密碼不得出現在日誌或任何回應中」。
- 平台的既有原則：回給呼叫者的話不透露別人是誰（`test_owner_tokens.py:123` 斷言輸出不含 `alice`）。新訊息同樣不得出現任何使用者名稱或 token。

## 範圍：檔案（只准改這些）
- `platform/abf_station/agent.py`（`_rejected` 與它的三個呼叫點）
- `platform/tests/test_station_rejected.py`（**新檔**，pytest 自動收進 `tests/`）
- **不准碰**：`platform/abf_platform/agents.py` 與其他平台端檔案（見裁決 1）、`web/`、`launch.py`、`.github/`、`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.claude-plugin/plugin.json`、任何既有測試。

## 作法
- **證據**（origin/v3@d1fa55e）：
  - `agent.py:97-101` `_rejected(status)`：401 → 一句「token 錯或被撤銷，用 `abf-platform agent-token new <name>` 重做」；其他任何狀態（實際上只會是 403）→ 固定「the platform refused this agent (%d): the token was made for another agent name.」
  - 三個呼叫點都已拿到回應內容但沒用：`agent.py:128-129`（`hello`，有 `status, body`）、`:150-151`（`answer`，`status, _ =` 把內容丟了）、`:180-181`（`loop`，有 `status, body`）。`Client.post` 回 `(status, parsed JSON dict)`，解析失敗時是 `{}`（`agent.py:63-67`）。
  - 平台端 403 有**兩種**，都是 `{"message": ...}`、沒有 code 之類的欄位：`agents.py:151-152` `wrong_name()` 回「This token was made for another agent name」；`agents.py:159-160` 的 `OwnerMismatch` 回「This agent belongs to another user」。`hello`（`:170-175`）、`poll`（`:188-193`）、`result`（`:214` 一帶）都可能回其中一種。
  - 沒有現成測試鎖 `_rejected` 的文字（在 `platform/tests` 搜尋 `another agent name`、`refused this agent` 沒有命中）；平台端兩句話之一被 `test_owner_tokens.py:18` 的 `MESSAGE = "This agent belongs to another user"` 鎖著。
- **決定**：
  1. `_rejected(status, body=None)`：`body` 是回應的 dict。401 照舊、文字逐字不變。
  2. 403 時取 `body.get("message")`（不是字串就當沒有），**只拿它做比對，絕不整句印出來**（平台回的內容算外部輸入）：
     - 含 `belongs to another user`（不分大小寫）→ 擁有者不符的話。
     - 否則含 `another agent name`（不分大小寫）→ 名稱不符的話。
     - 兩者都不含（沒有 message、格式不認得、或將來平台改了字）→ 涵蓋兩種原因的話，**不亂猜**。
  3. 三句固定的話（要點，措辭由 executor 定，但三條都必須含狀態碼 403、一個原因、一個下一步，且彼此不同）：
     - 擁有者不符：「平台拒絕了這個代理 (403)：這個代理名稱已經屬於另一位使用者，你的 token 是用另一位使用者的身分做的。請用屬於這個代理的使用者重新做 token（`abf-platform agent-token new <name> --user <那位使用者>`），或換一個沒人用過的代理名稱。」
     - 名稱不符：「平台拒絕了這個代理 (403)：這個 token 是為另一個代理名稱做的，和你啟動時的 --name 對不上。請把 --name 改成做 token 時用的名字，或用目前的名字重做一個 token。」
     - 不確定：「平台拒絕了這個代理 (403)：可能是 token 是為另一個代理名稱做的，也可能是這個代理名稱已經屬於另一位使用者。請先確認 --name 和做 token 時的名字一樣；若一樣，請確認 token 是用擁有這個代理的使用者做的。」
     （與同檔其他訊息風格一致即可；不得出現 token 的值、使用者名稱、堆疊或路徑。）
  4. 三個呼叫點都傳 `body`；`answer` 的 `status, _ =` 改成 `status, body =`。除此之外 `Rejected` 的流程（停止代理、`say("abf-station stopped: ...")`）完全不動。
- **平台端不改**（裁決 1）。

## 失敗先行測試
新檔 `platform/tests/test_station_rejected.py`，先寫、改程式前跑一次確認紅，紅的輸出貼進 ledger。
- 以真實平台的兩句話當輸入（不抄字串、直接向平台要，防兩邊漂移）：用 `test_owner_tokens.py` 同款的 `World`／`Duo` 與 `TestClient`（見該檔 `:40-46` 的 `_client`／`_hello`）造出兩種真 403——(a) 用屬於 alice 的 token 對 bob 已擁有的代理名稱 hello；(b) 在 body 的 `name` 填與 token 不同的名稱 hello——取得各自的 `response.json()`。
- `test_owner_mismatch_is_not_called_a_name_problem`：把 (a) 的 `(403, json)` 餵給 `agent._rejected(403, body)`；斷言文字指向「另一位使用者」，且**不含** `another agent name` 與 `另一個代理名稱`。**現在紅**（現在一律說名稱）。
- `test_name_mismatch_still_says_name`：(b) 的結果文字指向 `--name`，且不含「已經屬於另一位使用者」。對照組，必須一直綠（確保改完沒把名稱不符弄丟）。
- `test_unknown_403_covers_both_causes`：`_rejected(403, {})`、`_rejected(403, {"message": "something new"})`、`_rejected(403, {"message": 7})`、`_rejected(403, None)` 的文字都同時指向 `--name` 與「另一位使用者」兩個原因。**現在紅**。
- `test_texts_do_not_leak`：用含假 token 值 `abf_SECRET` 與使用者名 `alice` 的 message 餵進去，輸出不含 `abf_SECRET`、不含 `alice`、不含整句 message（只比對、不回貼）。必須一直綠。
- `test_every_call_site_passes_the_body`：用 monkeypatch 把 `Client.post` 換成回 `(403, {"message": "This agent belongs to another user"})`，分別驅動 `Agent.hello()`、`Agent.answer(1, "done", {})`、`Agent.loop()`（先讓 hello 過、poll 回 403），三個都丟 `agent.Rejected`，其訊息都屬於「擁有者不符」那一句。**現在紅**（三個呼叫點現在都說名稱）。
- 對照組（必須一直綠）：`_rejected(401)` 與 `_rejected(401, {"message": "x"})` 的文字與 origin/v3 逐字相同（斷言等於 base 的那句）；403 時 `Rejected` 仍使代理停止（`agent.run` 對 `Rejected` 印 `abf-station stopped: ...`，不重試、不進 backoff）；既有 `test_owner_tokens.py`、`test_station_platform.py` 全綠。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」）：在 `origin/v3` 與本分支各跑 `test_station_rejected.py`、`test_owner_tokens.py`、`test_station_platform.py`，貼輸出。

## 完成標準（done when）
- 新測試改前紅（標「現在紅」的）、改後綠；對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含 `agent.py` 與新測試檔；`_rejected` 的 401 分支逐字未動；沒有任何既有測試被改；兩分支輸出比對貼上。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_station_rejected.py bash tests/platform_test.sh`（相對於 `platform/`）。
  - 全套：在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束；測試還在背景跑時不准交報告。
- 測試輔助：`World`（`human_harness.py`）、`Duo`（`owner_harness.py`）、`Inproc`（`station_harness.py`）；`test_owner_tokens.py:18-46` 示範如何造出兩種 403。`Client.post` 在 `abf_station/agent.py:49`，monkeypatch 它即可，不需要真的開網路。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不改平台端的任何回應、狀態碼、訊息文字（`agents.py` 一個字都不碰）。
- 不改 401 的訊息、不改 `Rejected` 的停止行為、不新增重試。
- 不把平台回的 message 原文印到終端機或日誌。
- 不動 `abf-platform agent-token new` 的 CLI 訊息（`cli.py:125` 已經正確）。
- 不改 docs；沒有資料變動，**不需要 migration**。

## 裁決
1. **平台有沒有給可靠的分辨欄位？**——沒有。兩種 403 都只有 `{"message": 文字}`（`agents.py:152`、`:160`），沒有 `code`。**定案：站台端用訊息文字中的固定片語分辨，認不出就說兩種原因都可能；平台端不改。** 為什麼不順手加一個 `code` 欄位：那雖然只加不改，但要碰 `agents.py` 的三條路徑與 `test_owner_tokens.py` 鎖著的回應，且舊版站台對新版平台、新版站台對舊版平台都得相容（所以站台端仍要有「認不出」那一句）。A 級不擴大範圍；將來要更穩，另開一件讓平台加 `code`，那時再把站台端改成優先看 `code`。
2. **為什麼用片語比對而不是整句相等？**——整句相等遇到平台微調標點就整個掉到「不確定」那句；片語（`belongs to another user`、`another agent name`）夠窄、不會互相誤中，掉到不確定那句也仍是誠實的。兩個片語由測試直接向真平台要回應來驗證，漂移會被抓到。
3. **為什麼擁有者不符的訊息可以說「屬於另一位使用者」？**——平台自己的回應就說了這句，沒有多透露；但絕不補上是哪位（`test_owner_tokens.py:123` 的原則）。

### developer-agent 確認（2026-10-29）
證據已對 origin/v3@d1fa55e 逐行核對：`agent.py:97-101`、三個呼叫點 `:128-129`／`:150-151`／`:180-181`，平台端 `agents.py:151-152`、`:159-160`。A 級：只改錯誤文字，不放寬任何安全網。

### developer-agent 確認（2026-10-29 12:4x）
- `abf-platform agent-token new <name> --user <user>` 已在 origin/v3 `platform/abf_platform/cli.py:735` 核對存在，建議文字可用。
- 平台端 403 加 `code` 欄位不在本件，另列後續。

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
