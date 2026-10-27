# 引導式送出第二刀：參數表預檢、最新版本、流程圖連結、樣本表欄位、參數分組表 progress ledger

- [x] 失敗先行測試（`platform/tests/test_web_guided_launch_2.py`，commit `RED:`）：G01～G10 與 TC-001～TC-110 的自動項；假資料用真的 `actions._pf_view` 讀 fixtures。
- [x] `web_launch.py`（新）：第 1 步參數表列、第 2 步最新版本、第 3 步流程圖連結、第 4 步樣本表欄位、第 5 步分組表、`fields_of`／`merge_params`／`types_of`、`why`。
- [x] `web_board.py`：`render_launch` 加 `files`／`image`／`latest` 與呼叫點、`launch_checks` 加參數表那一列、`GUIDED` 的 `g2_*` 字串、樣式表新 class（只用 token）。
- [x] `web.py`：`/launch` GET 取資料（`launch_files`）、`p.*` 併入、`GET /launch/diagram`、POST 併入 `p.*`、檔頭路由清單。
- [x] `docs/PLATFORM.md`、`docs/TESTING.md` 補第二刀。

## 既有斷言的改動（舊→新＋理由）

| 檔案 | 舊 | 新 | 理由 |
|---|---|---|---|
| `test_web_guided_launch.py` `test_gl01_seven_numbered_steps` | 第 3 步含「之後開放」 | 第 3 步含「選好管線與版本後顯示」 | 計畫作法 5：第 3 步不再是「之後開放」 |
| `test_web_guided_launch.py` `test_gl03_...` | 第 1 步 `chk` 列數 `== 4` | `== 5` | 計畫裁決 12：第 1 步多了參數表那一列 |
| 同上 | 第 1 步含「之後開放」 | 第 1 步含「讀取中」 | 同上：那一列換成真的檢查列；站台代理還沒回答時顯示讀取中 |
| `test_web_guided_launch.py` `test_gl07_param_routes` | 第 5 步含「之後開放」 | 第 5 步含「讀取中」且不含「之後開放」 | 計畫作法 8、裁決 9：分組表位置換成讀取中／分組表 |
| `test_owner_binding.py` `test_tc068` | 路由集合不含 `/launch/diagram` | 加 `"/launch/diagram"` | 計畫範圍：新路由 |
| `test_confirm_page.py` `test_tcg04_g05_g06_...` | 路由清單不含 `/launch/diagram` | 加 `("/launch/diagram", ("GET", "HEAD"))` | 同 tc068：新路由（計畫沒點名這支，機械式跟著新路由） |
| `test_web_board.py` `test_tch11_read_only` | 路由清單不含 `/launch/diagram` | 加 `("/launch/diagram", ("GET", "HEAD"))` | 同上：新路由 |
| `test_clean_page.py` 的 `BASE_CONFIRM`／`BASE_EXPIRED`／`BASE_POST`／`BASE_BOARD`／`BASE_STYLE` | 頁面雜湊（含整份樣式表）舊值 | 重新釘住的新值 | 計畫作法允許「樣式表加必要的 class」（分組表 390 px 上下排要 media query）；每頁都內嵌那一份樣式表，所以雜湊必變。只有樣式表不同（沒有改任何頁面文字）；先前 cloud-cleanup-e 的 GREEN 也是這樣重新釘住 |

沒動：第 2 步「搜尋全部 nf-core 之後開放」與第 4 步「預覽 之後開放」的斷言。

## 實作中的決定（計畫沒寫死的）

- 送出被擋回的頁面（POST 400）呼叫 `pipeline_files`／`latest_release` 時 `enqueue=False`，且不加 15 秒自動更新：既有測試 `test_gl09`、`test_tc029_tc033` 要求「驗證失敗不排任何工作」，且 POST 的回應沒有可重問的網址。
- `jobs.JobRefused` 的「沒有在線代理」句子是「English (中文): English (中文)」的英文在前形狀，`web_board.plain_reason` 會切錯；`web_launch.why` 先處理這一形（英文頁取英文、中文頁取中文），再交給 `plain_reason`。沒改 `jobs.py`。
- 流程圖大小顯示位元組數（總覽「我不確定」第 1 點）；stale-cache 時間格式用 `web_board.taipei_time`（`MM-DD HH:mm`）。
- `p.*` 併入後，textarea 顯示併入後的文字，`p.*` 輸入框不回填（避免 textarea 優先把之後的修改蓋掉）。
- 參數名不是合法的名稱（`PARAM_KEY`）的 `p.*` 欄位直接忽略。
