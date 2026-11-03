# 測試案例：station 的「純 http 只准本機」拒絕訊息與 PLATFORM.md 補上 `::1`

**規格**：`specs/station-loopback-v6-doc/plan.md`（本件為 A 級小修，沒有 spec.md，以計畫為準）　**總覽**：`test-case-overview.md`

白話說明：`abf-station` 連平台時，網址如果是純 `http://`（沒加密），只有「這台機器」才准。程式早就把 `::1`（IPv6 的本機位址，等於 `127.0.0.1` 的 IPv6 版）當本機放行，但被拒絕時的提示和使用說明文件只寫了 `localhost` 和 `127.0.0.1`。這次只把「提示文字」和「文件那一句」改成跟程式一致，**放行／拒絕的判斷一個字都不動**。

維護者原話（出題依據）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」；文件原句「Plain `http://` is only for the same machine.」。

下列「訊息」指 `abf_station.cli.url_problem(url)` 回傳的字串；「放行」指它回傳 `None`；「拒絕」指它回傳非 `None` 的字串。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、被拒絕時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## User Story 1 — 拒絕訊息與文件都提到 `::1`（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-LB-01 | 目標；失敗先行測試 1 | 例外 | 平台網址為 `http://example.com:8788`（純 http、非本機） | 呼叫 `cli.url_problem("http://example.com:8788")` | 回傳的訊息含 `::1`（只斷言含 `"::1"`，不鎖整句） | 自動：`platform/tests/test_station_docs.py` |
| TC-LB-02 | 目標；專長守則（錯誤訊息要說明原因與處理方式） | 例外 | 同 TC-LB-01 | 呼叫 `cli.url_problem("http://example.com:8788")` | 訊息仍含 `Use HTTPS`（告訴使用者怎麼辦），且仍含 `localhost` 與 `127.0.0.1`（沒有因為補 `::1` 而漏掉原本兩個） | 自動：`platform/tests/test_station_docs.py` |
| TC-LB-03 | 裁決 3 | 功能 | 讀入 `docs/PLATFORM.md` 並壓掉換行 | 在壓平後的文字中找 "Plain `http://` is only for the same machine" 這個起點 | 找得到起點；找不到時測試失敗（不是悄悄略過） | 自動：`platform/tests/test_station_docs.py` |
| TC-LB-04 | 目標；失敗先行測試 2 | 功能 | 同 TC-LB-03 | 取起點之後到第一個句點加空白（". "）為止的那一句 | 這一句含 `::1` | 自動：`platform/tests/test_station_docs.py` |
| TC-LB-05 | 範圍：PLATFORM.md 只補不刪 | 功能 | 同 TC-LB-03 | 同 TC-LB-04 取出那一句 | 這一句仍含 `localhost` 與 `127.0.0.1` | 自動：`platform/tests/test_station_docs.py` |

## User Story 2 — 放行／拒絕的判斷完全沒變（優先度 P1）

這一組在改動前就是綠的，**必須一直綠**；它鎖住「程式的判斷一個字都不動」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-LB-06 | 失敗先行測試 3 | 功能 | 無 | `cli.url_problem("http://localhost:1")` | 回傳 `None`（放行） | 自動：`platform/tests/test_station_docs.py` |
| TC-LB-07 | 失敗先行測試 3 | 功能 | 無 | `cli.url_problem("http://127.0.0.1:1")` | 回傳 `None`（放行） | 自動：`platform/tests/test_station_docs.py` |
| TC-LB-08 | 失敗先行測試 3；目標（`http://[::1]:8788` 實際被放行） | 功能 | 無 | `cli.url_problem("http://[::1]:1")` | 回傳 `None`（放行） | 自動：`platform/tests/test_station_docs.py` |
| TC-LB-09 | 失敗先行測試 3；絕不放寬安全網 | 例外 | 無 | `cli.url_problem("http://example.com")` | 回傳非 `None`（拒絕） | 自動：`platform/tests/test_station_docs.py` |
| TC-LB-10 | 失敗先行測試 3；絕不放寬安全網 | 例外 | 無 | `cli.url_problem("http://192.168.1.5:8788")` | 回傳非 `None`（拒絕） | 自動：`platform/tests/test_station_docs.py` |
| TC-LB-11 | 失敗先行測試 3；絕不放寬安全網 | 例外 | 無 | `cli.url_problem("http://[::2]:1")`（另一個 IPv6 位址，不是本機） | 回傳非 `None`（拒絕）——證明只多說明 `::1`，沒有把整個 IPv6 放行 | 自動：`platform/tests/test_station_docs.py` |
| TC-LB-12 | 失敗先行測試 4 | 功能 | 無 | `cli.url_problem("https://example.com")` | 回傳 `None`（https 任何主機都放行） | 自動：`platform/tests/test_station_docs.py` |
| TC-LB-13 | 失敗先行測試 4；不做：不改其他兩個拒絕訊息 | 例外 | 無 | `cli.url_problem("ftp://x")` | 回傳非 `None`，且字串與改前完全相同：`the platform URL ftp://x is not an http or https address` | 自動：`platform/tests/test_station_docs.py` |
| TC-LB-14 | 失敗先行測試 4；不做：不改其他兩個拒絕訊息 | 例外 | 無 | `cli.url_problem("http://")` | 回傳非 `None`，且字串與改前完全相同：`the platform URL http:// is not an http or https address` | 自動：`platform/tests/test_station_docs.py` |

## User Story 3 — 範圍、流程與整體不退步（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-LB-15 | 範圍：檔案（只准改這些） | 不在範圍 | 本分支已完成 | 閱卷者執行 `git diff --stat origin/v3...HEAD` | 變動的檔案只有：`platform/abf_station/cli.py`、`docs/PLATFORM.md`、`platform/tests/test_station_docs.py`，加上本件自己的 `specs/station-loopback-v6-doc/`（計畫與 ledger）；沒有 `agent.py`、`launch.py`、`rules.py`、`records.py`、`handlers.py`、`abf_platform/common.py`、`.github/`、`docs/ROADMAP.md`、`.claude-plugin/plugin.json`、constitution、`spec.md`、`test-case*.md` | 手動：閱卷者讀 `git diff`（計畫決定 5：不新增 `docs/TESTING.md` 步驟，ledger 貼 diff 統計） |
| TC-LB-16 | 範圍：cli.py 只動一個字串；不做：不改判斷、不改 `LOOPBACK` | 不在範圍 | 同 TC-LB-15 | 閱卷者讀 `git diff origin/v3...HEAD -- platform/abf_station/cli.py` | 只有 `url_problem` 那串拒絕訊息的 "only localhost and 127.0.0.1 may use http" 改成含 `::1` 的說法；`LOOPBACK` 元組、`if parts.scheme == "http" and parts.hostname not in LOOPBACK:` 判斷式、其他兩個訊息、其他函式全無差異 | 手動：閱卷者讀 `git diff` |
| TC-LB-17 | 範圍：PLATFORM.md 只動第 176 行 | 不在範圍 | 同 TC-LB-15 | 閱卷者讀 `git diff origin/v3...HEAD -- docs/PLATFORM.md` | 只有第 176 行一行有差異；差異是 "except `localhost` and `127.0.0.1`" 補成含 `::1`；第 649、701 行等其他行無差異 | 手動：閱卷者讀 `git diff` |
| TC-LB-18 | 不做：不動 `public_url`（不准放寬） | 不在範圍 | 同 TC-LB-15 | 閱卷者確認 `platform/abf_platform/common.py` 在 diff 中無任何差異 | `public_url` 仍只放行 `127.0.0.1`、`localhost`，沒有加入 `::1`，沒有任何安全檢查被放寬 | 手動：閱卷者讀 `git diff` |
| TC-LB-19 | 不做：不改 `specs/007-station-agent/plan.md` | 不在範圍 | 同 TC-LB-15 | 閱卷者確認 `specs/007-station-agent/` 在 diff 中無差異 | 該歷史規格檔未被修改 | 手動：閱卷者讀 `git diff` |
| TC-LB-20 | 不做：不需要 migration；專長守則（資料結構變動需 migration 或明寫理由） | 不在範圍 | 同 TC-LB-15 | 閱卷者確認 diff 中沒有任何 migration、資料表、資料結構或資料檔變動 | 沒有；計畫已明寫「不需要 migration」的理由（沒有資料結構或資料內容變動） | 手動：閱卷者讀 `git diff` |
| TC-LB-21 | 範圍：不准動任何既有測試的既有斷言；閱卷規則（不得弱化測試） | 不在範圍 | 同 TC-LB-15 | 閱卷者讀 `git diff origin/v3...HEAD -- platform/tests/` | `test_station_docs.py` 的差異只有新增的行（含新測試與其 import）；既有測試沒有被刪、改、略過或放寬；`test_station_docs.py` 檔頭 `# Nothing existing:` 行未變；其他測試檔無差異 | 手動：閱卷者讀 `git diff` |
| TC-LB-22 | 失敗先行測試（兩分支比對）；專案 CLAUDE.md「Calibration failures」 | 功能 | 在 `origin/v3` 與本分支各有一份可跑的檢出 | 兩邊各執行 `ABF_PYTEST_TARGETS=tests/test_station_docs.py bash tests/platform_test.sh`（於 `platform/`） | 在 `origin/v3` 上：TC-LB-01、TC-LB-04 紅，其餘（含 TC-LB-06 至 TC-LB-14）綠；在本分支上：全部綠；ledger 貼出兩邊輸出，閱卷者看得到「改前紅、改後綠」 | 手動：閱卷者讀 ledger 並自行重跑本分支該檔 |
| TC-LB-23 | 完成標準：整個 `platform/tests` 套件全綠 | 功能 | 本分支 HEAD | 執行 `tests/run_all.sh`（WSL，見專案 CLAUDE.md）；以完成記號 `GREEN <HEAD sha>` 為準 | 完成記號與 HEAD 相符、工作樹乾淨；已知環境紅以 dev-plans README「通例：已知環境紅」為限，不得有新紅 | 自動：`tests/run_all.sh`（閘門記號） |

<!--
撰寫備註（給閱卷者）：
- 自動測試的註解要寫 TC 編號（`# TC-LB-01` 等），方便對照。
- TC-LB-01 與 TC-LB-04 是「失敗先行」：改程式與文件之前必須先確認紅。
- 專長守則（backend）中與本件無關的條目（動作層對等、跨使用者、確認管道、migration 套用）：本件不新增動作、不寫入資料、不涉及使用者紀錄，故無對應 TC；錯誤訊息規則對應 TC-LB-01、TC-LB-02；migration 規則對應 TC-LB-20。
-->
