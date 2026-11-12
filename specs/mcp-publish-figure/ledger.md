# MCP publish_figure：私有圖庫、勾選打包 progress ledger

## 進度（執行者，stamp 20261112-1900-L-mcp-publish-figure-r2）
- [x] 切片 1 全部：`publish_figure` 走確認通道（ELICITED／PAGE／CHAT 共用 `_ask`），確認後才寫 `figures_root/<user>/<run_id>/`；新種類 `publish_figure`（`confirm.NO_JOB_KINDS`，不建 job）；遷移 `_migrate_confirmation_kinds`。
- 本輪補的：`platform/tests/test_publish_figure_confirm.py`（確認通道拒絕與遷移測試）；英文確認頁用 facts 重建英文畫面（`screen_for_page`，bundle 多 `replaces`）；`test_web_parity.py` 登記三個新公開名（只增不減，OWED 不變）。
- 既有測試被改動（皆同步新種類／新工具）：`test_cleanup_store.py`（kinds 迴圈與 declared_kinds 多 publish_figure）、`test_web_parity.py`（INTERNAL／WEB_ONLY 增名）、`test_chat_tools.py`（REQUESTS 還原為原六個，聊天不提供 publish_figure）、各 mcp 合約與 tools.json、aws/azure/gcb/k8s 等的工具清單釘住。
- L 級證明：(a) 範圍見 `git diff --stat`（platform/ 與 docs，沒碰 spec／憲法／.github／plugin.json／ROADMAP）；(b) confirm.py 只加 approve 的 writer 分支與 facts 欄位；(c) 遷移：舊表資料列前後相同、`PRAGMA foreign_key_check` 為空、jobs 的 CHECK 不變（test_confirmations_check_migration、test_migration_of_the_oldest_database…）；(d) `confirmations.kind` 的讀寫處由 test_cleanup_store／test_confirm_page 覆蓋；(e) 失敗時回滾（test_migration_failure_rolls_back）。
- 新常數：MAX_FIGURES_PER_CALL=10、MAX_PER_RUN=30、MAX_BUNDLE_BYTES=5 MiB、NO_JOB_KINDS。`index.json` 版本 1，欄位 size／type／caption／code_file／params_file／created／packed／packed_at／request_id。
- 人工項（TC-057／058／098，截圖）：執行者未跑，UNVERIFIED。
- 要問維護者：憲法清單是否列入 publish_figure；刪圖是否另需確認；base64 保留到 forget 為止是否可接受。

## 修正輪（lead 裁決 F1 至 F8，2026-11-12 深夜；執行者）

- [x] F1 十條既有測試同步（只增不減）：`test_keep_submissions.py`（tc040：`test_actions_layer.py` 的 `WRITE_NAMES` 原字串不動，改為其後另加一行 `WRITE_NAMES = WRITE_NAMES + ["publish_figure"]`，`test_guidance.py` 的清單字串同樣在原清單後 `+ ["publish_figure"]`；tc073：CHANGELOG 的 keep-submissions 條目維持第一條，publish_figure 條目排第二；tc083：CHECK 字串加 `'publish_figure'`；tc094/095/104：寫入工具元組加 `publish_figure`）、`test_mcp.py::test_tc024`（寫入工具元組加名）、`test_su_usd.py::test_tc033`（工具集合加名）、`test_mcp_canvas_read.py::test_registration`（非唯讀集合加名）、`test_mcp_launch_pipeline.py`（`test_tool_count_and_no_extra_tools` 22→23；`test_no_schema_change` 允許的變動只限 `store.py` 內 publish_figure 這一筆的逐行清單，其餘任何一行（含 migrations、schema.sql）仍紅）、`test_guidance.py::test_tc501`（清單後加名）。修正前這十條在本分支紅、在 origin/v3 綠；修正後綠。
- [x] F2 補測試：新增的測試函式 TC 註解皆用已確認合約的編號（TC-008、011、012、013、014、021、022、023（14 種壞檔名＋同批同名，共 15 種）、024、025、026、027、028、030、031、032、033、034、035、036、037、038（以 `bundle_json` 剛好 5 MiB 與多 1 位元組）、052、054、061、062、063、084、086、095、096）。TC-054 的舊斷言（`"⚠" in zh or "✓" in zh or "!" in zh or "待" in zh`，永遠不會失敗）換成「按鈕為『送出』且說明段落存在」，另有 `test_confirm_page_states_say_it_in_words`：待確認、成功、逾時、寫入失敗四個狀態各以 `<p class="ok|bad">` 的文字說出狀態（既有三種確認種類頁面也是這個寫法：文字加 class，沒有符號字元）。`test_page_headers_and_css_are_unchanged` 原本比對的 `CSS_SHA256` 在 web.py 不存在（兩邊都是 None，永遠相等，等於沒測）；現改比對 `_HEADERS`、`LAUNCH_HEADERS`、路由表與 `web_board.py`（樣式表所在）整檔未改，找不到 origin/v3 時 `pytest.skip` 並寫明原因，不再靜默通過。`test_constitution_untouched` 取不到 origin/v3 時本來就是 `pytest.skip`（有原因）。
- [x] F3 TC-092（舊庫只有 clean_work，`make_old` 製作；以 WSL 實跑 `store.connect_state`）：遷移前 `confirmations` 3 列、`jobs` 4 列、`PRAGMA foreign_key_check` 輸出 `[]`、CHECK 不含 publish_figure；遷移後 3 列、4 列、`[]`、CHECK 含 publish_figure；再開一次：3、4、`[]`、同。測試 `test_confirmations_check_migration`、`test_migration_run_twice_gives_the_same_result`（兩次遷移的 `sqlite_master` 與 confirmations、jobs 全部列完全相同）。
- [x] F3 TC-093（`confirmations.kind` 的讀寫位置，grep `confirmations` 於 `platform/abf_platform`、`platform/abf_station`）：
  - 寫入：`confirm.py` `_confirm`（launch、cancel，終端機通道，不受影響）；`create_pending`（INSERT 帶 kind，新 kind 與其餘同一路徑）；`store.py` 的 CREATE（含 CHECK）與 `_migrate_confirmation_kinds`（複製 `shared` 欄位，新 kind 只是多收）。
  - 讀取依 kind 分支：`create_pending` 的 `kind = ?` 重用查詢（對 publish_figure 以 kind＋hash＋擁有者＋剩餘時間查，同一路徑）；`kind = 'clean_work'` 的額度與 `kind <> 'clean_work'` 的 10 筆額度（publish_figure 落在後者，與 launch、cancel 同組，TC-065／066 覆蓋）；`approve` 內 `row["kind"] in NO_JOB_KINDS`（新分支）與 `JOB_KIND[row["kind"]]`（launch、cancel、clean_work，原樣，publish_figure 在前一個分支就返回，不會走到）；`find_approved`（以呼叫端傳入的 kind 查，且 JOIN jobs，publish_figure 沒有 job 故不會被找到，沒人用它查）；`find_cancel`（kind='cancel'）；`open_clean_requests`（kind='clean_work'）；`facts`（新增 publish_figure 分支，其餘原樣）；`describe`（不看 kind，publish_figure 與其餘同樣被回傳）；`forget_content`（以 bundle 內 run 名稱找，不看 kind，publish_figure 的列一併被清；`test_confirmed_row_keeps_bundle_until_forget` 覆蓋）。
  - `jobs.py`：`_check_confirmation`（`CONFIRMED` 字典，未動，publish_figure 不在內，永遠不會被 `enqueue_confirmed` 接受）、`launch_confirmation`、`enqueue_confirmed`、`claim`（只對 jobs 的 kind 查其 confirmation）、845 行 `kind = 'launch'`（只找 launch）：皆不受影響。
  - 其他：`oauth.py` 與 `abf_station` 只在註解或自己的 `used_confirmations` 集合出現 `confirmations`，不讀 kind 欄；`actions/__init__.py` 的 `_ask` 傳入 kind 字串、`request_forget` 呼叫 `forget_content`。
  - 新增而依 kind 的位置只有：`approve` 的 NO_JOB 分支、`facts` 的 publish_figure 分支、`drop_figure_content`、`pending_figure_bytes`、web.py 的確認頁分支。
- [x] F4：`confirm.py` 新增三個函式與 `approve` 內 NO_JOB 分支的一個 UPDATE（見下「confirm.py 與 store.py 的改動清單」）。圖的 base64 在申請 confirmed 且寫入、或寫入失敗作廢的同一交易內即被清掉；void 與逾期的 pending 列在同一使用者下一次 `publish_figure` 申請的開頭被清；列保留檔名、類型、大小、sha256、說明、程式碼、參數與 `replaces`。新常數 `figures.MAX_PENDING_BYTES = 20 MiB`（每位使用者待確認且未逾期的 publish_figure 申請的 `bundle_json` 總長；同內容再問＝同一筆申請，不重算）。重放已完成的 `user_confirmed=true`：以儲存申請的 `replaces` 重算雜湊，回「已存入圖庫」。`test_confirmed_row_keeps_bundle_until_forget` 依裁決改寫（confirmed 後內容已清、中繼資料還在、圖庫檔案不受影響、forget 後整列內容清空）。**與合約的衝突（請 lead 知悉）：TC-071 寫「核准後 `bundle_json`（含圖 base64）仍在」、TC-083 寫「已確認列的…」；F4 的裁決與之相反，我照 F4，沒有改合約文件。**
- [x] F5：`write_confirmed` 先讀下所有將被動到的檔案（圖、程式碼檔、參數檔、`index.json`）的原位元組，任何一步失敗就逐一寫回（原本不存在者刪除）。測試 `test_f5_a_failed_overwrite_puts_every_old_byte_back`（失敗點為圖、程式碼檔、參數檔、`index.json` 四種）、`test_f5_a_failed_first_write_leaves_no_folder_content`。
- [x] F6：`write_confirmed` 重做大小寫不分的衝突檢查，並比對實際會被取代的集合與申請上的 `replaces`，不同就 `JobRefused`（頁面 409、列作廢、什麼都不寫）。測試 `test_f6_case_variants_approved_in_turn_only_the_first_lands`、`test_f6_a_request_that_did_not_say_replaces_does_not_replace`。
- [x] F7：caption 含換行或控制字元（Unicode 類別 Cc、Zl、Zp，含 `\t`、`\x85`、` `）拒絕；caption、code、params 含孤立代理字元在申請時拒絕（原本 `surrogatepass` 放行後在雜湊時才炸）；確認畫面每張多一行 SHA-256 前 12 碼（中、英）。
- [x] F8：`docs/TESTING.md` 手動步驟加第 6 步「不按、等 10 分鐘就不寫」；`docs/PLATFORM.md` 該工具段落改寫保留說明；`test_documents_describe_the_tool` 讀文件驗證。
- 不在本輪（lead 已排除）：SVG 過濾可被繞過（第 2 片送圖標頭把關）、Windows 保留檔名、forget 時圖庫檔案保留（請維護者看）。

### confirm.py 與 store.py 的改動清單（L 級，修正輪後的全部）

`git diff origin/v3 -- platform/abf_platform/confirm.py`：被**刪除**的行只有三行——`approve` 簽名那一行（多一個 `writer=None`）、其 docstring 的最後一行（接續新增段落）、`if status != "queued":`（改成 `not in ("queued", "written")`）。其餘全是新增：
1. `NO_JOB_KINDS = ("publish_figure",)`（`JOB_KIND` 字典不動）；
2. `approve` 內 `if row["kind"] in NO_JOB_KINDS:` 一個分支（呼叫 writer；失敗時作廢；最後把該列 `bundle_json` 換成不含圖位元組的版本），在 `job_kind = JOB_KIND[row["kind"]]` 之前，且各分支都 `return`，所以 launch、cancel、clean_work 永遠走不進去；
3. 三個新函式 `_without_content`、`drop_figure_content`、`pending_figure_bytes`（只有 publish_figure 的流程呼叫）；
4. `facts` 內 `if row["kind"] == "publish_figure":` 一個分支。
`store.py`：只有 CHECK 字串加 `'publish_figure'`、`_confirmations_current` 多一個條件、新函式 `figures_root`，與兩處註解；本輪未再動。
既有種類不受影響的證據：`test_cleanup_confirm.py`、`test_pending_confirm_restart.py`、`test_keep_submissions.py`、`test_chat_confirm.py`、`test_resume_*`、`test_confirm_page.py`、`test_clean_page.py`、`test_cleanup_store.py`（皆含 launch、cancel、resume、relaunch、clean_work、forget 的核准、逾時、遷移）在本輪結束時全綠（見回報的全套測試）。
