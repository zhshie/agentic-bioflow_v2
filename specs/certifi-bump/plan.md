---
id: certifi-bump
title: 把 platform/constraints.txt 的 certifi 從 2026.7.22 升到 >= 2026.10.18，讓 security 工作流的 pip-audit 轉綠（PYSEC-2026-4320）
tier: C
kinds: backend
risk: M
lane: L-certifi-bump
branch: fix/certifi-bump
dir: specs/certifi-bump
base: v3
source: chase session 2026-11-05 轉述維護者「建議升版，C 級」；v3 上 `security` 工作流的 pip-audit job 紅：certifi 2026.7.22 有 PYSEC-2026-4320，2026.10.18 修正
---

# certifi-bump

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/certifi-bump/plan.md`。**只處理本任務**。risk M：範圍不含 `.github/`、`platform/abf_station/`；只動依賴清單與一個新測試。

## 目標
把平台的釘版依賴 certifi 升到 2026.10.18 或更新，讓 `pip-audit -r platform/constraints.txt` 不再回報 PYSEC-2026-4320，`security` 工作流的 pip-audit job 轉綠。行為不變：只換一個函式庫的版本號。

## 維護者原話（verifier 出題用）
1. 「建議升版，C 級」（chase session 於 2026-11-05 轉述）→ 升版而不是加 ignore：`platform/pip-audit-ignore.txt` 不動（維持「Empty on purpose」）；C 級＝不碰保護路徑、不改行為。對應 TC：constraints 的 certifi ≥ 2026.10.18；ignore 檔 byte 不變。

## 範圍：檔案
- `platform/constraints.txt`：第 5 行 `certifi==2026.7.22` 改成 `certifi==2026.10.18`（或當時 PyPI 上 >= 2026.10.18 的最新版；executor 在 ledger 記下實際選的版本）。其餘行不動。
- 新測試：`platform/tests/test_certifi_pin.py`。
- `git grep -n -i certifi origin/v3` 實測：`platform/constraints.txt:5` 是唯一的釘版處。`platform/pyproject.toml`、`platform/setup.py`、任何 requirements*、docs 都沒有 certifi 釘版（其餘命中只是 certificate 一詞或 nf-core-modules.json 的描述文字，**不准動**）。executor 開工前再用 `git grep -n -i certifi origin/v3 -- ':!platform/abf_platform/data'` 確認一次；若有新增釘版處，一併改並寫進 ledger。
- 不准改：`.github/`、`platform/pip-audit-ignore.txt`、`platform/abf_station/`、其他依賴行。

## 作法
1. 先寫測試、確認紅（見下節），再改 `constraints.txt`，再確認綠。
2. `constraints.txt` 第 1 行註解寫「What pip resolved on Python 3.10.6 …」：只改 certifi 那一行，不重新生成整份檔（避免夾帶其他依賴升版）。
3. 不在 `pyproject.toml` 新增 certifi 直接依賴（它是傳遞依賴，只靠 constraints 釘住，與現況一致）。
4. 不需要 migration（沒有資料結構或資料內容變動）。
5. 副作用要在 PR 說明寫一句：`tests.yml` 的快取鍵含 `hashFiles('platform/constraints.txt', …)`，改檔後 CI 會重建一次 venv 快取，屬預期。

## 失敗先行測試
`platform/tests/test_certifi_pin.py`（先寫、現在會紅；用 `PLATFORM_DIR` 的取法比照既有測試，如 `test_guidance.py:463` 讀 `constraints.txt` 的做法）：
- `test_constraints_pins_certifi_at_or_above_fix`：讀 `platform/constraints.txt`，用逐行解析（不是子字串搜尋）找 `certifi==<版本>` 或 `certifi>=<版本>`；斷言有且恰好一行；版本以 `.` 切成整數元組，與 `(2026, 10, 18)` 比較，必須 `>=`。現在是 `(2026, 7, 22)` → 紅。
- `test_certifi_version_parser_compares_numerically`：解析函式對 `2026.7.22` < `2026.10.18`（數字比較，不是字串比較；字串比較會把 `7` 排在 `10` 之後而誤判）。這條確保上一條不是靠字典序僥倖綠。
- `test_pip_audit_ignore_stays_empty`：`platform/pip-audit-ignore.txt` 除了 `#` 開頭的註解與空行外沒有任何有效行（維護者選的是升版，不是忽略）。現在就綠，要一直綠。

## 允許的斷言（既有測試）
`git grep -n 'certifi' origin/v3 -- platform/tests tests` 的結果：**沒有任何既有測試提到 certifi 版本字串**（0 筆含 `2026.7.22`）。因此沒有需要更新的既有斷言；若 executor 發現有，列進 ledger 且只准把舊版本字串改成新版。
會讀 `constraints.txt` 的既有測試（只做「某字不在檔裡」或釘別的行，與 certifi 無關，必須維持綠、不得改）：
- `platform/tests/test_azure_upload.py:835`（不含 azure／boto3／botocore）、`test_catalogue.py:462`（不含 yaml）、`test_chat_tools.py:322`（不含 anthropic）、`test_cloud_upload.py:642`（不含 google）、`test_k8s_launch.py:782`（不含 kubernetes）。新版號不含這些字。
- `platform/tests/test_guidance.py:463`（`mcp==2.3.0` 那一行還在）。
- `tests/platform_test.sh:247`（以 constraints 安裝）、`tests/testing_web_doc_test.sh:12`、`tests/ci_security_workflow_test.sh:116`（釘住 `pip-audit -r platform/constraints.txt --no-deps --disable-pip` 這串字，本案不改 workflow）。

## 完成標準（done when）
- 三條新測試綠；`tests/run_all.sh` 全綠（環境紅依 README 通例）。
- `git diff --stat` 只有 `platform/constraints.txt`（1 行改）、`platform/tests/test_certifi_pin.py`（新）、`specs/certifi-bump/*`。
- `platform/pip-audit-ignore.txt`、`.github/` 的 diff 為空（貼 `git diff --stat origin/v3 -- .github platform/pip-audit-ignore.txt` 空輸出進 ledger）。
- 若本機有網路：`pip-audit -r platform/constraints.txt --no-deps --disable-pip` 無 PYSEC-2026-4320（無網路就在 ledger 註明，以 PR 上 `security` 工作流為準）。

## 環境事實
- 失敗現象：v3 上 `security.yml`（pip-audit job，約 39～56 行）跑 `pip-audit -r platform/constraints.txt --no-deps --disable-pip` 與 `pip-audit ./platform …`，因 certifi 2026.7.22 有 PYSEC-2026-4320 而紅；修正版為 2026.10.18。
- `docs/TESTING.md:1043`：`security` 工作流不是 required check，所以這不是合併阻擋，而是把已知紅轉綠。
- `constraints.txt` 是整份「pip 解析結果」快照；certifi 是 httpx／相關套件的傳遞依賴，升到較新的同系列版本不改 API。
- PITFALLS 已查，無相符項（`docs/PITFALLS.md` 與 `docs/solutions/`：後者不存在；前者對 certifi、constraints、pip-audit、PYSEC 無條目，僅有與此無關的「pin」字樣）。

## 不做
- 不改 `.github/` 任何檔、不改 `platform/pip-audit-ignore.txt`。
- 不順手升級 `constraints.txt` 的其他套件、不重新生成整份檔。
- 不新增 certifi 為 `pyproject.toml` 直接依賴。
- 不改文件（沒有文件提到 certifi 版本）。

## 裁決
1. 整套測試一律 `run_in_background`＋等待迴圈跑 `tests/run_all.sh --timeout 900`。
2. 合約規則：計畫未明寫的細節由 verifier 依專長守則與既有慣例自訂預期值，不以「計畫未寫」退回；test-case.md 全文放進回傳值，條數 ≤ 25。
3. 本任務是 backend 依賴升版、沒有動作層／寫入路徑；專長守則的對等性、跨使用者、確認管道項目對本案「不適用」，閱卷於「專長守則檢查」一行寫明理由即可。

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
