# 確認頁與看板提示的文字（刪除不再顯示成「取消」） progress ledger

- [x] 確認頁（web.py）：clean_work 顯示「清理確認」、「確認刪除」、7 天逾時、白話區塊三列；按下後成功／失敗頁不叫人回到 AI。launch／cancel 輸出以雜湊逐字比對未變。
- [x] 看板通知（web_board.py）：succeeded run 且本人有未逾時清理申請時，右欄多一張「待處理」卡片（只有連結）。
- [x] actions.clean_requests（唯讀，不是工具、不是路由）。
- [x] 測試 platform/tests/test_clean_page.py：28 條綠。

## 手工建一張清理申請（只用來看畫面，不要按「確認刪除」）
在 platform 目錄，對一個已有 Slurm 工作編號的 run（launches 表有 slurm_job_id）執行：
confirm.create_pending(state_db, "clean_work", "<環境名>", {"version":1,"run_name":..,"slurm_job_id":..,"run_folder":..,"agent":..,"ce":..,"work":<run_folder>/work}, "<摘要>", <使用者 id>)
回傳的申請編號開 /c/<編號>（加 ?lang=en 看英文）；該 run 的看板頁右欄會有卡片。

## git diff --stat（相對 5aa345c）
 platform/abf_platform/actions/__init__.py |   7 +
 platform/abf_platform/web.py              |  37 ++-
 platform/abf_platform/web_board.py        |  25 +-
 platform/tests/test_clean_page.py         | 492 ++++++++++++++++++++++++++++++
 4 files changed, 548 insertions(+), 13 deletions(-)

## 要問的問題
- 英文確認頁的標題、引言、逾時／作廢句沿用中文（計畫只定了英文的種類、欄位、按鈕）；英文通知卡片的內容與下一步文字是我照中文意思寫的，等維護者看截圖。
- 計畫寫 MCP 工具 12 個，實際 list_tools 現在是 15 個（本片沒動）；測試改成「沒有名稱含 clean 的工具」。
- 截圖（維護者回好／不好才合併）尚未附，需在本機看板操作。

## 裁決二執行（2026-10-25）
- 已改四條既有測試（test_cleanup_confirm.py::tc067、test_cleanup_store.py::TC-030、test_web_parity.py 兩條），並加唯讀檢查 `_clean_work_read_only_problems`（ast 逐函式，排除巢狀函式）。四檔相關測試 129 條綠。
- 全套四次都不是全綠，每次紅的不同，且單獨重跑多半綠：機器負載造成逾時／計時門檻（confirm_launch_test.sh 的「slow 1.2s」、platform_clock、test_relay_loopback 單跑 123 綠、test_station_e2e）。jev_test.sh 第一次紅是因為鏡像裡舊 pyc 含 "Jev" 位元組（清掉 __pycache__ 後綠）。

## 裁決三執行（2026-10-25）
- 截圖已放 `specs/cloud-cleanup-e/shots/`：confirm／board × zh／en × 1440／390 共八張 png（`shots/html/` 是渲染來源）。用測試世界渲染 HTML 後以 Playwright 截圖。
- 全套在 25e19e4 跑：123/125，紅的只有兩支且都是負載造成（機器 load average 約 29–37）：`confirm_launch_test.sh`（「slow 1.5s」超過 1.2s 門檻，只有 TC-051／POL-22 的 1 MB 計時案例）與 `platform_test.sh`（TIMEOUT 900s）。
- 單跑：`--only platform_test --timeout 1500` → 1/1 passed, all green；`--only confirm_launch` 負載降到 8.8 後 → 1/1 passed, all green（負載高時單跑同樣 slow 1.1–1.5s 紅，與本片無關：本片沒動 hook／shell）。依裁決三第 7 點視同綠。
- 本次之後只多了這份 ledger 的文字，沒有程式變動。
- ruling four: route hash pin replaced by 'no route contains clean' because #234 added /welcome; intent of TC-061 unchanged.
- ruling four 後全套 126/126 all green（無計時紅）。
