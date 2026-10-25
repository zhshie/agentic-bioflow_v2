# 臨時密碼登入後的設定密碼頁（/welcome） progress ledger

- [x] RED：`platform/tests/test_web_welcome.py` 新增（自動案例 TC-001..083，每個測試註解寫 TC 編號）。
- [x] GREEN：`platform/abf_platform/web.py`
  - 新路由 `GET|POST /welcome`（`welcome_get`／`welcome_post`／`welcome_form`）。
  - `login_post`：臨時密碼（`must_change`）303 到 `/welcome`，忽略 `next`；其餘照舊。失敗次數拿回的寫法抽成 `give_back`，登入與 `/welcome` 共用。
  - 共用小函式 `unauth(request)`：臨時 session 導 `/welcome`，否則 `/login`；原本 6 處未登入 303 `/login` 的分支都改用它（`logout_post` 結尾不動）。`/c/{rid}`、`/consent/{rid}` 沒登入仍回登入頁（不動），臨時 session 則 303 `/welcome`（`to_welcome`）。
  - 登入頁說明句改為計畫作法 6 的句子。檔頭路由清單 docstring 補 `/welcome`。
- [x] 文件：`docs/TESTING.md` 新一節手動驗收（發臨時密碼 → 登入 → 改密碼 → 進看板）；`docs/PLATFORM.md` 路由說明補一句 `/welcome`。

## 既有測試的改動（逐條，理由）

1. `platform/tests/test_temp_password.py::test_tc025`：臨時 session 打 `/` 的期望由 303 `/login` 改成 303 `/welcome`（裁決 1；憲法 6.1.0）。
2. `platform/tests/test_temp_password.py::test_tc027`：略過清單保留原本的，加略過 `/welcome` 與 `/authorize`；其餘每條路由每個方法，臨時 session 回應一律 303 且 Location＝`/welcome`，並確認 `w.jobs() == []`、確認單仍 pending、回應不含 run 名稱；另加 `/authorize` 對臨時 session 與沒登入逐項相同；`/consent/{rid}` 改用一筆真的 OAuth 同意請求的網址（原本用確認單 id，兩邊都 404，到不了登入判斷）；`seen >= 8` 保留（裁決 1）。
3. `platform/tests/test_owner_binding.py::test_tc068_no_new_way_to_log_in`：路由集合加 `"/welcome"`、`store.*` 名稱集合加 `"change_web_password"`，只這兩項（`/welcome` 路由與它用到的 `store.change_web_password` 是本任務新增；計畫範圍明載）。
4. 其他把登入頁說明句或路由集合逐字釘住的既有測試：無（全套測試沒有因此紅的）。

沒有刪除、略過、放寬任何既有斷言；`test_tch05` 與 `web.py` 字詞檢查一字未改；`store.py`、`web_board.py`、`web_settings.py` 未改。
