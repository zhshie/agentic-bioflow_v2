---
id: launchpad-ce-routing
title: 重用已註冊的 launchpad 管線時，先核對它綁的計算環境，不一致就不准默默沿用（issue #8）
tier: A
kinds: backend
lane: L3-plugin-tw
base: v3（`origin/v3`；程式碼與 main 逐字相同，v3 仍隨附 tw 路徑，v3.0.0 合回 main 時一併到達 v2 用戶。若維護者要現在就修 v2，再把同一份 diff 摘到 main，見「不做」）
source: GitHub zhshie/agentic-bioflow_v2 issue #8；查證日 2026-10-24（origin/main 66fbc94、origin/v3 54900a2）
---

# launchpad-ce-routing

> 本檔由 developer-agent 助手起草（2026-10-24）。**只處理 issue #8**：`scripts/prepare_launch.sh` 的「registered?」檢查只看「這個 repo 與 revision 有沒有登記」，不看它綁哪個計算環境（compute environment, CE）。A 級（把行為拉回規格：launch 步驟 1 本意是「同管線同版本不必重登記」，不是「可以送去任何環境」）。

## 目標
`prepare_launch.sh` 看到已登記的 launchpad 項目時，一併告訴使用者「它綁在哪個 CE」，與本部署設定的 `compute_env` 不同時明確標出並要求決定，**不再靜默放行**；launch 的指令也明講 `--compute-env`。對使用者的意義：在「新的隔離 CE 與正式 CE 並存」的部署裡，不會一個 `tw launch <短名>` 就把 run 送到錯的環境（issue 作者兩次靠手動改成完整 GitHub URL 才避開）。

### 查證結果（動手前的事實）
- **main 上仍會重現**：`origin/main:scripts/prepare_launch.sh:129-137` 只 `grep -qF "$REPO"` 與 `grep -qF "$REVISION"` 就 `REGISTERED="yes, at $REVISION"`，全程沒讀 CE；`origin/main:commands/launch.md:211`（`tw pipelines add`）一帶的步驟 3 寫「同版本……skip the step」，沒提 CE。
- **v3 上同一份程式**：`git diff origin/main origin/v3 -- scripts/prepare_launch.sh` 只差註解裡 `commands/launch.md` → `skills/launch/SKILL.md` 兩處；同一段邏輯在 `origin/v3:scripts/prepare_launch.sh:129-137`。v3 仍隨附 tw 路徑（`origin/v3:skills/launch/SKILL.md:86,212-225`），只在開頭加了「v2 only」分流（`tests/skills_name_the_v3_launch_path.sh`），所以 v3 用戶走 tw 路徑時同樣中。
- **可達性**：步驟 0 把 `== pipeline ==` 的 `registered: yes, at …` 當依據，步驟 3 據此跳過登記，之後 launch 用短名；整條都沒有 CE 的檢查。
- 沒有任何既有的 CE 綁定檢查：`scripts/preflight.sh:135` 只驗「設定的 CE 本身 AVAILABLE」，與「登記項目綁哪個 CE」無關。

## 維護者原話（verifier 出題用）
issue #8 內文逐字（含標題）：

> 標題：launch: reusing a registered launchpad pipeline can silently route to the wrong compute environment
>
> ## What happened
>
> Twice in the same session (nf-core/rnaseq, then nf-core/ampliseq), \`tw pipelines list\` showed an already-registered launchpad entry at the exact revision I wanted (\`nf-core-rnaseq-3140\`, \`nf-core-ampliseq-2180\`) — but each was registered against a **different** compute environment (the lab's original production CE) than the one this deployment was actually meant to use (a newly-built isolated CE, \`agentic-bioflow-v2test\`).
>
> \`launch.md\` step 1 says to prefer an existing registered entry ("re-running the same pipeline at the same revision needs nothing here — skip the step"), which is right for revision-pinning but says nothing about compute-environment binding. Launching via the registered shortname would have silently submitted the run against the *wrong* CE — a real footgun for exactly the "new isolated environment coexisting with production" scenario this deployment is in.
>
> ## Workaround used this session
>
> Both times, launched via the full GitHub URL + explicit \`--revision\` + explicit \`--compute-env\` instead of the registered shortname, to force the correct CE.
>
> ## Suggested fix
>
> When step 1 finds a registered entry at the wanted revision, also show (or check) which compute environment it's bound to, and flag it if it doesn't match the CE this session is currently configured for — rather than only checking the revision match.
>
> ## Environment
>
> - Plugin version 2.14.0, two separate compute environments on one Seqera workspace (production \`nchc-taiwania3\` + isolated \`agentic-bioflow-v2test\`)

（issue 沒有留言。內文裡的反斜線是 GitHub 回傳的原樣。）每句對應的測試：「show which CE it's bound to」→ T2；「flag it if it doesn't match」→ T1、T3、T4；「launched via … explicit --compute-env」→ T5；對照組（綁定相符時不吵、沒有 tw 時行為不變）→ T2、T6。

## 範圍：檔案（只准改這些）
- `scripts/prepare_launch.sh`（`# --- registered? ---` 區段與其後的 `case "$REGISTERED"`；`PIPELINE_BODY` 多一行 `bound to:`）
- `skills/launch/SKILL.md`（步驟 3「Register it…」那段與步驟 7 的 launch 指令說明；這是 v3 的路徑，main 上對應檔是 `commands/launch.md`）
- `tests/prepare_launch_ce_test.sh`（新；`tests/run_all.sh` 會自動收進來）
- `docs/PITFALLS.md`（只在檔尾新增一條，寫症狀、原因、修法）
- `specs/launchpad-ce-routing/ledger.md`（新，executor 進度帳本）

**不准動**：`platform/**`、`deploy/`、`configs/sites/*`、`scripts/nf_relay.py`、`scripts/egress_ctl.sh`、`scripts/on_site.sh`、`scripts/build_package.sh`、`docs/OPERATIONS.md`、`docs/INSTALL.md`、`docs/SETTINGS.md`、`docs/SITE_ADAPTER.md`、`docs/TESTING.md`。`hooks/` 是受保護路徑，**本任務也不需要改它**（只改 script 與 skill 文字；若 executor 發現非改 `hooks/*.sh` 不可，停下回報 BLOCKED，別自行處理）。

## 作法
1. **取得綁定的 CE（prepare_launch.sh）**：現有 `tw pipelines list`（文字）保留，只用來判斷「登記了沒、在哪個版本」，行為不變。登記為 yes 之後，**再多問一次** `"$TW" -o json pipelines list --workspace "$WORKSPACE"`，用 `pick_python` 解析：挑 `repository` 含 `$REPO` 的項目；每個項目的 CE 名取 `computeEnv.name`，沒有就取 `launch.computeEnv.name`；兩處都沒有 → 對該項目的 `name` 呼叫 `"$TW" -o json pipelines view -n <name> --workspace …` 再從同兩個位置（`pipeline.` 底下）取。最多查 5 個項目。
2. **期望的 CE**＝`setting compute_env`（部署設定，與 `preflight.sh:17` 同一個鍵；環境變數 `SEQERA_COMPUTE_ENV` 優先，同 `preflight.sh`）。
3. **輸出**（`== pipeline ==` 多一行，置於 `registered:` 之後）：
   - 相符（至少一個符合 repo 的項目綁在期望 CE）：`bound to: <ce>（matches this deployment's compute_env）`，**不加任何 decision／warning**。
   - 都不符：`bound to: <名稱列表>（this deployment's compute_env is <期望>）`，並 `add_decision "registered entry is bound to <列表>, not <期望> - do NOT launch it by short name; register a new entry with tw pipelines add --compute-env <期望>, or launch the GitHub URL with --compute-env <期望>"`。
   - 查不出（沒有 python、JSON 讀不懂、項目沒有 CE 欄位、`tw` 逾時）：`bound to: unknown`，並 `add_warning "could not tell which compute environment the registered entry is bound to - treat it as NOT matching until checked"`。
   - 期望的 CE 沒設定（`compute_env` 空）：`bound to: <列表>（no compute_env in the deployment settings, nothing to compare）`，加同一條 warning 的變體說明「沒有可比對的設定」。
   - `REGISTERED` 的原字串 `yes, at $REVISION` **不改**。
4. **skill 文字**：步驟 3 改成「只有 `== pipeline ==` 同時寫 `registered: yes` **且** `bound to:` 為 matches 時才跳過登記；否則照 decisions 處理」。步驟 7 的 `tw launch` 說明加一句：一律帶 `--compute-env "$(scripts/settings.sh compute_env)"`，**不靠登記項目預設的 CE**。
5. **PITFALLS**：新增一條，標題含 2026-10-24、issue #8。

## 失敗先行測試（`tests/prepare_launch_ce_test.sh`，現在會紅；全用假的 `tw`，不碰 Seqera）
做法：沿用 `tests/prepare_launch_test.sh` 的搭法（複製真的 `prepare_launch.sh`、`settings.sh`、`utils/*` 到暫存 `scripts/`，假 `preflight.sh`，`--fixture-dir`），設定檔寫 `workspace_id: ws1` 與 `compute_env: agentic-bioflow-v2test`，`TOWER_ACCESS_TOKEN=x`，`TW_BIN` 指向暫存的假 `tw`。假 `tw` 依參數回罐頭輸出：
- 文字 `pipelines list` → 含 `nf-core-rnaseq-3140  https://github.com/nf-core/rnaseq` 與 `3.14.0` 字樣（讓既有的 grep 判成 registered）。
- `-o json pipelines list` → `{"pipelines":[{"name":"nf-core-rnaseq-3140","repository":"https://github.com/nf-core/rnaseq","computeEnv":{"name":"<由測試設定>"}}]}`。
- 變體 V：JSON 項目沒有 `computeEnv`，由 `-o json pipelines view -n nf-core-rnaseq-3140` 回 `{"pipeline":{"launch":{"computeEnv":{"name":"<…>"}}}}`。

案例（`--repo nf-core/rnaseq --revision 3.14.0`，手算期望）：

| # | 登記項目綁的 CE | 設定的 compute_env | 期望輸出 |
|---|---|---|---|
| T1 | `nchc-taiwania3` | `agentic-bioflow-v2test` | 含 `bound to: nchc-taiwania3`；含一條 `DECIDE:` 同時提到 `nchc-taiwania3`、`agentic-bioflow-v2test`、`--compute-env`；`registered:` 仍含 `yes, at 3.14.0` |
| T2 | `agentic-bioflow-v2test` | `agentic-bioflow-v2test` | 含 `bound to: agentic-bioflow-v2test`；含 `bound to` 的 `DECIDE:`／`WARNING:` 計數為 0 |
| T3 | JSON 沒有 computeEnv，`view` 也失敗 | `agentic-bioflow-v2test` | 含 `bound to: unknown`；恰 1 條含 `bound to` 字樣的 `WARNING:` |
| T4 | 變體 V：`view` 回 `nchc-taiwania3` | `agentic-bioflow-v2test` | 同 T1（證明 `view` 備援有用） |
| T5 | 文字檢查 `skills/launch/SKILL.md` | 不適用 | 步驟 3 段含 `bound to`；步驟 7 段含 `--compute-env "$(scripts/settings.sh compute_env)"` |
| T6 | 回歸：`TW_BIN=/does/not/exist` | 不適用 | 與今天一樣：`registered: unknown …`、恰 1 條 `could not check whether the pipeline is already registered` WARNING、不出現任何 `bound to` WARNING（沒有 tw 就沒得比） |

**現在會紅**：T1–T5 在現有程式輸出沒有任何 `bound to` 字樣（T5 在 skill 文字沒有）。T6 現在就綠（鎖住不退步）。executor 先跑一次，貼出紅的輸出再動手。

**會改斷言的既有測試：無。** 已逐一核對：`tests/prepare_launch_test.sh` 所有情境都用 `TW_BIN=/does/not/exist`（`registered: unknown`），不受影響；`yes, at` 這個字串在 `tests/`、`scripts/`、`skills/`、`hooks/` 沒有其他消費者（以 `git grep` 查 origin/v3）。若 executor 發現有既有測試要改斷言，停下回報，不要自己放寬。

## 完成標準（done when）
- 新測試 T1–T6 綠；`tests/prepare_launch_test.sh` 與整個 `tests/run_all.sh`（在 WSL 跑，見 repo CLAUDE.md「For the executor and verifier」）綠。
- 閘門檔：`hooks/` 沒有任何改動（`git diff --stat origin/v3 -- hooks` 為空）；`tests/confirm_launch_test.sh` 在 base 與分支上輸出相同。
- `git diff --name-only` 只含「範圍：檔案」所列；上方不准動清單零命中。
- 沒有任何真的 `tw`／Seqera 呼叫（測試只用假 `tw`）；新測試在沒有網路的環境也綠。
- `.claude-plugin/plugin.json`、`spec.md`、`test-case*.md`、`.github/`、憲法未被編輯（repo CLAUDE.md 禁止項）。

## 環境事實
- 目前**沒有**可核對的真實 `tw pipelines list/view -o json` 輸出樣本：Seqera 文件頁（https://docs.seqera.io/platform-cli/reference/pipelines，2026-10-24 讀）沒列輸出欄位也沒列 `computeEnv`，本機也沒有 `tw`。因此作法 1 對欄位位置用「兩處都試＋`view` 備援＋查不出就警告」，**不可假設欄位一定存在**；T3 就是鎖這個。issue 作者（tw 0.40.0）能貼一份真實輸出時，再收斂成單一路徑。
- 此 repo 的 `tw` 呼叫慣例：一律 `--workspace $(scripts/settings.sh workspace_id)`、機器讀用 `tw -o json …`（如 `scripts/duplicate_run_check.sh:74`）。
- Windows 上 `python3` 可能是 Store 別名，用 `pick_python`（`prepare_launch.sh:178` 的做法），不要寫死 `python3`。
- 全套測試必須在 WSL／Linux 跑；worktree 不可在同步磁碟。

## 不做
- 不改 `platform/**`（v3 的 `abf-platform launch` 路徑不受此 bug 影響，別的任務在動）。
- 不自動改寫、重新登記或刪除使用者的 launchpad 項目；不替使用者選 CE。
- 不改 `preflight.sh` 的 CE 檢查、不改 `hooks/`、不新增設定鍵。
- 不在本任務同步 main：v2 若要現在就拿到修正，由 developer-agent 在 v3 合併後把 `scripts/prepare_launch.sh` 與測試檔原樣摘到 main，文字修改套在 `commands/launch.md`（同樣兩段）。

## 裁決
- **基底＝v3，不是 main**：bug 在兩個分支逐字相同（見查證），v3 仍隨附 tw 路徑，v3.0.0 合回 main 時一併到達；v2 在 2027 前只收 bug 修正，這份正是 bug 修正，所以「摘到 main」是之後可選的一步，不是本任務。
- **只警告並要求決定，不阻擋**：不符時用 `DECIDE:` 而非 `BLOCKING:`，因為使用者可能刻意要用那個 CE；風險在「靜默」，不在「選了」。
- **讀 CE 用 `-o json`，不解析給人看的表格**：欄寬與欄位順序會隨 tw 版本變，倉庫其他腳本也都用 `-o json`。
- 修在 `prepare_launch.sh` 與 skill 文字，不動 `hooks/`：hook 是安全網，這裡是「資訊沒呈現給使用者」的問題，且動 hook 需要在 base 與分支雙跑對照。

## 裁決二（2026-10-24 developer-agent）
1. 不符時用 DECIDE（讓使用者選），不擋。
2. 只修 v3，main 不另挑。
3. tw 輸出形狀照計畫：兩處讀、`view` 備援、讀不到就 WARNING；手動驗收時用真的 tw 0.40 輸出核對，結果記進 ledger。
4. `docs/PITFALLS.md` 只在檔尾新增一條（nano4-ce-fixes 也會加，合併時兩條都留）。車道 L3-plugin-tw。

## 裁決三（2026-10-24 developer-agent，回應 verifier 出題退回；以本段為準）
5. 比對範圍：先挑 repository 符合、且 revision 等於這次要用的 revision 的項目（JSON 有 revision 欄位時）。沒有 revision 欄位時，退回「任一同 repo 項目綁的 CE 不是期望 CE 就列出全部不符項目並出 DECIDE」——寧可多問，不靜默。補多項目案例：同管線兩個版本、CE 不同，要用的版本綁錯 → DECIDE；要用的版本綁對、舊版綁錯 → 相符（有 revision 欄位時）／DECIDE（沒有時）。
6. 手動驗收步驟寫在 ledger 即可，TC-032 判 UNVERIFIED 不擋合併。
7. 沒有 compute_env 設定時的 WARNING 措辭：`WARNING: no compute_env is configured, so the bound compute environment cannot be checked.`
8. 「最多查 5 個項目」＝`view` 備援最多呼叫 5 次。沒有 python、tw 逾時不出 TC。verifier 額外加的 TC-004/007/008/012/015/016/017/024 保留。

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
