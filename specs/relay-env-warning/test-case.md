# 測試案例：直接用環境變數放寬轉送對端時，送出前檢查要警告（relay-env-warning）

<!--
Written by the verifier (CONTRACT mode) from specs/relay-env-warning/plan.md (含裁決與裁決三), before any code.
這個任務沒有 spec.md；依據是 plan.md（A 級、backend），維護者原話與範例都引自計畫「維護者原話」與「失敗先行測試」。
-->

**規格**：`specs/relay-env-warning/plan.md`（本任務沒有 spec.md）　**總覽**：`test-case-overview.md`

白話說明：中繼（relay）是登入節點上替運算節點轉送對外連線的常駐程式。有人在啟動它的同一行指令前面帶上 `NF_RELAY_PEER_PREFIXES=…`（決定「哪些主機名開頭的機器可以連進中繼」），閘門（`hooks/confirm_launch.sh`）詢問使用者「要不要允許」時，必須明講這條指令自己帶了一份清單，做法跟已有的 `NF_RELAY_EXTRA_DOMAINS=` 警告一樣。「ask」＝閘門停下來問使用者；「警告」＝問話文字裡多的那一段。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：邊角情況或不該被放行的情況，系統怎麼反應（照樣詢問、不誤報）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

測試輔助函式約定（來自計畫）：`envq` 是複製 `envp` 的新函式，比對字串為 `THIS COMMAND ALSO SETS NF_RELAY_PEER_PREFIXES`；`has`＝詢問文字含該字串，`lacks`＝不含。`idg` 是既有函式，期望 `ask` 或 `allow`。以下「警告句」指 `THIS COMMAND ALSO SETS NF_RELAY_PEER_PREFIXES=${值}, which changes which hosts may connect to the relay…`。

## User Story 1 — 直接帶 NF_RELAY_PEER_PREFIXES= 啟動中繼時，詢問裡點名（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；PEER-1 | 功能 | 閘門已安裝；部署設定檔照 `id_env.yaml` | 對閘門送出 Bash 指令 `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh start` | 詢問文字含警告句，且值顯示為 `25a-cpn`（即含 `THIS COMMAND ALSO SETS NF_RELAY_PEER_PREFIXES=25a-cpn, which changes which hosts may connect to the relay`） | 自動：`tests/confirm_launch_test.sh`（`envq` has） |
| TC-002 | 作法 1；PEER-2 | 功能 | 同上 | 送出 `env NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh restart` | 詢問文字含 PEER 警告句（`restart` 也算啟動） | 自動：`tests/confirm_launch_test.sh`（`envq` has） |
| TC-003 | 作法 1、2；PEER-3 | 功能 | 同上 | 送出 `export NF_RELAY_PEER_PREFIXES=25a-cpn; bash scripts/egress_ctl.sh start` | 詢問文字含 PEER 警告句，值只顯示到分號之前，即 `NF_RELAY_PEER_PREFIXES=25a-cpn, which changes`（不含 `;`） | 自動：`tests/confirm_launch_test.sh`（`envq` has，並比對值＝`25a-cpn`） |
| TC-004 | 作法 6；裁決 3；PEER-4 | 例外 | 同上 | 送出 `NF_RELAY_PEER_PREFIXES= bash scripts/egress_ctl.sh start`（值為空） | 詢問文字仍含 PEER 警告句，值顯示為空（`NF_RELAY_PEER_PREFIXES=, which changes`）；空值不開例外 | 自動：`tests/confirm_launch_test.sh`（`envq` has） |
| TC-005 | 作法 1；PEER-5 | 功能 | 同上 | 送出 `NF_RELAY_PEER_PREFIXES=zzz-aaa bash "${CLAUDE_PLUGIN_ROOT}/scripts/egress_ctl.sh" start`（腳本路徑帶引號） | 詢問文字含 PEER 警告句 | 自動：`tests/confirm_launch_test.sh`（`envq` has） |
| TC-006 | 作法 4；PEER-6 | 功能 | 同上 | 送出 `NF_RELAY_EXTRA_DOMAINS=evil.org NF_RELAY_PEER_PREFIXES=zzz-aaa bash scripts/egress_ctl.sh start` | 詢問文字含 PEER 警告句 | 自動：`tests/confirm_launch_test.sh`（`envq` has） |
| TC-007 | 作法 4；PEER-6 | 功能 | 同上 | 送出與 TC-006 相同的指令 | 詢問文字同時仍含 EXTRA 警告（既有字樣 `overrides this deployment's list`）：兩段警告都出現 | 自動：`tests/confirm_launch_test.sh`（既有 `envp` has） |
| TC-008 | 作法 4（順序固定） | 功能 | 同上 | 送出與 TC-006 相同的指令 | 詢問文字中 EXTRA 警告出現在 PEER 警告之前（先 EXTRA 後 PEER） | 自動：`tests/confirm_launch_test.sh` |
| TC-009 | 裁決三 4；PEER-7 | 功能 | 同上 | 送出 `NF_RELAY_PEER_PREFIXES=25a-cpn,25a-lgn bash scripts/egress_ctl.sh start` | **警告句裡**顯示完整的值：含 `THIS COMMAND ALSO SETS NF_RELAY_PEER_PREFIXES=25a-cpn,25a-lgn, which changes`（只比對警告句，不比對整條指令的回顯） | 自動：`tests/confirm_launch_test.sh` |
| TC-010 | 作法 3 | 功能 | 同上 | 送出 TC-001 的指令 | 警告句完整含：`which changes which hosts may connect to the relay`、`instead of the deployment's setting (default cpn,gpn,bgm,lgn,localhost)`、`Show the user the prefixes it names.` | 自動：`tests/confirm_launch_test.sh` |
| TC-011 | 作法 3；裁決 2 | 功能 | 同上 | 送出只帶 PEER 的 TC-001 指令 | 詢問文字**不含** `overrides this deployment's list`（那是 EXTRA 專用字樣，兩段各自可辨） | 自動：`tests/confirm_launch_test.sh`（既有 `envp` lacks 形式） |
| TC-012 | 作法 1；PEER-8 | 例外 | 同上 | 送出 `bash scripts/egress_ctl.sh start`（沒帶任何變數） | 詢問文字不含 PEER 警告句（不誤報） | 自動：`tests/confirm_launch_test.sh`（`envq` lacks） |
| TC-013 | PEER-10 | 例外 | 同上 | 送出 `NF_RELAY_EXTRA_DOMAINS=evil.org bash scripts/egress_ctl.sh start`（只帶 EXTRA） | 詢問文字不含 PEER 警告句（EXTRA 警告不會被當成 PEER 警告） | 自動：`tests/confirm_launch_test.sh`（`envq` lacks） |
| TC-014 | 作法 1；PEER-11 | 例外 | 同上 | 送出 `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh stop` | 詢問文字不含 PEER 警告句（只有 start／restart 才警告） | 自動：`tests/confirm_launch_test.sh`（`envq` lacks） |
| TC-015 | 作法 1；裁決 4；PEER-9；「不做」第 2 點 | 不在範圍 | 同上 | 送出 `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/on_site.sh egress_ctl.sh start`（經 `on_site.sh`） | 詢問文字不含 PEER 警告句（`on_site.sh` 會用設定檔的值取代，不對該路徑加警告，與 EXTRA 一致） | 自動：`tests/confirm_launch_test.sh`（`envq` lacks） |
| TC-016 | 「既有斷言會被改的清單：無」 | 功能 | 本分支的 `tests/confirm_launch_test.sh` | 執行該檔，看原有四條 `envp`（EXTRA 的 start、env restart、export、對照組）的結果 | 四條都是 ok；它們的斷言文字與期望值與基底分支逐字相同 | 自動：`tests/confirm_launch_test.sh` |

## User Story 2 — 閘門不放寬、不變弱，改動範圍只有計畫列的三個檔（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 作法 4；PEER-12 | 例外 | 同 US1 | 以 `idg` 送出 `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh start` | 結果是 `ask`（不是放行） | 自動：`tests/confirm_launch_test.sh`（`idg` ask） |
| TC-018 | 作法 4；PEER-12 | 例外 | 同 US1 | 以 `idg` 送出 `env NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh restart` | 結果是 `ask` | 自動：`tests/confirm_launch_test.sh`（`idg` ask） |
| TC-019 | 作法 4；PEER-12 | 例外 | 同 US1 | 以 `idg` 送出 `export NF_RELAY_PEER_PREFIXES=25a-cpn; bash scripts/egress_ctl.sh start` | 結果是 `ask` | 自動：`tests/confirm_launch_test.sh`（`idg` ask） |
| TC-020 | 計畫「手算對照」末句 | 例外 | 同 US1 | 以 `idg` 送出 `NF_RELAY_PEER_PREFIXES= bash scripts/egress_ctl.sh start`（空值） | 結果是 `ask`（空值沒有繞過閘門的縫） | 自動：`tests/confirm_launch_test.sh`（`idg` ask） |
| TC-021 | 計畫「手算對照」末句 | 例外 | 同 US1 | 以 `idg` 送出 `NF_RELAY_PEER_PREFIXES=zzz-aaa bash "${CLAUDE_PLUGIN_ROOT}/scripts/egress_ctl.sh" start`（帶引號路徑） | 結果是 `ask` | 自動：`tests/confirm_launch_test.sh`（`idg` ask） |
| TC-022 | 作法 4；計畫「手算對照」末句 | 例外 | 同 US1 | 以 `idg` 送出 `NF_RELAY_EXTRA_DOMAINS=evil.org NF_RELAY_PEER_PREFIXES=zzz-aaa bash scripts/egress_ctl.sh start`（兩變數並存） | 結果是 `ask` | 自動：`tests/confirm_launch_test.sh`（`idg` ask） |
| TC-023 | 計畫「手算對照」末句 | 例外 | 同 US1 | 以 `idg` 送出 `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/on_site.sh egress_ctl.sh start` | 結果是 `ask`（沒有警告，但閘門本身照舊） | 自動：`tests/confirm_launch_test.sh`（`idg` ask） |
| TC-024 | 計畫「手算對照」末句 | 例外 | 同 US1 | 以 `idg` 送出 `bash scripts/egress_ctl.sh start`（沒帶變數） | 結果是 `ask`（本來就問，沒有因本任務改變） | 自動：`tests/confirm_launch_test.sh`（`idg` ask） |
| TC-025 | 作法 4 | 功能 | 本分支與 `ledger.md` | 讀 `git diff <v3>...HEAD -- hooks/confirm_launch.sh` 的新增區塊 | 新區塊裡沒有 `allow` 路徑、沒有新增 `exit 0` 分支、沒有新增 `ask` 呼叫；PEER 段落是附加在同一個 `RELAY_LIST`、由原有的唯一一次 `ask` 送出 | 手動：閱卷者讀 diff，證據記於 `ledger.md`（裁決三 3） |
| TC-026 | 作法 5 | 功能 | 本分支 | 讀新增區塊的每一行 | 條件只用 bash 內建 `[[ == *…* ]]` 子字串比對；只有命中後才多一次 `[[ =~ ]]`（用 `BASH_REMATCH[1]` 取值，不用 `${CMD#*…}`）；沒有 `grep`／`jq`／`python`／子行程／`$(…)`；未帶該變數的指令只多一次子字串比對 | 手動：閱卷者讀 diff，證據記於 `ledger.md` |
| TC-027 | 作法 1；「不做」第 3 點；裁決 1 | 不在範圍 | 本分支 | `git diff <v3>...HEAD -- hooks/confirm_launch.sh` | 只有新增行：沒有刪除行、沒有改動既有行；新區塊緊接在既有 `NF_RELAY_EXTRA_DOMAINS=` 區塊之後、在同一個 `RELAY_START_RE` 命中的 `if` 裡面；EXTRA 區塊原樣；沒有抽共用函式 | 手動：閱卷者重跑 `git diff`，結果記於 `ledger.md` |
| TC-028 | 範圍：檔案；「既有斷言會被改的清單：無」 | 功能 | 本分支 | `git diff <v3>...HEAD -- tests/confirm_launch_test.sh` | 只有新增行，加在既有 `envp` 那組之後；新增 `envq` 輔助函式與 PEER 斷言列；既有行一個字都沒改、沒有刪除、沒有跳過 | 手動：閱卷者重跑 `git diff`，結果記於 `ledger.md` |
| TC-029 | 範圍：檔案 | 不在範圍 | 本分支 | `git diff --name-only origin/v3...HEAD` | 只出現 `hooks/confirm_launch.sh`、`tests/confirm_launch_test.sh`、`specs/relay-env-warning/ledger.md`（計畫檔本身與規定的 TC 檔另計，不算實作檔）；沒有其他檔 | 手動：閱卷者重跑，結果記於 `ledger.md` |
| TC-030 | 範圍：禁止碰；「不做」第 1 點 | 不在範圍 | 本分支 | `git diff origin/v3...HEAD -- scripts/ platform/ deploy/ docs/ skills/ commands/` | 輸出為空（中繼、`egress_ctl.sh`、`on_site.sh`、設定檔文件、技能與指令檔都沒動） | 手動：閱卷者重跑，結果記於 `ledger.md` |
| TC-031 | 「不做」第 2 點 | 不在範圍 | 本分支 | 讀新增區塊 | 只處理 `NF_RELAY_PEER_PREFIXES=`；沒有對別的環境變數（例如 `NF_RELAY_PORT`）或 `on_site.sh` 路徑加任何警告 | 手動：閱卷者讀 diff，結果記於 `ledger.md` |
| TC-032 | 「不做」第 4 點 | 不在範圍 | 本分支 | `git diff origin/v3...HEAD -- hooks/hooks.json` | 輸出為空（matcher 與逾時設定都沒改） | 手動：閱卷者重跑，結果記於 `ledger.md` |
| TC-033 | 完成標準第 2 點；倉庫校正失敗 #1 | 功能 | 兩個工作樹：`origin/v3`（含 #185）與本分支 | 兩邊各跑一次 `bash tests/confirm_launch_test.sh`，輸出存檔後逐行比對（閱卷者自己重跑，不只信 ledger） | 差異只有新增的 PEER 行（PEER-1…12 對應的新行）；基底上每一條既有行，在本分支的 ok／FAIL 狀態完全相同；無任何既有行由 ok 變 FAIL，本分支 FAIL 數為 0 | 手動：兩邊輸出比對，結果貼進 `ledger.md`（裁決三 3） |
| TC-034 | 完成標準第 1 點 | 功能 | 本分支，WSL／Linux | 在 WSL 執行 `bash tests/run_all.sh`（見倉庫 CLAUDE.md） | 全套綠，包含新增的 PEER 斷言 | 自動：`tests/run_all.sh` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-035 | 憲法第 13 條（安全網做不了事時要說；缺 `jq` 時閘門拒絕它無法排除的東西）與安全網「啟動要經使用者明確確認」 | 功能 | 本分支 | 執行 `bash tests/confirm_launch_test.sh`，看既有「no jq」各區段與所有既有 `ask` 斷言 | 這些區段全部維持 ok，與基底相同；新增的 PEER 區塊沒有讓常駐程式（agent_ctl／egress_ctl）的 start／stop／restart 變得更容易被放行 | 自動：`tests/confirm_launch_test.sh` |
