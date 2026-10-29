# 網頁國網從頭送到完成的三個缺口 progress ledger

- [x] 作法 1 國網樣本表上傳：`uploads_web.py`（接收 `sheet` 欄、`sheet_problem`、`clean_sheet_name`、`save_sheet`）、`web_upload.py`（樣本表一節、成功句、`sheet_ready` 看狀態 available）、`web.py`（`sheet_post`、`?notice=sheet_saved&sheet=<檔名>`）。
- [x] 作法 2 送出後：`web.py` `confirm_post` 的 `sent()`；錯誤頁「請回到 AI 重新送出。」→「請重新送出。」。`clean_work` 頁不變。
- [x] 裁決 7 `?run_name=`：`web.py` `run_by_name`、`web_board.render_waiting`；`?run=` 不動。
- [x] 作法 3 運算環境欄：根因＝`get_run` 從不填 `compute_env`，卡片讀 `run.get("compute_env")` 永遠是空。修在取值處：`jobs.latest_launch_ce`（只讀，取最新一筆送出紀錄的 ce），由新的只讀動作 `actions.run_environment` 給值，`web.py` 的 `read_run` 補上 `compute_env`；結果階段卡片 outputs 沒值時退回 run 的值。不改資料庫結構、不改 `actions.get_run`（原先加在 get_run 時 `test_mcp.py::test_tc025_streamable_http_gives_the_same_answers_on_loopback` 因 stdio 與 HTTP 兩次讀取之間才寫入送出紀錄而不一致，故改到網頁層，不動那條斷言）。
- [x] `docs/TESTING.md` 新增「國網，網頁從頭到完成」。
- [x] 新測試 `platform/tests/test_web_nano4_path.py`（TC-001 至 TC-044 的自動項）。

## 被改的既有斷言（舊值 → 新值、原因）


`platform/tests/test_clean_page.py`（裁決 10：雜湊釘住的舊斷言，只改雜湊值，不刪斷言）：
- `BASE_CONFIRM['void-zh'/'void-en']` 8dc1fd751ab5aeca → b5dc5bfdf16907a4：作廢頁句子「請回到 AI 重新送出。」→「請重新送出。」（作法 2 最後一點）。`pending-*`、`confirmed-*` 不變（TC-027）。
- `BASE_EXPIRED` 四條：launch c35c165714b5f908 → 53632ce9d4983282、cancel 8451aff28a884534 → 2a611844fdf29f53：逾時頁同一句話。
- `BASE_POST['pressed-launch']` ef1083638be3de88 → 1547e332c788c9c1、`['pressed-cancel']` 9c76dd8bc4a4c249 → 7774e15781a19263：送出成功頁換成作法 2 的三句話加「查看進度」。
- `BASE_POST['late-launch'/'late-cancel']` d2df3540d123bd63 → 7d09046dd1a0078d：POST 被拒的頁同一句話。
- `BASE_BOARD['failed-zh']` f5866fcf5bb0a339 → fdf0381e843890cb、`['failed-en']` 918ba6c8db56e423 → 54b26610c18dba4b、`['running-zh']` f5b7e52afdb2ec69 → 526adc50c5cd8114、`['running-en']` 9c1d9195eacfbe23 → b0c4b62b17b8cf91：進度頁「運算環境」卡片原本是「—」，現在顯示該 run 送出紀錄的環境名稱（測試資料的送出紀錄 ce 是 lab-a）——這正是作法 3 要改的值，只有這張卡片不同。`succeeded-*` 不變。

`platform/tests/test_web_upload.py`（裁決 10 准許改寫）：
- TC-006：「沒有可用的雲端運算環境」→「沒有可用的運算環境。請先到設定頁建立並檢查運算環境。」（裁決 11）；原本「有國網環境也沒有檔案欄」改為：available 的國網環境只出現樣本表檔案欄（沒有 FASTQ 欄），不是 available 時什麼都沒有（裁決 8）。
- TC-007／TC-008：原本斷言「有國網環境時出現『國網環境的資料目前請用指令上傳』、英文含 Slurm 句」→ 改為這句整個拿掉，有 available 國網環境時改出現樣本表一節，狀態不是 available 時沒有（作法 1、裁決 8）。

`platform/tests/test_web_running.py::test_r40_r44_title_and_cards`：運算環境卡片 `—` → `lab-a`（中文與英文各一處）。測試資料的送出紀錄 ce 是 lab-a，作法 3 要的就是這個變化；卡片其他三格不變。
`platform/tests/test_web_parity.py`：`WEB_ONLY` 加一筆 `run_environment`（新的只讀動作，依該檔「加名字要改表」的規則；只加不刪）。

其他既有斷言：未刪、未放寬。`constitution_scope_test.sh` 在 WSL 紅是環境問題（Windows git 建的 worktree），以 CI 為準（裁決 5）。
