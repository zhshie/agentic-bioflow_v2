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
