# 測試案例總覽：hosted-deploy —— 一間實驗室一台主機的部署包（systemd＋Caddy＋備份）

狀態：合約已確認（2026-10-24，verifier）

**規格**：`specs/hosted-deploy/plan.md`（無 spec.md；裁決 17 接受以計畫為需求來源）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 三個單元檔：自動啟、自動重啟、只聽本機（TC-001～017） | 14 | 2 | 1 | 17 |
| US2 — Caddy：https 與分流，兩種前端共用一份模板（TC-018～031） | 10 | 2 | 2 | 14 |
| US3 — 備份腳本（TC-032～042） | 7 | 4 | 0 | 11 |
| US4 — 文件：OPERATIONS／INSTALL／TESTING（TC-043～065） | 23 | 0 | 0 | 23 |
| US5 — 這次不做的事（TC-066～074） | 1 | 1 | 7 | 9 |
| 憲法與安全網（TC-075～082） | 2 | 5 | 1 | 8 |
| **合計** | 57 | 14 | 11 | 82 |

自動驗證 76 條、手動驗證 6 條（TC-055、TC-064、TC-065、TC-067、TC-068、TC-070）。

編號說明：計畫「裁決三」提到的 TC-018～TC-021、TC-024、TC-035、TC-043，指的是先前被退回的那份出題；那份檔案不在 worktree 裡。本份合約已照裁決三的內容重排，使這些編號剛好落在對應的內容上：TC-018～021＝四組分流歸屬、TC-024＝模板路徑都能在原始碼找到依據、TC-035＝缺 `web_signing.key` 時備份照樣成功、TC-043＝逐步清單含 Caddy 讀 `ABF_SITE_ADDRESS` 的 `--envfile` 一步。

## 請你判斷的三件事

1. **每條是不是你要的？** 重點看 TC-018～021（哪些網址送到哪個程序）、TC-035（web 沒啟動過時備份照樣成功）、TC-066（程式一個字不改）。
2. **有沒有漏掉的出錯情況？** 想像實驗室成員會怎麼用錯它：備份漏給目的資料夾（TC-040）、缺資料庫檔（TC-038、039）、把服務綁成對外（TC-007、008）。
3. **「不在範圍」對嗎？** 不寫 Docker Compose、不出貨 `install.sh`／備份排程單元、不做多實驗室、不處理 `abf-station` 單元、不真的部署（TC-066～072）。

## 覆蓋檢查

- 規格（FR）：本任務沒有 spec.md，不適用；改以計畫各節為需求來源。計畫的失敗先行測試共 15 條 TC 名稱（`deploy-files`、`three-services`、`ports-localhost-only`、`ports-match-code`、`caddy-routes`、`caddy-https`、`restart-and-env`、`no-secrets`、`no-real-host`、`env-example-placeholders`、`backup-script`、`backup-script-runs`、`docs-host-section`、`docs-paths-exist`、`no-code-touched`），全部都有對應案例：是（缺：無）。
- 維護者原話共 5 條（H-1 第 186 行、裁決 11 第 48 行、裁決 13 第 52 行、進度回報網址第 44 行、第 215 行），全部都有案例：是。H-1 的每個名詞：`deploy/` 存在＝TC-001；`web`／`mcp`／`serve` 三個單元＝TC-003、004；Caddy 設定＝TC-018～031；備份腳本＝TC-032～042；OPERATIONS 有「託管一間實驗室」＝TC-044、045。第 48 行：兩種前端共用一份模板＝TC-027、031、043、046，既有「公開網址」不被弄壞＝TC-058。第 52 行「程式不改、不做跨實驗室」＝TC-066、070。第 44 行「進度回報也從同一網址轉進去」＝TC-018、019、025。第 215 行「文件寫到他照著做、不替他執行」＝TC-046、055、064、072。
- 裁決二、裁決三的變更（8、10、13～17）全部有案例：是（8＝TC-024、025、029；10＝TC-055；13＝TC-018～023；14＝TC-043；15＝TC-042；16＝TC-035、039；17＝本檔「規格」欄）。
- 計畫「不做」與「不准動」共 8 項（不真的部署；不寫 Compose／Dockerfile；不改 `platform/` 程式；不出貨 install.sh／排程單元；不做多租戶；不做監控／WAF；不處理 `abf-station`；不改 ROADMAP），全部有「不在範圍」案例：是。對應：不真的部署＝TC-072；不寫 Compose／不出貨 install.sh 與排程單元＝TC-069；不改程式與 ROADMAP＝TC-066；不做多租戶與 station＝TC-070；不做監控／WAF＝TC-069（`deploy/` 只有六個檔，沒有此類設定）。
- 計畫「既有測試」逐項釘子（operations_doc、install_doc、docs_nano4_keys、harness_kits、test_gcb_launch、credentials_stay_in_settings）：全部有案例：是（TC-057、058、060、061、081）。
- 專長守則（backend）：適用項（密鑰不入日誌或回應、錯誤訊息白話、migration）已對應 TC-075、078、038～040、080；不適用項（動作層對等性、跨使用者讀寫、寫入動作確認）本任務無新增動作，由 TC-066 守住「不碰程式」。

## 我（撰寫者）不確定的地方

1. **`uploads/` 或 `records/` 不存在時備份要不要失敗？** 計畫作法 5 把兩者列為必備，裁決三 16 的括號只說 `tokens.db`、`platform.db` 缺了非零結束。剛起好的新平台可能還沒有這兩個資料夾。本合約不對它下斷言（只測 `tokens.db`、`platform.db`、`web_signing.key`），執行者照裁決三 16 的字面自行處理即可；若要寫死，請在計畫補一句。
2. **「每個路徑前綴都在原始碼找得到」對 SDK 產生的路由不能逐字成立**：`/authorize`、`/token`、`/revoke`、`/.well-known/oauth-protected-resource` 在 `platform/abf_platform/*.py` 裡沒有逐字出現，由 `create_auth_routes`／`create_protected_resource_routes` 產生。TC-024 已寫明這兩類依據都接受，不構成阻擋。
3. **`env.example` 的值規則與 Funnel 位址**：計畫 TC `env-example-placeholders` 只准 `<…>`、`https://<your-domain>`、`127.0.0.1…` 或空，而 Funnel 用法的值是 `http://127.0.0.1:8080`。本合約不要求 `env.example` 內出現這個值（只在 OPERATIONS 寫，TC-043、046）；若放在 `env.example`，只能放註解行。
4. 計畫作法 4 與 TC `caddy-routes` 的本文（`/.well-known/*` → 8788）已被裁決三 13 蓋過；本合約全程照裁決三。若維護者其實想要本文那版，請告訴我，TC-021、023 要重寫。

## 核可紀錄

（尚無；本合約由 verifier 確認，維護者未另行核可。）
