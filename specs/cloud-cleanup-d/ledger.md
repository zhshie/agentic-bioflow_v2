# Google Batch 清理：先列再 gcloud storage rm progress ledger

- [x] 失敗先行測試 `platform/tests/test_station_clean_gcb.py`（RED commit 0dacaa2）
- [x] `platform/abf_station/clean.py`：`_clean_gcb`、`_head_gone`、`_gcloud_env`、`run_clean` 分派（GREEN）
- [x] 四處既有斷言更新（以前／以後／理由）：
  - `test_station_clean.py::test_tc013_...`：以前＝Google Batch 內容包被拒「尚未支援（cloud-cleanup-d）」；以後＝交給 `_clean_gcb`，這個測試部署的 run 資料夾不是 `_gcb_runs/<run>`，所以被「專屬資料夾」規則拒絕且仍零呼叫；理由：d 片接手。
  - `test_station_clean.py::test_tc073_...`：以前＝`clean.py` 全文不得出現 `run_fixed`；以後＝`run_fixed` 只准在 `_clean_gcb`、`_head_gone` 兩個函式內（ast 找範圍），`import subprocess`／`os.system`／`os.popen`／`start_detached` 仍禁，`ctx.site.call(` 仍恰一次；理由：裁決二第 1 點。
  - `test_gcb_ce.py::test_nothing_of_the_later_slices_exists`：以前＝所有檔都不得含四個字樣；以後＝`abf_station/clean.py` 只檢查前三個字樣（逐字比對，不用含 `buckets create` 的正則，以免 `test_cloud_upload` 剖析時抓錯那一行），其餘檔照舊；正則那一行字面未動。
  - `test_cloud_upload.py::test_the_scope_nail_...`：`options == [四個字樣]` 未動；最後的迴圈對 `abf_station/clean.py` 只檢查前三個字樣。

## 官方說明核對（2026-10-25，executor；網址為 gcloud 參考頁與 Cloud Storage 文件）
工作環境沒有 `gcloud`，所以只能讀官方頁面，沒有實測。

1. `gcloud storage rm --recursive`（https://cloud.google.com/sdk/gcloud/reference/storage/rm）：「Recursively delete the contents of buckets or directories that match the path expression」；`--project` 是 gcloud 全域旗標，`rm` 可用；`--continue-on-error`、`--all-versions` 本片都沒加。**重要**：頁面寫明「This option implies the --all-versions option」——`--recursive` 對開了物件版本控制的桶會連非現行版本一起刪（要只刪現行版本得用 `**` 萬用字元；本片不用，因為計畫規定 `--recursive`）。
2. **尾端斜線是否只刪該前綴、不波及 `work2/`、`work-keep`：官方參考頁沒有明文。** 頁面只說「directories that match the path expression」；目錄語意暗示 `work/` 不會吃到 `work2/`，但沒有逐字保證。所以程式不依賴它：刪之前用同一個網址（含尾端斜線）先 `ls --recursive`，每一行都必須以 `…/work/` 開頭，否則拒絕不刪（TC-042）。**f 片的真桶驗收必須實測這一點**（含 `work2/`、`work-keep` 的測試桶）。
3. `ls --recursive` 對不存在前綴的結束碼與訊息：（https://cloud.google.com/sdk/gcloud/reference/storage/ls）**參考頁沒寫。** 程式採保守判法：非零結束碼且輸出含 `matched no objects` 或 `No URLs matched`（不分大小寫；gcloud 的慣用訊息「One or more URLs matched no objects」）才當「已經沒有東西」；其他任何非零一律 `error`、不刪。若真實訊息不同，結果是「報錯、什麼都沒刪」（安全方向）。**需在 f 片真桶確認訊息。**
4. 版本控制／軟刪除（供 f 片文案，https://cloud.google.com/storage/docs/soft-delete 、https://cloud.google.com/storage/docs/object-versioning）：
   - 軟刪除：新建的桶預設保留 7 天（可設 7 至 90 天，0 為關閉）；「Soft-deleted objects continue to accrue storage charges until their retention period expires」——刪除後保留期內**仍計費、仍可還原**。所以 f 片畫面不能寫「立刻停止計費」或「無法還原」，除非維護者確認自己的桶已關閉軟刪除。
   - 物件版本控制：刪除現行版本會留下非現行版本，直到被明確移除；`--recursive` 隱含 `--all-versions`，所以會一併刪（見第 1 點）。
   - 本片程式沒有任何清除軟刪除物件或舊版本的動作。
5. `ps` 沿用 `gcb_launch.run_cancel` 已在用的形式（`ps -o user= -o args= -p <pid>`，20 秒），無新假設。

## 要告訴 f 片／維護者的疑慮
- 計畫與 TC-047／TC-052 規定的環境變數是 `GOOGLE_APPLICATION_CREDENTIALS`（與 `gcb_launch._head_env` 相同）。但預檢（`gcb_preflight._gcloud_env`）用的是 `CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE`，那才是 gcloud CLI 認的金鑰檔變數；`GOOGLE_APPLICATION_CREDENTIALS` 主要給函式庫用。若真桶驗收時 `gcloud storage ls/rm` 沒用到這把金鑰（改用機器上已登入的帳號），要在 f 片改環境變數（需同時改 TC-047／TC-052）。我照合約做，沒有擅自多加變數。

## git diff --stat（對基底 `git merge-base HEAD origin/v3`）
本片改的檔（其餘 specs/ 檔是 developer-agent／verifier 先前的 commit）：
```
 platform/abf_station/clean.py            | 121 ++++++-
 platform/tests/test_cloud_upload.py      |   3 +
 platform/tests/test_gcb_ce.py            |   3 +
 platform/tests/test_station_clean.py     |  20 +-
 platform/tests/test_station_clean_gcb.py | 510 +++
 specs/cloud-cleanup-d/ledger.md
```
`launch.py`、`gcb_launch.py`、`cancel.py`、`gcb_preflight.py`、`site.py`、`rules.py`、`handlers.py`、`test_gcb_launch.py` 與 `abf_platform/*`、`abf_launch/*` 未動。不需要 migration（沒碰資料結構）。
