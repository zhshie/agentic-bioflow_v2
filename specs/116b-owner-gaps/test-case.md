# 測試案例：116b 補上 #116 的擁有者綁定漏洞（參數裡的路徑、重複的 run 名稱、捷徑、指定舊 run 的擁有者）

**規格**：`specs/116b-owner-gaps/plan.md`（本功能沒有獨立的 spec.md，計畫即唯一來源；維護者的話是計畫開頭「給維護者」三句，沒有另外的逐字例句）　**總覽**：`test-case-overview.md`

名詞先講白：
- **A、B**＝平台上兩個不同的使用者（Alice、Bob）。**上傳資料夾**＝每人在平台上自己的檔案區 `<uploads_root>/<名字>`。**HTTP**＝透過網路登入的使用者（一定有「呼叫者」）；**終端機／stdio**＝在平台那台機器上直接打指令，或本機程式接 MCP（沒有呼叫者，行為照舊）。
- **參數（`params`）**＝送出分析時附帶的設定值，有些值是檔案路徑。**樣本表（samplesheet）**＝列出要分析哪些檔案的表。
- **捷徑／連結**＝符號連結（symlink），一個檔名其實指向別的地方。**真實路徑（real path）**＝把所有捷徑與 `..` 都解開之後，檔案真正在的位置。
- **代理（agent）**＝站台上替平台做事的程式；**工作（job）**＝平台交給代理做的一件事；工作被代理「拒絕」＝代理沒有執行它並給出理由。
- **擁有者**＝一筆送出紀錄（`launches.user_id`）屬於誰；**沒有擁有者（NULL）**＝舊資料。
- **「通用拒絕句」**＝計畫規定的那句 `this run name is taken; choose another`，不含任何 Slurm 編號、狀態或別人的名字。
- 下列「被拒絕」都包含：沒有留下待確認請求、沒有排進佇列的工作、沒有新的送出紀錄，除非該列另有說明。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## User Story 1 — 送出參數裡的檔案路徑也只能指自己的資料夾（優先度 P1）

維護者的話（給維護者 1）：「補 #116 的三個洞：送出參數裡的檔案路徑也只能指自己的資料夾；run 名稱重複時不再洩漏別人的 run；用捷徑（符號連結）繞過資料夾檢查的路全部堵上。」
計畫「檢查」第一條：「Bob's `params` pointing at Alice's file」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 給維護者 1；變更 1；檢查「Bob's params pointing at Alice's file」 | 例外 | Alice 的上傳資料夾裡有檔案 `<uploads_root>/alice/a.fq`；Bob 是已登入的 HTTP 使用者，自己的樣本表正常 | Bob 透過 HTTP 送出 launch，`params` 裡有一個值是 `<uploads_root>/alice/a.fq` | 被拒絕，沒有跳出確認問題 | 自動 |
| TC-002 | 變更 1 | 功能 | Bob 的上傳資料夾裡有 `<uploads_root>/bob/ref.txt` | Bob 透過 HTTP 送出 launch，`params` 裡有一個值是 `<uploads_root>/bob/ref.txt` | 不被這條規則拒絕，正常走到確認摘要（待確認請求建立） | 自動 |
| TC-003 | 變更 1（與樣本表欄位同一個 `caller_area()` 真實路徑規則） | 例外 | 同 TC-001 | Bob 的 `params` 值是 `<uploads_root>/bob/../alice/a.fq` | 被拒絕（`..` 解開後落在 Alice 的資料夾） | 自動 |
| TC-004 | 變更 1；變更 3 | 例外 | Bob 的資料夾裡有捷徑 `<uploads_root>/bob/lnk`，指向 `<uploads_root>/alice/a.fq` | Bob 的 `params` 值是 `<uploads_root>/bob/lnk` | 被拒絕（以真實路徑判斷，不看名字在不在自己的資料夾下） | 自動 |
| TC-005 | 變更 1（「以 `~` 開頭」算路徑） | 例外 | 測試環境的可讀根目錄（readRoots）不含執行者的家目錄 | Bob 的 `params` 值是 `~/secret.txt` | 被當成路徑檢查，並被拒絕；不會被當成普通文字放行 | 自動 |
| TC-006 | 變更 1；計畫「Pipeline reference files outside uploads_root … still pass」 | 功能 | 環境的可讀根目錄之下有共用基因組檔 `<readRoot>/genomes/g.fa`（在 uploads_root 之外） | Bob 的 `params` 值是 `<readRoot>/genomes/g.fa` | 不被拒絕，正常走到確認摘要 | 自動 |
| TC-007 | 變更 1（「Values that point elsewhere follow the environment's readRoots rule」） | 例外 | 一個不在 uploads_root、也不在環境可讀根目錄之下的路徑 `/elsewhere/x.fa` | Bob 的 `params` 值是 `/elsewhere/x.fa` | 被拒絕，說明在允許的可讀範圍之外 | 自動 |
| TC-008 | 變更 1（「Looks like a path」的定義：含 `/`、以 `~` 開頭、或是可讀根目錄下已存在的檔案；其餘不算） | 功能 | 無 | Bob 的 `params` 值是 `GRCh38`、`true`、整數 `4`、`skip_qc`（沒有 `/`、不以 `~` 開頭、不是既有檔案名） | 不被當成路徑，送出照常走到確認摘要，值原樣保留在內容裡 | 自動 |
| TC-009 | 變更 1；#116 慣例「拒絕句只講呼叫者自己的資料夾」 | 例外 | 同 TC-001 | 讀 Bob 在 TC-001 得到的拒絕句 | 句子點出 Bob 自己的上傳資料夾；不含 `alice`、不含 `a.fq`、不含任何別人資料夾的內容 | 自動 |
| TC-010 | 變更 1（「The terminal and stdio are unchanged」） | 不在範圍 | 沒有呼叫者（終端機與 stdio） | 終端機與 stdio 送出 launch，`params` 的值指向 `<uploads_root>/alice/a.fq`、`/elsewhere/x.fa` | 結果與改動前相同：新規則沒有套用在沒有呼叫者的入口 | 自動 |
| TC-011 | 變更 1 | 例外 | 同 TC-001 | Bob 的 TC-001 被拒絕之後，檢查平台資料 | 沒有待確認請求、沒有確認紀錄、沒有佇列工作、沒有新的 `launches` 紀錄 | 自動 |

## User Story 2 — run 名稱重複時不再洩漏別人的 run（優先度 P1）

計畫「檢查」第二條：「Bob reusing Alice's run name」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 給維護者 1；變更 2；檢查「Bob reusing Alice's run name」 | 例外 | Alice 送出過 run `r1`，已有 Slurm 工作編號 4242（送出者是 Alice）；Bob 的資料夾與 Alice 的不同 | Bob 透過 HTTP 送出 launch，run 名稱也是 `r1` | 被拒絕，字句就是通用拒絕句 `this run name is taken; choose another`；句子裡沒有 `4242`、沒有「已送出／等待／結果不明」這類狀態、沒有 `alice` | 自動 |
| TC-013 | 變更 2（「or to nobody」） | 例外 | 舊 run `r0` 的最新送出紀錄沒有擁有者（NULL），且有 Slurm 工作編號 777 | Bob 透過 HTTP 送出 launch，run 名稱是 `r0` | 被拒絕，字句與 TC-012 完全相同；沒有 `777`、沒有狀態字 | 自動 |
| TC-014 | 變更 2（「one generic refusal」） | 例外 | 同 TC-012、TC-013 的資料都在 | 比較 Bob 撞上 Alice 的名稱、與撞上沒有擁有者的名稱，兩次得到的拒絕句 | 兩句逐字相同，Bob 看不出對方是別人的還是沒人的 | 自動 |
| TC-015 | 變更 2 | 例外 | 同 TC-012 | 檢查 Bob 被拒絕之後的平台資料 | 沒有待確認請求、沒有佇列工作、`r1` 沒有出現新的 `launches` 紀錄 | 自動 |
| TC-016 | 變更 2（「The caller's own launch keeps today's detailed words」） | 功能 | Alice 自己送出過 `r1`，Slurm 工作編號 4242 | Alice 透過 HTTP 再用名稱 `r1` 送出 launch | 被拒絕，字句與改動前相同：「run 名稱已用過」並含 Slurm 工作編號 4242 | 自動 |
| TC-017 | 變更 2（同上，「還在等代理」那一種） | 功能 | Alice 自己送出過 `r2`，還沒有 Slurm 編號，代理工作仍在等待 | Alice 透過 HTTP 再用 `r2` 送出 | 被拒絕，字句與改動前相同（上一次送出還在等代理處理） | 自動 |
| TC-018 | 變更 2（同上，「結果不明」那一種） | 功能 | Alice 自己送出過 `r3`，沒有 Slurm 編號，結果不明 | Alice 透過 HTTP 再用 `r3` 送出 | 被拒絕，字句與改動前相同（結果不明，請先查站台） | 自動 |
| TC-019 | 變更 2（只改措辭，不改哪些名稱算被占用）；計畫「不放寬任何現有的拒絕」 | 功能 | Alice 用過名稱 `r4`，但她那一筆被代理拒絕、沒有 Slurm 編號（名稱仍可用） | Bob 透過 HTTP 用 `r4` 送出 | 與改動前一樣：名稱沒有被占用，不被名稱規則拒絕 | 自動 |
| TC-020 | 變更 2（檢查「owner-aware」套用在名稱檢查的每個地方） | 例外 | Bob 先為名稱 `r5` 建立了待確認請求；之後 Alice 的 `r5` 被送出並取得 Slurm 編號 | Bob 按「送出」（網頁確認）或讓這個請求進佇列 | 被拒絕，字句為通用拒絕句，沒有 Slurm 編號與狀態；沒有佇列工作 | 自動 |
| TC-021 | 變更 2（只對 HTTP 呼叫者） | 不在範圍 | 同 TC-012 | 終端機（沒有呼叫者）用 `r1` 送出 launch | 與改動前相同：仍被拒絕，詳細字句不變（含 Slurm 編號）；通用拒絕句只用在 HTTP | 自動 |

## User Story 3 — 用捷徑繞過資料夾檢查的路全部堵上（優先度 P1）

計畫「檢查」第三、四條：「a link in Alice's folder to Bob's folder; a swap between approval and job time」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 變更 3(a)；檢查「a link in Alice's folder to Bob's folder」 | 例外 | Alice 的資料夾裡有捷徑 `<uploads_root>/alice/to_bob`，指向 `<uploads_root>/bob` | Alice 透過 HTTP 列出站台檔案，路徑 `<uploads_root>/alice/to_bob` | 被拒絕（先解開捷徑再判斷：真實路徑在 Bob 的資料夾），句子是「只能列你自己的上傳資料夾」；沒有列檔工作排進佇列 | 自動 |
| TC-023 | 變更 3(a)（`realpath` 在上傳資料夾檢查之前） | 例外 | 在 uploads_root 之外、環境可讀範圍內有捷徑 `<readRoot>/lnk`，指向 `<uploads_root>/bob` | Alice 透過 HTTP 列出 `<readRoot>/lnk` | 被拒絕；沒有列檔工作 | 自動 |
| TC-024 | 變更 3(a)（不過度拒絕） | 功能 | Alice 的資料夾裡有捷徑 `<uploads_root>/alice/mine`，指向她自己的 `<uploads_root>/alice/real` | Alice 透過 HTTP 列出 `<uploads_root>/alice/mine` 與 `<uploads_root>/alice` | 兩個都成功排進佇列並取得結果 | 自動 |
| TC-025 | 變更 3(a)；計畫「Rewritten pins」 | 功能 | Bob 的資料夾沒有任何捷徑 | Bob 透過 HTTP 列出 `<uploads_root>/bob` | 與改動前相同，成功列出 | 自動 |
| TC-026 | 變更 3(a)（「the agent's listing does not follow links out of the requested folder」） | 例外 | Alice 的資料夾裡有捷徑指向 Bob 的資料夾，Bob 的資料夾裡有 `secret.fq` | 代理（站台端）處理對 `<uploads_root>/alice` 的列檔工作 | 結果裡看不到 Bob 資料夾裡的任何檔名、大小或內容（`secret.fq` 不出現），代理沒有走進捷徑指向的資料夾 | 自動 |
| TC-027 | 變更 3(b)（樣本表欄位） | 功能 | Alice 的資料夾裡 `lnk` 指向 `real/x.fq`（都在她的資料夾內）；樣本表一格寫 `<uploads_root>/alice/lnk` | Alice 透過 HTTP 送出 launch | 內容包（bundle）為該格記下請求當下解開的真實路徑（`<uploads_root>/alice/real/x.fq`） | 自動 |
| TC-028 | 變更 3(b)（路徑型 `params`） | 功能 | 同 TC-027；`params` 的一個值是 `<uploads_root>/alice/lnk` | Alice 透過 HTTP 送出 launch | 內容包為該參數值也記下請求當下的真實路徑 | 自動 |
| TC-029 | 變更 3(b)（「The approved hash covers those real paths」） | 例外 | Alice 對 `lnk` 指向 `real/x.fq` 的內容包已獲確認；之後把 `lnk` 改指向 `real/y.fq`，再送出同樣的請求 | 比較兩份內容包的雜湊值，並拿第一次的確認去批准第二份 | 雜湊值不同；第一次的確認不能用在第二份（沒有找到已核可的確認，要重新確認） | 自動 |
| TC-030 | 變更 3(c) | 功能 | Alice 的請求已獲確認，從核可到工作執行之間，沒有任何檔案或捷徑被改 | 代理執行 launch 工作 | 照常通過新的檢查，工作被送到排程器（與改動前相同） | 自動 |
| TC-031 | 變更 3(c)；檢查「a swap between approval and job time」 | 例外 | Alice 核可了一份樣本表格子指向 `lnk` 的 launch；核可之後、工作執行之前，`lnk` 被改成指向 `<uploads_root>/bob/secret.fq` | 代理執行這個工作 | 代理拒絕這個工作並給出白話理由（說這個路徑自核可後變了／不在擁有者的資料夾）；沒有任何東西被送到排程器 | 自動 |
| TC-032 | 變更 3(c)（「differs from the recorded one」，即使仍在自己的資料夾內） | 例外 | 同 TC-031，但 `lnk` 被改成指向 Alice 自己資料夾裡的另一個檔 `real/y.fq` | 代理執行這個工作 | 代理拒絕（解開的真實路徑與記錄的不同），給白話理由；沒有送到排程器 | 自動 |
| TC-033 | 變更 3(c)（「lies outside the recorded owner's folder」） | 例外 | 一份內容包（雜湊值與確認相符）記下的真實路徑落在擁有者資料夾之外 | 代理執行這個工作 | 代理拒絕，給白話理由；沒有送到排程器 | 自動 |
| TC-034 | 變更 3(c)（「refuses the job, with a plain reason」） | 例外 | 同 TC-031 | 在使用者查看工作狀態的地方查看 | 工作的狀態是「被代理拒絕」，並帶著白話理由；不是失敗不明，也不含 Bob 檔案的內容 | 自動 |
| TC-035 | 變更 3(c)（「The agent check is a refusal only. It never widens what the agent may read」） | 例外 | 一份內容包，記下的路徑與解開的路徑一致，但該路徑在代理自己的允許讀取範圍之外 | 代理執行這個工作 | 仍被代理原有的規則拒絕；新的檢查沒有讓它變成可以讀 | 自動 |
| TC-036 | 變更 3(c)（路徑型 `params` 也要被檢查） | 例外 | 同 TC-031，但被換掉的捷徑是 `params` 裡某個值指向的那個 | 代理執行這個工作 | 代理拒絕，給白話理由；沒有送到排程器 | 自動 |
| TC-037 | 變更 3(c)；計畫「Tier A (tightening only)」 | 功能 | 終端機送出的 launch（沒有上傳資料夾的路徑） | 代理執行這個工作 | 不被新的檢查拒絕，與改動前相同地被送到排程器 | 自動 |

## User Story 4 — 把沒有擁有者的舊 run 指定給某人（優先度 P2）

維護者的話（給維護者 2）：「多一個指令，可以把沒有擁有者的舊 run 指定給某人。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-038 | 給維護者 2；變更 4 | 功能 | 平台有使用者 alice、bob；run `r-old` 的最新送出紀錄沒有擁有者（NULL） | 在終端機執行 `abf-platform runs assign r-old --user alice` | 指令成功並印出已指定的訊息；該筆紀錄的 `user_id` 是 alice | 自動 |
| TC-039 | 給維護者 2；變更 4（接上 #116 的「只看得到自己的 run」） | 功能 | TC-038 完成之後 | Alice 與 Bob 各自透過 HTTP 列出／查詢 `r-old` | Alice 看得到；Bob 得到「找不到」 | 自動 |
| TC-040 | 變更 4（「the newest launch row of that run」） | 功能 | run `r-x` 有兩筆送出紀錄，兩筆擁有者都是 NULL | 指令把 `r-x` 指定給 alice | 只有最新的一筆改成 alice；較舊的一筆仍是 NULL | 自動 |
| TC-041 | 變更 4（只改擁有者） | 功能 | 同 TC-038，並有另一個 run `r-other` | 指令把 `r-old` 指定給 alice | 該筆紀錄的其他欄位（run 資料夾、環境、代理、Slurm 編號、確認時間、工作編號）與 `r-other` 的所有紀錄都沒變 | 自動 |
| TC-042 | 變更 4（「A row that already has an owner needs `--force`」） | 例外 | `r-owned` 最新一筆的擁有者是 bob | 執行 `abf-platform runs assign r-owned --user alice`（不帶 `--force`） | 被拒絕，說明這個 run 已有擁有者、要改需帶 `--force`；擁有者仍是 bob | 自動 |
| TC-043 | 變更 4（「`--force`, which prints the old and new owner」） | 功能 | 同 TC-042 | 執行同一指令但帶 `--force` | 擁有者改成 alice，輸出同時印出舊擁有者 bob 與新擁有者 alice | 自動 |
| TC-044 | 變更 4（「An unknown user … is refused」） | 例外 | `r-old` 沒有擁有者 | 執行 `abf-platform runs assign r-old --user nobody-here` | 被拒絕，說明沒有這個使用者；`r-old` 的擁有者仍是 NULL | 自動 |
| TC-045 | 變更 4（「An unknown … run is refused」） | 例外 | 沒有叫 `no-such-run` 的送出紀錄 | 執行 `abf-platform runs assign no-such-run --user alice` | 被拒絕，說明沒有這個 run；沒有新增任何紀錄 | 自動 |
| TC-046 | 變更 4（語法 `--user USER`） | 例外 | 同 TC-038 | 執行 `abf-platform runs assign r-old`（沒有 `--user`） | 指令失敗並說明需要 `--user`；擁有者沒變 | 自動 |
| TC-047 | 變更 4（「terminal only」） | 不在範圍 | 平台的 MCP 伺服器與網頁已啟動 | 檢查 MCP 工具清單與網頁的路由；用 HTTP 使用者試著改一個 run 的擁有者 | 沒有任何 MCP 工具、網頁路由或 HTTP 端點可以指定／更改 run 的擁有者 | 自動 |
| TC-048 | 計畫「Not in this PR：Roles and sharing (010)」 | 不在範圍 | 同 TC-038 | 對 `runs assign` 加上角色、實驗室、共享一類的選項（例如 `--role`、`--lab`、`--share`） | 指令不認得這些選項而失敗；一筆紀錄仍然只有一位擁有者，沒有共享機制 | 自動 |
| TC-049 | 計畫「Not in this PR：Roles and sharing (010)」 | 不在範圍 | Alice 與 Bob 屬於同一個實驗室（lab） | Bob 用 `params` 指向 Alice 的檔案、用 Alice 的 run 名稱送出 | 仍然都被拒絕（TC-001、TC-012 的結果），同實驗室不會讓他們共享 | 自動 |
| TC-050 | 計畫「Not in this PR：Per-user site folders for a remote station (009h)」 | 不在範圍 | 同 TC-027 的送出 | 比較內容包裡的 run 資料夾與站台上檔案的擺放位置，與改動前同樣輸入時的結果 | 沒有為使用者建立新的站台資料夾或改變站台上的資料夾結構（只多了記下的真實路徑，見 TC-027、TC-028） | 自動 |

## 憲法與安全網

這次改動碰到：原則 I.2（人的確認、只有一條送出路徑、不留第二份 run 狀態）、安全網的「launch 要完整顯示並等確認」、原則 II.3（路徑不寫死）。計畫要求「只讓規則變嚴，不放寬任何現有的拒絕」。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-051 | 原則 I.2；安全網「launch 要等明確確認」 | 例外 | 沒有人確認的 launch | 透過 MCP 工具與網頁路由各送一次 | 兩個入口都仍被拒絕、沒有排進佇列（既有的 `test_tch09_*` 與 `test_tch09_b_c_*` 不改動就通過） | 自動 |
| TC-052 | 原則 I.2（「no second copy of a run's state … at most one submission path」） | 功能 | 改動完成 | 執行 `tests/no_second_run_state_test.sh`；檢視 `runs assign` 與代理的新檢查 | 檢查通過；`runs assign` 只寫 `launches.user_id`；代理的新檢查沒有送出任何東西、沒有新增記錄 run 狀態的檔案或表 | 自動 |
| TC-053 | 安全網「不得放寬」；計畫「No existing refusal is loosened. Rewritten pins go in the ledger with old, new and reason」 | 功能 | 改動完成 | 驗收審查者拿本分支與 `main` 比對所有被修改的既有測試檔 | 每一個被改的斷言都列在 `specs/116b-owner-gaps/ledger.md`（舊、新、理由）；沒有被刪除、放寬或跳過的斷言；`docs/TESTING.md` 有這一步 | 手動：`docs/TESTING.md`（實作時補上這一步） |
| TC-054 | 原則 II.3（路徑不寫死） | 功能 | 改動完成 | 執行 `tests/no_hardcoded_paths.sh` | 通過；新程式的位置全部來自設定，不含個人或叢集路徑 | 自動 |
| TC-055 | 計畫「`bash tests/run_all.sh` is green」 | 功能 | 改動完成 | 在 WSL 或 Linux 執行 `bash tests/run_all.sh` | 全綠 | 自動 |
