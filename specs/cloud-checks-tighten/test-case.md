# 測試案例：收緊三處雲端安全檢查（cloud-checks-tighten）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
No spec.md exists for this task (tier A, plan only); the plan and the maintainer's dispatch words quoted in it are the ground truth.
-->

**規格**：`specs/cloud-checks-tighten/plan.md`（A 級小改，沒有 spec.md）　**總覽**：`test-case-overview.md`

這件事的三項改動都「只讓檢查更嚴」：合法的輸入行為不能變，只有本來就不該通過的輸入現在會被擋。所以每一項都配「該被擋的」和「必須維持放行的對照組」。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了（含「合法輸入維持不變」）。
- **例外**：不該通過的輸入，系統怎麼反應（拒絕）。
- **不在範圍**：計畫「不做」或「不准碰」的事；確認真的沒做。

維護者的原話（計畫引用）對應：

- 「s3 bucket 名稱含 `..` 在 `cloud_store._parse` 沒被擋，另外三處都擋，要一致」→ TC-001 至 TC-012
- 「`AWS_FORBIDDEN_ENV` 只擋固定名單，Azure 是按前綴擋，AWS 也照 Azure 做」→ TC-020 至 TC-036
- 「`test_azure_launch.py` 一則斷言的 `, f.name` 被吞進註解，失敗時沒檔名」→ TC-040 至 TC-043

「手動」欄的意思：由閱卷人看 `git diff` 與 `specs/cloud-checks-tighten/ledger.md`（這件事的工作紀錄）逐項核對；計畫禁止改 `docs/*`，所以不寫進 `docs/TESTING.md`。

## User Story 1 — s3 bucket 名稱含 `..` 一律拒絕（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 項目 1；維護者原話 1 | 例外 | 有一個 s3 位置，bucket 名稱中間有兩個點 | 解析 `s3://lab..bucket/uploads/a.fq.gz`（`parse_s3`） | 丟出 `CloudPathError`（改前會回 `("lab..bucket", "uploads/a.fq.gz")`，所以改前是紅的） | 自動：`platform/tests/test_aws_upload.py::test_parse_s3_refuses_a_double_dot_in_the_bucket` |
| TC-002 | 項目 1 | 例外 | 同上，名稱是 `a..b` | 解析 `s3://a..b/x` | 丟出 `CloudPathError` | 自動：同上測試 |
| TC-003 | 項目 1 | 例外 | 同上，兩個點在名稱尾端附近 | 解析 `s3://lab-bucket..x/x` | 丟出 `CloudPathError` | 自動：同上測試 |
| TC-004 | 項目 1 對照組 | 功能 | bucket 名稱含單一個點，合法 | 解析 `s3://lab.bucket/uploads/a.fq.gz` | 回 `("lab.bucket", "uploads/a.fq.gz")`，改前改後都一樣 | 自動：同上測試（對照組，全程綠） |
| TC-005 | 項目 1 對照組 | 功能 | bucket 名稱含連字號，合法 | 解析 `s3://lab-bucket/uploads/a.fq.gz` | 回 `("lab-bucket", "uploads/a.fq.gz")`，改前改後都一樣 | 自動：同上測試（對照組，全程綠） |
| TC-006 | 項目 1（`workdir_bucket` 路徑） | 例外 | 一個 AWS 計算環境，`workDir` 是 `s3://lab..bucket/work` | 呼叫 `workdir_bucket` 取 bucket | 丟出 `CloudPathError`（改前會回 `lab..bucket`，所以改前是紅的） | 自動：`platform/tests/test_aws_upload.py::test_workdir_bucket_refuses_a_double_dot_in_an_s3_workdir` |
| TC-007 | 項目 1 對照組 | 功能 | 一個 AWS 計算環境，`workDir` 是 `s3://lab.bucket/work` | 呼叫 `workdir_bucket` | 回 `"lab.bucket"`，改前改後都一樣 | 自動：同上測試（對照組，全程綠） |
| TC-008 | 項目 1「錯誤訊息沿用現有那句」 | 例外 | 一個含 `..` 的 s3 bucket 名稱，和一個本來就被拒的名稱（`s3://AB/x`） | 各解析一次，取出錯誤訊息 | 兩者的錯誤訊息完全相同，就是現有那句「bucket 名稱不正確：要 3 到 63 個字元……」；沒有新的訊息文字 | 自動：加在項目 1 的新測試內 |
| TC-009 | 項目 1「既有測試保持綠」 | 功能 | 既有的 `test_parse_s3_has_the_shape_of_parse_gs`、`workdir_bucket` 相關既有測試 | 改完後跑 `test_aws_upload.py` | 這些既有測試沒被修改、全部通過（含 `parse_gs("s3://lab-bucket/x")` 的訊息不變） | 自動：`ABF_PYTEST_TARGETS=tests/test_aws_upload.py bash tests/platform_test.sh` |
| TC-010 | 項目 1「決定」；完成標準 | 功能 | 完成後的分支 | 看 `git diff` 的 `platform/abf_platform/cloud_store.py` | 只有 `_container_ok` 的 s3 分支那一行邏輯改了，變成 `bool(compute_envs._AWS_BUCKET.match(name)) and ".." not in name`（或等價）；沒有別的邏輯改動 | 手動：看 git diff 與 ledger |
| TC-011 | 項目 1「不動 gs 分支」；不做 1 | 不在範圍 | 完成後的分支 | 看 `git diff` 的 `cloud_store.py` 的 `gs`、`az` 分支，並跑 `parse_gs`、`parse_az` 既有測試 | `gs` 與 `az` 分支那幾行沒變；沒有新增任何針對 gs 的 `..` 檢查；`parse_gs`、`parse_az` 既有測試沒改、保持綠 | 手動：看 git diff；自動：既有 gs、az 測試 |
| TC-012 | 不做 1；範圍「不准碰」 | 不在範圍 | 完成後的分支 | 看 `git diff --stat` | `compute_envs.py`、`abf_station/aws_preflight.py` 沒被改；`abf_station/launch.py` 約 813 行的 bucket 檢查那一行沒被改 | 手動：看 git diff |

## User Story 2 — AWS 環境變數：`AWS_` 開頭一律擋（優先度 P1）

這一組用 `box.bundle(ce=ace(environment=[{"name": <名稱>, "value": "v", "head": True, "compute": False}]))` 的寫法，仿 `test_aws_launch.py` 約 636 行的既有測試。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 項目 2；維護者原話 2 | 例外 | 環境變數清單裡有一個名稱 `AWS_MAX_ATTEMPTS` | 建立送出內容（bundle） | 丟出 `launch.BundleError`（改前通過，所以改前是紅的） | 自動：`platform/tests/test_aws_launch.py::test_every_aws_prefixed_environment_name_is_refused` |
| TC-021 | 項目 2 | 例外 | 名稱 `AWS_RETRY_MODE` | 建立送出內容 | 丟出 `launch.BundleError`（改前是紅的） | 自動：同上測試 |
| TC-022 | 項目 2 | 例外 | 名稱 `AWS_CA_BUNDLE` | 建立送出內容 | 丟出 `launch.BundleError`（改前是紅的） | 自動：同上測試 |
| TC-023 | 項目 2 | 例外 | 名稱 `AWS_REGION`（不在原本 8 個固定名稱裡） | 建立送出內容 | 丟出 `launch.BundleError` | 自動：同上測試 |
| TC-024 | 項目 2（大小寫） | 例外 | 名稱 `aws_profile`（小寫） | 建立送出內容 | 丟出 `launch.BundleError`（改前是紅的） | 自動：同上測試 |
| TC-025 | 項目 2（大小寫） | 例外 | 名稱 `Aws_Whatever` | 建立送出內容 | 丟出 `launch.BundleError` | 自動：同上測試 |
| TC-026 | 項目 2（只有前綴） | 例外 | 名稱 `AWS_`（只有前綴） | 建立送出內容 | 丟出 `launch.BundleError` | 自動：同上測試 |
| TC-027 | 項目 2 對照組 | 功能 | 名稱 `HEAD_ONLY`，head 為真 | 建立送出內容 | 不丟錯，且 `HEAD_ONLY` 被匯出到 head 腳本（既有測試 `test_head_environment_variables_are_exported_and_compute_ones_are_not`，不改、保持綠） | 自動：同上新測試的對照組＋既有測試 |
| TC-028 | 項目 2 對照組 | 功能 | 名稱 `MY_AWS_NOTE`（含 AWS 但不以 `AWS_` 開頭） | 建立送出內容 | 不丟錯 | 自動：同上新測試的對照組 |
| TC-029 | 項目 2 對照組 | 功能 | 名稱 `AWSX`（沒有底線） | 建立送出內容 | 不丟錯 | 自動：同上新測試的對照組 |
| TC-030 | 項目 2「tuple 保留、行為未退步」 | 例外 | `launch.AWS_FORBIDDEN_ENV` 這個清單 | 對清單裡每個名稱各建立一次送出內容 | 每個名稱都丟 `launch.BundleError`；清單本身仍存在、內容仍是原本 8 個名稱 | 自動：`platform/tests/test_aws_launch.py::test_aws_forbidden_env_tuple_is_still_refused_by_name` |
| TC-031 | 項目 2「既有測試不改」 | 功能 | 既有測試裡本來就被擋的 `AWS_SHARED_CREDENTIALS_FILE`、`AWS_ACCESS_KEY_ID`、`TOWER_ACCESS_TOKEN`、`ABF_X` | 改完後跑 `test_aws_launch.py` | 這四個仍被擋；該既有測試沒被修改、保持綠 | 自動：`ABF_PYTEST_TARGETS=tests/test_aws_launch.py bash tests/platform_test.sh` |
| TC-032 | 項目 2「決定」；完成標準 | 功能 | 完成後的分支 | 看 `git diff` 的 `abf_station/launch.py` | 只有 `_check_aws_ce` 環境迴圈那一個 `if` 多了 `or name.upper().startswith("AWS_")`（或等價）；`AWS_FORBIDDEN_ENV` 沒有刪、沒有改內容；`launch.py` 沒有別的邏輯改動 | 手動：看 git diff 與 ledger |
| TC-033 | 項目 2「拒絕訊息沿用現句」 | 例外 | 一個被新規則擋下的名稱（例如 `AWS_MAX_ATTEMPTS`）和一個本來就被擋的名稱（`AWS_ACCESS_KEY_ID`） | 各建立一次送出內容，取出錯誤訊息 | 兩者都是同一句現有訊息「這個變數由送出本身或代理設定，環境不能設……」（只帶變數名稱），沒有新的訊息文字 | 自動：加在項目 2 的新測試內 |
| TC-034 | 不做 2 | 不在範圍 | 完成後的分支 | 看 `git diff` 的 Azure 相關部分與 `_check_aws_ce` | Azure 的固定名單與判斷（約 1014–1015 行）沒改；AWS 沒有新增白名單、沒有新增 `TOWER_ACCESS_TOKEN` 之類的額外名稱 | 手動：看 git diff |
| TC-035 | 不做 4；範圍「不准碰」 | 不在範圍 | 完成後的分支 | 看 `git diff --stat` | `abf_station/aws_preflight.py` 沒被改（約 72 行對 `AWS_CA_BUNDLE` 的放行維持原樣，那是站台自己行程的環境） | 手動：看 git diff |
| TC-036 | 範圍「環境事實」：站台程式碼不得出現小寫單字 `azure` | 功能 | 完成後的分支 | 跑 `tests/test_station_static.py`（含約 46 行的檢查） | 通過；`launch.py` 本次改動沒有新增這個字 | 自動：`ABF_PYTEST_TARGETS=tests/test_station_static.py bash tests/platform_test.sh` |

## User Story 3 — 補回被吞進註解的檔名（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 項目 3；維護者原話 3 | 功能 | `platform/tests/test_azure_launch.py` 的 `test_no_azure_command_that_changes_anything`（約 1109 行） | 看那一行改完的樣子 | 變成 `assert not re.search(r"...", code), f.name      # azure-upload: blob upload and blob show are allowed`：`, f.name` 在 `assert` 運算式內、在 `#` 之前；`#` 之後的註解文字只剩原本那句 | 手動：看 git diff |
| TC-041 | 項目 3「驗證方式」② | 功能 | 一份不進 commit 的暫時副本，把那個正規式換成一定會命中的字串 | 跑那個測試 | 失敗訊息裡看得到被檢查的檔名；這個演練的輸出記在 ledger | 手動：看 ledger |
| TC-042 | 項目 3「正規式與其他部分一字不改」 | 功能 | 完成後的分支 | 看 `git diff` 的 `test_azure_launch.py` | 只動那一行；正規式內容與該檔其他斷言一字未改 | 手動：看 git diff |
| TC-043 | 項目 3 | 功能 | 改完後的分支 | 跑 `test_azure_launch.py` | `test_no_azure_command_that_changes_anything` 與該檔其他測試全部通過 | 自動：`ABF_PYTEST_TARGETS=tests/test_azure_launch.py bash tests/platform_test.sh` |

## 憲法與安全網

這件事動的是兩個「擋壞輸入」的檢查（安全門）。憲法的決策分級裡「只讓安全網更嚴」可由開發主導自合，但前提是不能有任何原本擋得住的形狀被放過（專案過去的退步案例第 1 條：修安全門時縮窄了範圍，三種原本會被擋的形狀漏過去，所有 TC 都過，只有拿舊形狀在兩個分支重跑才發現）。對應憲法第 IV 條「宣稱前先有證據」。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 第 IV 條（證據先於宣稱）；計畫「失敗先行測試」 | 功能 | 項目 1、2 的新測試 | 在改程式前先跑新測試，再改程式後跑 | 改前：TC-001、002、003、006、020、021、022、024 對應的斷言是紅的，紅的輸出貼進 ledger；改後全綠；對照組（TC-004、005、007、027、028、029）改前改後都綠 | 手動：看 ledger（紅的輸出）；自動：新測試改後綠 |
| TC-051 | 安全門不得縮窄（退步案例 1） | 例外 | 基準分支（`origin/v3`）與完成後的分支 | 兩邊各跑一次 `test_aws_launch.py`、`test_aws_upload.py` 裡所有「該被拒絕」的既有案例，包括 `AWS_FORBIDDEN_ENV` 的 8 個名稱、`ABF_` 開頭、`TOWER_ACCESS_TOKEN`、`NXF_LOG_FILE`、不合法的變數名稱、`s3://AB/x`、含控制字元或 `..` 路徑段的位置 | 基準分支擋住的，完成後的分支全部仍擋住；沒有任何一個原本被擋的形狀變成放行 | 自動：兩個分支比對測試結果 |
| TC-052 | 範圍「只准改這些」；不做 | 不在範圍 | 完成後的分支 | 看 `git diff --stat` 與已存在測試的差異 | 只含範圍列出的檔案（`cloud_store.py`、`launch.py`、`test_azure_launch.py`、`test_aws_upload.py`、`test_aws_launch.py`，或例外情況下的 `test_cloud_store_names.py`）和 ledger；沒動 `docs/*`、`compute_envs.py`、`aws_preflight.py`、`clean.py`、`put_upload.py`、`azure_launch.py`；沒有既有測試的斷言被刪除、放寬、跳過或改期望值；沒有改 `spec.md`、`test-case*.md`、constitution | 手動：看 git diff |
| TC-053 | 專長守則（backend）：資料結構不變要寫明不需 migration；不做 3 | 不在範圍 | 完成後的分支 | 看 `git diff` 與計畫 | 沒有新增 migration 檔；沒有新增任何使用者可見的錯誤訊息文字（`cloud_store.py`、`launch.py` 的 diff 裡沒有新的訊息字串）；計畫已明寫「不需要 migration」的理由 | 手動：看 git diff 與計畫「不做」 |
| TC-054 | 憲法「每階段全綠」；完成標準 | 功能 | 完成後的分支，gate 標記為 `GREEN <HEAD sha>`（閱卷人另外核對） | 完整的 `platform/tests` 套件 | 全綠（只有 dev-plans README「通例：已知環境紅」那一條可視同綠） | 自動：`tests/run_all.sh`（在 WSL；由 executor 的 gate 標記證明，閱卷人不重跑全套） |
| TC-055 | 專長守則（backend）：錯誤回應不洩漏密鑰 | 例外 | 環境變數清單裡有一個被擋的名稱，值設成一個辨認得出的字串（例如 `value-marker-123`） | 建立送出內容，取出錯誤訊息 | 錯誤訊息裡有變數名稱，但不含那個值 | 自動：加在項目 2 的新測試內 |
