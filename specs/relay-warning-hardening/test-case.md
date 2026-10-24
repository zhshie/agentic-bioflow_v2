# 測試案例：中繼啟動閘門對 NF_RELAY_EXTRA_DOMAINS= / NF_RELAY_PEER_PREFIXES= 的警告補強（relay-warning-hardening）

<!--
Written by the verifier (CONTRACT mode) from specs/relay-warning-hardening/plan.md, before any code.
第二版（2026-10-24）：計畫經 PR #196 的 /code-review 後重做，新增「裁決三」「裁決四」（只看啟動點那一段、逐字元切段、無回溯正則、64 KB／50 段上限、審查 8 點）。
第一版 TC-012（賦值超過 20 個）、TC-019（啟動點超過 8 個）、TC-042（迴圈上限 8／20）的依據已被裁決三／四取消，保留列號並劃掉。其餘第一版 TC 編號與意義不變；新 TC 從 TC-054 起。
這個任務沒有 spec.md；依據是 plan.md（A 級、backend）。維護者原話與範例引自計畫「維護者原話」「失敗先行測試」（RWH-1…RWH-21）與裁決四的審查 8 點。
-->

**規格**：`specs/relay-warning-hardening/plan.md`（本任務沒有 spec.md；以裁決四為最高，其次裁決三，其次裁決二、裁決，最後才是作法）　**總覽**：`test-case-overview.md`

白話說明：中繼（relay）是登入節點上替運算節點轉送對外連線的常駐程式。閘門（`hooks/confirm_launch.sh`）在有人要啟動它時會停下來問使用者「要不要允許」。如果那行指令自己帶了 `NF_RELAY_EXTRA_DOMAINS=…`（多放行哪些網域）或 `NF_RELAY_PEER_PREFIXES=…`（哪些主機名開頭的機器可以連進中繼），問話文字裡要有一句警告，把「真正會生效的值」講給使用者聽。這次要補的是：警告只看「啟動中繼的那一段指令」，不能被一句 `echo`、一段註解、另一條 on_site.sh 指令騙過去；顯示的值要乾淨、要說真話；兩個變數共用同一段程式；而且這段程式要夠便宜（hook 逾時＝放行，所以不能慢）。

名詞：「ask」＝閘門停下來問；「警告句」＝問話文字裡 `THIS COMMAND ALSO SETS …` 那一段；「V」＝`NF_RELAY_EXTRA_DOMAINS` 與 `NF_RELAY_PEER_PREFIXES` 兩個變數各跑一次（兩條斷言，兩條都要綠）；「命令段」＝指令被 `; & | ( ) 換行 反引號` 切開後的一段（引號內、`$( )` 內的這些符號不切）；「前綴」＝命令段開頭那串 `VAR=值`（或 `env VAR=值`）；「主角值」＝警告句 `SETS V=…` 顯示的那個值；「mentions 句」＝`This command also mentions V= elsewhere (not as the value the relay gets); read the whole command.`（V 代入實際變數名）；「not parsed 標頭」＝`THIS COMMAND ALSO SETS V (not parsed: the command is too long or has too many parts); read the whole command.`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：邊角情況或不該被放行／不該被藏掉的情況，系統怎麼反應（照樣詢問、照樣警告、不誤報）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

測試輔助函式約定（來自計畫）：`envw <label> <變數> <has|lacks> <指令> [必含字串]` 判的是**該變數自己的警告句** `THIS COMMAND ALSO SETS ${V}` 有沒有出現，並可附一個必含字串；本檔多條 TC 另需「必不含字串」，由 executor 在 `envw` 加反向字串（計畫 RWH-21 已預告這個需要）。`idg` 是既有函式，期望 `ask`；`envq_txt` 是既有函式，比對詢問文字含某固定字串。注意詢問文字**也會把使用者的指令原文印出來**，所以比對「值」時一律用帶 `SETS V=` 或 `assigns V` 的完整字串，不能只找裸值。以下指令中的 `V` 一律代入實際變數名；`ok`、`evil` 是任意值。「手動」＝依 `memory/dev-plans/README.md`「通例：閱卷看 diff」，證據貼進 `specs/relay-warning-hardening/ledger.md`，閱卷者自己重跑核對（不寫進 `docs/TESTING.md`）。每條「自動」測試要在註解裡寫它的 TC 編號。

## User Story 1 — 警告顯示真正會生效的值（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 發現 1；RWH-1（誘餌 echo） | 功能 | 閘門已安裝；部署設定檔照 `id_env.yaml` | 對 V 各送出 `echo V=ok; V=evil bash scripts/egress_ctl.sh start` | 詢問文字含該變數的警告句，且主角值是啟動那一段的 `evil`：含 `SETS V=evil`（不是 echo 裡的 `ok`） | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-002 | 發現 1；RWH-2（同段多重賦值） | 功能 | 同上 | 對 V 各送出 `V=ok V=evil bash scripts/egress_ctl.sh start` | 詢問文字含 `SETS V=evil`，且含 `assigns V 2 times: ok \| evil` | 自動：同上 |
| TC-003 | 作法 4／裁決四 5「最多列 5 個，隱藏時第一個和最後一個一定顯示」；原 RWH-22（改版） | 功能 | 同上 | 對 PEER 變數送出 `NF_RELAY_PEER_PREFIXES=a1 NF_RELAY_PEER_PREFIXES=a2 NF_RELAY_PEER_PREFIXES=a3 NF_RELAY_PEER_PREFIXES=a4 NF_RELAY_PEER_PREFIXES=a5 NF_RELAY_PEER_PREFIXES=a6 NF_RELAY_PEER_PREFIXES=a7 bash scripts/egress_ctl.sh start`（同段 7 個賦值） | 含 `SETS NF_RELAY_PEER_PREFIXES=a7`、`assigns NF_RELAY_PEER_PREFIXES 7 times:`；在那一行 assigns 句裡（不是指令原文那行）同時看得到第一個 `a1` 與最後一個 `a7`；含 `earlier ones not shown`。本條不鎖其餘中間值怎麼列、隱藏數字是幾（計畫未定，見總覽疑問 2） | 自動：`tests/confirm_launch_test.sh`（只對 PEER 一條，共用函式） |
| TC-004 | 發現 3；RWH-3（雙引號） | 功能 | 同上 | 對 V 各送出 `V="a,b" bash scripts/egress_ctl.sh start` | 含 `SETS V=a,b`（值外面沒有引號） | 自動：同上 |
| TC-005 | 發現 3；RWH-4（引號內有空白） | 功能 | 同上 | 對 V 各送出 `V="a b" bash scripts/egress_ctl.sh start` | 含 `SETS V=a b`（空白之後沒有被截斷） | 自動：同上 |
| TC-006 | 發現 3；RWH-5（單引號） | 功能 | 同上 | 對 V 各送出 `V='a,b' bash scripts/egress_ctl.sh start` | 含 `SETS V=a,b`（沒有引號） | 自動：同上 |
| TC-007 | 作法 4「顯示只取前 200 字元」；原 RWH-23 | 功能 | 同上 | 對 PEER 變數送出值為 250 個 `x` 的指令：`NF_RELAY_PEER_PREFIXES=<250 個 x> bash scripts/egress_ctl.sh start` | 警告句含 `SETS NF_RELAY_PEER_PREFIXES=` 後接恰好 200 個 `x` 再接 `…`；警告句內不含連續 201 個 `x`（只檢查 `SETS` 那行，因為詢問文字另外會印指令原文） | 自動：同上（只對 PEER 一條） |
| TC-008 | 發現 3；RWH-13（未加引號的命令替換） | 功能 | 同上 | 對 V 各送出 `V=$(cat /tmp/p) bash scripts/egress_ctl.sh start` | 含 `value is computed at run time: $(cat`（照抄被截斷的字面，並說明值是執行時才算出） | 自動：同上 |
| TC-009 | 作法 4「括號內補 cut at the first space」；原 RWH-24 | 功能 | 同上 | 對 PEER 變數送出 `NF_RELAY_PEER_PREFIXES=$(cat /tmp/p) bash scripts/egress_ctl.sh start` | 含 `cut at the first space; read the command` | 自動：同上（只對 PEER 一條） |
| TC-010 | 發現 3；RWH-14（加引號的命令替換） | 功能 | 同上 | 對 V 各送出 `V="$(cat /tmp/p)" bash scripts/egress_ctl.sh start` | 含 `value is computed at run time: $(cat /tmp/p)`（引號內完整字面，已去外層引號） | 自動：同上 |
| TC-011 | 發現 3；「不做」展開 `$VAR`；RWH-15（變數展開） | 功能 | 同上 | 對 V 各送出 `V=$P bash scripts/egress_ctl.sh start` | 含 `value is computed at run time: $P`（照抄字面，沒有被展開） | 自動：同上 |
| ~~TC-012~~ | ~~作法 2「賦值超過 20 個一律警告」；原 RWH-25~~ | ~~例外~~ | | | 已取消：裁決四 9「賦值最多取 20 個」取消。列號保留，不計入統計 | |
| TC-013 | 作法 4「單一賦值時與現行格式一致」 | 功能 | 本分支與 `ledger.md` | 對閘門送出只有一個賦值的 `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh start`，看詢問文字 | 警告句是 `THIS COMMAND ALSO SETS NF_RELAY_PEER_PREFIXES=25a-cpn, which …`，**不含** `assigns`、`times:`、`mentions` 這類多餘句（只有一個賦值、沒有別處提到，就不多說） | 手動：閱卷者自己跑一次，輸出貼進 `ledger.md` |
| TC-054 | 審查點 ⑦；裁決四 7「單引號值一律字面顯示」 | 功能 | 同 TC-001 | 對 V 各送出 `V='$P' bash scripts/egress_ctl.sh start` | 含 `SETS V=$P`；警告句**不含** `computed at run time`（單引號裡的 `$` 在 shell 裡就是字面，不能說成「執行時才算」） | 自動：同上（`envw` has＋反向字串） |
| TC-055 | 審查點 ⑦ | 功能 | 同上 | 對 V 各送出 `V='$(cat /tmp/p)' bash scripts/egress_ctl.sh start` | 含 `SETS V=$(cat /tmp/p)`；警告句**不含** `computed at run time` | 自動：同上 |
| TC-056 | 審查點 ⑤；裁決四 7「相鄰拼接照 shell 規則拼起來」 | 功能 | 同上 | 對 V 各送出 `V="a"b bash scripts/egress_ctl.sh start` | 含 `SETS V=ab`（不是 `a"b` 或 `"a"b`） | 自動：同上 |
| TC-057 | 審查點 ⑤；裁決四 7 | 功能 | 同上 | 對 V 各送出 `V='a b'"c d" bash scripts/egress_ctl.sh start` | 含 `SETS V=a bc d`（單引號與雙引號相鄰拼接、各自去引號、保留引號內空白） | 自動：同上 |
| TC-058 | 裁決四 7「雙引號值含反引號 → 執行時才算」 | 功能 | 同上 | 對 V 各送出 `V="`id`" bash scripts/egress_ctl.sh start`（雙引號內是反引號 id 反引號） | 含 `value is computed at run time: `id``（反引號字面照抄，已去外層雙引號） | 自動：同上 |
| TC-059 | 裁決四 2「切段要認得引號」 | 例外 | 同上 | 對 V 各送出 `V="a;b\|c&d" bash scripts/egress_ctl.sh start`（值在雙引號裡含 `;`、`\|`、`&`；表格內 `\|` 代表直線符號） | 含 `SETS V=a;b\|c&d`（引號裡的分隔符不切段、值沒有被截斷在第一個 `;`） | 自動：同上 |
| TC-060 | 審查點 ⑤；裁決四 5「左邊要有字界」 | 例外 | 同上 | 對 V 各送出 `MY_V=zz bash scripts/egress_ctl.sh start`（`MY_` 接在變數名前面，例如 `MY_NF_RELAY_PEER_PREFIXES=zz`） | 詢問文字**不含** `SETS V=zz`（`MY_V` 是另一個變數，不是 V；不採用為值） | 自動：同上（反向字串） |
| TC-061 | 審查點 ②；裁決四 6（啟動段之後的誘餌） | 例外 | 同上 | 對 V 各送出 `V=ok bash scripts/egress_ctl.sh start; echo V=evil` | 含 `SETS V=ok`；**不含** `SETS V=evil`（啟動點之後的 echo 不能改掉標題） | 自動：同上 |
| TC-062 | 審查點 ②；裁決四 5、6 | 例外 | 同上 | 對 V 各送出 `V=ok bash scripts/egress_ctl.sh start; export V=evil` | 含 `SETS V=ok`；**不含** `SETS V=evil`（啟動段**之後**的 export 不算值的來源） | 自動：同上 |
| TC-063 | 裁決四 6（註解裡提到）；審查點 ② | 例外 | 同上 | 對 V 各送出 `V=ok bash scripts/egress_ctl.sh start # V=evil` | 含 `SETS V=ok`；**不含** `SETS V=evil` | 自動：同上 |
| TC-064 | 裁決四 6 | 功能 | 同上 | 對 V 各送出 TC-001 的指令 `echo V=ok; V=evil bash scripts/egress_ctl.sh start` | 詢問文字含完整的 mentions 句：`This command also mentions V= elsewhere (not as the value the relay gets); read the whole command.`（V 代入實際變數名） | 自動：同上 |
| TC-065 | 裁決四 6；作法 4「單一賦值與現行一致」 | 功能 | 同上 | 對 V 各送出 `V=ok bash scripts/egress_ctl.sh start` | 詢問文字**不含** `also mentions V=`（沒有別處提到就不多說） | 自動：同上（反向字串） |
| TC-066 | 裁決四 6（引號字串裡提到） | 功能 | 同上 | 對 V 各送出 `echo 'V=zz'; bash scripts/egress_ctl.sh start`（啟動段沒有前綴，V= 只在 echo 的引號字串裡） | 詢問文字含 mentions 句；閘門仍 ask。本條不鎖標頭是否出現（計畫未定，見總覽疑問 1） | 自動：同上 |
| TC-067 | 裁決四 3、5（`env` 前導） | 功能 | 同上 | 對 V 各送出 `env V=evil bash scripts/egress_ctl.sh restart` | 含 `SETS V=evil` | 自動：同上 |
| TC-068 | 裁決四 5(b)（啟動段之前任一段的 export） | 功能 | 同上 | 對 V 各送出 `export V=a; echo hi; bash scripts/egress_ctl.sh start` | 含 `SETS V=a`（不要求 export 緊貼啟動段） | 自動：同上 |
| TC-069 | 裁決四 5「兩者都算，以實際生效順序的最後一個為主角，全部列出」 | 功能 | 同上 | 對 V 各送出 `export V=a; V=b bash scripts/egress_ctl.sh start` | 含 `SETS V=b` 與 `assigns V 2 times: a \| b` | 自動：同上 |
| TC-070 | 裁決四 2「切段要認得 `$( )`」；裁決四 6 | 例外 | 同上 | 對 V 各送出 `echo $(true; V=evil bash scripts/egress_ctl.sh start)`（啟動藏在 `$( )` 裡，`$( )` 內的 `;` 不切段） | 閘門 ask，且詢問文字含 mentions 句（這個 `V=evil` 不在啟動段的前綴，不採用為值，但要告訴使用者去讀整條指令） | 自動：同上 |

## User Story 2 — 豁免縮窄：只有「啟動本身經 on_site.sh」才免警告（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 發現 2；RWH-6（on_site.sh 出現在別的命令） | 例外 | 閘門已安裝；設定檔照 `id_env.yaml` | 對 V 各送出 `bash scripts/on_site.sh status; V=evil bash scripts/egress_ctl.sh start` | 詢問文字含該變數的警告句（`;` 把 on_site.sh 隔在別的命令段，不能豁免） | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-015 | 發現 2；RWH-7（尾端註解） | 例外 | 同上 | 對 V 各送出 `V=evil bash scripts/egress_ctl.sh start # on_site.sh` | 含警告句（該段的命令是 egress_ctl.sh，註解不算） | 自動：同上 |
| TC-016 | 發現 2；RWH-8（上一行的註解） | 例外 | 同上 | 對 V 各送出兩行指令：第一行 `# on_site.sh`，換行後第二行 `V=evil bash scripts/egress_ctl.sh start`（以 `$'# on_site.sh\nV=evil bash scripts/egress_ctl.sh start'` 組出） | 含警告句（換行是命令段邊界） | 自動：同上 |
| TC-017 | 發現 2；裁決四 4；RWH-9（on_site.sh 的引號負載） | 例外 | 同上 | 對 V 各送出 `scripts/on_site.sh 'V=evil bash scripts/egress_ctl.sh start'` | 含警告句標頭 `THIS COMMAND ALSO SETS V`（`egress_ctl.sh` 出現在引號裡＝藏在字串裡的啟動，on_site.sh 蓋不掉它，一律警告、不豁免；現行 hook 把這型藏掉了）。標頭後的格式不鎖（總覽疑問 1） | 自動：同上 |
| TC-018 | 發現 2；RWH-10（兩個啟動段） | 例外 | 同上 | 對 V 各送出 `scripts/on_site.sh egress_ctl.sh start; V=evil bash scripts/egress_ctl.sh start` | 含警告句（第二個啟動段是直接的，只要有一個直接就警告） | 自動：同上 |
| ~~TC-019~~ | ~~作法 2「啟動點最多掃 8 個」；原 RWH-26~~ | ~~例外~~ | | | 已取消：裁決三取代作法 2。列號保留，不計入統計 | |
| TC-020 | 裁決三 3、裁決四 4 免警告例；RWH-11 | 功能 | 同上 | 對 V 各送出 `V=ok bash scripts/on_site.sh egress_ctl.sh start` | 詢問文字**不含**該變數的警告句（段的命令是 on_site.sh，egress_ctl.sh 是它後面未加引號的參數）；閘門本身仍詢問（見 TC-032） | 自動：`envw` lacks，兩個變數各一條（等同既有 PEER-9） |
| TC-021 | 裁決四 4 免警告例；RWH-12 | 功能 | 同上 | 對 V 各送出 `V=ok scripts/on_site.sh --script scripts/egress_ctl.sh start` | 詢問文字**不含**該變數的警告句 | 自動：同上 |
| TC-022 | 既有 PEER-8、PEER-10、PEER-11 與 `envp` 對照 | 例外 | 同上 | 送出不該警告的指令：`bash scripts/egress_ctl.sh start`（沒帶變數）；只帶 EXTRA 的 start 看 PEER 警告；`NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh stop` | 這三種都不含對應的警告句（沒帶該變數、帶的是別的變數、或 stop，都不誤報）；對應既有斷言原樣保持 ok | 自動：`tests/confirm_launch_test.sh`（既有 `envq` lacks、`envp` lacks，不改） |
| TC-071 | 審查點 ④；裁決三 3、裁決四 4（`cat on_site.sh egress_ctl.sh start` 不豁免） | 例外 | 同上 | 對 V 各送出 `V=evil cat scripts/on_site.sh scripts/egress_ctl.sh start`（on_site.sh 只是 cat 的參數，段的命令是 `cat`） | 含警告句 `SETS V=evil` | 自動：同上（`envw` has＋必含字串） |
| TC-072 | 審查點 ④（同段兩個啟動只看一個）；裁決四 4 | 例外 | 同上 | 對 V 各送出 `V=evil scripts/on_site.sh egress_ctl.sh start "bash scripts/egress_ctl.sh start"`（同一段裡，一個是 on_site.sh 的未加引號參數，另一個藏在引號字串裡） | 含警告句（段內只要有藏在引號裡的啟動就不豁免；不能只看其中一個） | 自動：同上 |
| TC-073 | 裁決三 3＋RWH-10 的對稱（豁免啟動段在後） | 例外 | 同上 | 對 V 各送出 `V=evil bash scripts/egress_ctl.sh start; scripts/on_site.sh egress_ctl.sh start` | 含警告句 `SETS V=evil`（直接的啟動段在前、經 on_site.sh 的在後，一樣要警告） | 自動：同上 |
| TC-074 | 裁決四 3（`env` 後面接 `VAR=值` 再接 `bash` 都要跳過） | 功能 | 同上 | 對 V 各送出 `env V=ok bash scripts/on_site.sh egress_ctl.sh start` | 詢問文字**不含**該變數的警告句（跳過 `env V=ok`、`bash` 之後，命令是 on_site.sh） | 自動：`envw` lacks，兩個變數各一條 |
| TC-075 | 裁決四 3（`sh` 與 `bash` 同樣跳過） | 功能 | 同上 | 對 V 各送出 `V=ok sh scripts/on_site.sh egress_ctl.sh start` | 詢問文字**不含**該變數的警告句 | 自動：同上 |

## User Story 3 — PEER 警告訊息說真話，兩個警告的其他文字不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 發現 4；RWH-19 | 功能 | 閘門已安裝；設定檔照 `id_env.yaml` | 送出 `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh start`，看詢問文字 | 含 `Entries that are not valid are dropped`（說明無效項會被丟掉） | 自動：`tests/confirm_launch_test.sh`（`envq_txt`） |
| TC-024 | 發現 4；RWH-20 | 功能 | 同上 | 送出同一條指令 | 含 `falls back to the built-in one`（說明全無效時退回內建清單）；標頭句接 `which asks the relay to use this list of host-name prefixes` | 自動：同上（標頭措辭由被改字的既有 PEER-3/4/7 斷言證明） |
| TC-025 | 發現 4；裁決 5；RWH-21 | 功能 | 同上 | 送出同一條指令，看整段詢問文字 | **不含** `cpn,gpn,bgm,lgn,localhost`（訊息不寫死預設清單） | 自動：同上（反向字串判斷） |
| TC-026 | 作法 5；裁決 5 | 功能 | 本分支與 `ledger.md` | 執行 `grep -c 'cpn,gpn,bgm,lgn,localhost' hooks/confirm_launch.sh` | 結果為 0（連 hook 原始碼裡都沒有抄一份預設清單） | 手動：閱卷者自己跑，輸出貼進 `ledger.md` |
| TC-027 | 作法 5「空值說明句保留、措辭不變」 | 功能 | 本分支與 `ledger.md` | 送出 `NF_RELAY_PEER_PREFIXES= bash scripts/egress_ctl.sh start`，看詢問文字；並讀 `git diff` 裡該句 | 詢問文字仍含 `An empty value is ignored by the relay, which then uses the deployment's relay_peer_prefixes setting.`，與基底該句逐字相同；警告句仍顯示為空值（`SETS NF_RELAY_PEER_PREFIXES=, which asks the relay …`） | 手動：閱卷者自己跑並比對，輸出貼進 `ledger.md` |
| TC-028 | 作法 5、6；既有 PEER-6、PEER-7、`envp` | 功能 | 本分支 | 執行 `bash tests/confirm_launch_test.sh`，看既有 `envp` 四條與 PEER-6 兩變數並存、「先 EXTRA 後 PEER」順序、PEER-7 的 `Show the user the prefixes it names.` | 全部 ok：EXTRA 尾句 `overrides this deployment's list` 沒變；兩變數並存時兩段警告都在、順序固定先 EXTRA 後 PEER；PEER 尾句仍在 | 自動：`tests/confirm_launch_test.sh`（既有斷言，不改） |

## User Story 4 — 閘門只會更強不會更弱、夠便宜、改動範圍只有三個檔、兩個警告共用一段程式（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | 硬規則；RWH-16 | 例外 | 閘門已安裝；設定檔照 `id_env.yaml` | 以 `idg` 送出 `echo NF_RELAY_PEER_PREFIXES=ok; NF_RELAY_PEER_PREFIXES=evil bash scripts/egress_ctl.sh start` | 結果是 `ask` | 自動：`tests/confirm_launch_test.sh`（`idg` ask） |
| TC-030 | 硬規則；RWH-17 | 例外 | 同上 | 以 `idg` 送出 `bash scripts/on_site.sh status; NF_RELAY_PEER_PREFIXES=evil bash scripts/egress_ctl.sh start` | 結果是 `ask` | 自動：同上 |
| TC-031 | 硬規則；RWH-18 | 例外 | 同上 | 以 `idg` 送出 `scripts/on_site.sh 'NF_RELAY_PEER_PREFIXES=evil bash scripts/egress_ctl.sh start'` | 結果是 `ask` | 自動：同上 |
| TC-032 | 硬規則「現在會詢問的每一種情況仍要詢問」；既有 PEER-12 與 `idg`／`idw` 組 | 例外 | 本分支 | 執行 `bash tests/confirm_launch_test.sh`，看既有 PEER-12 八條與其餘 `idg`／`idw` 斷言 | 全部維持 ok，一條都沒由 ask 變 allow | 自動：`tests/confirm_launch_test.sh`（既有斷言，不改） |
| TC-033 | 完成標準「不更弱」比對；倉庫校正失敗 #1、#2 | 功能 | 兩份 hook：基底（`origin/v3`，含已合併的 #189）與本分支 | 把兩份 hook 各餵同一批指令：RWH-1…RWH-21 與本檔所有新增 TC 的指令、現有 EXTRA／PEER 全部指令、`bash scripts/egress_ctl.sh start\|stop\|restart\|status`、`bash scripts/agent_ctl.sh start`、一條不相關的 `ls`，再加兩條超過上限的指令（約 1 MB 單一超長段；約 1 MB 大量短段）與一條 51 段的指令，比對 `permissionDecision`；閱卷者自己重跑 | 新 hook 的 `ask` 集合**包含**舊 hook 的 `ask` 集合；其餘指令兩邊結果一致；`ls` 兩邊都放行 | 手動：兩邊輸出比對表貼進 `ledger.md` |
| TC-034 | 完成標準「兩個分支各跑一遍」；倉庫校正失敗 #1 | 功能 | 兩個工作樹：`origin/v3` 與本分支 | 兩邊各跑 `bash tests/confirm_launch_test.sh`，輸出存檔逐行比對（閱卷者自己重跑，不只信 ledger） | 差異只有兩類：5 條被改字的既有斷言，與新增的測試行；其餘每一行 ok／FAIL 狀態完全相同；本分支 FAIL 數為 0 | 手動：比對結果貼進 `ledger.md` |
| TC-035 | 計畫「既有斷言被改的清單」；裁決四 9「既有斷言除措辭外不改」 | 功能 | 本分支與 `ledger.md` | 讀 `git diff origin/v3...HEAD -- tests/confirm_launch_test.sh` 的刪除行 | 被改（被刪再加）的既有行**恰好 5 條**：PEER-3 value、PEER-4 empty value、PEER-7 the value is shown、PEER-7 which hosts、PEER-7 default list；且改動只在必含字串的措辭，標籤、指令、`ok`／`has` 期望都沒變；`envp` 四條、PEER-2（env 前綴）、PEER-3（export）與其餘既有斷言一字未動，沒有跳過、沒有放寬；`ledger.md` 貼了這 5 條的改前／改後 | 手動：閱卷者重跑 `git diff`，結果記於 `ledger.md` |
| TC-036 | 範圍：檔案；失敗先行測試的位置與寫法 | 功能 | 本分支 | 讀 `git diff origin/v3...HEAD -- tests/confirm_launch_test.sh` 的新增行 | 新增 `envw` 輔助函式與斷言列，緊接在 PEER-12 最後一條（`idg "PEER-12 plain start still asks"`）之後；寫法沿用 `envp`；RWH-1…RWH-15 與 TC-054…TC-075 中標「兩個變數各一條」的案例都用 `for V in NF_RELAY_EXTRA_DOMAINS NF_RELAY_PEER_PREFIXES` 對兩個變數各跑一次（標籤帶變數名）；RWH-16…RWH-24 與本檔其他「自動」TC 都在，且每條測試的註解寫了 TC 編號；原 RWH-25／26 已移除 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-037 | 範圍：檔案（共 3 個） | 不在範圍 | 本分支 | `git diff --name-only origin/v3...HEAD` | 實作檔只出現 `hooks/confirm_launch.sh`、`tests/confirm_launch_test.sh`、`specs/relay-warning-hardening/ledger.md`（計畫與規定的 TC 檔另計）；沒有其他檔 | 手動：閱卷者重跑，結果記於 `ledger.md` |
| TC-038 | 範圍：禁止碰；「不做」第 1、4 點 | 不在範圍 | 本分支 | `git diff origin/v3...HEAD -- scripts/ platform/ docs/ skills/ deploy/ commands/ hooks/hooks.json` | 輸出為空 | 手動：閱卷者重跑，結果記於 `ledger.md` |
| TC-039 | 完成標準「hook diff 只替換兩個區塊」；作法 1、8 | 功能 | 本分支 | 讀 `git diff origin/v3...HEAD -- hooks/confirm_launch.sh` | 既有行被改／刪的只有原 EXTRA 與 PEER 兩個警告區塊；新增的函式（`relay_env_warn` 及它呼叫的輔助函式，若有）位置在 `ask()` 之後、RESIDENT 區塊之前；`RELAY_START_RE`、`RESIDENT_RE`、`RELAY_DOMS` 摘要與其他既有行一字未動；改的只有 `RELAY_LIST` 的文字 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-040 | 發現 5；作法 1；裁決 1 | 功能 | 本分支 | 讀新的兩個呼叫處與函式 | 兩個變數都經 `relay_env_warn <變數名>` 這同一個函式取值；擷取／去引號／截斷／切段的邏輯只存在函式一處，呼叫處沒有各自的正則或重複程式；兩處各自帶自己的尾句；順序固定先 EXTRA 後 PEER；函式回傳 0＝要警告、1＝不用，結果用全域變數 `RELAY_ENV_HEAD`、`RELAY_ENV_MORE` 交回 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-041 | 完成標準「函式本體只用 bash 內建」；硬規則 | 功能 | 本分支 | 用 `sed -n` 取出 `relay_env_warn` 與它呼叫的所有輔助函式本體後 `grep` 檢查命令替換 `$(`（`$((` 算術除外）、反引號（寫在字串字面值裡的不算）、`grep`、`jq`、`python`、`sed`、`awk`、`tr`、`mktemp`、`eval` 等 | 找不到任何命令替換或外部程式（hook 逾時＝放行，不能 fork）；`grep` 檢查的輸出貼進 `ledger.md` | 手動：閱卷者自己重跑，結果記於 `ledger.md` |
| ~~TC-042~~ | ~~作法 2「迴圈上限 8／20」~~ | ~~功能~~ | | | 已取消：裁決三取代作法 2。由 TC-077 與 TC-078…TC-083 取代。列號保留，不計入統計 | |
| TC-043 | 完成標準「成本」；硬規則逾時＝放行 | 功能 | 本分支與基底各一份 hook | 用一條約 100 KB、不含 `NF_RELAY_EXTRA_DOMAINS=` 也不含 `NF_RELAY_PEER_PREFIXES=` 的指令，新舊 hook 各用 `time` 跑 | 新 hook 不比舊 hook 慢（容許量測誤差）；兩邊數字貼進 `ledger.md` | 手動：閱卷者自己量，結果記於 `ledger.md` |
| TC-044 | 完成標準「成本」 | 功能 | 本分支與基底；`hooks/hooks.json` 中 confirm_launch 的逾時（目前 30 秒，不改） | 用一條約 100 KB、含 3 個 `egress_ctl.sh start` 與 25 個 `V=` 賦值的指令（超過 64 KB，走「不解析」快路），新舊 hook 各用 `time` 跑 | 新 hook 的耗時遠低於逾時；數字貼進 `ledger.md` | 手動：閱卷者自己量，結果記於 `ledger.md` |
| TC-045 | 作法 7；硬規則 | 功能 | 本分支 | 讀 `git diff origin/v3...HEAD -- hooks/confirm_launch.sh` 的新增行 | 沒有新增 `allow` 路徑、沒有新增 `exit 0`、沒有新增 `ask` 呼叫；`ask "GATE: this starts…"` 的呼叫與外框文字原樣；`ask()` 未改；警告只附加進同一個 `RELAY_LIST`，由原有的唯一一次 `ask` 送出 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-046 | 完成標準第 1 點 | 功能 | 本分支 | 執行 `bash tests/confirm_launch_test.sh` | 全檔綠（FAIL 數 0），包含本檔所有新增斷言與 5 條改字的既有斷言 | 自動：`tests/confirm_launch_test.sh` |
| TC-047 | 完成標準第 1 點 | 功能 | 本分支，WSL／Linux | 在 WSL 執行 `bash tests/run_all.sh`（見倉庫 CLAUDE.md） | 全套綠（若有失敗，須證明基底同樣失敗且不在本任務範圍，記於 `ledger.md`） | 自動：`tests/run_all.sh` |
| TC-048 | 「不做」第 2 點（不對其他變數加警告） | 不在範圍 | 本分支與 `ledger.md` | 讀 diff；並送出 `NF_RELAY_PORT=1 bash scripts/egress_ctl.sh start` 與 `NF_RELAY_EXTRA_NOTE=x bash scripts/egress_ctl.sh start` 看詢問文字 | 函式只被這兩個變數名呼叫；兩條指令的詢問文字都不含 `THIS COMMAND ALSO SETS` | 手動：閱卷者自己跑，輸出貼進 `ledger.md` |
| TC-049 | 「不做」第 2 點、裁決二 3（間接指派另案） | 不在範圍 | 本分支與 `ledger.md` | 讀 `ledger.md`，並送出 `V=NF_RELAY_PEER_PREFIXES; export $V=evil; bash scripts/egress_ctl.sh start`（`V` 在此是 shell 變數） | `ledger.md` 有一句記載「間接指派（`export $V=…`、`printf -v`、`env -S`）未處理、另開任務」；該指令沒有因本任務而新增警告句，閘門仍詢問；沒有偷偷實作間接寫法的偵測 | 手動：閱卷者讀 ledger 並跑一次，結果記於 `ledger.md` |
| TC-050 | 「不做」第 3、5 點（不重做有效性檢查、不展開） | 不在範圍 | 本分支 | 讀函式本體 | 沒有任何前綴合法性檢查（沒有 `[a-z0-9-]` 之類的有效性正則、沒有長度／個數檢查）；沒有 `eval`、沒有展開 `$VAR`／`$(…)`，只照抄字面 | 手動：閱卷者讀函式，結果記於 `ledger.md` |
| TC-051 | 裁決 6；裁決二 2（引號形式 `--script "…"` 的誤報已接受） | 不在範圍 | 本分支與 `ledger.md` | 讀 `ledger.md`；送出 `V=ok scripts/on_site.sh --script "${CLAUDE_PLUGIN_ROOT}/scripts/egress_ctl.sh" start` | `ledger.md` 有記一筆「帶引號的 `--script "…"` 會多一句警告，已接受」；這一型**不**被測試鎖定為 lacks 或 has，閱卷者不得以它退回（閘門本身都要詢問） | 手動：閱卷者讀 ledger，結果記於 `ledger.md` |
| TC-077 | 裁決三 5「不准用 `^(.*)` 形式的 regex」；審查點 ⑥ | 功能 | 本分支 | 用 `sed -n` 取出 `relay_env_warn` 與它呼叫的輔助函式本體，找所有 `=~` 的右側（含存進變數的正則字串）；另檢查整個 hook diff 的新增行 | 沒有任何以 `^(.*)`、`(.*)` 開頭或帶「貪婪 `.*` 加後續必須相符」形式的回溯正則；切段是逐字元迴圈（≤64 KB 才跑）；`ledger.md` 列出 helper 內每條正則與其用途 | 手動：閱卷者自己重跑 `sed -n`＋`grep`，結果記於 `ledger.md` |
| TC-078 | 裁決四 1；裁決三 5；審查點 ⑥（單一超長段） | 功能 | 設定檔照 `id_env.yaml`；測試用檔案或標準輸入組 JSON，不用命令列引數傳（Windows 引數上限約 32 KB） | 對 V 各送出 `V=ok bash scripts/egress_ctl.sh start --note ` 後面接約 1 MB 的 `x`（整條指令沒有任何 `; & \| ( )`，是一個超長段），量 hook 執行時間 | 詢問文字含完整的 not parsed 標頭（`THIS COMMAND ALSO SETS V (not parsed: the command is too long or has too many parts); read the whole command.`）；整次執行 < 2 秒 | 自動：`tests/confirm_launch_test.sh` |
| TC-079 | 裁決四 1；審查點 ⑥（大量短段） | 功能 | 同 TC-078 | 對 V 各送出由約 130,000 個 `echo a;` 串成、最後接 `V=ok bash scripts/egress_ctl.sh start` 的指令（總長 ≥ 1 MB、段數遠超 50），量 hook 執行時間 | 詢問文字含完整的 not parsed 標頭；整次執行 < 2 秒 | 自動：同上 |
| TC-080 | 裁決四 1（段數超過 50） | 例外 | 設定檔照 `id_env.yaml` | 對 V 各送出 50 個 `echo a;` 後接 `V=ok bash scripts/egress_ctl.sh start`（51 段，總長遠小於 64 KB，無空段、無結尾分隔符） | 含完整的 not parsed 標頭；閘門 ask | 自動：同上 |
| TC-081 | 裁決四 1（段數剛好 50 要解析） | 功能 | 同上 | 對 V 各送出 49 個 `echo a;` 後接 `V=ok bash scripts/egress_ctl.sh start`（50 段） | 含 `SETS V=ok`；**不含** `not parsed` | 自動：同上 |
| TC-082 | 裁決四 1（超過 64 KB） | 例外 | 同上 | 對 V 各送出約 70,000 字元、由 40 段各約 1,750 個字元的 `echo xxxx…;` 後接 `V=ok bash scripts/egress_ctl.sh start` 組成的指令（段數 41、每段 < 4096 字元，只有「總長超過 64 KB」這個條件成立） | 含完整的 not parsed 標頭；閘門 ask | 自動：同上 |
| TC-083 | 裁決四 1（64 KB 以內要解析） | 功能 | 同上 | 對 V 各送出約 60,000 字元、由 40 段各約 1,400 個字元的 `echo xxxx…;` 後接 `V=ok bash scripts/egress_ctl.sh start` 組成的指令（段數 41、每段 < 4096 字元） | 含 `SETS V=ok`；**不含** `not parsed` | 自動：同上 |
| TC-084 | 完成標準「成本」＋裁決三 5（逐字元迴圈在上限內夠快） | 功能 | 本分支與基底各一份 hook | 用一條約 60,000 字元、41 段以內、含 25 個 `V=` 同段前綴賦值與 3 個 `egress_ctl.sh start` 命令段的指令，新舊 hook 各用 `time` 跑 | 新 hook 耗時遠低於 `hooks/hooks.json` 的 30 秒逾時；數字貼進 `ledger.md`，閱卷者自己重量 | 手動：結果記於 `ledger.md` |
| TC-085 | 裁決三 5、裁決四 8 ①⑧（regex 能編譯） | 功能 | 本分支 | 測試檔內有一條（或一組）測試：把 helper 用到的每條正則（含 `RELAY_START_RE` 與 helper 內自建的）各在 `bash --posix` 下執行 `[[ x =~ $re ]]`；閱卷者另外在 Git Bash 對基底 hook（`git show 0b104ad:hooks/confirm_launch.sh`）的空分支正則跑同一個檢查 | 新 hook 每條正則的回傳碼都**不是 2**；閱卷者核對測試涵蓋 helper 內每一個 `=~`（沒有漏的）；同一個檢查對舊 hook 的 `^(.*[;&\|`(換行]\|)…` 在這台 Git Bash 回 2（舊紅），證據貼進 `ledger.md` | 自動：`tests/confirm_launch_test.sh`；舊紅證據手動記於 `ledger.md` |
| TC-086 | 硬規則；裁決四 1（不解析也要問） | 例外 | 同 TC-078 | 以 `idg` 送出 TC-078、TC-079、TC-080、TC-082 的四種指令（PEER 變數） | 結果都是 `ask`（沒有因為超過上限而放行） | 自動：同上 |
| TC-087 | 裁決三 6、裁決四 8「每點至少一條舊寫法紅、新寫法綠」 | 功能 | 本分支與 `0b104ad` 的舊 hook（暫存副本，不改工作樹） | 把新測試檔對舊 hook（`git show 0b104ad:hooks/confirm_launch.sh`）跑一遍，列出 FAIL 的行 | 審查 8 點各至少有一條 FAIL（舊紅）：① TC-085（與 TC-020／021 在 regex 編譯失敗的 bash 上）、② TC-061／062、④ TC-071／072、⑤ TC-056／057／060、⑥ TC-078／079、⑦ TC-054／055、⑧ TC-085；③ 另見 TC-088。同一批測試對新 hook 全綠；對應表貼進 `ledger.md`，閱卷者自己重跑 | 手動：結果記於 `ledger.md` |
| TC-088 | 審查點 ③（死碼括號樣式）；裁決四 7 | 功能 | 本分支 | 讀 helper 內每一個括號運算式／萬用字元樣式（例如 `[[ $x == *[…]* ]]` 之類），在 bash 實跑 | `ledger.md` 對每個樣式列「一個會中的樣本、一個不會中的樣本」與實跑結果，證明沒有永遠不中的樣式；舊寫法 `*[\"\'\]*` 的實跑結果（永遠不中）也列出作對照。本條不鎖殘留引號／反斜線的顯示（計畫兩處矛盾，見總覽疑問 3） | 手動：閱卷者自己重跑，結果記於 `ledger.md` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-052 | 憲法第 13 條（安全網做不了事時要說；缺 `jq` 時閘門拒絕它無法排除的東西），檢查＝`tests/confirm_launch_test.sh` 的「no jq」區段 | 功能 | 本分支 | 執行 `bash tests/confirm_launch_test.sh`，看所有「no jq」區段 | 全部維持 ok，與基底相同；新函式只用 bash 內建，沒有讓缺 jq 時的行為變得更容易放行 | 自動：`tests/confirm_launch_test.sh` |
| TC-053 | 安全網：「啟動指令要明示並等使用者明確確認」與倉庫校正失敗 #1、#2（收窄閘門曾放行三種本該擋的形狀；對複合指令的一段豁免讓整行過關） | 功能 | 兩個工作樹：基底與本分支 | 把 TC-029…TC-031 的三條誘餌指令與 TC-033 的比對集，在基底與本分支各送一遍 | 凡基底會 `ask` 的，本分支都 `ask`；on_site.sh 出現在別的命令段、註解、引號負載時，本分支警告文字比基底更多而不是更少 | 手動：兩邊結果貼進 `ledger.md`，閱卷者自己重跑 |

<!--
Rules for the writer:
- 驗證方式 is 自動 or 手動. 手動 here follows memory/dev-plans/README.md「通例：閱卷看 diff」: evidence goes in ledger.md, not docs/TESTING.md.
- IDs are never renumbered after approval; a removed case keeps its row, struck through. 第二版的新 TC 從 TC-054 起，TC-054…TC-075 在 US1／US2 區段，TC-077…TC-088 在 US4 區段；TC-076 保留不用。
-->
