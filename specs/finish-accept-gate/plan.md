---
id: finish-accept-gate
title: finish 的 build_package.sh 遇到沒被使用者接受的 analysis.md 條目就拒絕建包（issue #12）
tier: B
kinds: backend
lane: L3-scripts-finish
base: v3（讀的是 origin/v3 @ 54900a2；開分支前先 `git fetch` 確認 build_package.sh 沒被別的任務動過）
source: GitHub issue zhshie/agentic-bioflow_v2#12（狀態 OPEN、無留言）；使用者要求「只讓安全網更嚴」的修補，所以 A 級
---

# finish-accept-gate

> 本檔由 developer-agent 起草（2026-10-24）。**只處理 issue #12 的第一個建議（硬性關卡）**。第二個建議（成功訊息要區分「已組裝」與「可交付」，印出還有幾個 Results 空位）**不在本任務**，見「不做」。
> **A 級**：只讓既有的安全網更嚴，沒有新能力；verifier 通過＋CI 綠由 developer-agent 自合。
> **確認過現在還會重現**（2026-10-24，讀 `origin/v3`）：`scripts/build_package.sh` 的 `FIELDS` 雖然列了 `status`（第 211 行），整支檔案裡沒有任何一行讀 `row["status"]`；`parse_table` 與 `parse_kv_blocks`（後者連 `status` 都不抽）都只取 `id`／`question`。所以 `status: proposed` 的 analysis.md 照樣建出 `manuscript.qmd`、印 `wrote     submission/manuscript.qmd`、退出碼 0。`tests/build_package_test.sh` 的所有夾具都寫 `status: accepted`，沒有任何一條測試涵蓋「沒被接受」。另外 `skills/downstream/SKILL.md` 第 178 行定義了四種值 `proposed | accepted | revised | done`，第 288 行說使用者「定案」時才改 `status`，這就是關卡該認的唯一訊號。
> **這台筆電實跑的限制**：把 `origin/v3` 的 `scripts/` 解到暫存區、用 `status: proposed` 的夾具跑 `build_package.sh`，這台的 Git Bash 只有 Windows Store 的 python 假檔（`python3 is unusable here: exit 49`），腳本在 `pick_python` 就停了，看不到「照建」的實況。上面的結論來自讀碼（grep `status` 只有第 211 行與第 275 行的說明文字）。**executor 必須在 WSL／Linux 跑測試**（repo 的 `tests/run_all.sh` 本來就要求），失敗先行那一步要實際看到「現在紅」。

## 目標
`build_package.sh` 只在 `analysis.md` 的**每一條**條目都是使用者接受過的（`status: accepted` 或 `done`）時才建包；只要有一條是 `proposed`、`revised`、空白、沒寫、或看不懂的值，就**在寫出任何檔案之前**拒絕，退出碼 2，並說出是哪幾條、各是什麼狀態、該怎麼辦。

為什麼這樣做：
1. issue #12 的現場：代理看到使用者從追問圖跳到 `/finish`，就把「換指令」當成「接受」，`build_package.sh` 也沒擋，交出一個外表像核准過、其實從沒被核准的包。`launch` 的 `hooks/confirm_walkthrough.sh` 已經對同型的洞做過硬關卡，`finish` 沒有。
2. 關卡看的是檔案裡的 `status`（人答了才被填的紀錄），不是代理的記憶或心情。
3. 拒絕要發生在 `mkdir submission/`、`provenance.json`、`methods.md` 之前：否則「拒絕」之後還留下一個半成品資料夾，看起來像建過了。

## 維護者原話（verifier 出題用）
以下是 issue #12 的本文，**逐字**（英文原樣，不翻譯；每個編號段落至少對應一條測試）：

> ## What happened (self-observed agent failure, not a crash)
>
> Across a `finish` run this session, I (the agent driving this plugin) made two related mistakes that a stricter gate would have caught mechanically instead of relying on my own discipline:
>
> 1. **Mistook a scaffold for a finished document.** `build_package.sh` printed `wrote submission/manuscript.qmd` after assembling the package — but the Results section it wrote was only placeholders (`<!-- Describe what this shows, from the data. ... -->` per accepted entry). `finish.md` step 4 explicitly says writing the actual Results prose is a manual step the agent must still do — but nothing in the tool's own output distinguishes "assembled, ready" from "assembled, still has N unfilled placeholder(s)." I treated the first successful `build_package.sh` run as if the deliverable were complete and handed it to the user before writing any of the actual prose.
>
> 2. **Treated "user moved on to the next command" as "user accepted the prior analysis."** `finish.md`'s own opening line says it "picks up where `downstream` leaves off — after figures exist and the user has accepted them, not before." In this session, the user asked a couple of follow-up questions about one figure and then directly typed `/finish` — without ever saying an explicit "accept" for any of the four analysis entries. I proceeded anyway, inferring acceptance from the command switch rather than from an explicit signal in `analysis.md`'s own `status` field.
>
> ## Why this matters
>
> `launch`'s route③ parameter walkthrough has a real, mechanical gate for this shape of problem: `hooks/confirm_walkthrough.sh` refuses to write `params.yaml` until the schema has actually been read and an explicit answer has come back from the user in the conversation. That gate exists specifically because, per `launch.md`'s own words, *"this step was completed without ever reaching a person, and the resulting file was indistinguishable from one they had approved."*
>
> `finish` has no equivalent. Nothing currently stops `build_package.sh` from running — and being reported as successful — against an `analysis.md` where every entry's `status` is still `proposed`, or where the Results placeholders were never filled in. The failure mode is exactly the one `launch.md` already identified and fixed for a different step: a file that looks approved and is indistinguishable, from the outside, from one that actually was.
>
> ## Suggested fix
>
> - Have `build_package.sh` (or a `hooks/confirm_finish.sh` mirroring `confirm_walkthrough.sh`'s design) refuse — or at minimum print a loud, impossible-to-miss warning — when it finds `analysis.md` entries with `status: proposed`/`revised` that a figure or Results section references, rather than silently building around them.
> - Have the tool's own success message distinguish "assembled" from "ready" — e.g. `wrote submission/manuscript.qmd (4 Results placeholder(s) still need prose — not yet a finished document)` — so an agent (or a person) can't misread a scaffold as a finished deliverable from the printed output alone.
>
> ## Context
>
> Filed as a self-critique after the user noted mid-session that I hadn't followed the plugin's documented flow 100% faithfully; this is a specific, reproducible instance of that. See also #5 (a different but related "silent completion" gap in the same command).

本任務採用的是「建議修補」第一點的**拒絕**那一支（不是「只印警告」那一支）：issue 自己說警告是「至少」；而問題的本質是代理會忽略印出的字，所以選拒絕。

## 範圍：檔案（只准改這些）
- `scripts/build_package.sh`（關卡本體）
- `tests/build_package_test.sh`（新增測試；**不改既有斷言**）
- `skills/finish/SKILL.md`（第 1 步「Take stock」補一句：未接受的條目會讓 build_package.sh 拒絕；只加一句，不改其他字——`tests/package_gaps_test.sh`、`tests/principle_9_test.sh`、`tests/where_test.sh` 會 grep 這個檔的特定字串）
- `docs/FINISH.md`（第 2 步「Assemble」補一句同樣的事；沒有被別的測試鎖字串）

**不需要碰 `hooks/` 與憲法。** 關卡放在 `build_package.sh` 內，不新增 `hooks/confirm_finish.sh`：①`hooks/` 是受保護路徑；②關卡要認的是檔案內容（`status`），不是 Claude 的工具呼叫，放在腳本裡平台端、終端機端、人手動跑都擋得到，hook 只擋 Claude Code 這一條路；③`build_package.sh` 不在憲法 Safety Net 清單內，所以不需要憲法修訂。若 executor 發現非動 `hooks/` 不可，停下回報 BLOCKED，不要自己碰。

## 作法
**決定一：關卡放哪、在哪個順序。** 順序固定為：
`PLAN 檔存在`（既有，退 2）→ `有 runs`（既有，退 2）→ **（新）選 Python → （新）解析條目＋檢查 status** → `mkdir submission/…`（從現在位置往後搬）→ 其餘不變。
也就是：把 `pick_python` 那一段（現在第 94 行起）搬到 `mkdir -p "$OUT/figures" "$OUT/scripts"`（現在第 83 行）**之前**，關卡緊接其後，`mkdir` 搬到關卡之後。這樣「沒有 plan」「沒有 runs」兩種既有拒絕的優先序不變（既有測試 `no plan`／`no runs` 因此不動），而新的拒絕發生在任何寫入之前。

**決定二：不新增 `scripts/plan_entries.py`，也不複製一份解析器。** 現在的條目解析（`parse_table`、`parse_kv_blocks`）住在 `RESULTS_SECTION=$("$PY" - … <<'PY'` 的內嵌 Python 裡。做法：把那段 Python 存進一個 shell 變數（`PLAN_PY=$(cat <<'PY' … PY)`），用 `"$PY" -c "$PLAN_PY" check "$PLAN"` 先跑一次「只解析＋檢查、不輸出 Results」，建包後面再用 `"$PY" -c "$PLAN_PY" results "$PLAN" "$OUT/figures"` 跑一次。兩次用同一份解析碼，避免 issue #5 那種「兩個解析器看到不同的檔案」的老毛病。（理由不選新模組：`tests/no_second_run_state_test.sh`、`tests/credentials_stay_in_settings_test.sh`、`tests/works_without_host_test.sh` 都會掃 `scripts/*.py`，多一個檔案多一個踩雷點。executor 如果發現上面的做法在 `set -u` 或 Windows 引號上有實際問題，可以改成模組，但要在 PR 說明寫為什麼。）

**決定三：`parse_kv_blocks` 也要抽出 `status`**（現在只回 `id`、`question`）。沿用 `question` 的寫法：`(?:^|\n)\s*status\s*[:=]\s*(.+)`，取值去頭尾空白。缺這一行的條目 `status` 是 `""`。表格格式本來就抽（`FIELDS` 含 `status`；沒有 status 欄的表格，該欄不存在於 `idx`，值同樣是 `""`——用 `row.get("status", "")`）。

**決定四：什麼算「已接受」。** 去頭尾空白、轉小寫後，**恰好**是 `accepted` 或 `done` 才算。其他一律不算，包括：`proposed`、`revised`、空字串或沒寫、`approved`／`ok`／`yes` 之類拼錯或同義詞、`accepted?`、`not accepted`。不做模糊比對、不做前綴比對（`accepted-ish` 不算）。理由：這是安全網，寧可擋錯也不放過；`skills/downstream/SKILL.md` 第 178 行已把合法值寫死為四個。`revised` 擋下是因為它代表「使用者提了修正、代理改過、尚未再被接受」。

**決定五：沒有 `--force`、沒有環境變數可以略過。** issue 要的是機械關卡；留旁路等於把洞留著。使用者真的要在未接受下建包，就是自己去改 `analysis.md` 的 `status`——那個動作本身就是「明說接受」。（見待裁決 1。）

**決定六：沒有 id 的列（#38 項目 2：`id` 為空但整列有內容）也檢查**，顯示為 `(no id)` 加上該列的 question 前 40 字。

**決定七：拒絕訊息（stderr，退出碼 2）。** 逐字（`<PLAN>`、`<OUT>` 換成實際路徑；條目清單每條一行，id 左對齊補空白到最長 id）：
```
build_package.sh: refusing to build - <N> of <M> entries in <PLAN> are not accepted:
  <id>   status: <值，空白寫成 (none)>
  ...
A package is built only from entries the user has accepted. Put each
figure in front of the user, and set that entry's `status: accepted` in
analysis.md when - and only when - they say so in words. Moving on to
/finish or asking a follow-up question is not acceptance (issue #12).
Nothing was written to <OUT>.
```
固定子字串（測試比對這些）：`refusing to build`、`not accepted`、每個未接受條目的 id、`status: proposed`（依實際值）、`Moving on to`、`Nothing was written to`。「Nothing was written」必須是真的：關卡在 `mkdir` 之前。

**決定八：0 條目的既有拒絕（#5，退出碼 1，訊息 `matched 0 plan entries`）原樣保留**，只是現在由 `check` 模式印出；訊息逐字不動，退出碼維持 1（既有測試用 `!= 0` 與子字串比對）。條目數是 0 時不會再報「0 of 0 not accepted」。

**決定九：`--render` 也要過關卡**（關卡在 `--render` 判斷之前，所以自動成立，不用額外寫；測試要鎖住）。

**決定十：標頭註解**。在 `build_package.sh` 開頭註解的「What it assembles」段落之後（**第 45 行之後**，不要動第 2–12 行〔`-h` 印的就是這幾行〕，也不要把 `#   report.md … report_facts.py` 那一行推出前 45 行〔`TC-040` 用 `sed -n '1,45p'` 找它〕）補一段：只組裝使用者接受過的條目、其餘拒絕。同一段順手把第 28–29 行 `manuscript.qmd` 那條「one section per accepted entry」從「描述願望」變成「描述事實」，不需要改字。

## 失敗先行測試（加在 `tests/build_package_test.sh` 最後一行 `echo`／結論之前；沿用該檔的 `ok`／`no` 函式與夾具風格，不碰網路：`CITE_CURL=false`、`ABF_PIPELINE_FETCHER=off` 已在檔頭設好）
夾具：用檔內既有的 `proj_report`（P3）做法，一個最小的 `runs/demo_20260101/results/pipeline_info/` 加 `analysis/analysis.md`。每個案例各用獨立的 `$TMP/gate_*` 目錄。

| 編號 | analysis.md 狀態 | 預期 | 今天 |
|---|---|---|---|
| TC-G01 | 一條，`status: proposed` | 退 2；stderr 含 `refusing to build`、`not accepted`、`richness`、`status: proposed`；`submission/` 目錄**不存在** | 紅（退 0，建了包） |
| TC-G02 | 兩條：`richness` accepted、`evenness` revised | 退 2；stderr 列出 `evenness`、`status: revised`；**不含** `richness`；`submission/` 不存在 | 紅 |
| TC-G03 | 區塊格式，一條完全沒有 `status:` 行 | 退 2；stderr 含 `status: (none)` | 紅 |
| TC-G04 | 表格格式，表頭只有 `id`、`question`（沒有 status 欄） | 退 2；`status: (none)` | 紅 |
| TC-G05 | 一條 `status: approved`（拼法不在清單） | 退 2；stderr 含 `status: approved` | 紅 |
| TC-G06 | 兩條 `accepted`、`done` | 退 0；`submission/manuscript.qmd` 存在；兩條 id 的問題都在 qmd 裡 | 綠（對照，現在就綠） |
| TC-G07 | 一條 `status: Accepted ` 前後有空白（大小寫與空白） | 退 0，建包 | 綠（對照） |
| TC-G08 | 一條 `status: accepted-ish` | 退 2 | 紅 |
| TC-G09 | 先用全 accepted 建一次包，再把其中一條改回 `proposed` 重跑 | 退 2；第一次建出的 `submission/manuscript.qmd`、`report.md`、`provenance.json` 逐位元組不變（`cmp`）；沒有新的 `report.facts.md` | 紅 |
| TC-G10 | 一條 `proposed`，加 `--render` | 退 2（不是 3）；stderr 是拒絕訊息而不是 quarto 缺失訊息 | 紅 |
| TC-G11 | 表格有一列沒 id、`status: proposed`，另一列 `fig1 accepted` | 退 2；stderr 含 `(no id)` | 紅 |
| TC-G12 | 一條 `proposed`，但同時**沒有 runs** | 退 2；stderr 含 `at least one run`（既有的 runs 檢查優先；鎖住順序） | 綠（對照） |
| TC-G13 | 一條 `proposed`，PATH 上的 python 全是壞掉的假檔 | 退非 0；stderr 含 `no working Python on this machine`（鎖住 pick_python 搬家後訊息沒變） | 綠（對照） |
| TC-G14 | 自然語言一段、非表格非區塊（#5 的夾具） | 退 1；stderr 含 `matched 0 plan entries`；不含 `not accepted` | 綠（對照；既有測試已覆蓋，這條防止 check 模式搬家時順序錯） |
| TC-G15 | 說明文字 | `skills/finish/SKILL.md` 與 `docs/FINISH.md` 各自含 `status: accepted` 字樣（`grep -qF`） | 紅 |

手算範例（verifier 可以不跑程式就核對）：
- analysis.md 是 `- **richness**⏎  id: richness⏎  question: Q?⏎  status: proposed` → **拒絕**，退 2，訊息第一行 `build_package.sh: refusing to build - 1 of 1 entries in …/analysis/analysis.md are not accepted:`，第二行 `  richness   status: proposed`，且 `submission/` 沒被建立。
- 兩條：`richness … accepted`、`evenness … revised` → **拒絕**，第一行 `… - 1 of 2 entries …`，只列 `evenness   status: revised`。
- 兩條：`richness … accepted`、`evenness … done` → **建包**，退 0，印 `wrote     submission/manuscript.qmd`。
- 表格 `| id | question |`＋`| fig1 | Q? |`（沒有 status 欄）→ **拒絕**，列 `fig1   status: (none)`。
- 檔案內容是 `We looked at richness and it seemed fine.` → 仍然是 #5 的退 1 `matched 0 plan entries`，**不是**「0 of 0 not accepted」。

## 必須更新的既有斷言（有意的更新；其他一律不准動）
**沒有任何既有測試的斷言需要改。** 逐一核對過：下列檔案的 analysis.md 夾具全部是 `status: accepted`，關卡放行：
- `tests/build_package_test.sh`：主夾具 P（區塊格式，兩條 accepted）、刪掉 analysis.md 之後重建的那條、P2 表格夾具、P3 report 夾具（`printf … status: accepted`）。「unparseable」測試仍是退非 0＋`matched 0 plan entries`＋不印 `wrote … manuscript.qmd`；`no plan`、`no runs`（夾具是 `echo "-"`，runs 檢查在關卡之前所以仍退 2 並含 `at least one run`）、`no working python`、`--render` 沒 quarto（夾具 accepted，仍退 3 含 `Positron`）都不變。
- `tests/package_gaps_test.sh`：P、P2、P5、P6、P7 的表格全是 `| … | accepted |`（含 `fig10`、`figA`、空 id 那一列也是 accepted）。
- `tests/methods_text_fetch_test.sh` 第 11 項：`status: accepted`。
- `tests/report_facts_test.sh` 第 29 行：`status: accepted`。
- `tests/principle_9_test.sh`：只 grep `build_package.sh` 的字串（`no figure file starting with`、`no plan entry claims it`、`trace to a file or to a script`）與不得出現 ```` ```{ ````；搬動程式碼時這三個字串與「不得有程式區塊」都必須原封保留。

如果 executor 做完發現上面任何一條必須改斷言才能綠，那是關卡寫得比決定四更嚴或更鬆的徵兆——**停下回報**，不要改測試。

## 完成標準（done when）
1. 新增的 TC-G01～G15 在實作前**實際跑過一次且紅的恰好是上表標「紅」的那幾條**（記錄在 PR 說明，貼輸出），實作後全綠。
2. 全套測試在 WSL 跑 `tests/run_all.sh` 綠（本機 Git Bash 不行：repo 規定，且這台的 python 是假檔）。
3. **兩個分支比對（repo CLAUDE.md 的 calibration failures 要求）**：把一組「接受」的 analysis.md 夾具（區塊格式、表格格式、含 `fig1`／`fig1_b` 前綴衝突、含空 id 列、含只有 csv 的 id）分別用 `origin/v3` 與本分支各建一次包，`submission/` 內容（除了時間戳）逐檔 `diff` 為空。理由：這次要搬動 `pick_python`／`mkdir` 並把解析碼拆成兩次呼叫，風險是不小心掉了 #32／#38／#39 那批修正（calibration failure 3）。
4. 沒有任何檔案出現在「範圍：檔案」之外的差異（`git diff --stat` 貼進 PR 說明）。
5. `build_package.sh` 開頭註解第 2–12 行未動、`TC-040` 仍綠。
6. 拒絕訊息與決定七逐字一致（TC-G01 比對固定子字串）。

## 環境事實
- repo：`C:\Users\marvi\Desktop\agentic-bioflow\agentic-bioflow_v2`，開發基準分支 `v3`（`origin/v3` @ 54900a2）。
- 這份檔的行號都是 `origin/v3` 當下的行號：`FIELDS` 第 211 行、`mkdir` 第 83 行、`pick_python` 第 94 行、`RESULTS_SECTION=$(` 第 204 行、`QMD=` 第 370 行。executor 要自己重新 grep，不要信這份的數字。
- `status` 合法值來源：`skills/downstream/SKILL.md` 第 178 行（`proposed | accepted | revised | done`）；寫入時機來源：同檔第 288 行（第 6 步「使用者定案時改」）。
- `finish` 對接受的描述：`skills/finish/SKILL.md` 第 38 行（「after figures exist and the user has accepted them, not before」）與第 86 行（第 1 步：「list which entries the user accepted」）。
- 跑單一測試：`bash tests/build_package_test.sh`（Git Bash 對這支多半能跑，但 python 要可用；這台不行，改在 WSL）。全套：見 repo `CLAUDE.md`「For the executor and verifier」——從 ASCII 目錄用 `wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree> && bash tests/run_all.sh'`，worktree 要在本機磁碟、不在同步雲端硬碟。
- 規則文件：`.specify/memory/constitution.md`。這個關卡不屬於 Safety Net 清單，不需要修憲；原則 9（「缺口要看得見」，`tests/principle_9_test.sh`）不得被削弱。
- 不要執行：任何連到站台／HPC 的指令；建包測試不需要網路（`ABF_PIPELINE_FETCHER=off`、`CITE_CURL=false`）。

## 不做
- issue #12 的第二個建議：成功訊息區分「已組裝」與「可交付」、計算並印出 Results 還有幾個 `[GAP: …]` 空位。這是另一個獨立的改動（輸出文字、使用者看得到），先不併入；若維護者要，另開任務。
- 不新增 `hooks/confirm_finish.sh`，不改 `hooks/hooks.json`，不改憲法。
- 不檢查「這個條目的圖檔存在」「Results 段落寫了沒」：既有的 `[GAP: …]` 機制負責，與接受無關。
- 不改 `analysis.md` 的格式、不新增 `status` 的值、不改 `skills/downstream/SKILL.md`。
- 不加 `--force`／`--allow-unaccepted`／環境變數旁路（決定五）。
- 不處理 `platform/` 內任何東西。這份計畫的檔案範圍裡沒有 `platform/abf_platform/actions/__init__`、`pipeline_launch`、`cli`、`store`、`receiver`、`cloud_store`、`actions/datasets.py`、`platform/abf_launch/*`、`platform/abf_station/*`、`scripts/nf_relay.py`、`scripts/egress_ctl.sh`、`scripts/on_site.sh`、`deploy/`、`configs/sites/*`，以及 `docs/OPERATIONS.md`、`INSTALL.md`、`SETTINGS.md`、`SITE_ADAPTER.md`、`TESTING.md`（其他任務正在那邊跑）。

## 待 developer-agent 裁決
1. **要不要留一條有意識的旁路？** 目前決定五是完全沒有。風險：使用者有一份很舊、根本沒有 `status` 欄的 `analysis.md`（`downstream` 還沒規定 `status` 之前寫的），現在會被擋，他必須手改檔案才能建包。我傾向不留旁路（改檔就是「明說接受」），但這是行為改變，請你決定；若要留，建議是 `--accept-all-for-me` 這種難以無意打出的長旗標，並且在 stderr 印一行「已略過接受檢查」。
2. **A 級還是 B 級？** 使用者指示 A（只讓安全網更嚴）。但對「手上有舊 analysis.md」的人這是看得見的行為改變（原本建得起來、現在被拒）。若你判斷這算「使用者看得到的改變」，請改成 B（等維護者看結果）。
3. **`docs/` 只動 `docs/FINISH.md` 一個檔。** 本任務範圍外的那幾份 docs（`OPERATIONS.md`、`TESTING.md` 等）我沒查它們有沒有講 `build_package.sh` 的拒絕條件；若有該補的一行，請在對應任務裡補，不要在這裡動。
4. **`tests/build_package_test.sh` 與 L3 車道其他任務可能同檔。** 我沒查 `dev-queue.json` 有沒有別的任務也要改 `tests/build_package_test.sh` 或 `scripts/build_package.sh`；派工前請先確認，有的話必須序列化，不要平行。

## 裁決

## 裁決二（2026-10-24 developer-agent）
1. 不設繞過旗標。
2. 改為 B 級（使用者看得到的拒絕行為改變；非網頁，verifier＋CI 綠由 developer-agent 合併）；PR 說明寫「以前沒驗收也照打包，以後只有 accepted／done 才打包」。
3. 沒有 status 欄位的舊條目照樣拒絕，訊息要說「在該條目加上 `status: accepted`」。
4. 佇列中沒有其他任務碰 build_package.sh；其他文件不補。

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
