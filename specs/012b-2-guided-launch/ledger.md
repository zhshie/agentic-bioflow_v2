# 引導送出第 4 步：樣本表預覽與欄位角色 progress ledger

狀態：實作完成，等全套測試。

## 做了什麼
- actions.preview_samplesheet（唯讀，沿用 read_confined_samplesheet 的範圍限制，前 5 列，1 MiB 上限）
- web.py launch_preview 與 launch_page 的 guide["preview"]（只在明確選定時）
- web_launch.preview_block、web_board 的 g_pv_* 字串（中英）
- 新測試 platform/tests/test_web_guided_launch_preview.py（18 個）
- docs/TESTING.md 新增手動檢查三項

## 改動的既有斷言（舊 -> 新，原因）
- test_web_guided_launch_2.py：`預覽與欄位角色（尚未開放）` -> `選定樣本表後顯示預覽。`，並新增選定樣本表時出現 樣本表預覽 的檢查。原因：占位句被真正的預覽取代。
- test_web_guided_launch_2b.py：「無管線」清單改為 `["尚未選擇", "分析名稱", "送出（前往確認頁）"]`。原因：舊清單含已不存在的占位句。
- test_web_guided_launch.py：s[4] 檢查 `尚未開放` -> `選定樣本表後顯示預覽。`。原因：同上。
- test_web_parity.py：WEB_ONLY 加 preview_samplesheet。原因：新公開動作須歸類。
- test_owner_guard.py：NO_TOOL 加 preview_samplesheet。原因：同上。

## 沒有加 CSS
沿用既有 class（tbl、muted、bad、csym）；無新 CSS、無 script、無 inline style，CSP 不變。

## 偏離
- TC-308／TC-512 的 zh 原句「樣本表超過 1 MiB，無法預覽。」改為「樣本表大於 1 MiB，無法預覽。」：既有 test_web_wording_sweep 禁用「超」字，且該測試不得改。需要核可者決定是否調整禁用詞表。

## 全套測試後追加的既有斷言改動
- test_k8s_launch.py：動作數 51 -> 52 與名稱雜湊（新增 preview_samplesheet）。
- test_web_settings_ce_mobile.py：web_board.STRINGS 雜湊（新增 g_pv_* 字串）。
- test_aws_ce 一次失敗為偶發，單跑通過。

## 修正回合（verifier 退回）
- TC-108、TC-315：測試改為真的 POST /launch。缺必填欄的樣本表送出後 303 到既有確認頁（新增一筆 pending）。讀取失敗的樣本表中，大於 1 MiB 的是合法 CSV，真的進入確認頁；含 NUL、非 UTF-8、空檔三種被既有送出檢查拒絕（400「未送出：…」），與有無預覽無關，測試斷言拒絕句不含預覽字樣、沒有新增 pending。
- TC-308 用字：未改，仍待維護者裁決。「超過」與既有 test_web_wording_sweep 禁字「超」衝突；執行者不能改 test-case.md 也不能放寬禁字表。二擇一：test-case.md 改成「大於」，或禁字表放行這一句。
- TC-621：diff 多了 test_k8s_launch.py（動作數 51->52 與名稱雜湊）、test_web_settings_ce_mobile.py（web_board.STRINGS 雜湊），是新增動作與字串必然的釘住值更新，計畫「範圍：檔案」沒有點名，需計畫補列或核可。

## 修正回合 R2（11-05）
- 補測試 11 個（29 通過），未改行為。TC-616 與 TC-613 的環境過濾未另寫斷言，原因見 decisions.tsv。TC-701～705 依裁決不做。
