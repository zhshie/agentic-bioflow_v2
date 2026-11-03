# 測試案例：k8s-kubeconfig-paste-rule（平台端拒收貼進文字欄位的 kubeconfig 密鑰行）

**規格**：`specs/k8s-kubeconfig-paste-rule/plan.md`（A 級任務沒有獨立 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

名詞：「密鑰行」＝ kubeconfig 檔裡 `client-certificate-data:`、`client-key-data:`、`certificate-authority-data:` 這三種後面接一長串 base64 內容的行。`MARK` ＝ 測試用的假密鑰值，在測試檔裡用片段拼接而成（追蹤的檔案裡不會有整段登入字串）。「拒收」＝ `compute_envs.create()` 丟出 `CEError`（建立失敗的錯誤）。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

新測試全放在新檔 `platform/tests/test_k8s_paste_rule.py`（以下簡稱「新檔」）。「驗證方式：自動」＝該檔內有一條測試，註解寫明本 TC 編號。

## User Story 1 — 三種 kubeconfig 密鑰行貼進文字欄位會被拒收（優先度 P1）

維護者原話（PR #272 交接）：「a description containing `client-certificate-data:`, `client-key-data:` or `certificate-authority-data:` lines is not blocked by the current rules. The fix … makes the rules stricter.」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；維護者原話；失敗先行測試第 1 組 | 例外 | 運算環境（compute environment）建立表單；`description` 為 `"clusters:\n- cluster:\n    client-certificate-data: " + MARK + "\n"` | 呼叫 `compute_envs.create` | 被拒收；錯誤訊息含 `description`（講出是哪個欄位）；訊息不含 `MARK` | 自動：新檔 |
| TC-002 | 同上 | 例外 | 同 TC-001，鍵名換成 `client-key-data` | 呼叫 `create` | 被拒收；訊息含 `description`；不含 `MARK` | 自動：新檔 |
| TC-003 | 同上 | 例外 | 同 TC-001，鍵名換成 `certificate-authority-data` | 呼叫 `create` | 被拒收；訊息含 `description`；不含 `MARK` | 自動：新檔 |
| TC-004 | 作法「所有文字欄位已走同一道檢查」；失敗先行測試第 2 組 | 例外 | 同一段文字（三個鍵名各一次）放進 `config.nextflowConfig` | 呼叫 `create` | 三次都被拒收；訊息含 `nextflowConfig`；不含 `MARK` | 自動：新檔 |
| TC-005 | 同上 | 例外 | 同一段文字（三個鍵名各一次）放進 `config.environment[0].value`（環境變數的值），變數名取一般名稱（如 `SOMEVAR`） | 呼叫 `create` | 三次都被拒收；訊息含 `environment[0].value`；不含 `MARK` | 自動：新檔 |
| TC-006 | 作法「不分大小寫、行首縮排不限」；失敗先行測試第 3 組 | 例外 | `description` 含 `"    Client-Key-Data: " + MARK`（大小寫混用、前面縮排） | 呼叫 `create` | 被拒收；訊息含 `description`；不含 `MARK` | 自動：新檔 |
| TC-007 | 作法「`\s*:`」；失敗先行測試第 3 組 | 例外 | `description` 含 `"client-key-data : " + MARK`（冒號前有空格） | 呼叫 `create` | 被拒收；訊息含 `description`；不含 `MARK` | 自動：新檔 |
| TC-008 | 作法「鍵名在行中間」；失敗先行測試第 3 組 | 例外 | `description` 為一句話後面接 `client-key-data: ` + `MARK`（鍵名不在行首） | 呼叫 `create` | 被拒收；訊息含 `description`；不含 `MARK` | 自動：新檔 |
| TC-009 | 裁決 5（不要求冒號後一定有值，YAML 的值可能換行） | 例外 | `description` 為 `"client-key-data:\n  " + MARK`（冒號後立刻換行，值在下一行） | 呼叫 `create` | 被拒收；訊息含 `description`；不含 `MARK` | 自動：新檔 |
| TC-010 | 作法「不新增拒絕訊息，走既有 `CREDENTIAL_ADVICE`」；專長守則（錯誤訊息說明原因與處理方式） | 例外 | 同 TC-002 | 呼叫 `create`，取錯誤訊息 | 訊息就是既有那句：欄位路徑 + 空格 + `CREDENTIAL_ADVICE`（「像憑證… 憑證要放在代理那邊，平台只記名字」），沒有新增別種訊息 | 自動：新檔 |
| TC-011 | 目標「不會原樣存進 platform.db」；失敗先行測試第 4 組 | 例外 | 乾淨的 `platform.db`；對三個鍵名各做一次被拒收的 `create` | 讀 `platform.db` 的位元組 | `MARK.encode()` 不在其中 | 自動：新檔 |
| TC-012 | 同上 | 例外 | 同 TC-011，先記下 `ip.rows()`（或等價查詢）的列數 | 對三個鍵名各做一次被拒收的 `create`，再查一次 | 列數沒有增加 | 自動：新檔 |
| TC-013 | 專長守則（密鑰不得出現在日誌或任何回應中） | 例外 | 同 TC-002，同時擷取日誌（logging）與標準輸出／標準錯誤 | 呼叫 `create`（被拒收） | 擷取到的日誌、輸出與錯誤訊息都不含 `MARK` | 自動：新檔 |
| TC-014 | 失敗先行測試第 5 組 | 功能 | 無 | 對 `compute_envs.looks_like_credential` 直接餵三個鍵名各加冒號的字串（如 `"client-key-data:"`） | 三個都回傳 True | 自動：新檔 |
| TC-015 | 裁決 4（舊紀錄不回掃；之後 `update` 才依新規則檢查） | 例外 | 先正常建立一筆環境 `k1`；之後 `compute_envs.update` 把 `description` 改成含 `client-key-data: ` + `MARK` 的行 | 呼叫 `update` | 被拒收（訊息含 `description`、不含 `MARK`）；`k1` 原本的描述沒有被改、`platform.db` 裡沒有 `MARK` | 自動：新檔 |

## User Story 2 — 正常描述與一般文字結果不變（優先度 P1）

計畫目標：「正常描述（包含在文字裡提到 certificate 這個字）結果不變」。以下六句各放進 `description`，`create()` 皆必須成功。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 對照組 1；不能誤擋既有「token」規則 | 功能 | `description="a context for the lab, token-free"` | 呼叫 `create` | 建立成功，`status == "creating"` | 自動：新檔 |
| TC-017 | 對照組 2 | 功能 | `description="the certificate is kept on the agent"` | 呼叫 `create` | 建立成功，`status == "creating"` | 自動：新檔 |
| TC-018 | 對照組 3（鍵名後面沒有冒號） | 功能 | `description="certificate-authority-data lives in the kubeconfig on the agent"` | 呼叫 `create` | 建立成功，`status == "creating"` | 自動：新檔 |
| TC-019 | 對照組 4（只有鍵名） | 功能 | `description="client-key-data"` | 呼叫 `create` | 建立成功，`status == "creating"` | 自動：新檔 |
| TC-020 | 對照組 5 | 功能 | `description="my client certificate, signed by the lab CA"` | 呼叫 `create` | 建立成功，`status == "creating"` | 自動：新檔 |
| TC-021 | 對照組 6（冒號前不是三個鍵名） | 功能 | `description="data: certificate"` | 呼叫 `create` | 建立成功，`status == "creating"` | 自動：新檔 |

## User Story 3 — 既有規則不退步，改動只有一條樣式（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 失敗先行測試「既有規則不退步」 | 例外 | `description` 為 `"to" + "ken: " + MARK`（片段拼接的 token 行） | 呼叫 `create` | 仍被拒收；訊息不含 `MARK` | 自動：新檔 |
| TC-023 | 完成標準；失敗先行測試「既有規則不退步」 | 功能 | 本分支 | 跑 `ABF_PYTEST_TARGETS=tests/test_k8s_ce.py bash tests/platform_test.sh` | 全綠，包含 TC-034～044 | 自動：`platform/tests/test_k8s_ce.py` |
| TC-024 | 同上；裁決確認段「`test_model_key_refusal.py:36` 的不是密鑰對照組必須維持綠」 | 功能 | 本分支 | 跑 `ABF_PYTEST_TARGETS=tests/test_model_key_refusal.py bash tests/platform_test.sh` | 全綠，包含 `test_tc011_ordinary_text_is_not_a_credential`（`disk-usage`、`task-runner-42`、`ask-me`、`sk-`+19 個 a 都不是憑證） | 自動：`platform/tests/test_model_key_refusal.py` |
| TC-025 | 完成標準「整個 `platform/tests` 套件全綠」 | 功能 | 本分支，WSL 內 `tests/run_all.sh` | 跑全套 | 全綠（已知環境紅依 dev-plans README「通例：已知環境紅」逐條列在 ledger，不得多於該清單） | 自動：`tests/run_all.sh` |
| TC-026 | 不做「不加 `token:` 規則」 | 不在範圍 | 本分支 | 看 `git diff origin/v3...HEAD -- platform/abf_platform/compute_envs.py` | 新增的那條 `re.compile` 只比對三個 kubeconfig 鍵名，不含 `token`；`:121` 那條原樣未動 | 手動：閱卷者看 diff（TESTING.md 無對應步驟，見總覽疑問 1） |
| TC-027 | 不做「base64 內容探測」 | 不在範圍 | `description` 為一段約 200 字元、看起來像 base64、但沒有任何鍵名也沒有冒號的文字（如 `"QUJD" * 50`） | 呼叫 `create` | 建立成功，`status == "creating"`（沒有因為「很長的 base64」被拒） | 自動：新檔 |
| TC-028 | 不做「不處理 TC-036（光禿禿的英數字 fake token 形狀像合法憑證名）」 | 不在範圍 | 在 `origin/v3` 與本分支各跑 `test_k8s_ce.py::test_the_credential_is_only_a_name` | 比對兩邊結果 | 兩邊都綠、行為相同（裸 `KTOK` 當 credentialsId 的處置沒有被這件改變），貼進 ledger | 手動：閱卷者看 ledger 的兩分支輸出 |
| TC-029 | 不做「不改 `_check_k8s`、`clean()` 流程，不新增錯誤訊息或函式」；範圍「不准碰」 | 不在範圍 | 本分支 | 看 `git diff origin/v3...HEAD -- platform/abf_platform/compute_envs.py` | 差異只有 `_VALUE_PATTERNS` 清單多一行 `re.compile(...)`；`_check_k8s`、`clean`、`credential_findings`、`looks_like_credential` 本體與 `common.is_secret_name` 無任何差異；沒有新函式、沒有新訊息字串 | 手動：閱卷者看 diff |
| TC-030 | 範圍：檔案（只准改這些）；完成標準「`git diff --stat` 只含範圍列的檔」 | 不在範圍 | 本分支 | `git diff --stat origin/v3...HEAD` | 只有 `platform/abf_platform/compute_envs.py`、`platform/tests/test_k8s_paste_rule.py`、`docs/TESTING.md`，加上 `specs/k8s-kubeconfig-paste-rule/` 下的 ledger；`platform/abf_station/`、`actions/`、`web/`、`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json` 都沒有出現 | 手動：閱卷者看 diff |
| TC-031 | 不做「不需要 migration」；專長守則（資料結構有變動必須附 migration，或明寫不需要的理由） | 不在範圍 | 本分支 | 檢查差異 | 沒有新增 migration 檔、沒有改資料表欄位；計畫已寫「不需要 migration」的理由 | 手動：閱卷者看 diff 與 plan.md |
| TC-032 | 範圍「不改 `test_k8s_ce.py`、`test_model_key_refusal.py` 的任何既有斷言」；閱卷規則（不得弱化既有測試） | 不在範圍 | 本分支 | `git diff origin/v3...HEAD -- platform/tests/` | 除新檔外，`platform/tests/` 底下唯一被改動的既有行是 `test_model_key_refusal.py` tc015 期望清單 `got[6:]` 尾端追加新樣式一條（計畫裁決 6，developer-agent 10-29 改本列）；前面既有項目內容與順序不變，沒有其他既有斷言被改 | 手動：閱卷者看 diff |
| TC-033 | 範圍：`docs/TESTING.md` 第 835 行；裁決 3 | 功能 | 本分支 | `git diff origin/v3...HEAD -- docs/TESTING.md` | 只改第 835 行（第 6 步）那句；原本的「(recorded, no rule added)」換成「已被 `compute_envs._VALUE_PATTERNS` 拒收」一類的白話；其餘行與其他步驟沒變。若 executor 判斷這超出 A 級而沒改，ledger 必須寫明理由（此時本 TC 以該理由視為通過） | 手動：閱卷者看 diff |
| TC-034 | 失敗先行測試「兩分支比對」（專案 CLAUDE.md 校準失敗案例） | 功能 | `origin/v3` 與本分支 | 兩邊各跑 `test_k8s_ce.py`、`test_model_key_refusal.py`、新檔 | ledger 貼出兩邊輸出：`origin/v3` 上新檔只有「會被拒收」的案例（TC-001～015）紅、對照組（TC-016～022、027）綠；本分支三個檔全綠；另貼「改程式前先跑一次、確認紅」的輸出 | 手動：閱卷者看 ledger |
| TC-035 | 裁決 2（共用樣式連帶影響其他呼叫者；要求 ledger 補 grep 證明） | 功能 | 本分支 | 看 ledger | ledger 有一段 grep 輸出，證明 repo 內三個鍵名只出現在 `docs/TESTING.md` 與 `specs/k8s-ce/`（及本任務的 specs），沒有既有測試或範例資料用到；若找到合法用例，ledger 寫 BLOCKED | 手動：閱卷者看 ledger，並自行重跑同一個 grep |
| TC-036 | 不做「不回掃舊紀錄、不寫 migration」；裁決 4 | 不在範圍 | 本分支 | 檢查差異與 ledger | 差異裡沒有任何掃描或改寫既有紀錄的程式；ledger 有一行記著「已存在的舊紀錄不回掃，之後 `update` 才會依新規則被拒收」 | 手動：閱卷者看 diff 與 ledger |
| TC-037 | 作法「測試字串一律用片段拼接」 | 功能 | 本分支 | 在新檔搜尋完整的登入字串寫法（如連續的 `token:` 加值、整段 `MARK` 常數） | 新檔裡沒有整段連續的登入字串；`MARK` 與 token 行都是用字串片段拼出來的 | 手動：閱卷者 grep 新檔 |

## 憲法與安全網

這件改的是平台的「憑證守門」。Safety Net 第五條：「平台絕不存下送進來的憑證——不寫進資料庫或資料夾」（Check：`platform/tests/test_secrets.py` 等）。專案另有「絕不放寬安全網」的派工指示。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-038 | Safety Net：平台不存憑證（`.specify/memory/constitution.md:208-213`） | 功能 | 本分支 | 跑 `platform/tests/test_secrets.py`（含 `test_tc040_*`、`test_tc042_*`、`test_tc_i03_*`） | 全綠；它點名的檢查仍涵蓋被改的程式（`credential_findings` 路徑沒變）。新樣式讓 kubeconfig 密鑰行也落在這條規則之內，其資料庫不含值由 TC-011／012 證明 | 自動：`platform/tests/test_secrets.py` |
| TC-039 | 絕不放寬安全網（派工指示） | 功能 | `origin/v3` 與本分支的 `_VALUE_PATTERNS` | 逐條比對 `compute_envs.py` 第 116～126 行附近原有的 11 條樣式 | 原有 11 條一字不差、順序不變，只多出一條；沒有任何一條被刪、被縮窄或被改寬鬆以外的方式動過 | 手動：閱卷者看 diff |

## 專長守則（backend）對照

- 錯誤訊息與日誌 TC：TC-001～010（錯誤含原因與處理方式、不含值）、TC-013（日誌與輸出不含值）。
- migration TC：TC-031（計畫明寫不需要 migration，閱卷者核對）。
- 對等性、跨使用者、確認管道三類：**不適用**——這件沒有新增任何使用者動作、路由或寫入路徑，只在既有共用檢查多一條樣式；TC-029／030 的差異檢查證明沒有新增動作層函式或路由。
