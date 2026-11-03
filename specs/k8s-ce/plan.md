---
id: k8s-ce
title: Kubernetes 計算環境類型：能建立、驗證、存放、唯讀預檢（kubeconfig 只放平台主機檔案，預檢不花錢、不寫叢集）
branch: feat/k8s-ce
tier: B
kinds: backend
lane: L2-platform-ce
after: azure-launch merged into v3（已合，PR #258，v3@e8619e2）；L2 車道上若另有 aws／azure 的 upload／clean 任務未合，先合完再開工
base: origin/v3@e8619e2（2026-10-29 `git fetch` 後量的）。以下行號為語意提示，開工一律用 `git show origin/v3:<檔>` 重新定位
source: memory/PLAN-abf-v3-replan-2026-10.md 的 C-5（「Azure Batch／K8s：同模式」，第 169 行）；Azure 那半已完成（azure-ce-type、azure-launch），本片只做 K8s 的「建立＋唯讀預檢」，做法仿 memory/dev-plans/azure-ce-type.md
---

# k8s-ce

> 本檔由 developer-agent 的子 agent 起草（2026-10-29），**待 developer-agent 裁決「待裁決」各點後才派工**。**只處理 C-5 的 Kubernetes 計算環境類型（`k8s-platform`）**：可以建立、驗證、儲存、預檢。**不送出、不取消、不花錢、不寫叢集**；真的在 K8s 上跑 Nextflow 是之後的 `k8s-launch`，不在本任務。B 級 → verifier 通過＋CI 綠由 developer-agent 自合。
> 車道 L2（`compute_envs.py`、`jobs.py`、`cli.py`），不可與其他動這三檔的任務平行。
> 與 azure-ce-type 的最大差別：現在 `CHECK_ONLY_TYPES == ()`，本任務要把它改成 `(K8S,)`，所以**有一批「釘住 `== ()`」的既有斷言必須更新**（見「必須更新的既有斷言」，這是前兩次 BLOCKED(contract) 的病因，已逐條列出）。

## 目標
讓管理者能用 `abf-platform ce create --platform k8s-platform --agent <平台主機上的代理> --credentials <名字> --context <kubeconfig context> --namespace <ns> --storage-claim <pvc> --work-dir /workspace/work [--storage-mount-path /workspace] [--service-account <sa>]` 登記一個 Kubernetes 環境，由**平台主機上的站台代理**用 `kubectl` 做唯讀檢查：設定合不合規、kubeconfig 檔讀不讀得到、context 在不在檔裡、命名空間裡的 PVC 存在且 `Bound`、存取模式含 `ReadWriteMany`、（有設時）service account 存在。結果記成 `available` 或 `invalid`。

為什麼這樣切（同 aws／azure）：①雲端用戶不裝站台代理，代理裝在平台主機；②kubeconfig 可能內含 token／憑證，只放代理那一側的檔案，資料庫只存憑證**名字**（`credentialsId`）；③預檢全是 `kubectl get`／`kubectl config get-contexts`，沒有任何會改叢集的動詞，所以不計費、不寫叢集；④launch 留給 `k8s-launch`，在那之前 `available` 的 K8s 環境**不能被選去送出**，也不會被自動挑為主要環境。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md`（行號未在本次重驗）：
- 「**C-5** Azure Batch／K8s：同模式」（第 169 行）→ 照 C-4／Azure 的模式：類型常數、設定鍵規則、憑證檔在代理側、預檢唯讀、launch 另做。
- 「10-21，他定：雲端優先於畫布；雲端用戶不裝站台代理。」→ K8s 環境沒有「使用者自己的代理」；預檢由平台主機上的代理做。
- 「四種計算環境都建：nano4 → Google Batch … → AWS Batch → Azure／K8s。架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（第 40 行）→ 憑證與環境分開，環境只記憑證名字。
- 「費用顯示美元、每人每月上限」（第 16 行）→ 本片不碰費用、不加幣別欄位。
- 「撞牆時先砍 …… AWS／Azure」（第 20 行）→ 本片刻意小：只做建立＋預檢。
- 交辦原話：「create + free read-only preflight only … NO launching, no cost, no writes to the cluster」→ 每條 kubectl 都要被測試證明是唯讀。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/compute_envs.py`（新常數 `K8S = "k8s-platform"`；`CHECK_ONLY_TYPES = (K8S,)`，**該行行尾註解「新雲端類型先放這裡，只開預檢」必須保留**，既有測試掃這行；新增 `_K8S_*` 規則與 `_check_k8s`；`clean` 分派加一支；`snapshot` 加 K8s 分支；`_VALUE_PATTERNS` 不必加，見作法 3）
- `platform/abf_station/k8s_preflight.py`（新；仿 `azure_preflight.py`；函式皆可注入）
- `platform/abf_station/handlers.py`（import 與 preflight 分支旁加 K8s 分支）
- `platform/abf_platform/jobs.py`（`_target` 的 CHECK_ONLY 拒絕訊息改成依類型取名，見作法 7；只動這一處）
- `platform/abf_platform/cli.py`（`_config_from_args` 旗標對照＋`add_argument` 區加 `--context`、`--namespace`、`--storage-claim`、`--storage-mount-path`、`--service-account`；`cmd_ce_preflight` 已是 `PLATFORM_HOST_TYPES + CHECK_ONLY_TYPES`，不必改）
- `platform/tests/test_k8s_ce.py`（新）
- 既有測試只改「必須更新的既有斷言」列的幾處：`test_station_envs.py`、`test_station_docs.py`、`test_gcb_ce.py`、`test_aws_ce.py`、`test_azure_ce.py`、`test_aws_launch.py`、`test_azure_launch.py`、`test_gcb_launch.py`
- `docs/PLATFORM.md`（型別表 K8s 列、第 8 節那段「ten types」句、新增「Kubernetes」小節）
- `docs/SEQERA_PARITY.md`（F 節說明段落末尾補一句、K8s 列）
- `docs/TESTING.md`（新增「Kubernetes environment (k8s-ce)」小節，仿 Azure 小節）
- `specs/k8s-ce/ledger.md`（新，executor 進度帳本）

**不准碰**：網頁相關檔（`web.py`、`web_board.py`、`static/*`、`DESIGN.md`、`test_web_*`）、`abf_launch/`、`gcb_preflight.py`、`aws_preflight.py`、`azure_preflight.py`（只 import 私有輔助，不改）、`launch.py`、`cloud_store.py`、`clean.py`。

## 作法
1. **型別常數**：`PLATFORM_HOST_TYPES` **原樣保留** `(GOOGLE_BATCH, AWS, AZURE)`（把 K8s 放進去會讓它悄悄獲准排 `launch_nextflow`／`clean_work`／`put_upload`，也會被 `cloud_store`、`launch.py` 依賴）。新增 `K8S = "k8s-platform"`，`CHECK_ONLY_TYPES = (K8S,)`。`CHECKABLE` 的組法不變，結果自動變成 `(SUPPORTED, GOOGLE_BATCH, AWS, AZURE, K8S)`。**`CLOUD_JOB_KINDS` 不加 K8s**（它是「可送出類型的允許表」；K8s 不在表內，`jobs._target` 走 CHECK_ONLY 分支只放行 `preflight`）。
2. **K8s 設定鍵（`_K8S_CONFIG = _COMMON_CONFIG + (...)`，仿 `_AZURE_CONFIG`）**。鍵名避開 `key`／`secret`／`token`（`common.is_secret_name` 會擋）：
   | 鍵 | 規則 | 對應 Nextflow（已讀官方頁，見環境事實） |
   |---|---|---|
   | `context` | 必填；kubeconfig 裡的 context 名；保守規則 `^[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,252}\Z`（EKS／GKE 自動產生的 context 名含 `:`、`/`、`@`；官方未明定格式，見 UNVERIFIED） | `k8s.context` |
   | `namespace` | 必填；DNS 標籤保守規則 `^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?\Z`。Nextflow 預設是 `default`，本計畫要求明寫（待裁決 2） | `k8s.namespace` |
   | `storageClaimName` | 必填；DNS 子網域保守規則 ≤253 字、小寫英數與 `-`、`.`、頭尾英數 | `k8s.storageClaimName` |
   | `storageMountPath` | 選填；絕對路徑，預設 `/workspace`（存的時候若沒給就補 `/workspace`，與 Nextflow 預設一致）；過 `path_problem` | `k8s.storageMountPath` |
   | `workDir` | 必填；絕對 POSIX 路徑，**必須在 `storageMountPath` 底下（`workDir` 以 `storageMountPath + "/"` 開頭，不可等於它）**；沿用 `path_problem`／`normalize_path`（去結尾斜線、拒 `..`、控制字元、超長） | `workDir` |
   | `serviceAccount` | 選填；同 PVC 名規則 | `k8s.serviceAccount` |
   | `maxvCpus`、`spot` | **不收**（K8s 沒有對應；未知鍵拒收） | 無 |
   | `nextflowConfig`、`environment`、`preRunScript`、`postRunScript` | 沿用共用檢查 | 共用 |
   - 未知鍵 → `unknown setting for a Kubernetes environment: X (known: …)`（句型同 AWS／Azure）。**舊的 `UNSUPPORTED` 範例記錄用的鍵 `namespace`、`storageClaimName`、`storageMountPath`、`workDir` 都是已知鍵**，所以舊 K8s 列只缺 `context`：`ce update`／`ce preflight` 會報「context is required」並點名鍵；舊列有其他未知鍵時才是 unknown。
   - 全部錯誤一次列出、每個點名鍵、被拒的值最多顯示 60 字（沿用 `_shown`）。
   - **`agent` 必填**：訊息句型同 Azure（「需要指定一個站台代理，就是平台主機上的那個」）。
3. **憑證只放名字**：`credentialsId`（CLI `--credentials`）只是標籤；沿 azure 裁決 12：**建立時可為空**，由第一次預檢的 `credential_name` 報 fail。`credential_findings` 原樣套用。**kubeconfig 是檔案，平台從不讀它**，所以不需要新的 `_VALUE_PATTERNS`；但要有測試證明「把 kubeconfig 片段（`client-certificate-data:`、`token:` 開頭行）貼進 `description`／`nextflowConfig`」會被**既有**規則擋下，若既有規則擋不住，列在 ledger 並回報（不要擅自加規則，見待裁決 6）。
4. **kubeconfig 位置（代理那一側）**：`k8s_preflight.credentials_path(settings_file, environ=None)` ＝ 環境變數 `ABF_STATION_KUBECONFIG`，否則 `<deployment>/_personal/kubeconfig`（寫法照 `azure_preflight.credentials_path`）。檔案永遠不進 DB、日誌、任何回傳；程式**不解析 YAML**（代理只用標準函式庫），只檢查「存在、一般檔案、POSIX 上 `mode & 0o077 == 0`、大小 ≤1 MB」，內容是否正確由 `kubectl` 自己讀、由 `context` 檢查回報。
5. **預檢（`k8s_preflight.py`）**——唯讀、不計費、不寫叢集。簽名 `run_preflight(env, *, cred_path, now=time.time, runner=None, which=None, stat=os.stat) -> {"ok","checks":[{"name","status","detail"}]}`；`runner(argv, env, timeout)` 回 `(returncode, output_tail)`，預設走 `site.run_fixed`（固定 argv、無 shell），逾時 30 秒、輸出截 300 字。`_scrub`、`_check`、`_run` 照 azure 的做法 import 自 `gcb_preflight`。**不 import `kubernetes` Python 套件**。**檔案內不得出現小寫字串 `kubernetes`**（`test_station_static.py::test_agent_stricter_scan_no_other_network_or_cloud_library` 逐行掃 `abf_station/*.py` 的 `r"kubernetes"`，連註解、字串、URL 都算；寫 "Kubernetes" 大寫或拆字 `"kuber" + "netes"`，azure 的先例是拆字）。檔頭 40 行內要有 `# Nothing existing: …`（TC-070），理由寫：搜過 Nextflow 的 k8s 執行器與 Seqera 的 Kubernetes 表單，沒有免費離線的預檢可用；Python 的 `kubernetes` 套件被 TC-085 禁用，所以走 `kubectl` 命令列。
   `clean_environment(ce)`：代理在組命令列前**再驗一次**，只留 `name, platform, credentialsId, context, namespace, storageClaimName, storageMountPath, workDir, serviceAccount`，重用 `compute_envs` 的 `_K8S_*` 規則（`_check_k8s`），不合規 → `rules.Refusal`。
   | 檢查名 | 做什麼 | 通過／失敗 |
   |---|---|---|
   | `credential_name` | `credentialsId` 有設 | 沒設 → fail |
   | `credential_file` | 存在、一般檔案、POSIX 上 `mode & 0o077 == 0`、≤1 MB；Windows 略過權限位並明說 | 缺檔 → fail，detail 含**應放的路徑**與 `chmod 600` |
   | `kubectl` | `which("kubectl")`；沒有 → **unchecked** | |
   | `context` | `kubectl config get-contexts -o name`（只讀本機檔，不連叢集；官方頁未明說，見 UNVERIFIED）；輸出的行裡含 `context` → pass | 不在 → fail「context X 不在這份 kubeconfig」，**不列出其他 context 名** |
   | `pvc` | `kubectl get pvc <storageClaimName> --namespace <ns> --context <ctx> --request-timeout=20s -o jsonpath={.status.phase}`；輸出 `Bound` → pass；`Pending`／`Lost` → fail；rc≠0 → fail＋`_scrub` 後前 300 字。這一項同時證明叢集連得到、憑證有效、命名空間存在、有權讀 PVC | |
   | `pvc_access` | 同上指令但 `-o jsonpath={.spec.accessModes[*]}`；輸出含 `ReadWriteMany` → pass，否則 fail「Nextflow 官方文件要求 ReadWriteMany」（待裁決 3）。`pvc` 沒過時此項為 unchecked | |
   | `service_account` | 有設 → `kubectl get serviceaccount <sa> --namespace <ns> --context <ctx> --request-timeout=20s -o name`；rc 0 → pass；沒設 → pass，detail「未設定，使用命名空間預設帳號」 | |
   - 憑證檔不可用或沒有 `kubectl` 時，`context`、`pvc`、`pvc_access`、`service_account`（有設時）為 `unchecked` 且 `runner` 一次都不呼叫。`context` 沒過時，後三項同樣 unchecked、不再呼叫叢集。逾時只讓該項 fail。任何一項不是 pass 就不是 `available`。
   - **每次呼叫的環境變數**（`_kube_env`）：從 `os.environ` 複製，**刪掉**所有 `ABF_*`、`KUBE*`（含 `KUBECONFIG`、`KUBECACHEDIR`）；再設 `KUBECONFIG=<憑證檔路徑>`、`KUBECACHEDIR=<每次新建的空暫存目錄>`（`KUBECACHEDIR` 是否被 kubectl 認得：UNVERIFIED，見環境事實；認不得也無害）。**路徑只在 env，不在 argv**；argv 只有資源名稱、命名空間、context 名、逾時（都不是祕密）。呼叫完刪暫存目錄。
   - **絕不呼叫** `kubectl config use-context`／`set-*`（會改 kubeconfig 檔本身），一律用 `--context` 旗標。
   - 結果走既有紀錄路徑：`jobs` 的 preflight 工作 → `compute_envs.apply_preflight`，`verdict_message` 不改。
6. **代理接線（handlers.py）**：`kind == "preflight"` 且 `ce["platform"] == k8s_preflight.TYPE` → `k8s_preflight.run_preflight(k8s_preflight.clean_environment(ce), cred_path=k8s_preflight.credentials_path(ctx.settings_file))`，回 `("done", _verdict(res["checks"]))`。K8s 環境**不得**落到 Slurm 的 `rules.clean_environment` 路徑。
7. **`jobs._target`**：目前的 CHECK_ONLY 分支把 "Azure Batch" 與 "azure-launch" 寫死（Azure 已在 `CLOUD_JOB_KINDS`，這句其實已是死碼，現在 K8s 讓它復活）。改成依類型取名：`%s is a Kubernetes environment: it is checked on the platform host, and launching on it is not built yet (尚未支援送出；下一步 k8s-launch)`，用 `compute_envs.KINDS[row["platform"]]` 取類型名（不再寫死）。AWS／Azure／Google 的拒絕句與 `put_upload` 的拒絕句**一個字都不改**。（我 grep 過 `尚未支援送出`，只有 azure-ce 的 docstring 提到，沒有測試釘這句。）
8. **`snapshot`**：`v["platform"] == K8S` 時回 `{name, platform, credentialsId, context, namespace, storageClaimName, storageMountPath, workDir, serviceAccount}`。其他類型的回傳一個字都不變。
9. **送出與自動選擇不放行（不改程式，要有測試）**：`abf_launch/build.py:117` 的 `primary_environment` 只選 `SUPPORTED`（Slurm）且 `available`；K8s 永遠不被自動挑；`target_problem` 走 `jobs.check_target` → 作法 7 的拒絕。
10. **CLI**：新旗標 `--context`、`--namespace`、`--storage-claim`、`--storage-mount-path`、`--service-account` 對應 config 鍵 `context`、`namespace`、`storageClaimName`、`storageMountPath`、`serviceAccount`。**說明文字不得含 `launch`／`submit`／`cancel` 這幾個字**（`test_station_envs.py` TC-060 掃整份 help），用 "Kubernetes: …" 直述即可。`_default_agent` 只對 `SUPPORTED` 生效，K8s 必須明寫 `--agent`。
11. **不需要 migration**：同一張 `compute_envs` 表的新 `config_json` 鍵；`status` 沿用既有五種值。
12. **文件**：`docs/PLATFORM.md` 型別表 K8s 列改為 `checked on the platform host (launch: not yet)`；第 8 節那段句子改為（**一字不差，供測試比對**）：`Slurm, Google Cloud Batch, AWS Batch and Azure Batch can run; Kubernetes can be created and checked on the platform host (launch: not yet); the other nine types can be modelled only`，該段出現「ten」「Fourteen types」之處同步修成 nine，且這句至少出現 2 次（azure-launch 的測試用 `count >= 2`）；新增「Kubernetes」小節（鍵表、七個檢查名、kubeconfig 位置與 `ABF_STATION_KUBECONFIG`、`chmod 600`、「預檢不計費：只讀，不建任何東西」、平台主機要裝 `kubectl`、PVC 必須事先由營運者建好、kubeconfig 若用 exec 型登入外掛會在代理主機執行該外掛——kubeconfig 是營運者自己放的信任檔）。`docs/SEQERA_PARITY.md`：F 節說明段（"Pre-flight checks:" 那段）**只在句尾追加** `; for Kubernetes the same agent runs the read-only checks (create + check; launch not yet)`，不動既有子句；K8s 列改為 `Have (create + check); launch not yet`，結尾維持 `[ ] |`。`docs/TESTING.md` 新增手動小節。範例一律用 `lab-context`、`lab-ns`、`lab-pvc`、`/workspace/work`、`lab-sa`，不得出現真實叢集名、位址或 token。

## 失敗先行測試（`platform/tests/test_k8s_ce.py`；現在都會紅；全部用假 `runner`、假 `which`，不碰網路；仿 `platform/tests/test_azure_ce.py` 的夾具；檔首 40 行內要有 `# Nothing existing: <≥15 字理由>`，TC-070 scope 規則）
ID 一律 `K8S-NN`。常數：`CTX="lab-context"`、`NS="lab-ns"`、`PVC="lab-pvc"`、`MOUNT="/workspace"`、`WORKDIR="/workspace/work"`、`SA="lab-sa"`、`CRED="k8s-lab"`；`good_config()` ＝ `{"context":CTX,"namespace":NS,"storageClaimName":PVC,"workDir":WORKDIR}`；`fields()` 帶 `agent="a1"`。**假 kubeconfig 內容一律用字串拼接**（`tests/credentials_stay_in_settings_test.sh` 掃全 repo）：`KTOK = "MARKER" + "KUBETOK" + "A" * 40`，`KCFG = "apiVersion: v1\nkind: Config\nusers:\n- user:\n    " + "to" + "ken: " + KTOK + "\n"`。

建立與驗證：
- K8S-01 `test_a_valid_k8s_environment_is_created_as_creating`：`good_config()` ＋ `serviceAccount` → `status=="creating"`、`config["storageMountPath"]=="/workspace"`（沒給就補預設）、`workDir` 去結尾斜線、`message` 含「waiting for the first preflight」。
- K8S-02 `test_required_settings_and_agent`：`context`、`namespace`、`storageClaimName`、`workDir` 各缺一個 → 錯誤點名該鍵；缺 `agent` → 含「需要指定一個站台代理」。
- K8S-03 `test_context_rules`：`lab-context`、`arn:aws:eks:eu-west-1:123456789012:cluster/x` 型字串（用拼接組）、`gke_proj_zone_name` 通過；`""`、`a b`、`a; b`、`-x`、含換行被拒。
- K8S-04 `test_namespace_and_names_follow_dns_rules`：`lab-ns` 通過；`Lab`、`-a`、`a-`、64 字、`a_b` 被拒（namespace 與 storageClaimName／serviceAccount 各測一次，後兩者允許 `.` 與到 253 字）。
- K8S-05 `test_workdir_must_be_inside_the_mount`：`/workspace/work`、`/workspace/a/b/` 通過；`/workspace`（等於掛載點）、`/data/work`（不在掛載點下）、`work`、`s3://b/x`、`/workspace/../x`、含控制字元被拒；`storageMountPath:"/mnt/vol"` ＋ `workDir:"/mnt/vol/w"` 通過，`workDir:"/workspace/w"` 被拒；`storageMountPath:"mnt"`（相對）被拒。
- K8S-06 `test_unknown_keys_are_refused`：`spot`、`maxvCpus`、`region`、`cluster`、`foo` 各被拒，訊息含 `unknown setting for a Kubernetes environment` 與已知鍵清單。
- K8S-07 `test_all_errors_are_listed_at_once_and_values_are_cut`：同時錯三鍵 → 一則訊息含三個鍵名；200 字壞值 ≤60 字。
- K8S-08 `test_shared_checks_apply`：`nextflowConfig` >20000 字、`environment` 鍵名不合規 → 與 Slurm 相同的拒絕。
- K8S-09 `test_create_without_credentials_is_allowed`：不給 `--credentials` → 建立成功（裁決 12 的先例），第一次預檢才報 `credential_name` fail。

憑證不進資料庫：
- K8S-10 `test_the_credential_is_only_a_name`：`credentialsId="k8s-lab"` 存下；config 裡沒有任何憑證鍵；含空白、`=`、`KTOK` 的 `credentialsId` 被拒。
- K8S-11 `test_a_kubeconfig_pasted_anywhere_is_refused_and_not_repeated`：把 `KCFG` 片段放進 `description`、`nextflowConfig`、`environment` 值 → 被**既有** `credential_findings` 擋下，錯誤訊息只含欄位路徑、不含 `KTOK`；DB 位元組找不到 `KTOK`。若有一種貼法擋不住，如實記在 ledger（見作法 3）。
- K8S-12 `test_a_key_named_field_is_refused`：config 有 `token`、`clientKey`、`password` → 被擋。
- K8S-13 `test_normal_values_are_not_mistaken_for_secrets`：`good_config()` 完整建立成功；普通 `description`（含 `context`、`token-free` 字樣）不被誤擋。
- K8S-14 `test_the_platform_does_not_read_the_kubeconfig`：把 `KCFG` 寫在代理部署的 `_personal/kubeconfig`，建立、列出、`ce show` 之後，`platform.db` 位元組與所有 CLI 輸出都找不到 `KTOK`。

預檢（假 runner，`monkeypatch.setattr(k8s_preflight, "_run", runner)`）：
- K8S-15 `test_every_check_is_reported_in_order`：七項依序為 `credential_name, credential_file, kubectl, context, pvc, pvc_access, service_account`，每項有 name／status／detail。
- K8S-16 `test_a_missing_credential_file_says_where_to_put_it`：沒檔 → `credential_file` fail，detail 含 `<deployment>/_personal/kubeconfig` 實際路徑與 `chmod 600`；後四項 unchecked；`runner` 呼叫 0 次；環境 `invalid`。
- K8S-17 `test_the_kubeconfig_location_follows_the_agents_setting`：設 `ABF_STATION_KUBECONFIG=<tmp>/x` 用該路徑；沒設用 `<settings 檔 parent.parent>/_personal/kubeconfig`。
- K8S-18 `test_a_kubeconfig_other_people_can_read_is_refused`（POSIX 專用）：0644 → fail 含 `chmod 600`；0600 → pass。Windows 版（假 `sys.platform=="win32"`）→ pass 且 detail 含「Windows 不檢查權限位」。資料夾 → fail「not a regular file」。
- K8S-19 `test_without_kubectl_nothing_is_run`：`which` 回 None → `kubectl` unchecked、後四項 unchecked、環境 `invalid`、`message` 含「kubectl」與「沒裝」；`runner` 0 次。
- K8S-20 `test_all_checks_passing_makes_the_environment_available`：假 runner 對 `config get-contexts` 回 `(0,"lab-context\nother")`、`phase` 回 `(0,"Bound")`、`accessModes` 回 `(0,"ReadWriteMany")`、`serviceaccount` 回 `(0,"serviceaccount/lab-sa")` → 七項皆 pass、`status=="available"`。
- K8S-21 `test_a_context_that_is_not_in_the_file_fails_without_listing_the_others`：輸出不含 `lab-context` → `context` fail、detail 含 `lab-context`、**不含**輸出裡其他 context 名；之後 `runner` 0 次呼叫。
- K8S-22 `test_a_pvc_that_is_missing_or_not_bound_fails`：rc≠0（`NotFound`）→ `pvc` fail 且 detail 含 `lab-pvc`；`Pending` → fail；`pvc_access` 為 unchecked。
- K8S-23 `test_a_pvc_without_readwritemany_fails_and_says_why`：`ReadWriteOnce` → `pvc_access` fail、detail 含 `ReadWriteMany`；`ReadWriteOnce ReadWriteMany` → pass。
- K8S-24 `test_the_service_account_is_checked_only_when_set`：沒設 → pass 且 `runner` 不為它被呼叫；設了而 rc≠0 → fail 且 detail 含 `lab-sa`。
- K8S-25 `test_an_api_failure_is_reported_trimmed_and_scrubbed`：`pvc` 回 `(1, 2000 字夾 KTOK 與 Bearer 字串)` → fail、detail ≤300 字、不含 `KTOK`。
- K8S-26 `test_a_timeout_fails_that_check_only`：`pvc` 的假 runner 丟 `TimeoutError` → fail 含「逾時」；`service_account` 仍被執行。（與 K8S-22 的 unchecked 規則對照：逾時算該項 fail，不連動後面；`pvc_access` 因 `pvc` 未過而 unchecked，`service_account` 與 `pvc` 無依賴所以照跑。）
- K8S-27 `test_the_commands_are_read_only`（**不花錢、不寫叢集的保證**）：記錄所有 argv；每條前綴必為 `kubectl config get-contexts`、`kubectl get pvc` 或 `kubectl get serviceaccount`；沒有任何一條含 `create`、`delete`、`apply`、`patch`、`replace`、`edit`、`exec`、`run`、`cp`、`scale`、`drain`、`cordon`、`taint`、`label`、`annotate`、`port-forward`、`proxy`、`attach`、`rollout`、`use-context`、`set-context`、`set-credentials`、`auth`、`logs`、`certificate` 這些字（**整詞比對**）。
- K8S-28 `test_the_kubeconfig_goes_in_the_environment_not_in_argv`：每次呼叫 env 有 `KUBECONFIG==<憑證檔路徑>`、`KUBECACHEDIR` 指向空暫存目錄；argv 不含憑證檔路徑、`KTOK`；env 不含 `ABF_` 開頭變數；測試先在自己環境設 `KUBECONFIG=X`、`KUBE_FAKE_HOST=Y`（名字用 `KUBE` 開頭的假變數，不要寫小寫 kubernetes）、`ABF_PLATFORM_TOKEN=T` 後，env 裡沒有繼承到 `X`／`Y`／`T`；呼叫後暫存目錄已刪。每條 get 指令的 argv 含 `--context lab-context`（或 `--context=lab-context`）、`--namespace lab-ns`、`--request-timeout`。
- K8S-29 `test_the_default_runner_is_a_fixed_argv_without_a_shell`：`subprocess.run` 以假物件替換 → 收到 `shell=False`、list 型 argv、`timeout=30`。
- K8S-30 `test_the_agent_judges_the_environment_again_before_it_builds_a_command`：`context:"x; touch c"`、`namespace:"A B"`、`storageClaimName:"q q"`、`workDir:"/etc/x"`、`credentialsId:"a b"` 各送進 `k8s_preflight.clean_environment` → `rules.Refusal`；`platform` 為其他類型 → 同樣被拒。

接線與 CLI：
- K8S-31 `test_create_queues_the_first_preflight_for_the_agent`：`ce create --platform k8s-platform --agent a1 --credentials k8s-lab --context lab-context --namespace lab-ns --storage-claim lab-pvc --work-dir /workspace/work`（代理在線）→ rc 0、輸出含「preflight queued」、`jobs` 表多一列 `preflight`、其 args 的 `ce` 即 `snapshot`，鍵集合恰為 `{name, platform, credentialsId, context, namespace, storageClaimName, storageMountPath, workDir, serviceAccount}`。
- K8S-32 `test_create_with_the_agent_offline_says_so`：代理離線 → 狀態仍 `creating`，`jobs` 沒有新列。
- K8S-33 `test_ce_preflight_prints_each_check`：`auto_serve` 夾具下 `ce preflight k1` → 每項印 `name: status - detail`。
- K8S-34 `test_cli_flags`：五個新旗標各進對應 config 鍵；help 文字不含 `launch`／`submit`／`cancel`。
- K8S-35 `test_other_types_are_unchanged`：Slurm、gcb、aws、azure 建立後仍各走自己的預檢與送出；四者 `snapshot` 與改動前逐鍵相同；`CLOUD_JOB_KINDS` 的四個項目不變（沿用 `test_aws_clean.py`／`test_azure_launch.py` 既有斷言，不重寫）。
- K8S-36 `test_jobs_other_than_the_preflight_are_refused_in_plain_words`：對 `available` 的 K8s 環境 `enqueue_*` 為 `launch_nextflow`、`cancel_run`、`clean_work`、`put_upload`、`list_site_files`、`pipeline_files` → 全 `JobRefused`，訊息含「Kubernetes」「尚未支援送出」「k8s-launch」，**不含** "Azure"、"AWS"、"Google"；`jobs` 表列數不變。
- K8S-37 `test_launch_is_refused_and_the_environment_is_never_auto_picked`：`build.target_problem(state,"k1","launch_nextflow")` 回非 None 的白話句；只有一個 `available` 的 K8s 環境時 `primary_environment` 回 None；有 `available` 的 Slurm 時選 Slurm。
- K8S-38 `test_another_users_k8s_environment_is_not_found`：B 以 `owner=` 取 A 的環境 → None；B 對它 `enqueue_preflight` → 與不存在相同的 `JobRefused` 文字。
- K8S-39 `test_updating_a_disabled_environment_queues_no_preflight`。
- K8S-40 `test_an_old_k8s_record_asks_for_the_missing_context`：直接 SQL 插一列 `k8s-platform`、`status='unsupported'`、config 為舊範例 `{"workDir":"/mnt/work","namespace":"nf","storageClaimName":"pvc-work","storageMountPath":"/mnt"}` → `ce list`／`ce show` 照常且仍 `unsupported`；`ce preflight` 與 `ce update`（不補 `context`）→ rc≠0，訊息點名 `context`；`ce update --agent a1 --context lab-context` → 成功並轉 `creating`。

範圍與靜態：
- K8S-41 `test_no_cloud_library_is_imported_and_no_forbidden_word_in_the_agent_package`：`k8s_preflight.py` 無 `import kubernetes`／`boto3`／`azure`／`google`／`requests`；**整個 `abf_station/` 沒有小寫 `kubernetes`**（直接重跑 `test_station_static` 那條規則的 regex）；`pyproject.toml` 不含 `kubernetes`。
- K8S-42 `test_the_platform_package_starts_no_program`：`abf_platform/` 底下沒有 `subprocess`、沒有 `kubectl` 字樣。
- K8S-43 `test_only_site_py_starts_programs`：`k8s_preflight.py` 不 `import subprocess`（TC-091 精神：只有 `site.py` 起程式）。
- K8S-44 `test_no_launch_or_write_code_for_k8s`：`abf_platform/`、`abf_station/` 原始碼沒有 `kuberun`、`kubectl apply`、`kubectl create`、`kubectl delete`、`-with-tower`（對 `k8s_preflight.py`）。
- K8S-45 `test_tool_list_unchanged_and_no_new_web_route`：MCP 工具名集合與改動前相同（**現況是 15 個，不是 Azure 計畫寫的 12**：`test_oauth_mcp.py:44`、`test_pat.py:383` 都釘 15）；測試寫法照 `test_azure_ce.py` 同名測試，但比較對象用「現有名單」而不是寫死數字；`web.py` 路由表不變。
- K8S-46 `test_docs_list_every_k8s_key_and_check`：`PLATFORM.md` 含 `` `context` ``、`` `namespace` ``、`` `storageClaimName` ``、`` `storageMountPath` ``、`` `workDir` ``、`` `serviceAccount` ``、七個檢查名、`ABF_STATION_KUBECONFIG`、`_personal/kubeconfig`、`預檢不計費`、`kubectl`、`ReadWriteMany`；第 8 節新句（作法 12）出現 ≥2 次且不再含 `the other ten`；`SEQERA_PARITY.md` 的 `k8s-platform` 列含 `Have (create + check); launch not yet` 且以 `[ ] |` 結尾，"Pre-flight checks:" 段仍含 Azure／AWS／Google 三個既有子句；`TESTING.md` 含 `k8s-ce`、`預檢不計費`、`git diff`、`TC`；文件無真實叢集位址、無 token 樣式。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」；行號取自 origin/v3@e8619e2，**用語意定位**）
**A. `CHECK_ONLY_TYPES` 不再是空 tuple、`CHECKABLE` 多一項（理由：K8s 是新的 check-only 類型；`PLATFORM_HOST_TYPES` 不變）**
| 檔：函式（約行） | 以前 | 以後 |
|---|---|---|
| `test_azure_ce.py::test_the_type_constants`（:720-722，TC-102） | `CHECK_ONLY_TYPES == ()`；`CHECKABLE == (SUPPORTED, gcb, aws, AZ)` | `CHECK_ONLY_TYPES == ("k8s-platform",)`；`CHECKABLE == (SUPPORTED, gcb, aws, AZ, "k8s-platform")`；上方「nothing is check-only any more」類註解一併改成說明 K8s |
| `test_azure_launch.py::test_type_constants_are_as_planned_and_nothing_indexes_them_by_position`（:985-987） | 同上 | 同上（`PLATFORM_HOST_TYPES` 與 `CLOUD_JOB_KINDS[AZURE]` 兩行不動；掃 `CHECK_ONLY_TYPES` 行含「新雲端類型先放這裡，只開預檢」的斷言不動，所以 compute_envs 那行註解要保留） |
| `test_aws_launch.py`（:985-986，TC-116／117／118／130 常數測試） | `CHECK_ONLY_TYPES == ()`；`CHECKABLE == (SUPPORTED, GCB, AWS, "azbatch-platform")` | `CHECK_ONLY_TYPES == ("k8s-platform",)`；`CHECKABLE` 尾端加 `"k8s-platform"`；:992 的註解行掃描不動 |
| `test_aws_ce.py::test_the_type_constants`（:905-908） | 同上 | 同上；歷史註解保留，加一行 "k8s-ce" |
| `test_gcb_ce.py::test_the_type_constants`（:851-854） | 同上 | 同上 |

**B. 「modelled only」的數量 10 → 9、K8s 從 UNSUPPORTED 名單移出（理由：K8s 不再是 unsupported）**
| 檔：函式（約行） | 以前 | 以後 |
|---|---|---|
| `test_station_envs.py::UNSUPPORTED`（:19-30，上方註解 "the 10 types"） | 含 `"k8s-platform": {...}` | 刪掉該項；註解改 "the 9 types"。**這份 dict 被 `test_aws_ce`／`test_azure_ce`／`test_gcb_ce` 匯入** |
| `test_station_envs.py::test_tc030_…`（參數化；函式名含 "ten"） | 10 個參數 | 9 個參數（函式名不改，避免動到測試 ID） |
| `test_station_envs.py::test_tc032_only_fourteen_types…`（:161） | `set(UNSUPPORTED) | {slurm, gcb, aws, azbatch}` 等於 `KINDS` | 集合加 `"k8s-platform"` |
| `test_gcb_ce.py::test_the_other_types_stay_unsupported`（:816） | `len(UNSUPPORTED) == 10` | `== 9` |
| `test_aws_ce.py::test_the_other_types_stay_unsupported`（:788） | `len(UNSUPPORTED) == 10 and AWS not in UNSUPPORTED` | `== 9 and …` |
| `test_azure_ce.py::test_the_other_types_stay_unsupported`（:899-901） | `== 10`；迴圈檢查 `("awscloud-platform","azcloud-platform","k8s-platform","eks-platform","gke-platform")` 都在 UNSUPPORTED | `== 9`；迴圈拿掉 `"k8s-platform"`（否則該斷言必紅） |
| `test_station_docs.py::test_tc077_the_parity_table_…`（:66-82） | 跳過清單四個類型；其餘列須含 "Modelled, needs a real account"；總數 `== 10` | 跳過清單加 `"k8s-platform"`（它的列改成 `Have (create + check); launch not yet`）；總數 `== 9` |
| `test_station_docs.py`（:41）、`test_station_envs.py::test_tc032`（:160） | `len(KINDS) == 14` | **不動**（K8s 沒有增減類型） |

**C. 文件句（理由：K8s 不再是 "modelled only"，原句不實）**
`Slurm, Google Cloud Batch, AWS Batch and Azure Batch can run; the other ten types can be modelled only` 被下列測試逐字比對，全部改成作法 12 的新句（只改這一句的字面，其餘斷言不動）：`test_aws_ce.py::test_docs_list_every_aws_key_and_check`（:924）、`test_azure_ce.py` 文件測試（:861，連同 `"the other eleven" not in d`，後半保留）、`test_azure_launch.py::test_platform_md_documents_azure_launch`（:1232，`count >= 2`）、`test_gcb_ce.py::test_docs_list_every_gcb_key_and_check`（:867）、`test_gcb_launch.py::test_docs_describe_the_launch_the_billing_sentence_and_the_requirements`（:1151）。

**D. 檢查過、確認不必動（請 executor 也各跑一次確認，列入 ledger）**
- `test_station_envs.py::test_tc085…`（:462，會在 PATH 放假的 `kubectl` 並要求沒被呼叫）：只迴圈 `UNSUPPORTED`，K8s 移出後不再涵蓋它，**不動**；它同時斷言 pyproject 無 `kubernetes` 套件、原始碼無 `import kubernetes`，新程式遵守即可。K8s 的「kubectl 只被預檢呼叫」由 K8S-27／28 負責。
- `test_station_envs.py:467` 與 `test_launch_cli.py::test_tc063`（:304）的假 `kubectl`：用的是 `azcloud-platform`，**不動**。
- `test_station_static.py::test_agent_stricter_scan_no_other_network_or_cloud_library`（:46，`r"kubernetes"`）：**不改規則**，新檔案要自己遵守（作法 5）。
- `test_station_envs.py` TC-060 的 help 掃描（`\blaunch\b|\bsubmit\b|\bcancel\b`）：新旗標說明要遵守，不改規則。
- MCP 工具數（15）：`test_oauth_mcp.py:44`、`test_pat.py:383/751`、`test_guidance.py:400`：本任務不新增工具，**全部不動**。
- `test_launch_bundle.py`、`test_cloud_cost.py`、`test_estimate_su.py`、`test_web_parity.py`：沒有指到 `k8s-platform`（已 grep），**不動**。
- `test_aws_clean.py:50/378`、`test_aws_upload.py:128`、`test_azure_launch.py:988`（`CLOUD_JOB_KINDS` 項目與長度）：K8s 不進該表，**不動**。
- `test_scope.py::test_tc070`：新 `.py` 檔頭要有 `# Nothing existing:` 標頭。
- `abf_launch/build.py:117` `primary_environment`：只選 `SUPPORTED`，K8s 不會被自動挑，程式不用改。
- **executor 在實作前先跑一次全套，找出任何本表沒列到的紅，列在 ledger；超出本表就回報 BLOCKED，不要自己改。** 已知環境紅：`test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched`，若它是唯一的紅視為綠。

## 完成標準（done when）
- 自動：K8S-01～46 綠；全套綠（在 WSL 跑 `tests/run_all.sh`）；MCP 工具數不變（15）；`git diff --name-only` 只含「範圍：檔案」列出的檔，不含任何網頁檔；上表 A／B／C 以外沒有任何既有斷言被刪除或放寬。
- 手動（維護者，有 K8s 叢集後做一次，**不計費、不寫叢集**）：營運者事先建好命名空間、`ReadWriteMany` 的 PVC（Bound）與（可選）service account；平台主機裝 `kubectl`，把 kubeconfig 放到 `<agent deployment>/_personal/kubeconfig`（600）；`abf-platform ce create --name k1 --platform k8s-platform --agent <代理> --credentials k8s-lab --context <ctx> --namespace <ns> --storage-claim <pvc> --work-dir /workspace/work`，看到七項檢查；全 pass 時 `ce show k1` 為 `available`；`ce show` 與 `platform.db` 搜不到 kubeconfig 任何片段；**同時驗證：①`kubectl config get-contexts -o name` 在離線時仍能列出 context、②`-o jsonpath={.spec.accessModes[*]}` 的輸出是以空白分隔的字串、③`KUBECACHEDIR` 是否生效（暫存目錄有沒有檔案）、④kubectl 用權限最小的帳號（只有該命名空間的 get pvc／get serviceaccount）時 `pvc` 檢查是否仍通過**——這四項在本計畫都是 UNVERIFIED，任何一項不成立就回報 developer-agent 改檢查方式，不要自己改。
- 文件：`docs/PLATFORM.md`、`docs/SEQERA_PARITY.md`、`docs/TESTING.md` 依作法 12 更新。

## 環境事實
**平台內部（origin/v3@e8619e2 現況，2026-10-29 讀 `git show origin/v3:<檔>`）**
- `compute_envs.py`：`KINDS` 14 個識別字，`k8s-platform` 為 `Kubernetes`；`SUPPORTED="slurm-platform"`；`PLATFORM_HOST_TYPES=(GOOGLE_BATCH, AWS, AZURE)`；`CHECK_ONLY_TYPES=()`（行尾註解「新雲端類型先放這裡，只開預檢」）；`CLOUD_JOB_KINDS` 每類型允許表（Azure 不含 `clean_work`／`put_upload`）；`CHECKABLE=(SUPPORTED,)+PLATFORM_HOST_TYPES+CHECK_ONLY_TYPES`。現在 `k8s-platform` 走 `_check_other`（只有共用檢查），狀態 `unsupported`。
- `jobs.py::_target`：`CLOUD_JOB_KINDS` 分支之後的 CHECK_ONLY 分支訊息寫死 "Azure Batch／azure-launch"（作法 7）；`cli.py` 的 `_queue_first_preflight`、`ce update` 後預檢用 `CHECKABLE`，`cmd_ce_preflight` 的補齊檢查用 `PLATFORM_HOST_TYPES + CHECK_ONLY_TYPES`，所以 K8s 自動涵蓋。
- `abf_station/azure_preflight.py` 是直接範本：`credentials_path`、`clean_environment`（內部呼叫 `compute_envs._check_azure`）、`_az_env`、`run_preflight`；`handlers.py` 的 preflight 分支一類型一段。
- 平台本身不啟動任何程式（`test_scope.py` TC-071）；啟動 `kubectl` 只在 `abf_station/`，經 `site.run_fixed`。
- 憑證防線：`common.is_secret_name` ＋ `compute_envs._VALUE_PATTERNS`；`tests/credentials_stay_in_settings_test.sh` 掃全 repo，測試金鑰用字串拼接。

**Nextflow k8s 執行器（2026-10-29 讀官方頁，VERIFIED）**
- `https://docs.seqera.io/nextflow/kubernetes`：啟用 `process.executor = 'k8s'`；`k8s.storageClaimName` ＝ PVC 名；`k8s.storageMountPath` 預設 `/workspace`；`workDir` 要設在掛載磁碟內，例 `/workspace/work`；每個 process 必須有 `container`；`k8s.storageSubPath` 預設 `/`；work 目錄「必須在共用的 persistent volume（或用 Fusion 時在物件儲存）」；PV 要 `ReadWriteMany`；`kuberun` 指令「obsolete and no longer maintained」。該頁**沒有**寫 RBAC 角色需求。
- `https://docs.seqera.io/nextflow/reference/config/k8s`：`k8s.namespace`（預設 `default`）、`k8s.context`（要用的 Kubernetes 設定 context，無預設）、`k8s.serviceAccount`（無預設）、`k8s.storageClaimName`、`k8s.storageMountPath`（預設 `/workspace`）。該頁沒有權限／RBAC 說明。
- 鍵名對應：`context`→`k8s.context`、`namespace`→`k8s.namespace`、`storageClaimName`→`k8s.storageClaimName`、`storageMountPath`→`k8s.storageMountPath`、`serviceAccount`→`k8s.serviceAccount`、`workDir`→`workDir`。**這只是命名表；本片不產生任何 Nextflow 設定，`k8s-launch` 必須重新讀上列頁面。**

**kubectl（VERIFIED，kubernetes.io 的 kubectl 參考頁）**
- `kubectl auth can-i`：只是查詢「某動作是否被允許」，有 `--list`、`-q`；頁面沒寫結束碼。本片**不使用**（待裁決 4）。
- `kubectl config get-contexts [-o name]`：顯示 kubeconfig 檔內的 context，有 `--kubeconfig`。
- `kubectl get`：支援 `-o jsonpath`；全域旗標 `--kubeconfig`、`--context`、`-n/--namespace`、`--request-timeout`（預設 0＝不逾時，值要帶單位）。

**UNVERIFIED（沒讀到官方明文，計畫只能當保守規則或待驗證項）**
- context 名稱的格式規則、namespace／PVC／service account 的命名規則（計畫用 DNS-1123 的保守版本，沒有重讀官方頁）。
- `config get-contexts` 是否完全不連叢集（頁面只說顯示 kubeconfig 檔內的 context，「不連線」是推論）。
- `-o jsonpath={.spec.accessModes[*]}` 的實際輸出形狀（空白分隔？）、`{.status.phase}` 的值集合（`Bound`／`Pending`／`Lost` 取自一般知識，本次未查頁面）。
- 環境變數 `KUBECACHEDIR` 是否被 kubectl 採用；唯讀指令是否仍會在 `~/.kube/cache` 寫快取。
- `get pvc`／`get serviceaccount` 所需最小 RBAC；Nextflow k8s 執行器自己執行時需要的 RBAC（官方頁沒寫）。
- kubeconfig 的 exec 型登入外掛會在代理主機執行外部程式；代理不解析 YAML，因此無法事先擋或偵測（待裁決 5）。
- 叢集費用（節點、儲存）本片不涉及；唯讀指令不建立資源，靠測試掃描禁用字保證，沒有讀任何價格頁。

## 不做
- **不送出、取消、續跑任何東西**（`k8s-launch`：K8s 版 bundle、`k8s.*` 設定落地、`-with-tower`、本機 Nextflow 主控程序全屬它）。
- 不做費用、上傳、清理、不建命名空間／PVC／service account／RBAC（營運者手動做）。
- 不支援 Fusion／Wave 免 PVC 模式、`storageSubPath`、自訂 pod 規格、多叢集、雲端商 IAM 登入的整合（只收營運者放好的 kubeconfig）。
- 不用 `kubernetes` Python 套件；不用 `nextflow kuberun`（官方已標 obsolete）。
- 不新增 MCP 工具、網頁路由或畫面；不改 `hello` 回傳；不改 `abf_launch/`。
- 不碰 `eks-platform`、`gke-platform`、`awscloud-platform`、`azcloud-platform`、`googlecloud-platform` 與其他類型，它們維持 `unsupported`（EKS／GKE 與 K8s 的差別在驗證外掛，另案）。
- 不動 `gcb_preflight.py`、`aws_preflight.py`、`azure_preflight.py`、`launch.py`、`cloud_store.py`、`clean.py`。

## 待裁決（每點附我的建議預設）
1. **範圍是否包含 `eks-platform`／`gke-platform`**：它們也是 K8s，但 kubeconfig 需靠 `aws eks get-token`／`gke-gcloud-auth-plugin` 這類外掛。**預設：不含**；本片只做通用 `k8s-platform`，營運者自備可用的 kubeconfig；EKS／GKE 另案。
2. **`namespace` 要不要必填**（Nextflow 預設 `default`）：**預設：必填**，避免悄悄用 `default` 命名空間。
3. **PVC 不是 `ReadWriteMany` 時：fail 還是放行**：官方頁寫要 `ReadWriteMany`，但單節點叢集用 RWO 實際可能可跑（未驗證）。**預設：fail（`pvc_access` 獨立一項），訊息引官方說法；若維護者的叢集是 RWO，再開放寬的旗標，不在本片**。
4. **要不要加 `kubectl auth can-i --list` 檢查 RBAC**：能提早發現「不能建 pod」，但輸出格式與所需最小權限我都沒查到（UNVERIFIED），解析容易脆。**預設：不加**；留給 `k8s-launch` 在真的要建 pod 前再檢查。
5. **kubeconfig 的 exec 外掛風險**：代理不解析 YAML，無法擋；**預設：不擋，只在文件與 `chmod 600` 檢查寫明「kubeconfig 是營運者放的信任檔」**（與 AWS 憑證檔同信任等級）。若要擋，需引進 YAML 解析（違反「代理只用標準函式庫」），另案。
6. **平台端要不要新增 kubeconfig 專用的 `_VALUE_PATTERNS`**（例如抓 `client-certificate-data:`、`client-key-data:`）：現有規則可能擋不住 `client-key-data`（base64，無前綴）。**預設：本片不加**，K8S-11 若發現漏洞就記進 ledger 回報，再由 developer-agent 決定。
7. **`context` 旗標名**：`--context` 簡短，但可能與日後別的「context」概念混淆；替代 `--kube-context`。**預設：`--context`**（與 Nextflow `k8s.context` 同名）。
8. **車道排序**：若 L2 上仍有未合的 `aws-*`／`azure-*` upload／clean 任務，它們也動 `compute_envs.py`／`jobs.py` 與同批測試；**預設：等它們合完再開工**，開工第一步用 `git grep -n 'CHECK_ONLY_TYPES\|k8s-platform\|the other ten' origin/v3 -- platform/tests docs` 重列本表。
9. **憑證建立時是否允許為空**（K8S-09）：沿 azure 裁決 12 的先例。**預設：允許**，第一次預檢的 `credential_name` 報 fail。

## 裁決（10-29 01:4x，developer-agent）
1–9 全照「待裁決」的建議預設：不含 eks／gke；namespace 必填；非 ReadWriteMany 的 PVC 判失敗（獨立一項檢查）；不加 `auth can-i`；不擋 exec-plugin，文件寫明 kubeconfig 是受信任的操作者檔；平台端不加 kubeconfig 專屬密鑰樣式（缺口記帳本）；旗標叫 `--context`；排在 azure-upload、azure-clean 之後，開工第一步重 grep「必須更新的既有斷言」清單、以實際為準；允許空憑證建立，第一次預檢在 credential_name 失敗。
10. 站台端新檔任何地方（含註解）不准出現小寫 `kubernetes`（test_station_static 禁字）；用 `K8s` 或 `Kubernetes`。
11. （10-29 04:3x）azure-upload（#261）與 azure-clean（#262）都已合併。v3 上 SEQERA_PARITY 的 Azure 列現為 `Have (create + check + launch + cancel + upload + clean)`，PLATFORM.md 的 Azure 段也改過；本計畫引用的行號與既有斷言一律以 origin/v3 重新 grep 為準，找不到的記帳本並回報，不猜。
12. （10-29 08:4x，合約退回第 1 點）`platform/tests/test_azure_upload.py:855` 逐字比對舊句「…the other ten types can be modelled only」→ **納入 C 表與「範圍：檔案」**，只改期望字串成新句，不刪斷言。開工第一步全面 `git grep -n -e 'the other ten' -e 'CHECK_ONLY_TYPES == ()' -e 'len(UNSUPPORTED)' origin/v3`，所有命中的既有測試檔視同 C 表成員（只改期望值、帳本逐條記檔:行、改前、改後）；命中非測試檔且不在範圍內 → BLOCKED 回報。
13. base 改以 origin/v3@e79a555（#262 合併後）為準；上方標頭的 e8619e2 作廢。
14. context 存在檢查＝**整行相等**（去掉前後空白後比較），不是子字串：清單只有 `lab-context-2` 時，`lab-context` 判為不存在 → fail。verifier 為此補一條 TC。

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
