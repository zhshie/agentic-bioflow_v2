---
id: cloud-checks-tighten
title: 收緊三處雲端安全檢查（s3 bucket 名稱的 ".."、AWS 環境變數改按前綴擋、一則測試失敗訊息補回檔名）
tier: A
kinds: backend
lane: L18-cloud-checks
branch: test/cloud-checks-tighten
base: origin/v3@e79a555（2026-10-29 量；行號取自此，executor 開工前用 `git show origin/v3:<檔>` 重查，不對以實際內容為準）
source: 2026-10-29 清理掃描（A 級：只讓安全檢查更嚴，合法輸入沒有任何使用者看得到的行為變化）
---

# cloud-checks-tighten

> 本檔由 developer-agent 的 subagent 寫（2026-10-29），只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。三項互不相依，可分三個 commit。

## 目標
讓三處「只該更嚴」的檢查補齊：①`cloud_store._parse` 對 s3 bucket 名稱含 `..` 一律拒絕（與另外三處一致）；②AWS 的環境變數黑名單改成「`AWS_` 開頭全擋」（與 Azure 一致）；③補回 `test_azure_launch.py` 一則斷言失敗訊息裡被吞進註解的檔名。對合法輸入沒有任何可見變化；只有「本來就不該通過」的輸入現在會被擋。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描結果）：「s3 bucket 名稱含 `..` 在 `cloud_store._parse` 沒被擋，另外三處都擋，要一致」；「`AWS_FORBIDDEN_ENV` 只擋固定名單，Azure 是按前綴擋，AWS 也照 Azure 做」；「`test_azure_launch.py` 一則斷言的 `, f.name` 被吞進註解，失敗時沒檔名」。
- A 級的前提：只更嚴、合法輸入行為不變；若發現需要改動合法輸入的行為，停下回報 BLOCKED，不自行決定。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/cloud_store.py`（項目 1）
- `platform/abf_station/launch.py`（項目 2；只改 `_check_aws_ce` 內環境變數那一個 `if`，約 843 行）
- `platform/tests/test_azure_launch.py`（項目 3，一行；加上項目 1、2 不放這裡）
- 項目 1 的新測試：加進既有 `platform/tests/test_aws_upload.py`（緊接 `test_parse_s3_has_the_shape_of_parse_gs`，約 249 行）；若該檔頂端的 "Nothing existing" 註解規則要求新檔，才改開 `platform/tests/test_cloud_store_names.py`（檔頭前 40 行內要有 `# Nothing existing: …` 至少 15 個字）
- 項目 2 的新測試：加進既有 `platform/tests/test_aws_launch.py`（緊接約 636 行的 `for name in (...)` 那個測試之後）
- **不准碰**：`compute_envs.py`、`aws_preflight.py`、`clean.py`、`put_upload.py`、`azure_launch.py`、`docs/*`、其他任何測試的既有斷言。

## 作法
### 項目 1：`cloud_store._parse` 接受 s3 bucket 名稱含 `..`
- **現況**：`platform/abf_platform/cloud_store.py`，`_container_ok(scheme, name)`（約 27–32 行）的最後一行 `return bool(compute_envs._AWS_BUCKET.match(name))`；`_AWS_BUCKET` 是 `^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]\Z`（`compute_envs.py:412`），字元集允許 `.`，所以 `a..b` 可通過。`_parse`（約 35 行起）在約 45 行呼叫 `_container_ok`，`workdir_bucket`（約 98 行）也呼叫同一個函式。
- **另外三處已擋**（都是 `_AWS_BUCKET.match(...)` 加 `".." in bucket`）：`compute_envs.py:444`、`abf_station/aws_preflight.py:52`、`abf_station/launch.py:813`。
- **決定**：只改 `_container_ok` 的 s3 分支，變成 `bool(compute_envs._AWS_BUCKET.match(name)) and ".." not in name`（寫法比照 az 分支的 `and "--" not in name`）。這樣 `parse_s3` 與 `workdir_bucket` 兩條路徑一次補齊。錯誤訊息沿用現有那句（不新增文字）。**不動 `gs` 分支**（見待裁決 1）。

### 項目 2：`AWS_FORBIDDEN_ENV` 改按前綴擋
- **現況**：`platform/abf_station/launch.py:789` 的 `AWS_FORBIDDEN_ENV` 是 8 個固定名稱的 tuple（`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_SESSION_TOKEN`、`AWS_PROFILE`、`AWS_DEFAULT_PROFILE`、`AWS_SHARED_CREDENTIALS_FILE`、`AWS_CONFIG_FILE`、`AWS_DEFAULT_REGION`）；使用處在 `_check_aws_ce` 的環境迴圈（約 843）：`if name in SET_BY_THE_SCRIPT or name in AWS_FORBIDDEN_ENV or name.upper().startswith("ABF_"):`。
- **Azure 的做法（已讀）**：`launch.py:1014–1015`：`name in SET_BY_THE_SCRIPT or name in AZURE_FORBIDDEN_ENV or name.upper().startswith("ABF_") or name.upper().startswith("AZURE_") or name.upper() == "TOWER_ACCESS_TOKEN"`（固定名單保留、另加前綴判斷）。
- **決定**：AWS 那個 `if` 加一個 `or name.upper().startswith("AWS_")`；`AWS_FORBIDDEN_ENV` tuple **保留不刪**（`test_aws_launch.py` 等可能 import 它，且名單可當文件）。拒絕訊息沿用現句。不加 `TOWER_ACCESS_TOKEN`（已在 `SET_BY_THE_SCRIPT`）。
- **已查有無合法用途**（`git grep` origin/v3 的 `platform/tests tests docs specs`）：沒有任何現有測試或程式碼把非黑名單的 `AWS_*` 名稱放進計算環境的 `environment` 清單。命中的只有：`test_aws_launch.py:636`（本來就被擋的 `AWS_SHARED_CREDENTIALS_FILE`、`AWS_ACCESS_KEY_ID`）、`test_station_envs.py:234` 與 `test_station_e2e.py:871`（`AWS_SECRET_ACCESS_KEY`，本來就被擋）、`aws_preflight.py:72` 的 `AWS_CA_BUNDLE`（那是**站台行程自己的環境**，不是計算環境的 `environment` 設定，不受本項影響）。結論：沒有現有路徑被打斷；潛在的合法需求（例如使用者想設 `AWS_MAX_ATTEMPTS`）見待裁決 2。

### 項目 3：`test_azure_launch.py` 吞進註解的 `f.name`
- **現況**：`platform/tests/test_azure_launch.py` 約 1109 行（在 `test_no_azure_command_that_changes_anything`，約 1104 起，迴圈 `for f in (PLATFORM_DIR / folder).rglob("*.py")` 裡）：
  `assert not re.search(r"...", code)      # azure-upload: blob upload and blob show are allowed, f.name`
  末尾的 `, f.name` 在 `#` 後面，被當成註解。（行號是 1109，不是派工單寫的約 1118；以內容為準。）
- **決定**：改成 `assert not re.search(r"...", code), f.name      # azure-upload: blob upload and blob show are allowed`。正規式與其他部分一字不改。

## 失敗先行測試
先寫、在改程式前跑一次，確認紅，紅的輸出貼進 ledger。
### 項目 1（加在 `test_aws_upload.py` 或新檔）
- `test_parse_s3_refuses_a_double_dot_in_the_bucket`：
  - `cs().parse_s3("s3://lab..bucket/uploads/a.fq.gz")` → 拋 `CloudPathError`（現在回 `("lab..bucket", "uploads/a.fq.gz")`，所以紅）。
  - `parse_s3("s3://a..b/x")`、`parse_s3("s3://lab-bucket..x/x")` 同樣拋 `CloudPathError`。
  - 對照組（必須維持綠）：`parse_s3("s3://lab.bucket/uploads/a.fq.gz")` → `("lab.bucket", "uploads/a.fq.gz")`；`parse_s3("s3://lab-bucket/uploads/a.fq.gz")` → `("lab-bucket", "uploads/a.fq.gz")`。
- `test_workdir_bucket_refuses_a_double_dot_in_an_s3_workdir`：`cs().workdir_bucket({"platform": <AWS 常數>, "config": {"workDir": "s3://lab..bucket/work"}})` → 拋 `CloudPathError`；`s3://lab.bucket/work` → 回 `"lab.bucket"`（組環境字典的寫法照同檔既有測試）。
- 另跑：`parse_gs("s3://...")` 與 `parse_az` 既有測試不改、保持綠（證明沒動到 gs、az 分支）。

### 項目 2（加在 `test_aws_launch.py`，仿約 636 行）
- `test_every_aws_prefixed_environment_name_is_refused`：對下列名稱各用 `box.bundle(ce=ace(environment=[{"name": name, "value": "v", "head": True, "compute": False}]))`，每個都 `pytest.raises(launch.BundleError)`：
  `AWS_MAX_ATTEMPTS`、`AWS_RETRY_MODE`、`AWS_CA_BUNDLE`、`AWS_REGION`、`aws_profile`（小寫）、`Aws_Whatever`、`AWS_`（只有前綴）。除 `AWS_REGION` 等本來就不在名單者外，上述至少 `AWS_MAX_ATTEMPTS`、`AWS_RETRY_MODE`、`AWS_CA_BUNDLE`、`aws_profile` 現在會通過所以是紅的。
- 對照組（必須維持綠）：`HEAD_ONLY`、`MY_AWS_NOTE`（名稱含 AWS 但不以 `AWS_` 開頭）、`AWSX`（無底線）→ 不拋；既有 `test_head_environment_variables_are_exported_and_compute_ones_are_not` 不改、保持綠。
- `test_aws_forbidden_env_tuple_is_still_refused_by_name`：`launch.AWS_FORBIDDEN_ENV` 裡每個名稱仍被拒（證明 tuple 保留且行為未退步）。

### 項目 3
- 這是測試檔本身的改動，沒有「先紅」可言；驗證方式：①`git diff` 只動那一行，且 `, f.name` 在 `assert` 運算式內、`#` 之前；②手動演練（在 scratch 副本，不進 commit）：把該 `re.search` 暫時換成一定命中的字串，確認失敗訊息含檔名，記進 ledger。

## 完成標準（done when）
- 項目 1、2 的新測試改前紅、改後綠；對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅：見 dev-plans README「通例：已知環境紅」，只剩那一條視同綠）。
- 手動差異檢查記在 ledger：`git diff --stat` 只含「範圍」列的檔案；`cloud_store.py` 與 `launch.py` 各只有一行邏輯改動；`test_azure_launch.py` 只有一行；沒有既有測試被改弱。
- 單檔測試命令與全套命令見「環境事實」。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單一測試檔：`bash tests/<name>.sh`（多數在 Git Bash 可跑）。pytest 型的單檔用 `tests/platform_test.sh`，以 `ABF_PYTEST_TARGETS`（相對於 `platform/` 的 pytest 目標，預設 `tests`）限縮，例如 `ABF_PYTEST_TARGETS=tests/test_aws_launch.py bash tests/platform_test.sh`；`ABF_PYTEST_ARGS` 可加 `-k <名稱>`。
  - 全套：`tests/run_all.sh` 不接受原生 Git Bash，要在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII（例如 `$HOME`）：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。repo 與 worktree 必須在本機磁碟、不在同步雲碟；同一個 checkout 不可同時跑兩次。
- **全套測試會超過單次指令 10 分鐘上限**（這台機器上 platform 分片約 6 分鐘，全套更久）：跑全套（`tests/run_all.sh --timeout 900`）時一律用 Bash 的 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 這類迴圈（每次 ≤ 9 分鐘）等它結束，讀完結果才結束回合；不准在測試還在背景跑時就交報告。（措辭取自 web-upload-page.md 裁決 23。）
- 規則文件：`.specify/memory/constitution.md`。不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- 站台程式碼不得出現小寫單字 `azure`（`test_station_static.py:46`）；`launch.py` 本次改動不新增這個字。
- 讀碼一律 `git -C <repo> show origin/v3:<path>`；實作在 worktree 的 `test/cloud-checks-tighten` 分支，base 為 `origin/v3`。

## 不做
- 不動 `gs` 的 bucket 檢查、不動 `compute_envs.py`／`aws_preflight.py` 那兩處已有的 `..` 檢查。
- 不刪 `AWS_FORBIDDEN_ENV` tuple、不改它的內容、不改 Azure 的 tuple 與邏輯。
- 不新增使用者可見的錯誤訊息文字、不改文件、不新增 migration（資料結構與資料內容都沒變，不需要 migration）。
- 不處理 `aws_preflight.py:72` 對 `AWS_CA_BUNDLE` 的放行（那是站台行程環境，另一個議題）。

## 待裁決
1. **`gs` 分支要不要同樣擋 `..`？** 現況：`cloud_store._BUCKET` 與 `compute_envs._GCB_BUCKET` 都允許 `.` 且**沒有**任何一處擋 `..`（GCS 官方 bucket 命名規則本來就不允許連續的點，但這份計畫沒讀官方頁驗證，不當事實）。派工只點名 s3，建議**本次不動 gs**（A 級範圍：不擴大）；若要一致化，另開一件，一次改 `cloud_store._BUCKET` 路徑與 `_GCB_BUCKET` 兩處以上。
2. **`AWS_` 全擋會不會擋掉有人想要的設定（如 `AWS_MAX_ATTEMPTS`、`AWS_RETRY_MODE`）？** 掃過 origin/v3 的測試、文件、spec，沒有任何人這樣用（所以不是「現有路徑打斷」）。建議**照派工全擋**，與 Azure 的 `AZURE_` 前綴同樣處理（認證與區域由站台代理設定，使用者不該在環境清單裡覆蓋）。若維護者之後需要某個 `AWS_*`，再開白名單，不要在這件順手加。
3. **新測試放既有檔還是新檔？** 建議放既有的 `test_aws_upload.py`（項目 1）與 `test_aws_launch.py`（項目 2），因為這兩檔已有同類測試（約 249、636 行）、也已有 fixture。若 executor 發現放進去會撞上該檔的「Nothing existing」或檔案層級掃描測試，才改開新檔並在 ledger 記一行。
4. **項目 3 的行號**：派工單寫約 1118，v3 e79a555 上實際是 1109。已按內容確認是同一行（唯一一行 `, f.name` 在 `#` 後面）；請 executor 按內容定位。

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
