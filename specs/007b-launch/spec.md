# Feature Specification: 站台代理第二片：送出分析、即時進度、取消（007b）

**Feature Branch**: `007b-launch`

**Created**: 2026-10-11

**Status**: Draft

**Input**: 維護者 2026-10-11 的回答：
- 驗收分析：「ampliseq＋microbiome_test」。
- 確認方式：「終端機問是／否」。
- 進度：「看看 Seqera 都怎麼做，上面應該能即時知道不同 task 的完成度」。
- 分析設定：「跟 9/20 那次一樣」。
- 取消：「這片就要能取消」。

憲法 4.0.0 原則 2 允許至多一條自己的送出路徑。研究見 `research.md`。

> 名詞見 `CONTEXT.md`。

## 這一片做什麼

使用者在平台的命令列說要跑哪條 nf-core 管線、用哪些資料與參數。之後的流程：
1. 平台把**完整的送出內容**列出來，在終端機問「是／否」。
2. 使用者答「是」，平台才把工作交給站台代理。
3. 代理在國網上做兩件事：
   - 為這次分析建一個專屬資料夾，寫入 samplesheet、參數檔、設定檔與主控工作腳本；
   - 用 `sbatch` 把 Nextflow 主控工作送進排程（照 Seqera 的做法）。
4. 主控工作執行時，Nextflow 把每個 task 的進度即時送回平台（同 Seqera）。送回的路線是：國網運算節點 → 登入節點上既有的 relay → 使用者共用連線上的反向通道 → 筆電上的平台。
5. 使用者可以從平台取消一個自己送出的分析，同樣要先在終端機確認。

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 送出前一定看到完整內容並確認（Priority: P1）

1. **Given** 一個可用的 Slurm 環境，**When** 使用者執行 `abf-platform launch`（管線、版本、輸入、參數），**Then** 終端機逐項列出以下內容，並問「確定送出？(y/N)」：
   - 管線與版本；
   - 環境；
   - 這次的專屬資料夾；
   - samplesheet 的每一列；
   - 參數；
   - 主控佇列與送出選項；
   - 計費帳號；
   - 設定檔的全文；
   - 主控工作腳本的全文。

   控制字元一律以看得見的方式顯示。只有輸入 `y` 或 `Y` 才送出。（正常）
2. **Given** 同上，**When** 使用者輸入 `y`／`Y` 以外的任何東西、直接 Enter、或輸入被關閉（非互動），**Then** 不送出，平台與國網都沒有任何改變。（例外）
3. **Given** 任何呼叫者（MCP、另一支程式、假平台）直接把「送出」工作塞給代理，但沒有這次確認產生的憑證，**When** 代理收到，**Then** 拒絕，國網上的 `sbatch` 一次都沒被呼叫。（例外）
4. **Given** 已確認的送出，**When** 確認之後內容被改動（參數、資料夾、腳本任何一字），**Then** 代理拒絕。代理執行的必須是使用者看到的那一份。（例外）

### User Story 2 — 在國網上送出，照 Seqera 的方式（Priority: P1）

1. **Given** 確認過的送出，**When** 代理執行，**Then** 它依序完成：
   - 在環境的工作區下建立這次的專屬資料夾（資料夾已存在就拒絕，不覆蓋）；
   - 寫入 samplesheet、參數檔、設定檔與主控工作腳本，全部只有使用者本人可讀；
   - 呼叫 `sbatch` 恰好一次，帶 `-D <專屬資料夾>`、`--no-requeue`、環境的主控佇列與送出選項，以及部署設定的計費帳號；
   - 回報 Slurm 工作編號與 Nextflow run 名稱。（正常）
2. **Given** 送出時國網連線斷了、`sbatch` 失敗、或帳號沒設，**When** 執行，**Then** 回報原因、不重試，並說清楚國網上留下了什麼（例如只建了資料夾）。（例外）
3. **Given** 任何檔案，**When** 檢查，**Then** 沒有任何 token 以明文或 base64 寫進其他人讀得到的檔案。（例外）

### User Story 3 — 即時看到每個 task 的進度（Priority: P1）

1. **Given** 分析在跑，**When** 使用者或 AI 用 `get_run`（008 已有）查詢，**Then** 看得到這些資訊，而且與 Nextflow 送出的事件一致：
   - 整體狀態；
   - 每個 process 的完成、執行中、失敗數；
   - 失敗 task 的名稱與原因。（正常）
2. **Given** 反向通道或 relay 中途斷了，**When** 分析繼續跑，**Then** 有三個結果：
   - 分析不受影響；
   - 平台在 3 分鐘無消息後顯示「失聯」（008 規則）；
   - 使用者可要求代理讀國網上該資料夾裡 Nextflow 自己的紀錄，平台以紀錄為準補齊（008 的 rebuild 規則）。（例外）
3. **Given** 已經送出，但 Nextflow 還沒開始（Slurm 排隊中），**When** 使用者查 `abf-platform launches`，**Then** 看到「已送出，尚未收到 Nextflow 事件」與 Slurm 工作編號。這是事實紀錄，不是平台推斷的狀態。（正常）
4. **Given** 送出前反向通道或 relay 不通，**When** 送出，**Then** 不送出，並說明哪一段不通、怎麼接上。原因是 Nextflow 在開頭連不到平台時會整個中止。（例外）

### User Story 4 — 取消（Priority: P1）

1. **Given** 一個由平台送出、還在跑的分析，**When** 使用者執行 `abf-platform cancel <run>`，**Then** 終端機列出 run 名稱、Slurm 工作編號與專屬資料夾，問「確定取消？(y/N)」。答 `y`，代理只對那一個主控工作送出取消，Nextflow 會收掉它底下的 task。（正常）
2. **Given** 要取消的不是平台自己送出的、不屬於這個使用者、已經結束、或工作編號與紀錄不符，**When** 取消，**Then** 拒絕，不送出任何取消。（例外）
3. **Given** 沒有確認憑證的取消工作，**When** 代理收到，**Then** 拒絕。（例外）

### User Story 5 — 驗收：ampliseq 跑完（Priority: P1）

1. **Given** microbiome_test 的 10 個 fastq，設定與 2026-09-20 那次相同：
   - 引子 27F／1492R；
   - PacBio；
   - SILVA 138.2；
   - nf-core/ampliseq 2.18.0。

   **When** 送出並跑完，**Then** 平台顯示「成功」，task 數與 Nextflow 自己的 trace 一致，結果在專屬資料夾的 `results/`。（手動）

## Requirements *(mandatory)*

- **FR-001**: 新增代理工作種類 `launch_nextflow` 與 `cancel_run`。兩者都是**寫入**動作，必須帶這次終端機確認產生、綁定內容的確認憑證。沒有憑證、憑證不符或內容被改，一律拒絕。
- **FR-002**: `launch_nextflow` 是全 repo 唯一會提交的程式，登記在 `tests/no_second_run_state_test.sh` 的 `LAUNCH_ALLOW`，並指向「未確認就拒絕」的測試（憲法 4.0.0 原則 2）。
- **FR-003**: 主控工作腳本照 Seqera 的 HPC 啟動方式產生：
  - `#SBATCH -D`、`-J nf-<name>`、`--no-requeue`；
  - 主控佇列與送出選項；
  - 執行 `nextflow run <pipeline> -r <固定版本> -name -params-file -c -with-tower <endpoint>`；
  - 不設 `NXF_LOG_FILE`，讓 `.nextflow.log` 與 `.nextflow/history` 留在專屬資料夾，供 008 rebuild 讀。
- **FR-004**: 平台給 Nextflow 的 run token 依下列規則處理：
  - 在代理領走工作時才產生，平台只存雜湊。
  - 只存在於兩處：專屬資料夾裡權限 0600 的檔案，以及主控工作自己的行程環境。
  - 不寫進腳本本文，不出現在任何指令列，不被印出。
  - 收到 run 的 complete 時撤銷；無論如何，14 天後撤銷。
- **FR-005**: 進度的路線：主控工作 → relay（`lgn*:18080`，計算節點本來就用它）→ 登入節點迴圈位址上的反向通道 → 平台。
  - 反向通道開在使用者既有的共用連線上，由 `scripts/on_site.sh` 管理；
  - relay 對這個目的地只放行一個登入節點迴圈位址加一個 port；
  - 不新增任何常駐程式。
- **FR-006**: 送出前的預檢除了 007 的項目，還要檢查：
  - 反向通道與 relay 都通，而且 Nextflow 會走的那條路真的到得了平台；
  - 計費帳號已設定；
  - 容器快取可寫；
  - 專屬資料夾不存在。
- **FR-007**: 008 的接收端要能接受國網上 Nextflow 25.10.4（nf-tower 1.17.5）送出的事件；錄真實事件當測試素材。
- **FR-008**: `cancel_run` 只能取消平台自己送出、紀錄在案、屬於這個代理的主控工作。只對那一個工作編號送 `scancel`，並先用 `squeue` 核對名稱與使用者。
- **FR-009**: 平台記錄「送出交接」的事實：run 名稱、Slurm 工作編號、專屬資料夾、確認時間。run 的狀態一律來自 Nextflow 的事件或紀錄，平台不自己推斷（原則 2）。
- **FR-011**: 新增唯讀工作 `fetch_run_records`。
  - 只從 `launches` 記錄的專屬資料夾取回 Nextflow 自己的紀錄：`.nextflow.log*`、`.nextflow/history`，以及 log 裡指名的 trace。
  - 不跟隨符號連結，每檔上限 20 MB。
  - 平台存到本機後，由 `rebuild` 以這些紀錄為準補齊。
- **FR-010**: 自動測試全部用 007 的假站台，不連國網。真國網只做手動驗收（US5）與手動的通道實測。

## 不在範圍

1. 網頁確認頁、MCP 寫入工具（009）。這一片的送出與取消只能從平台的命令列做。
2. 自動重試、恢復（resume）、重新送出。
3. 雲端種類的送出。
4. 讓反向通道撐過共用連線的 8 小時上限。超過時，即時進度停住，但分析照跑，事後可從紀錄補齊。
5. 國網 M6 的規範答覆。這一片照舊方式，使用者在場時開連線。

## Success Criteria

- **SC-001**: 在國網上送出 microbiome_test 的 ampliseq，跑的過程中 `get_run` 能看到各 process 的進度，最後顯示成功，task 數與 trace 一致（手動）。
- **SC-002**: 送出與取消都只在終端機答 `y` 後發生；繞過確認的工作一律被代理拒絕（自動＋手動）。
- **SC-003**: 取消一個跑到一半的測試分析，國網上它的主控工作與 task 都停止。平台顯示 Nextflow 回報的結局（失敗），並列出「取消請求已於 T 送出」這個事實（手動）。
- **SC-004**: 整套測試在 WSL 與 CI 全綠，平台測試不准被跳過。

## Assumptions

- 國網連線照舊方式由使用者在 WSL 終端機開好。
- 登入節點上的 relay（`scripts/egress_ctl.sh`）在跑。
- 國網的 sshd 不允許把反向通道開給其他主機（2026-10-11 實測：只聽在迴圈位址），所以必須經過 relay。
