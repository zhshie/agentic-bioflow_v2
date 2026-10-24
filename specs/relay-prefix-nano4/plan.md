---
id: relay-prefix-nano4
title: 登入節點的中繼（relay）允許連線的計算節點名稱前綴，改由設定 relay_peer_prefixes 決定（沒設就跟現在一模一樣）
tier: A
kinds: backend
lane: L-relay（只動 scripts/ 的中繼三件套與其測試、兩份文件；不與 abf_station／abf_launch／abf_platform 任何檔相交。replan 表把它排在 L1 站台任務之後，只是原文如此，檔案上不衝突）
base: v3
source: memory/PLAN-abf-v3-replan-2026-10.md Milestone 1 的 M1-11（第 137 行）；nano4 節點名稱出處見「環境事實」
---

# relay-prefix-nano4

> 本檔由 developer-agent 寫（2026-10-24）。A 級（使用者看不到新畫面、預設行為不變的後端備援）→ verifier 通過＋CI 綠由 developer-agent 自合。
> **這是備援，不是 nano4 的主路徑**：nano4 計算節點可直連外網、不需要中繼（探測紀錄與 `docs/SITE_ADAPTER.md` 都這樣寫）。這個任務只是讓「哪天國網把 nano4 對外封起來」時，中繼已經能在 nano4 上用，不必再改程式。
> **車道注意**：本任務同時要改 `docs/SETTINGS.md` 與 `docs/SITE_ADAPTER.md`；別與也在改這兩份文件的任務（例如 settings-nano4 一類）平行，同檔會衝突。

## 目標
`scripts/nf_relay.py` 裡寫死的 `ALLOW_HOST_PREFIXES = ("cpn", "gpn", "bgm", "lgn", "localhost")`（台灣杉三號的計算節點主機名稱開頭）改成可由設定 `relay_peer_prefixes` 指定；**沒設時行為與位元組都不變**。對使用者的意義：在別的叢集（例如 nano4，節點叫 `25a-cpn03`）要啟動中繼時，只要在設定檔加一行，不必改 plugin 程式碼。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md`：
- 「**M1-11 `relay-prefix-nano4`**（A／backend，備援）：`scripts/nf_relay.py` 的 `ALLOW_HOST_PREFIXES` 改由設定 `relay_peer_prefixes` 讀入（預設維持 T3 五個）；`platform/tests/test_relay_loopback.py`。」（第 137 行）→ 設定名叫 `relay_peer_prefixes`；預設就是現在這五個；`test_relay_loopback.py` 要有對應測試。
- 「SITE_ADAPTER 六契約表加 nano4 一列（……Egress＝直連無 relay；……）」（第 118 行，已完成）→ 文件必須維持「nano4 主路徑不用中繼」，新增的只是備援說明，不得改寫成 nano4 要用中繼。
- 驗收用語「預設維持 T3 五個」→ 未設定、設成空字串、設成全部無效，三種情況都得到那五個（見裁決 2）。

## 範圍：檔案（只准改這些）
- `scripts/nf_relay.py`（讀環境變數 `NF_RELAY_PEER_PREFIXES`、驗證、`startup_lines()`、`peer_ok()` 用新的元組；`ALLOW_HOST_PREFIXES` 這個名字與型別（tuple）保留）
- `scripts/egress_ctl.sh`（啟動中繼前，把設定 `relay_peer_prefixes` 帶進環境，寫法比照同檔第 24 行的 `NF_RELAY_PORT`）
- `scripts/on_site.sh`（兩處：①經 ssh 到站台時 `carry` 一行；②`REACH=local` 且是 `egress_ctl.sh` 時，與 `NF_RELAY_EXTRA_DOMAINS` 同一處 `export`，讓呼叫者自己的環境變數帶不進去）
- `platform/tests/test_relay_loopback.py`（新增測試；既有測試一個字都不改）
- `tests/egress_ctl_restart_test.sh`、`tests/nf_relay_domains_test.sh`（只許**新增**斷言段落；既有斷言原樣，尤其 TC-019 那條 tuple 比對）
- `docs/SETTINGS.md`（設定表加一列、說明該列出現的位置見作法 7）
- `docs/SITE_ADAPTER.md`（nano4 小節後加一段「備援：萬一 nano4 對外封起來」）
- `specs/relay-prefix-nano4/ledger.md`（新，executor 進度帳本）

**禁止碰**（其他任務正在這些地方動）：`platform/abf_station/*`、`platform/abf_launch/*`、`platform/abf_platform/{actions,pipeline_launch,cli,store,receiver}.py`、`deploy/`、`configs/sites/*`、`docs/OPERATIONS.md`、`docs/INSTALL.md`。也不碰 `hooks/`（見裁決 5）。

## 作法
1. **新環境變數 `NF_RELAY_PEER_PREFIXES`**：逗號分隔的主機名稱開頭。中繼本身**不讀設定檔**（它是站台上的 Python 行程，那裡沒有設定檔）；跟 `NF_RELAY_EXTRA_DOMAINS`、`NF_RELAY_PORT` 一樣，由 shell 層從設定讀出來、放進環境。
2. **解析函式 `_parse_peer_prefixes(raw) -> (prefixes, dropped_reasons)`**（仿同檔 `_parse_extra`）：
   - 逐項去頭尾空白、轉小寫；非 ASCII 的整項丟掉（避免 U+212A 之類被 `lower()` 折成 ASCII，與 `_parse_extra` 同一理由）。
   - 合法＝完整符合 `^[a-z0-9][a-z0-9-]{2,31}$`（3–32 字、只有小寫字母數字與連字號、不含點）。不合法 → 丟掉並記一句原因，原因文字走既有 `_clean()`（單行、可印字元）。
   - **空字串項目直接略過、不報**（`"a,,b"`）；但**空字串絕不能進結果**：`str.startswith("")` 永遠為真，等於對全世界開放中繼。測試要鎖。
   - 去重、保留順序、最多 20 項（超過的丟掉並記原因）。
3. **有效清單**：`ALLOW_HOST_PREFIXES = DEFAULT_HOST_PREFIXES`（就是今天那五個，常數 `DEFAULT_HOST_PREFIXES`）當環境變數未設、為空、或解析後一項都不剩；否則 = 解析出的項目，**末尾補 `"localhost"`**（若沒在裡面）。`localhost` 永遠在：中繼對自己的回送轉發（`forward_loopback`）和測試都靠它，使用者漏寫不該把自己鎖掉。**設定是「取代」不是「追加」**（裁決 1）。
4. **全部無效要大聲說（憲法不變量 13：讀不進來的清單不准默默變成別的行為）**：環境變數有內容但一項都不剩 → 用預設五個，並在啟動訊息印 `peers: relay_peer_prefixes had no usable entry, using the built-in list`。
5. **啟動訊息 `startup_lines()`**：未設時第二行仍是 `  peers  : cpn,gpn,bgm,lgn,localhost*`，與現在逐字相同。有設定時：同一行顯示有效清單，**後面追加**一行 `  peers (this deployment): set by relay_peer_prefixes`，以及每個被丟掉的項目一行 `  peers: dropped 'x' - <原因>`。`peer_ok()` 的邏輯不變，只是 `name.startswith(ALLOW_HOST_PREFIXES)` 用新元組；`_PEER_CACHE` 不動。
6. **shell 層**：
   - `egress_ctl.sh`：在 `nohup python3 …` 之前加 `export NF_RELAY_PEER_PREFIXES="${NF_RELAY_PEER_PREFIXES:-$(setting relay_peer_prefixes)}"`（環境變數優先，與 `NF_RELAY_PORT` 一致；站台上沒有設定檔時 `setting` 回空字串，不會蓋掉 ssh 帶來的值）。`restart` 因為是呼叫自己，環境原樣往下傳。
   - `on_site.sh`：在 `carry NF_RELAY_PORT …` 旁加 `carry NF_RELAY_PEER_PREFIXES "$(setting relay_peer_prefixes)"`；並在 `REACH = local` 且 `NAME = egress_ctl.sh` 的 `export NF_RELAY_EXTRA_DOMAINS=…` 那一處加 `export NF_RELAY_PEER_PREFIXES="$(setting relay_peer_prefixes)"`，理由與該處註解相同（呼叫者環境裡的值不可偷渡）。`carry` 對空值不輸出，所以未設定時 ssh 指令列與今天一字不差。
7. **文件**：
   - `docs/SETTINGS.md`：在 `relay_port` 那一列（約第 161 行）後面加一列 `relay_peer_prefixes`：逗號分隔、每項 3–32 字的小寫字母數字與 `-`；**取代**預設的 `cpn,gpn,bgm,lgn,localhost`，`localhost` 永遠保留；沒設＝台灣杉三號的五個；改了要 `egress_ctl.sh restart` 才生效（與網域清單相同）；無效項目會在中繼啟動訊息裡點名。範例只放 nano4 備援一行（見下）。第 532 行附近「travels」那張表：確認這個鍵落在「會跟著走」那一格（它不是機器專屬鍵），不用改就不要動。
   - 範例（寫進 SETTINGS.md 與 SITE_ADAPTER.md，**標明出處是 2026-10-20 的探測**）：`relay_peer_prefixes: 25a-cpn,25a-hgpn,25a-lgn`（nano4 的 CPU 計算節點 `25a-cpn*`、GPU 節點 `25a-hgpn*`、登入節點 `25a-lgn*`）。文字要寫明：**沒有用更短的 `25a-`**，因為那會放行同一代機房的所有節點。
   - `docs/SITE_ADAPTER.md`：nano4 一列「無中繼」的結論**不改**；新增的段落只說「若將來 nano4 計算節點被封，可這樣讓中繼接受它們」，並說明這條路徑**從未在 nano4 上實測過**（只有名稱來自探測，沒有跑過）。
8. **不改任何 `skills/`、`commands/`**：`tests/command_layer_is_site_neutral.sh` 禁止那裡出現 `nf_relay`、`relay_port` 等字樣；`relay_peer_prefixes` 同理不得出現在那裡。

## 失敗先行測試
**主要放 `platform/tests/test_relay_loopback.py`**（replan 指定）。現在都會紅（`ALLOW_HOST_PREFIXES` 寫死、沒有 `NF_RELAY_PEER_PREFIXES`、`_parse_peer_prefixes` 不存在）。為了能控制「反查出的主機名稱」，測試用 `importlib` 在行程內載入 `scripts/nf_relay.py`（先 `monkeypatch.setenv`、把 `sys.argv` 清成只有程式名，因為它在 import 時讀埠號），再 `monkeypatch` 掉 `relay.socket.gethostbyaddr`，與 `tests/nf_relay_domains_test.sh` 的 `peer()` 輔助函式同一招。每個測試載入一個新模組實例（`_PEER_CACHE` 是模組全域，不可共用）。

預設不變：
- `test_default_peer_prefixes_are_the_five_taiwania_ones_when_nothing_is_set`：環境變數不存在 → `relay.ALLOW_HOST_PREFIXES == ("cpn", "gpn", "bgm", "lgn", "localhost")`，型別是 tuple。
- `test_default_when_the_variable_is_empty_blank_or_all_invalid`：`""`、`"  "`、`","`、`"a,b"`（兩項都太短）、`"*"`、`"."` 各一次 → 都得到那五個；後三者的 `startup_lines()` 含 `had no usable entry`。
- `test_startup_lines_are_byte_identical_to_before_when_unset`：未設時 `startup_lines()` 第二行恰為 `  peers  : cpn,gpn,bgm,lgn,localhost*`，而且**沒有**任何 `peers (this deployment)` 或 `peers: dropped` 行。
- `test_tc075_golden_still_holds`：既有的 `test_tc075_…` 不改、原樣綠（它是真行程、30 個請求、與 `platform/tests/fixtures/relay_golden.json` 比對；這裡只是列為必綠）。

放行與拒絕（用手算得出的主機名稱，見完成標準的表）：
- `test_default_allows_t3_nodes_and_refuses_others`：`cpn3857.nchc.org.tw`、`gpn0101`、`bgm01`、`lgn304`、`localhost` → `peer_ok` 為真；`25a-cpn03`、`laptop.example`、`evilcpn3857.example`、`xcpn1` → 為假。
- `test_setting_replaces_the_list_and_localhost_is_always_kept`：`NF_RELAY_PEER_PREFIXES="25a-cpn,25a-hgpn,25a-lgn"` → `ALLOW_HOST_PREFIXES == ("25a-cpn", "25a-hgpn", "25a-lgn", "localhost")`；`25a-cpn03`、`25a-hgpn170`、`25a-lgn01`、`localhost` → 真；`cpn3857`、`lgn304`（舊預設）、`25a-gpu1`、`25a-` 開頭但不在清單的 `25a-xyz1` → 假。
- `test_prefix_match_is_on_the_reverse_name_start_and_case_is_folded`：設定 `"CPN, GPN"` 與反查名稱 `CPN3001.Example` 都轉小寫後比對 → 真；名稱 `mycpn3001` → 假。
- `test_an_empty_string_never_becomes_a_prefix`：`"cpn,,lgn"`、`",cpn"`、`"cpn,"` → 結果元組裡 `""` 不在其中；`peer_ok` 對 `laptop.example` 為假（防 `startswith("")`）。
- `test_invalid_entries_are_dropped_and_named_at_startup`：`"25a-cpn, a.b, ab, UPPER_CASE, ça-cpn, ok-x"` → 有效 `25a-cpn`、`ok-x`（加 `localhost`）；`startup_lines()` 含 `dropped 'a.b'`、`dropped 'ab'`、`dropped 'UPPER_CASE'`、`dropped 'ça-cpn'`，其中含控制字元的輸入（`"cpn\n"` 內嵌換行、`\x1b[31m`）不會在輸出中造成多一行或未跳脫的控制字元。
- `test_more_than_twenty_entries_are_cut_and_the_cut_is_named`：21 個合法項目 → 取前 20、`startup_lines()` 點名第 21 個。
- `test_an_extra_domain_or_a_domain_variable_does_not_become_a_peer`：同時設 `NF_RELAY_EXTRA_DOMAINS=download.example.org`，該名稱 `peer_ok` 仍為假（鏡射既有 TC-019 的最後一條）。

真行程（沿用檔內 `Relay` 類別，在其建構的 `env` 外另行加變數；`Relay` 目前沒有額外環境參數，**允許加一個選填參數 `extra_env=None`，其餘既有行為不動**）：
- `test_a_real_relay_started_with_a_prefix_setting_logs_it_and_still_refuses_a_stranger`：`NF_RELAY_PEER_PREFIXES="zzz-nomatch"` 啟動；`relay.send(..., source="127.0.0.1")`（反查為 `localhost`，因 `localhost` 永遠在而被放行，回應不是 403）；`source="127.0.0.2"` 仍得 403 且 log 有 `DENY-PEER`；`relay.lines()` 含 `peers  : zzz-nomatch,localhost*` 與 `set by relay_peer_prefixes`。

shell 層（放在既有 `tests/egress_ctl_restart_test.sh` 與 `tests/nf_relay_domains_test.sh`，**只新增**）：
- `egress_ctl_restart_test.sh`：`env.yaml` 寫 `relay_peer_prefixes: 25a-cpn,25a-lgn`、`NF_RELAY_PEER_PREFIXES` 未設 → `start` 後 `relay.log` 含 `peers  : 25a-cpn,25a-lgn,localhost*`；再用環境變數 `NF_RELAY_PEER_PREFIXES=zzz-aaa` 前綴 `restart` → log 改為 `zzz-aaa,localhost*`（環境變數優先）。
- `egress_ctl_restart_test.sh`：設定檔**沒有**該鍵、環境也沒設 → log 第二行為 `peers  : cpn,gpn,bgm,lgn,localhost*`。
- `nf_relay_domains_test.sh`：新增一段 `NF_RELAY_PEER_PREFIXES` 的 `peer` 檢查（與上面行內測試同值），**TC-019 既有六條原樣**。
- 若 repo 有測 `on_site.sh` 帶出哪些環境變數的測試（executor 先 `grep -rn 'NF_RELAY_PORT' tests/` 找），新增一條：設了 `relay_peer_prefixes` 才會出現 `NF_RELAY_PEER_PREFIXES=` 在遠端指令列；沒設時整條指令列與改動前相同。

文件：
- `test_setting_is_documented`（放在 `test_relay_loopback.py`，或既有 `platform/tests/test_launch_docs.py` 的風格）：`docs/SETTINGS.md` 含 `relay_peer_prefixes`、`25a-cpn`、「取代」的同義英文（`replaces`）、`egress_ctl.sh restart`；`docs/SITE_ADAPTER.md` 仍含 nano4 一列的「no relay」字樣，且新段含 `never been run on nano4` 之類的未實測聲明（關鍵語由 executor 與 verifier 在 test-case 定稿時對齊，不在此鎖死整句）。

## 完成標準（done when）
自動：
- 上面所有新測試綠；全套綠（WSL 內 `bash tests/run_all.sh`，見 repo CLAUDE.md「For the executor and verifier」）。
- **必須原樣綠、不准改**：`tests/nf_relay_domains_test.sh` 既有全部（含 TC-019）、`platform/tests/test_relay_loopback.py` 既有全部（含 TC-075 golden）、`tests/egress_ctl_restart_test.sh` 既有全部、`tests/egress_allow_test.sh`、`tests/command_layer_is_site_neutral.sh`、`tests/no_second_run_state_test.sh`、`platform/tests/test_scope.py`、`platform/tests/test_launch_docs.py`、`tests/confirm_launch_test.sh`（hook 不改，但它測 relay 啟動指令的詢問）。
- `git diff --name-only origin/v3...HEAD` 只出現「範圍」列的檔案；`git diff` 對 `platform/abf_*`、`deploy/`、`configs/`、`hooks/`、`docs/OPERATIONS.md`、`docs/INSTALL.md` 為空。
- `nf_relay.py` 沒有新增任何 import 以外的依賴（仍然只用標準函式庫）。

手算對照表（verifier 可自己拿主機名稱代進去算；「預設」＝環境變數不存在；「nano4」＝`NF_RELAY_PEER_PREFIXES=25a-cpn,25a-hgpn,25a-lgn`）：

| 反查出的主機名稱 | 預設 | nano4 設定 | 為什麼 |
|---|---|---|---|
| `cpn3857.nchc.org.tw` | 放行 | 拒絕 | 預設有 `cpn`；nano4 清單只認 `25a-cpn` |
| `lgn304` | 放行 | 拒絕 | 同上，`lgn` 不在 nano4 清單 |
| `localhost` | 放行 | 放行 | `localhost` 永遠保留 |
| `25a-cpn03` | 拒絕 | 放行 | 以 `25a-cpn` 開頭 |
| `25a-hgpn170` | 拒絕 | 放行 | 以 `25a-hgpn` 開頭 |
| `25a-lgn01` | 拒絕 | 放行 | 以 `25a-lgn` 開頭 |
| `25a-xyz1` | 拒絕 | 拒絕 | 不在清單（所以不能用寬的 `25a-`） |
| `CPN3001.Example` | 放行 | 拒絕 | 名稱先轉小寫 |
| `evilcpn3857` | 拒絕 | 拒絕 | 比的是開頭，不是包含 |
| `laptop.example` | 拒絕 | 拒絕 | 不在任何清單 |
| 無反查紀錄 | 拒絕 | 拒絕 | `<no-rdns>`，不變 |

設定值的手算：`""`→預設；`"cpn,,lgn"`→`cpn,lgn,localhost`；`"25a-cpn, a.b"`→`25a-cpn,localhost` 並點名 `a.b`；`"ab"`→無有效項→預設並說 `had no usable entry`；`"localhost,cpn"`→`localhost,cpn`（不重複補）。

手動（維護者，非必要）：在 WSL 或任一台機器上 `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh start`，看 `relay.log` 第一屏的 peers 行；然後 `stop`。**不要**為此連 nano4 或台灣杉（這個任務不碰站台）。

## 環境事實
（行號為 `origin/v3`；先 `git fetch -q origin`，用 `git show origin/v3:<path>` 讀）
- `scripts/nf_relay.py`：`ALLOW_HOST_PREFIXES` 定義在第 212 行；`startup_lines()` 第 230 行起（第 237 行印 `peers`）；`peer_ok()` 第 260 行起（第 271 行 `name.startswith(ALLOW_HOST_PREFIXES)`；沒有反查紀錄就拒絕，不退回用網段判斷）；`_parse_extra`、`_clean`、`EXTRA_LIMIT` 是可仿照的既有寫法（第 98–186 行）；埠號在 import 時從 `sys.argv` 讀（第 214 行），所以測試載入模組前要清 `sys.argv`。
- 中繼的設定怎麼進來：不是自己讀設定檔。`scripts/egress_ctl.sh` 第 24 行 `PORT="${NF_RELAY_PORT:-$(setting relay_port)}"`，第 82 行 `nohup python3 "$HERE/nf_relay.py" "$PORT"` 啟動；網域清單由 `scripts/on_site.sh` 第 477–513 行算出後以 `NF_RELAY_EXTRA_DOMAINS`／`NF_RELAY_EXTRA_NOTE` 帶到站台（local 走 `export`，ssh 走 `carry`）。`setting` 函式在 `scripts/settings.sh` 第 586 行，讀 `key: value` 一行、遇 `#` 即止，未設回空字串。
- 釘住這件事的既有測試：
  - `tests/nf_relay_domains_test.sh` 第 137–138 行：TC-019 比對 `relay.ALLOW_HOST_PREFIXES` 的 repr 必為 `('cpn', 'gpn', 'bgm', 'lgn', 'localhost')`；其後 `peer` 輔助函式（第 125–134 行）用假的 `gethostbyaddr`。
  - `platform/tests/test_relay_loopback.py`：沒有直接引用 `ALLOW_HOST_PREFIXES`；用真行程，`source="127.0.0.1"`（反查為 localhost，放行）與 `"127.0.0.2"`（拒絕，log 有 `DENY-PEER`，第 216–220 行）；TC-075（第 335 行起）把 30 個請求的回應與 `platform/tests/fixtures/relay_golden.json` 比對，其中 3 個是「非計算節點的對端」。`Relay` 類別第 99 行起，環境變數在其 `__init__` 組出。
  - `specs/002-relay-allowlist/{plan,tasks}.md` 與 `specs/007b-launch/research.md` 提到 `ALLOW_HOST_PREFIXES` 是歷史規格文件，**不改**。
- 憲法／結構測試對 `scripts/` 的限制：`tests/no_second_run_state_test.sh` 第二項掃 `scripts/` 的常駐程式字樣（本任務不新增任何 `nohup`／`setsid`／`daemon`）；`tests/command_layer_is_site_neutral.sh` 第 91 行禁止 `skills/` 出現 `nf_relay`、`relay_port` 等（只掃 `skills/`，不掃 `scripts/` 與 `docs/`）；`platform/tests/test_scope.py` TC-070 只管新增的 `.py` 檔頭（本任務不新增 `.py` 檔）；`tests/egress_allow_test.sh` 第 195 行要求指令文件不教人「編輯 nf_relay／ALLOW_DOMAINS」。沒有任何測試禁止修改 `scripts/nf_relay.py` 本身。
- **nano4 節點命名（有找到，出處在維護者工作區，不在 repo）**：`memory/reference/nchc-nano4-probe-2026-10-20.md` 記載登入節點 `25a-lgn01`；生醫 CPU 計算節點 `25a-cpn[01-10,16-18]`（13 台，ngs 系列分區）；GPU 節點 `25a-hgpn[170-177]`（8 台 H200）。同檔也記：ngstest job 587398 在 `25a-cpn03` 上直連 github／quay 皆 200，**所以 nano4 目前不需要中繼**。repo 內的 `docs/TESTING.md` nano4 小節、`docs/SETTINGS.md`、`configs/sites/nchc-nano4*.{json,config}` 都**沒有**節點命名；`docs/SITE_ADAPTER.md` 第 249 行的 `cpn3857` 是台灣杉三號 2026-09-09 的紀錄，不是 nano4。executor 不需要（也不應）連 nano4 驗證這些名稱；文件範例照上面寫並標「2026-10-20 探測所得」。
- 一個和本任務無關但會誤導的字樣：`docs/TESTING.md` 第 177 行「Nothing else was touched (TC-076)」是 007b 發行驗收，要求該次發行不動 `scripts/`；那是舊發行的條件，不適用本任務。
- repo CLAUDE.md「For the executor and verifier」：規則文件 `.specify/memory/constitution.md`；一個測試檔用 `bash tests/<name>.sh`；全套 `tests/run_all.sh` 須在 WSL／Linux 跑（Git Bash 會拒絕），從 ASCII 路徑（如 `$HOME`）呼叫 `wsl.exe`；repo 與 worktree 要在本機磁碟；**不得**改 `spec.md`、`test-case*.md`、憲法、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`；**不得**連站台或 HPC。

## 不做
- 不改中繼的任何其他行為：網域白名單、`DENY-PRIVATE`、回送轉發、DNS 快取、反查失敗即拒絕。
- 不啟動、不測試真的 nano4 或台灣杉三號上的中繼；不改 `configs/sites/*`、不加 nano4 的 CE 設定。
- 不讓 nano4 預設使用中繼；不改 `docs/SITE_ADAPTER.md` 六契約表裡 nano4 「Egress：直連無 relay」的結論。
- 不把前綴比對改成正規表示式或萬用字元；不接受含點的項目（不做網域式的對端判斷）。
- 不改 `hooks/confirm_launch.sh`（見裁決 5）；不改 `skills/`、`commands/`。
- 不新增 `.py` 檔、不新增相依套件。
- 不做 `site_profile` 的程式讀取（那是保留鍵，另有任務）。

## 裁決（2026-10-24，developer-agent 起草；與上文衝突時以本段為準）
1. **設定是「取代」預設，不是「追加」；唯一例外是 `localhost` 永遠保留。** 理由：這個任務的用途是換一個叢集；追加的話，nano4 使用者的中繼仍然放行任何叫 `cpn…`、`lgn…` 的對端，等於把不屬於這個叢集的名稱白白開著。取代的代價是使用者可能漏寫要的前綴——所以啟動訊息把有效清單印出來。**另一選項**：追加（設定只加不減，永遠含五個）。**預設：取代。**
2. **未設／空白／全部無效 ⇒ 用預設五個（行為不變），其中「全部無效」要在啟動訊息大聲說。** 理由：讀不進來的設定不該默默變成更寬或更窄的行為；退回現狀是最保守的，且用 `had no usable entry` 讓人看得見。**預設採此做法。**
3. **每項必須是 3–32 字的 `[a-z0-9-]`，不接受點、萬用字元、空字串，最多 20 項。** 理由：空字串會讓 `startswith` 恆真、太短的項（例如 `c`）會放行幾乎所有主機；現有五項都在 3 字以上；不含點是因為比對的是反查名稱的開頭，不是網域。**預設採此做法。**
4. **設定經環境變數 `NF_RELAY_PEER_PREFIXES` 傳進中繼，由 `egress_ctl.sh`／`on_site.sh` 負責從設定檔讀出，與 `relay_port`、網域清單同一條路。** 理由：中繼跑在站台上，沒有設定檔；多開第二條讀設定的路徑會與既有的「設定留在本機、只帶值過去」原則（`on_site.sh` 的 `carry`）不一致。
5. **不改 `hooks/confirm_launch.sh`，把「直接用環境變數前綴啟動中繼就能放寬誰能連」列為已知、不處理的小缺口。** 理由：該 hook 對 `NF_RELAY_EXTRA_DOMAINS=` 前綴會加警告（第 391–402 行），對對端前綴照理也該有；但這是安全閘門檔，repo CLAUDE.md 的校正失敗紀錄寫過改閘門曾放行三種本該擋的形狀，必須兩個分支各跑一遍測試。本任務不夠格順手動它。**緩解**：`on_site.sh` 在 `REACH=local` 時一律用設定檔的值覆蓋呼叫者的環境變數（作法 6），所以經正規入口啟動時這條偷渡路徑是關的；只有人手直接 `bash scripts/egress_ctl.sh start` 才打得開，而那個人本來就能直接跑 `nf_relay.py`。**另開小任務的選項**：hook 加一條同樣的詢問。**預設：不做，回報給維護者知悉。**
6. **文件範例只寫探測得到的三個前綴 `25a-cpn,25a-hgpn,25a-lgn`，不寫更寬的 `25a-`，且明講「未在 nano4 實測過」。** 理由：名稱來自 2026-10-20 的一次探測（一個登入節點、一個計算節點的實際連線），其餘節點編號是從分區資訊讀來的；nano4 不需要中繼，所以不會有人在上面驗證它。
7. **車道**：本任務與其他改 `docs/SETTINGS.md`／`docs/SITE_ADAPTER.md` 的任務不可平行；與 L1 站台任務不衝突（無共同檔案）。

## 裁決二（2026-10-24 developer-agent）
1. 取代語意（設了就取代預設、`localhost` 永遠保留）接受。
2. `hooks/confirm_launch.sh` 不動；直接啟動時的警告另開小任務。
3. nano4 節點名稱來自 10-20 探測，文件標「探測所得、未在 nano4 實跑」接受。
4. 車道 L-relay；因 `docs/SETTINGS.md`、`docs/SITE_ADAPTER.md` 與 nano4-ce-fixes 重疊，排在它合併之後，開工時以最新 v3 為準。

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
