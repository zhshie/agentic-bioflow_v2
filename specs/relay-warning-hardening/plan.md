---
id: relay-warning-hardening
title: 中繼啟動閘門對 NF_RELAY_EXTRA_DOMAINS= / NF_RELAY_PEER_PREFIXES= 的警告補強（取最後一個值、on_site.sh 例外收緊、值要乾淨、訊息要說真話）
tier: A
kinds: backend
lane: L-hook（只動 hooks/confirm_launch.sh 與 tests/confirm_launch_test.sh；不與其他任務的檔案相交）
base: v3
after: relay-env-warning
source: PR #189（fix/relay-env-warning）上 /code-review 的六項發現（兩個警告區塊都適用）；memory/dev-plans/relay-env-warning.md
---

# relay-warning-hardening

> 本檔由 developer-agent 起草（2026-10-24）。A 級：只讓一道既有的安全閘門「說得更準、警告得更全」，不放寬任何東西、使用者看不到新畫面 → verifier 通過＋CI 綠由 developer-agent 自合。
> **`hooks/` 是受保護路徑**：developer-agent 必須在 PR 上跑 `/code-review`（不能只靠 verifier）。
> **前置**：`relay-env-warning`（PR #189）要先合進 `v3`。以下行號是 `origin/fix/relay-env-warning` 的 `hooks/confirm_launch.sh` 與 `tests/confirm_launch_test.sh`（`git show origin/fix/relay-env-warning:<path>`）；#189 合併後若行號漂移，以內容為準。`origin/v3` 目前沒有 PEER 區塊（`hooks/confirm_launch.sh` 內 `NF_RELAY_PEER` 出現 0 次）。

## 目標
中繼啟動（`egress_ctl.sh start|restart`）的確認詢問，對指令自帶的 `NF_RELAY_EXTRA_DOMAINS=` 與 `NF_RELAY_PEER_PREFIXES=` 兩個變數，要**顯示真正會生效的值**，而且**不會被一句 `echo`、一段 `# on_site.sh` 註解或另一條 on_site.sh 指令騙過去**。對使用者的意義：他按「允許」前看到的，就是 shell 實際會交給中繼的清單，而不是攻擊者或誤寫者挑給他看的那一個。

## 維護者原話（verifier 出題用）
- PR #189 上 /code-review 的六項發現（任務指示，developer-agent 2026-10-24 轉述）：
  1. 擷取取的是指令裡**第一個** `VAR=`，shell 用**最後一個**賦值——誘餌 `echo NF_RELAY_PEER_PREFIXES=cpn; NF_RELAY_PEER_PREFIXES=evil bash scripts/egress_ctl.sh start` 會顯示無害的值。→ 每個賦值都要顯示（或至少顯示最後一個），不能只顯示第一個。
  2. `on_site.sh` 例外是對整條指令做子字串比對——`bash scripts/on_site.sh status; NF_RELAY_PEER_PREFIXES=evil bash scripts/egress_ctl.sh start` 或一行 `# on_site.sh` 註解就能藏掉警告。→ 只有「中繼啟動本身是經 on_site.sh 跑的」才免警告，否則警告。
  3. 顯示的值帶著引號、遇空白被截斷、`$(...)` 原樣顯示。→ 去掉外層引號；含 `$(`、反引號或 `$VAR` 的值要說「值在執行時才算出」並附字面。
  4. PEER 的訊息說以這份清單開頭的主機都會被接受，但 `nf_relay.py` 會丟掉無效項、全無效就退回內建清單。→ 改寫成真話；不要把預設清單寫死在 hook 裡。
  5. 兩個區塊程式碼重複。→ 抽一個小的 bash 輔助函式，兩個變數共用。
  6. 測試：兩個變數都補 誘餌、多重賦值、引號值、on_site.sh 出現在別的指令、註解、`$(...)`；既有斷言除訊息措辭外不得改。→ 下面「失敗先行測試」。
- 硬規則（任務指示）：hook 在「現在會詢問」的每一種情況下仍要詢問（只能更強，不能更弱）；只用 bash 內建（hook 逾時＝放行，不能 fork）。→ 完成標準與裁決 4。

## 範圍：檔案（只准改這些，共 3 個）
- `hooks/confirm_launch.sh`（刪掉兩個警告區塊 391–402 與 404–416，換成一個輔助函式＋兩次呼叫）
- `tests/confirm_launch_test.sh`（新增一個輔助函式＋斷言列，緊接在現有 PEER-12 列之後；另有 5 條既有斷言因訊息改寫而改字，清單在「失敗先行測試」末尾）
- `specs/relay-warning-hardening/ledger.md`（新，executor 進度帳本）

**禁止碰**：`scripts/`（含 `nf_relay.py`、`egress_ctl.sh`、`on_site.sh`）、`platform/`、`docs/`、`skills/`、`deploy/`、`commands/`、`hooks/hooks.json`。

## 作法
**現況**：兩個區塊各自做 `[[ $CMD == *VAR=* ]] && [[ $CMD != *on_site.sh* ]]`（`hooks/confirm_launch.sh:396`、`:407`），再用 `VAR=([^[:space:];&|]*)` 取 `BASH_REMATCH[1]`（`:399-400`、`:408-409`；只取第一個、不去引號、遇空白截斷）。改成：

1. **一個輔助函式 `relay_env_warn <變數名>`**（定義在 `ask()`（`:289`）之後、RESIDENT 區塊（`:364`）之前）。純 bash 內建、不開子行程、不用 `$(...)`；用全域變數回傳結果（`RELAY_ENV_HEAD`、`RELAY_ENV_MORE`），不經命令替換。回傳狀態：0＝要警告，1＝不用。兩個區塊各變成：`if relay_env_warn NF_RELAY_EXTRA_DOMAINS; then RELAY_LIST="${RELAY_LIST}<換行>${RELAY_ENV_HEAD}<尾句>${RELAY_ENV_MORE}"; fi`，PEER 同理；尾句各自保留（見 5、6）。
2. **便宜優先**：函式第一行是子字串比對 `[[ $CMD == *"$1="* ]] || return 1`；沒帶該變數的指令（絕大多數）成本不變。所有迴圈有上限（啟動點最多掃 8 個、賦值最多取 20 個）；超過上限時**一律當成要警告**（寧可多問，不可漏）。不得用 `${x//p/}` 或在長指令上反覆 `${CMD#*…}`（`:397-398` 的 #62 註解說明那是平方時間）；每個迴圈步驟只做一次正則比對加一次前綴去除。
3. **「經 on_site.sh 啟動」的精確定義（免警告條件）**：對指令裡**每一個**命中 `RELAY_START_RE`（`:376`）的啟動點，取它**前面、同一個命令段**的文字——命令段的邊界是 `;`、`&`、`|`、反引號、`(`、換行；也就是從上一個邊界之後，到 `egress_ctl.sh` 為止。該啟動點算「經 on_site.sh」，若且唯若這段文字：(a) 含獨立的 `on_site.sh` 詞（前面是行首、`/` 或空白，後面是空白），**且** (b) 從最後一個 `on_site.sh` 之後到 `egress_ctl.sh` 之間**沒有** `'` 或 `"`。**只有所有啟動點都經 on_site.sh 才免警告**；任何一個啟動點是直接的，就警告。例：
   - 免警告：`NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/on_site.sh egress_ctl.sh start`（段內有 on_site.sh，其後無引號）；`NF_RELAY_PEER_PREFIXES=x scripts/on_site.sh --script scripts/egress_ctl.sh start`。
   - 警告：`bash scripts/on_site.sh status; NF_RELAY_PEER_PREFIXES=evil bash scripts/egress_ctl.sh start`（`;` 把 on_site.sh 隔在別的命令段）；`NF_RELAY_PEER_PREFIXES=evil bash scripts/egress_ctl.sh start # on_site.sh`（註解在啟動點之後，不在它前面的段內）；換行後才出現啟動、`# on_site.sh` 在上一行；`scripts/on_site.sh 'NF_RELAY_PEER_PREFIXES=evil bash scripts/egress_ctl.sh start'`（引號內的負載在遠端是**直接**跑，on_site.sh 不會蓋掉它——這一型現行 hook 也被子字串例外藏掉了）；`scripts/on_site.sh --script "${CLAUDE_PLUGIN_ROOT}/scripts/egress_ctl.sh" start`（引號在 on_site.sh 與 egress_ctl.sh 之間，保守地警告；多一句警告無害，見裁決 6）；`scripts/on_site.sh egress_ctl.sh start; NF_RELAY_PEER_PREFIXES=evil bash scripts/egress_ctl.sh start`（第二個啟動點是直接的）。
   - 為什麼經 on_site.sh 的才能免：`scripts/on_site.sh:491-497` 在 `egress_ctl.sh` 本地執行時一律（含空值）以設定檔的值設定兩個變數（`:496` EXTRA、`:497` PEER），遠端執行時 `carry` 同樣覆蓋（`:509` PEER、`:514` EXTRA）。
4. **取值**：從整條指令找出**每一個** `VAR=` 賦值（不要求前面是詞邊界——多警告一個同名後綴變數無害，少警告才有害）。每個賦值的值取一個詞：以 `"` 開頭取到下一個 `"`、以 `'` 開頭取到下一個 `'`（含其中空白）、否則取到下一個空白或 `;&|`。成對的外層引號去掉。顯示只取前 200 字元，超過加 `…`。
   - **取最後一個當主角**：標頭句 `THIS COMMAND ALSO SETS ${變數}=${最後一個值}`，單一賦值時與現行格式一致（既有測試靠這個前綴）。
   - **有多個賦值就全列**：`RELAY_ENV_MORE` 附一句 `It assigns ${變數} N times: v1 | v2 | v3 (the last one is normally the one that takes effect; read the command).`。最多列最後 5 個，更多就寫 `(N-5 earlier ones not shown)`。
   - **值在執行時才算出**：去引號後的值含 `$`、反引號、或殘留的 `"`/`'`/`\`，標頭改成 `THIS COMMAND ALSO SETS ${變數} (value is computed at run time: ${字面})`。字面＝照抄（已去外層引號），例：`$(cat /tmp/p)`。未加引號的 `$(cat /tmp/p)` 會在空白處被截成 `$(cat`——照樣顯示截斷的字面，並在括號內補 `, cut at the first space; read the command`。
5. **PEER 尾句改寫（真話版）**：標頭後接 `, which asks the relay to use this list of host-name prefixes for the hosts that may connect, instead of the deployment's setting. Entries that are not valid are dropped, and a list with no valid entry falls back to the built-in one; the relay's startup line ("peers :") shows the list it really uses. Show the user the prefixes it names.` 依據（`origin/v3`）：`scripts/nf_relay.py:224-246` 丟掉無效項（`_PREFIX_RE` 要 3–32 字元的 a-z0-9-，`:220`；最多 20 項，`:221`），`:249-255` 全無效就用 `DEFAULT_HOST_PREFIXES`（`:212`），`:281` 啟動行印 `peers  :`。**hook 內不得出現 `cpn,gpn,bgm,lgn,localhost`**。空值說明句（現行 `:412-415`）保留、措辭不變：`scripts/egress_ctl.sh:83` 用 `${NF_RELAY_PEER_PREFIXES:-$(setting relay_peer_prefixes)}`，空值確實改用設定值。
6. **EXTRA 尾句不變**（`, which overrides this deployment's list: the relay would carry THAT list, not the one shown above. Show the user the domains it names.`），既有 `envp` 靠 `overrides this deployment's list` 判斷。兩段仍各自用不同字樣；順序固定先 EXTRA 後 PEER。
7. **離場行為不變且不更弱**：不新增 `allow` 路徑、不新增 `exit 0`、不改 `ask` 的呼叫與外框文字（`:418`；`ask()` 在 `:289`）。警告條件相對現行只會變多：現行「有變數且整條指令不含 `on_site.sh`」→ 沒有任何啟動點的命令段含 on_site.sh → 新條件必警告。
8. **只改 `RELAY_LIST` 的文字**；`RELAY_START_RE`、`RESIDENT_RE`、`RELAY_DOMS` 摘要都不動。

## 失敗先行測試
全放 `tests/confirm_launch_test.sh`，緊接在現有 PEER-12 列的最後一條（`idg "PEER-12 plain start still asks"`，第 853 行）之後。新增一個輔助函式 `envw <label> <變數> <has|lacks> <指令> [必含字串]`，沿用 `envp`（第 790–797 行）的寫法：`python3 -c json.dumps` 組輸入、`LAB_SETTINGS_FILE="$TMP/id_env.yaml" bash "$H"` 執行、`grep -qF --` 比對。以 `for V in NF_RELAY_EXTRA_DOMAINS NF_RELAY_PEER_PREFIXES; do … done` 讓每個案例對兩個變數各跑一次（標籤帶變數名）。`has/lacks` 判的是**該變數自己的標頭句** `THIS COMMAND ALSO SETS ${V}`。現在全會紅或不存在。

每個變數 15 條（`V` 代表該變數；`ok`、`evil` 是任意值）：
- **RWH-1 誘餌 echo**：`echo V=ok; V=evil bash scripts/egress_ctl.sh start` → has，且含 `SETS V=evil`。
- **RWH-2 同行多重賦值**：`V=ok V=evil bash scripts/egress_ctl.sh start` → has，含 `SETS V=evil` 與 `assigns V 2 times: ok | evil`。
- **RWH-3 雙引號**：`V="a,b" bash scripts/egress_ctl.sh start` → 含 `SETS V=a,b`（沒有引號）。
- **RWH-4 引號內有空白**：`V="a b" bash scripts/egress_ctl.sh start` → 含 `SETS V=a b`。
- **RWH-5 單引號**：`V='a,b' bash scripts/egress_ctl.sh start` → 含 `SETS V=a,b`。
- **RWH-6 on_site.sh 在別的命令**：`bash scripts/on_site.sh status; V=evil bash scripts/egress_ctl.sh start` → has。
- **RWH-7 尾端註解**：`V=evil bash scripts/egress_ctl.sh start # on_site.sh` → has。
- **RWH-8 上一行的註解**：`$'# on_site.sh\nV=evil bash scripts/egress_ctl.sh start'` → has。
- **RWH-9 on_site.sh 的引號負載**：`scripts/on_site.sh 'V=evil bash scripts/egress_ctl.sh start'` → has。
- **RWH-10 兩個啟動點**：`scripts/on_site.sh egress_ctl.sh start; V=evil bash scripts/egress_ctl.sh start` → has。
- **RWH-11 對照：經 on_site.sh 免警告**：`V=ok bash scripts/on_site.sh egress_ctl.sh start` → lacks（等同現有 PEER-9）。
- **RWH-12 對照：`--script` 形式免警告**：`V=ok scripts/on_site.sh --script scripts/egress_ctl.sh start` → lacks。
- **RWH-13 未加引號的命令替換**：`V=$(cat /tmp/p) bash scripts/egress_ctl.sh start` → 含 `value is computed at run time: $(cat`。
- **RWH-14 加引號的命令替換**：`V="$(cat /tmp/p)" bash scripts/egress_ctl.sh start` → 含 `value is computed at run time: $(cat /tmp/p)`。
- **RWH-15 變數展開**：`V=$P bash scripts/egress_ctl.sh start` → 含 `value is computed at run time: $P`。

仍須「詢問」（用現有 `idg`，期望 `ask`；只對 PEER 變數各一條，證明新增的是文字、閘門仍在）：
- **RWH-16** RWH-1 的指令；**RWH-17** RWH-6 的指令；**RWH-18** RWH-9 的指令。

僅 PEER 的訊息措辭（用現有 `envq_txt`；第三條需在 `envw` 加反向字串，或另寫一條 `lacks` 風格判斷）：
- **RWH-19** 含 `Entries that are not valid are dropped`；**RWH-20** 含 `falls back to the built-in one`；**RWH-21** 輸出**不含** `cpn,gpn,bgm,lgn,localhost`。

合計新增 15×2 ＋ 3 ＋ 3 ＝ **36 條**（≤40）。

**既有斷言被改的清單（只有訊息措辭，共 5 條，行號為 `origin/fix/relay-env-warning`；executor 在 ledger 貼改前／改後）：**
1. 第 830 行 `PEER-3 value stops before the semicolon`：必含字串 `${PW_SETS}25a-cpn, which changes` → `${PW_SETS}25a-cpn, which asks the relay to use this list of host-name prefixes`。
2. 第 832 行 `PEER-4 empty value is shown as empty`：`${PW_SETS}, which changes` → `${PW_SETS}, which asks the relay to use this list of host-name prefixes`。
3. 第 837 行 `PEER-7 the value is shown in the warning`：`${PW_SETS}25a-cpn,25a-lgn, which changes` → `${PW_SETS}25a-cpn,25a-lgn, which asks the relay to use this list of host-name prefixes`。
4. 第 838 行 `PEER-7 warning wording: which hosts`：`which changes which hosts may connect to the relay` → `for the hosts that may connect, instead of the deployment's setting`。
5. 第 839 行 `PEER-7 warning wording: default list`：`instead of the deployment's setting (default cpn,gpn,bgm,lgn,localhost)` → `falls back to the built-in one`（寫死預設清單的字樣依發現 4 拿掉）。

除這 5 條外，既有每一條（含 `envp` 四條 798–801、PEER-1…PEER-12 其餘、整個 `idg`／`idw` 組）原樣；若有任何其他條需要改才能綠，回報 BLOCKED。

## 完成標準（done when）
- 上面 36 條新測試綠；`bash tests/confirm_launch_test.sh` 全綠；全套綠（WSL 內 `bash tests/run_all.sh`，見 repo CLAUDE.md「For the executor and verifier」）。
- **「閱卷看 diff」的手動案例依 `memory/dev-plans/README.md`「通例：閱卷看 diff」處理**：不寫進 docs/TESTING.md；executor 把證據貼進 `specs/relay-warning-hardening/ledger.md`，verifier 依 ledger 並自己重跑核對，不以「TESTING.md 沒有步驟」退回。證據包含：
  - `git diff --name-only origin/v3...HEAD` 只有「範圍」列的三個檔；`git diff` 對 `scripts/`、`platform/`、`docs/`、`skills/` 為空。
  - **兩個分支各跑一遍**（repo CLAUDE.md 校正失敗紀錄的要求）：在 `origin/v3`（含已合併的 #189）與本分支各跑 `bash tests/confirm_launch_test.sh`，輸出存檔逐行比對：差異只允許是上述 5 條改字與 36 條新增；其餘每行 ok／FAIL 狀態一致。
  - **「不更弱」比對**：把舊 hook（v3 合併 #189 後）與新 hook 各餵同一批指令（RWH 全部指令、現有 EXTRA／PEER 全部指令、`bash scripts/egress_ctl.sh start|stop|restart|status`、`bash scripts/agent_ctl.sh start`、一條不相關的 `ls`），比對 `permissionDecision`：新 hook 的 `ask` 集合必須包含舊 hook 的 `ask` 集合，其餘指令兩邊一致。
  - **成本**：用一條約 100 KB、含 3 個 `egress_ctl.sh start` 與 25 個 `V=` 賦值的指令，及一條不含兩個變數的 100 KB 指令，各用 `time` 跑新舊 hook，貼出數字；後者不得比舊 hook 慢（容許量測誤差），前者要遠低於 `hooks/hooks.json` 裡 confirm_launch 那一項的逾時。
  - `relay_env_warn` 函式本體內沒有命令替換、`grep`、`jq`、`python` 等外部程式（用 `sed -n` 取出函式本體後 grep 檢查，貼結果）。
- `git diff hooks/confirm_launch.sh` 中，除 391–416 行的兩個區塊被替換外，沒有其他既有行被改。
- developer-agent 在 PR 上跑過 `/code-review`，無未處理的 high 項。

## 環境事實
（行號為 `origin/fix/relay-env-warning`，先 `git -C <repo> fetch -q origin`，用 `git show` 讀，不要改主 repo。）
- `hooks/confirm_launch.sh`：`ask()` `:289`；`RESIDENT_RE` `:364`；`RELAY_START_RE` `:376`；EXTRA 區塊 `:391-402`（條件 `:396`，取值正則 `:399-400`，訊息 `:401-402`）；PEER 區塊 `:404-416`（條件 `:407`，取值 `:408-409`，訊息 `:410-411`，空值說明 `:412-415`）；`:417` 是啟動 `if` 的 `fi`，`ask "GATE: this starts…"` 在 `:418`。
- 現行缺陷可重現：`[[ $CMD =~ $RELAY_PEER_OVR_RE ]]` 取第一個命中（`:409`）；例外 `[[ $CMD != *on_site.sh* ]]`（`:396`、`:407`）看整條指令。
- `scripts/nf_relay.py`（`origin/v3`）：`DEFAULT_HOST_PREFIXES` `:212`；`_PREFIX_RE` `:220`；`PREFIX_LIMIT` `:221`；`_parse_peer_prefixes` `:224-246`（空項略過、非 ASCII 丟、不合 `^[a-z0-9][a-z0-9-]{2,31}$` 丟、重複略過、超過 20 項丟）；`_PEER_RAW` `:248`；全無效退回預設 `:249-255`；`PEER_NOTE` `:256`；啟動行 `peers  :` `:281`。
- `scripts/egress_ctl.sh:83`（`origin/v3`）：`export NF_RELAY_PEER_PREFIXES="${NF_RELAY_PEER_PREFIXES:-$(setting relay_peer_prefixes)}"`（變數先、設定後；空值＝用設定）。
- `scripts/on_site.sh`（`origin/v3`）：`:491-497` 本地執行 `egress_ctl.sh` 時永遠設定（含空值）；`:509`、`:514` 遠端 `carry`；呼叫者環境的值被蓋掉。
- `tests/confirm_launch_test.sh`：`H` `:31`；`id_env.yaml` `:619`；`idg` `:621`；`envp` `:790-797`；`envq`／`envq_txt`／`envq_order` `:803-826`；PEER-1…11 `:827-845`；PEER-12 `:846-853`。
- repo 教訓：hook 逾時＝放行（檢查必須便宜）；改閘門曾放行三種本該擋的形狀（CLAUDE.md 校正失敗 #1）→ 必須兩分支各跑一遍。repo CLAUDE.md「For the executor and verifier」：規則文件 `.specify/memory/constitution.md`；單檔測試 `bash tests/<name>.sh`；全套 `tests/run_all.sh` 須在 WSL／Linux；**不得**改 `spec.md`、`test-case*.md`、憲法、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`；**不得**連站台或 HPC。

## 不做
- 不改 `scripts/`（中繼、`egress_ctl.sh`、`on_site.sh`）、`platform/`、`docs/`、`skills/` 的任何行為或文字，也不改設定檔。
- 不新增別的攔截：不對其他環境變數（例如 `NF_RELAY_PORT`、`NF_RELAY_EXTRA_NOTE`）加警告；不處理間接寫法（`V=NF_RELAY_PEER_PREFIXES; export $V=…`、`printf -v`、`env -S`）——現行也抓不到，另開任務，在 ledger 記一句即可。
- 不在 hook 裡重做 `nf_relay.py` 的有效性檢查（不驗每個前綴是否合法；訊息只說「無效項會被丟掉」，真實清單看中繼啟動行）。
- 不改 `hooks/hooks.json` 的 matcher 與逾時；不改 `ask()`；不改 EXTRA 訊息的尾句。
- 不展開 `$VAR`／`$(…)`（hook 不能求值指令內容，只能照抄字面）。

## 裁決（2026-10-24，developer-agent 起草；與上文衝突時以本段為準）
1. **抽共用函式，推翻 `relay-env-warning` 裁決 1 的「不抽函式」。** 理由：當時是為了讓 #189 的 diff 純新增、好審；#189 已合併，而重複正是 /code-review 找到的缺陷同時出現在兩處的原因，修一處漏一處的風險比 diff 大小更大。審查成本由「兩個分支各跑一遍＋舊 ask 集合 ⊆ 新 ask 集合」的證據吸收。**另一選項**：兩個區塊各修一遍。**預設：抽函式。**
2. **顯示最後一個值為主角、其餘全列，不只顯示其中一個。** 理由：shell 用最後一個，使用者要看到的是會生效的；但跨 `;` 的指令裡「最後一個」不一定就是套用到啟動點的那個，所以其餘也列，並寫「通常最後一個生效，請讀指令」。**另一選項**：只顯示最後一個（較短但會隱藏誘餌）。**預設：全列（最多 5 個）。**
3. **on_site.sh 例外改成「逐個啟動點、同一命令段、其後無引號」。** 理由：子字串測試被一句註解就繞過；完整解析 shell 語法在 hook 裡做不到也不該做。這個定義寧可誤報（引號形式的 `--script "…/egress_ctl.sh"` 會多一句警告）也不漏報。**另一選項**：整個拿掉例外、永遠警告（最簡單，但經 on_site.sh 的正規路徑會天天多一句假警報）。**預設：保留收緊後的例外。**
4. **迴圈上限與「超過就警告」。** 理由：hook 逾時＝放行，所以最壞情況的成本要有上限；超過上限選警告而不是放過，維持「不更弱」。
5. **PEER 訊息不寫預設清單。** 理由：預設清單住在 `nf_relay.py:212`，hook 抄一份遲早漂移；真實生效的清單由中繼啟動行 `peers  :`（`nf_relay.py:281`）顯示，訊息指向它。
6. **引號形式的 `scripts/on_site.sh --script "…/egress_ctl.sh" start` 會警告。** 這是裁決 3 的已知代價，測試不鎖定這一型，verifier 不得以此退回。

## 裁決二（2026-10-24 developer-agent）
1. 抽成一個 helper 接受（取代 relay-env-warning 裁決的「只新增」：那條是為了 #189 的 diff 好審，這件的目的就是消除重複）。
2. 保留縮窄後的 on_site.sh 豁免；`--script "…"` 帶引號形式的誤報接受、在 ledger 記一筆。
3. 間接指派（export $V=、printf -v、env -S）另案。
4. 開工前確認 #189 已合進 v3，行號以最新 v3 重新核對。

## 裁決三（2026-10-24 18:50 developer-agent，PR #196 的 /code-review 後重做；以本段為準，取代作法 2、3 與裁決二 2）
審查找到：空的分支 `(X|)` 在部分 bash（含這台 Git Bash）regex 編譯失敗、豁免整個失效；主角值取「整條指令最後一個 VAR=」會被啟動點**之後**的 echo 誘餌騙；`*[\"'\]*` 寫錯是死碼；`^(.*)…` 回溯在長指令可能超時（hook 逾時＝放行，等於安全網被繞過）；沒有左邊字界（MY_NF_RELAY_…）；單引號值被誤標「執行時才算」。改成更簡單、更嚴的做法：
1. **只看啟動點自己那一段**：用 bash 內建參數展開（`${cmd%%;*}` 這類，不用帶 `.*` 的回溯 regex）把指令依 `; & | ( ) 換行 反引號` 切段；只處理含 `egress_ctl.sh` 加 start/restart 的段。
2. **值只取該段開頭的環境前綴**（`VAR=… [VAR2=…] bash …/egress_ctl.sh start`，或該段前面同一連續區塊的 `export VAR=…`）；要求左邊字界（段首或空白）。同一段多個指派以 shell 實際生效的最後一個為主角，全部列出。段外任何地方出現 `VAR=`（echo、註解、其他段）：不採用為值，但只要整條指令任何地方出現 `VAR=` 而且有啟動點，就照樣印一行「指令其他地方也提到 VAR=，請讀整條指令」——寧可多警告。
3. **豁免**：只有當該段的命令本身是 `…on_site.sh`（段的第一個非指派詞以 `on_site.sh` 結尾）且 egress_ctl.sh 是它後面的參數時才豁免；`cat on_site.sh egress_ctl.sh start` 之類不豁免。
4. 引號：雙引號值去外層引號後若含 `$` 或反引號→「執行時才算」；單引號值一律字面顯示；`"a"b` 這類相鄰拼接照 shell 規則拼起來顯示。修掉死碼的括號樣式。
5. **成本**：不准用 `^(.*)` 形式的 regex；段數上限 50、每段長度上限 4096 字元，超過就直接警告（不解析）。加一條 1 MB 指令的計時測試，必須 < 2 秒。加一條測試斷言 helper 用到的每個 regex 在 `bash --posix` 下能編譯（`[[ x =~ $re ]]` 回傳碼不是 2）。
6. 審查的 8 點各加至少一條會在舊寫法紅、新寫法綠的測試；「不更弱」比對（舊版會問的新版都要問）照舊。

## 裁決四（2026-10-24 19:10 developer-agent，回答出題退回的 8 點；以本段為準，取代裁決三中衝突的部分）
1. **整條指令長度上限 64 KB、切出的段數上限 50**：超過就不解析，直接印標頭 `THIS COMMAND ALSO SETS <VAR> (not parsed: the command is too long or has too many parts); read the whole command.`（仍含 `THIS COMMAND ALSO SETS <VAR>`，envw 的 has 判斷照用）。所以 1 MB 測試必走這條快路，兩種形狀（單一超長段、大量短段）都要 < 2 秒。
2. **切段要認得引號與 `$( )`／反引號**：用一個逐字元的 bash 迴圈（只在 ≤64 KB 時跑）追蹤單引號、雙引號、`$(` 深度與反引號；只有在引號外、`$( )` 外的 `; & | ( ) 換行` 才切段。不用任何 `^(.*)` 回溯 regex。
3. **前導直譯器**：段內先跳過開頭的 `VAR=值` 指派；若下一個詞是 `env`，再跳過 `env` 和它後面的 `VAR=值`；若下一個詞是 `bash` 或 `sh`（可帶 `-c` 以外的選項），跳過它。剩下的第一個詞就是「命令」。
4. **豁免**：只有「命令」以 `on_site.sh` 結尾，且 `egress_ctl.sh` 以**未加引號**的詞出現在它後面時才豁免。`egress_ctl.sh` 若出現在引號裡（例如 `scripts/on_site.sh 'V=evil bash scripts/egress_ctl.sh start'`）＝藏在字串裡的啟動，一律警告、不豁免（RWH-9 照舊 has）。`cat on_site.sh egress_ctl.sh start` 的命令是 `cat`，不豁免。
5. **值的來源**：(a) 該段的前綴指派（含 `env` 後面的）；(b) 同一條指令裡、在啟動段**之前**的任一段 `export VAR=值`。兩者都算，以 shell 實際生效順序的最後一個為主角，全部列出；隱藏了項目時，第一個和最後一個一定都顯示。左邊要有字界（段首、空白或 `env `）。
6. **其他地方提到 VAR=**（echo、註解、引號字串、啟動段之後）：不採用為值，另印一行 `This command also mentions <VAR>= elsewhere (not as the value the relay gets); read the whole command.`。
7. **引號與顯示**：雙引號值去外層引號，若含 `$` 或反引號→`(value is computed at run time: <原文>)`；單引號值一律字面顯示；相鄰拼接（`"a"b`）照 shell 規則拼成 `ab`。修掉死碼括號樣式。
8. **審查 8 點全列**（每點至少一條「舊寫法紅、新寫法綠」的測試，舊寫法＝commit 0b104ad 的 hook）：①空分支 regex 編譯失敗（加測試：helper 用到的每個 regex 在 `bash --posix` 下 `[[ x =~ $re ]]` 回傳碼不是 2）②啟動點之後的誘餌改了標題 ③死碼括號 ④on_site.sh 只是參數也被豁免、同段兩個啟動點只看一個 ⑤沒有左邊字界／`"a"b` 顯示錯 ⑥回溯可能逾時 ⑦單引號值被誤標 ⑧沒有測試能抓到 regex 編譯失敗。
9. 作法 2 的「賦值最多取 20 個」取消；「最多列 5 個」保留但加上第 5 點的首尾規則。測試數量不設上限；既有斷言除措辭外不改，env 前綴（envp #45、PEER-2）與 export（PEER-3）照舊警告並顯示值。

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
