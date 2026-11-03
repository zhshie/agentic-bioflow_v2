# 測試案例：Kubernetes 計算環境類型（能建立、驗證、存放、唯讀預檢；不送出、不花錢、不寫叢集）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Every row can be judged without reading code.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/k8s-ce/plan.md`（本任務沒有 spec.md，計畫即規格；計畫末尾「裁決」1～14 與本文衝突時以裁決為準：裁決 12 把 `platform/tests/test_azure_upload.py` 納入「必須更新的既有斷言」C 表；裁決 13 把 base 改為 `origin/v3@e79a555`；裁決 14 規定 `context` 存在檢查是「整行相等」）　**總覽**：`test-case-overview.md`

名詞先講白：
- **Kubernetes（K8s）環境**：一個已經存在的 Kubernetes 叢集裡的一個命名空間，加一塊事先建好的共用儲存（PVC）。本任務只「登記並檢查」它，不能拿它來跑分析。
- **站台代理**：裝在某台機器上、替平台去做事的小程式。K8s 的環境由「平台主機上的那一個代理」做檢查，使用者自己什麼都不用裝。
- **預檢**：建好環境後，代理用 `kubectl`（Kubernetes 官方命令列工具）做一連串「只看不改」的檢查：設定合不合規、kubeconfig 檔讀不讀得到、`context` 在不在檔裡、PVC 存在且是 `Bound`（已綁定）、存取模式含 `ReadWriteMany`、（有設時）service account 存在。全過才是 `available`（可用）。
- **kubeconfig**：Kubernetes 的連線設定檔，內含連線位址與登入憑證。它只放在代理那台機器上；資料庫只記一個憑證**名字**。
- **context**：kubeconfig 裡的一組「連到哪個叢集、用哪個身分」的名字。**PVC**：叢集裡的一塊共用儲存。**service account**：叢集裡 pod 用的身分，可不填。
- **假 runner／假 which**：測試用的替身，假裝執行了 `kubectl`、假裝有沒有裝 `kubectl`，不碰網路、不花錢。
- **KTOK**：測試用的假登入字串，一律用字串拼接組出（`"MARKER" + "KUBETOK" + "A" * 40`），不得在任何檔案裡寫出完整字面（`tests/credentials_stay_in_settings_test.sh` 會掃全 repo）。`KCFG` 是含 KTOK 的假 kubeconfig 片段（`"apiVersion: v1\nkind: Config\nusers:\n- user:\n    " + "to" + "ken: " + KTOK + "\n"`）。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」。

「驗證方式」欄的「同檔」＝`platform/tests/test_k8s_ce.py`；括號內 `test_…` 是計畫已列的測試函式名（供 executor 對照），標「新增」的是本合約多出的情形（計畫沒列函式名，要在同檔新增或併入指定函式）。每個自動測試要在註解寫出它的 TC 編號。常數沿用計畫：`CTX="lab-context"`、`NS="lab-ns"`、`PVC="lab-pvc"`、`MOUNT="/workspace"`、`WORKDIR="/workspace/work"`、`SA="lab-sa"`、`CRED="k8s-lab"`；`good_config()` ＝ context、namespace、storageClaimName、workDir 四鍵；建立時代理名 `a1`。

## User Story 1 — 管理者能建立一個 Kubernetes 環境，設定不合規會被當場擋下（優先度 P1）

維護者原話（plan.md 引 `memory/PLAN-abf-v3-replan-2026-10.md`）：「**C-5** Azure Batch／K8s：同模式」（第 169 行）→ 照 AWS／Azure 的模式：類型常數、設定鍵規則、憑證檔在代理側、預檢唯讀、launch 另做。「10-21，他定：雲端優先於畫布；雲端用戶不裝站台代理。」→ 預檢由平台主機上的代理做。交辦原話：「create + free read-only preflight only … NO launching, no cost, no writes to the cluster」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話 C-5；作法 1、2 | 功能 | 一個在線的代理 `a1` | 管理者用 `good_config()` 加 `serviceAccount=lab-sa` 建立 `k8s-platform` 環境 | 建立成功；狀態 `creating`；訊息含「waiting for the first preflight」；欄位名與值沒有被憑證偵測誤傷 | 自動：同檔（`test_a_valid_k8s_environment_is_created_as_creating`） |
| TC-002 | 作法 2 `storageMountPath` 預設 | 功能 | 同 TC-001，但沒給 `storageMountPath` | 建立 | 存下的設定裡 `storageMountPath` 是 `/workspace`（自動補上，與 Nextflow 預設一致） | 自動：同檔（同上） |
| TC-003 | 作法 2 `workDir` 正規化 | 功能 | 同 TC-001，`workDir` 給 `/workspace/work/`（結尾有斜線） | 建立 | 存下的 `workDir` 是 `/workspace/work`（結尾斜線去掉） | 自動：同檔（同上） |
| TC-004 | 作法 2 `serviceAccount` 選填 | 功能 | 同 TC-001，給 `serviceAccount=lab-sa` | 建立後讀回設定 | `serviceAccount` 存為 `lab-sa` | 自動：同檔（同上） |
| TC-005 | 作法 2 必填 | 例外 | 設定齊全但缺 `context` | 建立 | 被拒；錯誤訊息點名 `context` | 自動：同檔（`test_required_settings_and_agent`） |
| TC-006 | 作法 2 必填；裁決 2 | 例外 | 設定齊全但缺 `namespace` | 建立 | 被拒；訊息點名 `namespace`（不會悄悄用 `default` 命名空間） | 自動：同檔（同上） |
| TC-007 | 作法 2 必填 | 例外 | 設定齊全但缺 `storageClaimName` | 建立 | 被拒；訊息點名 `storageClaimName` | 自動：同檔（同上） |
| TC-008 | 作法 2 必填 | 例外 | 設定齊全但缺 `workDir` | 建立 | 被拒；訊息點名 `workDir` | 自動：同檔（同上） |
| TC-009 | 作法 2「agent 必填」；原話「雲端用戶不裝站台代理」 | 例外 | 設定齊全但沒有 agent | 建立 | 被拒；訊息含「需要指定一個站台代理」 | 自動：同檔（同上） |
| TC-010 | 作法 10「K8s 必須明寫 --agent」 | 例外 | 線上剛好只有一個代理 | 命令列 `ce create --platform k8s-platform` 其餘齊全但不寫 `--agent` | 仍被拒（K8s 環境必須明寫 `--agent`，不會自動挑那唯一的代理） | 自動：同檔（新增，併入 `test_required_settings_and_agent`） |
| TC-011 | 作法 2 `context` 規則 | 功能 | 無 | 分別以 `lab-context`、`gke_proj_zone_name`、`arn:aws:eks:eu-west-1:123456789012:cluster/x` 型字串（用字串拼接組出）當 `context` 建立 | 三者都通過（含 `:`、`/`、`@`、`_`、`.` 的自動產生名稱合法） | 自動：同檔（`test_context_rules`） |
| TC-012 | 作法 2 `context` 規則 | 例外 | 無 | 分別以 `""`、`a b`、`a; b`、`-x`、含換行的字串當 `context` 建立 | 每一個都被拒，訊息點名 `context` | 自動：同檔（同上） |
| TC-013 | 作法 2 `namespace` 規則 | 功能 | 無 | 以 `lab-ns` 當 `namespace` 建立 | 通過 | 自動：同檔（`test_namespace_and_names_follow_dns_rules`） |
| TC-014 | 作法 2 `namespace` 規則 | 例外 | 無 | 分別以 `Lab`、`-a`、`a-`、64 個字、`a_b` 當 `namespace` | 每一個都被拒，訊息點名 `namespace` | 自動：同檔（同上） |
| TC-015 | 作法 2 `storageClaimName`／`serviceAccount` 規則 | 功能 | 無 | 分別以 `lab-pvc`、含 `.` 的名字（如 `a.b-c`）、64 個字、253 個字的合法名稱當 `storageClaimName` 與 `serviceAccount` | 全部通過（這兩個比 namespace 寬：允許 `.`、長度到 253） | 自動：同檔（同上） |
| TC-016 | 作法 2 `storageClaimName`／`serviceAccount` 規則 | 例外 | 無 | 分別以 `Lab`、`-a`、`a-`、`a_b`、254 個字當 `storageClaimName` 與 `serviceAccount` | 每一個都被拒，訊息點名該鍵 | 自動：同檔（同上） |
| TC-017 | 作法 2 `workDir` 規則 | 功能 | 無 | 以 `/workspace/work`、`/workspace/a/b/` 當 `workDir`（掛載點為預設 `/workspace`）建立 | 兩者通過 | 自動：同檔（`test_workdir_must_be_inside_the_mount`） |
| TC-018 | 作法 2「不可等於掛載點」 | 例外 | 掛載點 `/workspace` | `workDir` 設為 `/workspace` | 被拒，訊息點名 `workDir` | 自動：同檔（同上） |
| TC-019 | 作法 2「必須在掛載點底下」 | 例外 | 掛載點 `/workspace` | `workDir` 設為 `/data/work` | 被拒，訊息點名 `workDir` | 自動：同檔（同上） |
| TC-020 | 作法 2「絕對 POSIX 路徑」 | 例外 | 無 | 分別以 `work`、`s3://b/x` 當 `workDir` | 每一個都被拒 | 自動：同檔（同上） |
| TC-021 | 作法 2 `path_problem` | 例外 | 無 | 分別以 `/workspace/../x`、含控制字元的路徑當 `workDir` | 每一個都被拒 | 自動：同檔（同上） |
| TC-022 | 作法 2「以 `storageMountPath + "/"` 開頭」 | 例外 | 掛載點 `/workspace` | `workDir` 設為 `/workspace2/work`（字首相同但不在掛載點底下） | 被拒（比對的是 `/workspace/` 整段，不是只比字首） | 自動：同檔（新增，併入同函式） |
| TC-023 | 作法 2 `storageMountPath` 選填 | 功能 | 無 | `storageMountPath=/mnt/vol` 加 `workDir=/mnt/vol/w` 建立 | 通過，存下的掛載點是 `/mnt/vol` | 自動：同檔（同上） |
| TC-024 | 作法 2「必須在掛載點底下」 | 例外 | 無 | `storageMountPath=/mnt/vol` 加 `workDir=/workspace/w` | 被拒（不在自訂掛載點底下） | 自動：同檔（同上） |
| TC-025 | 作法 2 `storageMountPath` 絕對路徑 | 例外 | 無 | `storageMountPath` 設為 `mnt`（相對路徑） | 被拒，訊息點名 `storageMountPath` | 自動：同檔（同上） |
| TC-026 | 作法 2「maxvCpus、spot 不收；未知鍵拒收」 | 例外 | 無 | 分別在設定裡多放 `spot`、`maxvCpus`、`region`、`cluster`、`foo` | 每一個都被拒 | 自動：同檔（`test_unknown_keys_are_refused`） |
| TC-027 | 作法 2 未知鍵訊息句型 | 例外 | 同 TC-026 | 讀被拒的訊息 | 訊息含 `unknown setting for a Kubernetes environment`，並列出已知鍵清單 | 自動：同檔（同上） |
| TC-028 | 作法 2「全部錯誤一次列出」 | 例外 | 無 | 同時把 `context`、`namespace`、`workDir` 三個鍵都設錯 | 一則訊息裡同時點名這三個鍵 | 自動：同檔（`test_all_errors_are_listed_at_once_and_values_are_cut`） |
| TC-029 | 作法 2「被拒的值最多顯示 60 字」 | 例外 | 無 | `context` 設為 200 個字的壞值 | 訊息裡顯示的那個壞值不超過 60 字 | 自動：同檔（同上） |
| TC-030 | 作法 2 共用檢查 | 例外 | 無 | `nextflowConfig` 放超過 20000 字 | 被拒，拒絕方式與 Slurm 環境相同 | 自動：同檔（`test_shared_checks_apply`） |
| TC-031 | 作法 2 共用檢查 | 例外 | 無 | `environment` 放一個名稱不合規的鍵 | 被拒，拒絕方式與 Slurm 環境相同 | 自動：同檔（同上） |
| TC-032 | 作法 3；裁決 9（沿 azure 裁決 12） | 功能 | 設定齊全、有代理 | 建立時不給 `--credentials` | 建立成功（憑證名字建立時可為空） | 自動：同檔（`test_create_without_credentials_is_allowed`） |
| TC-033 | 作法 3；裁決 9 | 例外 | 同 TC-032 的環境，kubeconfig 檔已放好 | 跑第一次預檢 | `credential_name` 一項是 fail，環境為 `invalid`，不是 `available` | 自動：同檔（同上） |

## User Story 2 — 憑證只是名字：kubeconfig 的內容不進資料庫、日誌、任何回傳（優先度 P1）

維護者原話：「架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）」（第 40 行）→ 憑證與環境分開，環境只記憑證名字。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 | 作法 3 | 功能 | 無 | 建立時 `credentialsId=k8s-lab` | 憑證名字 `k8s-lab` 存下 | 自動：同檔（`test_the_credential_is_only_a_name`） |
| TC-035 | 作法 2、3 | 功能 | 已建好的環境 | 讀回它的設定 | 設定裡沒有任何憑證類的鍵（只有計畫列的那幾個鍵） | 自動：同檔（同上） |
| TC-036 | 作法 3 `credential_findings` | 例外 | 無 | `credentialsId` 分別設成含空白的字串、含 `=` 的字串、含 KTOK 的字串 | 每一個都被拒 | 自動：同檔（同上） |
| TC-037 | 作法 3；`credential_findings` 原樣套用 | 例外 | 無 | 把 `KCFG` 片段放進 `description` 欄建立 | 被**既有**規則擋下；錯誤訊息只含欄位路徑，不含 KTOK | 自動：同檔（`test_a_kubeconfig_pasted_anywhere_is_refused_and_not_repeated`） |
| TC-038 | 同上 | 例外 | 無 | 把 `KCFG` 片段放進 `nextflowConfig` 建立 | 被擋下；訊息只含欄位路徑，不含 KTOK | 自動：同檔（同上） |
| TC-039 | 同上 | 例外 | 無 | 把 `KCFG` 片段放進 `environment` 的某個值建立 | 被擋下；訊息只含欄位路徑，不含 KTOK | 自動：同檔（同上） |
| TC-040 | 作法 3、4 | 例外 | TC-037～039 三次被拒之後 | 讀 `platform.db` 的位元組 | 找不到 KTOK | 自動：同檔（同上） |
| TC-041 | 作法 2 鍵名避開 `key`／`secret`／`token` | 例外 | 無 | 設定裡分別放名為 `token`、`clientKey`、`password` 的鍵 | 每一個都被擋下 | 自動：同檔（`test_a_key_named_field_is_refused`） |
| TC-042 | 作法 3 | 功能 | 無 | 用 `good_config()` 完整建立；另建一個 `description` 含「context」「token-free」字樣的環境 | 兩者都建立成功，沒有被誤當成祕密 | 自動：同檔（`test_normal_values_are_not_mistaken_for_secrets`） |
| TC-043 | 作法 4「平台從不讀 kubeconfig」 | 功能 | 把 `KCFG` 寫在代理部署的 `_personal/kubeconfig`；建立、列出、`ce show` 都做過 | 讀 `platform.db` 的位元組 | 找不到 KTOK | 自動：同檔（`test_the_platform_does_not_read_the_kubeconfig`） |
| TC-044 | 作法 4 | 功能 | 同 TC-043 | 檢查建立、`ce list`、`ce show` 的所有命令列輸出 | 都找不到 KTOK | 自動：同檔（同上） |
| TC-045 | 作法 3 與裁決 6（平台端不加 kubeconfig 專屬規則，缺口記帳本） | 例外 | 實作完成後 | 驗收者讀 `specs/k8s-ce/ledger.md` | 帳本逐項寫明：把 `client-certificate-data:`、`client-key-data:` 開頭的行貼進 `description`／`nextflowConfig` 時，既有規則「擋下」還是「擋不住」；擋不住的如實列為缺口（不是擅自加規則） | 手動：驗收者讀帳本；步驟寫在 `docs/TESTING.md` 的 k8s-ce 小節 |

## User Story 3 — 預檢：唯讀、不花錢、不寫叢集（優先度 P1）

維護者原話：「create + free read-only preflight only … NO launching, no cost, no writes to the cluster」→ 每條 `kubectl` 都要被測試證明是唯讀。預檢的七項依序為 `credential_name, credential_file, kubectl, context, pvc, pvc_access, service_account`。以下「假 runner」皆用 `monkeypatch.setattr(k8s_preflight, "_run", runner)` 的替身，不碰網路。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-046 | 作法 5 檢查表 | 功能 | 假 runner、假 which，憑證檔 0600 | 跑預檢 | 回傳七項，順序為 `credential_name, credential_file, kubectl, context, pvc, pvc_access, service_account`，每項都有 name／status／detail | 自動：同檔（`test_every_check_is_reported_in_order`） |
| TC-047 | 作法 5 `credential_file` | 例外 | 憑證檔不存在 | 跑預檢 | `credential_file` 是 fail；detail 含**實際應放的路徑**（`<deployment>/_personal/kubeconfig`）與 `chmod 600` | 自動：同檔（`test_a_missing_credential_file_says_where_to_put_it`） |
| TC-048 | 作法 5「憑證檔不可用 → 後面 unchecked」 | 例外 | 同 TC-047 | 看整份結果 | `context`、`pvc`、`pvc_access`、`service_account` 四項都是 `unchecked`；假 runner 被呼叫 0 次；環境狀態 `invalid` | 自動：同檔（同上） |
| TC-049 | 作法 4 位置 | 功能 | 設環境變數 `ABF_STATION_KUBECONFIG=<tmp>/x` | 取憑證路徑 | 用該路徑 | 自動：同檔（`test_the_kubeconfig_location_follows_the_agents_setting`） |
| TC-050 | 作法 4 位置 | 功能 | 沒設該環境變數，有 settings 檔 | 取憑證路徑 | 為「settings 檔的上上層／`_personal/kubeconfig`」（`settings 檔 parent.parent`） | 自動：同檔（同上） |
| TC-051 | 作法 5 `credential_file` 權限 | 例外 | POSIX 上檔案權限 0644 | 跑預檢 | `credential_file` 是 fail，detail 含 `chmod 600` | 自動：同檔（`test_a_kubeconfig_other_people_can_read_is_refused`，POSIX 專用） |
| TC-052 | 同上 | 功能 | POSIX 上檔案權限 0600 | 跑預檢 | `credential_file` 是 pass | 自動：同檔（同上） |
| TC-053 | 作法 5「Windows 略過權限位並明說」 | 功能 | 假裝 `sys.platform=="win32"`，檔案存在 | 跑預檢 | `credential_file` 是 pass，detail 含「Windows 不檢查權限位」 | 自動：同檔（同上） |
| TC-054 | 作法 5「一般檔案」 | 例外 | 憑證路徑是個資料夾 | 跑預檢 | `credential_file` 是 fail，detail 含「not a regular file」 | 自動：同檔（同上） |
| TC-055 | 作法 4、5「大小 ≤1 MB」 | 例外 | 憑證檔大於 1 MB | 跑預檢 | `credential_file` 不是 pass；其後依賴憑證檔的四項為 `unchecked` | 自動：同檔（新增，併入同函式；見總覽疑問 1） |
| TC-056 | 作法 5 `kubectl` | 例外 | 假 `which("kubectl")` 回 None | 跑預檢 | `kubectl` 是 `unchecked`；`context`、`pvc`、`pvc_access`、`service_account` 也是 `unchecked`；環境 `invalid` | 自動：同檔（`test_without_kubectl_nothing_is_run`） |
| TC-057 | 作法 5「沒有 kubectl 時 runner 一次都不呼叫」 | 例外 | 同 TC-056 | 看假 runner 與環境訊息 | runner 被呼叫 0 次；環境 `message` 含「kubectl」與「沒裝」 | 自動：同檔（同上） |
| TC-058 | 作法 5；K8S-20 | 功能 | 假 runner：`config get-contexts` 回 `(0,"lab-context\nother")`、PVC phase 回 `(0,"Bound")`、accessModes 回 `(0,"ReadWriteMany")`、serviceaccount 回 `(0,"serviceaccount/lab-sa")`；設了 `serviceAccount=lab-sa` | 跑預檢 | 七項皆 pass | 自動：同檔（`test_all_checks_passing_makes_the_environment_available`） |
| TC-059 | 作法 5「全過才 available」 | 功能 | 同 TC-058 | 經 `jobs` 的預檢工作記錄結果 | 環境狀態 `available` | 自動：同檔（同上） |
| TC-060 | 作法 5 `context` | 例外 | 假 runner 的 `config get-contexts` 輸出不含 `lab-context` | 跑預檢 | `context` 是 fail；detail 含 `lab-context` | 自動：同檔（`test_a_context_that_is_not_in_the_file_fails_without_listing_the_others`） |
| TC-061 | 作法 5「不列出其他 context 名」 | 例外 | 同 TC-060，輸出裡有 `prod-cluster`、`other` 等別的名字 | 看 `context` 的 detail 與整份結果 | 不含輸出裡的其他 context 名 | 自動：同檔（同上） |
| TC-062 | 作法 5「context 沒過 → 後三項 unchecked、不再呼叫叢集」 | 例外 | 同 TC-060 | 看 `pvc`、`pvc_access`、`service_account` 與 runner 呼叫數 | 三項為 `unchecked`；`context` 之後 runner 不再被呼叫 | 自動：同檔（同上） |
| TC-063 | 裁決 14（整行相等） | 例外 | 假 runner 的 `config get-contexts` 輸出只有一行 `lab-context-2` | 跑預檢 | `context` 是 fail（`lab-context` 不是 `lab-context-2` 的子字串可湊數） | 自動：同檔（新增 `test_a_context_is_matched_as_a_whole_line`） |
| TC-064 | 裁決 14（去掉前後空白後比較） | 功能 | 假 runner 的輸出有一行 `  lab-context  `（前後有空白） | 跑預檢 | `context` 是 pass | 自動：同檔（同上） |
| TC-065 | 作法 5 `pvc` | 例外 | 假 runner 對 `get pvc` 回 `(1,"…NotFound…")` | 跑預檢 | `pvc` 是 fail，detail 含 `lab-pvc` | 自動：同檔（`test_a_pvc_that_is_missing_or_not_bound_fails`） |
| TC-066 | 作法 5 `pvc` | 例外 | 假 runner 的 phase 回 `(0,"Pending")` | 跑預檢 | `pvc` 是 fail | 自動：同檔（同上） |
| TC-067 | 作法 5 `pvc` | 例外 | 假 runner 的 phase 回 `(0,"Lost")` | 跑預檢 | `pvc` 是 fail | 自動：同檔（同上） |
| TC-068 | 作法 5「pvc 沒過時 pvc_access 為 unchecked」 | 例外 | 同 TC-065 | 看 `pvc_access` | `unchecked` | 自動：同檔（同上） |
| TC-069 | 作法 5 `pvc_access`；裁決 3 | 例外 | 假 runner 的 accessModes 回 `(0,"ReadWriteOnce")` | 跑預檢 | `pvc_access` 是 fail，detail 含 `ReadWriteMany`（說明 Nextflow 官方文件要求它） | 自動：同檔（`test_a_pvc_without_readwritemany_fails_and_says_why`） |
| TC-070 | 作法 5 `pvc_access` | 功能 | 假 runner 的 accessModes 回 `(0,"ReadWriteOnce ReadWriteMany")` | 跑預檢 | `pvc_access` 是 pass | 自動：同檔（同上） |
| TC-071 | 作法 5 `service_account` | 功能 | 沒設 `serviceAccount` | 跑預檢 | `service_account` 是 pass，detail 說「未設定，使用命名空間預設帳號」；假 runner 沒有為它被呼叫 | 自動：同檔（`test_the_service_account_is_checked_only_when_set`） |
| TC-072 | 作法 5 `service_account` | 例外 | 設 `serviceAccount=lab-sa`，假 runner 對 `get serviceaccount` 回 rc≠0 | 跑預檢 | `service_account` 是 fail，detail 含 `lab-sa` | 自動：同檔（同上） |
| TC-073 | 作法 5「輸出截 300 字」 | 例外 | 假 runner 的 `pvc` 回 `(1, 2000 字的輸出)` | 跑預檢 | `pvc` 是 fail，detail 不超過 300 字 | 自動：同檔（`test_an_api_failure_is_reported_trimmed_and_scrubbed`） |
| TC-074 | 作法 5 `_scrub`；專長守則 | 例外 | 上述 2000 字輸出裡夾了 KTOK 與一段 `Bearer …` 字串 | 看 detail | 不含 KTOK、不含該 Bearer 字串 | 自動：同檔（同上） |
| TC-075 | 作法 5「逾時只讓該項 fail」 | 例外 | 假 runner 對 `pvc` 丟 `TimeoutError` | 跑預檢 | `pvc` 是 fail，detail 含「逾時」 | 自動：同檔（`test_a_timeout_fails_that_check_only`） |
| TC-076 | 同上；K8S-26 | 功能 | 同 TC-075，且設了 `serviceAccount` | 看其他項 | `pvc_access` 是 `unchecked`（因 `pvc` 未過）；`service_account` 仍被執行（兩者無依賴） | 自動：同檔（同上） |
| TC-077 | 作法 5「context 沒過 → 後三項 unchecked」＋「逾時只讓該項 fail」 | 例外 | 假 runner 對 `config get-contexts` 丟 `TimeoutError` | 跑預檢 | `context` 是 fail，detail 含「逾時」；`pvc`、`pvc_access`、`service_account` 是 `unchecked` | 自動：同檔（新增，併入同函式） |
| TC-078 | 作法 5「唯讀」；K8S-27 | 功能 | 記錄一次完整預檢送出的所有指令 | 看每條指令 | 每條的前綴都是 `kubectl config get-contexts`、`kubectl get pvc` 或 `kubectl get serviceaccount` 其中之一 | 自動：同檔（`test_the_commands_are_read_only`） |
| TC-079 | 作法 5「絕不呼叫 use-context／set-*」；交辦「no writes」 | 例外 | 同 TC-078 | 逐條指令的每個字做**整詞**比對 | 沒有任何一條含 `create`、`delete`、`apply`、`patch`、`replace`、`edit`、`exec`、`run`、`cp`、`scale`、`drain`、`cordon`、`taint`、`label`、`annotate`、`port-forward`、`proxy`、`attach`、`rollout`、`use-context`、`set-context`、`set-credentials`、`auth`、`logs`、`certificate` | 自動：同檔（同上） |
| TC-080 | 作法 5 `_kube_env` | 功能 | 假 runner 記錄每次呼叫的環境變數 | 跑預檢 | 每次呼叫的環境變數 `KUBECONFIG` 等於憑證檔路徑，`KUBECACHEDIR` 指向一個空的暫存目錄 | 自動：同檔（`test_the_kubeconfig_goes_in_the_environment_not_in_argv`） |
| TC-081 | 作法 5「路徑只在 env，不在 argv」 | 功能 | 同 TC-080，憑證檔內含 KTOK | 看每次呼叫的指令列 | 指令列不含憑證檔路徑、不含 KTOK | 自動：同檔（同上） |
| TC-082 | 作法 5「刪掉所有 KUBE*」 | 功能 | 測試先在自己的環境設 `KUBECONFIG=X`、`KUBE_FAKE_HOST=Y` | 跑預檢 | 呼叫時的環境裡沒有繼承到 `X`、`Y`（`KUBECONFIG` 是檔案路徑那一個） | 自動：同檔（同上） |
| TC-083 | 作法 5「刪掉所有 ABF_*」 | 功能 | 測試先在自己的環境設 `ABF_PLATFORM_TOKEN=T` | 跑預檢 | 呼叫時的環境裡沒有任何 `ABF_` 開頭變數，也沒有 `T` | 自動：同檔（同上） |
| TC-084 | 作法 5「呼叫完刪暫存目錄」 | 功能 | 同 TC-080 | 預檢結束後看那個暫存目錄 | 已不存在 | 自動：同檔（同上） |
| TC-085 | 作法 5 指令形狀 | 功能 | 同 TC-080 | 看每條 `kubectl get` 指令 | 都帶 `--context lab-context`（或 `--context=lab-context`）、`--namespace lab-ns`、`--request-timeout` | 自動：同檔（同上） |
| TC-086 | 作法 5 預設 runner | 功能 | 把 `subprocess.run` 換成假物件 | 以預設 runner 執行一條指令 | 收到 `shell=False`、list 型指令列、`timeout=30` | 自動：同檔（`test_the_default_runner_is_a_fixed_argv_without_a_shell`） |
| TC-087 | 作法 5 `clean_environment` 再驗一次 | 例外 | 無 | 分別把 `context:"x; touch c"`、`namespace:"A B"`、`storageClaimName:"q q"`、`workDir:"/etc/x"`、`credentialsId:"a b"` 送進 `k8s_preflight.clean_environment` | 每一個都得到 `rules.Refusal`（代理在組指令前自己再擋） | 自動：同檔（`test_the_agent_judges_the_environment_again_before_it_builds_a_command`） |
| TC-088 | 作法 5 `clean_environment` | 例外 | 無 | 送進一個 `platform` 為其他類型的環境 | 同樣得到 `rules.Refusal` | 自動：同檔（同上） |
| TC-089 | 作法 5「只留 name, platform, credentialsId, context, namespace, storageClaimName, storageMountPath, workDir, serviceAccount」 | 功能 | 送進一個合規、但多帶了額外鍵（如 `foo`）的環境字典 | 看 `clean_environment` 的回傳 | 鍵集合是上述九個的子集，不含 `foo` | 自動：同檔（新增，併入同函式） |
| TC-090 | 作法 4「檔案永遠不進回傳」；專長守則 | 功能 | 憑證檔內容是 `KCFG`（含 KTOK）；七項全過 | 檢視預檢回傳的整個結構 | 找不到 KTOK | 自動：同檔（新增 `test_no_secret_in_the_result_or_in_the_log`） |
| TC-091 | 作法 4「檔案永遠不進日誌」；專長守則 | 例外 | 憑證檔含 KTOK；假 runner 的失敗輸出也夾 KTOK | 跑預檢，同時攔截日誌、標準輸出與標準錯誤 | 日誌與兩路輸出都找不到 KTOK | 自動：同檔（同上） |
| TC-166 | 完成標準「手動（維護者）」 | 功能 | 維護者有一個真的 K8s 叢集：營運者先建好命名空間、`ReadWriteMany` 且 `Bound` 的 PVC、（可選）service account；平台主機裝 `kubectl`；kubeconfig 放在 `<agent deployment>/_personal/kubeconfig`（權限 600） | `abf-platform ce create --name k1 --platform k8s-platform --agent <代理> --credentials k8s-lab --context <ctx> --namespace <ns> --storage-claim <pvc> --work-dir /workspace/work` | 看到七項檢查；全 pass 時 `ce show k1` 為 `available`；`ce show` 與 `platform.db` 搜不到 kubeconfig 任何片段；叢集上沒有任何新建資源；並回報計畫標為「未驗證」的四件事：①`kubectl config get-contexts -o name` 離線時仍能列出 context、②`-o jsonpath={.spec.accessModes[*]}` 的輸出是以空白分隔的字串、③`KUBECACHEDIR` 是否生效、④用權限最小的帳號（只有該命名空間的 get pvc／get serviceaccount）時 `pvc` 檢查仍通過；任何一項不成立就回報 developer-agent，不自己改檢查 | 手動：`docs/TESTING.md` 的 k8s-ce 小節 |

## User Story 4 — 接線、命令列、K8s 環境不能被拿去送出（優先度 P1）

維護者原話：「撞牆時先砍 …… AWS／Azure」（第 20 行）→ 本片刻意小，只做建立＋預檢；`available` 的 K8s 環境不能被選去送出，也不會被自動挑為主要環境（作法 9）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-092 | 作法 6、10 | 功能 | 代理 `a1` 在線 | `ce create --platform k8s-platform --agent a1 --credentials k8s-lab --context lab-context --namespace lab-ns --storage-claim lab-pvc --work-dir /workspace/work` | 結束碼 0；輸出含「preflight queued」；`jobs` 表多一列 `preflight` | 自動：同檔（`test_create_queues_the_first_preflight_for_the_agent`） |
| TC-093 | 作法 8 `snapshot` | 功能 | 同 TC-092 | 看那個預檢工作的 args 裡的環境快照 | 鍵集合恰為 `name, platform, credentialsId, context, namespace, storageClaimName, storageMountPath, workDir, serviceAccount`（九個，不多不少） | 自動：同檔（同上） |
| TC-094 | 作法 6 | 例外 | 代理離線 | 同 TC-092 的建立 | 環境狀態仍是 `creating`，並明白說代理離線；`jobs` 表沒有新列 | 自動：同檔（`test_create_with_the_agent_offline_says_so`） |
| TC-095 | 作法 5「結果走既有紀錄路徑」 | 功能 | `auto_serve` 夾具 | `ce preflight k1` | 每一項印成 `name: status - detail` 一行 | 自動：同檔（`test_ce_preflight_prints_each_check`） |
| TC-096 | 作法 10 旗標 | 功能 | 無 | 用 `--context`、`--namespace`、`--storage-claim`、`--storage-mount-path`、`--service-account` 各一個值 | 依序進到設定鍵 `context`、`namespace`、`storageClaimName`、`storageMountPath`、`serviceAccount` | 自動：同檔（`test_cli_flags`） |
| TC-097 | 作法 10 說明文字 | 例外 | 無 | 讀整份 `--help` 輸出 | 不含 `launch`、`submit`、`cancel` 這三個字（既有 TC-060 的掃描規則不改） | 自動：同檔（同上）；並跑 `platform/tests/test_station_envs.py` 的 TC-060 掃描 |
| TC-098 | 作法 6「K8s 不得落到 Slurm 的路徑」 | 功能 | 把 `rules.clean_environment` 換成一被呼叫就失敗的替身 | 讓代理處理一個 K8s 環境的 `preflight` 工作 | 走的是 `k8s_preflight`，Slurm 路徑的 `rules.clean_environment` 沒被呼叫；回 `("done", …)` | 自動：同檔（新增 `test_the_agent_checks_a_k8s_job_with_the_k8s_preflight`） |
| TC-099 | 作法 8「其他類型的回傳一個字都不變」；K8S-35 | 功能 | 建立 Slurm、gcb、aws、azure 各一個 | 取各自的 `snapshot` | 與改動前逐鍵相同；四者仍各走自己的預檢 | 自動：同檔（`test_other_types_are_unchanged`） |
| TC-100 | 作法 1 | 功能 | 無 | 讀常數 | `PLATFORM_HOST_TYPES` 仍是 `(GOOGLE_BATCH, AWS, AZURE)`（K8s 不在內）；`CLOUD_JOB_KINDS` 仍只有那四個項目、不含 K8s | 自動：同檔（同上），沿用 `test_aws_clean.py`／`test_azure_launch.py` 既有斷言 |
| TC-101 | 作法 7；K8S-36 | 例外 | 一個 `available` 的 K8s 環境 | 分別排入 `launch_nextflow`、`cancel_run`、`clean_work`、`put_upload`、`list_site_files`、`pipeline_files` | 六種全部被拒（`JobRefused`） | 自動：同檔（`test_jobs_other_than_the_preflight_are_refused_in_plain_words`） |
| TC-102 | 作法 7 訊息 | 例外 | 同 TC-101 | 讀被拒的訊息 | 含「Kubernetes」「尚未支援送出」「k8s-launch」 | 自動：同檔（同上） |
| TC-103 | 作法 7「不再寫死 Azure」 | 例外 | 同 TC-101 | 讀被拒的訊息 | 不含 "Azure"、"AWS"、"Google" | 自動：同檔（同上） |
| TC-104 | 作法 7 | 例外 | 同 TC-101，數 `jobs` 表列數 | 六種都被拒之後再數一次 | 列數不變（沒有任何東西被排進佇列） | 自動：同檔（同上） |
| TC-105 | 作法 7「AWS／Azure／Google 的拒絕句與 put_upload 的拒絕句一個字都不改」 | 功能 | 既有的 AWS、Azure、Google 環境與 Slurm 環境 | 跑既有測試對這些拒絕句的斷言 | 全部不改而通過（拒絕句與 base 逐字相同） | 自動：既有 `test_aws_ce.py`／`test_azure_launch.py`／`test_gcb_launch.py`／`test_aws_clean.py` 等，不得為此修改 |
| TC-106 | 作法 9 | 例外 | 一個 `available` 的 K8s 環境 | `build.target_problem(state,"k1","launch_nextflow")` | 回傳非 None 的白話句（說不能送出） | 自動：同檔（`test_launch_is_refused_and_the_environment_is_never_auto_picked`） |
| TC-107 | 作法 9 | 例外 | 只有一個 `available` 的 K8s 環境，沒有別的 | `primary_environment` | 回 None（K8s 永遠不被自動挑為主要環境） | 自動：同檔（同上） |
| TC-108 | 作法 9 | 功能 | 一個 `available` 的 Slurm 環境與一個 `available` 的 K8s 環境 | `primary_environment` | 選 Slurm | 自動：同檔（同上） |
| TC-109 | 專長守則（跨使用者讀）；K8S-38 | 例外 | 使用者 A 建了 K8s 環境 `k1` | 使用者 B 以 `owner=` 取 `k1` | 回 None（跟不存在一樣） | 自動：同檔（`test_another_users_k8s_environment_is_not_found`） |
| TC-110 | 專長守則（跨使用者寫） | 例外 | 同 TC-109 | B 對 `k1` 排入預檢工作 | 得到與「環境不存在」完全相同文字的 `JobRefused`；`jobs` 表沒有新列 | 自動：同檔（同上） |
| TC-111 | 既有行為（K8S-39） | 例外 | 一個已停用（disabled）的 K8s 環境 | 更新它 | 不排入預檢，`jobs` 表沒有新列 | 自動：同檔（`test_updating_a_disabled_environment_queues_no_preflight`） |

## User Story 5 — 舊的 K8s 記錄：只缺 `context`，其餘照常（優先度 P2）

計畫作法 2：舊的 `UNSUPPORTED` 範例記錄用的鍵 `namespace`、`storageClaimName`、`storageMountPath`、`workDir` 都是已知鍵，所以舊 K8s 列只缺 `context`。舊列：status=`unsupported`、設定 `{"workDir":"/mnt/work","namespace":"nf","storageClaimName":"pvc-work","storageMountPath":"/mnt"}`（用 SQL 直接插入）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112 | 作法 2、K8S-40 | 功能 | 上述舊列已插入 | `ce list`、`ce show` | 照常顯示，狀態仍是 `unsupported` | 自動：同檔（`test_an_old_k8s_record_asks_for_the_missing_context`） |
| TC-113 | 作法 2 | 例外 | 同上 | `ce preflight` | 結束碼不為 0；訊息點名 `context` | 自動：同檔（同上） |
| TC-114 | 作法 2 | 例外 | 同上 | `ce update`（不補 `context`） | 結束碼不為 0；訊息點名 `context`（告訴使用者缺什麼） | 自動：同檔（同上） |
| TC-115 | 作法 2「舊列有其他未知鍵時才是 unknown」 | 例外 | 同上 | 讀 TC-113、TC-114 的訊息 | 不說 `namespace`、`storageClaimName`、`storageMountPath`、`workDir` 是 unknown setting | 自動：同檔（同上） |
| TC-116 | 作法 2 | 功能 | 同上 | `ce update --agent a1 --context lab-context` | 成功；狀態轉為 `creating` | 自動：同檔（同上） |

## User Story 6 — 文件（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-117 | 作法 12 | 功能 | 實作完成 | 讀 `docs/PLATFORM.md` | 含 `` `context` ``、`` `namespace` ``、`` `storageClaimName` ``、`` `storageMountPath` ``、`` `workDir` ``、`` `serviceAccount` `` 六個鍵 | 自動：同檔（`test_docs_list_every_k8s_key_and_check`） |
| TC-118 | 作法 12 | 功能 | 同上 | 讀 `docs/PLATFORM.md` | 含七個檢查名 `credential_name`、`credential_file`、`kubectl`、`context`、`pvc`、`pvc_access`、`service_account` | 自動：同檔（同上） |
| TC-119 | 作法 12 | 功能 | 同上 | 讀 `docs/PLATFORM.md` | 含 `ABF_STATION_KUBECONFIG`、`_personal/kubeconfig`、`chmod 600` | 自動：同檔（同上） |
| TC-120 | 作法 12 | 功能 | 同上 | 讀 `docs/PLATFORM.md` | 含 `預檢不計費`（只讀，不建任何東西）、`kubectl`（平台主機要裝）、`ReadWriteMany` | 自動：同檔（同上） |
| TC-121 | 作法 12 小節要點 | 功能 | 同上 | 讀 `docs/PLATFORM.md` 的 Kubernetes 小節 | 寫明：PVC 必須事先由營運者建好；kubeconfig 若用 exec 型登入外掛會在代理主機執行該外掛，kubeconfig 是營運者自己放的信任檔 | 自動：同檔（同上） |
| TC-122 | 作法 12 型別表 | 功能 | 同上 | 讀 `docs/PLATFORM.md` 型別表的 K8s 列 | 該列為 `checked on the platform host (launch: not yet)` | 自動：同檔（同上） |
| TC-123 | 作法 12 第 8 節新句 | 功能 | 同上 | 數 `docs/PLATFORM.md` 中這句出現幾次：`Slurm, Google Cloud Batch, AWS Batch and Azure Batch can run; Kubernetes can be created and checked on the platform host (launch: not yet); the other nine types can be modelled only` | 一字不差，至少出現 2 次 | 自動：同檔（同上） |
| TC-124 | 作法 12；總覽疑問 2 | 功能 | 同上 | 讀 `docs/PLATFORM.md` 第 8 節 | 不再含 `the other ten`；`Fourteen types can be created` 仍在（K8s 沒有增減類型，`KINDS` 仍是 14 個） | 自動：同檔（同上） |
| TC-125 | 作法 12 `SEQERA_PARITY.md` | 功能 | 同上 | 讀 `docs/SEQERA_PARITY.md` 裡 `k8s-platform` 那一列 | 含 `Have (create + check); launch not yet`，且以 `[ ] |` 結尾 | 自動：同檔（同上） |
| TC-126 | 作法 12「只在句尾追加，不動既有子句」 | 功能 | 同上 | 讀 `docs/SEQERA_PARITY.md` 的 "Pre-flight checks:" 段 | Google、AWS、Azure 三個既有子句一字不變；句尾多了 `; for Kubernetes the same agent runs the read-only checks (create + check; launch not yet)` | 自動：同檔（同上） |
| TC-127 | 作法 12；B 表 | 功能 | 同上 | 讀 `docs/SEQERA_PARITY.md` F 節 | 標題 `## F. Compute environments (13 items)` 不變 | 自動：同檔（同上），並由既有 `test_station_docs.py` 的 TC-077 守住 |
| TC-128 | 作法 12 `TESTING.md` | 功能 | 同上 | 讀 `docs/TESTING.md` | 有「Kubernetes environment (k8s-ce)」小節，含 `k8s-ce`、`預檢不計費`、`git diff`、`TC`，且 TC-045、TC-157、TC-158、TC-166 的手動步驟都寫在裡面 | 自動：同檔（同上） |
| TC-129 | 完成標準「手動…同時驗證 ①②③④」 | 功能 | 同上 | 讀 `docs/TESTING.md` 的 k8s-ce 小節 | 四項「未驗證」事項（離線列 context、accessModes 輸出形狀、`KUBECACHEDIR` 是否生效、最小權限帳號能否通過 `pvc` 檢查）都寫成可照做的步驟，並寫明「任何一項不成立就回報、不自己改」 | 自動：同檔（同上） |
| TC-130 | 作法 12「範例一律用 lab-*；不得出現真實叢集名、位址或 token」 | 例外 | 同上 | 掃本任務新增或改過的文件與測試 | 範例只用 `lab-context`、`lab-ns`、`lab-pvc`、`/workspace/work`、`lab-sa`；沒有真實叢集名、網址、IP、token 樣式 | 自動：同檔（同上） |

## User Story 7 — 不在範圍（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-131 | 不做：送出、取消、續跑；不用 `nextflow kuberun` | 不在範圍 | 無 | 掃 `abf_platform/` 與 `abf_station/` 原始碼 | 沒有 `kuberun`、`kubectl apply`、`kubectl create`、`kubectl delete`、`-with-tower`（後者針對 `k8s_preflight.py`） | 自動：同檔（`test_no_launch_or_write_code_for_k8s`） |
| TC-132 | 不做：不用 `kubernetes` Python 套件 | 不在範圍 | 無 | 掃 `k8s_preflight.py`、整個 `abf_station/`、`pyproject.toml` | `k8s_preflight.py` 沒有 `import kubernetes`／`boto3`／`azure`／`google`／`requests`；整個 `abf_station/` 沒有小寫 `kubernetes`（用既有 `test_station_static` 同一條規則）；`pyproject.toml` 不含 `kubernetes` | 自動：同檔（`test_no_cloud_library_is_imported_and_no_forbidden_word_in_the_agent_package`） |
| TC-133 | 平台本身不啟動任何程式（`test_scope.py` TC-071） | 不在範圍 | 無 | 掃 `abf_platform/` | 沒有 `subprocess`，沒有 `kubectl` 字樣（含錯誤訊息與說明文字） | 自動：同檔（`test_the_platform_package_starts_no_program`） |
| TC-134 | 啟動程式只在 `site.py`（TC-091 精神） | 不在範圍 | 無 | 掃 `k8s_preflight.py` | 不 `import subprocess`（經 `site.run_fixed` 起程式） | 自動：同檔（`test_only_site_py_starts_programs`） |
| TC-135 | 不做：不新增 MCP 工具、網頁路由或畫面；不碰網頁檔 | 不在範圍 | 無 | 比對 MCP 工具名集合與 `web.py` 路由表和改動前 | 兩者與改動前相同（比對現有名單，不寫死數字；現況 15 個）；網頁相關檔（`web.py`、`web_board.py`、`static/*`、`DESIGN.md`、`test_web_*`）沒有被改 | 自動：同檔（`test_tool_list_unchanged_and_no_new_web_route`） |
| TC-136 | 不做：清理、上傳 | 不在範圍 | 一個 `available` 的 K8s 環境 | 排入 `clean_work`、`put_upload` | 被拒（K8s 環境不能清理、不能放資料），沒有排入任何工作 | 自動：同 TC-101 的測試，另單獨斷言這兩種 |
| TC-137 | 不做：費用；原話「費用顯示美元、每人每月上限」（第 16 行）本片不碰 | 不在範圍 | 無 | 看 K8s 環境的設定鍵、`snapshot` 與預檢結果 | 沒有任何幣別、費用、預算相關的欄位或檢查項 | 自動：同檔（新增，併入 `test_create_queues_the_first_preflight_for_the_agent`） |
| TC-138 | 不做：不碰 `eks-platform`、`gke-platform`、`awscloud-platform`、`azcloud-platform`、`googlecloud-platform`；裁決 1 | 不在範圍 | 無 | 建立這五種各一個 | 狀態維持 `unsupported`，預檢被當場拒絕（與改動前相同） | 自動：同檔（新增）；並由既有 `test_station_envs.py` 的 `UNSUPPORTED` 參數化測試守住 |
| TC-139 | 不做：Fusion／Wave 免 PVC、`storageSubPath`、自訂 pod 規格、多叢集 | 不在範圍 | 無 | 在 K8s 設定裡放 `storageSubPath`、`podOptions`、`fusion` 等鍵 | 每一個都被當未知鍵拒收，訊息含 `unknown setting for a Kubernetes environment` | 自動：同檔（新增，併入 `test_unknown_keys_are_refused`） |
| TC-140 | 不做：不加 `kubectl auth can-i`；裁決 4 | 不在範圍 | 同 TC-078 | 看預檢送出的所有指令 | 沒有任何一條含 `auth` 或 `can-i` | 自動：同檔（同 `test_the_commands_are_read_only`） |
| TC-141 | 不做：不解析 kubeconfig、不擋 exec 外掛；裁決 5 | 不在範圍 | 憑證檔內容是任意非 YAML 文字、權限 0600 | 跑預檢的 `credential_file` | 是 pass（代理只查存在、一般檔案、權限、大小，不看內容；內容對不對由 `kubectl` 與 `context` 檢查回報） | 自動：同檔（新增，併入 `test_a_kubeconfig_other_people_can_read_is_refused`） |
| TC-142 | 作法 11「不需要 migration」 | 不在範圍 | 無 | 比對 `compute_envs` 表的欄位與 base | 欄位完全相同；`status` 仍只有既有五種值；沒有新增 migration 檔 | 自動：同檔（新增 `test_no_schema_change`） |
| TC-143 | 範圍：檔案（只准改這些）、不准碰 | 不在範圍 | 實作完成 | 驗收者跑 `git diff --name-only`（相對 base `origin/v3@e79a555`） | 只含計畫「範圍：檔案」所列（含裁決 12 加入的 `platform/tests/test_azure_upload.py`），不含 `abf_launch/`、`gcb_preflight.py`、`aws_preflight.py`、`azure_preflight.py`、`launch.py`、`cloud_store.py`、`clean.py`、任何網頁檔 | 手動：驗收者看 `git diff`；步驟寫在 `docs/TESTING.md` 的 k8s-ce 小節 |

## User Story 8 — 既有測試的有意更新（優先度 P2）

計畫「必須更新的既有斷言」A／B／C／D：只准改這幾處，每處改法與理由逐條列在 PR 說明（以前／以後／理由）。行號以計畫為語意提示，實際以 `git grep` 為準。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-144 | A 表：`test_azure_ce.py::test_the_type_constants` | 功能 | 實作完成 | 讀該測試 | 斷言改為 `CHECK_ONLY_TYPES == ("k8s-platform",)`、`CHECKABLE == (SUPPORTED, gcb, aws, AZ, "k8s-platform")`；舊註解改成說明 K8s；測試通過 | 自動：`platform/tests/test_azure_ce.py` |
| TC-145 | A 表：`test_azure_launch.py::test_type_constants_are_as_planned_and_nothing_indexes_them_by_position` | 功能 | 同上 | 讀該測試 | 同樣兩行改；`PLATFORM_HOST_TYPES` 與 `CLOUD_JOB_KINDS[AZURE]` 兩行不動；掃 `CHECK_ONLY_TYPES` 那行含「新雲端類型先放這裡，只開預檢」的斷言不動且通過（`compute_envs.py` 該行註解保留） | 自動：`platform/tests/test_azure_launch.py` |
| TC-146 | A 表：`test_aws_launch.py` 常數測試 | 功能 | 同上 | 讀該測試 | `CHECK_ONLY_TYPES == ("k8s-platform",)`；`CHECKABLE` 尾端加 `"k8s-platform"`；註解行掃描不動 | 自動：`platform/tests/test_aws_launch.py` |
| TC-147 | A 表：`test_aws_ce.py::test_the_type_constants` | 功能 | 同上 | 讀該測試 | 同樣改；歷史註解保留並加一行 "k8s-ce" | 自動：`platform/tests/test_aws_ce.py` |
| TC-148 | A 表：`test_gcb_ce.py::test_the_type_constants` | 功能 | 同上 | 讀該測試 | 同樣改 | 自動：`platform/tests/test_gcb_ce.py` |
| TC-149 | B 表：`test_station_envs.py::UNSUPPORTED` | 功能 | 同上 | 讀該 dict | 刪掉 `"k8s-platform"` 那一項；註解 "the 10 types" 改成 "the 9 types"；匯入它的 `test_aws_ce`／`test_azure_ce`／`test_gcb_ce` 仍通過 | 自動：`platform/tests/test_station_envs.py` 等 |
| TC-150 | B 表：`test_tc030_…` 與 `test_tc032_…` | 功能 | 同上 | 讀兩個測試 | `test_tc030` 參數由 10 個變 9 個（函式名不改）；`test_tc032` 的集合加入 `"k8s-platform"` 後仍等於 `KINDS` | 自動：`platform/tests/test_station_envs.py` |
| TC-151 | B 表：三個 `len(UNSUPPORTED)` 斷言 | 功能 | 同上 | 讀 `test_gcb_ce.py`、`test_aws_ce.py`、`test_azure_ce.py` 的 `test_the_other_types_stay_unsupported` | 數量由 10 改 9（aws、azure 的後半條件 `… not in UNSUPPORTED` 保留） | 自動：三個測試檔 |
| TC-152 | B 表：azure 迴圈 | 功能 | 同上 | 讀 `test_azure_ce.py` 該迴圈 | 檢查清單拿掉 `"k8s-platform"`，其餘四個（`awscloud-platform`、`azcloud-platform`、`eks-platform`、`gke-platform`）仍在 `UNSUPPORTED` 內 | 自動：`platform/tests/test_azure_ce.py` |
| TC-153 | B 表：`test_station_docs.py::test_tc077_the_parity_table_…` | 功能 | 同上 | 讀該測試 | 跳過清單加 `"k8s-platform"`；"Modelled, needs a real account" 的總數由 10 改 9；`len(KINDS) == 14` 兩處不動 | 自動：`platform/tests/test_station_docs.py` |
| TC-154 | C 表：六個逐字比對舊句的文件測試 | 功能 | 同上 | 讀 `test_aws_ce.py`、`test_azure_ce.py`（連同 `"the other eleven" not in d` 保留）、`test_azure_launch.py`（`count >= 2`）、`test_azure_upload.py`、`test_gcb_ce.py`、`test_gcb_launch.py` 的文件斷言 | 只把期望字串改成 TC-123 的新句，其餘斷言一個字不動、不刪不放寬 | 自動：上述六個測試檔 |
| TC-155 | D 表：確認不必動 | 功能 | 同上 | 各跑一次：`test_station_envs.py::test_tc085…`、`test_launch_cli.py::test_tc063`、`test_station_static.py::test_agent_stricter_scan_no_other_network_or_cloud_library`、TC-060 說明文字掃描、MCP 工具數相關（`test_oauth_mcp.py`、`test_pat.py`、`test_guidance.py`）、`test_scope.py::test_tc070`、`test_aws_clean.py`、`test_aws_upload.py`、`test_azure_launch.py` 的 `CLOUD_JOB_KINDS` 斷言 | 全部不改檔而通過 | 自動：上述既有測試 |
| TC-156 | 裁決 12（全面 grep、所有命中視同 C 表） | 功能 | 實作完成 | 驗收者在 `origin/v3@e79a555` 重跑 `git grep -n -e 'the other ten' -e 'CHECK_ONLY_TYPES == ()' -e 'len(UNSUPPORTED)'` | 每個命中的既有測試檔都已改成只換期望值；命中非測試檔且不在範圍的情形不存在（有則實作應已 BLOCKED 回報） | 手動：驗收者看 `git diff`；步驟寫在 `docs/TESTING.md` 的 k8s-ce 小節 |
| TC-157 | 完成標準「A／B／C 以外沒有任何既有斷言被刪除或放寬」 | 功能 | 實作完成 | 驗收者對每個被改動的既有測試檔跑 `git diff` | 只有 A／B／C 列的改動；沒有斷言被刪除、放寬、跳過，也沒有為了配合新輸出而改期望值 | 手動：驗收者看 `git diff`；步驟寫在 `docs/TESTING.md` 的 k8s-ce 小節 |
| TC-158 | 計畫 D 表末條、`specs/k8s-ce/ledger.md` | 功能 | 實作完成 | 驗收者讀帳本 | 帳本記有：實作前全套測試的紅（含已知環境紅 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched`）、D 表各項確認結果、每個既有測試改動的檔:行／改前／改後、TC-045 的 kubeconfig 缺口紀錄 | 手動：驗收者讀帳本；步驟寫在 `docs/TESTING.md` 的 k8s-ce 小節 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-159 | 第 1 條（動手前先說明現有工具；每個新檔頭寫 `# Nothing existing: …`）；TC-070 | 功能 | 實作完成 | 讀 `platform/abf_station/k8s_preflight.py` 與 `platform/tests/test_k8s_ce.py` 的前 40 行 | 兩個檔都有 `# Nothing existing: …` 且理由至少 15 字；`k8s_preflight.py` 的理由寫明搜過 Nextflow 的 k8s 執行器與 Seqera 的 Kubernetes 表單、沒有免費離線的預檢可用，以及為何走 `kubectl` 命令列而不用 Python 套件 | 自動：`platform/tests/test_scope.py::test_tc070`（既有）；理由內容由驗收者讀檔 |
| TC-160 | 第 2 條（只有一條送出路徑；沒有第二個送出者） | 功能 | 實作完成 | 跑 `bash tests/no_second_run_state_test.sh` | 通過，且沒有為 K8s 新增任何 SUBMIT／LAUNCH 允許清單項目（K8s 檔案不提交任何作業） | 自動：`tests/no_second_run_state_test.sh` |
| TC-161 | 憑證不進 repo（憑證規則） | 功能 | 實作完成 | 跑 `bash tests/credentials_stay_in_settings_test.sh` | 通過；全 repo 找不到完整的假登入字串字面（KTOK 都用字串拼接） | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-162 | 第 3 條（沒有個人路徑、叢集路徑） | 功能 | 實作完成 | 跑 `bash tests/no_hardcoded_paths.sh` | 通過；文件與程式裡的位置都來自設定或環境變數（例如 `ABF_STATION_KUBECONFIG`、`<deployment>/_personal/kubeconfig`） | 自動：`tests/no_hardcoded_paths.sh` |
| TC-163 | 專長守則（backend）：對等性——動作層唯一、處理函式不得有第二份邏輯 | 功能 | 實作完成 | 跑既有動作層對等性測試（`platform/tests/test_actions_layer.py`、`test_web_parity.py`）；並檢查 `ce create`／`ce update`／`ce preflight` 的命令列處理函式 | 既有對等性測試不改而通過（使用者可見動作清單與動作層函式清單仍一一對應，K8s 沒有新增動作）；K8s 的設定驗證只在 `compute_envs`（代理側 `clean_environment` 重用同一組 `_K8S_*` 規則），命令列／處理函式沒有自己的第二份規則 | 自動：既有對等性測試；重用規則由驗收者讀 `k8s_preflight.py` |
| TC-164 | 專長守則（backend）：確認管道——未經確認不得寫入；憲法第 2 條的確認通道 | 功能 | 實作完成 | 跑既有確認通道測試（`test_tch09_*` of `test_human_channel.py`、`test_tch09_b_c_*` of `test_confirm_page.py`） | 不改而通過；加上 TC-101／TC-104：對 K8s 環境，所有寫入或送出類工作被拒後資料沒有任何改變 | 自動：既有測試，加同檔 TC-101、TC-104 的測試 |
| TC-165 | 專長守則（backend）：錯誤訊息說明原因與處理方式，不露堆疊、內部路徑、SQL | 例外 | 實作完成 | 蒐集本任務所有拒絕或失敗訊息（建立被拒、被拒的工作、舊記錄要求補 `context`、`credential_file` 缺檔）逐一讀 | 每則都說明發生了什麼事與該怎麼處理（如補哪個鍵、把檔放哪、`chmod 600`）；任何一則都不含 `Traceback`、SQL 字樣、平台主機上的內部路徑（缺檔提示給營運者的 `_personal/kubeconfig` 位置除外） | 自動：同檔（新增 `test_messages_say_what_to_do_and_leak_nothing_internal`） |
