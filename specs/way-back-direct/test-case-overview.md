# 測試案例總覽：進度回報改走公開網址（way_back: direct）

狀態：合約已確認（2026-10-22，verifier）

**規格**：`specs/way-back-direct/plan.md`（本任務沒有獨立 spec.md，plan.md 即規格，內含維護者裁示 8、13 原話）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — reach 為 ssh 時用 `way_back: direct`，進度直接打公開網址 | 7 | 0 | 0 | 7 |
| US2 — `direct` 但網址不安全時拒絕 launch | 0 | 5 | 0 | 5 |
| US3 — 沒設定時一切照舊，T3 不變 | 6 | 1 | 0 | 7 |
| US4 — 代理回報這兩個設定，平台只收合法值 | 3 | 2 | 0 | 5 |
| 不在範圍 | 0 | 0 | 6 | 6 |
| 憲法與安全網（含 backend 專長守則） | 3 | 2 | 0 | 5 |
| **合計** | 19 | 10 | 6 | 35 |

自動驗證 31 條、手動驗證 0 條；另有 4 條（TC-026、TC-027、TC-029、TC-030）是「沒有改某些東西」，只能由閱卷者看 `git diff <base>...HEAD` 核對（TC-025、TC-027 另含可執行的比對部分）。

## 請你判斷的三件事

1. **每條是不是你要的？** 重點看 TC-001、TC-008、TC-013：設了 `direct` 就改打公開網址；網址是明文 http 就拒絕；沒設就照舊。
2. **有沒有漏掉的出錯情況？** 見下方「不確定的地方」——計畫沒講的情況我沒有替它編預期結果。
3. **「不在範圍」對嗎？** 不改 head 腳本、不改 relay、不改 preflight、不處理 Tailscale 網路、reach 仍是 ssh。

## 覆蓋檢查

- 計畫「作法」共 4 點、「完成標準」1 條、「失敗先行測試」3 條：全部都有測試案例：是（作法 1→TC-013/014/021；作法 2→TC-020/022/023/024；作法 3→TC-001～007、015；作法 4→TC-008～012；完成標準→TC-001/002/013；失敗先行→TC-001/002/003/008/019）
- 維護者原話 2 句（裁示 8、裁示 13）全部有對應 TC：是（裁示 8→TC-001、020；裁示 13→TC-007、028）
- 計畫「不做」共 3 條＋「環境事實」的網路不在本任務＋「範圍：檔案」限制，全部都有「不在範圍」測試案例：是（TC-025～030）
- backend 專長守則：確認管道→TC-031、032；錯誤訊息與日誌（密鑰）→TC-009、033；migration→TC-018（不需要，理由是 facts 存成 JSON）；對等性與跨使用者→不適用（本任務沒有新增使用者可見動作，也沒有新增讀寫他人紀錄的路徑）。

## 我（撰寫者）不確定的地方

這些計畫沒講清楚，我沒有替它們編預期結果；若答案改變要檢查的事，請回頭補 TC：

1. `clean_facts` 說「值只允許字面值與 https URL」，但 `_tower` 又允許 loopback 的 `http://127.0.0.1`／`localhost`。若 `clean_facts` 把所有 http 網址都丟掉，那麼經由「設定檔 → hello → 平台 → bundle」這條真實路徑，loopback 例外就用不上，非 loopback http 也會變成「沒有網址」而不是 TC-009 的那句訊息。請問：`clean_facts` 對 loopback http 是保留還是丟掉？（TC-005、006、008 都在「直接把 facts 交給組 bundle」這一層驗證，不依賴這個答案。）
2. `way_back: direct` 但 `platform_public_url` 沒寫、是空的、或不是 http(s)（例如 ftp）時，要拒絕還是退回 forward？計畫沒說。我的建議是拒絕並說明要補網址，但不是我能替你決定的。
3. reach 為 local 又設了 `way_back: direct` 或 `forward` 時怎麼辦？以及 reach 為 local 時 hello 回報的 `way_back` 值是什麼（`"forward"` 還是空）？計畫只定義了 ssh 的預設。TC-016 只確認 local 的 bundle 行為不變。
4. 續跑（resume）會用 `own_facts` 重組 bundle 比對原件。計畫只講 launch；`direct` 的續跑是否要一樣不呼叫 `--check-forward`？（`_prechecks` 目前對 launch 與 resume 共用，依 `tower.mode` 判斷，應該自然成立，但計畫沒列。）
5. 計畫「範圍：檔案」只列 `test_station_channel.py` 一個測試檔，但 `clean_facts` 的測試既有案例在 `test_launch_platform.py`、組 bundle 的拒絕案例在 `test_launch_bundle.py`。TC 的測試檔位置我標「或」；若執行者需要動這兩個檔案，請確認算不算超出範圍。

## 核可紀錄

（尚無。本合約由 verifier 確認，維護者未另行核可。）
