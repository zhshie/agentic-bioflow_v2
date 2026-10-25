# 兩支最慢的 hook 測試改用 jq 編解碼 progress ledger

- [x] 實作（commit 621ca75）：兩檔 helper 的編碼改 `jq -cn --arg`，解碼改 jq；decision 欄位 `| tr -d '\r'`，reason 不去 CR；嚴格版（缺 `hookSpecificOutput` 即錯、不給 warn）用在原本 `['hookSpecificOutput']` 的 helper，寬鬆版 `// ""` 用在原本 `.get(...,'')` 的 helper。範圍外行（`bj()`、:119、:208-219、:261、:403、:599、launch 的 :1185-1195 等）未動。

## 證據（WSL，`git archive` 副本 ~/hk/base 與 ~/hk/head）
- TC-001/002（輸出比對）：cleanup base 與 head 皆 `all passed`，`diff` 只差一行時間數字（`1 s` vs `0 s`）。launch 兩邊都有同幾條 `slow (~1000 ms)` 的時間門檻 FAIL（TC-051 / POL-22，機器負載造成，base 4 條、head 2 條，與編碼無關）；其餘逐行相同，差異只有 ms 數字。
- TC-006 案例數：cleanup `^t "` 324／案例呼叫行 112，launch 139／181，base 與 head 相同。
- TC-010/T6：中文、`"`、`\`、`\r\n`、單引號、`$`、反引號 經 jq 編碼後 `jq -e .` 可解析、`.tool_input.command` 逐字還原，且與 python 編碼 `jq -S -c .` 正規化後相同。
- 突變（副本 tests+hooks，head 版測試）：
  - TC-019 對照：未突變 810 ok、0 fail。
  - TC-011 hook 只輸出 `{}`：809 failed、0 條 `ok (warn)`，exit 1。
  - TC-012 全放行：597 failed（只剩 pass 類 213 條 ok），exit 1。
  - TC-013 輸出 garbage：809 failed、0 條 `ok (warn)`。
  - TC-014 輸出 `{"hookSpecificOutput":{}}`：`ok (warn)` 4 條，與 base 相同。
  - TC-020 永遠 deny：pass／warn 類 0 條 ok。
  - TC-015 launch 全放行：405 failed；TC-016 `{}`：356 failed；TC-017 allow：374 failed；TC-018 ask 無 reason：`reason did not contain the full command` 4 條、`did not name on_site.sh` 28 條。皆 exit 1。
- TC-021/027：`git diff --name-only 50f696b HEAD` 只有兩個測試檔、ledger 與合約檔；`git diff 50f696b HEAD -- hooks` 為空。
- TC-023 計時（單次，機器有他人負載，雜訊大）：cleanup base 83 s，head 37 s（-55%）；launch base 77 s，head 60 s。未做 3 次中位數。
- 全套（abf-fast-suite）：123/124；唯一紅是 `platform_test.sh` 內的 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched`，即計畫 2026-10-25 07:35 裁決的已知環境紅（視同綠）。第一次全套曾有 3 條紅（機器忙時的時間門檻類），重跑後只剩這 1 條。
