# 測試案例：在 Kubernetes 上送出與取消分析（k8s-launch，C-5 的 K8s 半邊）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
來源：本任務沒有 spec.md，以 `specs/k8s-launch/plan.md` 為規格：含逐字引文的「維護者原話」、作法 1–11、失敗先行測試、「必須更新的既有斷言」、「完成標準」、「不做」、「裁決」與 developer-agent 的三段裁決（2026-10-29 21:0x 的 1–10、22:3x 的 11-1…11-7、22:5x 的 12-1…12-10）。與上文衝突時，以文末較晚的裁決為準（作法 7 的 `--from-file` 以 12-4 為準；作法 7 的訊息以 11-7 為準；`_snapshot_ce` 要加 K8s 分支以 12-3「不改」為準）。
IDs: TC-001..TC-191。每條只測一件事；驗證方式「自動」＝ `platform/tests/` 下的測試，並在測試內以註解 `# TC-nnn` 標明。計畫列出的測試名稱（`K8L-…`）寫在驗證方式欄，沒有列名的由 executor 命名並以註解標明。
編號對齊：計畫裁決文字引用的 TC-002、TC-026、TC-031、TC-060、TC-063、TC-077、TC-102～104、TC-128，已對到本檔同編號、同意思的案例。計畫裁決 12-1 所說「比照 azure-launch TC-136」是 azure-launch 合約自己的編號；計畫作法 11 說的「TC-070」（`# Nothing existing` 檔頭）與裁決 12-1 的 `docs/TESTING.md` TC-156 是專案既有測試的編號，不是本檔的 TC-070、TC-156。
所有測試輸入都用假值：環境名 `k8s1`、context `lab-ctx`、命名空間 `nf-ns`、PVC `nf-pvc`、掛載路徑 `/workspace`、`workDir=/workspace/work`、run 名稱 `r1`（Pod 名 `nf-r1`、Secret 名 `nf-r1-bundle`）、映像 `example/head:test`、公開網址 `https://platform.example.test`、假 token `TOKEN-FAKE-123`。全部用假的 `runner`／`run_fixed` 或 PATH 上記錄參數的假 `kubectl`（裁決 9）；不碰真叢集、不花錢、不啟動真程式。
-->

**規格**：`specs/k8s-launch/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「尚未支援」而不是悄悄亂做。

名詞：**主控 Pod**＝在叢集裡跑 Nextflow 的那一個 Pod（K8s 的主控程序不在平台主機上，而在叢集裡）；**task pod**＝Nextflow 為每個計算步驟另外開的 Pod；**PVC**＝叢集上事先建好的共用儲存空間；**Secret**＝叢集裡存放敏感內容的物件，這次用來裝 bundle 檔案與 run token；**站台代理**＝裝在平台主機上、本人答 y 之後才動手的程式；**內容包**＝平台與代理各自用同一個函式建一次、必須完全相等的那組要送出的檔案；**放行**＝平台願意為某種環境排入某種工作；**manifest**＝描述要建什麼 Pod／Secret 的文字，由 stdin（標準輸入）餵給 `kubectl`，不寫成檔案、不放在參數列；**預檢**＝送出前唯讀檢查環境的那組檢查；**run token**＝讓主控 Pod 回報進度的一次性憑證；**寫入類呼叫**＝會改變叢集的 `kubectl create`／`delete`，**讀取類呼叫**＝`get`／`logs`。

## User Story 1 — 本人答 y 之後，才在 Kubernetes 上送出一次分析（優先度 P1）

計畫目標：「沒有本人答 y 就不啟動自動成立」；k8s-ce 交辦原話：「create + free read-only preflight only … NO launching」，本任務才是開 launch 的那一步，「每條會寫入叢集的 `kubectl` 動詞都要有測試證明它只在確認之後才發生」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 7；11-7；K8L-RUN-01 | 功能 | 可用的 K8s 環境 `k8s1`、代理在線、有效確認憑證；站台設定 `k8s_head_image=example/head:test`；憑證檔 600、假 `kubectl` 在 PATH、預檢全 pass、`get pod`／`get secret` 回 NotFound、取 phase 回 `Running` | 代理收到 `launch_nextflow` 工作 | 結果 `ok` 為真；訊息含「已啟動：Pod nf-r1（命名空間 nf-ns）；叢集的運算費用從現在開始計」 | 自動：`K8L-RUN-01` |
| TC-002 | 作法 7；12-4；12-6；K8L-RUN-01 | 功能 | 同 TC-001，假 `runner` 記下每次呼叫 | 送出成功後看呼叫記錄 | **寫入類呼叫恰兩次**，依序：`create`（Secret manifest，由 stdin）→ `create`（Pod manifest，由 stdin）；讀取類呼叫（`get pod`、`get secret`、取 phase）次數不限 | 自動：`K8L-RUN-01` |
| TC-003 | 作法 7；K8L-RUN-01 | 功能 | 同 TC-001 | 看呼叫順序 | 順序為：預檢 → `get pod nf-r1` → `get secret nf-r1-bundle` → create Secret → create Pod → 取 phase；預檢先於任何寫入類呼叫 | 自動：`K8L-RUN-01` |
| TC-004 | 作法 3；12-4 | 功能 | 同 TC-001 | 看兩次 `create` 的 argv 與 stdin | argv 含 `create`、`-f`、`-`，且含 `--context lab-ctx`；兩份 manifest 全文只在 stdin，不在 argv；本機沒有被寫出的 manifest 暫存檔 | 自動：`test_k8s_launch.py`（註解標 TC-004） |
| TC-005 | 作法 7；裁決 4 | 功能 | 同 TC-001 | 送出成功後看結果與內容包紀錄 | 結果裡 `slurm_job_id` 是一個不是 0 的固定占位值（兩次送出相同）；內容包紀錄另存 `pod_name=nf-r1`；沒有新增欄位 | 自動：`test_k8s_launch.py`（註解標 TC-005） |
| TC-006 | 作法 7；裁決 4、作法 10 | 功能 | 平台端走完 `take_result` | 代理回報成功結果 | `launches.slurm_job_id` 等於該占位值；平台資料表欄位沒有新增 | 自動：`test_k8s_launch.py`（註解標 TC-006） |
| TC-007 | 目標第 1 點；K8L-CONF-01 | 功能 | K8s 環境可用，使用者明講環境名字 | 從 `prepare_launch` 開始送出 | 依序經過 `prepare_launch` → 確認頁 → 排入 `launch_nextflow` → 代理領取後 `verify_confirmation`；沒有另一條送出路徑 | 自動：`test_k8s_launch.py`（註解標 TC-007） |
| TC-008 | 作法 3；維護者原話（第 52 行） | 功能 | 同 TC-001，假 `start_detached` 記下呼叫 | 送出成功 | 代理沒有在本機啟動任何行程（`start_detached` 0 次）；平台主機上沒有建立 `head.pid`、`head.out` 或本機專屬資料夾；主控程序只存在於叢集的 Pod | 自動：`test_k8s_launch.py`（註解標 TC-008） |
| TC-009 | 作法 7 | 功能 | 同 TC-001，取 phase 分別回 `Pending`、`Running`、`Succeeded` | 各送出一次 | 三種都視為已啟動（`ok` 為真）；只有 `Failed` 才算起不來 | 自動：`test_k8s_launch.py`（註解標 TC-009） |
| TC-010 | 目標第 1 點；K8L-CONF-01 | 例外 | 代理收到 K8s 的 `launch_nextflow` 工作，但**沒有**確認憑證 | 代理處理 | 結果 `refused`；`runner` 呼叫 0 次；`tmp_path` 下沒有新檔 | 自動：`K8L-CONF-01` |
| TC-011 | K8L-CONF-01 | 例外 | 有確認憑證但雜湊與內容包不符 | 代理處理 | `refused`；`runner` 0 次；沒有新檔 | 自動：`K8L-CONF-01` |
| TC-012 | K8L-CONF-01 | 例外 | 確認憑證已用過一次 | 再送同一個工作 | `refused`；`runner` 0 次；沒有新檔 | 自動：`K8L-CONF-01` |
| TC-013 | K8L-CONF-01 | 例外 | 憑證的種類是 `cancel`（不是 `launch`） | 拿它去送出 | `refused`；`runner` 0 次；沒有新檔 | 自動：`K8L-CONF-01` |
| TC-014 | 目標；K8L-CONF-02 | 例外 | 對 K8s 環境發出送出要求 | 在人答 y 之前查 jobs 表 | 還沒有任何 `launch_nextflow` 工作被建立（不會自動排進佇列） | 自動：`K8L-CONF-02` |
| TC-015 | 目標；K8L-CONF-02 | 例外 | 同 TC-014 | 人答 n、或逾時、或取消 | jobs 表列數與送出前相同 | 自動：`K8L-CONF-02` |
| TC-016 | 作法 7（用自己的設定重建內容包並比對） | 例外 | 有效確認，但內容包的 `k8s.config` 被改了一個字元 | 代理處理 | 代理重建後發現不相等，拒絕；`kubectl` 呼叫 0 次；沒有新檔 | 自動：`test_k8s_launch.py`（註解標 TC-016） |
| TC-017 | 作法 7 | 例外 | 有效確認，但內容包是給另一個代理的 | 代理處理 | 白話拒絕；`kubectl` 呼叫 0 次 | 自動：`test_k8s_launch.py`（註解標 TC-017） |
| TC-018 | 作法 7（run token） | 例外 | 工作裡沒有 run token（或是空的） | 代理處理 | 白話拒絕；`kubectl` 呼叫 0 次 | 自動：`test_k8s_launch.py`（註解標 TC-018） |
| TC-019 | 作法 7（deadline） | 例外 | 工作期限剩餘低於門檻（與其他雲端同一個門檻） | 代理處理 | 拒絕；`kubectl` 呼叫 0 次 | 自動：`test_k8s_launch.py`（註解標 TC-019） |
| TC-020 | 作法 7；K8L-CRED-03 | 例外 | 憑證檔（kubeconfig）不存在 | 送出 | 白話拒絕並說明怎麼放；`runner` 一次都不呼叫；沒有建立任何東西 | 自動：`K8L-CRED-03` |
| TC-021 | 作法 7；K8L-CRED-03 | 例外 | 憑證檔權限不是 600 | 送出 | 白話拒絕；`runner` 0 次 | 自動：`K8L-CRED-03` |
| TC-022 | 作法 7；K8L-CRED-03 | 例外 | PATH 上找不到 `kubectl` | 送出 | 白話拒絕，說明缺 `kubectl` 與怎麼處理；`runner` 0 次 | 自動：`K8L-CRED-03` |
| TC-023 | 作法 7；K8L-RUN-02 | 例外 | 假 `runner` 讓預檢任一項不是 pass（逐項各試一次） | 送出 | 拒絕並顯示預檢的白話訊息；沒有任何寫入類呼叫（不 create Secret、不 create Pod） | 自動：`K8L-RUN-02` |
| TC-024 | 作法 7；K8L-BUNDLE-05 | 例外 | `get pod nf-r1` 回「存在」 | 送出 | 拒絕、不覆蓋；沒有寫入類呼叫；訊息點名該 Pod | 自動：`K8L-BUNDLE-05` |
| TC-025 | 11-4；12-6 | 例外 | `get pod` 回 NotFound，但 `get secret nf-r1-bundle` 回「存在」 | 送出 | 拒絕：不 create Secret、不 create Pod、不刪任何東西；訊息點名 `nf-r1-bundle`，並說明可用 `k8s-clean` 或手動刪除 | 自動：`test_k8s_launch.py`（註解標 TC-025） |
| TC-026 | 11-4；12-10 | 例外 | Secret 建成功、建 Pod 失敗（假 `kubectl` 回非零） | 送出 | 之後恰一次 `delete secret nf-r1-bundle`（名稱與本次剛建的完全相同、帶 `--namespace nf-ns --context lab-ctx`）；沒有刪其他東西；結果為錯誤並說出建 Pod 失敗的原因 | 自動：`test_k8s_launch.py`（註解標 TC-026） |
| TC-027 | 11-4 | 例外 | 同 TC-026，且 `delete secret` 也失敗 | 送出 | 結果為錯誤；訊息附上 Secret 名 `nf-r1-bundle`，請人手動清；不重試 | 自動：`test_k8s_launch.py`（註解標 TC-027） |
| TC-028 | 11-4 | 例外 | create Secret 失敗 | 送出 | 不 create Pod；不送任何 `delete`（Secret 沒建成）；結果為白話錯誤 | 自動：`test_k8s_launch.py`（註解標 TC-028） |
| TC-029 | 作法 7；K8L-RUN-03 | 例外 | Pod 建成功，取 phase 回 `Failed` | 送出 | 結果為錯誤，白話說明 Pod 起不來，附 log 尾端；不重試 | 自動：`K8L-RUN-03` |
| TC-030 | 11-6；K8L-RUN-01 | 例外 | 同 TC-029 | 看讀取類呼叫 | 恰一次 `kubectl logs nf-r1 --tail=50`（唯讀）；成功啟動的路徑沒有 `logs` 呼叫 | 自動：`K8L-RUN-01` |
| TC-031 | 12-10 | 例外 | 同 TC-029 | 看寫入類呼叫 | Pod 變 Failed 之後**不刪任何東西**（不 delete Pod、不 delete Secret）；留著供檢查 | 自動：`test_k8s_launch.py`（註解標 TC-031） |
| TC-032 | 12-8③ | 例外 | 檢查同名 Pod 時，`get pod` 非零且 stderr 不含 `NotFound`（例如連不上） | 送出 | 白話錯誤「連不上叢集」；沒有寫入類呼叫 | 自動：`test_k8s_launch.py`（註解標 TC-032） |
| TC-033 | 12-8④ | 例外 | Pod 建成功，之後取 phase 的呼叫失敗 | 送出 | 訊息含「無法取得 Pod 狀態」；不重試、不刪任何東西；run 的紀錄狀態不被改寫（維持上次值） | 自動：`test_k8s_launch.py`（註解標 TC-033） |
| TC-034 | 裁決 2；11-1 | 例外 | 站台設定沒有 `k8s_head_image` | 送出 | 白話拒絕並說明怎麼設（由管理者釘一個版本）；沒有寫入類呼叫；原始碼裡沒有預設映像標籤 | 自動：`test_k8s_launch.py`（註解標 TC-034） |

## User Story 2 — 共用閘門：K8s 只放行四種工作，其餘明白說「尚未支援」（優先度 P1）

計畫作法 1、2 與 12-7：`launch_nextflow`、`cancel_run`、`preflight`、`pipeline_files` 開；`clean_work`、`put_upload`、`list_site_files`、`fetch_run_records`、`read_task_log` 關，訊息是「Kubernetes 尚未支援<動作中文名>」，不得含 `AWS`／`Google Batch`／`Azure`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-035 | 作法 1；K8L-GATE-01 | 功能 | 可用的 K8s 環境 `k8s1` | 對它排入 `launch_nextflow` | 通過放行檢查，工作被建立 | 自動：`K8L-GATE-01` |
| TC-036 | 作法 1；K8L-GATE-01 | 功能 | 同上 | 排入 `cancel_run` | 通過 | 自動：`K8L-GATE-01` |
| TC-037 | 作法 1；K8L-GATE-01 | 功能 | 同上 | 排入 `preflight` | 通過（`handlers.py` 的 K8s 分支不動） | 自動：`K8L-GATE-01` |
| TC-038 | 作法 1；K8L-GATE-01 | 功能 | 同上 | 排入 `pipeline_files` | 通過 | 自動：`K8L-GATE-01` |
| TC-039 | 作法 1；12-7；K8L-GATE-01 | 不在範圍 | 同上 | 排入 `clean_work` | `JobRefused`；訊息含「Kubernetes」與「尚未支援清理」 | 自動：`K8L-GATE-01` |
| TC-040 | 作法 1；K8L-GATE-01 | 不在範圍 | 同上 | 排入 `put_upload` | `JobRefused`；訊息含「Kubernetes」與「尚未支援」 | 自動：`K8L-GATE-01` |
| TC-041 | 作法 1；K8L-GATE-01 | 不在範圍 | 同上 | 排入 `list_site_files` | `JobRefused`；訊息含「Kubernetes」與「尚未支援」 | 自動：`K8L-GATE-01` |
| TC-042 | 作法 1；K8L-GATE-01 | 不在範圍 | 同上 | 排入 `fetch_run_records` | `JobRefused`；訊息含「Kubernetes」與「尚未支援」 | 自動：`K8L-GATE-01` |
| TC-043 | 作法 1；K8L-GATE-01 | 不在範圍 | 同上 | 排入 `read_task_log` | `JobRefused`；訊息含「Kubernetes」與「尚未支援」 | 自動：`K8L-GATE-01` |
| TC-044 | 作法 1；K8L-GATE-01 | 例外 | 同上 | 看 TC-039～TC-043 五條拒絕訊息 | 都不含 `AWS`、`Google Batch`、`Azure`（K8s 不會落到別的雲端的句子） | 自動：`K8L-GATE-01` |
| TC-045 | 12-7 | 例外 | 同上 | 看 TC-039～TC-043 五條拒絕訊息 | 不再出現「尚未支援送出」與 `k8s-launch` 字樣 | 自動：`test_k8s_launch.py`（註解標 TC-045） |
| TC-046 | K8L-GATE-02 | 功能 | AWS 環境 | 逐種工作排入／被拒 | 放行與拒絕訊息與搬動前位元級相同 | 自動：`K8L-GATE-02` |
| TC-047 | K8L-GATE-02 | 功能 | Azure 環境 | 同上 | 與搬動前位元級相同 | 自動：`K8L-GATE-02` |
| TC-048 | K8L-GATE-02 | 功能 | Google Batch 環境 | 同上 | 與搬動前位元級相同（訊息仍寫 Google Batch） | 自動：`K8L-GATE-02` |
| TC-049 | 作法 2；K8L-GATE-03 | 功能 | 載入 `compute_envs` | 讀常數 | `PLATFORM_HOST_TYPES == (GOOGLE_BATCH, AWS, AZURE, K8S)`（順序相同） | 自動：`K8L-GATE-03` |
| TC-050 | 作法 2；12-2；K8L-GATE-03 | 功能 | 同上 | 讀 `CHECK_ONLY_TYPES` | 是空 tuple，行尾註解「新雲端類型先放這裡，只開預檢」保留；若實作改成移除該常數（12-2 允許二擇一），則 `cli.py:488` 的條件仍涵蓋 K8s、`ce preflight` 仍能排出；兩種做法都要有斷言 | 自動：`K8L-GATE-03` |
| TC-051 | 作法 2；K8L-GATE-03 | 功能 | 同上 | 讀 `CLOUD_JOB_KINDS[K8S]` | 恰四種：`preflight`、`launch_nextflow`、`cancel_run`、`pipeline_files` | 自動：`K8L-GATE-03` |
| TC-052 | 作法 2；K8L-GATE-03 | 功能 | 搜尋 `platform/` 原始碼 | 找 `PLATFORM_HOST_TYPES[` | 一處都沒有（沒有位置取用） | 自動：`K8L-GATE-03` |
| TC-053 | 作法 2 | 功能 | 載入 `compute_envs` | 讀 `CHECKABLE` | 組法不變：K8S 恰出現一次、沒有重複；其餘成員與搬動前相同 | 自動：`test_k8s_launch.py`（註解標 TC-053） |
| TC-054 | K8L-GATE-04 | 例外 | K8s 環境 | 用 `cloud_store` 解析任何雲端路徑 | 一律 `CloudPathError`（行為不改） | 自動：`K8L-GATE-04` |
| TC-055 | K8L-GATE-04 | 例外 | 資料集 `--destination` 填 K8s 環境名 | 執行 | 白話拒絕 | 自動：`K8L-GATE-04` |
| TC-056 | K8L-GATE-05 | 例外 | 直接對 K8s 排 `put_upload`、`clean_work` | 排入 | 被拒；jobs 表列數不變 | 自動：`K8L-GATE-05` |
| TC-057 | K8L-GATE-06 | 功能 | K8s 環境 | 執行 `ce preflight` | 仍排出預檢並走 `k8s_preflight` | 自動：`K8L-GATE-06` |
| TC-058 | K8L-GATE-06 | 例外 | 使用者有一個可用的 K8s 環境，沒明講環境名 | 呼叫 `primary_environment` | 不會自動挑到 K8s | 自動：`K8L-GATE-06` |
| TC-059 | 環境事實（`jobs.py` 既有規則：可用的環境才能送出） | 例外 | K8s 環境狀態不是 `available`（例如 `creating`） | 對它排 `launch_nextflow` | 被拒，白話說明只有可用的環境才能送出；jobs 表列數不變 | 自動：`test_k8s_launch.py`（註解標 TC-059） |

## User Story 3 — 憑證與祕密：kubeconfig 與 run token 不外洩（優先度 P1）

計畫作法 5 與裁決 3(b)、11-1、11-3、12-4：kubeconfig 只在代理這一側；資料庫只存憑證名字；token 與 bundle 內容只進 Secret（由 stdin 餵），不進 argv、manifest 文字、環境變數、日誌、回應。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | 11-6；12-8；專長守則（日誌不含密鑰） | 例外 | 假 `logs` 輸出含 `TOKEN-FAKE-123` 與一段假 kubeconfig 內容；Pod 變 Failed | 送出 | 結果訊息裡的 log 尾端已去掉這兩者；結果與日誌都搜不到 | 自動：`test_k8s_launch.py`（註解標 TC-060） |
| TC-061 | 11-6（log 尾端受 TC-128 限制） | 例外 | 假 `logs` 輸出很長（超過 200 字） | 送出，Pod 變 Failed | 訊息裡顯示的 log 尾端不超過 200 字 | 自動：`test_k8s_launch.py`（註解標 TC-061） |
| TC-062 | K8L-CRED-01 | 例外 | 呼叫端環境有 `ABF_FOO`、`KUBE_BAR`、`KUBECONFIG=/other` | 每次假 `runner` 收到的 env | 沒有任何 `ABF_*`；呼叫端原有的 `KUBE*` 都已刪掉 | 自動：`K8L-CRED-01` |
| TC-063 | 11-3；12-4；專長守則 | 例外 | 假 run token `TOKEN-FAKE-123` | 送出成功，搜尋所有 argv、Pod manifest 全文、每次 `runner` 的 env、日誌、回傳結果 | 一處都搜不到 token（只出現在 Secret manifest 的 base64 資料裡） | 自動：`test_k8s_launch.py`（註解標 TC-063） |
| TC-064 | K8L-CRED-01；作法 5 | 功能 | 假憑證檔在唯一路徑 | 看每次呼叫 | `KUBECONFIG` 與 `KUBECACHEDIR` 只在 env 裡；argv 裡沒有 kubeconfig 路徑或內容 | 自動：`K8L-CRED-01` |
| TC-065 | K8L-CRED-02 | 例外 | 憑證檔放假內容（以字串拼接組出）與唯一路徑 | 送出成功與各失敗路徑後，搜尋 argv、manifest（stdin）、日誌 | 搜不到假憑證內容與憑證檔路徑 | 自動：`K8L-CRED-02` |
| TC-066 | K8L-CRED-02 | 例外 | 同上 | 搜尋 `specs/k8s-launch/ledger.md` | 搜不到假憑證內容與憑證檔路徑 | 自動：`K8L-CRED-02` |
| TC-067 | K8L-CRED-04；作法 5 | 例外 | 送出成功、各失敗路徑、取消，全程記錄 argv | 逐個 argv 元素檢查（整個元素比對） | 沒有 `use-context`、沒有以 `set-` 開頭的子命令、沒有 `--all`、沒有 `-l`、沒有 `--selector`、沒有 `delete pvc` | 自動：`K8L-CRED-04` |
| TC-068 | 作法 5 | 功能 | 同上 | 看每次 `kubectl` 呼叫 | 每次都帶 `--context lab-ctx`（一律用 `--context`，從不切換目前 context） | 自動：`test_k8s_launch.py`（註解標 TC-068） |
| TC-069 | 12-4 | 例外 | 送出前後比對本機檔案系統（`tmp_path` 與暫存目錄） | 送出成功 | 本機沒有新增任何含 token 或 bundle 內容的檔案；參數列不含 token | 自動：`test_k8s_launch.py`（註解標 TC-069） |
| TC-070 | 12-4 | 例外 | 同 TC-001 | 看 create Secret 的呼叫 | 不用 `--from-file`、不用 `--from-literal`；是 `create -f -`，Secret manifest 由 stdin 餵入 | 自動：`test_k8s_launch.py`（註解標 TC-070） |
| TC-071 | K8L-BUNDLE-02 | 例外 | 憑證檔放假內容與唯一路徑 | 搜尋內容包、manifest、`head.sh`、`snapshot_ce` 結果、資料庫位元組、`ce show` 輸出 | 搜不到假憑證內容與憑證檔路徑 | 自動：`K8L-BUNDLE-02` |
| TC-072 | 裁決 3(b)；11-3；12-4 | 功能 | 同 TC-001 | 解開 Secret manifest | 種類是 Secret，名稱 `nf-r1-bundle`、命名空間 `nf-ns`；資料欄為 base64；解開後是 bundle 的檔案加 `tower.token` | 自動：`test_k8s_launch.py`（註解標 TC-072） |
| TC-073 | 裁決 3(b) | 例外 | `params.yaml` 內含一個獨一無二的字串 `ZZ-UNIQUE-PARAM-VALUE` | 送出成功，搜尋 Pod manifest 文字、argv、日誌 | 搜不到這個字串（只出現在 Secret manifest 的 base64 資料裡） | 自動：`test_k8s_launch.py`（註解標 TC-073） |
| TC-074 | 11-3 | 功能 | 同 TC-001 | 看 Pod manifest | Secret 以唯讀 volume 掛載；啟動命令先把檔案複製到 `/workspace/_k8s_runs/r1/`，並對 `tower.token` 做 `chmod 600`，之後才 `nextflow run`；Pod manifest 與 env 裡沒有 token | 自動：`test_k8s_launch.py`（註解標 TC-074） |
| TC-075 | 11-1 | 例外 | 站台設定有 `k8s_head_image=example/head:test` | 搜尋內容包、送出畫面、`hello` 事實；分別在設與不設映像的設定下，讓平台與代理各建一次內容包並比對雜湊 | 都搜不到映像字串；兩邊內容包與雜湊在兩種設定下都相等 | 自動：`test_k8s_launch.py`（註解標 TC-075） |
| TC-076 | 11-1；裁決 2 | 功能 | 同 TC-001 | 看 Pod manifest | 容器映像等於站台設定值 `example/head:test`（代理建 Pod 時才讀） | 自動：`test_k8s_launch.py`（註解標 TC-076） |
| TC-077 | 12-3 | 功能 | K8s 環境 | 呼叫 `snapshot_ce`（及平台端 `snapshot`） | 輸出與 base 完全相同：沿用原有的 K8s 分支、`maxMemoryGB` 條件不含 K8s | 自動：`test_k8s_launch.py`（註解標 TC-077） |
| TC-078 | 專長守則（錯誤訊息）；作法 7、8 | 例外 | 送出與取消路徑上每一種拒絕與錯誤（TC-010～TC-034、TC-119～TC-131） | 看每則訊息 | 都說明發生了什麼事、使用者該怎麼處理；不含 `Traceback`、不含程式碼目錄的絕對路徑、不含憑證檔路徑 | 自動：`test_k8s_launch.py`（註解標 TC-078） |
| TC-079 | 目標第 3 點；維護者原話（第 52 行） | 功能 | 建立 K8s 環境，憑證只填名字 | 看資料庫與 `ce show` | 只存憑證名字；沒有憑證路徑或內容 | 自動：`test_k8s_launch.py`（註解標 TC-079） |

## User Story 4 — 內容包、設定檔、Pod 與名稱（優先度 P1）

計畫作法 3、4 與裁決 6、11-5、12-5：`k8s.config` 只含指定的鍵；Pod 的形狀；Pod 名由 run 名轉換。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | 作法 4；K8L-BUNDLE-01 | 功能 | 合法環境（namespace `nf-ns`、PVC `nf-pvc`、掛載 `/workspace`、`workDir=/workspace/work`、未設 serviceAccount）；run `r1` | 建內容包，看 `k8s.config` 的鍵 | 鍵恰為：`process.executor = 'k8s'`、`k8s.namespace`、`k8s.storageClaimName`、`k8s.storageMountPath`、`workDir`，沒有別的設定鍵 | 自動：`K8L-BUNDLE-01` |
| TC-081 | 作法 4 | 功能 | 同上 | 看 `workDir` | 為 `/workspace/work/runs/r1/work`（在掛載路徑底下）；兩個不同 run 名稱的 `workDir` 互不相同 | 自動：`K8L-BUNDLE-01` |
| TC-082 | 作法 3、4 | 功能 | 環境設了 `serviceAccount`／沒設 | 各建一次 | 有設：`k8s.config` 有 `k8s.serviceAccount`、Pod 有 `serviceAccountName`；沒設：兩處都沒有 | 自動：`K8L-BUNDLE-01` |
| TC-083 | 作法 4；裁決 5 | 功能 | 環境有 `context=lab-ctx` | 看 `k8s.config` | 不含 `k8s.context`；`lab-ctx` 只用在代理的 `kubectl --context` | 自動：`K8L-BUNDLE-01` |
| TC-084 | 作法 4（`maxvCpus`、`spot` K8s 不收） | 功能 | 兩個環境只差 `spot=true`／`false`，另有 `maxvCpus` 的情形 | 各建一份 `k8s.config` | 不出現 `maxvCpus`、`spot` 相關的設定鍵；兩份的設定鍵完全相同 | 自動：`K8L-BUNDLE-01` |
| TC-085 | 作法 4；K8L-BUNDLE-01 | 例外 | 憑證檔放假內容 | 搜尋 `k8s.config` | 沒有任何憑證或 kubeconfig 內容 | 自動：`K8L-BUNDLE-01` |
| TC-086 | 作法 3；K8L-BUNDLE-03 | 功能 | 合法內容包 | 看 Pod manifest | 只有一個 Pod（種類 Pod，沒有第二個 Pod） | 自動：`K8L-BUNDLE-03` |
| TC-087 | 作法 3；K8L-BUNDLE-03 | 功能 | 同上 | 看欄位 | `claimName=nf-pvc`、`mountPath=/workspace`、`namespace=nf-ns`、（有設時）`serviceAccountName` 都與環境一致；Pod 名 `nf-r1` | 自動：`K8L-BUNDLE-03` |
| TC-088 | 作法 3；K8L-BUNDLE-03 | 功能 | 同上 | 看 `restartPolicy` | 為 `Never` | 自動：`K8L-BUNDLE-03` |
| TC-089 | 11-3；裁決 3(b) | 功能 | 同上 | 看 Pod 的 volume | bundle Secret 以**唯讀**方式掛載；PVC 以 `claimName` 掛在 `mountPath` | 自動：`K8L-BUNDLE-03` |
| TC-090 | 作法 3；K8L-BUNDLE-03 | 功能 | 同上 | 看啟動命令 | 恰一個 `nextflow run <pipeline> -r <rev> -name r1 -params-file params.yaml -c nextflow.config -c k8s.config -with-tower <endpoint>`，且是命令的最後一個動作（`k8s.config` 在 `nextflow.config` 之後） | 自動：`K8L-BUNDLE-03` |
| TC-091 | K8L-BUNDLE-03；憲法 I.2 | 功能 | 搜尋 `platform/` 原始碼 | 找 `nextflow run` | 只有 `launch.py` 有（`k8s_launch.py` 沒有） | 自動：`K8L-BUNDLE-03` |
| TC-092 | 作法 3；12-5 | 功能 | 同 TC-080 | 看執行檔案的位置 | 在 `/workspace/_k8s_runs/r1/`（基準是 `storageMountPath`），不落在該 run 的 `workDir`（`/workspace/work/runs/r1/work`）之內；啟動命令把檔案複製到這裡並在這裡執行 | 自動：`test_k8s_launch.py`（註解標 TC-092） |
| TC-093 | 作法 3；11-3 | 功能 | 同上 | 看 Secret 的鍵 | 恰為 `samplesheet.csv`、`params.yaml`、`nextflow.config`、`k8s.config`、`head.sh`、`tower.token` | 自動：`test_k8s_launch.py`（註解標 TC-093） |
| TC-094 | 作法 3；K8L-BUNDLE-05 | 功能 | run 名稱 `r1`、`my_run` | 算 Pod 名 | 分別為 `nf-r1`、`nf-my-run`（`_` 換成 `-`）；名字只含小寫英數與 `-`；內容包裡記下 Pod 名供取消用 | 自動：`K8L-BUNDLE-05` |
| TC-095 | 作法 3、11-5；K8L-BUNDLE-05 | 例外 | 一個很長的 run 名稱（轉換後超過 63 字） | 算 Pod 名 | 長度不超過 63 | 自動：`K8L-BUNDLE-05` |
| TC-096 | 11-5 | 例外 | 一個 run 名稱，使截斷到 63 字時剛好落在 `-` 上 | 算 Pod 名 | 截斷後去掉結尾的 `-`，結果不以 `-` 結尾 | 自動：`K8L-BUNDLE-05` |
| TC-097 | 作法 3；K8L-BUNDLE-05 | 例外 | run `a_b` 已有 Pod `nf-a-b`；再送 run `a-b`（轉換後同名） | 送出 | 被「同名 Pod 已存在」拒絕，不覆蓋、沒有寫入類呼叫 | 自動：`K8L-BUNDLE-05` |
| TC-098 | 作法 7；11-4 | 功能 | Pod 名 `nf-r1` | 算 Secret 名 | 為 `nf-r1-bundle`（Pod 名加 `-bundle`） | 自動：`test_k8s_launch.py`（註解標 TC-098） |
| TC-099 | 作法 3、4；K8L-BUNDLE-04 | 功能 | samplesheet 路徑欄都在 `/workspace` 底下 | 建內容包 | 通過 | 自動：`K8L-BUNDLE-04` |
| TC-100 | K8L-BUNDLE-04 | 例外 | samplesheet 路徑欄是本機其他路徑（如 `/home/x/a.fastq.gz`） | 建內容包 | 拒絕；訊息說明檔案要先放進 PVC（掛載路徑底下） | 自動：`K8L-BUNDLE-04` |
| TC-101 | K8L-BUNDLE-04 | 例外 | samplesheet 路徑欄是 `s3://`、`gs://`、`az://` 開頭 | 建內容包 | 各自拒絕；訊息說明檔案要先放進 PVC | 自動：`K8L-BUNDLE-04` |

## User Story 5 — 送出畫面與指令列（優先度 P1）

計畫作法 9、12-9、11-7 與維護者原話（第 46 行：費用顯示雲端自己的幣別、不換算 → 送出畫面不寫金額）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-102 | 12-9 | 功能 | 一次 K8s 送出的 `prepare_launch` | 看送出畫面 | 顯示 `params.yaml`、`nextflow.config`、`k8s.config` 的內容與啟動命令（含 `-with-tower` 位址） | 自動：`test_k8s_launch.py`（註解標 TC-102） |
| TC-103 | 12-9；TC-063 | 例外 | 同上，已有 run token `TOKEN-FAKE-123` | 看送出畫面全文 | 沒有 token | 自動：`test_k8s_launch.py`（註解標 TC-103） |
| TC-104 | 12-9；11-1 | 例外 | 同上，站台設定有映像 `example/head:test` | 看送出畫面全文 | 沒有映像字串 | 自動：`test_k8s_launch.py`（註解標 TC-104） |
| TC-105 | 作法 9；K8L-SCREEN-01 | 功能 | 同 TC-102 | 看第一段 | 第一段就是 `K8S_COST`：「由你的 Kubernetes 叢集所屬的雲端或機房計費；本系統目前沒有費用預估與上限」 | 自動：`K8L-SCREEN-01` |
| TC-106 | 作法 9；維護者原話（第 46 行）；K8L-SCREEN-01 | 例外 | 同上 | 看畫面全文 | 沒有任何金額、`NT$`、`USD`、換算 | 自動：`K8L-SCREEN-01` |
| TC-107 | 作法 9 | 功能 | 同上 | 看畫面 | 列出叢集 context `lab-ctx`、命名空間 `nf-ns`、PVC `nf-pvc`、將建立的 Pod 名 `nf-r1`、將寫入 PVC 的檔案與位置 `/workspace/_k8s_runs/r1/` | 自動：`test_k8s_launch.py`（註解標 TC-107） |
| TC-108 | K8L-SCREEN-02 | 功能 | Slurm 的送出要求 | 看送出畫面 | 與 base 位元級相同 | 自動：`K8L-SCREEN-02` |
| TC-109 | K8L-SCREEN-02 | 功能 | Google Batch 的送出要求 | 同上 | 與 base 位元級相同 | 自動：`K8L-SCREEN-02` |
| TC-110 | K8L-SCREEN-02 | 功能 | AWS 的送出要求 | 同上 | 與 base 位元級相同 | 自動：`K8L-SCREEN-02` |
| TC-111 | K8L-SCREEN-02 | 功能 | Azure 的送出要求 | 同上 | 與 base 位元級相同 | 自動：`K8L-SCREEN-02` |
| TC-112 | 11-7；K8L-SCREEN-03 | 功能 | K8s 型別的送出、取消在指令列 | 看 `abf_launch/cli.py` 的輸出 | 原本寫「Slurm 工作編號」之處（三處）改為「Pod 名稱」，K8s 輸出裡沒有「Slurm 工作編號」 | 自動：`K8L-SCREEN-03` |
| TC-113 | 11-7；K8L-SCREEN-03 | 功能 | K8s 送出成功 | 看「已啟動」那一行 | 整行為「已啟動：Pod nf-r1（命名空間 nf-ns）；叢集的運算費用從現在開始計」 | 自動：`K8L-SCREEN-03` |
| TC-114 | K8L-SCREEN-03 | 功能 | Slurm、gcb、aws、azure 的指令列輸出 | 與 base 比對 | 一字不變（用詞只對 K8s 改變） | 自動：`K8L-SCREEN-03` |
| TC-115 | 作法 6；裁決 3(a) | 功能 | 代理事實：`way_back=direct`、`platform_public_url=https://platform.example.test` | 建內容包 | 啟動命令的 `-with-tower` 位址就是這個 https 網址，不是 loopback | 自動：`test_k8s_launch.py`（註解標 TC-115） |
| TC-116 | 作法 6；裁決 3(a) | 例外 | `way_back` 不是 `direct`（如 `forward` 或未設） | 建內容包 | 白話拒絕，說明要怎麼設；不是悄悄省略 `-with-tower`；`kubectl` 0 次 | 自動：`test_k8s_launch.py`（註解標 TC-116） |
| TC-117 | 作法 6；裁決 3(a) | 例外 | `platform_public_url` 缺、是 http、或是 loopback | 建內容包 | 白話拒絕，說明要 https 公開網址；`kubectl` 0 次 | 自動：`test_k8s_launch.py`（註解標 TC-117） |

## User Story 6 — 本人確認後取消（刪掉那一個主控 Pod）（優先度 P1）

計畫作法 8、9 與 12-8：取消 ＝ 一次 `kubectl delete pod <名> --namespace <ns> --context <ctx> --wait=false`；不刪 PVC、不刪別的 Pod、不用 label selector、不用 `--all`；訊息提醒檢查 task pod。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-118 | 作法 9 | 功能 | K8s 環境上有一個已啟動的 run（內容包紀錄有 `pod_name=nf-r1`） | `prepare_cancel` | 出現確認畫面（`cancel_screen`），列出 Pod 名 `nf-r1`、命名空間、context，並白話說明將刪除這一個 Pod | 自動：`test_k8s_launch.py`（註解標 TC-118） |
| TC-119 | 目標；K8L-CONF-02 | 例外 | 同上 | 在人答 y 之前查 jobs 表；人答 n／逾時 | 沒有 `cancel_run` 工作被建立；jobs 列數不變 | 自動：`test_k8s_launch.py`（註解標 TC-119） |
| TC-120 | 作法 9；K8L-CANCEL-02 | 例外 | K8s run 的紀錄沒有 Pod 名 | `prepare_cancel` | 白話拒絕，照舊不排工作 | 自動：`K8L-CANCEL-02` |
| TC-121 | K8L-CANCEL-02 | 例外 | 同 TC-120 | 看拒絕訊息 | 提醒到叢集檢查 task pod | 自動：`K8L-CANCEL-02` |
| TC-122 | 作法 8；K8L-CANCEL-01 | 功能 | 有效取消確認、Pod 名 `nf-r1`、命名空間與環境一致；假 `kubectl` | 代理執行取消 | 寫入類呼叫恰一次：`delete pod nf-r1 --namespace nf-ns --context lab-ctx --wait=false`（之前可有唯讀 `get pod`）；結果 `ok` 為真 | 自動：`K8L-CANCEL-01` |
| TC-123 | 作法 8 | 例外 | 同上 | 看整個取消過程的寫入類呼叫 | 只有那一次 `delete`；沒有第二次、沒有重試、沒有迴圈 | 自動：`test_k8s_launch.py`（註解標 TC-123） |
| TC-124 | 作法 8 | 例外 | 取消確認裡的內容包是給另一個代理的 | 代理執行 | 白話拒絕；`kubectl` 0 次 | 自動：`test_k8s_launch.py`（註解標 TC-124） |
| TC-125 | 作法 8；K8L-CANCEL-01 | 例外 | 內容包裡的 Pod 名不是這個平台會為該 run 產生的名字（如 `other-pod`） | 代理執行 | 不送 `delete`；白話拒絕 | 自動：`K8L-CANCEL-01` |
| TC-126 | 作法 8；K8L-CANCEL-01 | 例外 | 內容包裡的命名空間與環境的命名空間不一致 | 代理執行 | 不送 `delete`；白話拒絕 | 自動：`K8L-CANCEL-01` |
| TC-127 | 作法 8；K8L-CONF-01 | 例外 | 取消沒有確認憑證／雜湊不符／已用過／種類是 `launch` | 代理執行 | `refused`；`kubectl` 0 次 | 自動：`test_k8s_launch.py`（註解標 TC-127） |
| TC-128 | 12-8② | 例外 | `kubectl delete` 回非零，stderr 很長且含 `TOKEN-FAKE-123` | 代理執行取消 | 結果為錯誤，訊息含 stderr 的前 200 字、已去掉 token；run 的狀態不變；不重試 | 自動：`test_k8s_launch.py`（註解標 TC-128） |
| TC-129 | 12-8① | 例外 | 取消時 `get pod` 的 stderr 含 `NotFound`（Pod 已不存在） | 代理執行取消 | 視為已停止：結果 `ok` 為真、run 標為已取消（cancelled），訊息為「Pod 已不存在，視為已停止」；不送會失敗的第二次寫入 | 自動：`test_k8s_launch.py`（註解標 TC-129） |
| TC-130 | 12-8③ | 例外 | 取消時 `get pod` 非零且 stderr 不含 `NotFound` | 代理執行取消 | 白話錯誤「連不上叢集」；run 的狀態不變；不送 `delete` | 自動：`test_k8s_launch.py`（註解標 TC-130） |
| TC-131 | 作法 8；「不做」 | 例外 | 取消成功的全部呼叫記錄 | 逐個 argv 元素檢查 | 沒有刪 PVC、刪別的 Pod、刪 Secret；沒有 `-l`、`--selector`、`--all` | 自動：`K8L-CRED-04` |
| TC-132 | 作法 8；裁決 9 | 功能 | 取消成功 | 看結果訊息 | 白話提醒：到叢集確認 task pod 是否已清掉、沒清乾淨要自己處理、費用從啟動到停掉都算；不宣稱 task pod 已一併刪除或已停止計費 | 自動：`test_k8s_launch.py`（註解標 TC-132） |
| TC-133 | 專長守則（跨使用者，讀） | 例外 | 使用者甲有一個 K8s 環境與一個 run；使用者乙持自己的 token | 乙查看甲的 K8s 環境與 run | 被拒絕，說法與「找不到」相同，不透露存在 | 自動：`test_k8s_launch.py`（註解標 TC-133） |
| TC-134 | 專長守則（跨使用者，寫） | 例外 | 同上 | 乙對甲的 K8s run 要求取消 | 被拒絕；沒有確認畫面、沒有 `cancel_run` 工作、jobs 列數不變 | 自動：`test_k8s_launch.py`（註解標 TC-134） |
| TC-135 | 專長守則（跨使用者，寫） | 例外 | 同上 | 乙對甲的 K8s 環境要求送出 | 被拒絕；沒有 `launch_nextflow` 工作 | 自動：`test_k8s_launch.py`（註解標 TC-135） |

## User Story 7 — 不在範圍與不退步（優先度 P1）

計畫「不做」：RBAC／PVC／命名空間／serviceAccount、Fusion、上傳、清理、續跑、費用預估與上限、`fetch_run_records`／`read_task_log`／`list_site_files`、自訂組合、第二條刪除路徑、網頁、資料表、新環境設定鍵；以及其他四種型別位元級不變、既有斷言只換值。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-136 | 作法 1；K8L-BUNDLE-06 | 不在範圍 | K8s run | 平台端 `prepare_resume` | 拒絕；訊息含 Kubernetes、不含 AWS | 自動：`K8L-BUNDLE-06` |
| TC-137 | K8L-BUNDLE-06 | 不在範圍 | K8s run | 平台端 `prepare_relaunch`（原樣重跑） | 拒絕；訊息含 Kubernetes、不含 AWS | 自動：`K8L-BUNDLE-06` |
| TC-138 | 範圍（`run_resume`、`K8S_NO_RESUME`） | 不在範圍 | 代理收到 K8s 的續跑工作 | 代理處理 | 拒絕；`kubectl` 0 次 | 自動：`K8L-BUNDLE-06` |
| TC-139 | K8L-BUNDLE-07；「不做」 | 不在範圍 | 自訂組合（composed）要送 K8s | 準備送出 | 拒絕（同其他雲端） | 自動：`K8L-BUNDLE-07` |
| TC-140 | 作法 1；「不做」 | 不在範圍 | K8s 送出 | 看送出畫面與流程 | 沒有費用預估與上限的計算或欄位；畫面明寫沒有預估與上限（同 TC-105） | 自動：`test_k8s_launch.py`（註解標 TC-140） |
| TC-141 | 裁決 3(b)；「不做」（上傳） | 不在範圍 | K8s 送出成功與各失敗路徑 | 逐個 argv 元素檢查 | 沒有 `kubectl cp`；除 bundle 外沒有任何資料被搬進 PVC | 自動：`test_k8s_launch.py`（註解標 TC-141） |
| TC-142 | 裁決 3(b)、7；「不做」（清理） | 不在範圍 | 送出成功 | 看呼叫記錄 | 成功路徑上沒有 `delete`；Secret 留著（清理留給 `k8s-clean`） | 自動：`test_k8s_launch.py`（註解標 TC-142） |
| TC-143 | 裁決 7 | 不在範圍 | 送出成功 | 看 Pod 與呼叫記錄 | 主控 Pod 不被自動刪（`restartPolicy: Never`，沒有任何自動刪除的呼叫） | 自動：`test_k8s_launch.py`（註解標 TC-143） |
| TC-144 | 「不做」（RBAC、PVC、命名空間、serviceAccount） | 不在範圍 | 送出與取消全程 | 檢查所有 manifest 的種類與 argv | 只建過 Secret 與 Pod 兩種；沒有 Role、RoleBinding、PVC、Namespace、ServiceAccount | 自動：`test_k8s_launch.py`（註解標 TC-144） |
| TC-145 | 「不做」（Fusion） | 不在範圍 | 內容包 | 看 `k8s.config` 與命令 | 沒有 Fusion 相關設定 | 自動：`test_k8s_launch.py`（註解標 TC-145） |
| TC-146 | 作法 11；K8L-CONF-04 | 不在範圍 | 看 `pyproject.toml` 與 `abf_station/*.py` | 找 `kubernetes` 套件與 import | `pyproject.toml` 沒有 `kubernetes` 套件；沒有 `import kubernetes` | 自動：`K8L-CONF-04` |
| TC-147 | 作法 11 | 功能 | 搜尋 `abf_station/*.py` 每一行（含註解、字串） | 找小寫 `kubernetes` | 一處都沒有（`test_station_static.py::test_agent_stricter_scan_no_other_network_or_cloud_library` 綠） | 自動：`test_station_static.py`（既有）＋ `test_k8s_launch.py`（註解標 TC-147） |
| TC-148 | 範圍（`fetch.py:18`） | 功能 | 看 `fetch.py` 的 `_NOT_RECORDS` | 與 `K8S_FILE_NAMES` 比對 | K8s 的每個檔名都在 `_NOT_RECORDS` 裡（不被當成 run 紀錄） | 自動：`test_k8s_launch.py`（註解標 TC-148） |
| TC-149 | 完成標準；範圍 | 功能 | 對 base 做 `git diff --name-only` | 看變更檔名 | 不含 `.github/`、憲法、版本號檔、`web.py`、`web_board.py`、`web_settings.py`、`static/*`、網頁模板、已安裝 plugin 副本；沒有 `spec.md`、`test-case*.md`、`docs/ROADMAP.md`、`.claude-plugin/plugin.json` 的變更 | 手動：`docs/TESTING.md`「k8s-launch」小節（閱卷時 verifier 對 diff 檢查） |
| TC-150 | 作法 10；專長守則（migration） | 不在範圍 | 比對 base 的資料表結構與環境設定鍵 | 看變更 | 沒有改資料表、沒有 migration 檔、沒有新增環境設定鍵；`ledger.md` 或 PR 寫明「不需要 migration」的理由 | 自動：`test_k8s_launch.py`（註解標 TC-150） |
| TC-151 | 範圍（不改的檔） | 不在範圍 | 看 diff | 檢查 `handlers.py`、`clean.py`、`put_upload.py`、`k8s_preflight.py`、`cloud_cost.py`、`actions/*`、`cli.py`（platform） | 都沒有變更；`cloud_store.py` 的行為不變 | 手動：`docs/TESTING.md`「k8s-launch」小節（閱卷時對 diff 檢查） |
| TC-152 | 作法 11；憲法 I.1 | 功能 | 看 `k8s_launch.py` 與 `test_k8s_launch.py` 前 40 行 | 找檔頭 | 有 `# Nothing existing: …`，理由寫明搜過 Nextflow 官方 Kubernetes 頁（kuberun 已過時）、Seqera `tw launch`、nf-core `tower launch` | 自動：既有檔頭檢查（`tests/scripts_name_their_alternative.sh` 或專案對 platform 檔頭的測試）＋ `test_k8s_launch.py`（註解標 TC-152） |
| TC-153 | 完成標準 | 功能 | Slurm 的內容包、`head.sh` | 與 base 比對 | 位元級不變 | 自動：既有 Slurm 測試不改且綠 |
| TC-154 | 完成標準 | 功能 | Google Batch 的內容包、`head.sh` | 同上 | 位元級不變 | 自動：既有 `test_gcb_launch.py` 不改（除 TC-159 列的句子）且綠 |
| TC-155 | 完成標準 | 功能 | AWS 的內容包、`head.sh` | 同上 | 位元級不變 | 自動：既有 `test_aws_launch.py` 不改（除 TC-158 列的行）且綠 |
| TC-156 | 完成標準 | 功能 | Azure 的內容包、`head.sh` | 同上 | 位元級不變 | 自動：既有 `test_azure_launch.py` 不改（除 TC-158、TC-159 列的行）且綠 |
| TC-157 | 完成標準 | 功能 | Slurm、gcb、aws、azure 的取消訊息 | 與 base 比對 | 一字不變 | 自動：各型別既有取消測試不改且綠 |
| TC-158 | 「必須更新的既有斷言」；12-2 | 功能 | 對 base 比對 `test_k8s_ce.py:732-734,758,968`、`test_aws_ce.py:907`、`test_gcb_ce.py:853`、`test_azure_ce.py:721`、`test_aws_launch.py:1011` 附近、`test_azure_launch.py:983` 附近 | 逐行看變更 | 只是把期望值換成新值（`CHECK_ONLY_TYPES == ()`、`PLATFORM_HOST_TYPES` 加 K8S、`CHECKABLE` 照新組合、K8s 拒絕訊息改成只對未開的種類斷言並讓 `launch_nextflow` 放行）；沒有刪斷言、沒有跳過、沒有放寬成模糊比對 | 手動：閱卷時 verifier 對這些測試檔 diff 逐行核對 |
| TC-159 | 12-1 | 功能 | 對 base 比對七個逐字釘句的測試（`test_aws_ce.py:924`、`test_azure_ce.py:863`、`test_azure_launch.py:1213`、`test_azure_upload.py:855`、`test_gcb_ce.py:867`、`test_gcb_launch.py:1151`、`test_k8s_ce.py:843` `NEW_SENTENCE`） | 逐行看變更 | 只把舊句換成新句；沒有刪斷言、沒有改成模糊比對 | 手動：閱卷時 verifier 對這些測試檔 diff 逐行核對 |
| TC-160 | 12-2 | 功能 | `specs/k8s-launch/ledger.md` | 對照 TC-158、TC-159 實際變更的每一行 | ledger 逐行列出「舊斷言→新斷言」，且與實際 diff 一一對得上；兩分支輸出比對（其他四型別）貼在 ledger | 手動：閱卷時 verifier 讀 ledger 與 diff |
| TC-161 | 「必須更新的既有斷言」最後一條 | 功能 | 對 base 看所有其他既有測試檔 | 看變更 | 沒有任何其他既有斷言被改動（Slurm、gcb、aws、azure 的內容包、畫面、`head.sh`、取消訊息斷言都沒動） | 手動：閱卷時 verifier 對 diff 檢查 |
| TC-162 | 完成標準 | 功能 | 完成標記 `GREEN <HEAD sha>` | 全套（含 `tests/platform_test.sh`、`no_second_run_state_test.sh`、`credentials_stay_in_settings_test.sh`）綠 | 全綠；`no_second_run_state_test.sh` 的 LAUNCH 允許清單沒有新增 K8s 條目；已知環境紅依 dev-plans README 通例 | 自動：`tests/run_all.sh`（完成標記） |

## User Story 8 — 文件（優先度 P2）

計畫「範圍」與 12-1：`docs/PLATFORM.md`、`docs/SEQERA_PARITY.md`、`docs/TESTING.md`、`docs/OPERATIONS.md`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-163 | 12-1；K8L-DOC-01 | 功能 | `docs/PLATFORM.md` | 找可跑清單那句（兩處：粗體句與 In full 句） | 兩處都是「Slurm, Google Cloud Batch, AWS Batch, Azure Batch and Kubernetes can run; the other nine types can be modelled only」，逐字 | 自動：`K8L-DOC-01` |
| TC-164 | 12-1；K8L-DOC-01 | 功能 | 同上 | 看型別表 K8s 列 | 為「checked and launched on the platform host (upload, clean, resume: not yet)」 | 自動：`K8L-DOC-01` |
| TC-165 | 12-1；K8L-DOC-01 | 功能 | 同上 | 看 `:513` 起的 Kubernetes 小節 | 不再寫「launching on it is not built yet」；改寫成可送出，拒絕清單只剩 upload／clean／resume | 自動：`K8L-DOC-01` |
| TC-166 | 作法 5；完成標準 2；K8L-DOC-01 | 功能 | 同上 | 看新增的「Launching on Kubernetes」小節 | 寫出：主控 Pod 在叢集裡跑並掛同一個 PVC、PVC 需 `ReadWriteMany`、serviceAccount 需要的 Role 權限（本任務不建立）、站台設定 `k8s_head_image` 怎麼設、`platform_public_url` 要 https | 自動：`K8L-DOC-01` |
| TC-167 | K8L-DOC-02 | 功能 | `docs/SEQERA_PARITY.md` | 看 K8s 列 | 反映「可送出、可取消；上傳、清理、續跑、費用預估尚未支援」，不再寫 launch 未開 | 自動：`K8L-DOC-02` |
| TC-168 | 完成標準「文件」；K8L-DOC-03 | 功能 | `docs/TESTING.md` | 看「k8s-launch」小節 | 有該小節，寫明手動驗收 1–6，列在「Needs human」之下 | 自動：`K8L-DOC-03` |
| TC-169 | 12-1；範圍（TESTING.md:835-837） | 功能 | `docs/TESTING.md` 的 k8s-ce 段落 | 看是否仍釘住「launch 未開」 | 依實況只做最小改動；`test_k8s_ce.py` 的 TC-156 敘述斷言仍綠 | 自動：`test_k8s_ce.py`（既有，值已更新）＋ `test_k8s_launch.py`（註解標 TC-169） |
| TC-170 | 範圍（OPERATIONS.md 雲端小節） | 功能 | `docs/OPERATIONS.md` | 看雲端小節 | 有一段說明 K8s 送出需要的設定（站台設定 `k8s_head_image`、kubeconfig 放在 `ABF_STATION_KUBECONFIG`、`kubectl` 在平台主機） | 自動：`test_k8s_launch.py`（註解標 TC-170） |

## User Story 9 — 維護者實跑一次（手動；需要真的 K8s 叢集，會花錢，屬 C 級）（優先度 P3）

計畫完成標準「手動 1–6」。依計畫與裁決 9：這些**不屬 executor／verifier 的完成標準**，要等維護者同意；閱卷只確認 `docs/TESTING.md` 有寫、夠具體可照做。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-171 | 手動 1 | 功能 | 平台主機有 `kubectl`、kubeconfig 在 `ABF_STATION_KUBECONFIG`（600） | 跑 k8s-ce 預檢 | 預檢 `available` | 手動：`docs/TESTING.md`「k8s-launch」小節 |
| TC-172 | 手動 2 | 功能 | 叢集已備好 | 逐項確認 | PVC 為 `ReadWriteMany`；serviceAccount 有權建立／刪除 Pod（RBAC 見文件）；主控 Pod 映像拉得到 | 手動：同上 |
| TC-173 | 手動 3 | 功能 | 最小 samplesheet，檔案已放進 PVC | 送出，看畫面 | 第一段是帳單句（K8S_COST） | 手動：同上 |
| TC-174 | 手動 3；憲法 I.2 | 功能 | 同上 | 答 n，再答 y | 答 y 之前叢集裡沒有 Pod；答 y 之後才建立 | 手動：同上 |
| TC-175 | 手動 4 | 功能 | 已送出 | 觀察叢集 | 主控 Pod 變 `Running`，task pods 出現 | 手動：同上 |
| TC-176 | 手動 4 | 功能 | 同上 | 觀察平台與 PVC | 平台 run 頁有進度（`-with-tower` 通）；結果在 PVC | 手動：同上 |
| TC-177 | 手動 5 | 功能 | 中途取消並答 y | 觀察叢集 | 主控 Pod 被刪 | 手動：同上 |
| TC-178 | 手動 5；裁決 9 | 功能 | 同上 | 判決 task pods 是否一併消失 | 結論記進 ledger；沒清乾淨就回報，不自行加刪除路徑 | 手動：同上 |
| TC-179 | 手動 6 | 功能 | 實跑結束 | 搜尋資料庫、`ce show`、畫面、日誌、manifest | 搜不到憑證片段 | 手動：同上 |
| TC-180 | 完成標準；裁決 9 | 功能 | `docs/TESTING.md` | 看該小節的說明 | 寫明這些步驟需要真的叢集、會花錢、屬 C 級須維護者同意，且不在完成標準內 | 手動：同上 |

## 憲法與安全網

本任務開了 Kubernetes 的送出路徑，碰到憲法 I.2（唯一一條送出路徑、人答 y 才啟動、不留第二份 run 狀態）與專長守則（backend）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-181 | I.2；k8s-ce 交辦原話；K8L-CONF-02 | 例外 | 假 `runner` 記錄所有 `kubectl` 呼叫 | 走遍所有「尚未答 y」的路徑：`prepare_launch`、畫面、未確認的工作、被拒的工作、`prepare_cancel` | 這些路徑上 `create`、`delete` 都是 0 次；寫入類呼叫只出現在答 y 之後的 `run_launch`／`run_cancel` | 自動：`K8L-CONF-02` |
| TC-182 | I.2；K8L-CONF-03 | 例外 | 搜尋 `platform/abf_platform/` 與 `k8s_launch.py` | 找啟動程式的程式碼 | 平台套件不啟動任何程式；`k8s_launch.py` 不含 `nextflow run`、`sbatch`、`subprocess`；`kubectl` 只經 `site.run_fixed` | 自動：`K8L-CONF-03` |
| TC-183 | I.2 | 功能 | `tests/no_second_run_state_test.sh` | 執行 | 通過；送出路徑仍只有 `launch.py` 一個 LAUNCH 允許條目，`k8s_launch.py` 沒有新增條目 | 自動：`tests/no_second_run_state_test.sh` |
| TC-184 | 專長守則（對等性）；K8L-CONF-04 | 功能 | 列舉使用者可見的動作清單（MCP 工具、網頁路由、CLI 指令）與動作層函式清單 | 與 base 比對 | MCP 工具仍 12 個；沒有新增網頁路由或動作；兩邊清單一一對應（缺一邊就失敗） | 自動：`K8L-CONF-04` |
| TC-185 | I.2（不留第二份 run 狀態） | 功能 | 送出成功 | 看新增的儲存 | 只多了占位值與 `pod_name`（既有內容包紀錄）；沒有新表、新檔或快取去保存 Pod 狀態；phase 只在送出當下讀一次 | 自動：`test_k8s_launch.py`（註解標 TC-185） |

## User Story 10 — 維護者原話對照（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-186 | 「4. 四種計算環境都建：nano4 → Google Batch → AWS Batch → Azure／K8s。架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）」（第 40 行） | 功能 | K8s 環境 | 走憑證 → 環境 → pipeline → run | K8s 環境可被選去送出，順序與其他雲端相同（同 TC-001、TC-007、TC-035） | 自動：同 TC-001、TC-007 |
| TC-187 | 「**C-5** Azure Batch／K8s：同模式」（第 169 行） | 功能 | K8s 與 Azure 各一個環境 | 比對確認流程與放行方式 | 同樣經 `prepare_launch` → 確認 → `launch_nextflow` → `verify_confirmation`；放行表的形式相同（同 TC-007、TC-049、TC-051） | 自動：同 TC-007、TC-049 |
| TC-188 | 「雲端用戶不裝代理——平台主機自己跑 Nextflow、雲端憑證放平台主機檔案（不進資料庫）」（第 52 行） | 功能 | 一次送出 | 看 `kubectl` 的執行位置與憑證存放 | `kubectl` 只在平台主機經 `site.run_fixed` 呼叫；kubeconfig 只是平台主機上的檔案；資料庫只存名字（同 TC-079、TC-064、TC-182）；叢集端不需要裝任何代理（主控程序放在叢集 Pod 內是裁決 1 的有意例外，見總覽） | 自動：同 TC-079、TC-182 |
| TC-189 | 「B 級部分自合：網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併」（第 54 行） | 功能 | 本任務的 diff | 看是否動到網頁畫面 | 不動 `web*.py`、模板、`static/*`（同 TC-149） | 手動：同 TC-149 |
| TC-190 | 「雲端費用照 10-18 裁示：顯示雲端自己的幣別（美元）、不換算」（第 46 行） | 例外 | K8s 送出畫面 | 看全文 | 不寫金額、不換算（同 TC-105、TC-106） | 自動：同 TC-106 |
| TC-191 | k8s-ce 交辦原話：「create + free read-only preflight only … NO launching」 | 例外 | 各路徑 | 看寫入類呼叫發生的位置 | 每個會寫入叢集的 `kubectl` 動詞只在答 y 之後才發生（同 TC-181） | 自動：同 TC-181 |

<!--
Rules for the writer:
- Every acceptance scenario and every FR in spec.md maps to at least one TC. Every
  "out of scope" item in spec.md maps to at least one 不在範圍 TC.
- A TC tests one thing. Two expectations = two rows.
- 驗證方式 is 自動 (a test file under tests/, named once it exists, "自動" until then)
  or 手動 (a step in docs/TESTING.md's manual half). Nothing else.
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
