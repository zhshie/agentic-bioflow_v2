# 轉送警告顯示細節（截斷標記、未列提醒、引號值、字界） progress ledger

## 進度
- [x] RED 提交：測試先行（POL-1..23、POL-bq、POL-back20；34 條失敗，原因都是缺功能）
- [x] GREEN 提交：`relay_env_warn` 改寫（第三參數 `empty`、左邊字界、`…`、未列行、引號值、64 KB 空值）；PEER 呼叫多傳 `empty`
- [x] `bash tests/confirm_launch_test.sh` 全綠（WSL）

## 既有斷言被改的 3 條（改前 -> 改後）
1. `TC-010 $S double-quoted value kept as written`：檢查 `'"qq1'` 且 `!qq1 rr2` -> 檢查 `'"qq1 rr2"'`
2. `TC-010 $S single-quoted value kept as written`：檢查 `"'qq1"` 且 `!qq1 rr2` -> 檢查 `"'qq1 rr2'"`
3. `TC-020 $S MY_ prefix still warns`（has，檢查 zzval）-> `TC-020 $S MY_ prefix is not a mention`（lacks）
`envbig` 既有限時（500/500/1500/1000/1000）一條未放寬。

## 決定與偏離
- 裁決二 1：字界集合反向定義，只有 `[A-Za-z0-9_]` 算「不是提到」；反引號、`{`、`$`、`=`、tab、換行、引號、`;&|(` 都算提到（POL-bq 測反引號仍警告且仍 ask）。視窗內用 `[a-zA-Z0-9_]`（在 LC_ALL=C 下，比 63 字元列舉快約 40%）；列出階段用顯式字母列表 `$wc`（不依賴 locale 的範圍）。
- 引號值收尾引號只在後面 119 字元內找（計畫寫 120；120 會讓含兩側引號的值長到 121 字元，違反「每處 120 字元」），其餘照計畫。
- 視窗迴圈裡「壞提到」的移除只在該視窗有提到（`${#gone} -lt ${#x}`）時才做，沒提到的視窗成本同舊版。
- 步數上限：往前 20 圈、往後 20 圈；用完即走「too many names that only end in V」輸出，不列原文（POL-23、POL-back20）。
- N=5 單數句、N>=6 `4 to N-1`；N<=4 無說明行。
- 空值只看最後一處（n<=3 時是第 n 處，n>3 時是最後一處）；超過 64 KB 時用 `${CMD%"$V="*}` 取最後一處，其前一字元是名字字元則不判斷。`RELAY_ENV_EMPTY=1` 只出現在 `[ "${3-}" = empty ]` 保護內（`hooks/confirm_launch.sh:418`；註解行 321 只是文字）。EXTRA 呼叫文字未動、不傳第三參數。
- 本機測 `python3` 是壞 stub，編輯用 `py`；測試一律在 WSL 跑。

## 證據
- `git diff --name-only origin/v3...HEAD`：hooks/confirm_launch.sh、tests/confirm_launch_test.sh、specs/relay-warning-polish/{ledger,plan,test-case,test-case-overview}.md（後三者是先前提交的計畫與測試案例）。`git diff origin/v3...HEAD -- scripts platform docs skills deploy commands hooks/hooks.json` 為空。
- `relay_env_warn` 本體：無 `$(`（只有 `$((`算術）、無 grep/jq/python/子行程；無逐字元迴圈。
- 成本（WSL，毫秒，舊 hook = origin/v3，新 = 本分支；各兩次）：
  - 1 MB 尾端一處：舊 663/647，新 582/603
  - 1 MB 8000 處：舊 645/703，新 約 800（本分支測試內 909/934，限時 1000）
  - 1 MB 8000 個 MY_ 壞提到：舊 644/673（舊版會警告），新 808/806（POL-22 測試內 862）
  - 100 KB 不含變數：舊 98/106，新 108/108
  - 8000 處的情況新版慢約 130 ms：每個有提到的視窗多一次移除（計畫裁決一已接受兩倍常數）；沒有提到的視窗與沒帶變數的指令不變慢。
