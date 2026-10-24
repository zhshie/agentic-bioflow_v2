---
id: launch-reader-dies
title: 送出 tw launch 前，當下重驗一次「輸出讀取 agent（Tower Agent）還活著」，死了就別送（issue #7）
tier: A
kinds: backend
lane: L3-plugin-tw
base: v3（`origin/v3`；tw 路徑與 main 逐字相同，v3.0.0 合回 main 時一併到達 v2 用戶。若維護者要現在就修 v2，再把同一份 diff 摘到 main，見「不做」）
source: GitHub zhshie/agentic-bioflow_v2 issue #7（無留言）；查證日 2026-10-24（origin/main 66fbc94、origin/v3 a7b9b48）
---

# launch-reader-dies

> 本檔由 developer-agent 助手起草（2026-10-24）。**只處理 issue #7**。A 級：把行為拉回規格——launch 技能自己宣稱「送出前確認環境可承載」，但實際上只在最前面驗一次，後面隔了任意長的人類對話才送，沒有當下重驗。

## 目標
`tw launch` 之前（使用者已說「確認執行」、指令即將送出的那一刻），技能先跑一支快速檢查，確認出口通道（egress relay）與輸出讀取 agent 此刻仍活著；死了就**不送**，回報並照既有流程（需使用者同意的重啟）復原後再送。對使用者的意義：不會花二十分鐘走完參數導覽、才在送出時撞上 `No Tower Agent is online…`，再多繞一整圈。

### 查證結果（動手前的事實）
- **仍會重現（v3 與 main 皆然）**：`origin/v3:skills/launch/SKILL.md:436` 步驟 7 與 `:526` 步驟 8 都沒有任何 agent 存活檢查；agent 只在步驟 0 由 `prepare_launch.sh` 內嵌的 `preflight.sh`（`origin/v3:scripts/preflight.sh:116-118`）驗一次。步驟 0 到步驟 8 之間夾著步驟 5 的逐組參數導覽（人在迴圈，時間無上限）。main 對應檔是 `commands/launch.md`，邏輯相同。
- **既有的閘門救不到最需要它的部署**：`SKILL.md:60` 宣稱「launch gate 會重驗會死的兩件事」，實作在 `origin/v3:hooks/confirm_launch.sh:970`（`agent_ctl.sh status`）。但同檔 `:962-963` 在 `reach` 是 `ssh` 或 `none` 時**刻意不查**（理由：經 ssh 查要 31 秒，超過 hook 的 10 秒上限，逾時的 hook 會放行且不出聲）。國網 Taiwania 是 `reach=ssh`，所以正是 issue 作者的部署，閘門整段靜默。另外 `LAB_RUNS_DIR` 在 ssh 部署的使用者 shell 裡本來就不設。
- **不是 Claude Code／runtime 的行為**：agent 是登入節點上的 `nohup java -jar` 常駐程式（`origin/v3:scripts/agent_ctl.sh`，`start` 段），「死」的是我們管的那個行程；沒有重驗是技能文字的缺口。**為什麼 agent 會死不在本任務範圍**（issue 也沒查，只說「悄悄死掉」）；本任務修的是「死了要在送出前就知道」。
- **ADR 的註記要先對齊**：`origin/v3:docs/adr/0006-four-entries-one-action-layer.md:165` 寫「Issues #7 and #8 (launch through `tw`) are closed at v3.0.0 as 'not fixed in v2'」。但 #8 已照同樣方式在 v3 上修了（`origin/v3:tests/prepare_launch_ce_test.sh` 存在），所以本任務沿用 #8 的做法；是否仍要在 v3.0.0 關單時改寫那句，見「待 developer-agent 裁決」。
- 沒有開著的分支碰這個問題：對所有 `fix/*`、`feat/*` 遠端分支比對 `skills/launch`、`prepare_launch`、`agent_ctl`，無命中。

## 維護者原話（verifier 出題用）
issue #7 內文逐字（含標題）：

> 標題：launch: outputs-reader agent can die between preflight and the actual tw launch call
>
> ## What happened
>
> Followed \`launch.md\` faithfully: ran \`preflight.sh\` (agent reported OK), then spent real conversation time walking through project/pipeline/samplesheet/params-route③ (the full per-group parameter walkthrough) before finally calling \`tw launch\`. That call failed:
>
> \`\`\`
> ERROR: No Tower Agent is online for the selected compute environment. Check that Tower Agent is running at your cluster.
> \`\`\`
>
> Checked directly: \`scripts/agent_ctl.sh status\` → \`not running\`. The agent had died sometime between the earlier \`preflight.sh\` pass and the actual launch call, which in this case was a good 20+ minutes later (real conversation time spent on the route③ parameter walkthrough the skill itself asks for).
>
> ## Why this matters
>
> \`preflight.sh\` is explicitly the "before anything" gate — but for a pipeline like ampliseq where step 5 (parameter walkthrough) can legitimately take a long time with a human in the loop, there can be a large gap between preflight passing and the actual submit. This is exactly the kind of staleness the reports.tsv race condition already demonstrates this deployment is prone to (agent process dying quietly, no alert).
>
> Restarting it (\`scripts/on_site.sh --script scripts/agent_ctl.sh start\`) and re-running \`tw launch\` fixed it immediately — so this isn't a hard blocker, just a wasted round-trip that a just-in-time check would have caught before the submit rather than after.
>
> ## Suggested fix
>
> In \`launch.md\` step 7 (right before showing/running the actual \`tw launch\` command), add a fast re-check of agent liveness — the same \`agent_ctl.sh status\` (or \`online <run-id>\`-style check \`downstream.md\` already uses) — rather than relying solely on the earlier \`preflight.sh\` pass, especially when step 5's parameter walkthrough can take arbitrarily long.
>
> ## Environment
>
> - Plugin version 2.14.0, nf-core/ampliseq 2.18.0 launch

（反斜線是 GitHub 回傳的原樣。）每句對應的測試：「just-in-time check … the same `agent_ctl.sh status`」→ T1、T2、T6；「died sometime between the earlier preflight pass and the actual launch call」→ T6（同一份環境，兩次呼叫之間 agent 倒了）；「Restarting it … fixed it immediately」→ T7（技能文字給出復原路徑）；「right before … the actual `tw launch` command」→ T7；「relying solely on the earlier preflight pass」→ T8（技能不再宣稱閘門已涵蓋）；對照組（沒有站台要查時不吵）→ T4、T5。

## 範圍：檔案（只准改這些）
- `scripts/launch_recheck.sh`（新；只讀、不改任何東西，不啟動任何行程）
- `skills/launch/SKILL.md`（第 60-63 行那段「launch gate re-checks…」的措辭；步驟 7 末尾加一句預告；步驟 8 開頭加重驗與失敗分支）
- `tests/launch_recheck_test.sh`（新；`tests/run_all.sh` 會自動收進來）
- `docs/PITFALLS.md`（只在檔尾新增一條：症狀、原因、修法、為什麼閘門在 ssh 部署看不到）
- `specs/launch-reader-dies/ledger.md`（新，executor 進度帳本）

**不准動**：`platform/**`、`deploy/`、`configs/sites/*`、`scripts/nf_relay.py`、`scripts/egress_ctl.sh`、`scripts/on_site.sh`、`scripts/build_package.sh`、`hooks/`、`docs/OPERATIONS.md`、`docs/INSTALL.md`、`docs/SETTINGS.md`、`docs/SITE_ADAPTER.md`、`docs/TESTING.md`。`scripts/agent_ctl.sh`、`scripts/preflight.sh`、`scripts/prepare_launch.sh` 也**不改**（新腳本只呼叫它們既有的 `status` 介面）。若 executor 發現非改以上任何一個不可，停下回報 BLOCKED。

## 作法
1. **新腳本 `scripts/launch_recheck.sh`**：一次快速重驗「此刻站台上兩個會死的常駐程式」。沿用 `preflight.sh` 的做法與輸出格式（`OK|FAIL|SKIP <名稱> <說明>`，欄寬同 `printf "%-10s %-14s %s\n"`），不重寫判斷邏輯，只重用它已用的呼叫：
   - 讀 `REACH="$(setting reach local)"`（`. "$HERE/settings.sh"`，同 `preflight.sh:11-14`）。
   - `none`：印 `OK reach none - Platform manages this site; no relay or outputs reader to re-check`，exit 0，**不**印 egress／agent 行。
   - `local`：直接問站台；`ssh`：先 `bash "$HERE/on_site.sh" --check-reach`，失敗則印 `FAIL reach …master connection … is down` 並把 `on_site.sh` 的輸出（含使用者要貼的那行）原樣印出，exit 1，**不**往下問（否則會卡在 Claude 答不了的一次性密碼提示，見 `preflight.sh` 的同段註解）。
   - 站台可達時，依序 `bash "$HERE/on_site.sh" --script "$HERE/egress_ctl.sh" status`、`… agent_ctl.sh status`，成功印 `OK egress|agent <輸出>`，失敗印 `FAIL egress|agent <原因>（<修復指令>）`；修復指令用與 `preflight.sh:38` 相同的 `fix()` 寫法（ssh 時帶 `scripts/on_site.sh --script` 前綴）。`egress_ctl.sh status` 輸出含 `WARNING` 時，另印 `FAIL egress-host …`，同 `preflight.sh:113`。
   - **不查**資源契約、`rsync`、計算環境狀態、token（那些是步驟 0 的事，且慢）。腳本**不得讀 token 檔**（`tests/credentials_stay_in_settings_test.sh` 掃描 `scripts/*.sh`）。
   - exit 0＝全部 OK；exit 1＝任一 FAIL。每次呼叫都重新問站台，**不快取**。
   - 總時限：每個 `on_site.sh` 呼叫沿用它自己的逾時，腳本本身不加 `sleep`、不重試。
2. **技能步驟 8（Launch）**：在原有第一句「**Launch**, then report…」之前插入一段：「使用者說 確認執行 之後、呼叫 `tw launch` 的**同一個 Bash 回合之前**，先跑 `. scripts/env.sh && scripts/launch_recheck.sh`。任一 `FAIL`：**不要送**；把那行原文給使用者看，說明這是步驟 0 之後才倒的，列出修復指令（agent 用 `scripts/on_site.sh --script scripts/agent_ctl.sh start`，閘門會要使用者同意；**不得自行以 `--set agent_connection` 之類改身分**），修好後重跑本檢查，全 OK 才送出**同一條**已確認的指令（指令沒變，不必重新確認）。」
3. **技能步驟 7 末尾**加一句：「送出前會再驗一次站台（步驟 8），因為從步驟 0 到現在可能隔了很久。」讓使用者知道為什麼等一下會多一行輸出。
4. **技能第 60-63 行**那段改寫成事實：閘門的重驗只在 `reach=local` 或有設 `LAB_RUNS_DIR` 的 shell 生效，`ssh`／`none` 部署刻意靜默（hook 有 10 秒上限）；所以送出前的重驗是步驟 8 的 `launch_recheck.sh`，不是閘門。其餘原句（步驟 0 較寬、也查資源契約與計算環境）保留。
5. **PITFALLS 新增一條**，標題含 2026-10-24、issue #7，寫：症狀（送出才撞 `No Tower Agent is online`）、原因（preflight 只在最前面驗一次；閘門在 ssh 部署靜默）、修法（步驟 8 的 `launch_recheck.sh`）、以及「agent 為什麼會死」尚未查明。

## 失敗先行測試（`tests/launch_recheck_test.sh`，現在會紅；不碰 Seqera、不連線）
做法：沿用 `tests/preflight_reach_test.sh` 的搭法（`mktemp -d`、`LAB_SETTINGS_FILE`、`ON_SITE_SSH_BIN` 指向假 ssh）。因為腳本用 `$HERE` 相對呼叫兄弟腳本，測試把整個 `scripts/` 複製到暫存夾，再用**假的** `agent_ctl.sh` 與 `egress_ctl.sh` 覆蓋：假 agent 在 `$TMP/agent.up` 存在時印 `running pid=1 connection=c on h since t` 並 exit 0，否則印 `not running` 並 exit 1；假 egress 同理看 `$TMP/egress.up`，且存在時印 `up`。設定檔寫 `reach: local`（除非案例另有說明）與 `storage_root: /work/runs`、`workspace_id: 1`、`compute_env: ce`。`TW_BIN` 指向一支會 `exit 99` 的假 `tw`，用來證明腳本從不呼叫 `tw`。

| # | 情境 | 期望（手算） |
|---|---|---|
| T1 | `reach: local`，`agent.up` 不存在、`egress.up` 存在 | exit 1；有一行 `^FAIL +agent`，該行含 `agent_ctl.sh` 與 `start`；有一行 `^OK +egress` |
| T2 | `reach: local`，兩個旗標檔都存在 | exit 0；有 `^OK +agent`、`^OK +egress`；沒有任何 `^FAIL` |
| T3 | `reach: ssh`、`site_host: me@example.org`，假 ssh `exit 255` | exit 1；有 `^FAIL +reach` 與 `me@example.org`；輸出中**沒有** `agent`、`egress` 行（不往下問） |
| T4 | `reach: none` | exit 0；有 `^OK +reach .*none`；沒有 `agent`、`egress` 行 |
| T5 | `reach: local`，`egress.up` 不存在、`agent.up` 存在 | exit 1；有 `^FAIL +egress` 與 `^OK +agent`（兩個獨立判斷，不是第一個壞就都不報） |
| T6 | 重現 issue：`reach: local`，兩旗標先在；跑第一次 → 刪掉 `agent.up` → 跑第二次 | 第一次 exit 0；第二次 exit 1 且有 `^FAIL +agent`（同一份設定、兩次呼叫之間 agent 倒了；腳本沒有快取） |
| T7 | 文字檢查：取 `skills/launch/SKILL.md` 從 `8. **Launch**` 到 `9. **Watch` 之間 | 含 `scripts/launch_recheck.sh`；含 `agent_ctl.sh start`；含 `FAIL`；`launch_recheck.sh` 第一次出現的位置在該段第一個 `tw launch` 字樣之前（若該段沒有 `tw launch` 字樣，改為在「report the run ID」之前） |
| T8 | 文字檢查：`skills/launch/SKILL.md` 前 70 行 | 不再含舊句子 `re-checks the two things that can die while you work` 單獨成立（即：該句後 400 字元內必須出現 `reach`）；且全檔含 `launch_recheck.sh` 至少 2 次（步驟 7 預告＋步驟 8） |
| T9 | `tw` 不得被呼叫 | 案例 T1-T6 的整個過程中，假 `tw` 的記錄檔（假 tw 每被呼叫就 `echo x >> $TMP/tw.called`）不存在 |

**現在會紅的原因**：`scripts/launch_recheck.sh` 不存在，T1-T6、T9 全部失敗（找不到腳本）；T7、T8 因技能文字沒有 `launch_recheck.sh` 而失敗。executor 先跑一次，貼出紅的輸出再動手。

**會改斷言的既有測試：無。** 已逐一核對 `origin/v3` 的 `tests/` 與 `platform/tests/`：沒有任何測試引用 `re-checks the two things` 或步驟 8 的文字；`tests/launch_provenance_test.sh`、`tests/prepare_launch_ce_test.sh`（對 `skills/launch/SKILL.md` 取步驟 3、步驟 7 的區段）只讀步驟 3 與步驟 7 的特定段落——步驟 7 末尾加一句不應影響，executor 要實跑確認；若有既有測試要改斷言，停下回報，不要自己放寬。掃描型測試（`tests/credentials_stay_in_settings_test.sh`、`tests/no_second_run_state_test.sh`）會讀新腳本：新腳本無 `nohup`、不讀 token，應直接過。

## 完成標準（done when）
- 新測試 T1–T9 綠；`tests/prepare_launch_test.sh`、`tests/prepare_launch_ce_test.sh`、`tests/launch_provenance_test.sh`、`tests/credentials_stay_in_settings_test.sh`、`tests/no_second_run_state_test.sh` 與整個 `tests/run_all.sh`（在 WSL 跑，見 repo CLAUDE.md「For the executor and verifier」）綠。
- `hooks/` 無任何改動（`git diff --stat origin/v3 -- hooks` 為空）；`tests/confirm_launch_test.sh` 在 base 與分支輸出相同。
- `git diff --name-only` 只含「範圍：檔案」所列；「不准動」清單零命中；`scripts/agent_ctl.sh`、`preflight.sh`、`prepare_launch.sh` 零改動。
- 沒有任何真的 `tw`／Seqera／ssh 呼叫（測試只用假 ssh 與假 `tw`）；新測試在沒有網路時也綠。
- `.claude-plugin/plugin.json`、`spec.md`、`test-case*.md`、`.github/`、憲法未被編輯（repo CLAUDE.md 禁止項）。
- 手動驗收（記進 ledger，不擋合併）：在真的 ssh 部署上，`scripts/agent_ctl.sh stop` 後跑 `scripts/launch_recheck.sh`，應 exit 1 並印 `FAIL agent` 與重啟指令；`start` 後再跑應 exit 0。

## 環境事實
- 這個 bug 只在有站台要查的部署出現：`reach` 是 `ssh` 或 `local`；`reach=none`（Platform 自管的雲端環境）沒有 agent 可言（`origin/v3:scripts/preflight.sh:93-110` 的註解）。
- `agent_ctl.sh status` 只看本機行程與 pid 檔（`origin/v3:scripts/agent_ctl.sh` 的 `alive()`），**不等於** Platform 認為它在線（該檔 `online` 子命令才問 Platform，且需要 run id，送出前還沒有 run）。issue 作者的案例是行程真的死了（`status` 回 `not running`），所以 `status` 足以涵蓋 issue；「行程活著但連線斷了」不在本任務範圍，見「不做」。
- 此 repo 對站台的呼叫慣例：一律經 `scripts/on_site.sh --script <path> <args>`，`--check-reach` 先驗主連線；測試縫是 `ON_SITE_SSH_BIN`、`LAB_SETTINGS_FILE`（見 `tests/preflight_reach_test.sh`）。
- 全套測試必須在 WSL／Linux 跑（原生 Windows Git Bash 會有已知的 MSYS 缺口，`tests/run_all.sh` 開頭註解）；worktree 不可在同步磁碟。

## 不做
- 不改 `hooks/confirm_launch.sh`（另一個任務正在改它；閘門在 ssh 部署靜默是**刻意**的，見查證）。是否要讓閘門讀一份「最近一次檢查結果」的快取檔來補洞，見「待 developer-agent 裁決」。
- 不自動重啟 agent、不自動重送：啟動常駐程式要使用者同意（`origin/v3:hooks/confirm_launch.sh:405` 的閘門），技能只負責停手與回報。
- 不查「agent 活著但 Platform 看不到它」（需要 run id 或另一個 API 呼叫；`agent_ctl.sh online` 的介面不在本任務改）。
- 不調查 agent 為什麼會死、不加看門狗或自動拉起（會新增常駐行為；若要做是另一張單）。
- 不改 `preflight.sh`／`prepare_launch.sh` 的行為，不新增設定鍵。
- 不同步到 main：v2 若要現在就拿到修正，由 developer-agent 在 v3 合併後把 `scripts/launch_recheck.sh` 與測試原樣摘到 main，文字修改套在 `commands/launch.md` 的對應兩處。

## 待 developer-agent 裁決
1. **`hooks/confirm_launch.sh`**（受保護；目前另一個任務在改，故本任務不碰）：`:962-963` 讓 `ssh`／`none` 部署完全不查 agent。可選補強：讓 `launch_recheck.sh` 在成功時寫一個帶時間戳的檔，閘門在 ssh 部署只讀這個檔（本機讀檔毫秒級，不踩 10 秒上限）並在檔缺失或超過 N 分鐘時加一條 precondition 警告。這會改 hook、需在 base 與分支雙跑 `confirm_launch_test.sh` 對照，建議等另一個任務合併後再開單。本任務的補丁不依賴它。
2. **ADR 0006 `:165`**（「#7 and #8 … closed at v3.0.0 as 'not fixed in v2'」）：#8 已在 v3 修了，#7 也將修在 v3。v3.0.0 合併時是否改寫這句？（docs/adr 不在本任務範圍。）
3. 要不要把 `launch_recheck.sh` 也併進 `skills/runs/SKILL.md` 的 relaunch 路徑？本任務假設不要（relaunch 走 `relaunch_with_override.sh`，不在 issue 內）。

## 裁決
- **基底＝v3，不是 main**：理由同 #8——bug 在兩個分支逐字相同，v3 仍隨附 tw 路徑，v3.0.0 合回 main 時一併到達。
- **新腳本，不改 `preflight.sh`**：`preflight.sh` 是循序、整體 exit 的長腳本，加一個「只做兩項」的旗標要在多處加保護，風險大於收益；新腳本重用同樣的 `on_site.sh … status` 呼叫與同樣的輸出格式，行為對得上就好。代價是兩處各有一份「怎麼問站台」的呼叫，T2/T1 的輸出格式測試鎖住它們不漂移。
- **只停手並回報，不自動重啟**：重啟常駐程式本來就是閘門要使用者同意的動作；風險在「送出才發現」，不在「要不要重啟」。
- **放在步驟 8（使用者確認之後、送出之前），不是步驟 7**：issue 建議放步驟 7，但步驟 7 之後還要等使用者回「確認執行」，那段時間同樣會讓檢查過期；放在最貼近 `tw launch` 的位置才是「當下」。步驟 7 只加預告。
- **重驗後沿用原確認**：指令沒變，使用者同意的是這條指令，不是環境快照；不重問。

## 裁決二（2026-10-24 developer-agent）
1. hooks 不動；閘門讀時間戳檔另案（等 relay-env-warning 合併後再評估）。
2. ADR 0006 那句在 v3.0.0 發版時一起改，本任務不動。
3. 不涵蓋 relaunch_with_override.sh、不追 agent 為何死。
4. PITFALLS 只在檔尾新增一條，用當下最後編號＋1。

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
