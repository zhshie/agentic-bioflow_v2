# 測試案例總覽：hosted-deploy —— 一間實驗室一台主機的部署包（systemd＋Caddy＋備份）

狀態：合約已確認（2026-10-24，verifier）

**規格**：`specs/hosted-deploy/plan.md`（無 spec.md；裁決 17 接受以計畫為需求來源）　**明細**：`test-case.md`

本版是依「裁決四」（executor BLOCKED 後的裁決）修訂的第二版。原有編號 TC-001～082 不變，新增 TC-083～087 五條；被改到內容的舊條：TC-001、003、005～014（單元檔改稱範本 `.service.in`）、TC-062、067、069、075（檔名）。

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 三個單元範本：自動啟、自動重啟、只聽本機（TC-001～017、083、084） | 14 | 4 | 1 | 19 |
| US2 — Caddy：https 與分流，兩種前端共用一份模板（TC-018～031） | 10 | 2 | 2 | 14 |
| US3 — 備份腳本（TC-032～042、085） | 7 | 5 | 0 | 12 |
| US4 — 文件：OPERATIONS／INSTALL／TESTING（TC-043～065、086） | 24 | 0 | 0 | 24 |
| US5 — 這次不做的事（TC-066～074、087） | 1 | 1 | 8 | 10 |
| 憲法與安全網（TC-075～082） | 2 | 5 | 1 | 8 |
| **合計** | 58 | 17 | 12 | 87 |

自動驗證 81 條、手動驗證 6 條（TC-055、TC-064、TC-065、TC-067、TC-068、TC-070）。

編號說明：
- 計畫「裁決三」提到的 TC-018～TC-021、TC-024、TC-035、TC-043，指的是先前被退回的那份出題；本份合約照裁決三的內容排，使這些編號剛好落在對應內容上：TC-018～021＝四組分流歸屬、TC-024＝模板路徑都能在原始碼找到依據、TC-035＝缺 `web_signing.key` 時備份照樣成功、TC-043＝逐步清單含 Caddy 讀 `ABF_SITE_ADDRESS` 的 `--envfile` 一步。
- 計畫「裁決四」說「`test_station_static.py::test_tc087` 必須維持綠」；那是既有測試自己的編號，在本合約對應 **TC-087**（巧合同號），兩者指同一件事。

## 請你判斷的三件事

1. **每條是不是你要的？** 重點看 TC-018～021（哪些網址送到哪個程序）、TC-035 與 TC-085（web 沒啟動過、或 `uploads/`／`records/` 還不存在時備份照樣成功）、TC-066（程式一個字不改）、TC-083／087（單元檔改成 `.in` 範本、既有安全網測試沒被放寬）。
2. **有沒有漏掉的出錯情況？** 想像實驗室成員會怎麼用錯它：備份漏給目的資料夾（TC-040）、缺資料庫檔（TC-038、039）、把服務綁成對外（TC-007、008）。
3. **「不在範圍」對嗎？** 不寫 Docker Compose、不出貨 `install.sh`／備份排程單元、不做多實驗室、不處理 `abf-station` 單元、不真的部署、不改既有安全網測試（TC-066～072、087）。

## 覆蓋檢查

- 規格（FR）：本任務沒有 spec.md，不適用；改以計畫各節為需求來源。計畫的失敗先行測試共 15 條 TC 名稱（`deploy-files`、`three-services`、`ports-localhost-only`、`ports-match-code`、`caddy-routes`、`caddy-https`、`restart-and-env`、`no-secrets`、`no-real-host`、`env-example-placeholders`、`backup-script`、`backup-script-runs`、`docs-host-section`、`docs-paths-exist`、`no-code-touched`），全部都有對應案例：是（缺：無）。
- 維護者原話共 5 條（H-1 第 186 行、裁決 11 第 48 行、裁決 13 第 52 行、進度回報網址第 44 行、第 215 行），全部都有案例：是。H-1 的每個名詞：`deploy/` 存在＝TC-001；`web`／`mcp`／`serve` 三個單元＝TC-003、004；Caddy 設定＝TC-018～031；備份腳本＝TC-032～042、085；OPERATIONS 有「託管一間實驗室」＝TC-044、045。第 48 行：兩種前端共用一份模板＝TC-027、031、043、046，既有「公開網址」不被弄壞＝TC-058。第 52 行「程式不改、不做跨實驗室」＝TC-066、070。第 44 行「進度回報也從同一網址轉進去」＝TC-018、019、025。第 215 行「文件寫到他照著做、不替他執行」＝TC-046、055、064、072。
- 裁決二、三、四的變更（8、10、13～21）全部有案例：是（8＝TC-024、025、029；10＝TC-055；13＝TC-018～023；14＝TC-043；15＝TC-042；16＝TC-035、039；17＝本檔「規格」欄；18＝TC-001、003、083、086、087、069、067；19＝TC-085；20＝TC-084；21＝TC-066／067 的 diff 檢查，沿用的三個 commit 不另設案例）。
- 計畫「不做」與「不准動」共 8 項（不真的部署；不寫 Compose／Dockerfile；不改 `platform/` 程式；不出貨 install.sh／排程單元；不做多租戶；不做監控／WAF；不處理 `abf-station`；不改 ROADMAP），全部有「不在範圍」案例：是。對應：不真的部署＝TC-072；不寫 Compose／不出貨 install.sh 與排程單元＝TC-069；不改程式與 ROADMAP＝TC-066；不做多租戶與 station＝TC-070；不做監控／WAF＝TC-069（`deploy/` 只有六個檔，沒有此類設定）。另加：不放寬既有安全網＝TC-068、087。
- 計畫「既有測試」逐項釘子（operations_doc、install_doc、docs_nano4_keys、harness_kits、test_gcb_launch、credentials_stay_in_settings）：全部有案例：是（TC-057、058、060、061、081）。
- 專長守則（backend）：適用項（密鑰不入日誌或回應、錯誤訊息白話、migration）已對應 TC-075、078、038～040、085、080；不適用項（動作層對等性、跨使用者讀寫、寫入動作確認）本任務無新增動作，由 TC-066 守住「不碰程式」。

## 計畫內不影響結果的小矛盾（不阻擋，供知悉）

1. 計畫「作法 2」「作法 5」與「失敗先行測試」的 `deploy-files` 仍寫 `abf-*.service`；裁決四 18 已改成 `.service.in`，且裁決自述「以本段為準」。本合約全程照裁決四。
2. 目前 worktree 裡已有三個被追蹤的 `deploy/systemd/abf-*.service`（先前 commit）。TC-083、067、069 要求它們被改名（`git mv`），而不是另複製一份留著；留著會讓既有 `test_station_static.py` 的 tc087 變紅。
3. 計畫作法 4 與 TC `caddy-routes` 的本文（`/.well-known/*` → 8788）已被裁決三 13 蓋過；若維護者其實想要本文那版，TC-021、023 要重寫。
4. 「每個路徑前綴都在原始碼找得到」對 SDK 產生的路由不能逐字成立（`/authorize`、`/token`、`/revoke`、`/.well-known/oauth-protected-resource`）；TC-024 已寫明逐字出現與 SDK 路由產生函式兩類依據都接受。

先前版本的兩個不確定處已由裁決四解決：`uploads/`／`records/` 不存在時只印一行略過（TC-085）；`env.example` 裡的 `http://127.0.0.1:8080` 只能在註解行（TC-084）。

## 核可紀錄

（尚無；本合約由 verifier 確認，維護者未另行核可。）
