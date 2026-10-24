# 測試案例：中繼啟動閘門對 NF_RELAY_EXTRA_DOMAINS= / NF_RELAY_PEER_PREFIXES= 的警告補強（relay-warning-hardening）

<!--
Written by the verifier (CONTRACT mode) from specs/relay-warning-hardening/plan.md (含裁決與裁決二), before any code.
這個任務沒有 spec.md；依據是 plan.md（A 級、backend），維護者原話與範例都引自計畫「維護者原話」與「失敗先行測試」（RWH-1…RWH-21）。
RWH-22…RWH-26 不是計畫列的測試，而是計畫「作法」2、4 明寫的行為（上限、列 5 個、200 字元、截斷說明），合約補上對應的 TC。
-->

**規格**：`specs/relay-warning-hardening/plan.md`（本任務沒有 spec.md）　**總覽**：`test-case-overview.md`

白話說明：中繼（relay）是登入節點上替運算節點轉送對外連線的常駐程式。閘門（`hooks/confirm_launch.sh`）在有人要啟動它時會停下來問使用者「要不要允許」。如果那行指令自己帶了 `NF_RELAY_EXTRA_DOMAINS=…`（多放行哪些網域）或 `NF_RELAY_PEER_PREFIXES=…`（哪些主機名開頭的機器可以連進中繼），問話文字裡要有一句警告，把「真正會生效的值」講給使用者聽。這次要補的是：警告不能被一句 `echo`、一段註解、另一條 on_site.sh 指令騙過去，顯示的值要乾淨、要說真話，兩個變數共用同一段程式。「ask」＝閘門停下來問；「警告句」＝問話文字裡 `THIS COMMAND ALSO SETS …` 那一段；「V」＝`NF_RELAY_EXTRA_DOMAINS` 與 `NF_RELAY_PEER_PREFIXES` 兩個變數各跑一次（兩條斷言，兩條都要綠）。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：邊角情況或不該被放行／不該被藏掉的情況，系統怎麼反應（照樣詢問、照樣警告、不誤報）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

測試輔助函式約定（來自計畫）：`envw <label> <變數> <has|lacks> <指令> [必含字串]` 判的是**該變數自己的警告句** `THIS COMMAND ALSO SETS ${V}` 有沒有出現，並可附一個必含字串；`idg` 是既有函式，期望 `ask`；`envq_txt` 是既有函式，比對詢問文字含某固定字串。以下指令中的 `V` 一律代入實際變數名；`ok`、`evil` 是任意值。「手動」＝依 `memory/dev-plans/README.md`「通例：閱卷看 diff」，證據貼進 `specs/relay-warning-hardening/ledger.md`，閱卷者自己重跑核對（不寫進 `docs/TESTING.md`）。

## User Story 1 — 警告顯示真正會生效的值（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 發現 1；RWH-1（誘餌 echo） | 功能 | 閘門已安裝；部署設定檔照 `id_env.yaml` | 對 V 各送出 `echo V=ok; V=evil bash scripts/egress_ctl.sh start` | 詢問文字含該變數的警告句，且主角值是最後一個：含 `SETS V=evil`（不是第一個的 `ok`） | 自動：`tests/confirm_launch_test.sh`（`envw` has，對兩個變數各一條） |
| TC-002 | 發現 1；RWH-2（同行多重賦值） | 功能 | 同上 | 對 V 各送出 `V=ok V=evil bash scripts/egress_ctl.sh start` | 詢問文字含 `SETS V=evil`，且含 `assigns V 2 times: ok \| evil` | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-003 | 作法 4「最多列最後 5 個」；RWH-22 | 功能 | 同上 | 對 PEER 變數送出 `NF_RELAY_PEER_PREFIXES=a1 NF_RELAY_PEER_PREFIXES=a2 NF_RELAY_PEER_PREFIXES=a3 NF_RELAY_PEER_PREFIXES=a4 NF_RELAY_PEER_PREFIXES=a5 NF_RELAY_PEER_PREFIXES=a6 NF_RELAY_PEER_PREFIXES=a7 bash scripts/egress_ctl.sh start`（共 7 個賦值） | 詢問文字含 `SETS NF_RELAY_PEER_PREFIXES=a7`、`assigns NF_RELAY_PEER_PREFIXES 7 times: a3 \| a4 \| a5 \| a6 \| a7`（只列最後 5 個，依出現順序）、`(2 earlier ones not shown)` | 自動：`tests/confirm_launch_test.sh`（只對 PEER 一條，共用函式） |
| TC-004 | 發現 3；RWH-3（雙引號） | 功能 | 同上 | 對 V 各送出 `V="a,b" bash scripts/egress_ctl.sh start` | 詢問文字含 `SETS V=a,b`（值外面沒有引號） | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-005 | 發現 3；RWH-4（引號內有空白） | 功能 | 同上 | 對 V 各送出 `V="a b" bash scripts/egress_ctl.sh start` | 詢問文字含 `SETS V=a b`（空白之後沒有被截斷） | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-006 | 發現 3；RWH-5（單引號） | 功能 | 同上 | 對 V 各送出 `V='a,b' bash scripts/egress_ctl.sh start` | 詢問文字含 `SETS V=a,b`（沒有引號） | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-007 | 作法 4「顯示只取前 200 字元」；RWH-23 | 功能 | 同上 | 對 PEER 變數送出值為 250 個 `x` 的指令：`NF_RELAY_PEER_PREFIXES=<250 個 x> bash scripts/egress_ctl.sh start` | 詢問文字含 `SETS NF_RELAY_PEER_PREFIXES=` 後接恰好 200 個 `x` 再接 `…`；不含連續 201 個 `x` | 自動：`tests/confirm_launch_test.sh`（只對 PEER 一條，共用函式） |
| TC-008 | 發現 3；RWH-13（未加引號的命令替換） | 功能 | 同上 | 對 V 各送出 `V=$(cat /tmp/p) bash scripts/egress_ctl.sh start` | 詢問文字含 `value is computed at run time: $(cat`（照抄被截斷的字面，並說明值是執行時才算出） | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-009 | 作法 4「括號內補 cut at the first space」；RWH-24 | 功能 | 同上 | 對 PEER 變數送出 `NF_RELAY_PEER_PREFIXES=$(cat /tmp/p) bash scripts/egress_ctl.sh start` | 詢問文字含 `cut at the first space; read the command` | 自動：`tests/confirm_launch_test.sh`（只對 PEER 一條，共用函式） |
| TC-010 | 發現 3；RWH-14（加引號的命令替換） | 功能 | 同上 | 對 V 各送出 `V="$(cat /tmp/p)" bash scripts/egress_ctl.sh start` | 詢問文字含 `value is computed at run time: $(cat /tmp/p)`（引號內完整字面，已去外層引號） | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-011 | 發現 3；「不做」展開 `$VAR`；RWH-15（變數展開） | 功能 | 同上 | 對 V 各送出 `V=$P bash scripts/egress_ctl.sh start` | 詢問文字含 `value is computed at run time: $P`（照抄字面，沒有被展開成別的東西） | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-012 | 作法 2「超過上限一律警告」；RWH-26 | 例外 | 同上 | 對 PEER 變數送出一行有 21 個 `NF_RELAY_PEER_PREFIXES=v1 … NF_RELAY_PEER_PREFIXES=v21` 賦值的 `bash scripts/egress_ctl.sh start`（賦值數超過 20 的上限） | 詢問文字含 PEER 警告句 `THIS COMMAND ALSO SETS NF_RELAY_PEER_PREFIXES`（超過上限仍然警告，不漏）。本條只鎖「有警告」，不鎖顯示哪一個值（見總覽疑問 1） | 自動：`tests/confirm_launch_test.sh`（只對 PEER 一條，共用函式） |
| TC-013 | 作法 4「單一賦值時與現行格式一致」 | 功能 | 本分支與 `ledger.md` | 對閘門送出只有一個賦值的 `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh start`，看詢問文字 | 警告句是 `THIS COMMAND ALSO SETS NF_RELAY_PEER_PREFIXES=25a-cpn, which …`，**不含** `assigns`、`times:` 這類多重賦值句（只有一個賦值就不多說） | 手動：閱卷者自己跑一次，輸出貼進 `ledger.md` |

## User Story 2 — on_site.sh 豁免縮窄：只有「啟動本身經 on_site.sh」才免警告（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 發現 2；RWH-6（on_site.sh 出現在別的命令） | 例外 | 閘門已安裝；設定檔照 `id_env.yaml` | 對 V 各送出 `bash scripts/on_site.sh status; V=evil bash scripts/egress_ctl.sh start` | 詢問文字含該變數的警告句（`;` 把 on_site.sh 隔在別的命令段，不能豁免） | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-015 | 發現 2；RWH-7（尾端註解） | 例外 | 同上 | 對 V 各送出 `V=evil bash scripts/egress_ctl.sh start # on_site.sh` | 詢問文字含警告句（註解在啟動之後，不是它前面的命令段） | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-016 | 發現 2；RWH-8（上一行的註解） | 例外 | 同上 | 對 V 各送出兩行指令：第一行 `# on_site.sh`，換行後第二行 `V=evil bash scripts/egress_ctl.sh start`（測試以 `$'# on_site.sh\nV=evil bash scripts/egress_ctl.sh start'` 組出） | 詢問文字含警告句（換行是命令段邊界） | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-017 | 發現 2；作法 3；RWH-9（on_site.sh 的引號負載） | 例外 | 同上 | 對 V 各送出 `scripts/on_site.sh 'V=evil bash scripts/egress_ctl.sh start'` | 詢問文字含警告句（引號內的負載在遠端是直接跑，on_site.sh 蓋不掉它；現行 hook 把這型藏掉了） | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-018 | 作法 3「所有啟動點都經 on_site.sh 才免」；RWH-10（兩個啟動點） | 例外 | 同上 | 對 V 各送出 `scripts/on_site.sh egress_ctl.sh start; V=evil bash scripts/egress_ctl.sh start` | 詢問文字含警告句（第二個啟動點是直接的，只要有一個直接就警告） | 自動：`tests/confirm_launch_test.sh`（`envw` has，兩個變數各一條） |
| TC-019 | 作法 2「啟動點最多掃 8 個，超過一律警告」；RWH-25 | 例外 | 同上 | 對 PEER 變數送出一行 `NF_RELAY_PEER_PREFIXES=ok bash scripts/on_site.sh egress_ctl.sh start` 後面用 `;` 再接 8 個 `bash scripts/on_site.sh egress_ctl.sh start`（共 9 個啟動點，每個都經 on_site.sh） | 詢問文字含 PEER 警告句（啟動點超過 8 個上限，寧可多問，不可漏） | 自動：`tests/confirm_launch_test.sh`（只對 PEER 一條，共用函式） |
| TC-020 | 作法 3 免警告例；RWH-11（對照：經 on_site.sh 免警告） | 功能 | 同上 | 對 V 各送出 `V=ok bash scripts/on_site.sh egress_ctl.sh start` | 詢問文字**不含**該變數的警告句（正規路徑不誤報）；閘門本身仍詢問（見 TC-032） | 自動：`tests/confirm_launch_test.sh`（`envw` lacks，兩個變數各一條；等同既有 PEER-9） |
| TC-021 | 作法 3 免警告例；RWH-12（對照：`--script` 形式免警告） | 功能 | 同上 | 對 V 各送出 `V=ok scripts/on_site.sh --script scripts/egress_ctl.sh start` | 詢問文字**不含**該變數的警告句 | 自動：`tests/confirm_launch_test.sh`（`envw` lacks，兩個變數各一條） |
| TC-022 | 作法 2「便宜優先」；既有 PEER-8、PEER-10、PEER-11 與 `envp` 對照 | 例外 | 同上 | 送出不該警告的指令：`bash scripts/egress_ctl.sh start`（沒帶變數）；只帶 EXTRA 的 start 看 PEER 警告；`NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh stop` | 這三種都不含對應的警告句（沒帶該變數、帶的是別的變數、或 stop，都不誤報）；對應既有斷言原樣保持 ok | 自動：`tests/confirm_launch_test.sh`（既有 `envq` lacks、`envp` lacks，不改） |

## User Story 3 — PEER 警告訊息說真話，兩個警告的其他文字不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 發現 4；RWH-19 | 功能 | 閘門已安裝；設定檔照 `id_env.yaml` | 送出 `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh start`，看詢問文字 | 含 `Entries that are not valid are dropped`（說明無效項會被丟掉） | 自動：`tests/confirm_launch_test.sh`（`envq_txt`） |
| TC-024 | 發現 4；RWH-20 | 功能 | 同上 | 送出同一條指令 | 含 `falls back to the built-in one`（說明全無效時退回內建清單）；並且標頭句接 `which asks the relay to use this list of host-name prefixes` | 自動：`tests/confirm_launch_test.sh`（`envq_txt`；標頭措辭由被改字的既有 PEER-3/4/7 斷言證明） |
| TC-025 | 發現 4；作法 5；裁決 5；RWH-21 | 功能 | 同上 | 送出同一條指令，看整段詢問文字 | **不含** `cpn,gpn,bgm,lgn,localhost`（訊息不寫死預設清單） | 自動：`tests/confirm_launch_test.sh`（反向字串判斷） |
| TC-026 | 作法 5；裁決 5 | 功能 | 本分支與 `ledger.md` | 執行 `grep -c 'cpn,gpn,bgm,lgn,localhost' hooks/confirm_launch.sh` | 結果為 0（連 hook 原始碼裡都沒有抄一份預設清單） | 手動：閱卷者自己跑，輸出貼進 `ledger.md` |
| TC-027 | 作法 5「空值說明句保留、措辭不變」 | 功能 | 本分支與 `ledger.md` | 送出 `NF_RELAY_PEER_PREFIXES= bash scripts/egress_ctl.sh start`，看詢問文字；並讀 `git diff` 裡該句 | 詢問文字仍含 `An empty value is ignored by the relay, which then uses the deployment's relay_peer_prefixes setting.`，與基底該句逐字相同；警告句仍顯示為空值（`SETS NF_RELAY_PEER_PREFIXES=, which asks the relay …`） | 手動：閱卷者自己跑並比對，輸出貼進 `ledger.md` |
| TC-028 | 作法 5、6；既有 PEER-6、PEER-7 | 功能 | 本分支 | 執行 `bash tests/confirm_launch_test.sh`，看既有 `envp` 四條（EXTRA 的 start、env restart、export、對照組）與 PEER-6 兩變數並存、「先 EXTRA 後 PEER」順序、PEER-7 的 `Show the user the prefixes it names.` | 全部 ok：EXTRA 尾句 `overrides this deployment's list` 沒變（`envp` 靠它判斷）；兩變數並存時兩段警告都在、順序固定先 EXTRA 後 PEER；PEER 尾句 `Show the user the prefixes it names.` 仍在 | 自動：`tests/confirm_launch_test.sh`（既有斷言，不改） |

## User Story 4 — 閘門只會更強不會更弱，改動範圍只有三個檔，兩個警告共用一段程式（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | 硬規則；RWH-16 | 例外 | 閘門已安裝；設定檔照 `id_env.yaml` | 以 `idg` 送出 `echo NF_RELAY_PEER_PREFIXES=ok; NF_RELAY_PEER_PREFIXES=evil bash scripts/egress_ctl.sh start`（RWH-1 的指令） | 結果是 `ask`（新增的是文字，閘門仍在） | 自動：`tests/confirm_launch_test.sh`（`idg` ask） |
| TC-030 | 硬規則；RWH-17 | 例外 | 同上 | 以 `idg` 送出 `bash scripts/on_site.sh status; NF_RELAY_PEER_PREFIXES=evil bash scripts/egress_ctl.sh start`（RWH-6 的指令） | 結果是 `ask` | 自動：`tests/confirm_launch_test.sh`（`idg` ask） |
| TC-031 | 硬規則；RWH-18 | 例外 | 同上 | 以 `idg` 送出 `scripts/on_site.sh 'NF_RELAY_PEER_PREFIXES=evil bash scripts/egress_ctl.sh start'`（RWH-9 的指令） | 結果是 `ask` | 自動：`tests/confirm_launch_test.sh`（`idg` ask） |
| TC-032 | 硬規則「現在會詢問的每一種情況仍要詢問」；既有 PEER-12 與 `idg`／`idw` 組 | 例外 | 本分支 | 執行 `bash tests/confirm_launch_test.sh`，看既有 PEER-12 八條（start、env restart、export、空值、帶引號路徑、兩變數並存、經 on_site.sh、無變數）與其餘 `idg`／`idw` 斷言 | 全部維持 ok，一條都沒由 ask 變 allow | 自動：`tests/confirm_launch_test.sh`（既有斷言，不改） |
| TC-033 | 完成標準「不更弱」比對 | 功能 | 兩份 hook：基底（`origin/v3`，含已合併的 #189）與本分支 | 把兩份 hook 各餵同一批指令（RWH 全部指令、現有 EXTRA／PEER 全部指令、`bash scripts/egress_ctl.sh start\|stop\|restart\|status`、`bash scripts/agent_ctl.sh start`、一條不相關的 `ls`），比對 `permissionDecision`；閱卷者自己重跑 | 新 hook 的 `ask` 集合**包含**舊 hook 的 `ask` 集合；其餘指令兩邊結果一致；`ls` 兩邊都放行 | 手動：兩邊輸出比對表貼進 `ledger.md`（倉庫校正失敗 #1、#2） |
| TC-034 | 完成標準「兩個分支各跑一遍」；倉庫校正失敗 #1 | 功能 | 兩個工作樹：`origin/v3` 與本分支 | 兩邊各跑 `bash tests/confirm_launch_test.sh`，輸出存檔逐行比對（閱卷者自己重跑，不只信 ledger） | 差異只有兩類：5 條被改字的既有斷言，與新增的測試行；其餘每一行 ok／FAIL 狀態完全相同；本分支 FAIL 數為 0 | 手動：兩邊輸出比對結果貼進 `ledger.md` |
| TC-035 | 計畫「既有斷言被改的清單」 | 功能 | 本分支與 `ledger.md` | 讀 `git diff origin/v3...HEAD -- tests/confirm_launch_test.sh` 的刪除行 | 被改（被刪再加）的既有行**恰好 5 條**：PEER-3 value、PEER-4 empty value、PEER-7 the value is shown、PEER-7 which hosts、PEER-7 default list；且改動只在必含字串的措辭（如計畫列出的新字串），標籤、指令、`ok`／`has` 期望都沒變；`envp` 四條與其餘既有斷言一字未動，沒有跳過、沒有放寬；`ledger.md` 貼了這 5 條的改前／改後 | 手動：閱卷者重跑 `git diff`，結果記於 `ledger.md` |
| TC-036 | 範圍：檔案；失敗先行測試的位置與寫法 | 功能 | 本分支 | 讀 `git diff origin/v3...HEAD -- tests/confirm_launch_test.sh` 的新增行 | 新增 `envw` 輔助函式與斷言列，緊接在 PEER-12 最後一條（`idg "PEER-12 plain start still asks"`）之後；寫法沿用 `envp`（`python3 -c json.dumps` 組輸入、`LAB_SETTINGS_FILE=… bash "$H"`、`grep -qF --`）；RWH-1…RWH-15 用 `for V in NF_RELAY_EXTRA_DOMAINS NF_RELAY_PEER_PREFIXES` 對兩個變數各跑一次（標籤帶變數名）；RWH-16…RWH-26 都在 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-037 | 範圍：檔案（共 3 個） | 不在範圍 | 本分支 | `git diff --name-only origin/v3...HEAD` | 實作檔只出現 `hooks/confirm_launch.sh`、`tests/confirm_launch_test.sh`、`specs/relay-warning-hardening/ledger.md`（計畫與規定的 TC 檔另計）；沒有其他檔 | 手動：閱卷者重跑，結果記於 `ledger.md` |
| TC-038 | 範圍：禁止碰；「不做」第 1、4 點 | 不在範圍 | 本分支 | `git diff origin/v3...HEAD -- scripts/ platform/ docs/ skills/ deploy/ commands/ hooks/hooks.json` | 輸出為空（中繼 `nf_relay.py`、`egress_ctl.sh`、`on_site.sh`、文件、技能、指令檔，與 matcher／逾時設定都沒動） | 手動：閱卷者重跑，結果記於 `ledger.md` |
| TC-039 | 完成標準「hook diff 只替換兩個區塊」；作法 1、8 | 功能 | 本分支 | 讀 `git diff origin/v3...HEAD -- hooks/confirm_launch.sh` | 既有行被改／刪的只有原 EXTRA 與 PEER 兩個警告區塊（原 391–416 行）；新增一個 `relay_env_warn` 函式，位置在 `ask()` 之後、RESIDENT 區塊之前；`RELAY_START_RE`、`RESIDENT_RE`、`RELAY_DOMS` 摘要與其他既有行一字未動；改的只有 `RELAY_LIST` 的文字 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-040 | 發現 5；作法 1；裁決 1 | 功能 | 本分支 | 讀新的兩個呼叫處與函式 | 兩個變數都經 `relay_env_warn <變數名>` 這同一個函式取值；擷取／去引號／截斷的邏輯只存在函式一處，呼叫處沒有各自的正則或重複程式；兩處各自帶自己的尾句；順序固定先 EXTRA 後 PEER；函式回傳 0＝要警告、1＝不用，結果用全域變數 `RELAY_ENV_HEAD`、`RELAY_ENV_MORE` 交回 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-041 | 完成標準「函式本體只用 bash 內建」；硬規則 | 功能 | 本分支 | 用 `sed -n` 取出 `relay_env_warn` 函式本體後 `grep` 檢查命令替換 `$(`、反引號、`grep`、`jq`、`python`、`sed`、`awk`、`tr`、`mktemp` 等 | 函式本體內找不到任何命令替換或外部程式（hook 逾時＝放行，不能 fork）；`grep` 檢查的輸出貼進 `ledger.md` | 手動：閱卷者自己重跑 `sed -n`＋`grep`，結果記於 `ledger.md` |
| TC-042 | 作法 2「迴圈有上限、不平方」 | 功能 | 本分支 | 讀函式本體的所有迴圈 | 啟動點最多掃 8 個、賦值最多取 20 個，且超過時走「要警告」分支；沒有 `${x//p/}`；沒有在長指令上反覆 `${CMD#*…}`；每個迴圈步驟只做一次正則比對加一次前綴去除 | 手動：閱卷者讀函式，結果記於 `ledger.md` |
| TC-043 | 作法 2「便宜優先」；完成標準成本 | 功能 | 本分支與基底各一份 hook | 用一條約 100 KB、不含 `NF_RELAY_EXTRA_DOMAINS=` 也不含 `NF_RELAY_PEER_PREFIXES=` 的指令，新舊 hook 各用 `time` 跑；函式第一行為子字串比對 `[[ $CMD == *"$1="* ]] \|\| return 1` | 新 hook 不比舊 hook 慢（容許量測誤差）；兩邊數字貼進 `ledger.md` | 手動：閱卷者自己量，結果記於 `ledger.md` |
| TC-044 | 完成標準成本；硬規則逾時＝放行 | 功能 | 本分支與基底；`hooks/hooks.json` 中 confirm_launch 的逾時（目前 30 秒，不改） | 用一條約 100 KB、含 3 個 `egress_ctl.sh start` 與 25 個 `V=` 賦值的指令，新舊 hook 各用 `time` 跑 | 新 hook 的耗時遠低於 `hooks/hooks.json` 裡 confirm_launch 那一項的逾時；數字貼進 `ledger.md` | 手動：閱卷者自己量，結果記於 `ledger.md` |
| TC-045 | 作法 7；硬規則 | 功能 | 本分支 | 讀 `git diff origin/v3...HEAD -- hooks/confirm_launch.sh` 的新增行 | 沒有新增 `allow` 路徑、沒有新增 `exit 0`、沒有新增 `ask` 呼叫；`ask "GATE: this starts…"` 的呼叫與外框文字原樣；`ask()` 未改；警告只附加進同一個 `RELAY_LIST`，由原有的唯一一次 `ask` 送出 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-046 | 完成標準第 1 點 | 功能 | 本分支 | 執行 `bash tests/confirm_launch_test.sh` | 全檔綠（FAIL 數 0），包含本檔所有新增斷言（RWH-1…RWH-26 對應的行）與 5 條改字的既有斷言 | 自動：`tests/confirm_launch_test.sh` |
| TC-047 | 完成標準第 1 點 | 功能 | 本分支，WSL／Linux | 在 WSL 執行 `bash tests/run_all.sh`（見倉庫 CLAUDE.md） | 全套綠 | 自動：`tests/run_all.sh` |
| TC-048 | 「不做」第 2 點（不對其他變數加警告） | 不在範圍 | 本分支與 `ledger.md` | 讀 diff；並送出 `NF_RELAY_PORT=1 bash scripts/egress_ctl.sh start` 與 `NF_RELAY_EXTRA_NOTE=x bash scripts/egress_ctl.sh start` 看詢問文字 | 函式只被這兩個變數名呼叫；兩條指令的詢問文字都不含 `THIS COMMAND ALSO SETS`（沒有對其他環境變數加警告） | 手動：閱卷者自己跑，輸出貼進 `ledger.md` |
| TC-049 | 「不做」第 2 點（間接指派另案） | 不在範圍 | 本分支與 `ledger.md` | 讀 `ledger.md`，並送出 `V=NF_RELAY_PEER_PREFIXES; export $V=evil; bash scripts/egress_ctl.sh start` | `ledger.md` 有一句記載「間接指派（`export $V=…`、`printf -v`、`env -S`）未處理、另開任務」；該指令沒有因本任務而新增警告句（現行也抓不到），閘門仍詢問；沒有偷偷實作間接寫法的偵測 | 手動：閱卷者讀 ledger 並跑一次，結果記於 `ledger.md` |
| TC-050 | 「不做」第 3、5 點（不重做有效性檢查、不展開） | 不在範圍 | 本分支 | 讀函式本體 | 沒有任何前綴合法性檢查（沒有 `[a-z0-9-]` 之類的有效性正則、沒有長度／個數檢查）；沒有 `eval`、沒有展開 `$VAR`／`$(…)`，只照抄字面（RWH-14、RWH-15 已證明顯示的是字面） | 手動：閱卷者讀函式，結果記於 `ledger.md` |
| TC-051 | 裁決 6；裁決二 2（引號形式 `--script "…"` 的誤報已接受） | 不在範圍 | 本分支與 `ledger.md` | 讀 `ledger.md`；送出 `V=ok scripts/on_site.sh --script "${CLAUDE_PLUGIN_ROOT}/scripts/egress_ctl.sh" start` | `ledger.md` 有記一筆「帶引號的 `--script "…"` 會多一句警告，已接受」；這一型**不**被測試鎖定為 lacks，閱卷者不得以它退回（它警告或不警告都可，閘門本身都要詢問） | 手動：閱卷者讀 ledger，結果記於 `ledger.md` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-052 | 憲法第 13 條（安全網做不了事時要說；缺 `jq` 時閘門拒絕它無法排除的東西），檢查＝`tests/confirm_launch_test.sh` 的「no jq」區段 | 功能 | 本分支 | 執行 `bash tests/confirm_launch_test.sh`，看所有「no jq」區段 | 全部維持 ok，與基底相同；新函式只用 bash 內建，沒有讓缺 jq 時的行為變得更容易放行 | 自動：`tests/confirm_launch_test.sh` |
| TC-053 | 安全網：「啟動指令要明示並等使用者明確確認」與倉庫校正失敗 #1、#2（收窄閘門曾放行三種本該擋的形狀；對複合指令的一段豁免讓整行過關） | 功能 | 兩個工作樹：基底與本分支 | 把 TC-029…TC-031 的三條誘餌指令與 TC-033 的比對集，在基底與本分支各送一遍 | 凡基底會 `ask` 的，本分支都 `ask`；on_site.sh 出現在別的命令段、註解、引號負載時，本分支警告文字比基底更多而不是更少（基底被子字串例外藏掉的三型，本分支都有警告句） | 手動：兩邊結果貼進 `ledger.md`，閱卷者自己重跑 |

<!--
Rules for the writer:
- 驗證方式 is 自動 or 手動. 手動 here follows memory/dev-plans/README.md「通例：閱卷看 diff」: evidence goes in ledger.md, not docs/TESTING.md.
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
