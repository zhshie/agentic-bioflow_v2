---
id: relay-warning-polish
title: 轉送啟動警告的顯示細節：截斷處標 …、第 4～n-1 處未列要說、引號內的值顯示到收尾引號、64 KB 以上說明值沒列、空值說明只看最後一處、變數名要有左邊字界
tier: A
kinds: backend
lane: L-relay（只動 hooks/confirm_launch.sh 與 tests/confirm_launch_test.sh；不與其他任務的檔案相交）
base: v3
after: relay-warning-hardening
source: PR #196 上第三輪 /code-review 的六項顯示類發現；memory/dev-queue.json 的 relay-warning-polish 條
---

# relay-warning-polish

> 本檔由 developer-agent 起草（2026-10-24）。A 級：只改「警告文字怎麼寫」，不新增解析器，閘門仍然每次詢問並印整條指令 → verifier 通過＋CI 綠由 developer-agent 自合。
> **`hooks/` 是受保護路徑**：developer-agent 必須在 PR 上跑 `/code-review`。
> **前置**：PR #196（`relay-warning-hardening`）已合進 `v3`。以下行號是 `origin/v3` 的 `hooks/confirm_launch.sh` 與 `tests/confirm_launch_test.sh`（`git -C <repo> fetch -q origin` 後用 `MSYS_NO_PATHCONV=1 git -C <repo> show "origin/v3:<path>"` 讀）；行號若漂移以內容為準。

## 目標
中繼啟動（`egress_ctl.sh start|restart`）的確認詢問，對指令文字裡提到的 `NF_RELAY_EXTRA_DOMAINS=` 與 `NF_RELAY_PEER_PREFIXES=`，所列出的原文要「看得出哪裡被截掉、哪些沒列、引號內的值是整個」，而且「只因為名字尾巴相同的別的變數（`MY_NF_RELAY_EXTRA_DOMAINS=`）」不再誤報。對使用者的意義：他按「允許」前看到的警告不會因為被悄悄截短而誤導他。**閘門本身（詢問、整條指令的顯示）完全不變。**

## 維護者原話（verifier 出題用）
第三輪 /code-review 的六項發現（任務指示，developer-agent 2026-10-24 轉述）：
1. 被截斷的原文沒有標記 → 在 120 字元處截斷，或在引號沒關的情況下於分隔符處截斷時，尾端加 `…`。
2. 第 4～n-1 處沒列出 → N>4 時加一行 `(mentions 4 to N-1 are not listed; read the whole command shown below)`。
3. 雙引號或單引號的值在引號內第一個空白就被截斷 → `<VAR>=` 後面緊接引號時，顯示到對應的收尾引號（仍受 120 字元＋`…` 限制）；不去跳脫、不展開。
4. 超過 64 KB 的路徑 → 也要說 `the values are not listed because the command is over 64 KB; read the whole command shown below`。
5. 空值說明（只有 PEER）要依「最後一處」判斷，超過 64 KB 的路徑在「最後一處是空的」且能便宜知道時也要出現（最後一處用 `${CMD##*"$V="}` 取），EXTRA 不得去算。
6. 左邊字界：`MY_NF_RELAY_EXTRA_DOMAINS=` 不算一處提到（前一個字元必須是字串開頭、空白、tab、換行、`;&|(` 或引號），仍須 O(n)，並說明怎麼做到。
硬規則（任務指示）：不新增任何解析器；不改變「哪些指令會警告／詢問」到更弱；不能比現在慢（既有計時測試照留）。

## 範圍：檔案（只准改這些，共 3 個）
- `hooks/confirm_launch.sh`（只動 `relay_env_warn` 函式本體 `:308-348` 與 PEER 那一次呼叫 `:458`、其後的空值判斷 `:461-464`；函式上方的說明註解 `:294-307` 同步改字）
- `tests/confirm_launch_test.sh`（新增一個區塊，緊接 `envbig` 迴圈 `:968-974` 之後；`envbig` 的 python 片段 `:947-957` 新增兩種 kind；另有 2 條既有斷言因規格改變而改，清單見「失敗先行測試」末尾）
- `specs/relay-warning-polish/ledger.md`（新，executor 進度帳本）

**禁止碰**：`scripts/`、`platform/`、`docs/`、`skills/`、`deploy/`、`commands/`、`hooks/hooks.json`；`ask()`（`hooks/confirm_launch.sh:289`）；`RELAY_START_RE`（`:432`）；EXTRA 呼叫的文字（`:452`）與 PEER 呼叫的結尾句文字（`:458`）。

## 作法
**現況（`origin/v3`）**：`relay_env_warn <變數名> <結尾句>`（`hooks/confirm_launch.sh:308`）。第一行 `case $CMD in *"$V="*)` 沒帶就 `return 1`（`:311`）。計次用 8 KB 視窗：`x=${CMD:i:win}; gone=${x//"$V="/}`，次數＝長度差除以 `${#V}+1`（`:321-325`），期間 `LC_ALL=C`（`:319-326`）。超過 64 KB（`:329`）只印標頭與次數（`:330`）。否則取前 3 處（`for k in 1 2 3`，`:333-338`）與最後 1 處（`${CMD%"$V="*}`，`:340`），每處 `${t:0:120}`（`:337`、`:342`），每處只要原文是空的就設 `RELAY_ENV_EMPTY=1`（`:336`、`:341`）。PEER 呼叫端用它印空值說明（`:461-464`）。

以下是決定，不是程式碼：

1. **新增第三個參數** `relay_env_warn <變數名> <結尾句> [empty]`。只有第三個參數等於字串 `empty` 時才算 `RELAY_ENV_EMPTY`（PEER 的呼叫 `:458` 傳 `empty`；EXTRA 的呼叫 `:452` 不傳，函式內任何地方都不得為 EXTRA 算空值）。**空值只看「最後一處」（有效的最後一處，見 4）**：不再因為前 3 處裡有空的就設 1。
2. **左邊字界（發現 6），保持 O(n)**：
   - 字界字元集合放在一個區域變數 `nb=$' \t\n;&|(\"\''`（空白、tab、換行、`;`、`&`、`|`、`(`、`"`、`'`）。
   - 在現有每個 8 KB 視窗迴圈裡，**多做一次**同形式的移除：`y=${CMD:i-1:win+1}`（`i>0` 時視窗往左多取 1 個字元，讓視窗第一個位置的提到也看得到前一個字元；`i=0` 時用 `${CMD:0:win}`），`gone2=${y//[!$nb]"$V="/}`，壞提到數 `nbad += (${#y} - ${#gone2}) / (${#V} + 2)`。「壞」＝前一個字元不在字界集合內。字串開頭的提到沒有前一個字元，自然不會被這個式子數到，所以不算壞。
   - 有效提到數 `n = nraw - nbad`。`n` 為 0 → `return 1`（不警告）。
   - 為什麼 O(n)：每個視窗各做一次 `${y//pat/}`（現有那一次加這一次），視窗長度固定（約 8 KB），視窗數 = 長度/8 KB；沒有逐次剝前綴、沒有 `^(.*)`、沒有子行程、沒有命令替換。
   - **往安全方向的誤差**：左邊字元恰好是另一個提到的最後一個字元（`V=V=x`，兩個 `=` 相連的怪形）時，`[!$nb]` 會被前一個提到吃掉，壞數少算，有效數多算 → 只會多警告，不會少。
3. **列出前 3 處與最後 1 處時，跳過壞提到**：往前掃的迴圈每一圈取一個原始提到，看它前一個字元是否在字界集合內（`prev=${x_before: -1}`；第一圈前面沒有字元＝字串開頭＝好）；好的才算進「前 3 處」。往後取最後一處也一樣：`t=${CMD%"$V="*}`，前一個字元是 `${t: -1}`，壞的就繼續 `t=${t%"$V="*}` 往前找。**步數上限：往前 20 圈、往後 20 圈**（只在 ≤64 KB 時跑，所以每圈成本有界）。任一方向用完上限還沒湊到所需的好提到 → **不列原文**，改走和「超過 64 KB」同形的輸出（標頭＋次數＋下面 6 的那一行，但原因改寫成 `the values are not listed because the command has too many names that only end in ${V}; read the whole command shown below`）。寧可不列也不能列錯。
4. **「最後一處」的定義**：好的提到裡位置最後的一個（跳過壞的）。空值說明只看它。
5. **值的取法（發現 3、1）**，對每個要列的好提到，`x` ＝該提到的 `=` 後面到字串尾的文字：
   - **x 的第一個字元是 `"` 或 `'`**：令 `q` 為該字元，`rest=${x:1:120}`（只看前 120 字元，成本有界），`pre=${rest%%"$q"*}`。若 `${#pre} < ${#rest}`（120 字元內找到收尾引號）→ 值＝`${x:0:${#pre}+2}`（含兩側引號，**照原樣保留引號**）；收尾引號後面的下一個字元若存在且不是 `[[:space:];&|]` → 值後面加 `…`（值還在繼續，例 `"a b"c`）。若 120 字元內找不到收尾引號 → 退回下面的「一般取法」，並**一定**加 `…`（引號沒關）。
   - **一般取法**：與現在相同，`t=${x%%[[:space:];&|]*}`，顯示 `${t:0:120}`。加 `…` 的條件：`${#t} > 120`；或 `t` 的前 120 字元裡 `"` 的個數是奇數、或 `'` 的個數是奇數（引號沒關就在分隔符處被切）。個數用 `${s//[!\"]/}` 取長度，`s` 只是那 ≤120 字元，成本有界。
   - 不去跳脫、不展開、不解析（`a\"b` 只算一個 `"`，會多一個 `…`，是可接受的誤差，方向是多提醒）。
   - 顯示格式不變：`[值]`，`…` 放在右括號之前，例 `[xxxx…]`；`Text after each ${V}= as written (first 3 and last 1 of them): …; N mention(s) in total.` 整行格式不變（既有斷言靠它，`tests/confirm_launch_test.sh:830`、`:832`、`:837`、`:931`）。
6. **未列出的說明（發現 2、4）**：
   - N=5 → 在 `Text after each…` 那行之後加一行 `(mention 4 is not listed; read the whole command shown below)`；N≥6 → `(mentions 4 to N-1 are not listed; read the whole command shown below)`（N-1 換成數字）。N≤4 不加。（N=5 時把複數改單數是為了不寫出「4 to 4」；這是單一細節決定，任務指示的字面是 `4 to N-1`。）
   - 超過 64 KB 的路徑：現有一行改成 `${n} ${w} in total.`（拿掉括號裡的 `(the command is over 64 KB, so the text after each is not listed)`，`:330`），其後另起一行 `The values are not listed because the command is over 64 KB; read the whole command shown below.` 其他字不動。
7. **超過 64 KB 路徑的空值說明（發現 5）**：只在第三參數為 `empty` 時才做。取最後一處：`t=${CMD%"$V="*}`，前一個字元 `${t: -1}` 在字界集合內才有效；有效時 `x=${CMD:${#t}+${#V}+1}`，用第 5 點的取法（只看前 120 字元；`""`／`''` 兩個緊鄰的引號也算空）判斷是否為空，空就設 `RELAY_ENV_EMPTY=1`。**不用 `${CMD##*"$V="}`**：它也得到最後一處，但拿不到前一個字元；用 `%` 形式一次得到兩者。`##` 的實測成本供參考（Git Bash，1 MB／8000 處：0.147 秒；`%` 形式 0.008 秒），所以 `%` 形式更便宜。最後一處的前一個字元是壞的 → 這條路徑不判斷空值（不輸出說明）。這是顯示用的，寧可少說也不誤說。
8. **離場行為不變且不更弱**：不新增 `allow` 路徑、不新增 `exit 0`；警告出現與否只有一處改變——`MY_NF_RELAY_EXTRA_DOMAINS=` 這類「名字只是尾巴相同」的指令不再多印一段警告。**詢問不受影響**：`ask` 無條件呼叫（`hooks/confirm_launch.sh:467`），整條指令仍印在 `permissionDecisionReason`（同處）。其餘每一種「現在警告」的指令，新版仍警告（第 2 點的誤差方向、第 3 點的「用完上限就走不列原文路徑」都保證這點）。
9. **成本**：沒帶該變數的指令仍在 `:311` 一次子字串比對就離開；帶了的，每個視窗多一次 `${y//pat/}`；列出階段只在 ≤64 KB、最多各 20 圈。既有 `TC-048…051` 計時（`tests/confirm_launch_test.sh:968-974`）限制不放寬。

## 失敗先行測試
全放 `tests/confirm_launch_test.sh`，沿用現有輔助函式：`envw <label> <var> <has|lacks> <指令> [檢查字串…]`（`:861`；以 `!` 開頭的檢查字串＝不得出現）、`idg`（`:621`）、`envbig`（`:946`）、`envq_txt`（`:811`）。新增區塊緊接 `:974` 之後，標籤前綴 `POL-`。`X120` 同 `:908`（120 個 `x`）。`P`＝`NF_RELAY_PEER_PREFIXES`，`E`＝`NF_RELAY_EXTRA_DOMAINS`；`S`＝empty sentence＝`An empty value is ignored by the relay, which then uses the deployment's relay_peer_prefixes setting.`

**每個變數各跑一次（`for V in E P`，共 5 項 ×2 ＝ 10 條）：**
- **POL-1 截斷標 `…`（發現 1）**：`$V=${X120}yy bash scripts/egress_ctl.sh start` → has，含 `${X120}…]`、不含 `${X120}y`。
- **POL-2 N=5 說第 4 處沒列（發現 2）**：`$V=m1x $V=m2x $V=m3x $V=m4x $V=m5x bash scripts/egress_ctl.sh start` → has，含 `(mention 4 is not listed; read the whole command shown below)`。
- **POL-3 雙引號整個顯示（發現 3）**：`$V="qq1 rr2" bash scripts/egress_ctl.sh start` → has，含 `["qq1 rr2"]`、不含 `…`（用 `!…` 檢查：`!"qq1 rr2"…`）。
- **POL-4 超過 64 KB 說明（發現 4）**：`envbig … $V spread70 1500 "The values are not listed because the command is over 64 KB; read the whole command shown below." "sc7"`（沿用 `:971` 的 spread70）。
- **POL-5 左邊字界（發現 6）**：`MY_$V=zzval bash scripts/egress_ctl.sh start` → lacks。

**只用 PEER（行為由共用函式決定，不必兩個變數各一份）共 14 條：**
- **POL-6 引號沒關就在分隔符切（發現 1）**：`P=a"b c d bash scripts/egress_ctl.sh start` → has，含 `[a"b…]`。
- **POL-7 N=6**：6 處 → 含 `(mentions 4 to 5 are not listed; read the whole command shown below)`。
- **POL-8 N=4 不加那行**：4 處 → 不含 `are not listed`、不含 `is not listed`。
- **POL-9 單引號整個顯示（發現 3）**：`P='qq1 rr2' bash …` → 含 `['qq1 rr2']`。
- **POL-10 引號內的值很長（發現 3＋1）**：`P="` + 200 個 `x` + `" bash …` → 含 `"` + 119 個 `x` + `…]`（120 字元＝引號加 119 個 x）。
- **POL-11 引號沒關、且後面還有字**：`P="a b; c bash scripts/egress_ctl.sh start` → 含 `["a…]`。
- **POL-12 收尾引號後面緊接字（發現 3）**：`P="a b"c bash …` → 含 `["a b"…]`。
- **POL-13 左邊字界：`(` 之後算**：`(P=a bash scripts/egress_ctl.sh start)` → has。
- **POL-14 左邊字界：引號之後算**：`echo "P=a"; bash scripts/egress_ctl.sh start` → has。
- **POL-15 好壞混合**：`MY_P=bad P=good bash scripts/egress_ctl.sh start` → has，含 `[good]`、`1 mention in total`、不含 `bad`。
- **POL-16 空值只看最後一處（發現 5）**：`P=a P= bash …` → 含 `S`；`P= P=a bash …` → 不含 `S`（兩條）。
- **POL-17 空的引號也算空**：`P="" bash …` → 含 `S`。
- **POL-18 仍然詢問**：`MY_P=x bash scripts/egress_ctl.sh start` → `idg … ask`（證明沒有警告的指令，閘門仍在）。

**64 KB 以上與計時（PEER 3 條，EXTRA 1 條）：**
- **POL-19 超過 64 KB、最後一處是空的 → 有 `S`**：新 `envbig` kind `empty70`：`"echo " + (P+"=sc7 "+"y"*112+" ")*500 + "; " + P + "= bash scripts/egress_ctl.sh start"`，限時 1500 ms，必含 `S`。
- **POL-20 超過 64 KB、最後一處不空 → 沒有 `S`**：同上但最後是 `P=real1`，必不含 `S`（`envbig` 第 6 參數）。
- **POL-21 EXTRA 的同形指令沒有 `S`（發現 5「EXTRA 不得算」）**：`E` 版 `empty70`，必不含 `S`。
- **POL-22 一堆「名字只是尾巴相同」的 1 MB 指令**：新 kind `lookalike1m`：`"echo " + ("MY_"+P+"=sc7 "+"y"*90+" ")*8000 + "; " + P + "=tail1 bash scripts/egress_ctl.sh start"`，限時 1000 ms，必含 `1 mention in total`、`The values are not listed because the command is over 64 KB`。（證明 O(n)，且壞提到不被算進次數。）
- **POL-23 用完步數上限 → 不列原文**：新 kind `lookalike25`：`"echo " + ("MY_"+P+"=x ")*25 + "; " + P + "=real1 bash scripts/egress_ctl.sh start"`（≈1 KB 即可，不必是大指令），限時 500 ms，必含 `1 mention in total`、`too many names that only end in NF_RELAY_PEER_PREFIXES`，且不含 `real1`。

合計 10 ＋ 14 ＋ 5 ＝ **29 條**（≤30）。tab、換行、`;`、`&`、`|` 這幾個字界字元沒有各自的測試：它們和 `(`、引號在同一個字元集合變數裡，verifier 看 diff 確認集合內容即可。

**既有斷言被改的清單（共 3 條，executor 在 ledger 貼改前／改後；除這兩條與新增外，既有每一條原樣）：**
1. `:894` `TC-010 $S double-quoted value kept as written`：現在檢查 `'"qq1'` 且 `!qq1 rr2`；改成檢查 `'"qq1 rr2"'`（整個值現在顯示到收尾引號）。
2. `:895` `TC-010 $S single-quoted value kept as written`：同理改成 `"'qq1 rr2'"`。
3. （附帶）`:910` `TC-020 $S MY_ prefix still warns`：期望從 `has` 改 `lacks`，標籤改成 `MY_ prefix is not a mention`（發現 6 的反面）。


## 完成標準（done when）
- 上面 29 條新測試綠；`bash tests/confirm_launch_test.sh` 全綠；全套綠（WSL 內 `bash tests/run_all.sh`，見 repo CLAUDE.md「For the executor and verifier」）。
- **「閱卷看 diff」的手動案例依 `memory/dev-plans/README.md`「通例：閱卷看 diff」處理**：不寫進 docs/TESTING.md；executor 把證據貼進 `specs/relay-warning-polish/ledger.md`，verifier 依 ledger 並自己重跑核對，不以「TESTING.md 沒有步驟」退回。證據包含：
  - `git diff --name-only origin/v3...HEAD` 只有「範圍」列的三個檔；`git diff` 對 `scripts/`、`platform/`、`docs/`、`skills/` 為空。
  - **兩個分支各跑一遍**：在 `origin/v3` 與本分支各跑 `bash tests/confirm_launch_test.sh`，輸出存檔逐行比對；差異只允許是上述 3 條改字／改期望與 29 條新增，其餘每行 ok／FAIL 狀態一致。
  - **「不更弱」比對**：舊 hook（`origin/v3`）與新 hook 各餵同一批指令（上面全部測試指令、`tests/confirm_launch_test.sh` 裡既有的 EXTRA／PEER 指令、`bash scripts/egress_ctl.sh start|stop|restart|status`、`bash scripts/agent_ctl.sh start`、一條 `ls`），比對 `permissionDecision`：兩邊完全一致（這件事不改任何 ask／allow）；另比對「是否印出 `THIS COMMAND ALSO MENTIONS <VAR>=`」：新版是舊版的子集，且差集只有名字帶左邊壞字元的那幾條（`MY_…`）。
  - **成本**：`TC-048…051` 與 `POL-22` 的毫秒數貼出新舊對照；一條 100 KB、不含兩個變數的指令，各跑新舊 hook，新版不得比舊版慢（容許量測誤差）。
  - `relay_env_warn` 函式本體（`sed -n` 取出）內：沒有命令替換 `$(`、沒有 `grep`／`jq`／`python`；`empty` 判斷只出現在 `[ "$3" = empty ]` 的保護內（貼 `sed -n` 結果，證明 EXTRA 不算空值）。
- `git diff hooks/confirm_launch.sh` 中，除 `relay_env_warn` 本體與其上方註解、PEER 那次呼叫多一個參數外，沒有其他既有行被改。
- developer-agent 在 PR 上跑過 `/code-review`，無未處理的 high 項。

## 環境事實
（行號為 `origin/v3`，先 `git -C <repo> fetch -q origin`，用 `git show` 讀，不要改主 repo；repo 在 `C:\Users\marvi\Desktop\agentic-bioflow\agentic-bioflow_v2`。）
- `hooks/confirm_launch.sh`：`ask()` `:289`；說明註解 `:294-307`；`relay_env_warn` `:308-348`（早退 `:311`、計次視窗 `:321-325`、標頭 `:328`、>64 KB 分支 `:329-330`、前 3 處 `:333-338`、最後 1 處 `:339-343`、輸出行 `:344`）；`RELAY_START_RE` `:432`；EXTRA 呼叫 `:452`；PEER 呼叫 `:458`、空值說明 `:461-464`；`ask` 呼叫 `:467`。
- `tests/confirm_launch_test.sh`：`id_env.yaml` `:619`；`idg` `:621`；`envp` `:790`；`envq`／`envq_txt`／`envq_order` `:803-824`；`PW_SETS` `:826`；`envw` `:861`；通用 `for V` 迴圈 `:880-927`（TC-010 `:894-896`、TC-017/018 `:906-907`、TC-019 `:909`、TC-020 `:910`）；`TC-035` 空值斷言 `:942-943`；`envbig` `:946-967`；`TC-048…051` `:968-974`。
- 語言事實：這台 Git Bash 實測，1 MB、8000 處時 `${CMD##*"$V="}` 0.147 秒、`${CMD%"$V="*}` 0.008 秒（`${x//p/}` 整段做是平方時間，所以才有 8 KB 視窗，見 `:312-318` 的註解）。`hooks/hooks.json:11` 的逾時是 30 秒（hook 逾時＝放行）。
- repo 教訓：改閘門曾放行三種本該擋的形狀（repo CLAUDE.md 校正失敗 #1）→ 必須兩分支各跑一遍。repo CLAUDE.md「For the executor and verifier」：規則文件 `.specify/memory/constitution.md`；單檔測試 `bash tests/<name>.sh`；全套 `tests/run_all.sh` 須在 WSL／Linux；**不得**改 `spec.md`、`test-case*.md`、憲法、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`；**不得**連站台或 HPC。

## 不做
- 不新增任何 shell 斷詞器、引號平衡器或「哪個值會生效」的判斷（前三輪審查已證明那條路一直有新洞；見 `memory/dev-plans/relay-warning-hardening.md` 裁決五）。
- 不去跳脫、不展開 `$VAR`／`$(…)`、不處理 `\"`。
- 不改 `ask()`、`RELAY_START_RE`、EXTRA／PEER 的結尾句文字、`hooks/hooks.json`；不改 `scripts/`。
- 不為反引號、`{` 等字加進左邊字界集合（見裁決 3）。

## 裁決（2026-10-24，developer-agent 起草；與上文衝突時以本段為準）
1. **用同一個視窗迴圈多做一次 `${y//[!$nb]"$V="/}` 數壞提到，不寫逐字元迴圈。** 理由：硬規則是不新增解析器且要 O(n)；這個做法的成本是現有的兩倍常數，且壞數少算的方向是多警告。**另一選項**：不計次、只在列出時過濾（次數會把 `MY_` 也算進去，不符發現 6）。**預設：多一次視窗移除。**
2. **步數用完就不列原文（走「不列值」輸出），不繼續掃。** 理由：列出階段只在 ≤64 KB 才跑，但一個 64 KB 的指令裡可能有近三千個壞提到，逐圈複製剩餘字串會變平方；寧可不列也不超時（超時＝放行）。**另一選項**：往前掃不設上限（簡單，但最壞情況數百毫秒到秒級，無證據可保證）。**預設：各 20 圈。**
3. **字界集合照任務指示：開頭、空白、tab、換行、`;&|(`、兩種引號；不含反引號與 `{`。** 理由：反引號內的 `` `P=x bash …egress_ctl.sh start` `` 這型前一個字元是反引號，會被歸為壞提到而不警告——這是**變弱**的唯一已知形狀，所以**這一條需要維護者點頭**（見開放問題 1）；在他回答前，預設照任務指示不含反引號，並在 ledger 記一句。**另一選項**：把反引號與 `{` 也放進集合（更安全，多兩個字元，不影響成本）。
4. **N=5 寫單數 `(mention 4 is not listed; …)`，N≥6 寫 `(mentions 4 to N-1 are not listed; …)`。** 理由：避免「4 to 4」。
5. **>64 KB 路徑的最後一處用 `%` 形式取，不用 `##`。** 理由：要同時知道前一個字元以套用字界；實測更快（0.008 秒對 0.147 秒）。
6. **`""`／`''` 緊鄰的兩個引號算空值。** 理由：shell 把它們當成空字串，中繼也只看到空字串；hook 只做字面比對。
7. **引號沒關或 120 字元內找不到收尾引號時，退回舊取法並加 `…`。** 理由：不猜引號到哪裡結束（那是解析器）；加 `…` 提醒使用者此處有被截。

## 裁決二（2026-10-24 21:30 developer-agent；以本段為準）
1. **字界改成反過來定義**：只有前一個字元是 `[A-Za-z0-9_]`（變數名的一部分，例如 `MY_`）才算「不是提到」；其他任何字元（含反引號、`{`、`$`、`=`、tab、換行、引號、`;&|(`）或字串開頭都算提到。這樣唯一變少的警告就是名字尾巴相同的別的變數，不會有「反引號型變弱」。實作照計畫的視窗計數法，把集合換成 `[A-Za-z0-9_]`。
2. 最後一處用 `${CMD%"$V="*}` 接受（實測較快）。
3. N=5 用單數句、N≥6 用 `4 to N-1`，接受。
4. 64 KB 以上、最後一處前一字元是變數名字元時不輸出空值說明，接受。
5. tab、換行、`;&|` 等由 verifier 看 diff，接受（集合已改成反向，只剩 `[A-Za-z0-9_]` 要測）。

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
