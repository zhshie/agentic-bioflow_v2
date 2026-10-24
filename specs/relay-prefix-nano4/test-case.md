# 測試案例：中繼的允許主機前綴改由設定 `relay_peer_prefixes` 讀入（nano4 範例）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Language: 繁體中文; identifiers and file paths stay as they are.
-->

**規格**：`specs/relay-prefix-nano4/plan.md`（本任務沒有獨立的 spec.md，計畫就是規格；裁決一～三以後者為準）　**總覽**：`test-case-overview.md`

先講幾個詞（全篇用同一個意思）：

- **中繼（relay）**：登入節點上的一支小程式，讓「沒有對外網路的計算節點」透過它上網。
- **前綴**：計算節點主機名稱的開頭，例如 `cpn3857` 的前綴是 `cpn`。中繼只放行名稱開頭符合清單的對端。
- **反查名稱**：中繼拿連進來的 IP 去查到的主機名稱。測試裡用假的反查結果來控制它。
- **預設五個**：`cpn、gpn、bgm、lgn、localhost`（台灣杉三號的）。
- **設定**：設定檔裡的 `relay_peer_prefixes`，經環境變數 `NF_RELAY_PEER_PREFIXES` 帶給中繼。
- **nano4 設定**：`NF_RELAY_PEER_PREFIXES=25a-cpn,25a-hgpn,25a-lgn`（來源是 2026-10-20 的探測）。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、退回預設）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

驗證方式的「自動」＝由 executor 寫成測試（每條在註解寫 TC 編號）；「手動」＝閱卷者用 `git diff`／讀檔核對（裁決三 10，不另寫 `docs/TESTING.md` 步驟）。`PL`＝`platform/tests/test_relay_loopback.py`。

## User Story 1 — 沒設定時，中繼跟現在一模一樣（優先度 P1）

維護者原話：「預設維持 T3 五個」；計畫：「沒設時行為與位元組都不變」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話「預設維持 T3 五個」；作法 3；`test_default_peer_prefixes_are_the_five_taiwania_ones_when_nothing_is_set` | 功能 | 環境變數 `NF_RELAY_PEER_PREFIXES` 不存在 | 載入 `scripts/nf_relay.py` | `ALLOW_HOST_PREFIXES` 恰為 `("cpn", "gpn", "bgm", "lgn", "localhost")`，型別是 tuple（名字也沒被改掉） | 自動：PL |
| TC-002 | 作法 3 | 功能 | 同上 | 讀 `DEFAULT_HOST_PREFIXES` | 常數存在，內容與 TC-001 的五個相同 | 自動：PL |
| TC-003 | 作法 3；`test_default_when_the_variable_is_empty_blank_or_all_invalid` | 例外 | 環境變數設成空字串 `""` | 載入中繼 | 得到預設五個（有沒有抱怨這一句不鎖） | 自動：PL |
| TC-004 | 同上；裁決三 7 | 例外 | 環境變數設成 `"  "`（只有空白） | 載入中繼，取 `startup_lines()` | 得到預設五個，啟動訊息含 `had no usable entry` | 自動：PL |
| TC-005 | 同上；裁決三 7 | 例外 | 環境變數設成 `","` | 同上 | 得到預設五個，啟動訊息含 `had no usable entry` | 自動：PL |
| TC-006 | 同上；作法 4 | 例外 | 環境變數設成 `"a,b"`（兩項都太短） | 同上 | 得到預設五個，啟動訊息含 `had no usable entry` | 自動：PL |
| TC-007 | 同上 | 例外 | 環境變數設成 `"*"` | 同上 | 得到預設五個，啟動訊息含 `had no usable entry` | 自動：PL |
| TC-008 | 同上 | 例外 | 環境變數設成 `"."` | 同上 | 得到預設五個，啟動訊息含 `had no usable entry` | 自動：PL |
| TC-009 | 作法 5；`test_startup_lines_are_byte_identical_to_before_when_unset` | 功能 | 環境變數不存在 | 取 `startup_lines()` | 第二行恰為 `  peers  : cpn,gpn,bgm,lgn,localhost*` | 自動：PL |
| TC-010 | 同上 | 功能 | 環境變數不存在 | 取 `startup_lines()` | 沒有任何含 `peers (this deployment)` 或 `peers: dropped` 的行 | 自動：PL |
| TC-011 | 作法 4、5 | 功能 | 環境變數不存在 | 取 `startup_lines()` | 沒有 `had no usable entry`（沒設就不該囉嗦） | 自動：PL |
| TC-012 | 「位元組都不變」 | 功能 | 環境變數不存在；測試裡存一份改動前的啟動訊息逐行原文 | 取 `startup_lines()` 與原文逐行比對 | 完全相同，一行不多一行不少 | 自動：PL |
| TC-013 | 對照表；`test_default_allows_t3_nodes_and_refuses_others` | 功能 | 預設；假反查名稱 `cpn3857.nchc.org.tw` | 呼叫 `peer_ok` | 放行 | 自動：PL |
| TC-014 | 同上 | 功能 | 預設；反查名稱 `gpn0101` | 同上 | 放行 | 自動：PL |
| TC-015 | 同上 | 功能 | 預設；反查名稱 `bgm01` | 同上 | 放行 | 自動：PL |
| TC-016 | 同上；對照表 | 功能 | 預設；反查名稱 `lgn304` | 同上 | 放行 | 自動：PL |
| TC-017 | 同上；對照表 | 功能 | 預設；反查名稱 `localhost` | 同上 | 放行 | 自動：PL |
| TC-018 | 對照表（25a- 各列） | 例外 | 預設；反查名稱依序 `25a-cpn03`、`25a-hgpn170`、`25a-lgn01`、`25a-xyz1` | 各呼叫一次 `peer_ok` | 四個都拒絕（預設不認 nano4 的名字） | 自動：PL |
| TC-019 | 對照表 | 例外 | 預設；反查名稱 `laptop.example` | 同上 | 拒絕 | 自動：PL |
| TC-020 | 對照表（比的是開頭不是包含） | 例外 | 預設；反查名稱 `evilcpn3857.example` | 同上 | 拒絕 | 自動：PL |
| TC-021 | 同上 | 例外 | 預設；反查名稱 `xcpn1` | 同上 | 拒絕 | 自動：PL |
| TC-022 | 對照表（名稱先轉小寫） | 功能 | 預設；反查名稱 `CPN3001.Example` | 同上 | 放行 | 自動：PL |
| TC-023 | 對照表（無反查紀錄）；「反查失敗即拒絕」不變 | 例外 | 預設；反查失敗 | 同上 | 拒絕，名稱記為 `<no-rdns>` | 自動：PL |
| TC-024 | 完成標準「必須原樣綠」 | 功能 | 既有 `tests/nf_relay_domains_test.sh` 一個字沒改 | 執行 | 既有全部（含 TC-019 的 tuple 比對 `('cpn', 'gpn', 'bgm', 'lgn', 'localhost')`）通過 | 自動：`tests/nf_relay_domains_test.sh` |
| TC-025 | 完成標準；`test_tc075_golden_still_holds` | 功能 | 既有 TC-075 測試不改（真行程、30 個請求、對 `platform/tests/fixtures/relay_golden.json`） | 執行 | 30 個回應與 golden 檔逐項相同 | 自動：PL |
| TC-026 | 完成標準 | 功能 | PL 既有測試（含 `127.0.0.1` 放行、`127.0.0.2` 得 403 與 `DENY-PEER`）一個字沒改 | 執行 | 既有全部通過 | 自動：PL |
| TC-027 | 完成標準 | 功能 | 既有 `tests/egress_ctl_restart_test.sh` 一個字沒改 | 執行 | 既有全部通過 | 自動：`tests/egress_ctl_restart_test.sh` |
| TC-028 | shell 層第二條 | 功能 | 設定檔沒有 `relay_peer_prefixes`，環境變數也沒設 | `egress_ctl.sh start` | `relay.log` 含 `peers  : cpn,gpn,bgm,lgn,localhost*` | 自動：`tests/egress_ctl_restart_test.sh` |
| TC-029 | 裁決（鏡射 TC-019 最後一條） | 例外 | 預設；`NF_RELAY_EXTRA_DOMAINS=download.example.org`；反查名稱 `download.example.org` | 呼叫 `peer_ok` | 拒絕（額外網域不會變成對端） | 自動：PL |

## User Story 2 — 設了就取代預設，`localhost` 永遠保留（優先度 P1）

計畫例子：`NF_RELAY_PEER_PREFIXES=25a-cpn,25a-hgpn,25a-lgn`（nano4 設定）；設定「取代」不是「追加」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 作法 3；`test_setting_replaces_the_list_and_localhost_is_always_kept` | 功能 | `NF_RELAY_PEER_PREFIXES=25a-cpn,25a-hgpn,25a-lgn` | 載入中繼 | `ALLOW_HOST_PREFIXES == ("25a-cpn", "25a-hgpn", "25a-lgn", "localhost")` | 自動：PL |
| TC-031 | 對照表 | 功能 | nano4 設定；反查名稱 `25a-cpn03` | `peer_ok` | 放行 | 自動：PL |
| TC-032 | 對照表 | 功能 | nano4 設定；反查名稱 `25a-hgpn170` | 同上 | 放行 | 自動：PL |
| TC-033 | 對照表 | 功能 | nano4 設定；反查名稱 `25a-lgn01` | 同上 | 放行 | 自動：PL |
| TC-034 | 對照表；裁決一（`localhost` 永遠在） | 功能 | nano4 設定（清單裡沒寫 `localhost`）；反查名稱 `localhost` | 同上 | 放行 | 自動：PL |
| TC-035 | 對照表；裁決一（取代不是追加） | 例外 | nano4 設定；反查名稱 `cpn3857.nchc.org.tw` | 同上 | 拒絕 | 自動：PL |
| TC-036 | 對照表 | 例外 | nano4 設定；反查名稱 `lgn304`（舊預設） | 同上 | 拒絕 | 自動：PL |
| TC-037 | 對照表；作法 7（不用更短的 `25a-`） | 例外 | nano4 設定；反查名稱 `25a-gpu1`、`25a-xyz1`（開頭是 `25a-` 但不在清單） | 各呼叫一次 | 兩個都拒絕 | 自動：PL |
| TC-038 | 對照表 | 例外 | nano4 設定；反查名稱 `CPN3001.Example` | 同上 | 拒絕（名稱轉小寫後是 `cpn…`，不在 nano4 清單） | 自動：PL |
| TC-039 | 對照表 | 例外 | nano4 設定；反查名稱 `laptop.example`；另一次反查失敗 | 同上 | 兩次都拒絕 | 自動：PL |
| TC-040 | 對照表 | 例外 | nano4 設定；反查名稱 `evilcpn3857` | 同上 | 拒絕 | 自動：PL |
| TC-041 | 作法 2；裁決三 8；`test_invalid_entries_are_dropped_and_named_at_startup` | 例外 | 設定值含內嵌換行，例如 `"cp\nn"`（中間一個換行字元）；與一個合法項目並用 | 取 `startup_lines()` | 該項被丟掉並被點名；輸出的行數只比沒有這項時多「一行 dropped」，沒有被換行字元切成多一行 | 自動：PL |
| TC-042 | 作法 2；同上 | 例外 | 設定值含 `\x1b[31m`（終端機換色字元） | 取 `startup_lines()` | 輸出裡沒有任何原始控制字元（含 ESC）；該項被點名丟掉 | 自動：PL |
| TC-043 | 作法 5 | 功能 | nano4 設定 | 取 `startup_lines()` | 有一行 `  peers  : 25a-cpn,25a-hgpn,25a-lgn,localhost*`（有效清單被印出來） | 自動：PL |
| TC-044 | 作法 5 | 功能 | nano4 設定 | 同上 | 另有一行 `  peers (this deployment): set by relay_peer_prefixes` | 自動：PL |
| TC-045 | 作法 2；`test_prefix_match_is_on_the_reverse_name_start_and_case_is_folded` | 功能 | 設定 `"CPN, GPN"`；反查名稱 `CPN3001.Example` | `peer_ok` | 放行（設定與名稱都先轉小寫、設定項去頭尾空白） | 自動：PL |
| TC-046 | 同上；對照表（`evilcpn3857`） | 例外 | 設定 `"CPN, GPN"`；反查名稱 `mycpn3001` | 同上 | 拒絕（比的是開頭） | 自動：PL |
| TC-047 | 作法 2；`test_an_empty_string_never_becomes_a_prefix`；手算 `"cpn,,lgn"` | 例外 | 設定 `"cpn,,lgn"` | 載入中繼 | 結果為 `("cpn", "lgn", "localhost")`；`""` 不在其中；空項目不被當成錯誤點名 | 自動：PL |
| TC-048 | 同上 | 例外 | 設定 `",cpn"` | 載入中繼 | 結果元組裡沒有 `""` | 自動：PL |
| TC-049 | 同上 | 例外 | 設定 `"cpn,"` | 載入中繼 | 結果元組裡沒有 `""` | 自動：PL |
| TC-050 | 同上（防 `startswith("")` 恆真） | 例外 | TC-047～049 的三種設定；反查名稱 `laptop.example` | 各自 `peer_ok` | 全部拒絕（沒有變成對全世界開放） | 自動：PL |
| TC-051 | 作法 2；測試名單 `"25a-cpn, a.b, ab, UPPER_CASE, ça-cpn, ok-x"` | 功能 | 該設定值 | 載入中繼 | 有效項目恰為 `25a-cpn`、`ok-x`，外加 `localhost`，順序如此 | 自動：PL |
| TC-052 | 同上 | 例外 | 同 TC-051 | 取 `startup_lines()` | 含 `dropped 'a.b'`、`dropped 'ab'`、`dropped 'UPPER_CASE'`，每項後面有一句原因 | 自動：PL |
| TC-053 | 同上（`ça-cpn`） | 例外 | 同 TC-051 | 取 `startup_lines()` | 有一行 `dropped` 點名這一項（非 ASCII 字元依 `_clean()` 可能顯示成 `?`，不鎖字元），且它不在有效清單 | 自動：PL |

## User Story 3 — 設定檔的值一路帶到中繼（優先度 P1）

計畫：「中繼本身不讀設定檔」，由 `egress_ctl.sh`／`on_site.sh` 從設定讀出放進環境；環境變數優先。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-054 | 作法 6；裁決三 5 | 功能 | 設定檔 `reach` 為 ssh，含 `relay_peer_prefixes: 25a-cpn,25a-lgn` | 執行 `on_site.sh`（假 ssh，看遠端指令列） | 指令列含 `NF_RELAY_PEER_PREFIXES=` 與該值（逗號有正確跳脫） | 自動：`tests/on_site_test.sh` |
| TC-055 | 作法 6（未設時與今天一字不差） | 功能 | 同上但設定檔沒有該鍵 | 同上 | 遠端指令列完全沒有 `NF_RELAY_PEER_PREFIXES`，其餘與改動前相同 | 自動：`tests/on_site_test.sh` |
| TC-056 | 作法 6；裁決三 5 | 功能 | `reach: local`，設定檔含 `relay_peer_prefixes: 25a-cpn,25a-lgn`，假 `egress_ctl.sh` 印出它收到的環境變數 | 以 `on_site.sh --script scripts/egress_ctl.sh start` 執行 | 假腳本收到 `25a-cpn,25a-lgn` | 自動：`tests/on_site_test.sh` |
| TC-057 | 作法 6；裁決三 5；裁決 5（偷渡路徑是關的） | 例外 | `reach: local`，設定檔沒有該鍵；呼叫者自己的環境設 `NF_RELAY_PEER_PREFIXES=evil-x` | 同上 | 假腳本收到的值是空的，`evil-x` 帶不進去 | 自動：`tests/on_site_test.sh` |
| TC-058 | shell 層第一條 | 功能 | `env.yaml` 寫 `relay_peer_prefixes: 25a-cpn,25a-lgn`，環境變數未設 | `egress_ctl.sh start` | `relay.log` 含 `peers  : 25a-cpn,25a-lgn,localhost*` | 自動：`tests/egress_ctl_restart_test.sh` |
| TC-059 | shell 層第一條（環境變數優先） | 功能 | 接續 TC-058 的狀態 | 以前綴 `NF_RELAY_PEER_PREFIXES=zzz-aaa` 執行 `restart` | 新一輪 `relay.log` 含 `peers  : zzz-aaa,localhost*` | 自動：`tests/egress_ctl_restart_test.sh` |
| TC-060 | shell 層第三條 | 功能 | `tests/nf_relay_domains_test.sh` 新增一段：與 TC-058 同值的 `NF_RELAY_PEER_PREFIXES`；既有 TC-019 六條原樣 | 用該檔的 `peer` 輔助函式代入 `25a-cpn03`、`cpn3001.example` | 前者 `True`，後者 `False` | 自動：`tests/nf_relay_domains_test.sh` |
| TC-061 | 真行程；`test_a_real_relay_started_with_a_prefix_setting_logs_it_and_still_refuses_a_stranger` | 功能 | 真的啟動中繼，`NF_RELAY_PEER_PREFIXES=zzz-nomatch` | 以來源 `127.0.0.1`（反查為 `localhost`）送請求 | 回應不是 403（`localhost` 永遠保留而被放行） | 自動：PL |
| TC-062 | 同上 | 例外 | 同上 | 以來源 `127.0.0.2` 送請求 | 回應 403，中繼 log 有 `DENY-PEER` | 自動：PL |
| TC-063 | 同上 | 功能 | 同上 | 讀中繼啟動輸出 | 含 `peers  : zzz-nomatch,localhost*` 與 `set by relay_peer_prefixes` | 自動：PL |

## User Story 4 — 文件說清楚（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-064 | 作法 7；裁決三 6 | 功能 | `docs/SETTINGS.md` 的「Travels」那一列 | 讀該列的鍵名列舉 | 含 `relay_peer_prefixes`（跟著設定根走的鍵，不在機器專屬那一格） | 自動：PL（或 `platform/tests/test_launch_docs.py` 風格的文件測試） |
| TC-065 | 作法 7；`test_setting_is_documented` | 功能 | `docs/SETTINGS.md` | 讀檔 | 含 `relay_peer_prefixes`、`25a-cpn`、`replaces`、`egress_ctl.sh restart` | 自動：PL |
| TC-066 | 作法 7 | 功能 | `docs/SETTINGS.md` 新增的那一列與範例 | 閱卷者讀 `git diff` | 寫明：逗號分隔、每項 3–32 字小寫字母數字與 `-`；取代預設五個且 `localhost` 永遠保留；沒設＝台灣杉三號五個；無效項目在啟動訊息點名；範例是 `25a-cpn,25a-hgpn,25a-lgn`、標明來源是 2026-10-20 探測、並說明為何沒用更短的 `25a-` | 手動：`git diff` 讀檔 |
| TC-067 | 作法 7；裁決 6 | 功能 | `docs/SITE_ADAPTER.md` nano4 小節之後 | 閱卷者讀 `git diff` | 有「備援：萬一 nano4 對外封起來」一段，只說『若將來被封可這樣讓中繼接受』，明講這條路徑 `never been run on nano4`（只有名稱來自探測），範例同 TC-066 | 手動：`git diff` 讀檔 |
| TC-068 | 原話「Egress＝直連無 relay」；`test_setting_is_documented` | 功能 | `docs/SITE_ADAPTER.md` | 讀檔 | nano4 一列仍含 `no relay`，且全文含 `never been run on nano4` | 自動：PL |

## User Story 5 — 合併規則與邊界（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-069 | 作法 2；`test_more_than_twenty_entries_are_cut_and_the_cut_is_named` | 例外 | 設定 21 個合法且互不相同的項目 | 載入中繼並取 `startup_lines()` | 只取前 20 個（外加 `localhost`）；第 21 個在啟動訊息被點名丟掉並說明超過上限 | 自動：PL |
| TC-070 | 作法 3；手算 `"localhost,cpn"` | 功能 | 設定 `"localhost,cpn"` | 載入中繼 | 結果為 `("localhost", "cpn")`，`localhost` 不重複補 | 自動：PL |
| TC-071 | 作法 2（去重、保留順序） | 功能 | 設定 `"cpn,lgn,cpn"` | 載入中繼 | 結果為 `("cpn", "lgn", "localhost")` | 自動：PL |
| TC-072 | `test_an_extra_domain_or_a_domain_variable_does_not_become_a_peer` | 例外 | 同時設 `NF_RELAY_PEER_PREFIXES=25a-cpn` 與 `NF_RELAY_EXTRA_DOMAINS=download.example.org`；反查名稱 `download.example.org` | `peer_ok` | 拒絕 | 自動：PL |
| TC-073 | 裁決 3（3–32 字） | 功能 | 設定一個剛好 32 字的合法項目 | 載入中繼 | 該項被接受，不被點名 | 自動：PL |
| TC-074 | 裁決 3 | 例外 | 設定一個 33 字的項目（其餘合法） | 載入中繼並取 `startup_lines()` | 該項被丟掉並被點名 | 自動：PL |
| TC-075 | 作法 2（必須以字母或數字開頭） | 例外 | 設定 `"-abc"` 與一個合法項目 | 同上 | `-abc` 被丟掉並被點名，合法項目保留 | 自動：PL |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-076 | 不變量 13／原則 VI（讀不進來的清單不准默默變成別的行為）；作法 4 | 例外 | 真的啟動中繼，`NF_RELAY_PEER_PREFIXES=ab`（一項都不合格） | 讀中繼啟動輸出，並用 `127.0.0.1` 與反查為 `cpn…` 的假對端各測一次 | 輸出含 `had no usable entry`，peers 行是預設五個，行為等同沒設 | 自動：PL |
| TC-077 | 同上 | 例外 | 真的啟動中繼，設定 `25a-cpn, a.b` | 讀中繼啟動輸出 | 有效清單是 `25a-cpn,localhost`，且有一行點名 `dropped 'a.b'` | 自動：PL |
| TC-078 | 原則 V／完成標準（沒有新增常駐程式） | 功能 | 改動後的 `scripts/` | 執行 `tests/no_second_run_state_test.sh` | 通過（本任務沒有新增 `nohup`／`setsid`／`daemon`） | 自動：`tests/no_second_run_state_test.sh` |
| TC-079 | 作法 8 | 功能 | 改動後的 `skills/`、`commands/` | 執行 `tests/command_layer_is_site_neutral.sh` | 通過，且這兩個資料夾沒有出現 `relay_peer_prefixes` | 自動：`tests/command_layer_is_site_neutral.sh` |
| TC-080 | 完成標準 | 功能 | 改動後的整個 repo | 執行 `tests/egress_allow_test.sh` | 通過（指令文件沒有教人編輯 `nf_relay`／`ALLOW_DOMAINS`） | 自動：`tests/egress_allow_test.sh` |
| TC-081 | 完成標準 | 功能 | 改動後的整個 repo | 執行 `platform/tests/test_scope.py` 與 `platform/tests/test_launch_docs.py` | 兩者都通過 | 自動 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-082 | 不做：不改中繼其他行為（網域白名單、`DENY-PRIVATE`、回送轉發、DNS 快取、反查失敗即拒絕） | 不在範圍 | `scripts/nf_relay.py` 的 diff | 閱卷者讀 diff | 只有對端前綴的解析、啟動訊息、`peer_ok` 用新元組這幾處有變；其他函式與常數沒動，`_PEER_CACHE` 沒動 | 手動：`git diff` |
| TC-083 | 不做：不讓 nano4 預設用中繼、不改六契約表「Egress：直連無 relay」 | 不在範圍 | `docs/SITE_ADAPTER.md` 的 diff | 閱卷者讀 diff | 六契約表 nano4 那一列一個字沒改；新段沒有說 nano4 需要或預設使用中繼 | 手動：`git diff` |
| TC-084 | 不做：不改 `configs/sites/*`、不加 nano4 的 CE 設定 | 不在範圍 | repo diff | `git diff --stat` | `configs/`、`deploy/` 底下沒有任何變動 | 手動：`git diff` |
| TC-085 | 不做：不啟動、不測試真的 nano4 或台灣杉三號上的中繼 | 不在範圍 | 新增與改動的所有測試與腳本 | 閱卷者讀 | 沒有任何一條會連站台或 HPC；真行程測試只在本機回送位址 | 手動：`git diff` |
| TC-086 | 不做：不新增 `.py` 檔、不新增相依套件 | 不在範圍 | repo diff 與 `scripts/nf_relay.py` 的 import 區 | 閱卷者讀 | 沒有新增的 `.py` 檔；`nf_relay.py` 只用標準函式庫（沒有新的第三方 import） | 手動：`git diff` |
| TC-087 | 範圍：檔案（只准改這些）；完成標準 | 不在範圍 | `git diff --name-only origin/v3...HEAD` | 閱卷者比對 | 只出現計畫「範圍」列的檔案（含裁決三加入的 `tests/on_site_test.sh` 與 `specs/relay-prefix-nano4/` 下的帳本）；`platform/abf_*`、`deploy/`、`configs/`、`hooks/`、`docs/OPERATIONS.md`、`docs/INSTALL.md` 無變動 | 手動：`git diff` |
| TC-088 | 不做：不用正規式或萬用字元、不接受含點的項目 | 不在範圍 | 設定 `"cpn*"`、`"cpn.nchc"`（再加一個合法項目） | 載入中繼並取 `startup_lines()` | 兩項都被丟掉並被點名，沒有被當成萬用字元或網域；只有合法項目留下 | 自動：PL |
| TC-089 | 裁決 5、裁決二 2：不改 `hooks/confirm_launch.sh` | 不在範圍 | repo diff | 閱卷者讀 | `hooks/` 無任何變動；『直接用環境變數前綴啟動中繼時 hook 不會警告』是已知小缺口，由總覽回報給維護者，不在本次做 | 手動：`git diff` |
| TC-090 | 不做：不改 `skills/`、`commands/` | 不在範圍 | repo diff | 閱卷者讀 | 這兩個資料夾無任何變動 | 手動：`git diff` |
| TC-091 | 不做：不做 `site_profile` 的程式讀取 | 不在範圍 | repo diff | 閱卷者搜尋新增的行 | 新增的程式碼沒有讀取 `site_profile` | 手動：`git diff` |
| TC-092 | 範圍：既有測試一個字都不改；不改 `spec.md`、`test-case*.md`、憲法、歷史規格文件 | 不在範圍 | `platform/tests/test_relay_loopback.py`、`tests/egress_ctl_restart_test.sh`、`tests/nf_relay_domains_test.sh`、`tests/on_site_test.sh` 與歷史文件 `specs/002-relay-allowlist/*`、`specs/007b-launch/research.md` 的 diff | 閱卷者與 base 逐檔比對 | 四個測試檔只有「新增」的行（`Relay` 類別只多一個預設為 `None` 的選填參數 `extra_env`，既有斷言與 TC-019 的 tuple 比對原樣）；歷史文件、憲法、`test-case*.md` 無變動 | 手動：`git diff` |

<!--
Rules for the writer:
- Every requirement and example in the plan maps to at least one TC. Out-of-scope items map to 不在範圍 TCs.
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
