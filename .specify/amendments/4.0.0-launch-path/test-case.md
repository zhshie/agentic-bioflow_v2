# 測試案例：憲法 4.0.0 修訂（唯一的提交路徑，綁在使用者確認之後）

**計畫**：`.specify/amendments/4.0.0-launch-path/plan.md`（含 Revision 2）　**總覽**：`test-case-overview.md`

類型只有三種：
- 功能：計畫說要改的，改了。
- 例外：不該變的，沒變。
- 不在範圍：這次不做的，真的沒做。

本修訂改這些東西，不加任何提交程式：
- 文件；
- 一個檢查檔（`tests/no_second_run_state_test.sh`）；
- `platform/abf_station/handlers.py` 的一處寫法。

「自動」的測試檔：
- `tests/no_second_run_state_test.sh`（自測區）
- `tests/platform_direction_docs_test.sh`
- `tests/constitution_scope_test.sh`
- `tests/constitution_checks_exist_test.sh`
- `tests/platform_test.sh`（平台 pytest）

「手動」是驗收者讀 `git diff main...HEAD`、對兩個分支各跑一次檢查，或自己改一份副本做突變（mutation），不另加 `docs/TESTING.md` 步驟。一個案例同時有自動與手動部分時，算手動。

他的話（「照原本路線」等）給方向，不是輸入範例，所以 US4 看的是方向有沒有被守住。

## US1 — 憲法 3.0.0 → 4.0.0（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 4 版本頁尾 | 功能 | 修訂完成 | 讀憲法最後一行 | 恰為 `**Version**: 4.0.0 \| **Ratified**: 2026-09-28 \| **Last Amended**: 2026-10-11` | 自動：`tests/constitution_scope_test.sh`、`tests/platform_direction_docs_test.sh`（TC-001 已更新） |
| TC-002 | 計畫 4 修訂紀錄 | 功能 | 同上 | 讀 Amendments 區 | 在 3.0.0 之後有 `### 4.0.0 (2026-10-11): one submission path of our own, behind the user's confirmation`。<br>它含這幾段：<br>• Rationale<br>• What changes<br>• Impact on existing deployments：含 `existing deployments`，寫明沒有影響。不改任何 hook／script／command／skill；允許清單為空，合併時 repo 沒有任何提交路徑，007b 才建立；plugin 仍經 Seqera、在 `hooks/confirm_launch.sh` 之後啟動<br>• Version（MAJOR）<br>• Approval（maintainer）<br>另記錄 007b 必須修改 `platform/tests/test_scope.py` TC-071 與 `platform/tests/test_station_static.py` TC-084。<br>2.0.0／2.0.1／2.1.0／3.0.0 四則仍在 | 手動：驗收者讀憲法 |
| TC-003 | 計畫 Why、4 Rationale | 功能 | 同上 | 讀 4.0.0 的 Rationale | 引用他的話原文：「照原本路線」「雲端伺服器（像 Seqera 有 AWS 等）也要一起」「雲端伺服器不限於 AWS，請直接參考 Seqera Platform 的設計」。<br>說明 3.0.0 的「no submission script of our own」為何不再適用：<br>• 自架平台須做 Seqera 的送出步驟<br>• Nextflow 沒有送自己 head job 的指令<br>• Tower Agent 封閉且只連 Seqera | 手動：驗收者讀憲法 |
| TC-004 | 計畫 1 原則 2 前段 | 功能 | 同上 | 讀原則 2 | 仍含：<br>• Nextflow 自己的記錄（trace、report、log、nf-tower plugin 事件）是 run 的真相<br>• Platform 的顯示與之不一致時，以 Nextflow 為準<br>• `No file in this repository MAY keep a second copy of a run's state`<br>• `no state machine and no monitoring daemon beyond the channels its check allow-lists`<br>• `follows Seqera's nouns` | 自動：`tests/platform_direction_docs_test.sh`（TC-004 已更新） |
| TC-005 | Revision 2 第 1 項 | 功能 | 同上 | 讀原則 2 | 含 `There MAY be at most one submission path of our own`，並明寫是「the station agent's launch job, which hands the Nextflow head job to the site's own scheduler the way Seqera Platform does」；不再含 `exactly one` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-006 | 計畫 1 確認 | 功能 | 同上 | 讀原則 2 | 含 `runs only after the user has seen the full launch command and confirmed it`；含「提交的檔案與拒絕未確認啟動的測試一起列入檢查的允許清單，其他任何東西都不得提交」之意 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-007 | 計畫 1 交接後 | 功能 | 同上 | 讀原則 2 | 含 `everything known about the run comes from Nextflow's records` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-008 | 計畫 1 Check 行 | 功能 | 同上 | 讀原則 2 的 Check 行 | 仍引用 `tests/no_second_run_state_test.sh`（檔案存在），並註明其提交掃描涵蓋 `scripts/` 與 `platform/`；括號內不引入另一個不存在的 `tests/` 檔名 | 自動：`tests/platform_direction_docs_test.sh`、`tests/constitution_checks_exist_test.sh` |
| TC-009 | 計畫 1 理由句 | 功能 | 同上 | 讀原則 I 的 Rationale 段 | 多一句：這條唯一的提交路徑存在，是因為自架平台必須做 Seqera 的送出步驟，而且只有使用者的確認才讓它跑；其餘 Rationale 原文仍在 | 手動：驗收者讀憲法 |
| TC-010 | 計畫 4 Version | 功能 | 同上 | 讀 4.0.0 的 Version 段與頁尾 | 寫 MAJOR，理由是原則 2 被重新定義；版本是 4.0.0，不是 3.1.0 | 手動：驗收者讀憲法（Governance：移除或重新定義原則為 MAJOR） |
| TC-011 | Revision 2 第 1 項：條文與檢查一致 | 功能 | 同上 | 讀原則 2、4.0.0 紀錄與檢查檔 `LAUNCH_ALLOW` 邏輯，兩邊對照 | • 條文只說「至多一條」，不要求合併當天已存在<br>• 修訂紀錄明寫合併時一條都沒有，007b 才建立<br>• 檢查在 `LAUNCH_ALLOW` 多於一筆時失敗（見 TC-026）<br>• 條文與檢查對條數的說法一致，沒有一邊說「恰好」、一邊允許零條 | 手動：驗收者對照條文與檢查 |
| TC-012 | 計畫 1 舊禁令移除；3.0.0 TC-006 | 例外 | 同上 | 搜尋憲法 | 原則 2 內不再有無條件的 `no submission script of our own`；憲法全文仍不含 `run index`（它仍在 ROADMAP 等待清單） | 手動：驗收者 grep；`run index` 部分另有自動：`tests/platform_direction_docs_test.sh`（TC-006） |

## US2 — 檢查加強：`tests/no_second_run_state_test.sh`（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 計畫 2 掃描一讀 `platform/abf_station` | 功能 | 檢查已更新 | 自測：暫存樹 `platform/abf_station/x.py` 寫 `subprocess.run(["sbatch", "job.sh"])`，`LAUNCH_ALLOW` 無條目 | 結束碼 1 | 自動：`tests/no_second_run_state_test.sh` 自測（新增） |
| TC-014 | 計畫 2 掃描一讀 `platform/abf_platform`；`.py` 與 `.sh` | 功能 | 同上 | 自測：`platform/abf_platform/x.py` 與 `platform/abf_platform/x.sh` 各寫一行提交（`sbatch job.sh`），無條目 | 兩者都結束碼 1 | 自動：同上（新增） |
| TC-015 | 計畫 2 `platform/tests/` 排除 | 功能 | 同上 | 自測：`platform/tests/x.py` 寫 `sbatch job.sh` | 結束碼 0 | 自動：同上（新增） |
| TC-016 | 計畫 2 列入且測試存在 | 功能 | 同上 | 自測：`platform/abf_station/x.py` 提交，`LAUNCH_ALLOW_EXTRA` 列它，並指向 `platform/tests/` 下一個存在、且含 `def <name>(` 的測試檔 | 結束碼 0 | 自動：同上（新增） |
| TC-017 | 計畫 2 測試名不存在 | 功能 | 同上 | 自測：同上，但測試檔存在、不含該測試定義 | 結束碼 1，輸出含 `LAUNCH  platform/abf_station/x.py submits, but its confirmation test <name> does not exist` | 自動：同上（新增） |
| TC-018 | 計畫 2 測試檔不存在 | 功能 | 同上 | 自測：同上，但測試檔不存在 | 結束碼 1，同一句訊息 | 自動：同上（新增） |
| TC-019 | 計畫 2 過期條目 | 功能 | 同上 | 自測：`LAUNCH_ALLOW_EXTRA` 列一個檔，該檔已無任何提交 | 結束碼 1，輸出以 `STALE` 開頭，與其他過期條目同形 | 自動：同上（新增） |
| TC-020 | 計畫 2 條目格式、本 PR 為空 | 功能 | 同上 | 讀檢查檔的 `LAUNCH_ALLOW` | 註解說明格式 `<file>\|<test file>::<test name>\|<why>`；本 PR 內沒有任何未註解條目；對真實 repo 跑檢查結束碼 0 | 手動：驗收者讀檔並跑 `bash tests/no_second_run_state_test.sh` |
| TC-021 | 計畫 2 檔頭 | 功能 | 同上 | 讀檔頭註解 | 寫明四項掃描、掃描一涵蓋 `platform/`、`LAUNCH_ALLOW` 的用途，並引用 constitution 4.0.0；保留「a net, not a proof」的自承 | 手動：驗收者讀檔 |
| TC-022 | Revision 2 第 2 項：`handlers.py` | 功能 | 同上 | 以掃描一的正規式讀 `platform/abf_station/handlers.py` 的 `CHECK_ORDER` 與 `for tool in` 兩處；對照 main 的 diff | • 對真實 repo 跑檢查，結束碼 0<br>• 兩處不再有「引號緊貼 `sbatch`」的形狀，靠的是改寫該檔，不是改弱 `CMDS`／`PFX`／引號規則（這三者與 main 逐位元組相同）<br>• `CHECK_ORDER` 的 id 與順序、`has_sbatch` 欄位、所有使用者看得到的檢查文字都不變<br>• 改寫處有註解說明原因 | 手動：驗收者跑檢查、讀 diff |
| TC-023 | Revision 2 第 2 項：不得靠允許清單遮蓋 | 功能 | 同上 | 檢查 `handlers.py` 不在 `LAUNCH_ALLOW`、不在 `SUBMIT_ALLOW`；驗收者在副本的 `handlers.py` 加一行真提交 `subprocess.run(["sbatch", "job.sh"])` | 兩份清單都沒有它；副本跑檢查結束碼 1 | 手動：驗收者做突變 |
| TC-024 | 計畫 2、Verification 突變 | 功能 | 同上 | 驗收者在副本逐一拿掉：<br>• 掃描一的 `platform/` 範圍<br>• `platform/tests/` 排除<br>• 定義存在檢查<br>• 過期檢查<br>• 多於一筆檢查<br>• 路徑限定檢查 | 每一次，對應的自測回報 `SELFTEST FAIL` 且結束碼 1（每條新自測都能變紅） | 手動：驗收者做突變 |
| TC-025 | Revision 2 第 4 項：`LAUNCH_ALLOW_EXTRA` 只在暫存樹生效 | 功能 | 同上 | 自測：不設 `NO_RUN_STATE_ROOT`，設 `LAUNCH_ALLOW_EXTRA` 塞一筆條目，對含提交的樹跑檢查 | 注入的條目被忽略，仍失敗（真實樹不能靠環境變數放行） | 自動：同上（新增） |
| TC-026 | Revision 2 第 1 項：至多一條 | 功能 | 同上 | 自測：`LAUNCH_ALLOW_EXTRA` 有兩筆條目（各有存在的測試） | 結束碼 1，輸出含 `LAUNCH  only one submission path is allowed (I.2); found 2` | 自動：同上（新增） |
| TC-027 | Revision 2 第 4 項：測試須是 `platform/tests/` 下的定義 | 功能 | 同上 | 自測三個情況：<br>(a) 測試名只在註解或字串出現<br>(b) 測試檔不在 `platform/tests/` 下<br>(c) 定義寫成 `async def <name>(` | (a)、(b) 結束碼 1，同 TC-017 的訊息；(c) 結束碼 0 | 自動：同上（新增） |
| TC-028 | Revision 2 第 4 項：條目只准 `platform/abf_platform`／`platform/abf_station` | 功能 | 同上 | 自測：`scripts/a.sh` 寫 `sbatch job.sh`，並被列入 `LAUNCH_ALLOW_EXTRA` | 結束碼 1，輸出含 `LAUNCH  scripts/a.sh: only platform code may hold the launch path`；`scripts/` 的提交不因此放行 | 自動：同上（新增） |
| TC-029 | 計畫 2「掃描二至四仍只看 `scripts/`」 | 例外 | 同上 | 自測：`platform/abf_station/x.py` 寫 `nohup ./w &`、`platform/abf_platform/x.py` 寫 `runs.db` | 結束碼 0（平台的 index 與 `platform.db` 不被掃描二至三誤判） | 自動：同上（新增） |
| TC-030 | 不得變鬆 | 例外 | 同上 | 跑檢查 | 既有 28 條自測原樣在、全過 | 自動：`tests/no_second_run_state_test.sh` |
| TC-031 | 預檢行為不變 | 例外 | 同上 | 跑平台測試 | `abf_station` 預檢仍檢查 `sbatch`、`squeue`、`sinfo`，並回報同樣的 pass／fail 文字；平台 pytest 全綠 | 自動：`tests/platform_test.sh`（CI） |

## US3 — 引用原則 2 的文件（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 計畫 3 與 Revision 2：`platform_direction_docs_test.sh` TC-004 | 功能 | 修訂完成 | 讀該檔 TC-004 區 | • 舊句換成 `no state machine and no monitoring daemon beyond the channels its check allow-lists` 與 `There MAY be at most one submission path of our own`<br>• 新增 `runs only after the user has seen the full launch command and confirmed it` 與 `everything known about the run comes from Nextflow's records`<br>• 其餘 TC 斷言原樣 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-033 | Revision 2 第 3 項：釘字更新 | 功能 | 同上 | 讀 `constitution_scope_test.sh` 第 29、31 行，與 `platform_direction_docs_test.sh` 的 TC-001、TC-059 | • 版本與日期期望值改為 4.0.0／2026-10-11<br>• TC-059 的 `CLAUDE.md points at constitution`，以及 README 的 `the truth under constitution`，都改為 4.0.0<br>• 2.0.0 與 3.0.0 修訂紀錄的斷言仍在<br>• 沒有斷言被刪或放寬 | 自動：兩檔都綠 |
| TC-034 | 計畫 3 README | 功能 | 同上 | 讀 `README.md` 第 56 行，與其後的 constitution 版本字樣 | 第 56 行寫 `no submission script outside the one confirmed launch path (constitution 4.0.0)`，句子其餘部分不變；`the truth under constitution` 後為 4.0.0 | 手動：驗收者讀 diff |
| TC-035 | Revision 2 第 3 項：CLAUDE.md 與 PRINCIPLES.md | 功能 | 同上 | 讀 `CLAUDE.md` 第 11 行，與 `docs/PRINCIPLES.md` 談原則 2 處 | • `CLAUDE.md` 寫 `4.0.0, principle 2`（不再是 3.0.0）<br>• 兩檔都沒有把原則 2 寫得與 4.0.0 不同<br>• `Constitution 2.0.0`、`hooks/in_use.sh` 等 TC-019／TC-059 釘字仍在 | 手動：驗收者一致性閱讀；`tests/constitution_scope_test.sh` 與 `tests/platform_direction_docs_test.sh` 仍綠 |
| TC-036 | 計畫 3 與 Revision 2 的 ROADMAP | 功能 | 同上 | 讀「Principles waiting for a check」與階段 1 那列 | • 「Every platform write tool (launch, delete, clear `work/`) refuses without the user's confirmation step」那列仍在，附註 `4.0.0 binds the launch path to this check; 007b builds it for launch.`<br>• 階段 1 那列在 slice 1 句後有 `Slice 2 (007b) launches through the agent, under constitution 4.0.0, behind the user's confirmation.`<br>• 其他列不變 | 手動：驗收者讀 diff；`tests/platform_direction_docs_test.sh`（TC-023）仍綠 |
| TC-037 | 計畫 3 一致性 | 功能 | 同上 | 搜尋全 repo `no submission script` 與 `no submission` | 沒有任何現行規則文件仍把它寫成無條件禁令；只出現在歷史段（3.0.0 修訂紀錄、舊 bugs／amendments）與 README 的限定句 | 手動：驗收者 grep |
| TC-038 | 計畫 3 hook 不動 | 例外 | 同上 | 比對 `hooks/confirm_launch.sh` | 與 main 逐位元組相同（含第 7 行註解） | 手動：驗收者 diff |

## US4 — 他的話（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-039 | 「照原本路線」「雲端伺服器（像 Seqera 有 AWS 等）也要一起」 | 功能 | 修訂完成 | 讀原則 2 與 4.0.0 紀錄 | 路線沒轉彎：<br>• 原則 2 仍要求 Seqera 的名詞<br>• 提交路徑寫成「the way Seqera Platform does」<br>• 紀錄寫明這條路徑是為了讓自架平台能做 Seqera 做的事，不是另起爐灶 | 手動：驗收者閱讀 |
| TC-040 | 「雲端伺服器不限於 AWS，請直接參考 Seqera Platform 的設計」 | 功能 | 同上 | 讀原則 2、4.0.0 紀錄、檢查檔的提交正規式 | • 條文以「the site's own scheduler」稱呼，不點名 AWS 或單一排程器（與 II.4 一致）<br>• 檢查的 `CMDS` 仍涵蓋 `sbatch`／`qsub`／`bsub`／`srun`／`nextflow run`／`tw launch`，沒有只針對 Slurm 或 AWS | 手動：驗收者閱讀 |

## 憲法與安全網（不得改變的）

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 | Safety Net 全段（含第 3 條：啟動需完整顯示並等確認） | 例外 | 修訂完成 | 與固定字串及指紋比對 | 逐字不變，無新增段落，仍指 `hooks/confirm_launch.sh` | 自動：`tests/constitution_scope_test.sh`（TC-040..044） |
| TC-042 | 原則 1、3–13 | 例外 | 同上 | `git diff main...HEAD -- .specify/memory/constitution.md` | 原則 1 與原則 3–13 的文字與 Check 行零差異；原則 2 以外只有三處差異：頁尾、Principle I 的 Rationale 多一句、Amendments 多一則 | 手動：驗收者 diff |
| TC-043 | 前言「每條規則指名存在的 Check」 | 例外 | 同上 | 跑 `constitution_checks_exist_test.sh` | 結束碼 0，輸出 `all 14 rules`；新增文字沒有讓規則解析多出或遺漏 | 自動：`tests/constitution_checks_exist_test.sh` |
| TC-044 | 行為不變 | 例外 | 同上 | 比對 `hooks/`、`scripts/`、`commands/`、`skills/`、`.claude-plugin/` | 與 main 逐位元組相同；`platform/` 的差異只有 TC-022 所需的最小改寫，行為不變 | 手動：驗收者 diff |
| TC-045 | Safety Net「不變」的誠實性 | 例外 | 同上 | 讀 4.0.0 紀錄與原則 2 | • 明寫 Safety Net 的範圍（hook 管的 session）不涵蓋平台自己的路徑，由原則 2 自己承擔確認要求，沒有 hook 守這條路徑<br>• 不暗示 hook 會擋<br>• 把閘門移進平台工具層，仍列為等待中的原則 | 手動：驗收者閱讀 |
| TC-046 | 不弱化測試 | 例外 | 同上 | 比對 `tests/` 與 `platform/tests/` 的差異 | • 差異只有：版本／日期期望值（TC-033）、TC-004 的拆句與新增（TC-032）、新增的自測與斷言<br>• 沒有斷言被刪、放寬、跳過<br>• `SUBMIT_ALLOW`／`DAEMON_ALLOW`／`CMDS`／`PFX`／`TW_NOUNS` 與 main 相同<br>• `test_scope.py` TC-071 與 `test_station_static.py` TC-084 零差異 | 手動：驗收者 diff |
| TC-047 | 綠燈 | 例外 | 同上 | WSL 跑 `bash tests/run_all.sh`，或看 CI | 不比 main 差：CI 100/100；WSL 允許 `conditions_matrix` 因環境原因同樣失敗（99/100） | 自動：`tests/run_all.sh`（CI） |
| TC-048 | 不改 spec／TC | 例外 | 實作期間 | 比對 `.specify/amendments/4.0.0-launch-path/test-case*.md` 與已確認版本 | 實作期間零修改 | 手動：驗收者 diff |

## US5 — 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-049 | 不做：啟動 job 本身（007b） | 不在範圍 | 修訂完成 | grep 新增與既有 `platform/` 非測試程式碼的提交 | 沒有新的提交、`nextflow run`、`--wrap` 或 `subprocess` 啟動程式；`LAUNCH_ALLOW` 無任何條目；repo 仍是零條提交路徑 | 手動：驗收者 grep 與 diff |
| TC-050 | 不做：確認步驟的形式（終端機 yes/no、009 的網頁確認頁） | 不在範圍 | 同上 | 檢查 diff | 沒有任何確認提示、token 或確認頁的程式碼 | 手動：驗收者 diff |
| TC-051 | 不做：把閘門移進平台工具層 | 不在範圍 | 同上 | 讀 Safety Net 範圍條件 3 與 ROADMAP | 範圍條件 3 文字不變；「Gates live in the platform's tool layer」仍在等待清單，未寫進憲法規則 | 手動：驗收者閱讀 |
| TC-052 | 不做：其他等待中的原則（含 run index 規則，另開修訂 PR） | 不在範圍 | 同上 | 讀憲法與 ROADMAP 等待清單 | 憲法不含 `run index`；其餘等待列仍在，沒有被併入 | 自動：`tests/platform_direction_docs_test.sh`（TC-006、TC-023） |
| TC-053 | 不做：release | 不在範圍 | 同上 | 讀 `.claude-plugin/plugin.json` 與 diff | `version` 仍為 `2.17.0`；沒有新 changelog 或 tag | 手動：驗收者 diff |
| TC-054 | 不做：007b、009 的 spec／tasks | 不在範圍 | 同上 | 列出 `specs/` | 沒有新增 007b 或 009 相關目錄 | 手動：驗收者 diff |
