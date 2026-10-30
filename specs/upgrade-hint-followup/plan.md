---
id: upgrade-hint-followup
title: 升級腳本的點名提示改指向真的存在的文件段落；拿掉一條不論結果都過關的測試行
tier: A
kinds: backend
lane: L43-upgrade-hint
branch: fix/upgrade-hint-followup
base: origin/v3@108bfdff（#281 已合併；executor 開工前用 `git show origin/v3:<檔>` 重查行號）
source: PR #281 verifier「需要人看的事」兩點
---

# upgrade-hint-followup

> 只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
`deploy/platform-upgrade.sh` 在代理人沒重新連上時印的提示，叫人去看「docs/TESTING.md 的 403 一節」，但 TESTING.md 沒有這樣命名的段落。改成指向真的存在、教人重發 token 的段落；並加一條測試，讓提示裡引用的段落名一定存在於該文件。另外 `tests/platform_upgrade_test.sh` 的 TC-U27 是一行無條件 `ok`，什麼都沒檢查，拿掉它。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。
- PR #281 的目的（他 10-29 nano4 403 事件後）：升級後沒連回來的代理人要「當場點名」，並提示用 `abf-platform agent-token` 修。

## 範圍：檔案（只准改這些）
- `deploy/platform-upgrade.sh`（只改第 136 行左右那一句提示文字裡的段落名）
- `tests/platform_upgrade_test.sh`（新增一條測試；刪掉 TC-U27 那個 if/else 區塊）
- **不准碰**：`platform/` 底下任何檔、`docs/TESTING.md` 的標題（不准為了讓提示成立去改文件標題）、其他測試檔、`.github/`。

## 作法
- **證據**（origin/v3@108bfdff）：
  - `deploy/platform-upgrade.sh:136`：`…（abf-platform${sp}agent-token；docs/TESTING.md 的 403 一節）…`
  - `docs/TESTING.md:793` 標題 `## Owner binding follow-up (owner-binding)`；`:798` 第 2 步「Reissue the old tokens…check that its hello is now refused (403), then `abf-platform agent-token revoke <name>` and `abf-platform agent-token new <name> --user <U>`…」——這是現有唯一教人處理 403、重發 token 的段落。
  - `docs/OPERATIONS.md:114-116` 是 `agent-token` 指令表。
  - `tests/platform_upgrade_test.sh:228-231`：TC-U27 在沒設 `ABF_UPGRADE_SKIP_PLATFORM_TEST` 時直接 `ok`，沒有執行任何檢查。
- **決定**：提示改成「docs/TESTING.md 的「Owner binding follow-up」一節第 2 步」，其餘字不動（代理人名單、`agent-token`、看日誌都保留）。

## 失敗先行測試
加進 `tests/platform_upgrade_test.sh`，先寫、改腳本前跑一次確認紅，紅的輸出貼進 ledger。
- 新測試：從 `deploy/platform-upgrade.sh` 抓出提示裡「docs/TESTING.md 的「…」一節」引號內的段落名，斷言 `docs/TESTING.md` 有一行 `## ` 開頭的標題含這個名字。**現在紅**（現在的提示沒有引號內段落名，或名字是「403」找不到）。
- 對照：既有的點名測試（名單、結束碼 1、不含 token）全部維持綠。
- TC-U27 區塊刪除後，整支 `tests/platform_upgrade_test.sh` 仍全綠；ledger 記刪除前後的 ok 數差正好 1。

## 完成標準（done when）
- 新測試改前紅、改後綠；`bash tests/platform_upgrade_test.sh` 全綠；全套 `tests/run_all.sh` 全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含範圍兩個檔；腳本只改一句提示；除 TC-U27 外沒有任何既有斷言被刪或放寬。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」。
- 單檔：在 WSL repo 根目錄 `bash tests/platform_upgrade_test.sh`。
- 全套：從 Git Bash 且工作目錄為純 ASCII：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`；超過 10 分鐘一律 `run_in_background`，用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 等；背景還在跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不改等待秒數、名單邏輯、結束碼。
- 不在 TESTING.md 新增「403」段落（另一件事；這片只修指標）。

## 裁決
1. **拿掉 TC-U27 算不算放寬安全網？** 不算：它是無條件 `ok`，從來沒檢查過任何東西；真正的保護是 CI 跑 `platform_test.sh`。**定案：刪除。**
2. **提示指向 TESTING.md 還是 OPERATIONS.md？** TESTING.md 的 Owner binding 第 2 步有完整步驟（先確認 403、revoke、new、重啟）；OPERATIONS.md 只有指令表。**定案：指 TESTING.md 那一節。**

### developer-agent 確認（2026-10-29 21:4x）
證據已在 origin/v3@108bfdff 逐行核對；裁決如上。

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
