# 測試案例：進度回報改走公開網址（way_back: direct）

<!--
Written by the verifier (CONTRACT mode) from specs/way-back-direct/plan.md. 本任務沒有 spec.md；plan.md 就是規格，維護者原話（裁示 8、裁示 13）引在 plan 內。
Language: 繁體中文; identifiers and file paths stay as they are.
-->

**規格**：`specs/way-back-direct/plan.md`　**總覽**：`test-case-overview.md`

白話先講：計算節點要把「跑到哪了」回報給平台。國網 Taiwania-3（T3）的計算節點上不了外網，只能靠 SSH 反向轉發加中繼程式（relay）繞一圈（現行做法，叫 `forward`）。nano4 的計算節點可以直連外網，所以新增一種做法 `direct`：直接打平台的 https 公開網址。**沒設定的時候一切照舊（`forward`）。**

類型只有三種：功能（做到了）、例外（出錯時的反應）、不在範圍（這次明講不做）。

名詞：
- **站台設定檔**：站台代理（在使用者電腦上）讀的設定，新鍵 `way_back` 與 `platform_public_url`。
- **bundle**：一次 launch 要送到站台的「整包內容」，其中 `tower` 欄位說進度怎麼回報。
- **`--check-forward`**：launch 在 forward 模式下，為了確認反向通道還開著，會經 `scripts/on_site.sh` 呼叫的檢查；測試用「假的 ssh runner」記錄所有送往站台的呼叫。

## User Story 1 — reach 為 ssh 時用 `way_back: direct`，進度直接打公開網址（優先度 P1）

維護者原話（裁示 8）：「進度回報網址：本週用 Tailscale Funnel 給筆電平台一個 https 公開網址；正式版平台跑在常開機或託管主機的公開網址。程式改法兩者相同（`way_back: direct` ＋ `platform_public_url`），所以現在就照正式版的方式寫。」
裁示 13：「站台代理：國網用戶裝在個人電腦（持 2FA）」——站台仍在使用者電腦，reach 仍是 ssh。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 失敗先行測試 `test_tc023b…`；完成標準；作法第 3 點 | 功能 | 站台設定 reach 為 ssh、`way_back: direct`、`platform_public_url: https://abf.example.ts.net` | 組出一次 launch 的 bundle | bundle 的 `tower.mode` 等於 `"direct"`，`tower.endpoint` 等於 `https://abf.example.ts.net`（就是設定的那個網址，不是代理自己連平台用的網址） | 自動：`platform/tests/test_station_channel.py` |
| TC-002 | 完成標準；作法第 3 點「direct 時 launch 不呼叫 --check-forward」；失敗先行測試 | 功能 | 同 TC-001，用假的 ssh runner 記錄所有送往站台的呼叫 | 完整跑一次 launch | 記錄中**沒有任何** `--check-forward` 呼叫 | 自動：`platform/tests/test_station_channel.py` |
| TC-003 | 目標「不必靠 SSH 反向轉發」；測試名 `…opens_no_forward…` | 功能 | 同 TC-002 | 完整跑一次 launch | 記錄中沒有開反向通道的呼叫（沒有 `--forward`，也沒有 `-O forward`）；站台上沒有寫出 `_relay/forward_port` | 自動：`platform/tests/test_station_channel.py` |
| TC-004 | 作法第 3 點「不再要求 `platform_local`」 | 功能 | reach 為 ssh、`way_back: direct`、https 公開網址；代理回報的 `platform_local` 為 false，也沒有 `forward_file` | 組出 bundle | 成功組出 `tower.mode == "direct"`；不會出現「反向通道要求平台與代理在同一台機器」或「沒有回報合法的 forward 檔路徑」這兩種拒絕 | 自動：`platform/tests/test_station_channel.py` |
| TC-005 | 作法第 3 點 loopback 例外（給本機測試） | 功能 | reach 為 ssh、`way_back: direct`、`platform_public_url: http://127.0.0.1:8787` | 組出 bundle | `tower.mode == "direct"`，`tower.endpoint` 指向 `http://127.0.0.1:8787`（不被拒絕） | 自動：`platform/tests/test_station_channel.py` |
| TC-006 | 作法第 3 點 loopback 例外 | 功能 | 同 TC-005，但網址是 `http://localhost:8787` | 組出 bundle | `tower.mode == "direct"`，`tower.endpoint` 指向 `http://localhost:8787`（不被拒絕） | 自動：`platform/tests/test_station_channel.py` |
| TC-007 | 裁示 13（站台仍是 ssh）；完成標準 | 功能 | 同 TC-001，假站台能正常回應 | 從代理收到 launch 工作，一路跑到送出 | 工作最後狀態為完成（送出了 `sbatch`），且所有往站台的呼叫仍走 ssh；與 TC-002、TC-003 同一回合驗證 | 自動：`platform/tests/test_station_channel.py` |

## User Story 2 — `direct` 但網址不安全時，拒絕 launch（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-008 | 作法第 4 點；失敗先行測試 `test_tc023c…` | 例外 | reach 為 ssh、`way_back: direct`、`platform_public_url: http://abf.example.ts.net`（明文 http、非 loopback） | 嘗試 launch | launch 被拒絕，沒有產生 bundle | 自動：`platform/tests/test_station_channel.py` |
| TC-009 | 作法第 4 點「訊息說明『進度回報需要 https 公開網址或 loopback』」；專長守則（錯誤訊息） | 例外 | 同 TC-008 | 看拒絕訊息 | 訊息說明原因與處理方式，意思是「進度回報需要 https 公開網址或 loopback」（含 `https` 與 `loopback` 兩詞）；不含 Traceback、站台設定檔的完整路徑、任何密鑰 | 自動：`platform/tests/test_station_channel.py` |
| TC-010 | 作法第 4 點「拒絕 launch」 | 例外 | 同 TC-008，用假的 ssh runner 記錄呼叫 | 嘗試 launch | 拒絕之後，假站台上沒有新資料夾、沒有 `sbatch`、沒有任何反向通道呼叫（`--check-forward`／`--forward`）——拒絕發生在動站台之前 | 自動：`platform/tests/test_station_channel.py` |
| TC-011 | 作法第 4 點（非 loopback 的 http） | 例外 | `way_back: direct`、`platform_public_url: http://192.168.1.5:8787`（私網 IP，不是 loopback） | 嘗試 launch | 同 TC-008 被拒絕、訊息相同 | 自動：`platform/tests/test_station_channel.py` |
| TC-012 | 作法第 4 點（loopback 只限 127.0.0.1／localhost） | 例外 | `way_back: direct`、`platform_public_url: http://localhost.example.com:8787`（長得像 localhost 的外部網域） | 嘗試 launch | 被拒絕、訊息同 TC-008（不能因為網址以 `localhost` 開頭就放行） | 自動：`platform/tests/test_station_channel.py` |

## User Story 3 — 沒設定時一切照舊，T3 不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 作法第 1 點「預設：reach 為 ssh → forward」；完成標準「T3 路徑不變」 | 功能 | reach 為 ssh，設定檔完全沒有 `way_back` | 組出 bundle 並跑一次 launch | `tower.mode == "forward"`、`tower.forward_file` 為站台儲存區的 `_relay/forward_port`；launch 有呼叫 `--check-forward`（與現在相同） | 自動：`platform/tests/test_station_channel.py` |
| TC-014 | 作法第 1 點 | 功能 | reach 為 ssh、`way_back: forward`（明寫），也沒有公開網址 | 組出 bundle 並跑 launch | 結果與 TC-013 逐項相同 | 自動：`platform/tests/test_station_channel.py` |
| TC-015 | 作法第 3 點（只有 `way_back == direct` 才走公開網址） | 功能 | reach 為 ssh、沒有 `way_back`（或 `forward`），但設定檔有 `platform_public_url: https://abf.example.ts.net` | 組出 bundle 並跑 launch | 仍是 `tower.mode == "forward"`，公開網址被忽略；仍呼叫 `--check-forward` | 自動：`platform/tests/test_station_channel.py` |
| TC-016 | 失敗先行測試「預設行為逐位元同現在」；reach local 現行行為 | 功能 | reach 為 local，沒有 `way_back` | 組出 bundle | `tower.mode == "direct"`、`tower.endpoint` 為代理連平台用的網址，與改動前相同；沒有 `--check-forward` | 自動：`platform/tests/test_launch_bundle.py`、`platform/tests/test_station_launch.py` 既有案例 |
| TC-017 | 作法第 2 點（forward 的條件沒放寬） | 例外 | reach 為 ssh、沒有 `way_back`、代理回報 `platform_local` 為 false | 組出 bundle | 仍被拒絕，訊息仍是「反向通道要求平台與代理在同一台機器」（既有 `test_tc024_a_reverse_forward_needs_the_platform_on_the_same_machine` 不改仍過） | 自動：`platform/tests/test_launch_bundle.py` |
| TC-018 | 專長守則（資料結構）：不需要 migration | 功能 | 平台資料庫裡存的是舊代理回報的 facts（沒有 `way_back`、沒有 `platform_public_url`）；reach 為 ssh | 以這份 facts 組出 bundle | 當成 `forward`，與 TC-013 相同；讀出時不報錯。理由：facts 以 JSON 存在 `agents.facts_json`，沒有新欄位，故不需要 migration | 自動：`platform/tests/test_station_channel.py` |
| TC-019 | 失敗先行測試「`test_relay_loopback` 與既有 forward 測試不動」 | 功能 | 改動完成後 | 跑 `test_relay_loopback.py` 與 `test_station_channel.py` 中既有的 forward 案例；與 base 比對 | 這些案例的程式碼與斷言和 base 完全相同（只新增、沒有刪改），而且全部通過 | 自動：`platform/tests/test_relay_loopback.py`、`platform/tests/test_station_channel.py` |

## User Story 4 — 代理回報這兩個設定，平台只收合法值（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 作法第 2 點「`own_facts` 回報 `way_back` 與 `platform_public_url`」 | 功能 | 站台設定檔寫 `way_back: direct` 與 `platform_public_url: https://abf.example.ts.net` | 代理啟動、送出 hello | hello 的 facts 含 `way_back == "direct"`、`platform_public_url == "https://abf.example.ts.net"`，其他既有欄位不變 | 自動：`platform/tests/test_station_launch.py` 或 `test_station_channel.py` |
| TC-021 | 作法第 1 點預設值 | 功能 | reach 為 ssh，設定檔沒寫 `way_back`、沒寫公開網址 | 代理送出 hello | facts 的 `way_back == "forward"`，`platform_public_url` 為空（None） | 自動：`platform/tests/test_station_channel.py` |
| TC-022 | 作法第 2 點「clean_facts 白名單…值只允許字面值」 | 例外 | 代理（或惡意來源）送來的 facts 中 `way_back` 為 `"sideways"`、或 `["direct"]`、或 `5` | 平台整理 facts（`clean_facts`） | `way_back` 一律被丟成 None，不會原樣存起來；`"forward"`、`"direct"` 兩個字面值則保留 | 自動：`platform/tests/test_launch_platform.py` 或 `test_station_channel.py` |
| TC-023 | 作法第 2 點「值只允許…https URL」 | 例外 | facts 中 `platform_public_url` 為 `5`、`["https://x"]`、`javascript:alert(1)`、`ftp://abf.example.ts.net` | 平台整理 facts | 每一個都被丟成 None | 自動：`platform/tests/test_launch_platform.py` 或 `test_station_channel.py` |
| TC-024 | 作法第 2 點 | 功能 | facts 中 `platform_public_url` 為 `https://abf.example.ts.net` | 平台收下 hello 後再讀回（register → get_facts） | 讀回的 `platform_public_url` 與 `way_back` 和送出的相同；未知欄位（例如 `evil`）仍被丟掉（既有行為） | 自動：`platform/tests/test_launch_platform.py` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 不做：「不改 `_head_script`」 | 不在範圍 | 同一組 forward 設定，分別用 base 與本分支組 bundle | 比對 bundle 的 `files`（含 head.sh）與 `tower` | 逐位元相同；`launch.py` 中 `_head_script` 的程式碼沒有任何差異 | 自動（比對 base 輸出）；`_head_script` 差異由閱卷以 `git diff` 核對 |
| TC-026 | 不做：「不改 relay 程式（M1-11 備援）」 | 不在範圍 | 改動完成後 | 閱卷者看 `git diff <base>...HEAD` | relay 相關檔案（`scripts/on_site.sh` 的 relay／forward 區段、egress／relay 程式）沒有任何變動 | 閱卷核對 git diff（無法用執行測試證明「沒改」） |
| TC-027 | 不做：「不改 preflight」 | 不在範圍 | 改動完成後 | 閱卷者看 `git diff`，並跑既有 preflight 測試 | preflight 相關程式沒有變動；既有 preflight 測試不改仍過 | 閱卷核對 git diff；既有測試自動 |
| TC-028 | 裁示 13：站台仍在使用者電腦，reach 仍是 ssh | 不在範圍 | `way_back: direct`、reach 為 ssh | 代理送 hello、跑 launch | hello 的 `reach` 仍是 `"ssh"`（`direct` 不會把 reach 改成 local）；往站台的呼叫仍全部經 ssh | 自動：`platform/tests/test_station_channel.py` |
| TC-029 | 環境事實：「Tailscale Funnel 由維護者安裝；本任務不處理網路」 | 不在範圍 | 改動完成後 | 閱卷者搜尋 diff 中的程式碼 | 沒有任何安裝、啟動、設定 Tailscale／Funnel／反向代理的程式；網址只從設定檔讀 | 閱卷核對 git diff |
| TC-030 | 範圍：檔案（只動四個檔案） | 不在範圍 | 改動完成後 | `git diff --name-only <base>...HEAD`（排除 `specs/way-back-direct/` 自己的檔案） | 只出現 `platform/abf_station/launch.py`、`platform/abf_station/agent.py`、`platform/abf_platform/common.py`、`platform/tests/test_station_channel.py`；`launch.py` 內只有 `_tower`、`own_facts` 變動（`_prechecks` 的 forward 才呼叫 `_channel` 原本已成立，不需改） | 閱卷核對 git diff |

## 憲法與安全網（含 backend 專長守則）

本任務沒有新增使用者可見的動作、沒有新增網頁／API／聊天指令，所以專長守則中的「對等性」「跨使用者」兩類 TC 不適用（理由見總覽）。與本任務有關的是確認管道、錯誤訊息、密鑰、migration（TC-018）與憲法第 3、4 條。

| 編號 | 憲法條目／專長守則 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-031 | 專長守則：確認管道（每個寫入動作未經確認不得寫入） | 例外 | `way_back: direct` 的 launch 工作，但沒有帶確認（或確認屬於別的內容） | 代理收到該工作 | 被拒絕，站台上沒有寫任何東西、沒有 `sbatch`（`direct` 沒有開出一條繞過確認的路） | 自動：`platform/tests/test_station_channel.py` |
| TC-032 | 專長守則：確認管道；憲法 4.0.0（送出前須使用者確認的就是這份 bundle） | 功能 | 兩份除了 `platform_public_url` 不同（`https://a.example.ts.net` 對 `https://b.example.ts.net`）其餘完全相同的 direct bundle | 比較兩份 bundle 的 sha256；用其中一份的確認去送另一份 | 兩個 sha256 不同；用 A 的確認送 B 被拒絕（回報網址是被確認內容的一部分，不能事後換） | 自動：`platform/tests/test_station_channel.py` |
| TC-033 | 專長守則：密鑰不得出現在日誌或任何回應中 | 例外 | `way_back: direct` 的 launch，測試用的 token 字串為已知值 | 跑完整個 launch，收集所有送往站台的指令列、拒絕訊息、hello facts | 這些內容都找不到該 token 字串（與 `test_tc037…` 對 forward 的檢查同等嚴格） | 自動：`platform/tests/test_station_channel.py` |
| TC-034 | 憲法第 3 條（位置來自設定，不寫死）；檢查 `tests/no_hardcoded_paths.sh` | 功能 | 改動完成後 | 跑 `bash tests/no_hardcoded_paths.sh` | 通過；程式碼裡沒有寫死的公開網址或主機名（`ts.net`、`example` 只出現在測試裡） | 自動：`tests/no_hardcoded_paths.sh` |
| TC-035 | 憲法第 4 條（不在共用層點名排程器／站台）；檢查 `tests/command_layer_is_site_neutral.sh` | 功能 | 改動完成後 | 跑 `bash tests/command_layer_is_site_neutral.sh` | 通過；`way_back` 的新程式沒有寫死 `nano4`、`Taiwania`、`T3`、`Funnel` 等站台名 | 自動：`tests/command_layer_is_site_neutral.sh` |
