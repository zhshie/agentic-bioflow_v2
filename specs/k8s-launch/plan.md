---
id: k8s-launch
title: 在 Kubernetes 上送出與取消分析（確認流程同其他雲端；主控程序以一個 Pod 跑在叢集裡，掛同一個 PVC）
tier: B
kinds: backend
lane: L40-k8s-launch
branch: feat/k8s-launch
base: origin/v3@02597261（k8s-ce PR #272 已合；行號取自此版，executor 開工前用 `git show origin/v3:<檔>` 重查）
source: memory/PLAN-abf-v3-replan-2026-10.md 第 169 行（C-5「Azure Batch／K8s：同模式」）；Azure 半邊已完成；memory/dev-plans/k8s-ce.md（前置，「不做」寫明 launch 留給 `k8s-launch`）；memory/dev-plans/azure-launch.md（同型範本）
---

# k8s-launch

> 本檔由 developer-agent 的 subagent 起草（2026-10-29），**未經 developer-agent 確認，裁決各點待確認後才派工**。只處理 C-5 的 K8s 半邊的 C-2 等價物：`k8s-platform` 環境可被選去送出一次分析、可取消。費用預估與上限、資料上傳、清理、續跑、`fetch_run_records`／`read_task_log`／`list_site_files` 都不在本任務。B 級（後端行為改變）→ verifier 通過＋CI 綠由 developer-agent 自合；不動網頁畫面。
> **車道**：改 `compute_envs.py`／`jobs.py`（L2）與 `abf_station/*`（L1），不可與動這幾檔的任務平行。**不碰** `web.py`、`web_board.py`、`web_settings.py`、網頁模板與 static。
> **與 azure-launch 的關鍵差別（先讀）**：Azure／AWS／Google 的主控程序（head process）跑在平台主機上，計算工作交給雲端服務。Kubernetes 不能照抄：Nextflow 官方說工作目錄「必須在共用的 persistent volume」，且執行中的 pod「必須用與設定相同的 PVC 名稱與掛載建立」，沒有 Fusion 時主控程序「通常」跑在同叢集的 pod 裡（〔來源：https://docs.seqera.io/nextflow/kubernetes，2026-10-29 讀〕）；`kuberun`「已過時、不再維護」。所以本任務的主控程序是**叢集裡的一個 Pod**，不是平台主機上的行程。這帶來三個要裁決的問題（裁決 1–3）。

## 目標
讓使用者像在其他環境一樣：在送出畫面看到全部會被送出的內容，本人答 y 後，平台主機上的站台代理用 `kubectl` 在叢集的指定命名空間建立一個「主控 Pod」（掛 `storageClaimName` 的 PVC，執行 `nextflow run`，executor 為 `k8s`），進度經 `-with-tower` 回到平台；需要時本人確認後可取消（刪掉那個主控 Pod）。雲端使用者不裝站台代理。

為什麼這樣切：
1. 確認流程不另做一套：沿用 `prepare_launch` → 確認 → `launch_nextflow` job → `verify_confirmation`（`launch.py:1596` 起的 `run_launch`），沒有本人答 y 就不啟動自動成立。
2. 平台程式（`abf_platform/`）不啟動任何程式；`kubectl` 只經 `site.run_fixed` 呼叫，與 `k8s_preflight`（`k8s_preflight.py:59` `_run`）同一條路。
3. kubeconfig 只在代理那一側的檔案（`k8s_preflight.py:22-23` `ABF_STATION_KUBECONFIG`、`_personal/kubeconfig`），資料庫只存憑證名字；不進 argv、內容包、manifest、日誌。

## 維護者原話（verifier 出題用）
**查無 K8s 送出專屬的維護者原話。** 以下逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md`（azure-launch.md 所引同一組）：
- 「4. 四種計算環境都建：nano4 → Google Batch（開發上限 NT$1,000/月）→ AWS Batch → Azure／K8s。架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（第 40 行）
- 「**C-5** Azure Batch／K8s：同模式」（第 169 行）
- 「13. （10-21 拷問二）……**雲端用戶不裝代理**——平台主機自己跑 Nextflow、雲端憑證放平台主機檔案（不進資料庫）」（第 52 行）
- 「14. （10-21 拷問三）**B 級部分自合**：網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併」（第 54 行）
- 「雲端費用**照 10-18 裁示**：顯示雲端自己的幣別（美元）、不換算……」（第 46 行）→ 送出畫面不寫金額、不換算。
- 「10-21，他定：雲端優先於畫布；雲端用戶不裝站台代理。」
- k8s-ce 計畫的交辦原話：「create + free read-only preflight only … NO launching」——本任務才是開 launch 的那一步，每條會寫入叢集的 `kubectl` 動詞都要有測試證明它只在確認之後才發生。

## 範圍：檔案（只准改這些）
平台側（不啟動任何程式）：
- `platform/abf_platform/compute_envs.py`（`PLATFORM_HOST_TYPES`〔:39〕加 `K8S`；`CHECK_ONLY_TYPES`〔:40〕變 `()`，行尾註解「新雲端類型先放這裡，只開預檢」保留；`CLOUD_JOB_KINDS`〔:41-45〕加 K8S 一列四種：`preflight`、`launch_nextflow`、`cancel_run`、`pipeline_files`；`snapshot`〔:929〕加 K8s 內容）
- `platform/abf_platform/jobs.py`（`_target`〔:95〕：:110-115 的拒絕訊息鏈寫死 AWS／Azure／Google 三句，K8S 進表後會落到「Google Batch」那句，必須加 K8s 分支，最好改成依型別名取名；:116-118 的 CHECK_ONLY 分支訊息含「k8s-launch」，型別清空後變成死碼，改寫或移除；:119-120 的 `put_upload` 拒絕訊息維持，K8s 不在其內）
- `platform/abf_launch/build.py`（加 `is_k8s`；`k8s_launch_screen`；`launch_screen`〔約 :770〕、`cancel_screen`〔約 :798〕、`prepare_cancel`〔約 :302〕分派；`prepare_resume`／`prepare_relaunch`〔約 :432〕對 K8s 拒絕）
- `platform/abf_launch/cli.py`（只在「Slurm 工作編號」用詞處〔約 :200、:240、:270〕依型別換用詞；其餘輸出一字不變）
- `platform/abf_platform/cloud_store.py`（不認 K8s，行為不改；只在需要時調整〔:83-84〕的錯誤句）
- `platform/abf_platform/cli.py`、`actions/*`、`cloud_cost.py`、`web*.py`：**不改**（`cli.py:488` 的條件是 `PLATFORM_HOST_TYPES + CHECK_ONLY_TYPES`，搬動後仍涵蓋 K8s）

站台代理側：
- `platform/abf_station/launch.py`（加 `K8S`、`K8S_RUNS = "_k8s_runs"`、`K8S_FILE_NAMES`、`K8S_NO_RESUME`、`_check_k8s_ce`、`_k8s_config`、`_k8s_head_manifest`、`_check_k8s_samplesheet`、`render_k8s_bundle`；`_snapshot_ce`〔:172-198〕加 K8s 分支；`snapshot_ce`〔:160〕的 `maxMemoryGB` 條件不含 K8s，**維持不含**；`render_bundle`〔:511-530〕加 K8s 分支；`run_launch`〔:1596〕分派〔:1608 之後〕；`run_resume`〔:1774、:1784〕加拒絕）
- `platform/abf_station/k8s_launch.py`（新；鏡像 `azure_launch.py`：`run_launch`〔:82 型〕、`run_cancel`〔:156 型〕）
- `platform/abf_station/cancel.py`（旁加 K8s 分派，仿 :34-36）
- `platform/abf_station/fetch.py`（`_NOT_RECORDS`〔:18〕加 K8s 的設定檔名與 manifest 檔名）
- `platform/abf_station/handlers.py`、`clean.py`、`put_upload.py`、`k8s_preflight.py`：**不改**（只重用 k8s_preflight 的 `clean_environment`、`credentials_path`、`run_preflight`）

測試與文件：
- `platform/tests/test_k8s_launch.py`（新）
- 「必須更新的既有斷言」列的幾處
- `docs/PLATFORM.md`（型別表 K8s 列；`:513` 起的 Kubernetes 小節；新增「Launching on Kubernetes」）、`docs/SEQERA_PARITY.md`（K8s 列）、`docs/TESTING.md`（新增「k8s-launch」小節含手動驗收；`:835-837` 附近 k8s-ce 的段落若釘住「launch 未開」要依實況更新）、`docs/OPERATIONS.md` 雲端小節
- `specs/k8s-launch/ledger.md`（新）

## 作法
1. **逐型別放行**：

   | 路徑 | K8s 本任務的決定 |
   |---|---|
   | `launch_nextflow` | **開**（主體） |
   | `cancel_run` | **開** |
   | `preflight` | **開**（k8s-ce 已做；`handlers.py:83` 分支不動） |
   | `pipeline_files` | **開** |
   | `clean_work`、`put_upload`、資料集 `--destination` | **關**，訊息含「尚未支援」與型別名「Kubernetes」，不得含 `AWS`／`Google Batch`／`Azure` |
   | 費用預估 | **不做**；送出畫面明寫沒有預估與上限 |
   | 續跑／原樣重跑 | **拒**（`K8S_NO_RESUME`） |
   | `list_site_files`／`fetch_run_records`／`read_task_log` | **拒**（同款「尚未支援」） |

2. **型別常數**：`PLATFORM_HOST_TYPES = (GOOGLE_BATCH, AWS, AZURE, K8S)`、`CHECK_ONLY_TYPES = ()`；程式裡不得有 `PLATFORM_HOST_TYPES[` 位置取用。`CHECKABLE` 組法不變。
3. **主控 Pod（待裁決 1）**：代理在叢集建立**一個** Pod（`kubectl create -f -`，manifest 由 stdin 餵入，不落地、不進 argv）：
   - `metadata.name = <run 名稱>`（run 名稱規則 `launch.RUN_NAME`，小寫英數與 `-_`；Pod 名只准小寫英數與 `-`，所以含 `_` 的 run 名要有決定：提案 `nf-<run 名把 _ 換成 ->`，並截 63 字，記進內容包供取消用）
   - `namespace`＝環境的 `namespace`；`serviceAccountName`＝環境的 `serviceAccount`（有設才寫）；`restartPolicy: Never`
   - volume：`persistentVolumeClaim.claimName = storageClaimName`，掛在 `storageMountPath`
   - 容器：映像由待裁決 2 決定；命令為 `nextflow run <pipeline> -r <rev> -name <run> -params-file params.yaml -c nextflow.config -c k8s.config -with-tower <endpoint>`，工作目錄在 PVC 內的專屬資料夾
   - 執行用的檔案（`samplesheet.csv`、`params.yaml`、`nextflow.config`、`k8s.config`、`head.sh`）放進 PVC 的 `<workDir 之外的>/_k8s_runs/<run>/`；寫入方式見待裁決 3。
4. **`k8s.config`** 只含這些鍵（全取自環境的非機密欄位）：`process.executor = 'k8s'`、`k8s.namespace`、`k8s.storageClaimName`、`k8s.storageMountPath`、`workDir`（環境的 `workDir`＋`/runs/<run>/work`，須在掛載路徑底下；`_check_k8s` 已保證，`compute_envs.py:545`）、`k8s.serviceAccount`（有設才寫）。`k8s.context` **不寫**（Pod 在叢集內，用叢集內身分；context 只供代理的 `kubectl --context`）。不含任何憑證或 kubeconfig 內容。`maxvCpus`、`spot` K8s 不收（k8s-ce 作法 2）。
5. **憑證**：kubeconfig 只在代理這一側（`ABF_STATION_KUBECONFIG`）。代理呼叫 `kubectl` 時的環境變數沿用 `k8s_preflight._kube_env`（`:65`，刪 `ABF_*`、`KUBE*`，再設 `KUBECONFIG`、`KUBECACHEDIR`），路徑只在 env、不在 argv。**絕不呼叫** `kubectl config use-context`／`set-*`，一律 `--context`。Pod 內不放 kubeconfig；Pod 靠 `serviceAccount` 與叢集內 RBAC 建立 task pod（需要的 Role 寫進文件，不由本任務建立，見不做）。
6. **進度回報（待裁決 3）**：`-with-tower` 的端點必須是 Pod 連得到的位址，loopback 不行。沿用 `launch._tower`（`launch.py:390`）的 `direct` 模式（要求 `facts.way_back == "direct"` 與 https 的 `platform_public_url`）；不符合就用白話拒絕，不靜默省略。
7. **`k8s_launch.py`**（鏡像 `azure_launch.py`）：`run_launch(job, ctx, bundle)` 順序：確認內容包是給這個代理的 → run token → 用自己的設定重建內容包並比對 → deadline → 憑證檔（`k8s_preflight.credentials_path`）→ `kubectl` 在不在 → **重跑預檢**（`k8s_preflight.run_preflight`，任何一項不是 pass 就不建立任何東西）→ 檢查同名 Pod 不存在（`kubectl get pod <名>`；存在就拒絕，不覆蓋）→ 寫執行檔到 PVC → `kubectl create` → 等 settle，`kubectl get pod -o jsonpath={.status.phase}` 不是 `Failed` → 回傳 `{"ok": True, "slurm_job_id": …, "message": "已啟動：Pod <名>（命名空間 <ns>）…；叢集的運算費用從現在開始計"}`。`slurm_job_id` 欄位沿用，K8s 無 pid：提案寫入 0 以外的固定占位值並在 `bundle` 內另存 `pod_name`（待裁決 4，不改資料表、不 migration）。
8. **取消**：`k8s_launch.run_cancel`：核對 bundle 是給這個代理、Pod 名是這個平台會產生的名字、命名空間與環境一致，然後**一次** `kubectl delete pod <名> --namespace <ns> --context <ctx> --wait=false`。不刪 PVC、不刪別的 Pod、不用 label selector、不用 `--all`。訊息白話提醒「請到叢集確認 task pod 是否已清掉；沒清乾淨要自己處理，費用從啟動到停掉都算」。主控 Pod 被刪時 Nextflow 是否會清掉 task pods：官方頁未說明（見環境事實），以手動驗收 5 判決，不自行加 `kubectl delete pod -l`。
9. **畫面**（`build.py`）：`k8s_launch_screen` 第一段帳單句（常數 `K8S_COST`）：「由你的 Kubernetes 叢集所屬的雲端或機房計費；本系統目前沒有費用預估與上限」，不含金額、`NT$`、`USD`。列出：叢集 context、命名空間、PVC、將建立的 Pod 名、將寫入 PVC 的檔案、主控 Pod 映像。`cancel_screen`／`prepare_cancel` 擴到 K8s；無 Pod 名時照舊拒絕。
10. **不需要 migration**：不改資料表與環境設定鍵。
11. **新檔頭規則**：`k8s_launch.py`、`test_k8s_launch.py` 前 40 行有 `# Nothing existing: …`（TC-070），理由寫「搜過 Nextflow 官方 Kubernetes 頁（kuberun 已過時）、Seqera `tw launch`、nf-core `tower launch`，沒有現成可由本機代理在人確認後建立主控 Pod 並可取消的東西」。**`abf_station/*.py` 任何一行（含註解、字串）不得出現小寫 `kubernetes`**（`test_station_static.py::test_agent_stricter_scan_no_other_network_or_cloud_library`；見 k8s-ce.md 作法 5，用大寫或拆字）；不 import `kubernetes` 套件。

## 失敗先行測試（`platform/tests/test_k8s_launch.py`，現在都紅；全用假的 `runner`／`run_fixed`、`tmp_path`，不碰叢集、不花錢；輸入用 fake：`lab-ctx`、`nf-ns`、`nf-pvc`、`/workspace/work`）
編號前綴 `K8L-`。
閘門：
- K8L-GATE-01：可用的 K8s 環境，`launch_nextflow`／`cancel_run`／`preflight`／`pipeline_files` 通過；`clean_work`、`put_upload`、`list_site_files`、`fetch_run_records`、`read_task_log` → `JobRefused`，含「尚未支援」，不含 `AWS`／`Google Batch`／`Azure`。
- K8L-GATE-02：AWS／Azure／Google 的放行與拒絕訊息與搬動前位元級相同。
- K8L-GATE-03：`PLATFORM_HOST_TYPES == (GOOGLE_BATCH, AWS, AZURE, K8S)`、`CHECK_ONLY_TYPES == ()`、`CLOUD_JOB_KINDS[K8S]` 恰四種；原始碼無 `PLATFORM_HOST_TYPES[`。
- K8L-GATE-04：`cloud_store` 對 K8s 環境一律 `CloudPathError`；資料集 `--destination` 填 K8s 環境名 → 白話拒絕。
- K8L-GATE-05：直接排 `put_upload`／`clean_work` 給 K8s → 被拒、jobs 列數不變。
- K8L-GATE-06：`ce preflight` 對 K8s 仍排出預檢並走 `k8s_preflight`；`primary_environment` 不會自動挑 K8s。
內容與 manifest：
- K8L-BUNDLE-01：`k8s.config` 鍵集合恰為作法 4；無憑證、無 `context`。
- K8L-BUNDLE-02：內容包、manifest、`head.sh`、`snapshot_ce`、資料庫、`ce show` 搜不到假 kubeconfig 內容與憑證檔路徑（字串拼接組出）。
- K8L-BUNDLE-03：manifest 只有一個 Pod；`claimName`、`mountPath`、`namespace`、`serviceAccountName` 對得上環境；`restartPolicy: Never`；命令最後恰一個 `nextflow run … -c nextflow.config -c k8s.config -with-tower`；source 全文只有 `launch.py` 有 `nextflow run`。
- K8L-BUNDLE-04：samplesheet 路徑欄必須在掛載路徑底下；本機其他路徑、`s3://`、`gs://`、`az://` → 拒絕，訊息說明檔案要先放進 PVC。
- K8L-BUNDLE-05：Pod 名規則（含 `_` 的 run 名轉換、長度截斷、轉換後撞名）；同名 Pod 已存在 → 拒絕不覆蓋。
- K8L-BUNDLE-06：續跑／原樣重跑對 K8s 拒絕，訊息含 Kubernetes、不含 AWS。
- K8L-BUNDLE-07：自訂組合（composed）送 K8s → 拒絕（同其他雲端）。
憑證與環境：
- K8L-CRED-01：每次假 `runner` 收到的 env 沒有 `ABF_*`、沒有 argv 中的 kubeconfig 路徑或內容；`KUBECONFIG` 只在 env。
- K8L-CRED-02：argv、manifest（stdin）、日誌、ledger 搜不到假憑證。
- K8L-CRED-03：憑證檔缺／權限不是 600／`kubectl` 缺 → 拒絕，`runner` 一次都不呼叫。
- K8L-CRED-04：任何一次呼叫的 argv 不含 `use-context`、`set-`、`--all`、`-l`、`--selector`、`delete pvc`。
確認與憲法：
- K8L-CONF-01：未確認／雜湊不符／已用過／種類是 cancel → refused，`runner` 0 次、無新檔。
- K8L-CONF-02：每個會寫入叢集的 `kubectl` 動詞（`create`、`delete`）只出現在答 y 後的路徑。
- K8L-CONF-03：平台套件不啟動任何程式；`k8s_launch.py` 不含 `nextflow run`、`sbatch`、`subprocess`。
- K8L-CONF-04：`pyproject.toml` 無 `kubernetes` 套件；MCP 工具仍 12。
送出與取消：
- K8L-RUN-01：成功路徑只呼叫預期的 `kubectl` 序列（預檢、get pod、寫檔、create、get phase）。
- K8L-RUN-02：預檢任一項 fail → 不 create。
- K8L-RUN-03：Pod 起不來（phase `Failed`）→ 回報白話與 log 尾端，不重試。
- K8L-CANCEL-01：取消只送一次 `delete pod <名> --wait=false`；Pod 名或命名空間對不上 → 不送。
- K8L-CANCEL-02：無 Pod 名 → 白話拒絕；訊息提醒檢查 task pods。
畫面與文件：
- K8L-SCREEN-01：第一段含 `K8S_COST`，全文無金額；K8L-SCREEN-02：Slurm／gcb／aws／azure 畫面位元級不變；K8L-SCREEN-03：CLI 用詞只對 K8s 改變。
- K8L-DOC-01/02/03：PLATFORM.md、SEQERA_PARITY.md、TESTING.md 對應段落。

## 必須更新的既有斷言（有意更新；其他一律不准動；PR 逐條寫「以前／以後／理由」）
開工前先跑 `git grep -nE "CHECK_ONLY_TYPES|k8s-launch|尚未支援送出" -- platform docs`，以實際結果為準。origin/v3@02597261 的清單：
- `platform/tests/test_k8s_ce.py:734`（`CHECK_ONLY_TYPES == (K8S,)`）→ `== ()`，並加 `K8S in PLATFORM_HOST_TYPES`。
- `platform/tests/test_k8s_ce.py:758`（拒絕訊息含「尚未支援送出」與 `k8s-launch`）、`:968`（`"k8s-launch" in msgs["launch"]`）→ 改成只對未開的種類斷言，`launch_nextflow` 改放行。
- `platform/tests/test_aws_ce.py:907`、`test_gcb_ce.py:853`、`test_azure_ce.py:721`、`test_aws_launch.py:1011`（含 :1018 附近 `startswith("CHECK_ONLY_TYPES")`）、`test_azure_launch.py:983`（含 :990 附近）→ `CHECK_ONLY_TYPES == ("k8s-platform",)` 改 `== ()`，`PLATFORM_HOST_TYPES` 期望值加 K8S；`CHECKABLE` 期望值照新組合。
- `docs/TESTING.md:837` 的 TC-156 敘述若被測試逐字釘住，只做最小改動。
- 其他任何既有斷言要變動 → 回報 BLOCKED，不自行判斷。不准動 Slurm、gcb、aws、azure 的內容包、畫面、`head.sh`、取消訊息斷言。

## 完成標準（done when）
- 新測試先紅後綠；全套綠（含 `tests/platform_test.sh`、`no_second_run_state_test.sh`、`credentials_stay_in_settings_test.sh`）；已知環境紅依 dev-plans README 通例；其他四型別的內容包、畫面、取消訊息位元級不變（兩分支輸出比對貼 ledger）；MCP 工具仍 12。
- `git diff --name-only` 不含 `.github/`、憲法、版本號檔、`web.py`、`web_board.py`、`web_settings.py`、`static/*`、模板、已安裝 plugin 副本。
- 手動（維護者；**需要一個真的 K8s 叢集，會花錢，屬 C 級須維護者同意**；測試全綠不代表要做）：
  1. 平台主機有 `kubectl`；kubeconfig 在 `ABF_STATION_KUBECONFIG`（600）；k8s-ce 預檢 `available`。
  2. 叢集：PVC 為 `ReadWriteMany`；serviceAccount 有權建立／刪除 Pod（RBAC 見文件）；主控 Pod 映像拉得到。
  3. 送最小 samplesheet（檔案已放 PVC）；畫面第一段見帳單句；答 y 才建立 Pod。
  4. Pod 變 `Running`，task pods 出現，平台 run 頁有進度（`-with-tower` 通），結果在 PVC。
  5. 中途取消：確認主控 Pod 被刪，**判決 task pods 是否一併消失**；沒清乾淨記進 ledger 回報，不自行加刪除路徑。
  6. 資料庫、`ce show`、畫面、日誌、manifest 搜不到憑證片段。
- 文件：TESTING.md「k8s-launch」小節寫明手動驗收 1–6，列在「Needs human」之下。

## 環境事實
- 官方〔https://docs.seqera.io/nextflow/kubernetes，2026-10-29 讀〕：可從叢集內的 pod 直接 `nextflow run`，pod 必須用與設定相同的 PVC 名稱與掛載建立；用 Fusion 時可從任何連得到叢集的機器啟動；`kuberun` 已過時；`workDir` 必須在共用 PV（或 Fusion 的物件儲存）；`storageClaimName`、`storageMountPath`（預設 `/workspace`）。〔查不到〕：`k8s.context`、`k8s.namespace`、`k8s.serviceAccount` 的語意（該頁指向 `k8s` 設定範圍頁，本次未讀）；取消／終止時 pods 是否被刪（該頁未說）。
- origin/v3@02597261：`compute_envs.py:35-46`（常數與 `CLOUD_JOB_KINDS`）、`:538-573`（`_K8S_CONFIG`、`_check_k8s`）、`:654-655`（clean 分派）、`:929` `snapshot`；`jobs.py:95-120`（`_target`）；`launch.py:160-198`（`snapshot_ce`）、`:390`（`_tower`）、`:511-530`（`render_bundle`）、`:1596-1610`（`run_launch` 分派）、`:1774-1785`（`run_resume`）；`cancel.py:34-36`；`fetch.py:18`；`gcb_launch.py:232`（`_cancel_head`：以 pid 為基礎，K8s 不能重用，需另寫 Pod 版）；`k8s_preflight.py:21-29`（常數）、`:41` `clean_environment`、`:65` `_kube_env`、`:91` `run_preflight`；`handlers.py:83-86`。
- 測試指令（專案根 `CLAUDE.md`「For the executor and verifier」）：單檔 `ABF_PYTEST_TARGETS=tests/test_k8s_launch.py bash tests/platform_test.sh`（於 `platform/`）；全套在 WSL 跑，超過 10 分鐘，用 `run_in_background` 並輪詢，測試跑完前不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不建立或修改 RBAC（Role／RoleBinding）、PVC、命名空間、serviceAccount；只在文件寫出需要的權限。
- 不做 Fusion 路線（物件儲存 workDir）。
- 不做上傳（資料進 PVC 靠使用者自己）、清理（`k8s-clean`）、續跑、費用預估與上限、`fetch_run_records`／`read_task_log`／`list_site_files`、自訂組合。
- 不用 label selector 或 `--all` 刪 task pods；不加第二條刪除路徑。
- 不改網頁；不改資料表；不新增環境設定鍵。

## 裁決
以下皆為提案，**待 developer-agent 確認**。
1. **主控程序放哪裡？** 提案：叢集裡的一個 Pod（作法 3），因官方說非 Fusion 時主控程序要掛同一個 PVC。替代：平台主機上跑 `nextflow run` 並用 Fusion（需 Fusion 授權與設定，超出本片）。若 developer-agent 認為「只做 Pod 版」太大，這是整片的前提，請先裁決再派。
2. **主控 Pod 用哪個映像？** 提案：站台設定檔新增一個鍵 `k8s_head_image`（代理側設定，不進環境表、不進資料庫），預設不給；沒設就拒絕並說明怎麼設，由管理者釘一個版本如 `nextflow/nextflow:<版本>`。〔查不到〕本次未核對官方映像標籤與是否需要 `bash`、`git`；executor 不得自行猜標籤。
3. **進度回報與檔案怎麼進 PVC？** 提案：(a) 進度走 `direct` 模式，要求 https 的 `platform_public_url`，否則白話拒絕；(b) 執行檔不用 `kubectl cp`（需要先有 Pod），改為把檔案內容放進主控 Pod 的啟動命令之前的 init 步驟：manifest 裡用 `emptyDir`＋命令以 heredoc 寫檔，再 `cp` 到 PVC 的專屬資料夾。**這兩點都沒有現成範本，是本片最大的不確定處**；若 executor 覺得 (b) 會讓 params 內容落進 manifest 日誌，停下回報 BLOCKED。
4. **`slurm_job_id` 欄位放什麼？** 提案：沿用欄位、放 0 以外固定占位（例如 1），真正識別用 bundle 內的 `pod_name`；`cancel` 核對 Pod 名而不是 pid。替代：改欄位名（要 migration，不建議）。
5. **要不要同時支援 `k8s.context`？** 提案：不寫進 `k8s.config`（Pod 內用叢集身分）；context 只給代理的 `kubectl --context`。
6. **Pod 名與 run 名的轉換**（作法 3）是否接受？替代：限制 K8s 環境的 run 名不得含 `_`（改動 `RUN_NAME` 規則，影響面大，不建議）。
7. **主控 Pod 結束後要不要自動刪？** 提案：不刪（`restartPolicy: Never` 留著看 log），清理留給 `k8s-clean`。
8. **車道**：提案 `L40-k8s-launch`，等 L2 上沒有其他動 `compute_envs.py`／`jobs.py` 的任務時再派。

### developer-agent 確認（2026-10-29 21:0x）
1. 定案：主控程序＝叢集內一個 Pod，掛同一個 PVC。不做 Fusion 版。
2. 定案如提案：站台設定 `k8s_head_image` 必填、不給預設；沒設就白話拒絕並說明怎麼設。executor 不得自訂映像標籤，測試用假值。
3. (a) 定案如提案（direct 模式、要求 https 的 `platform_public_url`）。(b) **改判**：不把檔案內容寫進 manifest（`kubectl get pod -o yaml` 看得到，會洩漏 params）。改成代理先用 `kubectl create secret generic <pod 名>-bundle --from-file=...` 建一個 Secret 裝 bundle 檔，主控 Pod 以唯讀 volume 掛載，啟動時 `cp` 到 PVC 專屬資料夾後再 `nextflow run`。manifest 與日誌裡不得出現任何 bundle 檔內容（加一條測試：manifest 文字不含 params 的值）。Secret 的清理留給 k8s-clean，與裁決 7 一致。
4. 定案如提案（占位值＋bundle 內 `pod_name`；cancel 核對 Pod 名）。不改欄位名、不需要 migration。
5. 定案如提案。
6. 定案如提案（作法 3 轉換），轉換規則要有單元測試含 `_`、大寫、超長名。
7. 定案如提案：不自動刪。
8. **定案：等 L38 k8s-kubeconfig-paste-rule 合併後才派**（它也改 `compute_envs.py`）。
9. 新增：所有 kubectl 呼叫在測試裡一律用假 kubectl（PATH 上的腳本，記錄參數），**不碰真叢集**。真實叢集驗收會花錢＝C 級，列進 PR 的 Needs human，不在本片做。取消時 task pods 是否一併刪除：不在本片自加刪除路徑，同樣列進 Needs human。
10. 主計畫 C-2 寫 `local_runner.py` 與實作不符：屬總表文字落差，不在本片處理。

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
