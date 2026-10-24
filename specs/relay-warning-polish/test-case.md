# 測試案例：轉送啟動警告的顯示細節（relay-warning-polish）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Language: 繁體中文; identifiers and file paths stay as they are.
-->

**規格**：`specs/relay-warning-polish/plan.md`（本任務沒有 spec.md；計畫含「裁決」與「裁決二」，衝突時以裁決二為準）　**總覽**：`test-case-overview.md`

名詞（第一次出現就翻譯）：

- **V**：指兩個變數名之一。`E` ＝ `NF_RELAY_EXTRA_DOMAINS`（中繼額外放行的網域清單），`P` ＝ `NF_RELAY_PEER_PREFIXES`（哪些主機可以連中繼的名稱前綴清單）。標「V 各一次」的 TC 對 E、P 兩個都跑。
- **警告區**：hook 回給 AI 的那段文字（`additionalContext`），裡面有 `THIS COMMAND ALSO MENTIONS V=`、`[值]` 清單、`N mention(s) in total`。測試用 `envw`／`envbig` 檢查的就是它。
- **提到**：指令文字裡出現一次 `V=`。
- **左邊字界**：`V=` 左邊那個字元。依裁決二，只有它是英數字或底線（`A-Za-z0-9_`，例如 `MY_P=` 的 `_`）才「不算一處提到」；字串開頭或任何其他字元（空白、tab、換行、`;&|(`、引號、反引號、`{`、`$`、`=`…）都算提到。
- **S**：PEER 的空值說明句 `An empty value is ignored by the relay, which then uses the deployment's relay_peer_prefixes setting.`
- **X120**：120 個 `x`。
- **手動**：依 `memory/dev-plans/README.md`「通例：閱卷看 diff」，證據貼進 `specs/relay-warning-polish/ledger.md`，閱卷者自己重跑核對；不寫進 `docs/TESTING.md`，也不得以「TESTING.md 沒有步驟」退回。
- 自動測試都放 `tests/confirm_launch_test.sh`，新增的標籤前綴 `POL-`（對應計畫的 POL-n）；改過的既有斷言保留原標籤。「既有」＝計畫沒說要改、必須原樣仍綠的斷言。

類型只有三種：**功能**（規格說要做到的事做到了）、**例外**（出錯或可能變弱時系統怎麼反應）、**不在範圍**（計畫明講不做的事，確認真的沒做）。

## User Story 1 — 被截掉或沒列出的地方要標出來（優先度 P1；發現 1、2、4）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 發現 1；POL-1 | 功能 | hook 與測試設定同既有 `envw` | V 各一次：送 `V=<X120>yy bash scripts/egress_ctl.sh start`（值是 120 個 x 再加 `yy`） | 警告區含 `<X120>…]`（120 個 x 後面緊接 `…` 再接 `]`），**不含** `<X120>y`；有標頭 | 自動：`tests/confirm_launch_test.sh`（POL-1） |
| TC-002 | 發現 1；POL-6 | 功能 | 同上 | 送 `P=a"b c d bash scripts/egress_ctl.sh start`（引號沒關，在空白處被切） | 警告區含 `[a"b…]` | 自動（POL-6） |
| TC-003 | 發現 1；POL-11 | 功能 | 同上 | 送 `P="a b; c bash scripts/egress_ctl.sh start`（引號沒關，在分號處被切） | 警告區含 `["a…]` | 自動（POL-11） |
| TC-004 | 發現 2；POL-2 | 功能 | 同上 | V 各一次：送 `V=m1x V=m2x V=m3x V=m4x V=m5x bash scripts/egress_ctl.sh start`（5 處） | 警告區含一行 `(mention 4 is not listed; read the whole command shown below)` | 自動（POL-2） |
| TC-005 | 發現 2；POL-7 | 功能 | 同上 | 送 P 的 6 處提到（`P=m1x … P=m6x bash scripts/egress_ctl.sh start`） | 警告區含 `(mentions 4 to 5 are not listed; read the whole command shown below)` | 自動（POL-7） |
| TC-006 | 發現 2；POL-8 | 功能 | 同上 | 送 P 的 4 處提到 | 警告區**不含** `are not listed`、也**不含** `is not listed`（4 處全列，不多說） | 自動（POL-8） |
| TC-007 | 發現 4；POL-4 | 功能 | 同既有 `envbig`（新增的測試沿用 `spread70`：約 70 KB、500 處提到） | V 各一次：送 `spread70`，限時 1500 ms | 警告區含 `The values are not listed because the command is over 64 KB; read the whole command shown below.`、含 `sc7`（值）的相反：**不含** `sc7`；仍含 `500 mentions in total`；閘門仍是 ask | 自動（POL-4，`envbig`） |
| TC-008 | 作法 3「步數上限」；POL-23 | 例外 | 新 `envbig` kind `lookalike25`：`echo ` ＋ 25 個 `MY_P=x ` ＋ `; P=real1 bash scripts/egress_ctl.sh start`（約 1 KB） | 送出，限時 500 ms | 警告區含 `1 mention in total`、含 `too many names that only end in NF_RELAY_PEER_PREFIXES`，**不含** `real1`（寧可不列也不列錯）；閘門仍是 ask | 自動（POL-23） |
| TC-009 | 作法 3「任一方向用完上限」（計畫無例子，由規則推出） | 例外 | 同 TC-008 的做法 | 送 `P=m1x P=m2x P=m3x P=m4x` 後面接 25 個 ` MY_P=x`，再 `bash scripts/egress_ctl.sh start`（最後一個好的提到之後有 25 個名字只是尾巴相同的壞提到，往後掃 20 圈找不到） | 警告區含 `4 mentions in total`、含 `too many names that only end in NF_RELAY_PEER_PREFIXES`，**不含** `m1x`、`m2x`、`m3x`、`m4x`（整份不列原文）；閘門仍是 ask | 自動（POL-新增，標籤 `POL-back20`） |
| TC-010 | 作法 5「顯示格式不變」；既有 TC-015/016/017/018/019/021 | 功能 | 既有斷言 | 跑既有的 1 處、4 處、5 處、6 處、超過 120 字元、E＋P 同時提到的指令 | 既有斷言**原樣**仍綠：`Text after each V= as written (first 3 and last 1 of them): …; N mention(s) in total.` 這一行格式沒變；4 處全列、5 處第 4 處不列、6 處第 4、5 處不列；兩個變數的區塊順序不變 | 自動（既有，不改） |

## User Story 2 — 引號裡的值要整個顯示（優先度 P1；發現 3）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 發現 3；POL-3；既有 TC-010 雙引號改期望 | 功能 | 同上 | V 各一次：送 `V="qq1 rr2" bash scripts/egress_ctl.sh start` | 警告區含 `["qq1 rr2"]`（引號原樣保留、顯示到收尾引號），**不含** `"qq1 rr2"…`（值沒被截）。既有 `TC-010 … double-quoted value kept as written` 的檢查從 `'"qq1'` 加 `!qq1 rr2` 改成 `'"qq1 rr2"'` | 自動（POL-3 ＋改後的 TC-010） |
| TC-012 | 發現 3；POL-9；既有 TC-010 單引號改期望 | 功能 | 同上 | 送 `P='qq1 rr2' bash scripts/egress_ctl.sh start`；以及既有 TC-010 的 E、P 兩個單引號案例 | 警告區含 `['qq1 rr2']`；既有 `TC-010 … single-quoted value kept as written` 的檢查改成 `"'qq1 rr2'"` | 自動（POL-9 ＋改後的 TC-010） |
| TC-013 | 發現 3＋1；POL-10 | 功能 | 同上 | 送 `P="` ＋ 200 個 `x` ＋ `" bash scripts/egress_ctl.sh start`（引號內的值超過 120 字元） | 警告區含 `"` ＋ 119 個 `x` ＋ `…]`（共 120 字元：引號加 119 個 x，然後 `…`） | 自動（POL-10） |
| TC-014 | 發現 3；POL-12 | 功能 | 同上 | 送 `P="a b"c bash scripts/egress_ctl.sh start`（收尾引號後面緊接字） | 警告區含 `["a b"…]`（值還在繼續，所以加 `…`） | 自動（POL-12） |
| TC-015 | 「不做」第 2 點（不去跳脫、不展開）；作法 5 | 不在範圍 | 既有斷言 | 跑既有 TC-010 `V=a\"b c`、TC-011 `V=$(cat /tmp/p)`（不加引號與加引號兩種）、TC-012 `V=$P` | 既有斷言**原樣**仍綠：`a\"b` 照字面顯示且**不含** `a\"b c`；`$(cat` 照字面顯示，不含 `$(cat /tmp/p)`（不加引號時）、不含 `computed at run time`；`$P` 照字面顯示。沒有任何展開、去引號、跳脫處理 | 自動（既有，不改） |

## User Story 3 — 名字只是尾巴相同的變數不再誤報，其餘都照舊警告（優先度 P1；發現 6）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 發現 6；POL-5；既有 TC-020 翻轉 | 功能 | 同上 | V 各一次：送 `MY_V=zzval bash scripts/egress_ctl.sh start`。既有 `TC-020 … MY_ prefix still warns` 期望從 has 改 lacks、標籤改成 `MY_ prefix is not a mention` | 警告區**沒有** `THIS COMMAND ALSO MENTIONS V=` 這個標頭 | 自動（POL-5 ＋改後的 TC-020） |
| TC-017 | 發現 6；POL-13 | 功能 | 同上 | 送 `(P=a bash scripts/egress_ctl.sh start)` | 有警告（`(` 後面的提到算一處） | 自動（POL-13） |
| TC-018 | 發現 6；POL-14 | 功能 | 同上 | 送 `echo "P=a"; bash scripts/egress_ctl.sh start` | 有警告（引號後面的提到算一處） | 自動（POL-14） |
| TC-019 | 發現 6；POL-15 | 功能 | 同上 | 送 `MY_P=bad P=good bash scripts/egress_ctl.sh start` | 有警告；含 `[good]`、含 `1 mention in total`、**不含** `bad`（壞提到既不列也不計次） | 自動（POL-15） |
| TC-020 | 作法 8；POL-18；既有 TC-030/038/039/040 | 例外 | 同上 | 送 `MY_P=x bash scripts/egress_ctl.sh start`（沒有警告的指令）；並跑既有「沒提到但仍詢問」「誘餌仍詢問」等 `idg` 斷言 | 閘門決定仍是 `ask`（沒警告不等於放行）；既有 `idg` 斷言原樣仍綠 | 自動（POL-18 ＋既有） |
| TC-021 | 裁決二 1（唯一變弱的形狀已消除；計畫無測試例，由明文理由推出） | 例外 | 同上 | V 各一次：送 ``` `V=x bash scripts/egress_ctl.sh start` ```（整條包在反引號裡，`V=` 左邊是反引號） | 有警告、含標頭；閘門仍是 ask（反引號不是名字字元，必須算一處提到，不得因此少警告） | 自動（標籤 `POL-bq`） |
| TC-022 | 裁決二 1、5；作法 2 | 功能 | 本分支 diff | 讀 `git diff origin/v3...HEAD -- hooks/confirm_launch.sh`，找字界判斷（壞提到的移除式與列出階段的 `prev`／`${t: -1}` 判斷） | 「不算提到」的字元集合只有 `[A-Za-z0-9_]`；沒有把 tab、換行、`;`、`&`、`\|`、`(`、引號、反引號、`{`、`$`、`=` 放進「不算提到」的集合（閱卷者逐一對照）；壞提到數的除數是 `${#V}+2`；結果記於 `ledger.md`，並有一句記載「裁決二 1：集合反向定義」 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-023 | 發現 6「仍須 O(n)，並說明怎麼做到」；作法 2 | 功能 | 本分支 diff | 讀 `relay_env_warn` 上方的說明註解與函式本體 | 註解已改字，說明：每個 8 KB 視窗多做一次同形的移除來數壞提到、沒有逐次剝前綴、沒有 `^(.*)`、沒有子行程；函式本體確實是這樣做（沒有逐字元迴圈）；結果記於 `ledger.md` | 手動：閱卷者讀 diff，結果記於 `ledger.md` |

## User Story 4 — 空值說明只看最後一處，超過 64 KB 也說（優先度 P1；發現 5）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-024 | 發現 5；POL-16 前半 | 功能 | 同上 | 送 `P=a P= bash scripts/egress_ctl.sh start`（最後一處是空的） | 警告區含 S | 自動（POL-16a） |
| TC-025 | 發現 5；POL-16 後半 | 功能 | 同上 | 送 `P= P=a bash scripts/egress_ctl.sh start`（前面有空的、最後一處不空） | 警告區**不含** S（舊版會錯誤地說） | 自動（POL-16b） |
| TC-026 | 作法 7、裁決 6；POL-17 | 功能 | 同上 | 送 `P="" bash scripts/egress_ctl.sh start` | 警告區含 S（緊鄰的兩個引號算空值） | 自動（POL-17） |
| TC-027 | 發現 5；POL-19 | 功能 | 新 `envbig` kind `empty70`：`echo ` ＋ （`P=sc7 ` ＋ 112 個 `y` ＋ 空白）×500 ＋ `; P= bash scripts/egress_ctl.sh start`（超過 64 KB，最後一處是空的） | 送出，限時 1500 ms | 警告區含 S；有標頭；閘門仍是 ask | 自動（POL-19） |
| TC-028 | 發現 5；POL-20 | 功能 | 同 TC-027 但最後是 `P=real1` | 送出，限時 1500 ms | 警告區**不含** S；有標頭；閘門仍是 ask | 自動（POL-20） |
| TC-029 | 發現 5「EXTRA 不得去算」；POL-21 | 不在範圍 | 同 TC-027 的形狀，但變數換成 `NF_RELAY_EXTRA_DOMAINS`（最後一處是空的） | 送出，限時 1500 ms | 警告區**不含** S；有標頭；閘門仍是 ask | 自動（POL-21） |
| TC-030 | 作法 1、「EXTRA 不得算空值」；既有 TC-035 | 不在範圍 | 既有斷言 | 跑既有 `TC-035 PEER empty-value sentence kept`（`P= bash …start` 有 S）與 `TC-035 EXTRA has no such sentence`（`E= bash …start` 沒有 `An empty value is ignored by the relay`） | 兩條原樣仍綠 | 自動（既有，不改） |
| TC-031 | 作法 1、7；完成標準（貼 `sed -n`） | 不在範圍 | 本分支 | `sed -n` 取出 `relay_env_warn` 函式本體與 PEER／EXTRA 兩處呼叫 | 設定 `RELAY_ENV_EMPTY=1` 的每一行都在 `[ "$3" = empty ]` 的保護內（含超過 64 KB 的路徑）；PEER 的呼叫多傳 `empty`，EXTRA 的呼叫文字一字不動、不傳；結果記於 `ledger.md` | 手動：閱卷者讀函式本體，結果記於 `ledger.md` |

## User Story 5 — 閘門不變弱、不變慢、只動指定範圍（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 作法 2「O(n)」；POL-22 | 功能 | 新 `envbig` kind `lookalike1m`：`echo ` ＋ （`MY_P=sc7 ` ＋ 90 個 `y` ＋ 空白）×8000 ＋ `; P=tail1 bash scripts/egress_ctl.sh start`（約 1 MB，8000 個壞提到） | 送出，限時 1000 ms | 警告區含 `1 mention in total`、含 `The values are not listed because the command is over 64 KB`；有標頭；閘門仍是 ask；整次 hook 不到 1 秒 | 自動（POL-22） |
| TC-033 | 作法 9；既有 TC-048…051 | 功能 | 既有 `envbig` 迴圈 | 跑 V 各一次的 60 KB 尾端、60 KB 500 處、70 KB 500 處、1 MB 尾端、1 MB 8000 處 | 全部仍綠，**時間上限不放寬**（500／500／1500／1000／1000 ms）；`TC-050` 仍含 `500 mentions in total` 且不含 `sc7`；差異只准是這一行改成 `500 mentions in total.` 加另起的說明行 | 自動（既有，不改限時） |
| TC-034 | 完成標準「成本」；硬規則「不能比現在慢」 | 功能 | 基底（`origin/v3`）與本分支各一份 hook | 用一條約 100 KB、**不含**兩個變數的指令，新舊 hook 各用 `time` 跑；另貼 TC-033 與 TC-032 的毫秒數新舊對照 | 新版不比舊版慢（容許量測誤差）；沒帶變數的指令仍在第一次子字串比對就離開；數字貼進 `ledger.md`，閱卷者自己重量 | 手動：結果記於 `ledger.md` |
| TC-035 | 硬規則「不新增解析器、只用內建」；完成標準（貼 `sed -n`） | 功能 | 本分支 | `sed -n` 取出 `relay_env_warn` 函式本體 | 本體內沒有命令替換 `$(`、沒有 `grep`／`jq`／`python`／子行程；列出階段有步數上限（往前 20 圈、往後 20 圈）；結果記於 `ledger.md` | 手動：閱卷者讀函式本體，結果記於 `ledger.md` |
| TC-036 | 範圍：檔案（只准改 3 個） | 不在範圍 | 本分支 | `git diff --name-only origin/v3...HEAD` | 實作檔只出現 `hooks/confirm_launch.sh`、`tests/confirm_launch_test.sh`、`specs/relay-warning-polish/ledger.md`（計畫與規定的 TC 檔另計）；沒有其他檔 | 手動：閱卷者重跑，結果記於 `ledger.md` |
| TC-037 | 範圍：禁止碰 | 不在範圍 | 本分支 | `git diff origin/v3...HEAD -- scripts/ platform/ docs/ skills/ deploy/ commands/ hooks/hooks.json` | 輸出為空 | 手動：閱卷者重跑，結果記於 `ledger.md` |
| TC-038 | 完成標準「hook diff 只動指定區塊」 | 功能 | 本分支 | 讀 `git diff origin/v3...HEAD -- hooks/confirm_launch.sh` | 被改的既有行只有：`relay_env_warn` 本體與其上方說明註解、PEER 那一次呼叫多一個 `empty` 參數、其後的空值判斷區塊；其餘既有行一字未動 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-039 | 範圍：禁止碰；「不做」第 3 點 | 不在範圍 | 本分支 | 在 diff 與檔案裡找 `ask()`、`RELAY_START_RE`、EXTRA 呼叫的文字、PEER 呼叫的結尾句文字、`hooks/hooks.json` | 這些全都原樣沒動（EXTRA／PEER 的結尾句一字不差） | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-040 | 作法 8「離場行為不變且不更弱」 | 例外 | 本分支 | 讀 diff 數 `allow`、`exit 0`、`ask` 的新增行 | 沒有新增 `allow` 路徑、沒有新增 `exit 0`、沒有新增或移除 `ask` 呼叫；`ask` 仍無條件呼叫，且整條指令仍印在 `permissionDecisionReason` | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-041 | 完成標準「不更弱比對」；repo 校正失敗 #1 | 例外 | 基底 hook 與本分支 hook | 用同一批指令各餵兩份 hook：本檔全部測試指令、`tests/confirm_launch_test.sh` 裡既有的 E／P 指令、`bash scripts/egress_ctl.sh start\|stop\|restart\|status`、`bash scripts/agent_ctl.sh start`、一條 `ls`、TC-021 的反引號指令 | 兩邊的 `permissionDecision` **完全一致**；`permissionDecisionReason` 的第一段（整條指令原文）也一致；逐條對照貼進 `ledger.md` | 手動：閱卷者自己重跑，結果記於 `ledger.md` |
| TC-042 | 完成標準「警告只可能變少、且只少在名字尾巴相同」 | 例外 | 同 TC-041 | 同一批指令，比對是否印出 `THIS COMMAND ALSO MENTIONS <VAR>=` | 新版出現標頭的指令集合是舊版的子集；差集**只有**左邊字元是英數字或底線的那幾條（`MY_…`）；反引號、`(`、引號、`{`、`$` 等形狀沒有任何一條掉出集合 | 手動：閱卷者自己重跑，結果記於 `ledger.md` |
| TC-043 | 完成標準「兩分支各跑一遍」；repo 校正失敗 #1 | 例外 | 基底與本分支 | 兩邊各跑 `bash tests/confirm_launch_test.sh`，輸出存檔逐行比對 | 差異只允許：3 條改字／改期望的既有斷言與新增的 POL 斷言（`-U` 標籤）；其餘每行 ok／FAIL 狀態一致；兩邊貼進 `ledger.md` | 手動：閱卷者自己重跑，結果記於 `ledger.md` |
| TC-044 | 「失敗先行測試」末尾清單；閱卷「不得削弱測試」 | 功能 | 本分支 | `git diff origin/v3...HEAD -- tests/confirm_launch_test.sh` | 被改的既有斷言恰好 3 條：TC-010 雙引號、TC-010 單引號、TC-020（標籤與期望如 TC-011／TC-012／TC-016 所述）；ledger 貼改前／改後；沒有其他既有斷言被刪、放寬或加 skip；`envbig` 的限時一條都沒放寬 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-045 | 完成標準第 1 點 | 功能 | 本分支 | 執行 `bash tests/confirm_launch_test.sh` | 全檔綠（FAIL 數 0），包含全部新增與改過的斷言，以及既有的 "no jq" 區段 | 自動：`tests/confirm_launch_test.sh` |
| TC-046 | 完成標準第 1 點 | 功能 | 本分支，WSL／Linux | 在 WSL 執行 `bash tests/run_all.sh`（見倉庫 CLAUDE.md） | 全套綠（若有失敗，須證明基底同樣失敗且不在本任務範圍，記於 `ledger.md`） | 自動：`tests/run_all.sh` |
| TC-047 | 「不做」第 1 點（不新增斷詞器、引號平衡器、「哪個值會生效」判斷） | 不在範圍 | 本分支 | 讀 `relay_env_warn` 的引號處理與計數段 | 引號處理只看 `x` 開頭的一個引號字元與前 120 字元（有界），沒有逐字元走訪整條指令的迴圈、沒有配對引號的狀態機、沒有判斷哪個值生效或說「takes effect」的新文字；ledger 記一句 | 手動：閱卷者讀函式本體，結果記於 `ledger.md` |
| TC-048 | 「不做」（不對其他環境變數加警告）；既有 TC-059 | 不在範圍 | 既有斷言 | 跑既有 `NF_RELAY_PORT=1 bash scripts/egress_ctl.sh start` 與 `NF_RELAY_EXTRA_NOTE=x bash scripts/egress_ctl.sh start` | 兩條的警告區都**不含** `THIS COMMAND ALSO MENTIONS`（`envw` lacks），原樣仍綠 | 自動（既有，不改） |

## 憲法與安全網

本任務改的是 `hooks/confirm_launch.sh`（受保護路徑）。碰到的條目：安全網「啟動指令要完整顯示並等明確確認」、憲法第 13 條（安全網做不到時要明說，不得悄悄放行）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-049 | 安全網：啟動指令完整顯示並等確認 | 例外 | 同上 | 對「有警告」與「沒警告」的每一種新形狀（`MY_P=x`、`(P=a …)`、引號、反引號、超過 64 KB、1 MB、用完步數上限）都檢查閘門決定 | 每一條都是 `ask`，沒有任何一條因警告變少或走「不列原文」路徑而變成放行（POL-18、TC-008、TC-009、TC-021、TC-032 的 `ask` 檢查合起來涵蓋） | 自動：`tests/confirm_launch_test.sh`（`idg`／`envbig` 的 ask 檢查） |
| TC-050 | 第 13 條（不得悄悄放行；沒有 jq 時仍拒絕） | 例外 | 既有 "no jq" 區段 | 跑 `bash tests/confirm_launch_test.sh` 的 "no jq" 各段 | 全數原樣仍綠；本任務沒有削弱它們的任何斷言 | 自動：`tests/confirm_launch_test.sh`（既有） |

<!--
- 編號不重編；刪掉的案例保留原列並劃線。
- 計畫 POL-1…POL-23 全部對應：POL-1→TC-001，POL-2→TC-004，POL-3→TC-011，POL-4→TC-007，POL-5→TC-016，POL-6→TC-002，POL-7→TC-005，POL-8→TC-006，POL-9→TC-012，POL-10→TC-013，POL-11→TC-003，POL-12→TC-014，POL-13→TC-017，POL-14→TC-018，POL-15→TC-019，POL-16→TC-024／025，POL-17→TC-026，POL-18→TC-020，POL-19→TC-027，POL-20→TC-028，POL-21→TC-029，POL-22→TC-032，POL-23→TC-008。
-->
