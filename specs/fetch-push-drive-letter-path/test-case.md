# 測試案例：fetch.sh／push.sh 把 C:/… 本機路徑轉成 rsync 看得懂的 /c/…

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Language: 繁體中文; identifiers and file paths stay as they are.
-->

**規格**：`specs/fetch-push-drive-letter-path/plan.md`（本任務沒有 spec.md，計畫的「目標／作法／失敗先行測試／不做／裁決 D1–D3」就是規格；計畫正文與 D3 衝突時，以 D3 為準）　**總覽**：`test-case-overview.md`

類型只有三種：功能、例外、不在範圍（意義同範本）。

**怎麼讀這份表**

- 「rsync」是 `fetch.sh`／`push.sh` 背後真正搬檔案的程式。它有個規矩：引數裡出現「字母＋冒號」（例如 `C:/…`）就當成「某台遠端電腦上的路徑」。這就是本任務要避開的坑：本機的 `C:/Users/me/out` 被誤判成遠端。
- 所有自動測試都用「假 rsync」（只把收到的每個引數各寫一行到 `$TMP/rsync.args` 的小腳本）和「假 ssh」，在 `$TMP` 內 `cd` 後執行，所以資料夾 `C:/Users/me/...` 在 Linux 只是普通資料夾。不需要 Windows、不連網。
- 「最後一個引數」＝ `rsync.args` 的最後一行；「倒數第二個」＝來源端。
- 自動測試只在 Linux／WSL 跑（D3(d)）。「閱卷者檢查」＝閱卷者直接讀程式或 diff 確認，沒有對應的自動測試。
- 測試機沒有 `cygpath`（Linux 本來就沒有）。轉換結果寫成 `/c/…` 小寫、無冒號。
- 以下 fetch 的前置條件都是：`settings 'reach: ssh' 'site_host: me@example.org'`、`mkssh 26000`（站台回報 26 MB）、遠端路徑 `/work/runs/myrun/results`；指令是 `fetch.sh /work/runs/myrun/results <本機目的地>`。

## User Story 1 — fetch.sh：本機目的地是磁碟機寫法時，不再被 rsync 當成遠端（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；作法 1、2；失敗先行測試 1 | 功能 | 如上；記錄用假 rsync；`cd "$TMP"` | `fetch.sh /work/runs/myrun/results 'C:/Users/me/out/results'` | 退出碼 0；rsync 收到的最後一個引數正好是 `/c/Users/me/out/`（含尾斜線）；沒有任何本機端引數以「字母＋冒號」開頭 | 自動：`tests/fetch_test.sh` |
| TC-002 | 作法 1、2；失敗先行測試 2；D3(c) | 功能 | 同上 | 目的地是反斜線寫法，bash 單引號逐字 `'D:\data\out\results'`（單反斜線） | 最後一個引數正好是 `/d/data/out/`，且不匹配 `^[A-Za-z]:` | 自動：`tests/fetch_test.sh` |
| TC-003 | 作法 1（其他路徑原樣）；失敗先行測試 3 | 功能 | 同上 | 目的地 `/tmp/x/results` | 最後一個引數正好是 `/tmp/x/`（與修改前逐字相同） | 自動：`tests/fetch_test.sh` |
| TC-004 | 作法 1；失敗先行測試 3 | 功能 | 同上 | 目的地相對路徑 `rel/results` | 最後一個引數正好是 `rel/` | 自動：`tests/fetch_test.sh` |
| TC-005 | D3(b)（磁碟機根目錄，照收為必過條件） | 功能 | 同上 | 目的地 `'C:/results'` | 最後一個引數正好是 `/c/`，不以「字母＋冒號」開頭 | 自動：`tests/fetch_test.sh` |
| TC-006 | D3(b) | 功能 | 同上 | 目的地 `'C:\results'`（單反斜線） | 最後一個引數正好是 `/c/` | 自動：`tests/fetch_test.sh` |
| TC-007 | 作法 1（regex `[A-Za-z]`、代號轉小寫） | 功能 | 同上 | 目的地 `'c:/Users/me/out/results'`（小寫代號） | 最後一個引數正好是 `/c/Users/me/out/` | 自動：`tests/fetch_test.sh` |
| TC-008 | 作法 1（已是 `/c/…` 的原樣輸出） | 功能 | 同上 | 目的地 `/c/Users/me/out/results` | 最後一個引數正好是 `/c/Users/me/out/`，沒有被改成別的樣子（如 `/c/c/…`） | 自動：`tests/fetch_test.sh` |
| TC-009 | 作法 1（`./C:foo` 原樣輸出） | 功能 | 同上 | 目的地 `./C:foo/results` | 最後一個引數正好是 `./C:foo/`（開頭的 `./` 讓它不是遠端，不得被當磁碟機轉換） | 自動：`tests/fetch_test.sh` |
| TC-010 | 作法 2（stdout 用原始路徑）；失敗先行測試 4 | 功能 | 同 TC-001 | 目的地 `'C:/Users/me/out/results'`，看輸出最後一行 | 最後一行正好是使用者給的 `C:/Users/me/out/results`，不是 `/c/…` | 自動：`tests/fetch_test.sh` |
| TC-011 | 作法 2、5（`--dry-run` 輸出格式不變）；失敗先行測試 4 | 功能 | 同 TC-001 | `fetch.sh --dry-run /work/runs/myrun/results 'C:/Users/me/out/results'` | 退出碼 0；輸出含原始 `C:/Users/me/out/results`、不含 `/c/Users`；格式與修改前相同（`ssh me@example.org`、遠端路徑、本機路徑、`(26 MB)`）；假 rsync 沒有被呼叫（`rsync.args` 不存在或為空） | 自動：`tests/fetch_test.sh` |
| TC-012 | 作法 2（遠端端不動）；失敗先行測試 5 | 功能 | 同 TC-001 | 目的地 `'C:/Users/me/out/results'`，檢查全部引數 | 引數中存在一行正好是 `me@example.org:/work/runs/myrun/results` | 自動：`tests/fetch_test.sh` |
| TC-013 | 作法 2（`mkdir -p` 用原始路徑） | 功能 | 同 TC-001；`$TMP` 內沒有 `C:` 資料夾 | 同 TC-001 | 退出碼 0；`$TMP/C:/Users/me/out` 這個相對資料夾存在（若 mkdir 誤用 `/c/…`，在 Linux 會建立失敗而退出碼 2） | 自動：`tests/fetch_test.sh` |
| TC-014 | 作法 5（錯誤訊息、退出碼不變） | 例外 | 同 TC-001，但假 rsync 以退出碼 1 結束 | 目的地 `'C:/Users/me/out/results'` | 退出碼 2；訊息含 `the transfer of '/work/runs/myrun/results' failed.`，與修改前逐字相同 | 自動：`tests/fetch_test.sh` |

## User Story 2 — push.sh：本機來源是磁碟機寫法時，不再被 rsync 當成遠端（優先度 P1）

push 的前置條件：`settings 'reach: ssh' 'site_host: me@example.org'`，記錄用假 rsync，假 ssh，`cd "$TMP"`；站台路徑 `/work/runs/myrun/rawdata`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 目標；作法 3；失敗先行測試 6 | 功能 | 如上；`$TMP` 內有相對資料夾 `C:/Users/me/reads`，內含一個小檔 | `push.sh 'C:/Users/me/reads' /work/runs/myrun/rawdata` | 退出碼 0；rsync 的倒數第二個引數（來源）正好是 `/c/Users/me/reads/`（尾斜線保留） | 自動：`tests/push_test.sh` |
| TC-016 | 作法 3（`$to` 不動）；失敗先行測試 6 | 功能 | 同 TC-015 | 同 TC-015，看最後一個引數 | 正好是 `me@example.org:/work/runs/myrun/rawdata/` | 自動：`tests/push_test.sh` |
| TC-017 | 作法 3；失敗先行測試 7 | 功能 | `$TMP` 內有檔案 `C:/Users/me/a.fastq.gz` | `push.sh 'C:/Users/me/a.fastq.gz' /work/runs/myrun/rawdata/a.fastq.gz` | 來源引數正好是 `/c/Users/me/a.fastq.gz`（單一檔案，沒有尾斜線）；最後一個引數仍是 `me@example.org:` 加原本的站台路徑 | 自動：`tests/push_test.sh` |
| TC-018 | 作法 1、3；D3(e)（push 反斜線來源） | 功能 | `$TMP` 內有一個名字就叫 `C:\Users\me\reads` 的資料夾（Linux 允許名稱含反斜線），內含小檔 | `push.sh 'C:\Users\me\reads' /work/runs/myrun/rawdata` | 來源引數正好是 `/c/Users/me/reads/`，不匹配 `^[A-Za-z]:` | 自動：`tests/push_test.sh` |
| TC-019 | 作法 3；失敗先行測試 8（控制組） | 功能 | 既有 `$TMP/reads` 資料夾 | `push.sh "$TMP/reads" /work/runs/myrun/rawdata` | 來源引數正好是 `$TMP/reads/`、最後引數是 `me@example.org:/work/runs/myrun/rawdata/`，與修改前逐字相同 | 自動：`tests/push_test.sh` |
| TC-020 | 作法 1（其他路徑原樣） | 功能 | `$TMP/reads/a.fastq.gz` 單一檔案 | `push.sh "$TMP/reads/a.fastq.gz" /work/runs/myrun/rawdata/a.fastq.gz` | 來源引數正好是 `$TMP/reads/a.fastq.gz`（沒有尾斜線、沒被改） | 自動：`tests/push_test.sh` |
| TC-021 | 作法 5（`--dry-run` 輸出不變） | 功能 | 同 TC-015 | `push.sh --dry-run 'C:/Users/me/reads' /work/runs/myrun/rawdata` | 輸出含原始 `C:/Users/me/reads` 與 `ssh me@example.org:/work/runs/myrun/rawdata`，格式與修改前相同；不含 `/c/Users`；假 rsync 沒被呼叫 | 自動：`tests/push_test.sh` |
| TC-022 | 作法 3（stdout 不變） | 功能 | 同 TC-015 | 同 TC-015，看輸出最後一行 | 正好是 `/work/runs/myrun/rawdata` | 自動：`tests/push_test.sh` |
| TC-023 | 作法 5（錯誤訊息、退出碼不變） | 例外 | 同 TC-015，但假 rsync 以退出碼 1 結束 | `push.sh 'C:/Users/me/reads' /work/runs/myrun/rawdata` | 退出碼 2；訊息以 `the transfer of 'C:/Users/me/reads' failed.` 開頭並含 `--partial`，與修改前相同 | 自動：`tests/push_test.sh` |
| TC-024 | 作法 3（存在檢查先於轉換）；作法 5 | 例外 | `$TMP` 內沒有 `C:/Users/me/nope` | `push.sh 'C:/Users/me/nope' /work/runs/myrun/rawdata` | 退出碼 2；訊息含 `'C:/Users/me/nope' does not exist on this machine.`（顯示使用者給的原始路徑）；假 rsync 沒被呼叫 | 自動：`tests/push_test.sh` |

## User Story 3 — 兩支腳本一致、改動範圍守得住（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 作法 4；失敗先行測試 9 | 功能 | 兩支腳本都已改好 | 用 `sed -n '/^rsync_local_path()/,/^}/p'` 從 `scripts/fetch.sh`、`scripts/push.sh` 各抽出函式本體，互相 `diff` | 兩份抽出的內容都不是空的（各至少一行），且 `diff` 完全相同（兩邊都沒有函式時不得算通過） | 自動：`tests/fetch_test.sh` 或 `tests/push_test.sh`（擇一） |
| TC-026 | 不做：不改 fetch 的 tar 後備；作法 2 | 不在範圍 | 同 TC-001，但 `FETCH_RSYNC_BIN` 指到不存在的檔案（強制走 tar\|ssh）；假 ssh 回空的 gzip（沿用既有 `mktar_fallback_ssh`） | 目的地 `'C:/Users/me/out/results'` | 退出碼 0；tar 後備確實跑了（`tar_fallback_invoked` 存在）；輸出最後一行是原始 `C:/Users/me/out/results`；沒有任何東西被寫到 `/c/…`（若 tar 或 mkdir 誤用轉換後路徑，Linux 上會失敗而不是 0） | 自動：`tests/fetch_test.sh` |
| TC-027 | 不做：不改 push 的 tar 後備 | 不在範圍 | 同 TC-015，但 `PUSH_RSYNC_BIN` 指到不存在的檔案；假 ssh 沿用既有 `mktar_fallback_ssh` | `push.sh 'C:/Users/me/reads' /work/runs/myrun/rawdata` | 退出碼 0；假 ssh 的紀錄顯示遠端指令仍是原本的 `mkdir -p … && tar xzf - -C …`；本機 tar 讀的是原始相對資料夾（誤用 `/c/…` 會讓 Linux 上失敗） | 自動：`tests/push_test.sh` |
| TC-028 | 不做：WSL 的 `/mnt/c/…` 不處理（D1 ①） | 不在範圍 | 同 TC-001、TC-015 | fetch 目的地 `'C:/Users/me/out/results'`、push 來源 `'C:/Users/me/reads'` | 交給 rsync 的本機端引數都不含 `/mnt/`；轉換結果只有 `/c/…` 形式 | 自動：`tests/fetch_test.sh`、`tests/push_test.sh` |
| TC-029 | 不做：不處理 UNC（`\\server\share`） | 不在範圍 | `$TMP` 內有名字就叫 `\\server\share\reads` 的資料夾 | `push.sh '\\server\share\reads' /work/runs/myrun/rawdata` | 來源引數正好是 `\\server\share\reads/`（只多原本就有的尾斜線，沒被轉成 `/c/…` 或任何別的樣子） | 自動：`tests/push_test.sh` |
| TC-030 | 不做：不處理 UNC | 不在範圍 | 同 TC-001 | fetch 目的地 `'//server/share/out/results'` | 最後一個引數正好等於 `"$(dirname '//server/share/out/results')/"`（即修改前的算法結果），沒有被當磁碟機轉換 | 自動：`tests/fetch_test.sh` |
| TC-031 | 範圍：檔案（只准改這些）；禁止碰 `scripts/utils/*`、`hooks/`、`platform/**`、`.github/` 等；「一項一個變更」 | 不在範圍 | 實作完成 | 閱卷者執行 `git diff --name-only origin/v3...HEAD`（再加上未提交的 `git status --porcelain`） | 只出現 `scripts/fetch.sh`、`scripts/push.sh`、`tests/fetch_test.sh`、`tests/push_test.sh`、`specs/fetch-push-drive-letter-path/ledger.md`；`specs/.../plan.md` 在本任務開始前就已提交，實作期間不得再被改 | 閱卷者檢查 |
| TC-032 | 作法 5；「不處理 #23 其他幾項」；一項一個變更 | 不在範圍 | 實作完成 | 閱卷者讀 `scripts/fetch.sh`、`scripts/push.sh` 對 base 的 diff | 腳本裡只有：新增 `rsync_local_path()` 一個函式，加上 fetch 的目的地引數與 push 的來源引數兩處呼叫；沒有改任何錯誤訊息文字、`--dry-run` 輸出、退出碼、tar 後備、遠端端引數 | 閱卷者檢查 |
| TC-033 | 作法 1（有 cygpath 就優先用）；D3(d) | 功能 | 實作完成 | 閱卷者讀兩支腳本的 `rsync_local_path()` | 先 `command -v cygpath` 且 `cygpath -u -- "$p"` 成功時採用其結果；否則才手動轉換（代號轉小寫、去冒號、反斜線換正斜線、前面補 `/`）；regex 是 `^[A-Za-z]:([\\/]|$)`；非磁碟機寫法原樣輸出。（這條分支在 CI 不測，D3(d) 已承認） | 閱卷者檢查 |
| TC-034 | 範圍：既有斷言原樣；失敗先行測試 3 | 功能 | 實作完成 | 閱卷者比對 `tests/fetch_test.sh`、`tests/push_test.sh` 與 base 的 diff；各跑一次 `bash tests/fetch_test.sh`、`bash tests/push_test.sh` | diff 只有新增行，沒有刪除或修改既有斷言；既有每一條（含 `a real fetch prints the local path`）仍是 ok；兩檔結尾 `all passed` | 閱卷者檢查 |
| TC-035 | 完成標準：沒有新增相依、沒有 `nohup`／`setsid`；不新增共用輔助檔 | 不在範圍 | 實作完成 | 閱卷者搜尋 diff 中新增行 | 沒有新的外部指令相依（`cygpath` 只在 `command -v` 通過後使用）；沒有 `nohup`、`setsid`；沒有 skills／commands 字樣變動；沒有新檔案進 `scripts/utils/` | 閱卷者檢查 |
| TC-036 | 維護者原話：不得宣稱已證實為唯一原因；D1 ①、D2 | 功能 | 實作完成 | 閱卷者讀 `specs/fetch-push-drive-letter-path/ledger.md` 與兩支腳本新增的註解 | ledger 明寫「根因是推論、未在 Windows 重現」與「WSL `/mnt/c/…` 未量測」；腳本註解與測試註解沒有任何「已證實這就是 #23 第 5 項原因」的說法 | 閱卷者檢查 |
| TC-037 | D3(d)（MSYS／Cygwin 略過新斷言） | 例外 | 在 Git Bash（`uname -s` 開頭 `MINGW`）執行 | `bash tests/fetch_test.sh`、`bash tests/push_test.sh` | 新增的磁碟機斷言整段略過，印出一行 `note: drive-letter assertions run on Linux/WSL only`；既有斷言照跑；不算失敗，結尾仍 `all passed`、退出碼 0 | 閱卷者檢查 |

## 憲法與安全網

本任務動到 Windows Git Bash 的路徑處理，碰到原則 II（無寫死路徑、指令層不具名站台）與原則 V（不要求使用者搬資料夾）。安全網（hooks／gates）本任務不碰，故無相關 TC。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-038 | 第 3 條：不寫死個人路徑 | 功能 | 實作完成 | `bash tests/no_hardcoded_paths.sh` | 通過；新增的 `C:/Users/me/…`、`/c/Users/me/…` 範例字串沒有讓檢查變紅（若檢查會掃到，executor 須改用不違規的範例，而不是放寬檢查） | 自動：`tests/no_hardcoded_paths.sh` |
| TC-039 | 第 4 條：指令層不具名排程器等站台屬性 | 功能 | 實作完成 | `bash tests/command_layer_is_site_neutral.sh` | 通過 | 自動：`tests/command_layer_is_site_neutral.sh` |
| TC-040 | 第 11 條：使用者在哪個資料夾都能用；腳本自己定位 | 功能 | 實作完成 | `bash tests/path_shapes_test.sh`；並確認兩支腳本仍以 `${BASH_SOURCE[0]}` 定位、新函式沒有用 `pwd` 推導路徑 | 通過；使用者給 `C:\…`／`C:/…` 不再需要換寫法才能用 | 自動：`tests/path_shapes_test.sh` |

<!--
Rules for the writer:
- Every requirement, 失敗先行測試 1–9 and every 不做 item maps to at least one TC.
- IDs are never renumbered after approval.
-->
