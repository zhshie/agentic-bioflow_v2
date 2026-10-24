# 轉送警告顯示細節（截斷標記、未列提醒、引號值） progress ledger

依計畫「裁決三」（取消左邊字界）重做。

## 進度
- [x] RED：測試依裁決三改（POL-5/15/22 翻轉；新增 POL-dash-e、POL-cl1..4、POL-lk-empty、POL-19b、POL-lk25；刪 POL-23/back20）；17 條失敗
- [x] GREEN：`relay_env_warn` 移除字界計數與跳過壞提到的掃描與 `too many names` 路徑；收尾引號後接 `) \` }` 不加 `…`
- [x] `bash tests/confirm_launch_test.sh` 全綠（WSL）；全套見 commit 後

## 既有斷言被改（2 條）
1. `TC-010 $S double-quoted value kept as written`：`'"qq1'` 且 `!qq1 rr2` -> `'"qq1 rr2"'`
2. `TC-010 $S single-quoted value kept as written`：`"'qq1"` 且 `!qq1 rr2` -> `"'qq1 rr2'"`
`TC-020 $S MY_ prefix still warns` 與 base 一字不差。`envbig` 既有限時未放寬。

## 決定
- 跳脫引號 `\"` 不處理，為已知顯示限制（閘門仍印整條指令）。
- 64 KB 以位元組計（`LC_ALL=C` 下取長度），註解已寫明，判斷式 `${#CMD} -gt 65536` 同 base。
- 收尾引號後面看 119 字元內找（含兩側引號共 ≤120 字元）。
- `RELAY_ENV_EMPTY=1` 只在 `[ "${3-}" = empty ]` 保護內；EXTRA 呼叫文字未動。
- 函式本體無 `$(`（只有 `$((`）、無 grep/jq/python、無逐字元迴圈。
- 本機 `python3` 為壞 stub，編輯用 `py`；測試在 WSL 跑。
