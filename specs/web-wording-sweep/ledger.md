# 網頁中文全面改正式書面語＋禁用詞測試擴到每頁 progress ledger

- [x] 新測試 `platform/tests/test_web_wording_sweep.py`（RED 提交 caf0b5a）：共用禁用詞表、七張中文字串表、web.py 內嵌句、每頁每狀態
- [x] 替換七張表與 web.py 內嵌句、`confirm.py:390`（只動中文字面值，不增刪鍵、不動路由、不動英文）
- [x] 更新現有測試的期望字串（見下表）
- [x] DESIGN.md「用字」段尾、禁用詞表、Open 一行

## RED 輸出（TC-082 `test_banned_words_cover_every_zh_string_table`，改動前）

```
AssertionError: 28 values are spoken Chinese: [('web_board.STRINGS', 'mine', ['run'], '我的 run'),
 ('web_board.STRINGS', 'none_yet', ['還沒有', '還沒', 'run'], '還沒有 run。'), ('web_board.STRINGS', 'no_analyses', ['還沒有', '還沒'], '還沒有分析'),
 ('web_board.STRINGS', 'this_analysis', ['這個'], '這個分析的對話'), ('web_board.STRINGS', 'ask_here', ['這個'], '問這個分析'),
 ('web_board.STRINGS', 'c_content_text', ['這個', '被動', 'run'], '這個 run 已成功；它的中間檔（work）可以清掉，結果不會被動。'), ...]
assert [...] == []   Left contains 28 more items, first extra item: ('web_board.STRINGS', 'mine', ['run'], '我的 run')
整檔：15 failed, 3 passed（通過的三個：守衛抓得到每個新詞、2b 仍用共用表、英文頁無 CJK）
```

測試案例寫「約 40 句」；實際掃出的表值是 28 句（七張表合計，含 `web_settings`、`web_cost`、`web_finished`），另有 `web.py` 內嵌句與表外項（見下）。

## 現有斷言改動（Existing assertions that changed）

只改期望的字串或摘要；沒有刪除、跳過或放寬任何斷言。行號為改後行號。

| 檔:行 | 改前 | 改後 | 依據 |
|---|---|---|---|
| test_clean_page.py:90 | assert "下面就是會被刪除的全部內容。確定了再按「確認刪除」；按了才會排進佇列。" in t | assert "以下為將被刪除的全部內容。確認無誤後，請按「確認刪除」；按下後才會排入佇列。" in t | 計畫替換表（期望字串隨表值） |
| test_clean_page.py:105 | assert re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", block) == [("種類", "清理中間檔"), ("run 名稱", "run-one"), ("要刪除的資料夾", WORK)] | assert re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", block) == [("種類", "清理中間檔"), ("分析名稱", "run-one"), ("要刪除的資料夾", WORK)] | 計畫替換表（期望字串隨表值） |
| test_clean_page.py:119 | assert "清理確認" in page.text and "這個申請已作廢：X-reason。" in page.text | assert "清理確認" in page.text and "該申請已作廢：X-reason。" in page.text | 計畫替換表（期望字串隨表值） |
| test_clean_page.py:125 | assert "清理確認" in t and "這個申請已逾時（7 天），不會自動重新提出。" in t | assert "清理確認" in t and "該申請已逾時（7 天），不會自動重新提出。" in t | 計畫替換表（期望字串隨表值） |
| test_clean_page.py:157 | BASE_CONFIRM = {'pending-launch-zh': (200, '31e3c878f10406bb'), 'pending-cancel-zh': (200, 'ccfbd045712deb75'), / 'pending-launch-en': (200, 'f85ab8a479514dc6'), 'pending… | BASE_CONFIRM = {'pending-launch-zh': (200, '0050cf7ac01bd5a1'), 'pending-cancel-zh': (200, 'ab844654d972f4fc'), 'pending-launch-en': (200, '95b11bfdaeb263a7'), 'pending-c… | 整頁 SHA 摘要：頁面中文改了，摘要依實際頁面重算；英文板面摘要（succeeded-en／failed-en／running-en）未變 |
| test_clean_page.py:161 | BASE_BOARD = {'succeeded-zh': (200, 'b900748476502f3d'), 'succeeded-en': (200, '870addd406492402'), / 'failed-zh': (200, 'f5866fcf5bb0a339'), 'failed-en': (200, '918ba6c8… | BASE_BOARD = {'succeeded-zh': (200, 'd71583f9e5e70797'), 'succeeded-en': (200, '870addd406492402'), 'failed-zh': (200, '756d18e5eb9d525b'), 'failed-en': (200, '918ba6c8db… | 整頁 SHA 摘要：頁面中文改了，摘要依實際頁面重算；英文板面摘要（succeeded-en／failed-en／running-en）未變 |
| test_clean_page.py:252 | assert "已送出。工作編號 %s。代理會開始清理這個 run 的中間檔；結果不會被動。" % jobs[0]["id"] in r.text | assert "已送出。工作編號 %s。代理將清理該次分析的中間檔，結果不受影響。" % jobs[0]["id"] in r.text | 計畫替換表（期望字串隨表值） |
| test_clean_page.py:339 | assert "這個 run 已成功；它的中間檔（work）可以清掉，結果不會被動。" in n[0] / assert "打開確認頁，看清楚要刪的資料夾再決定。" in n[0] and 'class="when"' not in n[0] | assert "該次分析已成功；其中間檔（work）可清理，結果不受影響。" in n[0] / assert "請開啟確認頁，核對將刪除的資料夾後再決定。" in n[0] and 'class="when"' not in n[0] | 計畫替換表（期望字串隨表值） |
| test_cleanup_confirm.py:281 | with pytest.raises(jobs.JobRefused, match="還有工作在排隊"): | with pytest.raises(jobs.JobRefused, match="仍有工作在排隊"): | 裁決 2、12：confirm.py:390 |
| test_confirm_page.py:87 | assert "不是你的申請" in page.text and 'name="csrf"' not in page.text | assert "非您的申請" in page.text and 'name="csrf"' not in page.text | 裁決 11：期望字串 |
| test_oauth_consent.py:101 | assert "claude.example" in page and "不能替你送出" in page and "送出" in page | assert "claude.example" in page and "不能代您送出" in page and "送出" in page | 裁決 11：期望字串 |
| test_oauth_mcp.py:290 | assert r.status_code == 403 and "不是你的申請" in r.text | assert r.status_code == 403 and "非您的申請" in r.text | 裁決 11：期望字串 |
| test_oauth_review.py:100 | assert "表單" in listed and "不能替你送出" not in listed / assert "表單" not in other and "網站" in other and "確認" in other and "不能替你送出" in other | assert "表單" in listed and "不能代您送出" not in listed / assert "表單" not in other and "網站" in other and "確認" in other and "不能代您送出" in other | 計畫清單與裁決 11 之外（見範圍外）；僅期望字串，依所改表值 |
| test_web_actions.py:430 | assert "目前沒有通知" in t and ("要你" + "處理") not in t | assert "目前無通知" in t and ("要你" + "處理") not in t | 計畫替換表（期望字串隨表值） |
| test_web_board.py:296 | assert left.index("＋ 新分析") < left.index("我的 run") < left.index("go") < left.index("設定") < left.index("登出") | assert left.index("＋ 新分析") < left.index("我的分析") < left.index("go") < left.index("設定") < left.index("登出") | 計畫替換表（期望字串隨表值） |
| test_web_board.py:352 | assert "這個分析的對話 r 目前沒有通知 問這個分析 之後開放" in plain(right) / assert re.search(r'<span class="off">問這個分析 <span class="later">之後開放</span></span>', right) | assert "本分析的對話 r 目前無通知 詢問本分析 之後開放" in plain(right) / assert re.search(r'<span class="off">詢問本分析 <span class="later">之後開放</span></span>', right) | 計畫替換表（期望字串隨表值） |
| test_web_board.py:438 | for key, text in (("a-run", "a-run 執行中 執行 · 8 / 10"), ("b-fail", "b-fail 失敗 執行 · —"), ("c-lost", "c-lost 失敗 執行 · 站台沒有回應"), | for key, text in (("a-run", "a-run 執行中 執行 · 8 / 10"), ("b-fail", "b-fail 失敗 執行 · —"), ("c-lost", "c-lost 失敗 執行 · 站台無回應"), | 計畫替換表（期望字串隨表值） |
| test_web_board.py:547 | for stage, feature in (("launch", "012b"), ("downstream", "016"), ("finished", "這個 run 還沒到這個階段。")):      # finished-stage: a run that has not succeeded has not reached it | for stage, feature in (("launch", "012b"), ("downstream", "016"), ("finished", "該次分析尚未進行至此階段。")):      # finished-stage: a run that has not succeeded has not reached it | 計畫替換表（期望字串隨表值） |
| test_web_board.py:686 | assert cause(bad1) == "Out of memory second" and cause(bad2) == "—" and cause(gone) == "站台沒有回應" | assert cause(bad1) == "Out of memory second" and cause(bad2) == "—" and cause(gone) == "站台無回應" | 計畫替換表（期望字串隨表值） |
| test_web_board.py:697 | assert "<article" not in right and "目前沒有通知" in right | assert "<article" not in right and "目前無通知" in right | 計畫替換表（期望字串隨表值） |
| test_web_board.py:733 | assert r.status_code == 200 and "還沒有" in pane(r.text, "left") and "還沒有分析" in pane(r.text, "middle") and "—" in pane(r.text, "right") | assert r.status_code == 200 and "尚無" in pane(r.text, "left") and "尚無分析" in pane(r.text, "middle") and "—" in pane(r.text, "right") | 計畫替換表（期望字串隨表值） |
| test_web_board.py:736 | assert r.status_code == 200 and "還沒有" in r.text | assert r.status_code == 200 and "尚無" in r.text | 計畫替換表（期望字串隨表值） |
| test_web_board.py:740 | assert "還沒有" in c.get("/").text | assert "尚無" in c.get("/").text | 計畫替換表（期望字串隨表值） |
| test_web_board.py:784 | assert "找不到這個 run" in r.text and 'href="/"' in r.text | assert "找不到該次分析" in r.text and 'href="/"' in r.text | 計畫替換表（期望字串隨表值） |
| test_web_confirm_plain.py:61 | assert p == {"種類": "送出新分析", "run 名稱": "run-one", "管線": "nf-core/ampliseq", "版本": "2.18.0", "環境": "lab-a", | assert p == {"種類": "送出新分析", "分析名稱": "run-one", "管線": "nf-core/ampliseq", "版本": "2.18.0", "環境": "lab-a", | 計畫替換表（期望字串隨表值） |
| test_web_confirm_plain.py:79 | assert p["種類"] == "重跑" and p["run 名稱"] == "run-c-a2" and p["管線"] == "nf-core/ampliseq" and p["版本"] == "2.18.0" | assert p["種類"] == "重跑" and p["分析名稱"] == "run-c-a2" and p["管線"] == "nf-core/ampliseq" and p["版本"] == "2.18.0" | 計畫替換表（期望字串隨表值） |
| test_web_confirm_plain.py:87 | assert p["種類"] == "續跑" and p["run 名稱"] == "run-a-a2" and p["管線"] == "nf-core/ampliseq" and p["版本"] == "2.18.0" | assert p["種類"] == "續跑" and p["分析名稱"] == "run-a-a2" and p["管線"] == "nf-core/ampliseq" and p["版本"] == "2.18.0" | 計畫替換表（期望字串隨表值） |
| test_web_confirm_plain.py:99 | assert plain_of(page) == {"種類": "取消", "run 名稱": "run-b"} | assert plain_of(page) == {"種類": "取消", "分析名稱": "run-b"} | 計畫替換表（期望字串隨表值） |
| test_web_cost.py:26 | NOTE_ZH = "雲端費用以美元顯示，不換算新台幣；國網以 SU 計。數字是依執行紀錄估算，略低於實際帳單。" | NOTE_ZH = "雲端費用以美元顯示，不換算新台幣；國網以 SU 計。數字依執行紀錄估算，略低於實際帳單。" | 計畫替換表（期望字串隨表值） |
| test_web_cost.py:151 | assert [plain(h) for h in re.findall(r"<th\b[^>]*>(.*?)</th>", head, re.S)] == ["分析名稱", "開始時間", "在哪裡跑", "用量", "狀態"] | assert [plain(h) for h in re.findall(r"<th\b[^>]*>(.*?)</th>", head, re.S)] == ["分析名稱", "開始時間", "執行位置", "用量", "狀態"] | 計畫替換表（期望字串隨表值） |
| test_web_cost.py:190 | assert c[2] == "US$ 1.20" and "另有 2 個分析算不出" in c[3] | assert c[2] == "US$ 1.20" and "另有 2 個分析無法計算" in c[3] | 計畫替換表（期望字串隨表值） |
| test_web_cost.py:215 | assert "另有 2 個分析算不出" in card(get(w, "ann").text, 1)[3] | assert "另有 2 個分析無法計算" in card(get(w, "ann").text, 1)[3] | 計畫替換表（期望字串隨表值） |
| test_web_cost.py:226 | assert "這個月還沒有分析" in plain(pane(get(w, "ann", "/usage?month=2099-01").text, "middle")) | assert "本月尚無分析" in plain(pane(get(w, "ann", "/usage?month=2099-01").text, "middle")) | 計畫替換表（期望字串隨表值） |
| test_web_cost.py:230 | assert bad.status_code == 200 and "月份格式不對，顯示本月。" in plain(pane(bad.text, "middle")) | assert bad.status_code == 200 and "月份格式不符，已顯示本月。" in plain(pane(bad.text, "middle")) | 計畫替換表（期望字串隨表值） |
| test_web_cost.py:349 | assert "— 這個月還沒有分析" in plain(pane(get(w, "ann").text, "middle")) | assert "— 本月尚無分析" in plain(pane(get(w, "ann").text, "middle")) | 計畫替換表（期望字串隨表值） |
| test_web_cost.py:389 | assert "月份格式不對，顯示本月。" in bad.text | assert "月份格式不符，已顯示本月。" in bad.text | 計畫替換表（期望字串隨表值） |
| test_web_cost.py:465 | mid = re.sub(r"SU 換美元依 \S+ 匯率約略換算，不是帳單。\|SU figures are converted to US dollars at the \S+ rate, roughly; this is not a bill\.", "", mid) | mid = re.sub(r"SU 以 \S+ 匯率概算為美元，並非帳單金額。\|SU figures are converted to US dollars at the \S+ rate, roughly; this is not a bill\.", "", mid) | 計畫替換表（期望字串隨表值） |
| test_web_cost.py:525 | assert "另有 1 個分析算不出" in mid | assert "另有 1 個分析無法計算" in mid | 計畫替換表（期望字串隨表值） |
| test_web_finished.py:90 | assert [plain(k) for k, _ in prov_rows(t)] == ["管線", "版本", "改過的參數", "運算環境", "送出時間", "完成時間", "送出者", "樣本表"] | assert [plain(k) for k, _ in prov_rows(t)] == ["管線", "版本", "已變更的參數", "運算環境", "送出時間", "完成時間", "送出者", "樣本表"] | 計畫替換表（期望字串隨表值） |
| test_web_finished.py:108 | assert "這個 run 還沒到這個階段。" in mid(t) and "來源紀錄" not in mid(t) and "交付包" not in mid(t), st | assert "該次分析尚未進行至此階段。" in mid(t) and "來源紀錄" not in mid(t) and "交付包" not in mid(t), st | 計畫替換表（期望字串隨表值） |
| test_web_finished.py:121 | codes = re.findall(r"<code>(.*?)</code>", rows["改過的參數"]) | codes = re.findall(r"<code>(.*?)</code>", rows["已變更的參數"]) | 計畫替換表（期望字串隨表值） |
| test_web_finished.py:135 | assert rows["改過的參數"] == "— 全部用預設值" | assert rows["已變更的參數"] == "— 全部採預設值" | 計畫替換表（期望字串隨表值） |
| test_web_finished.py:144 | assert "這次送出的內容已不保留。" in sec and sec.index("這次送出的內容已不保留。") < sec.index("<dl") | assert "該次送出的內容已不保留。" in sec and sec.index("該次送出的內容已不保留。") < sec.index("<dl") | 計畫替換表（期望字串隨表值） |
| test_web_finished.py:146 | for k in ("管線", "版本", "改過的參數", "運算環境"): | for k in ("管線", "版本", "已變更的參數", "運算環境"): | 計畫替換表（期望字串隨表值） |
| test_web_finished.py:160 | assert plain(sec) == "— 不是從平台送出的分析，沒有來源紀錄。" and "<dl" not in sec | assert plain(sec) == "— 此分析並非經由平台送出，無來源紀錄。" and "<dl" not in sec | 計畫替換表（期望字串隨表值） |
| test_web_finished.py:183 | assert rows["結果表格"] == "✓ 在輸出資料夾" and rows["MultiQC 報告"] == "— 這次沒有產生" | assert rows["結果表格"] == "✓ 在輸出資料夾" and rows["MultiQC 報告"] == "— 該次未產生" | 計畫替換表（期望字串隨表值） |
| test_web_finished.py:186 | assert dict(pack_rows(c.get(url(rid)).text))["MultiQC 報告"] == "— 這次沒有產生" | assert dict(pack_rows(c.get(url(rid)).text))["MultiQC 報告"] == "— 該次未產生" | 計畫替換表（期望字串隨表值） |
| test_web_finished.py:189 | assert rows["結果表格"] == "— 沒有檔案" | assert rows["結果表格"] == "— 無檔案" | 計畫替換表（期望字串隨表值） |
| test_web_guided_launch_2b.py:654 | assert "我的 run" in t and "<script" not in t and "<figure" not in t and "style=" not in t | assert "我的分析" in t and "<script" not in t and "<figure" not in t and "style=" not in t | 計畫清單與裁決 11 之外（見範圍外）；僅期望字串，依所改表值 |
| test_web_results_outputs.py:106 | assert "沒有失敗的任務" in mid(c.get(url(rid, tab="tasks")).text) | assert "無失敗任務" in mid(c.get(url(rid, tab="tasks")).text) | 計畫替換表（期望字串隨表值） |
| test_web_results_outputs.py:120 | assert "這個 run 還沒到這個階段。" in t and 'class="rtabs"' not in mid(t) and "sumcards" not in mid(t) | assert "該次分析尚未進行至此階段。" in t and 'class="rtabs"' not in mid(t) and "sumcards" not in mid(t) | 計畫替換表（期望字串隨表值） |
| test_web_results_outputs.py:177 | assert "— 這個資料夾是空的" in plain(t) and "<table" not in t and "讀取於" in t and "重新讀取" in t | assert "— 此資料夾為空" in plain(t) and "<table" not in t and "讀取於" in t and "重新讀取" in t | 計畫替換表（期望字串隨表值） |
| test_web_results_outputs.py:187 | assert "✗" in t and "讀不到" in t and "the folder does not exist on the site" in t and "重新讀取" in t | assert "✗" in t and "無法讀取" in t and "the folder does not exist on the site" in t and "重新讀取" in t | 計畫替換表（期望字串隨表值） |
| test_web_results_outputs.py:192 | assert "讀不到" in t | assert "無法讀取" in t | 計畫替換表（期望字串隨表值） |
| test_web_results_outputs.py:198 | assert "讀不到" in t and "讀取中" not in t and "站台沒有回應" in t | assert "無法讀取" in t and "讀取中" not in t and "站台沒有回應" in t | 計畫替換表（期望字串隨表值） |
| test_web_results_outputs.py:211 | assert "讀不到" in t and "站台沒有回應" in t and "讀取中" not in t | assert "無法讀取" in t and "站台沒有回應" in t and "讀取中" not in t | 計畫替換表（期望字串隨表值） |
| test_web_results_outputs.py:224 | assert "讀不到" in c.get(url(rid)).text | assert "無法讀取" in c.get(url(rid)).text | 計畫替換表（期望字串隨表值） |
| test_web_results_outputs.py:226 | assert "這個資料夾是空的" in c.get(url(rid)).text | assert "此資料夾為空" in c.get(url(rid)).text | 計畫替換表（期望字串隨表值） |
| test_web_results_outputs.py:262 | assert "— 沒有輸出資料夾紀錄" in plain(t) and "不是從平台送出的分析，沒有輸出資料夾紀錄" in t | assert "— 無輸出資料夾紀錄" in plain(t) and "不是從平台送出的分析，沒有輸出資料夾紀錄" in t | 計畫替換表（期望字串隨表值） |
| test_web_running.py:88 | assert fields(m) == [("步驟", "—"), ("原因", "站台沒有回應"), ("之後", "重跑（確認頁）")] | assert fields(m) == [("步驟", "—"), ("原因", "站台無回應"), ("之後", "重跑（確認頁）")] | 計畫替換表（期望字串隨表值） |
| test_web_running.py:192 | assert notices(right) == [] and "目前沒有通知" in right | assert notices(right) == [] and "目前無通知" in right | 計畫替換表（期望字串隨表值） |
| test_web_running.py:239 | assert "目前沒有通知" in c.get("/?run=" + u1).text | assert "目前無通知" in c.get("/?run=" + u1).text | 計畫替換表（期望字串隨表值） |
| test_web_running.py:308 | assert "沒有失敗的任務" in text and "<table" not in text | assert "無失敗任務" in text and "<table" not in text | 計畫替換表（期望字串隨表值） |
| test_web_settings.py:103 | assert "—" in items[1] and "請用指令確認" in items[1] and "abf-platform token new" in items[1] and "✓" not in items[1] and "✗" not in items[1] / assert "✗" in items[2] and "未完成… | assert "—" in items[1] and "請以指令確認" in items[1] and "abf-platform token new" in items[1] and "✓" not in items[1] and "✗" not in items[1] / assert "✗" in items[2] and "未完成… | 計畫替換表（期望字串隨表值） |
| test_web_settings.py:117 | assert setup_items(mid)[1][1] == before and "請用指令確認" in before | assert setup_items(mid)[1][1] == before and "請以指令確認" in before | 計畫替換表（期望字串隨表值） |
| test_web_settings.py:162 | assert "沒有運算環境。" in setup_items(mid)[1][2] | assert "尚無運算環境。" in setup_items(mid)[1][2] | 計畫替換表（期望字串隨表值） |
| test_web_settings.py:240 | assert "沒有運算環境。" in sec and "<tr>" not in sec | assert "尚無運算環境。" in sec and "<tr>" not in sec | 計畫替換表（期望字串隨表值） |
| test_web_settings.py:295 | assert "AI 模型金鑰" in mid and "金鑰只存在你的瀏覽器，不會送到平台。" in mid and "逐步模式" in mid and "開發模式" in mid | assert "AI 模型金鑰" in mid and "金鑰僅儲存於您的瀏覽器，不會傳送至平台。" in mid and "逐步模式" in mid and "開發模式" in mid | 計畫替換表（期望字串隨表值） |
| test_web_settings_register.py:483 | assert "什麼都沒有改" in text and "重新整理" in text | assert "未變更任何內容" in text and "重新整理" in text | 裁決 11：期望字串 |
| test_web_settings_register.py:827 | assert r.status_code == 200 and "沒有運算環境。" in mid_of(r.text) and "/settings/pipelines" not in r.text | assert r.status_code == 200 and "尚無運算環境。" in mid_of(r.text) and "/settings/pipelines" not in r.text | 裁決 11：期望字串 |
| test_web_status_squares_3.py:150 | assert "站台沒有回應" in plain(pane(zh, "right")) and "執行 · 站台沒有回應" in plain(pane(zh, "left")) | assert "站台無回應" in plain(pane(zh, "right")) and "執行 · 站台無回應" in plain(pane(zh, "left")) | 計畫替換表（期望字串隨表值） |
| test_web_status_squares_3.py:173 | assert ("目前沒有通知" if lang == "zh" else "No notices") in pane(t, "right") | assert ("目前無通知" if lang == "zh" else "No notices") in pane(t, "right") | 計畫替換表（期望字串隨表值） |
| test_web_status_squares_3.py:206 | assert "還沒有分析" in t and 'class="sq"' not in t and not any(g in t for g in GLYPHS) | assert "尚無分析" in t and 'class="sq"' not in t and not any(g in t for g in GLYPHS) | 計畫替換表（期望字串隨表值） |
| test_web_upload.py:943 | assert "已存在" in text and "檔案仍在你的雲端資料夾，可換一個版本重新上傳" in text | assert "已存在" in text and "檔案仍在您的雲端資料夾，可換一個版本重新上傳" in text | 裁決 11：期望字串 |
| test_web_v2_skeleton.py:157 | assert "還沒有分析" in plain(mid) and "<h1>" not in mid and "bob-failed" not in r.text | assert "尚無分析" in plain(mid) and "<h1>" not in mid and "bob-failed" not in r.text | 計畫替換表（期望字串隨表值） |
| test_web_v2_skeleton.py:160 | assert "這個分析的對話" in plain(right) and "—" in plain(right) and "<button" not in right and "<form" not in right | assert "本分析的對話" in plain(right) and "—" in plain(right) and "<button" not in right and "<form" not in right | 計畫替換表（期望字串隨表值） |
| test_web_v2_skeleton.py:197 | "ann-lost": "執行 · 站台沒有回應", "ann-cancelled": "執行 · 已取消", "ann-done": "結果"}, second | "ann-lost": "執行 · 站台無回應", "ann-cancelled": "執行 · 已取消", "ann-done": "結果"}, second | 計畫替換表（期望字串隨表值） |
| test_web_v2_skeleton.py:237 | assert "這個分析的對話" in plain(right) and "ann-running" in plain(right) and "目前沒有通知" in plain(right) | assert "本分析的對話" in plain(right) and "ann-running" in plain(right) and "目前無通知" in plain(right) | 計畫替換表（期望字串隨表值） |
| test_web_v2_skeleton.py:242 | assert plain(right).endswith("問這個分析 之後開放") and "<textarea" not in right and "<input" not in right | assert plain(right).endswith("詢問本分析 之後開放") and "<textarea" not in right and "<input" not in right | 計畫替換表（期望字串隨表值） |
| test_web_v2_skeleton.py:295 | assert "11:07" in plain(nl) and plain(dd(nl, "原因")) == "站台沒有回應" and "state-failed" in nl | assert "11:07" in plain(nl) and plain(dd(nl, "原因")) == "站台無回應" and "state-failed" in nl | 計畫替換表（期望字串隨表值） |
| test_web_v2_skeleton.py:338 | assert plain(dd(right_notices(c.get("/?run=" + ids["lost"]).text)[0], "原因")) == "站台沒有回應" | assert plain(dd(right_notices(c.get("/?run=" + ids["lost"]).text)[0], "原因")) == "站台無回應" | 計畫替換表（期望字串隨表值） |
| test_web_welcome.py:18 | WELCOME_TITLE = "設定你自己的密碼 (set your own password)" / ZH = "你用的是管理者給的臨時密碼，它 72 小時內有效、只能用來設定你自己的密碼。設好之後就用新密碼登入。" | WELCOME_TITLE = "設定個人密碼 (set your own password)" / ZH = "目前使用的是管理者提供的臨時密碼，效期 72 小時，僅可用於設定個人密碼。設定完成後，請改以新密碼登入。" | 計畫替換表（期望字串隨表值） |
| test_web_welcome.py:567 | assert ("請用你的姓名與<strong>網頁密碼</strong>登入（網頁密碼不是 AI 用的權杖；它在平台主機的終端機用 <code>abf-platform user passwd</code> " / "設定，或用管理者給你的一次性臨時密碼）。") in text | assert ("請以您的姓名與<strong>網頁密碼</strong>登入（網頁密碼不同於 AI 使用的權杖；於平台主機的終端機以 <code>abf-platform user passwd</code> " / "設定，或使用管理者提供的一次性臨時密碼）。") in text | 計畫替換表（期望字串隨表值） |

## 改動對照（每一處表值與表外項）

| 位置 | 鍵／處 | 改前 | 改後 |
|---|---|---|---|
| web_board | mine | 我的 run | 我的分析 |
| web_board | none_yet | 還沒有 run。 | 尚無分析紀錄。 |
| web_board | no_analyses | 還沒有分析 | 尚無分析 |
| web_board | this_analysis / ask_here | 這個分析的對話／問這個分析 | 本分析的對話／詢問本分析 |
| web_board | c_open | 打開確認頁 | 開啟確認頁 |
| web_board | c_content_text / c_next_text | 這個 run 已成功…結果不會被動。／打開確認頁，看清楚要刪的資料夾再決定。 | 該次分析已成功；其中間檔（work）可清理，結果不受影響。／請開啟確認頁，核對將刪除的資料夾後再決定。 |
| web_board | r_site / row_site | 站台沒有回應 | 站台無回應 |
| web_board | not_reached | 這個 run 還沒到這個階段。 | 該次分析尚未進行至此階段。 |
| web_board | not_found_title / not_found_body | 找不到這個 run／沒有這個 run，或它不是你的。 | 找不到該次分析／無此分析，或該分析不屬於您。 |
| web_board | quick | 用這個 run 的內容再啟動一次 | 沿用設定重新分析（與 GUIDED g_quick 同字串，裁決 4） |
| web_board | no_notices / no_failed_tasks | 目前沒有通知／沒有失敗的任務 | 目前無通知／無失敗任務 |
| web_board | r_none / r_generic / r_form | 什麼都沒有送出。／這件事現在做不了。／這個表單的記號不對…… | 未送出任何內容。／目前無法執行此操作。／表單驗證碼不符或已失效，未送出任何內容。請重新整理頁面後再操作。 |
| web_board | o_failed / o_none / o_empty | 讀不到／沒有輸出資料夾紀錄／這個資料夾是空的 | 無法讀取／無輸出資料夾紀錄／此資料夾為空 |
| web_settings | token_hint / check_cmd | 在終端機用 … 建立。／請用指令確認 | 請於終端機執行 … 建立。／請以指令確認 |
| web_settings | ce_none / no_ce | 沒有運算環境。 | 尚無運算環境。 |
| web_settings | key_note | 金鑰只存在你的瀏覽器，不會送到平台。 | 金鑰僅儲存於您的瀏覽器，不會傳送至平台。 |
| web_settings（表外，裁決 10） | pf_expired / pf_foreign | 表單的記號不正確…什麼都沒有改／表單不是從本頁送出的 | 表單驗證碼不符或已失效，未變更任何內容。／此表單並非由本頁送出，未變更任何內容。 |
| web_cost | unknown_runs / action / note / th_where / empty / bad_month / no_reason / usd_note | 算不出／用完／數字是依…／在哪裡跑／這個月還沒有分析／月份格式不對，顯示本月。／算不出／SU 換美元依 %s 匯率約略換算，不是帳單。 | 無法計算／用盡／數字依…／執行位置／本月尚無分析／月份格式不符，已顯示本月。／無法計算／SU 以 %s 匯率概算為美元，並非帳單金額。 |
| web_finished | params / defaults / gone_note / foreign / no_multiqc / no_files | 改過的參數／全部用預設值／這次送出…／不是從平台送出的分析，沒有來源紀錄。／這次沒有產生／沒有檔案 | 已變更的參數／全部採預設值／該次送出…／此分析並非經由平台送出，無來源紀錄。／該次未產生／無檔案 |
| web_upload（裁決 1，只動 zh 值） | intro / cmds_note / p_keep | 含「你」 | 「您」或省略主詞（`intro`、`cmds_note`、`p_keep` 三處，裁決 10） |
| web.py `_PLAIN["zh"]` | run | run 名稱 | 分析名稱 |
| web.py 內嵌句 | 登入說明、來源不符、/welcome 標題與說明、表單失效（三處）、無此申請（三處）、無此網址（三處）、非您的申請（標題與內文，表外，裁決 10）、確認頁說明（刪除／送出／取消）、逾時／作廢（四處）、已送出（兩處）、同意頁（未命名、限制兩段、連線說明）、已處理／已逾時／未處理 | 口語（你、這個、什麼都沒有改、回到…） | 正式書面語，見 `git diff platform/abf_platform/web.py`；英文半句與標記一字未動 |
| confirm.py:390 | JobRefused 訊息 | 這個 run 還有工作在排隊或進行中，不能刪除 | 該次分析仍有工作在排隊或進行中，無法刪除（英文半句不動；裁決 2、12） |
| web.py /welcome 標題（表外，裁決 10） | title | 設定你自己的密碼 | 設定個人密碼 |

`confirm.py:145` 不改（裁決 2）。GUIDED、`web_launch.py`、`welcome.py` 與其他動作層檔案沒有碰。

## 手動證據

- 範圍：`git diff --stat`（非測試部分）只有 DESIGN.md、confirm.py、web.py、web_board.py、web_cost.py、web_finished.py、web_settings.py、web_upload.py 八個檔；每一行改動都含中文字（掃描 0 行例外），路由與 `@app`／`Route(` 行 0 變動，各表的鍵集合改前改後相同（逐檔比對）。
- 英文頁不變：`test_clean_page.py` 的看板整頁摘要 `succeeded-en`、`failed-en`、`running-en` 在字串改動後仍是 870addd406492402、918ba6c8db56e423、9c1d9195eacfbe23，未重算；新測試 `test_english_pages_have_no_cjk_everywhere` 綠。確認頁（含 en）帶中文句，屬原本就如此，其摘要因中文句改而重算。
- TC-020（未列入表的鍵維持原值）：以鍵集合逐檔比對確認，改動只落在表列的值。
- TC-081：夾具的 run 名稱用 `alpha-*`／`beta-one`，避開單獨的 `run`；規則 `(?<![A-Za-z])runs?(?![A-Za-z])` 從不關閉，`<code>`／`<pre>`／`<kbd>` 與管線說明欄之外全頁適用。
- 國網與雲端啟動測試（`test_aws_launch.py`、`test_azure_launch.py`、`test_gcb_launch.py`）：期望字串未動，保持綠。

## 後續（看到但沒改的動作層句子）

- `confirm.py:145` 與其他動作層訊息（`actions/__init__.py` 的 `_OUTPUTS_NO_LAUNCH`「不是從平台送出的分析，沒有輸出資料夾紀錄」、`_OUTPUTS_NO_ANSWER`「站台沒有回應」等）仍有口語；本任務按裁決 2 只動 `confirm.py:390`，這些留給後續任務。
- 登入、/welcome、同意頁的「中文 (English)」並排與 `?lang` 單語規則不一致：已在 DESIGN.md Open 記一行，另案處理（裁決 6）。

## 清單之外的兩處期望字串（需要維護者知悉）

`test_oauth_review.py::test_r2`（同意頁「不能替你送出」→「不能代您送出」）與 `test_web_guided_launch_2b.py::test_scope_page_limits`（「我的 run」→「我的分析」）不在計畫清單與裁決 11 內，但它們隨計畫替換表的值變紅。只改了期望字串，斷言數量與強度不變。

`test_su_usd.py`（同樣不在清單內）在全套測試中變紅，五處期望字串隨 `web_cost` 與 `web_board` 的表值改了：附註句「數字依執行紀錄估算」、匯率句「SU 以 %s 匯率概算為美元，並非帳單金額。」（兩處）、「— 本月尚無分析」（兩處）、「找不到該次分析」、「待處理：本月雲端額度已用盡」。斷言數量與強度不變。

## 合併 origin/v3 後新增的字串（10-29）

| 檔:行 | 改前 | 改後 | 依據 |
|---|---|---|---|
| web_settings.py:42 `pf_pick_gone` | 站台清單中沒有這個版本，請按「重新讀取站台清單」。 | 站台清單中無此版本，請按「重新讀取站台清單」。 | 合併進來的新中文字串違反禁用詞（這個、沒有這個） |
| test_settings_pick_installed.py:25 `GONE_ZH` | 同上改前 | 同上改後 | 期望字串隨表值 |
| test_settings_pick_installed.py:37 `EXPIRED_HINT` | 表單的記號不正確或已失效，什麼都沒有改。請重新整理頁面後再試。 | 表單驗證碼不符或已失效，未變更任何內容。請重新整理頁面後再試。 | 隨 `pf_expired` 表值（本計畫裁決 10） |
| test_settings_pick_installed.py:725 | "沒有運算環境。" | "尚無運算環境。" | 隨 `no_ce` 表值 |
