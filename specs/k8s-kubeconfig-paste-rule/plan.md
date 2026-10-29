---
id: k8s-kubeconfig-paste-rule
title: 平台端拒收貼進文字欄位的 kubeconfig 密鑰行（client-certificate-data／client-key-data／certificate-authority-data）
tier: A
kinds: backend
lane: L38-k8s-paste-rule
branch: fix/k8s-kubeconfig-paste-rule
base: origin/v3（PR #272 k8s-ce 已在內；行號取自 origin/v3@0f69df6fe3bf9ffd9796957d77fd2007dee2a398，executor 開工前用 `git show origin/v3:<檔>` 重查）
source: PR #272 verifier TC-045「需要人看的事」（PR 內文「Follow-ups」：這條由 A 級任務補嚴規則）；docs/TESTING.md:835 寫著「recorded, no rule added」
---

# k8s-kubeconfig-paste-rule

> 只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
使用者把 kubeconfig 內容貼進運算環境的文字欄位時，`client-certificate-data:`、`client-key-data:`、`certificate-authority-data:` 這三種行目前不會被擋（內容是 base64，現有樣式都不吻合），會原樣存進 `platform.db`。補一條樣式，讓這三種行和其他密鑰一樣被拒收、且拒絕訊息不重複該值。正常描述（包含在文字裡提到 certificate 這個字）結果不變。

## 維護者原話（verifier 出題用）
- PR #272 內文（verifier 的 TC-045 交接）：「a description containing `client-certificate-data:`, `client-key-data:` or `certificate-authority-data:` lines is not blocked by the current rules. The fix is an A-tier task that makes the rules stricter.」
- 本次派工指示：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。
- `compute_envs.py:629` 上方註解：「first of all, before any rule that could repeat a value in its message」——拒絕訊息只講欄位路徑、不重複值。
- A 級的前提：只更嚴、合法輸入行為不變；若發現需要改動合法輸入的行為，停下回報 BLOCKED。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/compute_envs.py`（只在 `_VALUE_PATTERNS` 清單多加一條 `re.compile(...)`，約第 115–127 行）
- `platform/tests/test_k8s_paste_rule.py`（**新檔**；不改 `test_k8s_ce.py`、`test_model_key_refusal.py` 的任何既有斷言）
- `docs/TESTING.md`（只改第 835 行那句「recorded, no rule added」，改成「now refused by `compute_envs._VALUE_PATTERNS`」一類的白話；其餘不動。若 executor 認為這超出 A 級，可不改並回報，見裁決 3）
- **不准碰**：`_check_k8s`、`clean()`、`credential_findings`、`looks_like_credential` 函式本體、`common.is_secret_name`、`platform/abf_station/`、`actions/`、`web/`、任何既有測試的既有斷言。

## 作法
- **證據**（origin/v3@0f69df6）：
  - 所有文字欄位已走同一道檢查：`compute_envs.py:629` `bad = [... for b in credential_findings({"description": desc, "credentialsId": cred, "config": config}, "")]`，發現就 `raise CEError("%s %s" % (bad[0], CREDENTIAL_ADVICE))`（`compute_envs.py:630–631`）。k8s 的 `_check_k8s`（`:536`）在這之後才跑，所以 `description`、`credentialsId`、`config.*`（含 `nextflowConfig`、`environment[].value`、任何額外鍵）一次涵蓋；不必在 k8s 分支另加檢查。
  - 現有樣式清單 `_VALUE_PATTERNS`（`compute_envs.py:115–127`）：PEM 私鑰標頭（`:116`）、AWS key（`:117`）、`aws_secret_access_key`（`:118`）、`abf_…`（`:119`）、`export …TOKEN=`（`:120`）、`(password|passwd|secret|api[_-]?key|access[_-]?key|secret[_-]?key|token)\w*\s*[=:]\s*\S`（`:121`）、模型 key、Azure 連線字串。三個 kubeconfig 鍵名都不吻合：`client-key-data` 不是 `api/access/secret key` 的寫法，`certificate-*-data` 根本沒有對應樣式。
  - **`token:` 已有規則**：`:121` 已含 `token\w*\s*[=:]\s*\S`，且 `test_k8s_ce.py:323` `test_a_kubeconfig_pasted_anywhere_is_refused_and_not_repeated`（TC-037～040）與 `:309–320`（TC-034～036）已用 `"to"+"ken: "+KTOK` 驗過。所以本件**不加** `token:`。
  - 這道檢查另被這些地方共用（改樣式會同步影響）：`actions/__init__.py:395`、`actions/datasets.py:307,326,349,361`、`actions/uploads.py:178`。見裁決 2。
- **決定**：在 `_VALUE_PATTERNS` 加一條不分大小寫的樣式，要求鍵名後面緊接冒號（行首縮排不限）：`re.compile(r"\b(?:client-certificate-data|client-key-data|certificate-authority-data)\s*:", re.I)`。不要求冒號後一定有值（YAML 的值可能換行）。只比對鍵名加冒號，所以文字裡單獨提到這些字、或提到 certificate 這個字，都不吻合。
  - 不新增拒絕訊息，走既有 `CREDENTIAL_ADVICE`；不新增函式。
  - 測試字串一律用片段拼接（照 `test_k8s_ce.py:27–28` 的作法），讓追蹤的檔案裡沒有整段登入字串。

## 失敗先行測試
全放在新檔 `platform/tests/test_k8s_paste_rule.py`，先寫、改程式前跑一次確認紅，紅的輸出貼進 ledger。fixture 與 `create`／`refused` 輔助照 `test_k8s_ce.py:36–79` 的寫法在新檔內自備（用 `Inproc`、`compute_envs.create`；不 import `test_k8s_ce`）。
- 對三個鍵名各一組（`client-certificate-data`、`client-key-data`、`certificate-authority-data`），放進 `description`，內容為 `"clusters:\n- cluster:\n    " + key + ": " + MARK + "\n"`：`refused()` 回傳的訊息含 `description`、不含 `MARK`。**現在紅**（現在會建立成功）。
- 同一段分別放進 `config.nextflowConfig`、`config.environment[0].value`：訊息各含欄位名、不含 `MARK`。**現在紅**。
- 大小寫與縮排變體：`"    Client-Key-Data:"`、`"client-key-data :"`（冒號前有空格）、鍵名在行中間。**現在紅**。
- 拒收後 `MARK.encode()` 不在 `platform.db` 的位元組裡，且 `ip.rows()`（或等價查詢）沒有新增列。**現在紅**。
- `looks_like_credential` 直接測：三個鍵名加冒號為 True。**現在紅**。
- 對照組（必須一直綠）：`description="a context for the lab, token-free"`；`"the certificate is kept on the agent"`；`"certificate-authority-data lives in the kubeconfig on the agent"`（鍵名後無冒號）；`"client-key-data"`（只有鍵名）；`"my client certificate, signed by the lab CA"`；`"data: certificate"`——`create()` 皆回 `status == "creating"`。
- 既有規則不退步：`test_k8s_ce.py`（含 TC-034～044）、`test_model_key_refusal.py` 全綠；`token: XXXX` 仍被拒（用片段拼接）。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」）：在 `origin/v3` 與本分支各跑 `test_k8s_ce.py`、`test_model_key_refusal.py`、新檔，貼輸出；新檔在 origin/v3 上預期只有上述「現在紅」的案例紅，對照組綠。

## 完成標準（done when）
- 新測試改前紅、改後綠；對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含「範圍」列的檔；`compute_envs.py` 只多一條 `re.compile`；沒有既有測試被改弱；兩分支輸出比對貼上。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_k8s_paste_rule.py bash tests/platform_test.sh`（相對於 `platform/`）。
  - 全套：在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束；測試還在背景跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不加 `token:` 規則（`compute_envs.py:121` 已涵蓋）。
- 不處理 TC-036（光禿禿的英數字 fake token 形狀像合法憑證名）——PR #272 另列為記錄事項，不在本件。
- 不改 `_check_k8s`、`clean()` 的流程，不新增錯誤訊息或函式，不讀取 kubeconfig 檔。
- 不做 base64 內容探測（例如「很長的 base64 就拒收」）：容易誤傷合法輸入，超出 A 級。
- 不需要 migration：沒有資料結構變動；已存在的舊紀錄不回掃（`update` 重新驗證時才會依新規則檢查，見裁決 4）。

## 裁決
以下皆為**提案**，由 developer-agent 確認或改判。
1. **樣式放哪裡？** 提案：加進共用的 `_VALUE_PATTERNS`，不在 k8s 分支另寫。理由：所有文字欄位已經走這一條（`compute_envs.py:629`），單一來源最不容易漏。
2. **共用樣式會連帶影響 datasets／uploads／actions 的訊息過濾嗎？** 會（`datasets.py:307,326,349,361`、`uploads.py:178`、`actions/__init__.py:395` 呼叫同一函式）。提案：接受——只有含「這三個鍵名加冒號」的字串才會多被擋，那本來就不該出現在樣本表格儲存格、路徑或回報訊息。要求 executor 在 ledger 補一句 grep 證明沒有既有測試或範例資料含這三個鍵名。若找到合法用例 → BLOCKED 回報。
3. **要不要順手改 `docs/TESTING.md:835`？** 提案：改（一句，把「no rule added」更新為已拒收），否則文件會說謊。若認為文件不屬 A 級範圍，可拆出去，不影響程式部分。
4. **既有的舊紀錄怎麼辦？** 提案：不回掃、不寫 migration。副作用要明講：之後有人 `update` 一筆描述裡已含這些行的舊紀錄，會因新規則被拒收，這正是想要的行為，並在 ledger 記一行。
5. **要不要要求冒號後面一定有值？** 提案：不要。YAML 的值可能換行，只比對「鍵名＋冒號」，較不容易漏，且正常文字不會出現這種形式。

### developer-agent 確認（2026-10-29）
裁決 1–5 全部照提案定案。已在 origin/v3@0f69df6 核對：`looks_like_credential` 的呼叫者是 `actions/__init__.py:395`、`actions/datasets.py:307,326,349,361`、`actions/uploads.py:178`（提案寫的 `uploads.py` 路徑少了 `actions/`）；repo 內這三個鍵名只出現在 docs/TESTING.md:835 與 specs/k8s-ce/，沒有程式或測試資料用到，所以不會誤擋合法輸入。`platform/tests/test_model_key_refusal.py:36` 的「不是密鑰」對照組必須維持綠。A 級：只收緊。

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
