---
id: cancel-resume-folder
title: 取消「續跑中的 run」不再被站台誤拒（資料夾核對要認得續跑沿用原 run 的資料夾）
tier: A
kinds: backend
lane: L1
base: v3（`origin/v3` @ 279363b；所有程式碼行號都是該版本）
source: developer-agent 讀碼查證（2026-10-24，未實機跑）；規劃者先前的懷疑已被讀碼證實
---

# cancel-resume-folder

> A 級 bug 修正：把行為拉回規格。規格（`cancel.py` 檔頭、spec 007b FR-008）要的是「確認過的那一個 head job，核對名稱、擁有者、資料夾」，不是「資料夾名必須等於 run 名」。續跑（resume）依設計沿用原 run 的資料夾，所以現在續跑中的 run 一律取消不了。

## 目標
站台的 `cancel_run` 在核對資料夾時，認得「續跑嘗試 `<root>-a<N>` 的資料夾是原 run `<root>` 的資料夾」，取消續跑中的 run 能成功；其他不對的資料夾（別的 run、`/etc`、`..`）照舊拒絕。對使用者的意義：續跑卡住或跑錯時能按停，不會被告知「資料夾不對」而只能去 HPC 手動 `scancel`。

### 查證結果（動手前的事實，皆 `origin/v3`）
- 續跑的內容包：`platform/abf_station/launch.py:903-904` 的 `render_resume_bundle` 令 `run_name=<root>-a<N>`、`run_folder=origin["run_folder"]`（原 run 的資料夾）。測試也釘著：`platform/tests/test_resume_render.py:94`（`b["run_folder"] == origin["run_folder"] and b["run_name"] == "run-one-a2"`）。
- 平台記錄：`platform/abf_platform/jobs.py:547-549` 強制「續跑用原資料夾」，`jobs.py:580-582` 把續跑那列的 `run_name=<root>-a2`、`run_folder=原資料夾` 寫進 `launches`。
- 取消內容包由那列組成：`platform/abf_launch/build.py:303-304`（`run_name`、`run_folder` 原樣取自該列）。
- **誤拒處**：`platform/abf_station/cancel.py:35` `folder != "%s/runs/%s" % (env["workDir"], run)`。續跑時 `run="x-a2"`、`folder=".../runs/x"`，必定不等，丟 `Refusal("run 名稱或專屬資料夾不對 …")`，連 `squeue` 都不問。
- 排程器那邊本來就對得上：head 腳本 `launch.py:424-425` 的 `-D <run_folder>`、`-J nf-<run_name>`，續跑時是（原資料夾、`nf-x-a2`），所以 `cancel.py:55`（名稱）與 `:59`（資料夾）不需要改。
- 同病灶：`platform/abf_station/fetch.py:42` 有一模一樣的比對；`jobs.py:195` 把續跑那列的 `run_name`/`run_folder` 交給它，所以讀續跑 run 的紀錄也被拒。**一併修**（同一個共用判斷）。
- 不受影響：`gcb_launch.py:237`（Google Batch 的續跑本來就被拒，`test_gcb_launch.py:1035-1050`）。
- 命名規則：`platform/abf_launch/build.py:321-324` `attempt_name(root, N)` 是 `root[:64-len(suffix)] + "-a%d" % N`（`suffix="-a%d"`）。

## 維護者原話（verifier 出題用）
本任務沒有他的逐字裁示；來源是規劃者的疑點與本檔「查證結果」。他的原始要求等價於下列兩句（出題以此為準）：
- 「取消續跑中的 run 不該被拒」→ T1、T2。
- 「其他不是這個 run 的資料夾仍要拒絕，不放寬安全檢查」→ T3–T8。

## 範圍：檔案（只准改這些，共 5 個）
- `platform/abf_station/launch.py`（在 `RUN_NAME`（:33）附近新增共用函式 `run_folder_ok(work, run, folder)`；不動其他函式）
- `platform/abf_station/cancel.py`（只改 :35 的比對）
- `platform/abf_station/fetch.py`（只改 :42 的比對）
- `platform/tests/test_station_cancel.py`（新增測試；既有斷言一律不改）
- `specs/cancel-resume-folder/ledger.md`（新，executor 進度帳本）

**不准動**：`platform/abf_platform/**`、`platform/abf_launch/**`（取消內容包的組法正確，不改）、`gcb_launch.py`、`hooks/`、`.claude-plugin/plugin.json`、`spec.md`、`test-case*.md`、`.github/`、憲法。

## 作法
1. `launch.run_folder_ok(work, run, folder) -> bool`（純函式，不碰檔案系統）：
   - `folder == "%s/runs/%s" % (work, run)` → True（首次送出、重跑，行為不變）。
   - 否則，`run` 符合 `^(.+)-a([2-9]|[1-9][0-9]+)$`，且 `folder` 以 `"%s/runs/" % work` 開頭，剩下的 `root` 符合 `RUN_NAME`（因此沒有 `/`、`..`），且 `run == root[:64-len(suffix)] + suffix`（`suffix="-a" + N`，即 `attempt_name` 的反向）→ True。
   - 其他一律 False（包含 `run` 無 `-a<N>` 尾巴、`root` 自己也是 `…-a<N>` 之外的任何不吻合、`N` 是 0／1／前導零如 `-a02`）。
2. `cancel.py:35` 與 `fetch.py:42` 的 `folder != "%s/runs/%s" % (…)` 改成 `not launch.run_folder_ok(env["workDir"], run, folder)`；其餘條件（`isinstance(run, str)`、`RUN_NAME.match`）與錯誤訊息文字不變。
3. 不改 `cancel.py:55`、`:59`：它們核對的是排程器的實際值，續跑時就是（`nf-<run>`、原資料夾），不需要放寬。

## 失敗先行測試（`platform/tests/test_station_cancel.py`，用現有的 `site`/`fake`/`agent_on`/`cancel_job`/`fetch_job`）
手算：`work=site.work`；原 run `run-a` 的資料夾 `folder(site, "run-a")`；續跑名 `run-a-a2`。
| # | 情境 | 期望 | 現在 |
|---|---|---|---|
| T1 | 取消：`run_name="run-a-a2"`、`run_folder=folder(site,"run-a")`，排程器有 `4243\|nf-run-a-a2\|tester\|<run-a 資料夾>` | `state=="done"`，`scancels==["scancel 4243"]` | 紅（`refused`） |
| T2 | 同 T1 但 N=10（`run-a-a10`）、root 長 64 字、續跑名＝`root[:60] + "-a10"`（被截斷的名字，依 `attempt_name` 造） | `done` | 紅 |
| T3 | 取消：`run_name="run-a-a2"`、`run_folder=folder(site,"run-b")`（別人的資料夾） | `refused`，無 scancel | 綠（鎖住） |
| T4 | 取消：`run_name="run-a-a1"`、folder=run-a | `refused` | 綠 |
| T5 | 取消：`run_name="run-a-a02"`、folder=run-a | `refused` | 綠 |
| T6 | 取消：`run_name="run-b"`、folder=run-a（無 `-a<N>`） | `refused` | 綠 |
| T7 | 取消：`run_name="run-a-a2"`、`run_folder="%WORK%/runs/run-a/.."` 與 `"%WORK%/runs/../x"` | `refused` | 綠 |
| T8 | 取消：續跑名對、資料夾對，但排程器裡該號碼的名稱是 `nf-run-a`（不是 `nf-run-a-a2`） | `refused`（名稱不符） | 紅→修後仍 `refused`，證明名稱核對沒被放寬 |
| T9 | 讀紀錄：`fetch_job(site, run="run-a-a2", run_folder=folder(site,"run-a"))`（先 `make_records(site)`） | 成功且 `files` 含 `.nextflow.log` | 紅 |
| T10 | 讀紀錄：`run-a-a2` + run-b 的資料夾 | `refused` | 綠 |
| T11 | `launch.run_folder_ok` 單元：上述各例與 `work` 結尾斜線、空字串、非字串 `folder` | 如上表；非字串回 False 不丟例外 | 紅（函式不存在） |

**現在會紅**：T1、T2、T9、T11（T8 是修後防護）。executor 先跑一次，貼出紅的輸出再動手；T3–T7、T10 現在就綠，用來證明沒放寬。

**會改斷言的既有測試：無。** 已核對 `git grep` 的釘子（要全綠且不改）：`test_station_cancel.py:138`（`/etc` 與 `../x` 仍 refused）、`:204-206`（fetch 的 `/etc`、`run-b`、`runs/run-a/..` 仍 refused）、`test_gcb_launch.py:845-853`（GCB 取消不走新函式）、`test_resume_render.py:94`、`test_resume_lineage.py:298`、`test_station_resume.py`。

## 完成標準（done when）
- T1–T11 全綠；`platform/tests/test_station_cancel.py` 與整個 `bash tests/run_all.sh`（在 WSL，見 repo `CLAUDE.md`「For the executor and verifier」）綠。
- `git diff --name-only` 只含上列 5 個檔；「不准動」清單零命中；`hooks/` 無改動。
- 新增測試 ≤ 20 條（含參數化展開）；既有測試沒有被刪、跳過或放寬。
- 沒有真的連 Slurm／HPC：測試只用現成的 `FakeSite`。

## 環境事實
- 本計畫是讀碼推得，**沒有實機重現**（規劃者與本檔作者都沒跑）。T1 在動手前先紅，就是重現證據；若 T1 在 base 上就綠，停下回報 BLOCKED，代表推論有誤。
- 全套測試必須在 WSL／Linux 跑；worktree 不可在同步磁碟（見 repo `CLAUDE.md`）。
- 續跑的 head job 用 `#SBATCH -D <原資料夾>`、`-J nf-<續跑名>`（`launch.py:424-425`），測試的 `FakeSite.add_job(id, name, user, folder)` 照這個形狀造。

## 不做
- 不改取消內容包的組法（`build.py:303`）、不改平台資料庫、不加 migration（**不需要 migration**：沒有動資料表或 JSON 欄位內容，只放寬站台一處比對）。
- 不處理 Google Batch 的取消（續跑尚未支援）。
- 不新增設定鍵、不改錯誤訊息文字、不改 `slurm` 名稱／擁有者核對。

## 裁決
- **fetch.py 一併修**：同一個比對、同一個原因，且 `jobs.py:195` 對續跑那列會同樣送出（原資料夾、續跑名）；分兩個任務會在同一函式上打架。若維護者要只修取消，把 `fetch.py` 與 T9–T10 拿掉即可，其餘不變。
- **用「反推 `attempt_name`」而不是「去掉 `-a<N>` 尾巴」**：根名超過 61 字時會被截斷，單純去尾巴會對不上資料夾，也會放過 `x-a2` 指向任意以 `x` 開頭的資料夾；反推能精確只接受平台自己會造出的組合。
- **放寬只加在資料夾比對**：名稱（`nf-<run>`）、擁有者、排程器回報的工作目錄三項核對保持原樣，安全姿態不變。

## 裁決二（2026-10-24，developer-agent）
1. fetch.py:42 同一個錯一起修，留在範圍內（T9、T10 保留）。
2. T1 在 base 上若是綠的＝計畫前提錯，回 BLOCKED，不要硬改。

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
