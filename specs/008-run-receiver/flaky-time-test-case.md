# 測試案例:rebuild 時間比對 flake(A 級,只動測試)

範圍:`platform/tests/test_nextflow_e2e.py` 的 `_same_runs`。
證據:CI run 38598019862 第 1 次嘗試,commit cba254d,`started_at` live=`2026-10-14T16:33:36Z`、rebuild=`...38Z`,差 2 秒,斷言在 test_nextflow_e2e.py:234;tc030、tcf3_11、tc031 同時失敗(同一次 run)。

| TC | 類型 | 內容 | 預期結果 |
|---|---|---|---|
| TC-FT-01 | 自動 | `_same_runs` 的 started_at 與 ended_at 容許值改成同一個有名字的模組常數(如 `_CLOCK_SLACK_SECONDS`),兩處都用它,不再有裸數字 `<= 1` | 檔內 `_same_runs` 沒有字面 `<= 1`;常數值 3 |
| TC-FT-02 | 自動 | 常數上方有註解,寫明理由並引用:CI run 38598019862 的 2 秒實例,以及 research.md「Time resolution」。註解不得聲稱已證實成因,除非執行者另附來源 | 註解含 run id、2 秒、research.md 引用 |
| TC-FT-03 | 自動 | 同一個 `_same_runs` 對 started_at 差 2 秒的資料(CI 實例)通過,對 ended_at 差 2 秒也通過 | 不再丟 AssertionError |
| TC-FT-04 | 自動(防線) | 對 started_at 差 60 秒的資料,`_same_runs` 仍然失敗;ended_at 差 60 秒也仍失敗。差剛好比常數多 1 秒也失敗 | 有直接呼叫 `_same_runs` 並預期 AssertionError 的測試;沒有這個測試就是 FAIL |
| TC-FT-05 | 自動 | 其他斷言一字不動:`assert before.keys() == after.keys()`、`_compared(a) == _compared(b)`、`ended_at` 為 None 時的 `==` 精確比對、第 385 行 `last_message_at` 的 `<= 1` | `git diff main` 在該檔只有:新常數與註解、`_same_runs` 兩行改用常數、新增的防線測試 |
| TC-FT-06 | 自動 | 用 `ended_at` 為 None 的資料呼叫,兩邊都 None 通過;一邊 None 一邊有值仍失敗 | 精確比對仍有效 |
| TC-FT-07 | 文件 | research.md "Time resolution" 補記:2 秒的實例(日期、run id、欄位)、現有「差 1 秒」解釋不足以說明 2 秒、容許值改為 3 秒及原因;不得刪掉原有 1 秒段落 | 段落存在且引用 CI 實例 |
| TC-FT-08 | 文件 | PITFALLS.md 新增一條,指向此 flake 與 TC-FT-04 的防線 | 條目存在 |
| TC-FT-09 | 不在範圍 | 產品程式碼、rebuild 邏輯、其他測試檔、CI 設定、`tests/` 以外 | `git diff main --stat` 只含 test_nextflow_e2e.py、research.md、PITFALLS.md、本 spec 的檔案 |
| TC-FT-10 | 不在範圍 | 不得用重試、`xfail`、skip、retry 裝飾器代替放寬 | 檔內無新增 skip/xfail/retry |

通過條件:WSL 全套綠(已知的 gate_process_count 環境失敗除外)、CI 綠、verifier 驗收 PASS。
