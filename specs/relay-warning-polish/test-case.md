# 測試案例：轉送啟動警告的顯示細節（relay-warning-polish）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Language: 繁體中文; identifiers and file paths stay as they are.
本版依計畫的「裁決三」（PR #203 /code-review 後，取消左邊字界）重寫。編號沿用上一版（已確認）的編號；因裁決三失效的案例保留原列並劃線，新增的從 TC-051 起。
-->

**規格**：`specs/relay-warning-polish/plan.md`（本任務沒有 spec.md；計畫含「裁決」「裁決二」「裁決三」，衝突時以裁決三為準，其次裁決二、裁決）　**總覽**：`test-case-overview.md`

名詞（第一次出現就翻譯）：

- **V**：指兩個變數名之一。`E` ＝ `NF_RELAY_EXTRA_DOMAINS`（中繼額外放行的網域清單），`P` ＝ `NF_RELAY_PEER_PREFIXES`（哪些主機可以連中繼的名稱前綴清單）。標「V 各一次」的 TC 對 E、P 兩個都跑；測試命令裡寫 `V=` 時實際是完整變數名。
- **警告區**：hook 回給 AI 的那段文字（`additionalContext`），裡面有 `THIS COMMAND ALSO MENTIONS V=`、`[值]` 清單、`N mention(s) in total`。測試用 `envw`／`envbig` 檢查的就是它。
- **提到**：指令文字裡出現一次 `V=`，**不論左邊是什麼字元**（裁決三：取消「左邊字界」，回到 #196 的規則）。所以 `MY_V=`、`-eV=`（docker／CLI 的黏著選項）、反引號後面的 `V=` 都算一處提到、都警告。
- **S**：PEER 的空值說明句 `An empty value is ignored by the relay, which then uses the deployment's relay_peer_prefixes setting.`
- **X120**：120 個 `x`。
- **手動**：依 `memory/dev-plans/README.md`「通例：閱卷看 diff」，證據貼進 `specs/relay-warning-polish/ledger.md`，閱卷者自己重跑核對；不寫進 `docs/TESTING.md`，也不得以「TESTING.md 沒有步驟」退回。
- 自動測試都放 `tests/confirm_launch_test.sh`，新增的標籤前綴 `POL-`；改過的既有斷言保留原標籤。「既有」＝計畫沒說要改、必須原樣仍綠的斷言（含 `TC-020 … MY_ prefix still warns`，它在裁決三後**不改**）。
- 標「（推導）」的案例：計畫沒給命令或期望，但規則白紙黑字，期望只由規則的字面推出，見總覽「不確定的地方」。

類型只有三種：**功能**（計畫說要做到的事做到了）、**例外**（出錯或可能變弱時系統怎麼反應）、**不在範圍**（計畫明講不做的事，確認真的沒做）。

## User Story 1 — 被截掉或沒列出的地方要標出來（優先度 P1；發現 1、2、4）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 發現 1；POL-1 | 功能 | hook 與測試設定同既有 `envw` | V 各一次：送 `V=<X120>yy bash scripts/egress_ctl.sh start`（值是 120 個 x 再加 `yy`） | 警告區含 `<X120>…]`（120 個 x 後面緊接 `…` 再接 `]`），**不含** `<X120>y`；有標頭 | 自動：`tests/confirm_launch_test.sh`（POL-1） |
| TC-002 | 發現 1；POL-6 | 功能 | 同上 | 送 `P=a"b c d bash scripts/egress_ctl.sh start`（引號沒關，在空白處被切） | 警告區含 `[a"b…]` | 自動（POL-6） |
| TC-003 | 發現 1；POL-11 | 功能 | 同上 | 送 `P="a b; c bash scripts/egress_ctl.sh start`（引號沒關，在分號處被切） | 警告區含 `["a…]` | 自動（POL-11） |
| TC-004 | 發現 2；POL-2 | 功能 | 同上 | V 各一次：送 `V=m1x V=m2x V=m3x V=m4x V=m5x bash scripts/egress_ctl.sh start`（5 處） | 警告區含一行 `(mention 4 is not listed; read the whole command shown below)` | 自動（POL-2） |
| TC-005 | 發現 2；POL-7 | 功能 | 同上 | 送 P 的 6 處提到（`P=m1x … P=m6x bash scripts/egress_ctl.sh start`） | 警告區含 `(mentions 4 to 5 are not listed; read the whole command shown below)` | 自動（POL-7） |
| TC-006 | 發現 2；POL-8 | 功能 | 同上 | 送 P 的 4 處提到 | 警告區**不含** `are not listed`、也**不含** `is not listed`（4 處全列，不多說） | 自動（POL-8） |
| TC-007 | 發現 4；POL-4 | 功能 | 同既有 `envbig`（沿用 `spread70`：約 70 KB、500 處提到） | V 各一次：送 `spread70`，限時 1500 ms | 警告區含 `The values are not listed because the command is over 64 KB; read the whole command shown below.`、含 `500 mentions in total`、**不含** `sc7`（值沒被列）；有標頭；閘門仍是 ask | 自動（POL-4，`envbig`） |
| ~~TC-008~~ | ~~作法 3 步數上限；POL-23~~ | ~~例外~~ | 裁決三 1：刪除「too many names」路徑 | 取消，由 TC-051 取代 | 不再測；hook 與測試檔裡都不應再有 `too many names` 這串字（見 TC-022） | 取消 |
| ~~TC-009~~ | ~~作法 3 往後掃用完 20 圈~~ | ~~例外~~ | 裁決三 1：刪除往前／往後 20 圈的掃描 | 取消 | 不再測 | 取消 |
| TC-010 | 作法 5「顯示格式不變」；既有 TC-015/016/017/018/019/021 | 功能 | 既有斷言 | 跑既有的 1 處、4 處、5 處、6 處、超過 120 字元、E＋P 同時提到的指令 | 既有斷言**原樣**仍綠：`Text after each V= as written (first 3 and last 1 of them): …; N mention(s) in total.` 這一行格式沒變；4 處全列、5 處第 4 處不列、6 處第 4、5 處不列；兩個變數的區塊順序不變 | 自動（既有，不改） |
| TC-051 | 裁決三 1（推導；取代原 POL-23） | 例外 | 新 `envbig` kind `lookalike25`：`echo ` ＋ 25 個 `MY_P=x ` ＋ `; P=real1 bash scripts/egress_ctl.sh start`（約 1 KB） | 送出，限時 500 ms | 警告區含 `26 mentions in total`（`MY_P=` 也各算一處）、含 `[real1]`（最後一處照列）、含 `(mentions 4 to 25 are not listed; read the whole command shown below)`，**不含** `too many names`；有標頭；閘門仍是 ask | 自動（標籤 `POL-lk25`） |

## User Story 2 — 引號裡的值要整個顯示（優先度 P1；發現 3；裁決三 2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 發現 3；POL-3；既有 TC-010 雙引號改期望 | 功能 | 同上 | V 各一次：送 `V="qq1 rr2" bash scripts/egress_ctl.sh start` | 警告區含 `["qq1 rr2"]`（引號原樣保留、顯示到收尾引號），**不含** `"qq1 rr2"…`（值沒被截）。既有 `TC-010 … double-quoted value kept as written` 的檢查從 `'"qq1'` 加 `!qq1 rr2` 改成 `'"qq1 rr2"'` | 自動（POL-3 ＋改後的 TC-010） |
| TC-012 | 發現 3；POL-9；既有 TC-010 單引號改期望 | 功能 | 同上 | 送 `P='qq1 rr2' bash scripts/egress_ctl.sh start`；以及既有 TC-010 的 E、P 兩個單引號案例 | 警告區含 `['qq1 rr2']`；既有 `TC-010 … single-quoted value kept as written` 的檢查改成 `"'qq1 rr2'"` | 自動（POL-9 ＋改後的 TC-010） |
| TC-013 | 發現 3＋1；POL-10 | 功能 | 同上 | 送 `P="` ＋ 200 個 `x` ＋ `" bash scripts/egress_ctl.sh start`（引號內的值超過 120 字元） | 警告區含 `"` ＋ 119 個 `x` ＋ `…]`（共 120 字元：引號加 119 個 x，然後 `…`） | 自動（POL-10） |
| TC-014 | 發現 3；POL-12 | 功能 | 同上 | 送 `P="a b"c bash scripts/egress_ctl.sh start`（收尾引號後面緊接字） | 警告區含 `["a b"…]`（值還在繼續，所以加 `…`） | 自動（POL-12） |
| TC-015 | 「不做」第 2 點（不去跳脫、不展開）；作法 5 | 不在範圍 | 既有斷言 | 跑既有 TC-010 `V=a\"b c`、TC-011 `V=$(cat /tmp/p)`（不加引號與加引號兩種）、TC-012 `V=$P` | 既有斷言**原樣**仍綠：`a\"b` 照字面顯示且**不含** `a\"b c`（多出一個 `…` 是計畫接受的誤差）；`$(cat` 照字面顯示，不含 `$(cat /tmp/p)`（不加引號時）、不含 `computed at run time`；`$P` 照字面顯示。沒有任何展開、去引號、跳脫處理 | 自動（既有，不改） |
| TC-053 | 裁決三 2（推導） | 功能 | 同上 | 送 `(echo P="a b"); bash scripts/egress_ctl.sh start`（收尾引號後面緊接 `)`） | 警告區含 `["a b"]`，**不含** `"a b"…`（`)` 也算值結束，不加 `…`） | 自動（標籤 `POL-cl1`） |
| TC-054 | 裁決三 2（推導） | 功能 | 同上 | 送 ``echo `echo P="a b"`; bash scripts/egress_ctl.sh start``（收尾引號後面緊接反引號） | 警告區含 `["a b"]`，**不含** `"a b"…` | 自動（標籤 `POL-cl2`） |
| TC-055 | 裁決三 2（推導） | 功能 | 同上 | 送 `echo ${x:-P="a b"}; bash scripts/egress_ctl.sh start`（收尾引號後面緊接 `}`） | 警告區含 `["a b"]`，**不含** `"a b"…` | 自動（標籤 `POL-cl3`） |

## User Story 3 — 所有 `V=` 都警告，包括名字尾巴相同與黏著選項（優先度 P1；發現 6 被裁決三取消）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 裁決三 1；POL-5（翻轉）；既有 TC-020 恢復 | 功能 | 同上 | V 各一次：送 `MY_V=zzval bash scripts/egress_ctl.sh start` | 警告區**有** `THIS COMMAND ALSO MENTIONS V=`、含 `[zzval]`（`MY_` 多警告一次是可接受的）。既有 `TC-020 … MY_ prefix still warns`（期望 has、標籤）**一字不改**，仍綠 | 自動（POL-5 ＋既有 TC-020） |
| TC-017 | POL-13 | 功能 | 同上 | 送 `(P=a bash scripts/egress_ctl.sh start)` | 有警告 | 自動（POL-13） |
| TC-018 | POL-14 | 功能 | 同上 | 送 `echo "P=a"; bash scripts/egress_ctl.sh start` | 有警告 | 自動（POL-14） |
| TC-019 | POL-15（期望由裁決三改，推導） | 功能 | 同上 | 送 `MY_P=bad P=good bash scripts/egress_ctl.sh start` | 有警告；含 `[bad]`、含 `[good]`、含 `2 mentions in total`（兩處都是提到，都列） | 自動（POL-15） |
| TC-020 | 作法 8；POL-18；既有 TC-030/038/039/040 | 例外 | 同上 | 送 `MY_P=x bash scripts/egress_ctl.sh start`；並跑既有「沒提到但仍詢問」「誘餌仍詢問」等 `idg` 斷言 | 閘門決定是 `ask`；既有 `idg` 斷言原樣仍綠 | 自動（POL-18 ＋既有） |
| TC-021 | 裁決三 1（反引號型不得變弱；推導） | 例外 | 同上 | V 各一次：送 ``` `V=x bash scripts/egress_ctl.sh start` ```（整條包在反引號裡，`V=` 左邊是反引號） | 有警告、含標頭；閘門仍是 ask | 自動（標籤 `POL-bq`） |
| TC-022 | 裁決三 1（刪除左邊字界機制） | 功能 | 本分支 diff 對 `origin/v3`（#196 已合入） | 讀 `git diff origin/v3...HEAD -- hooks/confirm_launch.sh tests/confirm_launch_test.sh`，並在兩個檔裡搜 `too many names`、`nbad`、`[a-zA-Z0-9_]"$V="`、視窗內第二次移除 | `relay_env_warn` 的計次仍是 base 的單一 `${x//"$V="/}` 視窗移除，沒有第二次壞提到計數、沒有往前／往後跳過壞提到的掃描、沒有 20 圈步數上限、沒有 `too many names` 路徑；測試檔裡沒有 POL-23 的 `too many names` 斷言；結果記於 `ledger.md` | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-023 | 發現 6 被取消後的函式說明；「仍須 O(n)」 | 功能 | 本分支 diff | 讀 `relay_env_warn` 上方的說明註解與函式本體 | 註解已改字：不再有「左邊鄰居是字母數字底線就不算」的段落；說明引號規則（`"`／`'` 開頭顯示到收尾引號、只往後看 119 字元；其餘到空白或 `; & \|`）、`…` 的條件、4～N-1 處沒列的說明、64 KB 以上的行為；函式本體沒有逐字元迴圈、沒有逐次剝前綴；結果記於 `ledger.md` | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-052 | 裁決三 1（黏著選項 `-e<VAR>=`；推導命令形狀） | 例外 | 同上 | V 各一次：送 `-eV=evil bash scripts/egress_ctl.sh start`（`V=` 左邊是字母 `e`） | 有警告、含標頭、含 `[evil]`、含 `1 mention in total`；閘門仍是 ask（這是裁決三要消除的「安全網變弱」） | 自動（標籤 `POL-dash-e`） |

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
| TC-056 | 裁決三 2（推導） | 功能 | 同上 | 送 `(echo P=""); bash scripts/egress_ctl.sh start`（`""` 後面緊接 `)`） | 警告區含 S（這種情況下 `""` 仍算空值） | 自動（標籤 `POL-cl4`） |
| TC-057 | 裁決三 1（取消字界後最後一處就是文字上最後的 `V=`；推導） | 功能 | 同上 | 送 `MY_P= bash scripts/egress_ctl.sh start` | 有警告、警告區含 S（最後一處是空的，左邊是什麼不影響） | 自動（標籤 `POL-lk-empty`） |
| TC-058 | 裁決三 1，64 KB 以上的路徑（推導） | 功能 | 新 `envbig` kind：`echo ` ＋ （`P=sc7 ` ＋ 112 個 `y` ＋ 空白）×500 ＋ `; MY_P= bash scripts/egress_ctl.sh start`（超過 64 KB，最後一處的名字帶 `MY_`） | 送出，限時 1500 ms | 警告區含 S；有標頭；閘門仍是 ask（舊設計會因左邊是 `_` 而不說） | 自動（標籤 `POL-19b`） |

## User Story 5 — 閘門不變弱、不變慢、只動指定範圍（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 作法「O(n)」；POL-22（期望由裁決三改，推導） | 功能 | 新 `envbig` kind `lookalike1m`：`echo ` ＋ （`MY_P=sc7 ` ＋ 90 個 `y` ＋ 空白）×8000 ＋ `; P=tail1 bash scripts/egress_ctl.sh start`（約 1 MB） | 送出，限時 1000 ms | 警告區含 `8001 mentions in total`（`MY_P=` 都算）、含 `The values are not listed because the command is over 64 KB`；有標頭；閘門仍是 ask；整次 hook 不到 1 秒 | 自動（POL-22） |
| TC-033 | 作法 9；既有 TC-048…051 | 功能 | 既有 `envbig` 迴圈 | 跑 V 各一次的 60 KB 尾端、60 KB 500 處、70 KB 500 處、1 MB 尾端、1 MB 8000 處 | 全部仍綠，**時間上限不放寬**（500／500／1500／1000／1000 ms）；`TC-050` 仍含 `500 mentions in total` 且不含 `sc7`；差異只准是這一行改成 `500 mentions in total.` 加另起的說明行 | 自動（既有，不改限時） |
| TC-034 | 完成標準「成本」；硬規則「不能比現在慢」 | 功能 | 基底（`origin/v3`）與本分支各一份 hook | 用一條約 100 KB、**不含**兩個變數的指令，新舊 hook 各用 `time` 跑；另貼 TC-033 與 TC-032 的毫秒數新舊對照 | 新版不比舊版慢（容許量測誤差）；沒帶變數的指令仍在第一次子字串比對就離開；數字貼進 `ledger.md`，閱卷者自己重量 | 手動：結果記於 `ledger.md` |
| TC-035 | 硬規則「不新增解析器、只用內建」；完成標準（貼 `sed -n`） | 功能 | 本分支 | `sed -n` 取出 `relay_env_warn` 函式本體 | 本體內沒有命令替換 `$(`、沒有 `grep`／`jq`／`python`／子行程；沒有逐字元走訪整條指令的迴圈；結果記於 `ledger.md` | 手動：閱卷者讀函式本體，結果記於 `ledger.md` |
| TC-036 | 範圍：檔案（只准改 3 個） | 不在範圍 | 本分支 | `git diff --name-only origin/v3...HEAD` | 實作檔只出現 `hooks/confirm_launch.sh`、`tests/confirm_launch_test.sh`、`specs/relay-warning-polish/ledger.md`（計畫與規定的 TC 檔另計）；沒有其他檔 | 手動：閱卷者重跑，結果記於 `ledger.md` |
| TC-037 | 範圍：禁止碰 | 不在範圍 | 本分支 | `git diff origin/v3...HEAD -- scripts/ platform/ docs/ skills/ deploy/ commands/ hooks/hooks.json` | 輸出為空 | 手動：閱卷者重跑，結果記於 `ledger.md` |
| TC-038 | 完成標準「hook diff 只動指定區塊」 | 功能 | 本分支 | 讀 `git diff origin/v3...HEAD -- hooks/confirm_launch.sh` | 被改的既有行只有：`relay_env_warn` 本體與其上方說明註解、PEER 那一次呼叫多一個 `empty` 參數、其後的空值判斷區塊；其餘既有行一字未動 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-039 | 範圍：禁止碰；「不做」第 3 點 | 不在範圍 | 本分支 | 在 diff 與檔案裡找 `ask()`、`RELAY_START_RE`、EXTRA 呼叫的文字、PEER 呼叫的結尾句文字、`hooks/hooks.json` | 這些全都原樣沒動（EXTRA／PEER 的結尾句一字不差） | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-040 | 作法 8「離場行為不變且不更弱」 | 例外 | 本分支 | 讀 diff 數 `allow`、`exit 0`、`ask` 的新增行 | 沒有新增 `allow` 路徑、沒有新增 `exit 0`、沒有新增或移除 `ask` 呼叫；`ask` 仍無條件呼叫，且整條指令仍印在 `permissionDecisionReason` | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-041 | 完成標準「不更弱比對」；repo 校正失敗 #1 | 例外 | 基底 hook 與本分支 hook | 用同一批指令各餵兩份 hook：本檔全部測試指令、`tests/confirm_launch_test.sh` 裡既有的 E／P 指令、`bash scripts/egress_ctl.sh start\|stop\|restart\|status`、`bash scripts/agent_ctl.sh start`、一條 `ls`、TC-021 的反引號指令、TC-052 的 `-eV=evil` 指令 | 兩邊的 `permissionDecision` **完全一致**；`permissionDecisionReason` 的第一段（整條指令原文）也一致；逐條對照貼進 `ledger.md` | 手動：閱卷者自己重跑，結果記於 `ledger.md` |
| TC-042 | 裁決三 1「警告出現與否不比 #196 少」 | 例外 | 同 TC-041 | 同一批指令，比對是否印出 `THIS COMMAND ALSO MENTIONS <VAR>=` | 新版出現標頭的指令集合與舊版**完全相同**（裁決三取消字界後沒有任何指令掉出集合，連 `MY_…` 也還在）；反引號、`(`、引號、`{`、`$`、`-e` 形狀都沒掉；差集為空 | 手動：閱卷者自己重跑，結果記於 `ledger.md` |
| TC-043 | 完成標準「兩分支各跑一遍」；repo 校正失敗 #1 | 例外 | 基底與本分支 | 兩邊各跑 `bash tests/confirm_launch_test.sh`，輸出存檔逐行比對 | 差異只允許：2 條改字的既有斷言（TC-010 雙引號、單引號）與新增的 POL 斷言；其餘每行 ok／FAIL 狀態一致（`TC-020 … MY_ prefix still warns` 兩邊同為 ok）；兩邊貼進 `ledger.md` | 手動：閱卷者自己重跑，結果記於 `ledger.md` |
| TC-044 | 「失敗先行測試」末尾清單（裁決三後剩 2 條）；閱卷「不得削弱測試」 | 功能 | 本分支 | `git diff origin/v3...HEAD -- tests/confirm_launch_test.sh` | 被改的既有斷言恰好 2 條：TC-010 雙引號、TC-010 單引號（如 TC-011／TC-012 所述）；`TC-020` 那一行與 base 一字不差；ledger 貼改前／改後；沒有其他既有斷言被刪、放寬或加 skip；`envbig` 的限時一條都沒放寬 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-045 | 完成標準第 1 點 | 功能 | 本分支 | 執行 `bash tests/confirm_launch_test.sh` | 全檔綠（FAIL 數 0），包含全部新增與改過的斷言，以及既有的 "no jq" 區段 | 自動：`tests/confirm_launch_test.sh` |
| TC-046 | 完成標準第 1 點 | 功能 | 本分支，WSL／Linux | 在 WSL 執行 `bash tests/run_all.sh`（見倉庫 CLAUDE.md） | 全套綠（若有失敗，須證明基底同樣失敗且不在本任務範圍，記於 `ledger.md`） | 自動：`tests/run_all.sh` |
| TC-047 | 「不做」第 1 點（不新增斷詞器、引號平衡器、「哪個值會生效」判斷） | 不在範圍 | 本分支 | 讀 `relay_env_warn` 的引號處理與計數段 | 引號處理只看 `x` 開頭的一個引號字元與前 120 字元（有界），沒有逐字元走訪整條指令的迴圈、沒有配對引號的狀態機、沒有判斷哪個值生效或說「takes effect」的新文字；ledger 記一句 | 手動：閱卷者讀函式本體，結果記於 `ledger.md` |
| TC-048 | 「不做」（不對其他環境變數加警告）；既有 TC-059 | 不在範圍 | 既有斷言 | 跑既有 `NF_RELAY_PORT=1 bash scripts/egress_ctl.sh start` 與 `NF_RELAY_EXTRA_NOTE=x bash scripts/egress_ctl.sh start` | 兩條的警告區都**不含** `THIS COMMAND ALSO MENTIONS`（`envw` lacks），原樣仍綠 | 自動（既有，不改） |
| TC-059 | 裁決三 3 | 功能 | 本分支 diff | 讀 `relay_env_warn` 上方註解與 `LC_ALL=C` 附近 | 註解明寫「超過 64 KB 的判斷以位元組計（`LC_ALL=C`）」；`${#CMD} -gt 65536` 的判斷與 base 相同（沒有另修）；結果記於 `ledger.md` | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-060 | 裁決三 4（不處理 `\"`） | 不在範圍 | 本分支 | 讀 `ledger.md`；並確認函式本體沒有任何處理反斜線跳脫的程式 | `ledger.md` 記一句「跳脫引號 `\"` 不處理，為已知顯示限制（閘門仍印整條指令）」；hook 裡沒有處理 `\\` 的新程式；既有 `a\"b c` 斷言（TC-015）仍綠 | 手動：閱卷者讀 ledger 與函式本體，結果記於 `ledger.md` |

## 憲法與安全網

本任務改的是 `hooks/confirm_launch.sh`（受保護路徑）。碰到的條目：安全網「啟動指令要完整顯示並等明確確認」、憲法第 13 條（安全網做不到時要明說，不得悄悄放行）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-049 | 安全網：啟動指令完整顯示並等確認 | 例外 | 同上 | 對「有警告」的每一種新形狀（`MY_P=x`、`-eP=evil`、`(P=a …)`、引號、反引號、超過 64 KB、1 MB、25 個 `MY_P=x` 加一個 `P=real1`）都檢查閘門決定 | 每一條都是 `ask`，沒有任何一條因顯示變動而變成放行（POL-18、TC-051、TC-052、TC-021、TC-032 的 `ask` 檢查合起來涵蓋） | 自動：`tests/confirm_launch_test.sh`（`idg`／`envbig` 的 ask 檢查） |
| TC-050 | 第 13 條（不得悄悄放行；沒有 jq 時仍拒絕） | 例外 | 既有 "no jq" 區段 | 跑 `bash tests/confirm_launch_test.sh` 的 "no jq" 各段 | 全數原樣仍綠；本任務沒有削弱它們的任何斷言 | 自動：`tests/confirm_launch_test.sh`（既有） |

<!--
- 編號不重編；刪掉的案例保留原列並劃線（TC-008、TC-009 因裁決三取消）。
- 計畫 POL 對應：POL-1→TC-001，POL-2→TC-004，POL-3→TC-011，POL-4→TC-007，POL-5→TC-016（翻轉為 has），POL-6→TC-002，POL-7→TC-005，POL-8→TC-006，POL-9→TC-012，POL-10→TC-013，POL-11→TC-003，POL-12→TC-014，POL-13→TC-017，POL-14→TC-018，POL-15→TC-019（期望改），POL-16→TC-024／025，POL-17→TC-026，POL-18→TC-020，POL-19→TC-027，POL-20→TC-028，POL-21→TC-029，POL-22→TC-032（期望改），POL-23→取消（TC-008 劃線，命令改由 TC-051 測）。
- 裁決三：1→TC-016、019、021、022、042、052、057、058；2→TC-053、054、055、056；3→TC-059；4→TC-060；5（不再開新的顯示修正）無可測項。
-->
