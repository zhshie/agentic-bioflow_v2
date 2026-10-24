# 測試案例：中繼啟動閘門對 NF_RELAY_EXTRA_DOMAINS= / NF_RELAY_PEER_PREFIXES= 的警告補強（relay-warning-hardening）

<!--
Written by the verifier (CONTRACT mode) from specs/relay-warning-hardening/plan.md, before any code.
第三版（2026-10-24）：計畫經第二輪 /code-review 後走「簡單路線」（裁決五）：刪掉斷詞器、不再豁免 on_site.sh、不宣稱哪個值生效、只列文字裡每一處 `<VAR>=` 的原文、成本 O(n)。裁決五明文「取代裁決三、裁決四與作法 2–4 的全部解析設計」，所以前兩版的 TC（含 `SETS V=` 主角值、去引號、on_site.sh 豁免、逐字元切段、regex 編譯檢查）整批作廢，本版從 TC-001 重新編號，不沿用舊號。
這個任務沒有 spec.md；依據是 plan.md（A 級、backend）。維護者原話引自計畫「維護者原話」（/code-review 六項發現）、「失敗先行測試」（RWH-1…RWH-21，其中措辭已被裁決五改變者在總覽「對照表」逐條說明）與裁決五。
-->

**規格**：`specs/relay-warning-hardening/plan.md`（本任務沒有 spec.md；衝突時以「裁決五」為最高，其次裁決與裁決二，最後才是作法）　**總覽**：`test-case-overview.md`

白話說明：中繼（relay）是登入節點上替運算節點轉送對外連線的常駐程式。閘門（`hooks/confirm_launch.sh`）在有人要啟動它時會停下來問使用者「要不要允許」。如果那行指令的文字裡出現 `NF_RELAY_EXTRA_DOMAINS=…`（多放行哪些網域）或 `NF_RELAY_PEER_PREFIXES=…`（哪些主機名開頭的機器可以連進中繼），問話文字要有一段警告。這次的新做法很簡單：**只要指令是中繼啟動、而且文字裡任何地方出現 `<變數>=`，就警告；警告不判斷哪一個值會生效（那要懂 shell，hook 做不到），只把每一處出現的原文照抄列給使用者看，並叫他讀整條指令。** 不再因為指令裡有 `on_site.sh` 就免警告。而且這段程式必須夠便宜（hook 逾時＝放行，所以不能慢）。

名詞：

- 「ask」＝閘門停下來問。
- 「V」＝`NF_RELAY_EXTRA_DOMAINS` 與 `NF_RELAY_PEER_PREFIXES` 兩個變數各跑一次（一條 TC 兩條斷言，兩條都要綠）。以下指令中的 `V` 一律代入實際變數名；`okval`、`evilval` 等是任意值。
- 「警告區」＝閘門輸出 JSON 解碼後的 `additionalContext` 欄位。**它不含使用者的指令原文**（指令原文在 `permissionDecisionReason` 欄位）；所以凡是要證明「警告把某段原文列出來」或「警告沒有列出某段原文」，一律只看警告區，不看整份輸出，否則會被指令原文那一份干擾。
- 「標頭」＝警告區含 `THIS COMMAND ALSO MENTIONS V=`（V 代入變數名）。「尾句」＝警告區含 `Read the whole command; the value that takes effect depends on the shell.`。計畫標頭句中間那段括號（`(it would change which hosts/domains the relay accepts)`）的確切字樣計畫沒有定死，本檔不鎖。
- 「N 次句」＝警告區含 `N mentions in total`（N 為該變數在整條指令文字裡出現 `V=` 的次數）。N=1 時複數寫法計畫沒定，本檔只鎖子字串 `1 mention`。
- 「列出原文」＝每一處 `V=` **後面**到下一個空白或 `;` `&` `|` 為止的原樣文字（不去引號、不解析、不展開），每處最多 120 字元。列出的格式（分隔符號、有無 `V=` 前綴）計畫沒定，本檔一律只檢查「警告區含某字串／不含某字串」，不鎖格式。
- 測試輔助函式約定：`envw <label> <變數> <has|lacks> <指令> [必含字串…] [必不含字串…]` 判的是警告區有沒有該變數自己的標頭，並可附必含／必不含字串；沿用既有 `envp`（第 790–797 行，v3）的寫法：用 `python3`（或檔案／標準輸入）組輸入 JSON、`LAB_SETTINGS_FILE="$TMP/id_env.yaml" bash "$H"` 執行、`grep -qF --` 比對（必須先解碼 JSON 再比對，否則含引號的字串會因跳脫而比不到）。`idg` 是既有函式（期望 `ask`／`allow`）。大型指令（≥ 約 30 KB）不能用命令列引數傳給 `python3 -c`（Windows 上限約 32 KB），要用檔案或標準輸入組 JSON。每條「自動」測試要在註解裡寫它的 TC 編號。
- 「手動」＝依 `memory/dev-plans/README.md`「通例：閱卷看 diff」，證據貼進 `specs/relay-warning-hardening/ledger.md`，閱卷者自己重跑核對（不寫進 `docs/TESTING.md`，也不得以「TESTING.md 沒有步驟」退回）。
- 「基底」＝`origin/v3`（已含 #189 的 EXTRA／PEER 兩個警告區塊；計畫開頭「v3 目前沒有 PEER 區塊」的說法已過期）。

類型只有三種：**功能**（計畫說要做到的事，正常情況下做到了）、**例外**（邊角情況或不該被放行／不該被藏掉的情況，系統怎麼反應）、**不在範圍**（計畫明講這次不做的事，測試確認它真的沒做）。

## User Story 1 — 警告把指令文字裡每一處 `V=` 照抄列出來，不宣稱哪個生效（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 裁決五 3（固定標頭）；發現 1「不能只顯示一個」 | 功能 | 閘門已安裝；部署設定檔照 `id_env.yaml` | 對 V 各送出 `V=aaaval bash scripts/egress_ctl.sh start` | 警告區含標頭與尾句；警告區含 `aaaval`；警告區**不含** `THIS COMMAND ALSO SETS`（新警告不再宣稱「這個值會生效」） | 自動：`tests/confirm_launch_test.sh`（`envw`，兩個變數各一條） |
| TC-002 | 發現 1；RWH-1（誘餌 echo） | 功能 | 同上 | 對 V 各送出 `echo V=okval; V=evilval bash scripts/egress_ctl.sh start` | 有標頭；警告區**同時**含 `okval` 與 `evilval`（誘餌與真值都列出，使用者看得到全部）；含 `2 mentions in total`；不含 `THIS COMMAND ALSO SETS` | 自動：同上 |
| TC-003 | 發現 1；RWH-2（同行多重賦值） | 功能 | 同上 | 對 V 各送出 `V=okval V=evilval bash scripts/egress_ctl.sh start` | 有標頭；警告區同時含 `okval` 與 `evilval`；含 `2 mentions in total` | 自動：同上 |
| TC-004 | 發現 1；裁決五 1（文字裡任何地方；審查：啟動點之後的誘餌） | 例外 | 同上 | 對 V 各送出 `V=okval bash scripts/egress_ctl.sh start; echo V=evilval` | 有標頭；警告區同時含 `okval` 與 `evilval`；含 `2 mentions in total` | 自動：同上 |
| TC-005 | 裁決五 1（註解裡也算） | 例外 | 同上 | 對 V 各送出 `bash scripts/egress_ctl.sh start # V=evilval` | 有標頭；警告區含 `evilval`（寧可多警告） | 自動：同上 |
| TC-006 | 裁決五 5（#189 的 export 測試照舊要警告）；既有 `envp` 第三條、PEER-3 | 功能 | 同上 | 對 V 各送出 `export V=evilval; bash scripts/egress_ctl.sh start` | 有標頭；警告區含 `evilval` | 自動：同上 |
| TC-007 | 裁決五 5（env 前綴照舊要警告）；既有 `envp` 第二條、PEER-2；審查：`nohup`／`sudo` 包裝認不得 | 功能 | 同上 | 對 V 各送出四條：`env V=evilval bash scripts/egress_ctl.sh restart`、`nohup V=evilval bash scripts/egress_ctl.sh start`、`sudo V=evilval bash scripts/egress_ctl.sh start`、`nohup env V=evilval bash scripts/egress_ctl.sh start` | 四條都有標頭，警告區都含 `evilval`（不需要認得包裝；文字裡有就警告） | 自動：同上 |
| TC-008 | 裁決五 1；審查：引號字串裡提到 | 例外 | 同上 | 對 V 各送出 `echo 'V=zzval'; bash scripts/egress_ctl.sh start`（`V=` 只在 echo 的引號字串裡） | 有標頭；警告區含 `zzval`；`1 mention` | 自動：同上 |
| TC-009 | 裁決五 1（換行）；發現 2 的換行型 | 例外 | 同上 | 對 V 各送出兩行指令 `$'echo V=evilval\nbash scripts/egress_ctl.sh start'`（`V=` 在第一行，啟動在第二行） | 有標頭；警告區含 `evilval`（同一條指令文字裡有 `V=` 就警告，不管在哪一行） | 自動：同上 |
| TC-010 | 發現 3 改版（裁決五 3「不去引號、不解析」）；審查：跳脫引號讓值吃掉整行 | 功能 | 同上 | 對 V 各送出三條：`V="qq1 rr2" bash scripts/egress_ctl.sh start`；`V='qq1 rr2' bash scripts/egress_ctl.sh start`；`V=a\"b c bash scripts/egress_ctl.sh start`（`\"` 是反斜線加雙引號） | 前兩條：警告區含 `"qq1`（第二條含 `'qq1`），即引號原樣保留、列到第一個空白為止；警告區**不含** `qq1 rr2`（不把引號內空白當同一個值）。第三條：警告區含 `a\"b`，**不含** `a\"b c`（跳脫引號不會把值吃到整行） | 自動：同上（含必不含字串） |
| TC-011 | 發現 3 改版；RWH-13（未加引號的命令替換） | 功能 | 同上 | 對 V 各送出 `V=$(cat /tmp/p) bash scripts/egress_ctl.sh start`；以及加引號的 `V="$(cat /tmp/p)" bash scripts/egress_ctl.sh start` | 兩條都有標頭；警告區含 `$(cat`；第一條警告區**不含** `$(cat /tmp/p)`（列到第一個空白為止）；警告區**不含** `computed at run time`（新警告不判斷值何時算出） | 自動：同上 |
| TC-012 | 「不做」：不展開 `$VAR`／`$(…)`；RWH-15（變數展開） | 不在範圍 | 同上 | 對 V 各送出 `V=$P bash scripts/egress_ctl.sh start`（測試環境不設 `P`） | 有標頭；警告區含字面 `$P`（照抄，沒有被展開成空字串或別的值） | 自動：同上 |
| TC-013 | 裁決五 3（列到下一個空白或 `;&\|` 為止）；既有 PEER-3「值停在分號前」 | 功能 | 同上 | 對 V 各送出三條：`V=aa1;bb2 bash scripts/egress_ctl.sh start`；`V=cc3&dd4 bash scripts/egress_ctl.sh start`；`V=ee5\|ff6 bash scripts/egress_ctl.sh start`（表格內 `\|` 代表直線符號） | 三條都有標頭；警告區依序含 `aa1`、`cc3`、`ee5`；且**不含** `bb2`、`dd4`、`ff6`（值在分隔符號前就停） | 自動：同上 |
| TC-014 | 既有 PEER-4（空值仍要警告） | 功能 | 同上 | 對 V 各送出 `V= bash scripts/egress_ctl.sh start` | 有標頭；含 `1 mention`（空值也算一次，也要警告） | 自動：同上 |
| TC-015 | 裁決五 3「寫 N mentions in total」 | 功能 | 同上 | 對 V 各送出 `V=only1 bash scripts/egress_ctl.sh start` | 有標頭；警告區含 `only1` 與 `1 mention` | 自動：同上 |
| TC-016 | 裁決五 3「最多列前 3 處與最後 1 處」（4 處全列） | 功能 | 同上 | 對 V 各送出 `V=m1x V=m2x V=m3x V=m4x bash scripts/egress_ctl.sh start` | 警告區含 `m1x`、`m2x`、`m3x`、`m4x`（前 3 加最後 1＝全部）與 `4 mentions in total` | 自動：同上 |
| TC-017 | 裁決五 3（5 處：中間 1 處不列） | 功能 | 同上 | 對 V 各送出 `V=m1x V=m2x V=m3x V=m4x V=m5x bash scripts/egress_ctl.sh start` | 警告區含 `m1x`、`m2x`、`m3x`、`m5x` 與 `5 mentions in total`；**不含** `m4x` | 自動：同上 |
| TC-018 | 裁決五 3（6 處：中間 2 處不列） | 功能 | 同上 | 對 V 各送出 `V=m1x V=m2x V=m3x V=m4x V=m5x V=m6x bash scripts/egress_ctl.sh start` | 警告區含 `m1x`、`m2x`、`m3x`、`m6x` 與 `6 mentions in total`；**不含** `m4x`、`m5x` | 自動：同上 |
| TC-019 | 裁決五 3「每處截 120 字元」 | 功能 | 同上 | 對 V 各送出值為 250 個 `x` 的指令：`V=<250 個 x> bash scripts/egress_ctl.sh start` | 警告區含連續 120 個 `x`，且**不含**連續 121 個 `x`（只看警告區；指令原文在另一欄不影響） | 自動：同上 |
| TC-020 | 裁決五 1（「整條指令文字裡任何地方含 `<VAR>=`」，不要求左邊字界）；舊審查：沒有左邊字界 | 例外 | 同上 | 對 V 各送出 `MY_V=zzval bash scripts/egress_ctl.sh start`（例如 `MY_NF_RELAY_PEER_PREFIXES=zzval`） | 有標頭（多警告一個同名後綴變數無害；少警告才有害）；警告區含 `zzval` | 自動：同上 |
| TC-021 | 既有 PEER-6（兩變數並存、先 EXTRA 後 PEER）；裁決五 3 | 功能 | 同上 | 送出 `NF_RELAY_EXTRA_DOMAINS=e1v NF_RELAY_PEER_PREFIXES=p1v NF_RELAY_PEER_PREFIXES=p2v bash scripts/egress_ctl.sh start` | 警告區有 EXTRA 標頭也有 PEER 標頭；EXTRA 標頭出現在 PEER 標頭之前；EXTRA 那段含 `e1v` 與 `1 mention`、PEER 那段含 `p1v`、`p2v` 與 `2 mentions in total`（兩個變數各自計次） | 自動：同上（沿用既有 `envq_order` 判順序） |

## User Story 2 — 不再豁免 on_site.sh：指令文字裡只要出現 `V=` 就警告（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 裁決五 2；發現 2；RWH-11（對照：舊版免警告，新版要警告） | 功能 | 閘門已安裝；設定檔照 `id_env.yaml` | 對 V 各送出 `V=okval bash scripts/on_site.sh egress_ctl.sh start` | 有標頭；警告區含 `okval`（經 on_site.sh 也警告：正常的 on_site.sh 路徑從設定檔帶值，文字裡不會出現 `V=`，出現了就是要讀的東西） | 自動：`tests/confirm_launch_test.sh`（`envw` has） |
| TC-023 | 裁決五 2；RWH-12（對照：`--script` 形式） | 功能 | 同上 | 對 V 各送出 `V=okval scripts/on_site.sh --script scripts/egress_ctl.sh start` | 有標頭；警告區含 `okval` | 自動：同上 |
| TC-024 | 裁決五 2；審查：`on_site.sh env V=evil egress_ctl.sh start` 繞過豁免 | 例外 | 同上 | 對 V 各送出三條：`scripts/on_site.sh env V=evilval egress_ctl.sh start`；`env V=okval bash scripts/on_site.sh egress_ctl.sh start`；`V=okval sh scripts/on_site.sh egress_ctl.sh start` | 三條都有標頭，警告區分別含 `evilval`、`okval`、`okval` | 自動：同上 |
| TC-025 | 發現 2；RWH-6（on_site.sh 出現在別的命令） | 例外 | 同上 | 對 V 各送出 `bash scripts/on_site.sh status; V=evilval bash scripts/egress_ctl.sh start` | 有標頭；警告區含 `evilval` | 自動：同上 |
| TC-026 | 發現 2；RWH-7（尾端註解） | 例外 | 同上 | 對 V 各送出 `V=evilval bash scripts/egress_ctl.sh start # on_site.sh` | 有標頭；警告區含 `evilval` | 自動：同上 |
| TC-027 | 發現 2；RWH-8（上一行的註解） | 例外 | 同上 | 對 V 各送出 `$'# on_site.sh\nV=evilval bash scripts/egress_ctl.sh start'` | 有標頭；警告區含 `evilval` | 自動：同上 |
| TC-028 | 發現 2；RWH-9（on_site.sh 的引號負載；現行 hook 把這型藏掉了） | 例外 | 同上 | 對 V 各送出 `scripts/on_site.sh 'V=evilval bash scripts/egress_ctl.sh start'` | 有標頭；警告區含 `evilval` | 自動：同上 |
| TC-029 | 發現 2；RWH-10（兩個啟動點） | 例外 | 同上 | 對 V 各送出 `scripts/on_site.sh egress_ctl.sh start; V=evilval bash scripts/egress_ctl.sh start` | 有標頭；警告區含 `evilval` | 自動：同上 |
| TC-030 | 裁決五 2「指令文字裡不會出現 `<VAR>=`」的正常路徑（對照：沒有 `V=` 就不誤報，但閘門照問） | 功能 | 同上 | 送出 `scripts/on_site.sh egress_ctl.sh start`（文字裡沒有任何 `V=`）；並以 `idg` 判閘門 | 兩個變數的標頭都**沒有**出現（不誤報）；`idg` 結果仍是 `ask` | 自動：`envw` lacks（兩變數）＋`idg` ask |

## User Story 3 — PEER 警告說真話；既有的其他文字不亂動（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-031 | 發現 4；RWH-19 | 功能 | 閘門已安裝；設定檔照 `id_env.yaml` | 送出 `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh start`，看警告區 | 含 `Entries that are not valid are dropped`（說明無效項目會被丟掉） | 自動：`tests/confirm_launch_test.sh`（既有 `envq_txt`） |
| TC-032 | 發現 4；RWH-20 | 功能 | 同上 | 送出同一條指令 | 含 `falls back to the built-in one`（說明全部無效時退回內建清單） | 自動：同上 |
| TC-033 | 發現 4；裁決 5；RWH-21 | 功能 | 同上 | 送出同一條指令；再送出 `NF_RELAY_PEER_PREFIXES= bash scripts/egress_ctl.sh start`（空值） | 兩條的警告區（以及整份輸出）都**不含** `cpn,gpn,bgm,lgn,localhost`（不寫死預設清單） | 自動：同上（反向字串） |
| TC-034 | 作法 5；裁決 5 | 功能 | 本分支 | 執行 `grep -c 'cpn,gpn,bgm,lgn,localhost' hooks/confirm_launch.sh` | 結果為 0（連 hook 原始碼裡都沒有抄一份預設清單） | 手動：閱卷者自己跑，輸出貼進 `ledger.md` |
| TC-035 | 作法 5「空值說明句保留、措辭不變」（裁決五只取代作法 2–4，未取消作法 5） | 功能 | 同上 | 送出 `NF_RELAY_PEER_PREFIXES= bash scripts/egress_ctl.sh start`；對 `NF_RELAY_EXTRA_DOMAINS= bash scripts/egress_ctl.sh start` 也送一次 | PEER：警告區仍含 `An empty value is ignored by the relay, which then uses the deployment's relay_peer_prefixes setting.`（與基底該句逐字相同）；EXTRA：警告區**不含**這一句 | 自動：同上（`envq_txt`＋反向字串） |
| TC-036 | 「不做」：不改 EXTRA 訊息尾句；裁決五 5（EXTRA 的 envp 測試照舊）；既有 `envp` 四條與 PEER-7「peer-only does not use the extra wording」 | 功能 | 本分支 | 執行既有斷言：`envp` 的 env 前綴、env、export 三條必須 has（警告區含 `overrides this deployment's list`），`bash scripts/egress_ctl.sh start` 必須 lacks；PEER-only 指令 `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh start` 警告區**不含** `overrides this deployment's list` | 全部 ok，且這四條 `envp`（第 798–801 行）與 PEER-7 那一條**一字未改** | 自動：`tests/confirm_launch_test.sh`（既有斷言，不改） |
| TC-037 | 作法 5「看中繼啟動訊息的實際清單」；裁決五 3 | 功能 | 本分支 | 讀 hook 裡 PEER 警告的文字 | 文字有一句叫使用者去看中繼啟動時印出的實際清單（而不是在 hook 內宣稱清單是什麼）；`ledger.md` 貼出這句的位置 | 手動：閱卷者讀 hook，結果記於 `ledger.md` |

## User Story 4 — 閘門只會更強不會更弱、夠便宜（O(n)）、改動範圍只有三個檔、兩個警告共用一段程式（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-038 | 硬規則；RWH-16 | 例外 | 閘門已安裝；設定檔照 `id_env.yaml` | 以 `idg` 送出 `echo NF_RELAY_PEER_PREFIXES=okval; NF_RELAY_PEER_PREFIXES=evilval bash scripts/egress_ctl.sh start` | 結果是 `ask` | 自動：`tests/confirm_launch_test.sh`（`idg` ask） |
| TC-039 | 硬規則；RWH-17 | 例外 | 同上 | 以 `idg` 送出 `bash scripts/on_site.sh status; NF_RELAY_PEER_PREFIXES=evilval bash scripts/egress_ctl.sh start` | 結果是 `ask` | 自動：同上 |
| TC-040 | 硬規則；RWH-18 | 例外 | 同上 | 以 `idg` 送出 `scripts/on_site.sh 'NF_RELAY_PEER_PREFIXES=evilval bash scripts/egress_ctl.sh start'` | 結果是 `ask` | 自動：同上 |
| TC-041 | 硬規則「現在會詢問的每一種情況仍要詢問」；既有 PEER-12 八條與整個 `idg`／`idw` 組 | 例外 | 本分支 | 執行 `bash tests/confirm_launch_test.sh`，看既有 `idg`／`idw` 全部斷言（含 PEER-12：start、env restart、export start、空值、引號路徑、兩變數、via on_site.sh、plain start） | 全部維持 ok，一條都沒由 ask 變 allow；其中沒有任何 `idg` 斷言被改（標籤、指令、期望都原樣） | 自動：`tests/confirm_launch_test.sh`（既有斷言，不改） |
| TC-042 | 完成標準「不更弱」比對；裁決五 6；倉庫校正失敗 #1、#2 | 例外 | 兩份 hook：基底 `origin/v3` 與本分支 | 把兩份 hook 各餵同一批 **≥60 條**指令（含：本檔所有新增 TC 的指令各變數各一份、既有 EXTRA／PEER 全部指令、`bash scripts/egress_ctl.sh start\|stop\|restart\|status`、`bash scripts/agent_ctl.sh start`、`NF_RELAY_PORT=1 bash scripts/egress_ctl.sh start`、一條不相關的 `ls`、一條 70 KB 與一條 1 MB 的超長指令），比對 `permissionDecision`；再比對警告：基底輸出含 `THIS COMMAND ALSO SETS V` 的每一條指令，本分支輸出都含 `THIS COMMAND ALSO MENTIONS V=`。閱卷者自己重跑 | 新 hook 的 `ask` 集合**包含**基底的 `ask` 集合（其餘指令兩邊一致，`ls` 兩邊都放行）；基底有警告的，本分支一定也有警告（只會多、不會少）；比對表貼進 `ledger.md` | 手動：兩邊輸出比對表貼進 `ledger.md` |
| TC-043 | 完成標準「兩個分支各跑一遍」；倉庫校正失敗 #1 | 功能 | 兩個工作樹：基底與本分支 | 兩邊各跑 `bash tests/confirm_launch_test.sh`，輸出存檔逐行比對（閱卷者自己重跑，不只信 ledger） | 差異只有兩類：被改字（或被改鍵）的既有斷言（TC-044 規定的範圍），與新增的測試行；其餘每一行 ok／FAIL 狀態完全相同；本分支 FAIL 數為 0 | 手動：比對結果貼進 `ledger.md` |
| TC-044 | 裁決五 5「措辭改變的斷言逐條列在 ledger（以前／以後）」；維護者原則「既有斷言除訊息措辭外不得改」 | 功能 | 本分支與 `ledger.md` | 讀 `git diff origin/v3...HEAD -- tests/confirm_launch_test.sh` 的刪除行（被刪再加的既有行） | 被改的既有斷言只有兩類：(1) 因標頭／訊息措辭改變而改「必含字串」或判斷用的標頭字串（`envq` 內的 `THIS COMMAND ALSO SETS …`、PEER-3／4／7 的 `${PW_SETS}…, which changes` 等）；(2) **PEER-9**（`NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/on_site.sh egress_ctl.sh start`）的期望由 `lacks` 改成 `has`（裁決五 2：不再豁免 on_site.sh），標籤同步改。除此之外，每條既有斷言的指令、`has`／`lacks`／`ask`／`allow` 期望都不得變；沒有被跳過、被放寬或被刪的既有斷言；`envp` 四條、PEER-1／2／5／6／8／10／11 的 has／lacks 期望不變；`ledger.md` 逐條貼出改前／改後 | 手動：閱卷者重跑 `git diff`，結果記於 `ledger.md` |
| TC-045 | 倉庫校正失敗 #1（只靠新測試會漏）；維護者「失敗先行」 | 功能 | 本分支與基底 hook | 把新增的測試行對基底 hook 跑一遍 | 新增行中至少涵蓋誘餌（TC-002／004）、on_site.sh 不豁免（TC-022…TC-029）、標頭措辭（TC-001）的測試在基底上為 FAIL（舊紅）；同一批在本分支全綠；紅的清單貼進 `ledger.md` | 手動：結果記於 `ledger.md` |
| TC-046 | 發現 5；作法 1；裁決 1；裁決五 1「共用一個很小的 helper」 | 功能 | 本分支 | 讀新的兩個呼叫處與 helper | 兩個變數都經同一個 helper 取得標頭、列表與次數；計次、取原文、截斷的邏輯只存在 helper 一處，呼叫處沒有各自的重複程式；兩處順序固定先 EXTRA 後 PEER；EXTRA 與 PEER 各自帶自己的尾句；舊的 `relay_env_word`、`relay_env_seg`、`relay_env_exempt`、`RELAY_ENV_RE_*` 這一整組斷詞器已不存在（`grep` 為 0）；`ledger.md` 貼出 helper 行數 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-047 | 完成標準「函式本體只用 bash 內建」；裁決五 4（O(n) 的寫法） | 功能 | 本分支 | 用 `sed -n` 取出 helper 本體後檢查 | (a) 沒有命令替換 `$(`（`$((` 算術除外）、反引號（寫在字串字面值裡的不算）、也沒有 `grep`、`jq`、`python`、`sed`、`awk`、`tr`、`mktemp`、`eval`；(b) 沒有任何 `^(.*)` 或帶貪婪 `.*` 後面還必須相符的 regex；(c) 次數用一次 `${CMD//"$V="/}` 的長度差除以字串長算出，前 3 處用 `${x#*"$V="}` 最多 3 次、最後 1 處用一次 `${CMD##*"$V="}`，沒有逐次剝前綴的迴圈；(d) 第一步是便宜的子字串比對（沒帶該變數的指令馬上返回）；(e) 沒有切段、辨認引號、豁免 on_site.sh 的程式；輸出貼進 `ledger.md` | 手動：閱卷者自己重跑 `sed -n`＋`grep`，結果記於 `ledger.md` |
| TC-048 | 裁決五 4；成本 O(n)（60 KB、`V=` 在尾端） | 功能 | 設定檔照 `id_env.yaml`；測試用檔案或標準輸入組 JSON | 對 V 各送出約 60,000 字元的指令：`echo ` 後接約 59,900 個 `y`，再接 `; V=tail1 bash scripts/egress_ctl.sh start`；量 hook 執行時間 | 警告區含標頭、`tail1` 與 `1 mention`；閘門 `ask`；整次 hook 執行 < 0.5 秒 | 自動：`tests/confirm_launch_test.sh` |
| TC-049 | 裁決五 4；成本 O(n)（60 KB、`V=` 遍布全文）；審查：計數迴圈在 60 KB 仍是平方時間 | 功能 | 同上 | 對 V 各送出約 60,000 字元的指令：`echo ` 後接 500 個單位（每個單位＝`V=sc7`、一個空白、92 個 `y`、一個空白），再接 `; bash scripts/egress_ctl.sh start`；量 hook 執行時間 | 警告區含標頭與 `500 mentions in total`（次數要精確）；閘門 `ask`；整次 hook 執行 < 0.5 秒 | 自動：同上 |
| TC-050 | 裁決五 4「超過 64 KB 不列原文，只印標頭與次數」；硬規則（不解析也要問） | 例外 | 同上 | 對 V 各送出約 70,000 字元的指令：`echo ` 後接 500 個單位（每個單位＝`V=sc7`、一個空白、112 個 `y`、一個空白），再接 `; bash scripts/egress_ctl.sh start`（遠離 64 KB 邊界，避開 65536／64000 之爭） | 警告區含標頭與 `500 mentions in total`；警告區**不含** `sc7`（沒有列原文）；以 `idg` 判閘門仍是 `ask` | 自動：同上 |
| TC-051 | 裁決五 4（1 MB < 1 秒）；審查：逾時＝放行 | 例外 | 同上；JSON 要用檔案或標準輸入組 | 對 V 各送出兩條約 1,000,000 字元的指令並量 hook 執行時間：(a) 尾端型：`echo ` 後接約 1,000,000 個 `y`，再接 `; V=tail1 bash scripts/egress_ctl.sh start`；(b) 遍布型：`echo ` 後接 8,000 個單位（每個單位＝`V=sc7`、一個空白、97 個 `y`、一個空白），再接 `; bash scripts/egress_ctl.sh start` | 兩條都：有標頭、警告區不含 `tail1`／`sc7`（不列原文）、閘門 `ask`、整次 hook 執行 < 1 秒；(b) 另含 `8000 mentions in total` | 自動：同上 |
| TC-052 | 完成標準「成本」；硬規則逾時＝放行 | 功能 | 基底與本分支各一份 hook | 用一條約 100 KB、不含 `NF_RELAY_EXTRA_DOMAINS=` 也不含 `NF_RELAY_PEER_PREFIXES=` 的指令，新舊 hook 各用 `time` 跑 | 新 hook 不比基底慢（容許量測誤差）；兩邊數字貼進 `ledger.md`，閱卷者自己重量 | 手動：結果記於 `ledger.md` |
| TC-053 | 完成標準「成本」 | 功能 | 基底與本分支；`hooks/hooks.json` 中 confirm_launch 的逾時（30 秒，不改） | 用一條約 100 KB、含 3 個 `egress_ctl.sh start` 與 25 個 `V=` 的指令，新舊 hook 各用 `time` 跑 | 新 hook 耗時遠低於逾時；數字貼進 `ledger.md`，閱卷者自己重量 | 手動：結果記於 `ledger.md` |
| TC-054 | 範圍：檔案（共 3 個） | 不在範圍 | 本分支 | `git diff --name-only origin/v3...HEAD` | 實作檔只出現 `hooks/confirm_launch.sh`、`tests/confirm_launch_test.sh`、`specs/relay-warning-hardening/ledger.md`（計畫與規定的 TC 檔另計）；沒有其他檔 | 手動：閱卷者重跑，結果記於 `ledger.md` |
| TC-055 | 範圍：禁止碰；「不做」第 1、4 點 | 不在範圍 | 本分支 | `git diff origin/v3...HEAD -- scripts/ platform/ docs/ skills/ deploy/ commands/ hooks/hooks.json` | 輸出為空 | 手動：閱卷者重跑，結果記於 `ledger.md` |
| TC-056 | 完成標準「hook diff 只替換兩個區塊」；作法 7、8；「不改 `ask()`」 | 功能 | 本分支 | 讀 `git diff origin/v3...HEAD -- hooks/confirm_launch.sh` | 既有行被改／刪的只有原 EXTRA 與 PEER 兩個警告區塊；新增的 helper 位置在 `ask()` 之後、RESIDENT 區塊之前；`RELAY_START_RE`、`RESIDENT_RE`、`RELAY_DOMS` 摘要與其他既有行一字未動；沒有新增 `allow` 路徑、沒有新增 `exit 0`、沒有新增 `ask` 呼叫；`ask "GATE: this starts…"` 的呼叫與外框文字原樣；警告只附加進同一個 `RELAY_LIST`；`hooks/hooks.json` 未動 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-057 | 完成標準第 1 點 | 功能 | 本分支 | 執行 `bash tests/confirm_launch_test.sh` | 全檔綠（FAIL 數 0），包含本檔所有新增斷言 | 自動：`tests/confirm_launch_test.sh` |
| TC-058 | 完成標準第 1 點 | 功能 | 本分支，WSL／Linux | 在 WSL 執行 `bash tests/run_all.sh`（見倉庫 CLAUDE.md） | 全套綠（若有失敗，須證明基底同樣失敗且不在本任務範圍，記於 `ledger.md`） | 自動：`tests/run_all.sh` |
| TC-059 | 「不做」第 2 點（不對其他環境變數加警告） | 不在範圍 | 同 TC-001 | 送出 `NF_RELAY_PORT=1 bash scripts/egress_ctl.sh start` 與 `NF_RELAY_EXTRA_NOTE=x bash scripts/egress_ctl.sh start`；並讀 diff 看 helper 被誰呼叫 | 兩條指令的警告區都**不含** `THIS COMMAND ALSO MENTIONS`；helper 只被 `NF_RELAY_EXTRA_DOMAINS`、`NF_RELAY_PEER_PREFIXES` 兩個變數呼叫 | 自動：`envw` lacks（兩條）＋手動讀 diff 記於 `ledger.md` |
| TC-060 | 「不做」第 2 點、裁決二 3（間接指派另案） | 不在範圍 | 本分支與 `ledger.md` | 讀 `ledger.md`；送出 `P=NF_RELAY_PEER_PREFIXES; export $P=evilval; bash scripts/egress_ctl.sh start` | `ledger.md` 有一句記載「間接指派（`export $V=…`、`printf -v`、`env -S`）未處理、另開任務」；該指令沒有因本任務而新增警告標頭（沒有偷偷實作間接寫法的偵測），閘門仍 `ask` | 手動：閱卷者讀 ledger 並跑一次，結果記於 `ledger.md` |
| TC-061 | 「不做」第 3、5 點（不重做 `nf_relay.py` 的有效性檢查、不展開、不解析）；裁決五 3「不去引號、不解析」 | 不在範圍 | 本分支 | 讀 helper | 沒有任何前綴合法性檢查（沒有 `[a-z0-9-]` 之類的有效性正則、沒有長度／個數檢查）；沒有 `eval`、沒有展開 `$VAR`／`$(…)`、沒有去引號、沒有判斷「值何時算出」的程式；只照抄字面 | 手動：閱卷者讀函式，結果記於 `ledger.md` |
| TC-062 | 裁決五 5「審查兩輪共 14 點逐條對應『新規格下不再適用的理由』或『對應測試』，寫進 ledger」 | 功能 | 本分支與 `ledger.md` | 讀 `ledger.md` 的對應表 | 表中恰好列出 14 點（第一輪 8 點＋第二輪 6 點），每一點都有一條「不再適用的理由」或一個具名的 TC／測試行；第二輪的 6 點至少含：計數迴圈平方時間→TC-049／TC-051；`on_site.sh env V=evil egress_ctl.sh start` 繞過→TC-024；最後一個值不一定生效→TC-001／TC-002；跳脫引號吃整行→TC-010；`nohup`／`sudo` 包裝→TC-007；閱卷者核對每點的對應真的存在 | 手動：閱卷者讀 ledger 並抽查，結果記於 `ledger.md` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-063 | 安全網：「A launch command is shown in full and waits for explicit confirmation before it runs」，檢查＝`hooks/confirm_launch.sh` 與 `tests/confirm_launch_test.sh`；倉庫校正失敗 #1、#2（收窄閘門曾放行本該擋的形狀；對複合指令的一段豁免讓整行過關） | 功能 | 兩個工作樹：基底與本分支 | 把 TC-038…TC-040 的三條誘餌、TC-050／TC-051 的超長指令、TC-042 的比對集在基底與本分支各送一遍 | 凡基底會 `ask` 的，本分支都 `ask`；on_site.sh 出現在別的命令段、註解、引號負載、或作為參數時，本分支的警告文字比基底更多而不是更少；hook 內沒有任何 on_site.sh 豁免殘留（`grep -n on_site` 在 helper 與兩個呼叫處為 0） | 自動：`tests/confirm_launch_test.sh`（TC-038…TC-041、TC-050、TC-051）；比對結果手動貼進 `ledger.md` |
| TC-064 | 憲法第 13 條（安全網做不了事時要說；缺 `jq` 時閘門拒絕它無法排除的東西），檢查＝`tests/confirm_launch_test.sh` 的「no jq」區段 | 功能 | 本分支 | 執行 `bash tests/confirm_launch_test.sh`，看所有「no jq」區段 | 全部維持 ok，與基底相同；新 helper 只用 bash 內建，沒有讓缺 jq 時的行為變得更容易放行 | 自動：`tests/confirm_launch_test.sh` |

<!--
Rules for the writer:
- 驗證方式 is 自動 or 手動. 手動 here follows memory/dev-plans/README.md「通例：閱卷看 diff」: evidence goes in ledger.md, not docs/TESTING.md.
- IDs are never renumbered after approval; a removed case keeps its row, struck through. 本版（第三版）是整批重編：前兩版的 TC 編號作廢，不與本版對應。
- 專長守則（backend）：本任務沒有新增網頁／API／聊天指令、沒有使用者紀錄、沒有資料結構變動，對等性、跨使用者、migration 規則不適用（不需要 migration）；「確認管道」精神由閘門本身承擔，由 TC-038…TC-041、TC-050、TC-051、TC-063 證明閘門仍在且不更弱；錯誤訊息與日誌不含密鑰：警告只回顯指令中使用者自己寫的 `V=` 後面的字面，不涉及密鑰（閱卷時一併檢視 TC-010、TC-011 的輸出）。
-->
