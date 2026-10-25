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
- TC-003（大 here-doc 後重跑）：兩邊各跑 `bash tests/confirm_cleanup_behind_heredoc_test.sh`，皆 rc=0、輸出 3 行；`diff`（時間數字遮罩後）零差異，末行都是 `all passed`，另有 `awk runs: 3, want 3` ok。該檔不在 diff 內。
- TC-004（cleanup 輸入記錄比對）：把 `hooks/confirm_cleanup.sh` 第 2 行插入「`__in=$(</dev/stdin)`、追加寫到記錄檔、再 `exec <<<"$__in"`」的副本（base 與 head 各一份，皆由 `git archive` 副本再改，不動 worktree），各跑一次 `confirm_cleanup_test.sh`（兩邊 rc=0）。記錄檔兩邊各 811 筆。每行先把 `/tmp/tmp.XXXX`（mktemp 隨機名）遮成 `/tmp/TMP`，再 `jq -S -c .`，`cmp` 零差異，沒有一行無法解析。變體鍵兩邊相同：`tool_name` 為 Bash 209／PowerShell 193／mcp__win__powershell 2／缺 407；頂層鍵集合 `tool_input`、`cwd,tool_input`、`tool_input,tool_name`、`cwd,tool_input,tool_name`；`tool_input` 內 `command` 809／`script_block` 2。
- TC-005（launch 輸入記錄比對）：同法，兩邊各 844 筆。其中 312 筆是 :1185-1195 那段一次性 python 產生的約 21 KB「filler line」大 here-doc；測試以 8 路背景並行呼叫 hook（base 就是這樣），錄製檔由多個行程同時 append，行會互相切斷、順序不定（base 與 head 都是，與編碼無關），無法逐行比，且它們的輸入由未改動的 python 區塊產生（TC-028）。其餘 532 筆（含 `tool_name:"Bash"`、`Edit`／`MultiEdit`／`Write`、`PowerShell`、`mcp__*`、`hook_event_name`、`cwd`、`content`／`file_path`／`new_string` 等非 `command` 鍵）：筆數 532＝532、順序相同、遮罩後 `jq -S -c .` 逐行 `cmp` 零差異。
- TC-030（cleanup no-jq 突變）：副本 head 版，hook 第 2 行加 `command -v jq >/dev/null 2>&1 || exit 0`（jq 不在就悄悄放行）。未突變：`(b) no jq + a real delete` ok (rc=2, no stdout)、`stderr names the fix` ok。突變後：`(b)` 變 `FAIL: rc=0 out=''`、`stderr names the fix` 變 `FAIL: stderr did not name both install commands`，另兩條（delete on a later line、truncate／unlink）也 FAIL，共 4 條 FAIL、exit 1；`(a) no jq + a harmless command - exit 0, no noise` 仍 `ok (rc=0, silent)`（新編碼沒有在 `nojq()` 內製造雜訊）。
- TC-031（launch no-jq 突變）：同法。未突變 no-jq 段全 ok。突變後 13 條 FAIL（`(b)` real launch、sbatch、ssh、stderr names the fix、egress_allow.tsv 的兩條 ask、Bash ssh 控制組、4 條 shapes BLOCKED），`(a)` 與各 passes 類對照仍 ok，exit 1。
- TC-021（範圍）指令輸出：
  - `git diff --name-only 50f696b HEAD` → `specs/hook-tests-jq/ledger.md`、`specs/hook-tests-jq/plan.md`、`specs/hook-tests-jq/test-case-overview.md`、`specs/hook-tests-jq/test-case.md`、`tests/confirm_cleanup_test.sh`、`tests/confirm_launch_test.sh`
  - `git diff 50f696b HEAD -- hooks | wc -c` → `0`
  - `git diff --stat 50f696b HEAD -- tests hooks` → `tests/confirm_cleanup_test.sh | 30 +++---`、`tests/confirm_launch_test.sh | 34 +++---`（hooks 無輸出）
  - `git diff --name-only 9fe249e HEAD`（9fe249e＝verifier 定案合約的 commit）→ `ledger.md`、`plan.md`（只加了 2026-10-25 的已知環境紅裁決）、兩個測試檔；`test-case.md`、`test-case-overview.md` 在 9fe249e 之後零改動；本任務沒有 `spec.md`。
- TC-023 計時（WSL，`git archive` 副本，同一台機器，base／head 交錯各連跑 3 次；同時有其他 worktree 的測試在跑，負載 3.5–8，所以另記 user 時間）：
  - cleanup 秒數（real）：base 51.4／52.7／52.5，中位數 **52.5 s**；head 28.2／28.9／29.6，中位數 **28.9 s**（少 45%）。user 中位數 41.9 s → 23.0 s。六次 rc 皆 0。
  - launch 秒數（real）：base 58.8／61.6／69.5，中位數 **61.6 s**；head 44.3／50.2／52.8，中位數 **50.2 s**（少 19%）。user 中位數 60.8 s → 56.0 s（約 8%）。launch 的 rc：base 1／0／0、head 0／1／1，rc=1 都是機器忙時的時間門檻（`slow (~1000 ms)`）類 FAIL，兩邊皆有，與編碼無關。
  - 說明：cleanup 少 ≥ 20%（符合）。launch real 少 19%、CPU 只少約 8%（< 20%），因為 launch 大部分時間花在不能換的一次性 python 區塊與 8 路並行的大 here-doc 區（TC-028、計畫「不做」）。速度不是通過條件。
- TC-025（不平行化）：head 的 diff 新增行 grep `&` 背景、`wait`、`xargs`、`parallel`、`--jobs` 零筆；TC-001／002 輸出逐行相同，案例順序與 base 一致。
- TC-026（不准動清單）：`git diff --stat 50f696b HEAD -- tests/run_all.sh tests/on_site_parallel_test.sh tests/lib tests/confirm_cleanup_behind_heredoc_test.sh tests/flow_skills_layout_test.sh .github` 輸出為空（零改動）；`run_all.sh` 沒動，故沒有 `--jobs`；兩個檔名沒變，`flow_skills_layout_test.sh` 在全套內通過。
- TC-028（範圍外 python 呼叫）：兩個測試檔 diff 的 hunk 起點（base 行號）cleanup 為 33 35 93 232 237 242 247 296 298 423 425 782 784 889 892，launch 為 67 366 371 383 389 423 429 442 449 624 792 805 813 820 864，皆落在 helper 內；cleanup 的 :119、:167（`bj()`）、:208-219、:261、:403、:599 與 launch 的 :1185-1195 不在其中，與 base 逐字相同。
- TC-029（無 migration）：diff 只含兩個測試檔與 specs 下文件，無資料結構、設定檔格式、資料內容或 migration 檔。
- 全套（abf-fast-suite）：123/124；唯一紅是 `platform_test.sh` 內的 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched`，即計畫 2026-10-25 07:35 裁決的已知環境紅（視同綠）。第一次全套曾有 3 條紅（機器忙時的時間門檻類），重跑後只剩這 1 條。
