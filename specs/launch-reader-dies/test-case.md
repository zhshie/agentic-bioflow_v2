# 測試案例：送出 tw launch 前，當下重驗「輸出讀取 agent（Tower Agent）還活著」（issue #7）

<!--
Written by the verifier (CONTRACT mode). Source of expectations: plan.md (T1-T9 table, 作法, 不做, 完成標準) and the
maintainer's issue #7 text quoted verbatim in the plan. Nothing here is invented beyond the plan; rows marked
"（作法）" come from plan 作法/完成標準 sentences that the plan's T table does not itself test.
-->

**規格**：`specs/launch-reader-dies/plan.md`（本任務沒有獨立的 spec.md，以 plan 為規格；維護者原話在 plan「維護者原話」節＝issue #7 內文）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、站台壞了、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫「不做」或「不准動」的事；測試確認它真的沒做。

驗證方式只有兩種：

- **自動**：`tests/launch_recheck_test.sh`（新）或既有測試檔，由程式判定。
- **手動**：閱卷者（verifier）讀檔、看 `git diff`、或在真的 ssh 部署上照步驟做。`docs/TESTING.md` 在本任務「不准動」清單內，所以手動步驟不新增到那裡，改記進 `specs/launch-reader-dies/ledger.md`（見總覽「不確定的地方」第 1 題）。

名詞：**重驗腳本**＝新增的 `scripts/launch_recheck.sh`；**假 agent／假 egress**＝測試用的替身腳本（旗標檔 `agent.up`／`egress.up` 在就當作活著）；**步驟 8**＝`skills/launch/SKILL.md` 裡 `8. **Launch**` 到 `9. **Watch` 之間那段。

## User Story 1 — 送出前一刻，重驗腳本能抓到「站台上兩個會死的常駐程式」是否倒了（優先度 P1）

維護者原話（issue #7）：「add a fast re-check of agent liveness — the same `agent_ctl.sh status`」；「Checked directly: `scripts/agent_ctl.sh status` → `not running`」；「The agent had died sometime between the earlier `preflight.sh` pass and the actual launch call」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | plan T2；原話「fast re-check of agent liveness」 | 功能 | `reach: local`；假 agent、假 egress 的旗標檔都在（兩個都活著） | 執行 `scripts/launch_recheck.sh` | 結束碼為 0 | 自動：`tests/launch_recheck_test.sh`（T2） |
| TC-002 | plan T2 | 功能 | 同 TC-001 | 執行 `scripts/launch_recheck.sh`，看輸出 | 有一行以 `OK` 開頭、第二欄是 `agent` 的行，有一行以 `OK` 開頭、第二欄是 `egress` 的行；沒有任何以 `FAIL` 開頭的行 | 自動：同上（T2） |
| TC-003 | plan T1；原話「`agent_ctl.sh status` → `not running`」 | 例外 | `reach: local`；`agent.up` 不存在（agent 倒了）、`egress.up` 存在 | 執行 `scripts/launch_recheck.sh` | 結束碼為 1（代表「不要送」） | 自動：同上（T1） |
| TC-004 | plan T1；原話「Restarting it (`scripts/on_site.sh --script scripts/agent_ctl.sh start`)」 | 例外 | 同 TC-003 | 看輸出 | 有一行以 `FAIL` 開頭、第二欄是 `agent` 的行，且該行同時含 `agent_ctl.sh` 與 `start`（使用者知道怎麼救） | 自動：同上（T1） |
| TC-005 | plan T1 | 例外 | 同 TC-003 | 看輸出 | 仍有一行 `OK` 開頭、第二欄是 `egress` 的行（agent 壞了不影響 egress 的回報） | 自動：同上（T1） |
| TC-006 | plan T5 | 例外 | `reach: local`；`egress.up` 不存在（出口通道倒了）、`agent.up` 存在 | 執行 `scripts/launch_recheck.sh` | 結束碼為 1，且有一行 `FAIL` 開頭、第二欄是 `egress` 的行 | 自動：同上（T5） |
| TC-007 | plan T5（「兩個獨立判斷，不是第一個壞就都不報」） | 例外 | 同 TC-006 | 看輸出 | 仍有一行 `OK` 開頭、第二欄是 `agent` 的行 | 自動：同上（T5） |
| TC-008 | plan 作法（`egress_ctl.sh status` 輸出含 `WARNING` 時另印 `FAIL egress-host`，同 `preflight.sh:113`）（作法） | 例外 | `reach: local`；假 egress 活著，但它的 `status` 輸出含 `WARNING` 字樣；agent 活著 | 執行 `scripts/launch_recheck.sh` | 結束碼為 1，且有一行 `FAIL` 開頭、第二欄是 `egress-host` 的行 | 自動：同上（須在 T 表之外新增此案例） |
| TC-009 | plan T6；原話「between the earlier `preflight.sh` pass and the actual launch call」 | 功能 | `reach: local`；兩旗標檔都在；同一份設定 | 第一次執行 `scripts/launch_recheck.sh` | 結束碼為 0 | 自動：同上（T6 第一段） |
| TC-010 | plan T6（重現 issue：兩次呼叫之間 agent 倒了；腳本沒有快取） | 例外 | 接 TC-009：不改任何設定，只刪掉 `agent.up` | 第二次執行 `scripts/launch_recheck.sh` | 結束碼為 1，且有一行 `FAIL` 開頭、第二欄是 `agent` 的行（每次都重新問站台，不沿用上一次的 OK） | 自動：同上（T6 第二段） |
| TC-011 | plan T3 | 例外 | `reach: ssh`、`site_host: me@example.org`；假 ssh 一律 `exit 255`（主連線斷了） | 執行 `scripts/launch_recheck.sh` | 結束碼為 1；有一行 `FAIL` 開頭、第二欄是 `reach` 的行，且輸出含 `me@example.org` | 自動：同上（T3） |
| TC-012 | plan T3（「不往下問」，否則會卡在 Claude 答不了的一次性密碼提示） | 例外 | 同 TC-011 | 看輸出 | 沒有任何以 `OK`／`FAIL`／`SKIP` 開頭、第二欄是 `agent` 或 `egress` 的行 | 自動：同上（T3） |
| TC-013 | plan 作法（「把 `on_site.sh` 的輸出（含使用者要貼的那行）原樣印出」）（作法） | 例外 | 同 TC-011 | 看輸出 | 輸出含 `on_site.sh --check-reach` 失敗時印出的、使用者要貼的那行（與 `tests/preflight_reach_test.sh` 同樣可用 `ControlMaster=auto` 認出） | 自動：同上（須在 T 表之外新增此案例） |
| TC-014 | plan T4 | 功能 | `reach: none`（Platform 自管的雲端環境，沒有 agent 可言） | 執行 `scripts/launch_recheck.sh` | 結束碼為 0，且有一行 `OK` 開頭、第二欄是 `reach`、內容含 `none` 的行 | 自動：同上（T4） |
| TC-015 | plan T4 | 功能 | 同 TC-014 | 看輸出 | 沒有任何第二欄是 `agent` 或 `egress` 的行（不把健康的雲端站台報成壞的） | 自動：同上（T4） |
| TC-016 | plan T9；plan 作法「不查 token」「不呼叫 tw」 | 不在範圍 | 案例 T1–T6 的整個過程；`TW_BIN` 指向一支被呼叫就 `exit 99` 並記錄的假 `tw` | 跑完 T1–T6 後檢查記錄檔 `tw.called` | 記錄檔不存在（重驗腳本從不呼叫 `tw`、不查計算環境狀態） | 自動：同上（T9） |
| TC-017 | plan 作法（只呼叫 `status`）、不做「不自動重啟 agent」 | 不在範圍 | 假 agent 會把每次被呼叫的參數記下來；跑 TC-003 與 TC-010 的情境（agent 倒了） | 檢查記錄 | 假 agent 只被以 `status` 呼叫過，從沒被以 `start`、`stop`、`register` 呼叫（腳本只讀，不自動把 agent 拉起來） | 自動：同上（須在 T 表之外新增此案例） |
| TC-018 | plan 不做「不查 agent 活著但 Platform 看不到它」 | 不在範圍 | 同 TC-017 | 檢查記錄 | 假 agent 從沒被以 `online` 呼叫過 | 自動：同上（須新增） |
| TC-019 | plan 作法（「不查資源契約、`rsync`、計算環境狀態、token」） | 不在範圍 | 測試用的 `scripts/` 副本裡，`check_resource_contract.sh` 換成會記錄被呼叫的替身；跑 TC-001 與 TC-003 的情境 | 檢查記錄 | 替身從沒被呼叫（重驗腳本只問 egress 與 agent 兩項，不做步驟 0 那些慢檢查） | 自動：同上（須新增） |
| TC-020 | plan 作法（「腳本本身不加 `sleep`、不重試」） | 不在範圍 | 新腳本檔案 | 在 `scripts/launch_recheck.sh` 裡找 `sleep`、重試迴圈（`while`／`until`／`for … retry`） | 一個也找不到 | 自動：同上（須新增靜態檢查） |
| TC-021 | plan 完成標準「手動驗收」；作法（ssh 時修復指令帶 `scripts/on_site.sh --script` 前綴） | 例外 | 真的 ssh 部署（例如國網）；先 `scripts/agent_ctl.sh stop` | 執行 `scripts/launch_recheck.sh` | 結束碼為 1，印出 `FAIL agent`，並印出完整重啟指令 `scripts/on_site.sh --script scripts/agent_ctl.sh start` | 手動：記進 `specs/launch-reader-dies/ledger.md`（不擋合併） |
| TC-022 | plan 完成標準「手動驗收」 | 功能 | 接 TC-021：`start` 後 | 再執行 `scripts/launch_recheck.sh` | 結束碼為 0 | 手動：記進 `specs/launch-reader-dies/ledger.md`（不擋合併） |

## User Story 2 — 技能「步驟 8」在送出前先重驗，失敗就停手（優先度 P1）

維護者原話：「In `launch.md` step 7 (right before showing/running the actual `tw launch` command), add a fast re-check」；「rather than relying solely on the earlier `preflight.sh` pass」；「Restarting it … and re-running `tw launch` fixed it immediately」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | plan T7；原話「right before … the actual `tw launch`」 | 功能 | `skills/launch/SKILL.md`；取 `8. **Launch**` 到 `9. **Watch` 之間 | 在這一段找 `scripts/launch_recheck.sh` | 找得到 | 自動：`tests/launch_recheck_test.sh`（T7） |
| TC-024 | plan T7；原話「Restarting it (`scripts/on_site.sh --script scripts/agent_ctl.sh start`)」 | 功能 | 同 TC-023 | 在這一段找 `agent_ctl.sh start` | 找得到（技能文字給出復原路徑） | 自動：同上（T7） |
| TC-025 | plan T7 | 功能 | 同 TC-023 | 在這一段找 `FAIL` | 找得到（技能文字說明遇到 FAIL 怎麼辦） | 自動：同上（T7） |
| TC-026 | plan T7（順序）；原話「right before … `tw launch`」 | 功能 | 同 TC-023 | 比較 `launch_recheck.sh` 第一次出現的位置與該段第一個 `tw launch` 字樣的位置（若該段沒有 `tw launch` 字樣，改比「report the run ID」） | `launch_recheck.sh` 在前 | 自動：同上（T7） |
| TC-027 | plan 作法 2（「任一 `FAIL`：**不要送**」） | 例外 | 步驟 8 的文字 | 閱卷者讀步驟 8 | 明寫：重驗有任何一行 `FAIL` 時不得送出 `tw launch` | 手動：閱卷者讀 `skills/launch/SKILL.md` 步驟 8 |
| TC-028 | plan 作法 2（「把那行原文給使用者看，說明這是步驟 0 之後才倒的，列出修復指令」） | 例外 | 同 TC-027 | 閱卷者讀步驟 8 | 明寫：把 `FAIL` 那行原文給使用者看、說明是步驟 0 之後才倒的、列出修復指令 | 手動：同上 |
| TC-029 | plan 作法 2、裁決（放在使用者說「確認執行」之後、送出之前；與 `tw launch` 同一個 Bash 回合） | 功能 | 同 TC-027 | 閱卷者讀步驟 8 | 明寫：使用者說「確認執行」之後、呼叫 `tw launch` 的同一個 Bash 回合之前，先跑 `. scripts/env.sh && scripts/launch_recheck.sh`（不是在步驟 7 就跑完了事） | 手動：同上 |
| TC-030 | plan 作法 2、裁決「重驗後沿用原確認」；原話「re-running `tw launch` fixed it immediately」 | 功能 | 同 TC-027 | 閱卷者讀步驟 8 | 明寫：修好後重跑本檢查，全 OK 才送出**同一條**已確認的指令，指令沒變就不必重新確認 | 手動：同上 |
| TC-031 | plan 作法 3 | 功能 | 步驟 7 的文字（`7. **Show the complete command**` 到 `8. **Launch**` 之間） | 閱卷者讀步驟 7 末尾 | 有一句預告：送出前會再驗一次站台（步驟 8），因為從步驟 0 到現在可能隔了很久，並提到 `launch_recheck.sh` | 手動：閱卷者讀步驟 7（TC-033 的出現次數檢查是旁證） |
| TC-032 | plan T8；原話「rather than relying solely on the earlier `preflight.sh` pass」 | 功能 | `skills/launch/SKILL.md` 前 70 行，找到舊句子 `re-checks the two things that can die while you work` | 取這句之後的 400 個字元 | 其中出現 `reach`（不再單獨宣稱閘門已涵蓋，而是講明它只在特定 reach 生效） | 自動：同上（T8） |
| TC-033 | plan T8 | 功能 | 整份 `skills/launch/SKILL.md` | 數 `launch_recheck.sh` 出現幾次 | 至少 2 次（步驟 7 預告＋步驟 8） | 自動：同上（T8） |
| TC-034 | plan 作法 4（「其餘原句（步驟 0 較寬、也查資源契約與計算環境）保留」；閘門只在 `reach=local` 或有設 `LAB_RUNS_DIR` 的 shell 生效，`ssh`／`none` 刻意靜默；送出前重驗是步驟 8 的 `launch_recheck.sh`，不是閘門） | 功能 | 技能第 60 行起那一段 | 閱卷者讀該段 | 內容是事實：閘門重驗只在 `reach=local` 或有設 `LAB_RUNS_DIR` 時生效、`ssh`／`none` 刻意靜默；點名送出前重驗是步驟 8 的 `launch_recheck.sh`；保留「步驟 0 較寬、也查資源契約與計算環境」那句 | 手動：閱卷者讀 `skills/launch/SKILL.md` 第 60 行附近 |
| TC-035 | plan 不做「不自動重啟 agent、不自動重送」；作法 2（`--set agent_connection` 不得自行改） | 不在範圍 | 步驟 8 的文字 | 閱卷者讀步驟 8 | 沒有叫模型自己重啟 agent 或自己重送；明寫重啟要使用者同意、不得自行以 `--set agent_connection` 之類改身分 | 手動：同 TC-027 |
| TC-036 | plan 不做「不查 agent 活著但 Platform 看不到它」 | 不在範圍 | 步驟 8 的文字 | 閱卷者讀步驟 8 | 沒有要求跑 `agent_ctl.sh online <run-id>` 之類需要 run id 的檢查 | 手動：同上 |
| TC-037 | plan 裁決二 3（不涵蓋 relaunch）；不做第 3 待裁決 | 不在範圍 | `skills/runs/SKILL.md`、`scripts/relaunch_with_override.sh` | `git diff origin/v3...HEAD --stat` 看這兩個檔 | 沒有任何改動 | 手動：閱卷者看 diff |

## User Story 3 — 留下紀錄，且只動計畫准許的地方（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-038 | plan 作法 5、裁決二 4（只在檔尾新增一條，編號＝當下最後編號＋1） | 功能 | `docs/PITFALLS.md`（base 最後一條是 55） | `git diff origin/v3...HEAD -- docs/PITFALLS.md` | 只在檔尾新增一條、編號為 56；檔案其他位置零改動 | 手動：閱卷者看 diff |
| TC-039 | plan 作法 5（標題含 2026-10-24、issue #7；症狀、原因、修法） | 功能 | 同 TC-038 的新條目 | 閱卷者讀新條目 | 標題含 `2026-10-24` 與 `#7`；寫了症狀（送出才撞 `No Tower Agent is online`）、原因（preflight 只在最前面驗一次）、修法（步驟 8 的 `launch_recheck.sh`） | 手動：同上 |
| TC-040 | plan 作法 5（為什麼閘門在 ssh 部署看不到） | 功能 | 同 TC-038 的新條目 | 閱卷者讀新條目 | 寫明：閘門在 `reach` 為 `ssh` 或 `none` 時刻意不查（hook 有 10 秒上限），所以閘門在 ssh 部署整段靜默 | 手動：同上 |
| TC-041 | plan 不做「不調查 agent 為什麼會死」；作法 5 | 不在範圍 | 同 TC-038 的新條目 | 閱卷者讀新條目 | 明寫「agent 為什麼會死」尚未查明；沒有編造原因，也沒有加看門狗或自動拉起 | 手動：同上 |
| TC-042 | plan 完成標準、不做（不改 `hooks/`） | 不在範圍 | 分支 | `git diff --stat origin/v3 -- hooks` | 輸出為空 | 手動：閱卷者執行 |
| TC-043 | plan 完成標準（`tests/confirm_launch_test.sh` 在 base 與分支輸出相同） | 不在範圍 | base 與分支各一份 | 兩邊各跑一次 `bash tests/confirm_launch_test.sh` | 兩邊輸出相同 | 自動：`tests/confirm_launch_test.sh`（閱卷者兩邊各跑並比較） |
| TC-044 | plan 完成標準（`git diff --name-only` 只含「範圍：檔案」） | 不在範圍 | 分支 | `git diff --name-only origin/v3...HEAD` | 只含：`scripts/launch_recheck.sh`、`skills/launch/SKILL.md`、`tests/launch_recheck_test.sh`、`docs/PITFALLS.md`、`specs/launch-reader-dies/` 下的檔 | 手動：閱卷者看 diff |
| TC-045 | plan「不准動」清單與完成標準（`agent_ctl.sh`、`preflight.sh`、`prepare_launch.sh` 零改動） | 不在範圍 | 分支 | `git diff --stat origin/v3...HEAD` 看 `platform/**`、`deploy/`、`configs/sites/*`、`scripts/nf_relay.py`、`scripts/egress_ctl.sh`、`scripts/on_site.sh`、`scripts/build_package.sh`、`scripts/agent_ctl.sh`、`scripts/preflight.sh`、`scripts/prepare_launch.sh`、`docs/OPERATIONS.md`、`docs/INSTALL.md`、`docs/SETTINGS.md`、`docs/SITE_ADAPTER.md`、`docs/TESTING.md` | 以上全部零改動 | 手動：閱卷者看 diff |
| TC-046 | plan 不做「不新增設定鍵」 | 不在範圍 | 分支 | 看 diff 有沒有新增設定鍵（`scripts/settings.sh`、`docs/SETTINGS.md`、新腳本內 `setting <新鍵>`） | 沒有；新腳本只用既有的 `reach`、`site_host`、`storage_root` 等已存在的鍵 | 手動：閱卷者看 diff |
| TC-047 | plan 不做「不同步到 main」 | 不在範圍 | 分支 | `git diff origin/v3...HEAD --stat` 看 `commands/launch.md` | 沒有改動 | 手動：閱卷者看 diff |
| TC-048 | plan 完成標準（`plugin.json`、`spec.md`、`test-case*.md`、`.github/`、憲法未被編輯）與裁決二 2（ADR 0006 本任務不動） | 不在範圍 | 分支 | `git diff --stat origin/v3...HEAD` 看 `.claude-plugin/plugin.json`、任何 `spec.md`、`test-case*.md`、`.github/`、`.specify/memory/constitution.md`、`docs/adr/0006-four-entries-one-action-layer.md`、`docs/ROADMAP.md` | 全部零改動 | 手動：閱卷者看 diff |
| TC-049 | plan「會改斷言的既有測試：無」 | 不在範圍 | 分支 | `git diff origin/v3...HEAD --stat -- tests/` | 只新增 `tests/launch_recheck_test.sh`；既有測試檔零改動（沒有放寬任何斷言） | 手動：閱卷者看 diff |
| TC-050 | plan 完成標準（新測試 T1–T9 綠；`prepare_launch_test.sh`、`prepare_launch_ce_test.sh`、`launch_provenance_test.sh`、`credentials_stay_in_settings_test.sh`、`no_second_run_state_test.sh` 與整個 `tests/run_all.sh` 綠） | 功能 | 分支，在 WSL 跑（原生 Git Bash 不行） | 跑 `tests/run_all.sh` | 全綠，其中包含新測試與上列五支既有測試 | 自動：`tests/run_all.sh` |
| TC-051 | plan 完成標準（沒有任何真的 `tw`／Seqera／ssh 呼叫；新測試沒有網路也綠） | 功能 | `tests/launch_recheck_test.sh` | 閱卷者讀測試檔 | 只使用假 ssh（`ON_SITE_SSH_BIN`）與假 `tw`（`TW_BIN`）、`LAB_SETTINGS_FILE` 暫存設定；沒有任何指向真站台或 Seqera 的呼叫 | 手動：閱卷者讀測試檔 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-052 | 不變條款 2（不得有第二份執行狀態、不得有常駐程式、腳本不得 `tw launch`）——重驗腳本每次重問、不快取，不新增狀態檔或 `nohup` | 功能 | 新腳本 `scripts/launch_recheck.sh` 已加入 | 跑 `bash tests/no_second_run_state_test.sh` | 通過（新腳本無 `nohup`、無 `tw launch`、不建立狀態檔） | 自動：`tests/no_second_run_state_test.sh` |
| TC-053 | 安全網第四條（憑證只在設定區、不被印出）——重驗腳本不讀 token 檔 | 功能 | 同 TC-052 | 跑 `bash tests/credentials_stay_in_settings_test.sh`（它掃描 `scripts/*.sh`） | 通過（新腳本沒有讀或印 token） | 自動：`tests/credentials_stay_in_settings_test.sh` |
