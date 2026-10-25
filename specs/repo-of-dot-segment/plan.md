---
id: repo-of-dot-segment
title: releases.repo_of 拒絕「.」段與結尾換行
tier: A
kinds: backend
lane: L-release-fix
base: v3（origin/v3，2026-10-25）
source: release-lookup-job 規劃者發現（裁決二第 4 條）；developer-agent 讀碼查證 releases.py:12-27
---

# repo-of-dot-segment

## 目標
`releases.repo_of` 現在放行 `./x`、`x/.`、`./.` 這種含單點段的名字（只擋 `..`），而且 `_REPO` 用 `$`，會放行結尾帶一個換行的 `nf-core/ampliseq\n`。這些名字之後會被拿去組 GitHub 網址（release-lookup-job），必須在這一層就擋掉。對使用者：亂打的管線名稱會得到清楚的拒絕，不會變成奇怪的網址。

## 維護者原話（verifier 出題用）
- 「Pin an exact pipeline revision, never a branch」（repo `CLAUDE.md` Working conventions）——名稱與版本都要是確定、乾淨的值。
- 2026-10-25「好，放寬」：站台代理讀公開 GitHub 檔（release-lookup-job 的前提）；名稱檢查是這條放寬的安全邊界。

## 範圍：檔案（3 個）
- `platform/abf_platform/releases.py`（只改 `_REPO` 與 `repo_of`）
- `platform/tests/test_releases.py`（只在 `test_t2_repo_of_rejects` 的參數清單加新案例；不刪不改既有案例）
- `specs/repo-of-dot-segment/ledger.md`

## 作法（決定）
1. `_REPO` 的結尾 `$` 改成 `\Z`。
2. `repo_of`：`p.split("/")` 的任一段等於 `.` 或 `..` → 拒絕（原本只看 `..`）。訊息不變。
3. 其他行為不變：`ampliseq` → `nf-core/ampliseq`；`owner/name` 原樣。

## 失敗先行測試
`test_t2_repo_of_rejects` 參數加：`"./x"`、`"x/."`、`"./."`、`"."`（補成 `nf-core/.`）、`"nf-core/ampliseq\n"`、`"ampliseq\n"`。現在這六個都會被放行（紅）。`test_t1_repo_of_accepts` 不動，仍要綠；另加 `"a.b/c.d"`（段內含點但不是單點段）要被接受。

## 完成標準（done when）
- 上述新案例全綠，`test_releases.py` 其他案例不變且綠；全套綠。
- `git diff --name-only` 只含範圍 3 個檔。

## 環境事實
- 純函式、不連網；`test_scope.py` TC-061／TC-071 掃 `abf_platform/`，本片不加任何 import。

## 不做
- 不碰 release-lookup-job 的代理端檢查（那片自己另補）。
- 不改錯誤訊息文字。

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
