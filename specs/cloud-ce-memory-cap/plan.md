---
id: cloud-ce-memory-cap
title: 雲端計算環境可設單一 task 的記憶體上限（maxMemoryGB），且平台寫的 resourceLimits 不再吃掉使用者自己設的鍵
tier: B
kinds: backend
lane: L30-cloud-ce-memory
branch: fix/cloud-ce-memory-cap
base: origin/v3（行號取自 origin/v3@d1fa55e，executor 開工前先 `git fetch origin v3`，再用 `git show origin/v3:<檔>` 重查）
source: 2026-10-29 AWS Batch 真實試跑（他以「試跑」核准）。環境 aws1 的 maxvCpus 是 4，他在環境的 nextflowConfig 寫了 `process.resourceLimits = [cpus: 4, memory: 6.GB]`，但平台寫的 aws.config 只有 `[cpus: 4]`，整張表被換掉、記憶體上限消失；nf-core 預設要 12–36 GB，超過 Batch 機器，task 永遠卡在 unschedulable，試跑 1 因此掛住
---

# cloud-ce-memory-cap

> 只有計畫、沒有程式。B 級（會改使用者送出時產生的設定檔內容）→ 需要使用者驗收；verifier 通過＋CI 綠後交 developer-agent 回報他，不自合。

## 目標
- 以前它會：雲端環境（AWS／Google Batch／Azure Batch）只能設 `maxvCpus`，平台寫的 `<aws|gcb|azure>.config` 一律寫成 `process.resourceLimits = [cpus: N]`；這行在 `nextflow.config` 之後讀，**整個換掉**使用者在環境 `nextflowConfig` 自己寫的 resourceLimits（包括他設的記憶體上限），沒有記憶體上限的 task 會要求超過機器的記憶體而永遠排不上。
- 以後改成：環境多一個選填的 `maxMemoryGB`（單一 task 的記憶體上限），平台寫成 `[cpus: N, memory: M.GB]`；若使用者在 `nextflowConfig` 已經寫了 resourceLimits，平台把兩邊**合併**（同一個鍵取較小的、只有使用者設的鍵保留），絕不默默丟掉使用者設的鍵；讀不懂他寫的就拒絕送出並說清楚怎麼改。
- 對使用者的意義：送雲端時，他設的記憶體上限會真的進到跑的設定裡，不再因為平台多寫一行就失效。

## 維護者原話（verifier 出題用）
- 這一件沒有逐字原話。來源是 2026-10-29 AWS 試跑的實際失敗（他當時說「試跑」核准整個試跑）；下面「作法」的每個預期值都來自該次試跑的設定檔與 launch.py 的程式，不是新需求。
- 試跑的事實（verifier 把它當真實案例出題）：環境 `maxvCpus: 4`、環境 `nextflowConfig` 含 `process.resourceLimits = [cpus: 4, memory: 6.GB]`；平台產生的 aws.config 為 `process.resourceLimits = [cpus: 4]`。
- 他的一貫要求：「絕不放寬安全網」；設定檔裡的值必須經過 `_gcb_quote`／既有字元檢查，不得讓使用者文字未經檢查地進到平台寫的檔。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/compute_envs.py`（三個 `_*_CONFIG` 元組加 `"maxMemoryGB"`；三個 `_check_gcb`／`_check_aws`／`_check_azure` 各加一段檢查，緊接在各自 `maxvCpus` 檢查後面）
- `platform/abf_station/launch.py`（三個 `_check_*_ce` 驗證並放進 bundle 的 `ce`；新增**一個**共用的小函式組出 resourceLimits 那一行；三個 `_gcb_config`／`_aws_config`／`_azure_config` 改呼叫它）
- `platform/abf_launch/build.py`（三個送出確認畫面各多一列記憶體上限，只在有設時才出現）
- `docs/PLATFORM.md`（只動 `maxvCpus` 與 `process.resourceLimits` 相關的六處表格列：約 269、313、331、372、437、496 行；加 `maxMemoryGB` 與合併規則）
- 測試：**只新增**測試函式，不改任何既有斷言——`platform/tests/test_aws_ce.py`、`test_gcb_ce.py`、`test_azure_ce.py`、`test_aws_launch.py`、`test_gcb_launch.py`、`test_azure_launch.py`
- **不准碰**：`web/`、`.github/`、`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.claude-plugin/plugin.json`、`docs/TESTING.md`、`platform/abf_platform/compute_envs.py` 的 `snapshot()`（它給代理看的欄位，既有測試鎖死了集合，見下）、`platform/abf_station/launch.py` 的 Slurm 路徑與上述以外的其他函式、任何既有測試的既有斷言。
- 註：`launch.py` 這次**必須**改——resourceLimits 就是在那裡寫的（`launch.py:681`、`:860`、`:1036`），不改它做不到。

## 作法
- **證據**（origin/v3@d1fa55e）：
  - `launch.py:681`（Google Batch）、`:860`（AWS）、`:1036`（Azure）：`if ce["maxvCpus"] is not None: lines.append("process.resourceLimits = [cpus: %d]" % ce["maxvCpus"])`——三處同樣寫法，這就是整張表被換掉的地方。
  - `launch.py:772-774`（Google Batch；AWS 與 Azure 同形）：`nextflow.config` 是使用者的 `nextflowConfig` 原文加 `OVERWRITE_BLOCK`；`head.sh` 用 `-c nextflow.config -c aws.config`（`launch.py:877`，Google 是 `:698`，Azure 是 `:1053`），後面的檔贏。
  - `launch.py:160-183` `snapshot_ce` 把環境轉成 bundle 用的 dict（`maxvCpus` 在 `:170`、`:175`、`:181`）；三個 `_check_*_ce` 逐欄驗證（`maxvCpus` 在 `:630-633`、`:826-829`、`:997-1000`），驗證後的 `nextflowConfig` 在 `:636-638`、`:832-834`、`:1003-1005`。
  - `compute_envs.py:315-316`、`:410`、`:466`：三個 `_*_CONFIG` 元組，未知鍵被拒（例如 AWS 的 `:421-426` "unknown setting"）；`maxvCpus` 檢查在 `:403-405`、`:459-461`、`:521-523`。
  - `build.py:670-671`、`:691-692`、`:713-714`：三個確認畫面各有一列「單一 task 的 cpus 上限」。
  - **不需要 migration 的理由**：環境設定存在 `compute_envs.config_json` 這一欄的 JSON 文字裡（`compute_envs.py:611` 讀、`:722`／`:754` 寫），`maxMemoryGB` 只是 JSON 多一個選填鍵；沒有新欄位、沒有新表，舊的環境沒有這個鍵就等於沒設。
- **決定一：新鍵 `maxMemoryGB`**。選填、整數 1 到 10000（同 `maxvCpus` 的寫法與錯誤句型），三種雲端環境都加；布林、字串、小數、0 都拒。錯誤訊息固定：`maxMemoryGB must be a whole number from 1 to 10000`。Slurm 環境不加（它不走這三個函式）。
- **決定二：bundle 裡只在有設時才有 `maxMemoryGB` 這一鍵**（`out["maxMemoryGB"] = v` 只在 `v is not None` 時）。理由：既有測試鎖死 `set(b["ce"])`（`test_aws_launch.py:522`）與 `compute_envs.snapshot` 的欄位集合（`test_aws_ce.py:584`），無條件加鍵會讓它們紅，而那些斷言不准改。`snapshot_ce`（`launch.py:160`）同理：只在環境有設時才把 `maxMemoryGB` 放進去。
- **決定三：合併規則（共用小函式，輸入＝驗證後的 `ce`，輸出＝要寫的那一行或 None）**
  1. 平台沒有任何值要寫（`maxvCpus` 與 `maxMemoryGB` 都沒設）→ 回傳 None、`<平台>.config` 不寫這行、**使用者的 resourceLimits 完全不碰**（維持現狀）。
  2. 平台有值要寫，而使用者的 `nextflowConfig` 沒有 `resourceLimits` → 寫 `process.resourceLimits = [cpus: N, memory: M.GB]`（只含有設的鍵，固定順序 cpus、memory）。
  3. 平台有值要寫，而使用者**有**寫 → 讀他那一行並合併：cpus 與 memory 取**較小**的；使用者設而平台沒設的鍵原樣保留；`disk`、`time` 一律保留他的原文。輸出鍵序固定 cpus、memory、disk、time。
  4. 「讀得懂」的定義（刻意很窄，寧可拒絕也不猜）：沒被 `//` 註解掉的行裡，字 `resourceLimits` 恰好出現一次，且該行整行是 `process.resourceLimits = [ ... ]` 或 `resourceLimits = [ ... ]`（方括號在同一行、不含巢狀方括號）；每一項是 `鍵: 值`，鍵只能是 cpus／memory／disk／time；cpus 值是整數；memory 值是 `N.GB`／`N.MB` 或 `'N GB'`／`'N MB'`（N 為數字，可有小數）；disk、time 的值只准字母數字與 `_ . '` 和空格、至多 40 字。
  5. 讀不懂（出現多次、跨行、`resourceLimits {` 區塊寫法、變數、未知鍵、值不合規則）→ 送出前就 `BundleError`，**不寫任何檔**。訊息要含：哪個環境、發生什麼事、怎麼辦，例如：`環境 aws1 的 nextflowConfig 有 resourceLimits，但平台讀不懂它的寫法，不能安全地和環境的上限合併。請改成單行 process.resourceLimits = [cpus: 4, memory: 6.GB]，或刪掉它、改設環境的 maxvCpus／maxMemoryGB (the platform cannot merge this resourceLimits safely; write it on one line or remove it)`。訊息不得貼出使用者設定檔的全文（只可帶鍵名）。
  6. 合併不改使用者的 `nextflow.config`：他的原文照舊整份寫進去（它本來就被後讀的平台檔蓋過）；只有平台寫的那一行是合併結果。
- **決定四：確認畫面**。`build.py` 三處在 cpus 那列後面加 `("單一 task 的記憶體上限（GB）", ce["maxMemoryGB"])`，只在 `ce.get("maxMemoryGB") is not None` 時出現。合併後的實際那一行本來就會顯示在畫面上的 `<平台>.config` 區塊裡（`terminal.block`），不另加。
- **不變**：寫進檔的值都走 `_gcb_quote`／固定格式 `%d` 與 `%d.GB`；使用者的 disk、time 原文只在過了上面第 4 點的字元限制後才寫入。

## 失敗先行測試
先寫、改程式前跑一次確認紅，紅的輸出貼進 ledger。全部只新增、不改既有。
**環境驗證**（三個 `*_ce.py` 各一條，仿 `test_aws_ce.py:240` 的 `test_spot_and_maxvcpus_rules`）：
- `test_max_memory_gb_rules`：`maxMemoryGB` 為 0、10001、True、"8"、1.5 時 `refused(...)` 的訊息含 `maxMemoryGB must be a whole number from 1 to 10000`（**現在紅**：現在的訊息是 "unknown setting"）；`create(..., good_config(maxMemoryGB=10000))["config"]["maxMemoryGB"] == 10000`（**現在紅**）。
**送出內容**（`test_aws_launch.py` 寫完整矩陣；`test_gcb_launch.py`、`test_azure_launch.py` 各寫下面 1、2、3、5）：
1. 試跑原案：環境 `maxvCpus=4`、`maxMemoryGB=6` → `config_keys(files["aws.config"])["process.resourceLimits"] == "[cpus: 4, memory: 6.GB]"`。**現在紅**。
2. 試跑的真實失敗：環境 `maxvCpus=4`，`nextflowConfig="process.resourceLimits = [cpus: 4, memory: 6.GB]\n"`，沒設 `maxMemoryGB` → 那行必須等於 `[cpus: 4, memory: 6.GB]`（使用者的記憶體鍵保留）。**現在紅**（現在是 `[cpus: 4]`）。
3. 只設 `maxMemoryGB=6`、不設 `maxvCpus` → `[memory: 6.GB]`。**現在紅**。
4. （只在 AWS 檔）合併取較小：使用者 `cpus: 64` 平台 4 → `cpus: 4`；使用者 `cpus: 2` 平台 4 → `cpus: 2`；使用者 `memory: 32.GB` 平台 `maxMemoryGB=6` → `memory: 6.GB`；使用者 `memory: 4.GB` 平台 6 → 保留使用者的 `4.GB`；使用者 `time: 48.h` 平台只設 cpus → 輸出含 `time: 48.h` 且鍵序為 cpus、…、time；使用者寫 `'6 GB'` 與 `6144.MB` 也能比較大小。**現在紅**。
5. 讀不懂就拒絕：使用者 `nextflowConfig` 含 (a) 跨行 `resourceLimits = [` 換行 `cpus: 4` 換行 `]`、(b) 出現兩次、(c) `process { resourceLimits { cpus = 4 } }`、(d) `resourceLimits = [cpus: params.c]`、(e) 未知鍵 `gpus: 1`，且平台有值要寫 → 各自 `BundleError`，訊息含 `resourceLimits` 與修法、**不含**使用者設定檔的其他內容、`box.started == []` 且沒有 run 資料夾。**現在紅**（現在不報錯，悄悄換掉）。
6. 確認畫面：設了 `maxMemoryGB` 時 `build.launch_screen(b, ...)` 的文字含 `單一 task 的記憶體上限`。**現在紅**。
**對照組（必須全程綠）**：
- 沒設任何上限、使用者有 resourceLimits → `<平台>.config` 不含 resourceLimits，`nextflow.config` 含使用者那行原文（維持現狀）。
- 只設 `maxvCpus=16`、使用者沒寫 resourceLimits → 仍是 `[cpus: 16]`（`test_aws_launch.py:520`、`test_gcb_launch.py:573`、`test_azure_launch.py:499` 既有斷言不動）。
- 沒設 `maxMemoryGB` 時 bundle 的 `ce` 鍵集合與 `compute_envs.snapshot` 的欄位集合不變（`test_aws_launch.py:522`、`test_aws_ce.py:584` 既有斷言不動）。
- 畫面上沒設記憶體上限時，不出現 `記憶體上限` 字樣。
- 使用者的 `nextflow.config` 原文逐字不變（有／無 resourceLimits 兩種都比）。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」）：在 `origin/v3` 與本分支各跑 `test_aws_launch.py`、`test_gcb_launch.py`、`test_azure_launch.py`、`test_aws_ce.py`、`test_gcb_ce.py`、`test_azure_ce.py`，貼輸出；本分支除了新增的測試外，與 base 的通過／失敗名單一致。

## 完成標準（done when）
- 上面的失敗先行測試改前紅、改後綠；對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含「範圍」列的檔；沒有既有測試的既有斷言被改弱；兩分支輸出比對貼上；合併函式只有一份（三個 `_*_config` 都呼叫它，沒有三份複製）。
- 手動案例（閱卷看 diff，不必進 TESTING.md）：對試跑原案（環境 `maxvCpus: 4` 加 `nextflowConfig` 含 `memory: 6.GB`）產生 bundle，貼出 `aws.config` 那行。
- 真實 AWS 驗證（新寫法 Nextflow 是否接受、task 是否排得上）**不在本任務**：executor 不得碰真實雲端，留給他之後的雲端試跑（B 級的使用者驗收）。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_aws_launch.py bash tests/platform_test.sh`（相對於 `platform/`）；其餘五個檔同法。
  - 全套：在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束；測試還在背景跑時不准交報告。
- 測試輔助：`test_aws_launch.py` 的 `ace(**over)`（`:41`）、`box.bundle(...)`（`:120`）、`config_keys(text)`（`:183`）；GCB 是 `gce`（`test_gcb_launch.py:38`）、Azure 是 `zce`（`test_azure_launch.py:49`）；環境驗證用 `good_config`／`create`／`refused`（`test_aws_ce.py:47-70`，另兩檔同名）。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- 絕不跑：任何碰真實 AWS／GCP／Azure、站台、HPC 的東西。

## 不做
- 不做「總量」上限（整個佇列的 vCPU／記憶體總和）：Nextflow 的 resourceLimits 是單一 task 的上限，總量屬於環境本身（`docs/PLATFORM.md` 已寫明 `maxvCpus` 不是總量）。
- 不加 `maxDiskGB`、`maxTime`；使用者自己寫的 disk、time 只保留、不取最小。
- 不改 Slurm 環境、不改 `compute_envs.snapshot()`、不改 web 設定頁（網頁目前沒有 `maxvCpus` 欄位，要不要加另開一件）。
- 不解析整份 Groovy／Nextflow 設定（只認上面第 4 點那一種單行寫法，其餘一律拒絕）。
- 不改使用者的 `nextflow.config` 原文；不刪既有環境的任何鍵。
- 不更新 `docs/TESTING.md`。

## 裁決
1. **使用者的 resourceLimits 怎麼辦？**——三條路：(a) 平台值整個取代（現狀，丟掉使用者的鍵，這次試跑就是被它害到）；(b) 使用者的整個贏（平台的 cpus 上限就失效，而那是平台的安全網）；(c) 逐鍵合併。**定案：(c)，同一個鍵取較小的（平台值是天花板，使用者要更低可以、要更高不行），只有使用者設的鍵保留。** 沒有任何使用者設的鍵會被默默丟掉。
2. **讀不懂他寫的怎麼辦？**——猜（容易寫出錯的設定而送上雲端花錢）或拒絕。**定案：拒絕，並告訴他兩個修法（改成單行、或刪掉改設環境鍵）。** 「讀得懂」刻意定得很窄，寧可多拒絕幾種寫法也不猜。
3. **新鍵名**：`maxMemoryGB`，跟 `maxvCpus` 同風格、單位寫在名字裡，值是整數 GB，不收 `"6 GB"` 之類字串（只在使用者自己的 nextflowConfig 裡才讀這種寫法）。
4. **三種雲端一起做**：三處寫法與驗證逐行相同（`launch.py:681`／`:860`／`:1036`），只改一家等於留兩個同樣的洞。

### developer-agent 確認（2026-10-29）
證據已對 origin/v3@d1fa55e 查過：resourceLimits 在 `launch.py` 而不在 `build.py`（`build.py` 只負責確認畫面），`compute_envs.py:410`／`:459` 是 AWS 的元組與 maxvCpus 檢查。B 級，需他驗收（建議在他下一次雲端試跑時一併確認）。

### developer-agent 確認（2026-10-29 12:4x）
- 合併後 `[cpus: N, memory: M.GB]` 在真實 AWS 是否被接受，列入 B 級事後驗收（下次雲端試跑）；本件以單元測試鎖產出的 config 文字。
- 車道名改 `L30-cloud-ce-memory`（與 k8s-ce 是否碰同檔，派工前用 `git diff --stat` 檢查；重疊就排在 k8s-ce 之後）。

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
