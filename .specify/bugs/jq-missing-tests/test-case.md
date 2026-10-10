# 測試案例：沒有 jq 時，安全閘門不放行；測試跑不動時要說清楚（issue #70）

**規格**：`.specify/bugs/jq-missing-tests/assessment.md`（Bug，無 spec.md）　**總覽**：`test-case-overview.md`

issue #70 的兩個要求就是這份考卷的依據，沒有維護者的範例（A 級）：(a) 證明沒有 jq 時閘門不會放行；(b) 有一個測試在 PATH 上拿掉 jq 的情況下跑閘門。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

「exit 2」是 Claude Code 的規矩：閘門回 2 就代表這個指令被擋下。「exit 0」代表放行。

## 一、沒有 jq 時閘門仍然擋人（新檔 `tests/gates_without_jq_test.sh`，要求 (a)(b)）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | issue #70 要求 (a)；assessment 表 第 1 列 | 例外 | PATH 上看不到 jq | 把 `rm -rf results` 餵給 `hooks/confirm_cleanup.sh` | exit 2，stderr 有 `BLOCKED` 與「jq is missing」 | 自動：`tests/gates_without_jq_test.sh` |
| TC-002 | 要求 (a)；表 第 2 列 | 例外 | 同上 | 餵 `ssh u@host rm -rf /work/results` 給 `confirm_cleanup.sh` | exit 2，stderr 有 `BLOCKED` | 自動：`tests/gates_without_jq_test.sh` |
| TC-003 | 表 第 3 列（沒東西要擋，是設計，issue #15） | 功能 | 同上 | 餵 `ls -la` 給 `confirm_cleanup.sh` | exit 0，不被擋 | 自動：`tests/gates_without_jq_test.sh` |
| TC-004 | 要求 (a)；表 第 4 列 | 例外 | 同上 | 餵 `tw launch nf-core/rnaseq` 給 `hooks/confirm_launch.sh` | exit 2，stderr 有 `BLOCKED` | 自動：`tests/gates_without_jq_test.sh` |
| TC-005 | 要求 (a)；表 第 5 列 | 例外 | 同上 | 餵 `nextflow run nf-core/rnaseq -profile slurm` 給 `confirm_launch.sh` | exit 2，stderr 有 `BLOCKED` | 自動：`tests/gates_without_jq_test.sh` |
| TC-006 | 要求 (a)；表 第 6 列 | 例外 | 同上 | 餵 `ssh u@host sbatch job.sh` 給 `confirm_launch.sh` | exit 2，stderr 有 `BLOCKED` | 自動：`tests/gates_without_jq_test.sh` |
| TC-007 | 要求 (a)；表 第 7 列 | 例外 | 同上 | 餵 `ssh -o BatchMode=yes -F jump.cfg u@node01 squeue` 給 `confirm_launch.sh` | exit 2，stderr 有 `BLOCKED`（連唯讀的 squeue 也不放行，因為沒 jq 無法判斷） | 自動：`tests/gates_without_jq_test.sh` |
| TC-008 | 要求 (a)；表 第 8 列 | 例外 | 同上 | 對 `hooks/confirm_walkthrough.sh` 餵一個把 `tower_access_token: ...` 寫進 `params.yaml` 的 Write 動作 | exit 2，stderr 有 `BLOCKED` | 自動：`tests/gates_without_jq_test.sh` |
| TC-009 | 要求 (a)；表 第 9 列 | 例外 | 同上 | 餵 `echo tower_access_token: ... >> params.yaml` 給 `confirm_walkthrough.sh` | exit 2，stderr 有 `BLOCKED` | 自動：`tests/gates_without_jq_test.sh` |
| TC-010 | 要求 (a)；表 第 10 列 | 例外 | 同上；`CLAUDE_PLUGIN_ROOT` 指向一個暫存資料夾 | 對 `hooks/guard_plugin_files.sh` 餵一個編輯該資料夾內檔案的 Edit 動作 | exit 2，stderr 有 `BLOCKED` | 自動：`tests/gates_without_jq_test.sh` |
| TC-011 | 要求 (a)；表 第 10 列 | 例外 | 同上 | 餵 `sed -i` 修改該資料夾內檔案的指令給 `guard_plugin_files.sh` | exit 2，stderr 有 `BLOCKED` | 自動：`tests/gates_without_jq_test.sh` |
| TC-012 | 要求 (b)；防止測試空轉 | 例外 | 機器上有真的 jq（CI 就是這樣） | 測試用 `tests/lib/nojq_path.sh` 隱藏 jq；若隱藏後仍找得到 jq（`nojq_path` 回傳 1） | 這個測試本身判為失敗並說明原因，不是跳過、也不是帶著 jq 照跑然後綠燈 | 自動：`tests/gates_without_jq_test.sh` |
| TC-013 | 要求 (b)；Done when 第 1 條 | 功能 | 一台真的沒有 jq 的 WSL（維護者的桌機） | 在那裡執行 `bash tests/gates_without_jq_test.sh` | 全部通過；測試所有輸入都用 `printf` 組出，不需要 jq | 手動：`docs/TESTING.md`（WSL 無 jq 那一步） |
| TC-014 | 要求 (b)；計畫「Tests」段 | 例外 | 本機暫時把某支 hook 的無 jq 出口從 `exit 2` 改成 `exit 0`（不提交） | 跑 `tests/gates_without_jq_test.sh` | 測試變紅，指出放行的那一列；還原 hook 後變綠；修復紀錄寫下這次紅燈 | 手動：`docs/TESTING.md`（變異檢查那一步） |

## 二、測試跑不動時，`run_all.sh` 說清楚並停下（22 個紅檔其實是測試的問題）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 計畫第 1 項；assessment 診斷 | 例外 | PATH 上看不到 jq，python3 正常 | 執行 `run_all.sh`（不帶 `--only`） | exit 3，一個測試檔都沒跑 | 自動：`tests/run_all_test.sh` |
| TC-016 | 計畫第 1 項 | 例外 | 同上 | 讀輸出訊息 | 訊息點名 jq；說明閘門本身沒有 jq 仍然會擋；指向 `tests/gates_without_jq_test.sh`；附 `sudo apt install jq` 與 `brew install jq`；且與 MSYS 停止的訊息不同（不提 WSL 當作原因） | 自動：`tests/run_all_test.sh` |
| TC-017 | 計畫第 1 項（「不跑任何檔」） | 例外 | 同 TC-015 | 檢查輸出與暫存區 | 沒有「N/M passed」，沒有建立 `bioflow-tests.*` 記錄資料夾 | 自動：`tests/run_all_test.sh` |
| TC-018 | 計畫第 1 項 | 例外 | python3 是「執行了但什麼都不印」的假檔（Windows Store stub），jq 正常 | 執行 `run_all.sh` | exit 3，訊息點名 python3，不點名 jq | 自動：`tests/run_all_test.sh` |
| TC-019 | 計畫第 1 項 | 例外 | jq 和 python3 都不能用 | 執行 `run_all.sh` | exit 3，訊息兩個工具都點名 | 自動：`tests/run_all_test.sh` |
| TC-020 | 憲法 13（「missing or broken」） | 例外 | PATH 上有個叫 jq 的假檔，執行了但什麼都不印 | 執行 `run_all.sh` | 視為沒有 jq：exit 3、點名 jq（不是因為「檔案存在」就放行） | 自動：`tests/run_all_test.sh` |
| TC-021 | 計畫第 1 項（探針與 hook 相同，允許結尾 CR） | 功能 | jq 會回 `[1]\r`（Windows 風格結尾） | 執行 `run_all.sh --only <會跑的檔>` | 不被當成缺 jq，正常往下跑 | 自動：`tests/run_all_test.sh` |
| TC-022 | 計畫第 1 項 | 功能 | PATH 上看不到 jq | 執行 `run_all.sh --allow-missing-tools --only intro_languages_test` | 照樣把檔案跑起來，不停在 exit 3 | 自動：`tests/run_all_test.sh` |
| TC-023 | 計畫第 1 項（「紅燈要有歸屬」） | 功能 | 同 TC-022 | 讀最後的結論行 | 結論行點名缺的是 jq（讓紅燈歸因於缺工具，而不是看起來像安全網壞了） | 自動：`tests/run_all_test.sh` |
| TC-024 | 計畫第 1 項 | 功能 | PATH 上看不到 jq | 執行 `run_all.sh --list` | exit 0，列出檔案清單，不要求工具 | 自動：`tests/run_all_test.sh` |
| TC-025 | 計畫第 2 項 | 功能 | PATH 上看不到 jq | 執行 `run_all.sh --only gates_without_jq` | 工具檢查被略過；該檔真的被跑且通過；exit 0，印 `all green` | 自動：`tests/run_all_test.sh` |
| TC-026 | 計畫第 2 項（略過條件只限這一個檔） | 例外 | PATH 上看不到 jq | 執行 `run_all.sh` 並選到 `gates_without_jq` 以外的檔（例如 `--only gates_without_jq` 加另一個 `--only` 目標不可行時，用選到兩個檔的子字串） | 只要選到任何別的檔，工具檢查就照常生效：exit 3 | 自動：`tests/run_all_test.sh` |
| TC-027 | 計畫第 1 項 | 功能 | 無 | 執行 `run_all.sh --help` | 用法說明列出 `--allow-missing-tools` | 自動：`tests/run_all_test.sh` |
| TC-028 | 計畫第 1 項（其餘行為不變） | 功能 | jq 與 python3 都正常 | 執行 `run_all.sh --only intro_languages_test` | 沒有任何缺工具訊息，照舊跑完，exit 0 | 自動：`tests/run_all_test.sh` |
| TC-029 | 計畫第 1 項（「Exit codes otherwise unchanged」） | 例外 | 無 jq 也一樣 | 執行 `run_all.sh --only zz-no-such-test-zz` | 仍是 exit 2 與「no test files matched」（找不到檔案的錯優先，與有沒有 jq 無關） | 自動：`tests/run_all_test.sh` |
| TC-030 | 計畫第 1 項（不可弄壞 MSYS 的停止） | 功能 | 假裝是 Windows Git Bash，jq 與 python3 正常 | 執行 `run_all.sh` | 仍是 exit 3、提到 WSL 與 PITFALLS 20c；`--allow-msys` 的既有行為不變（見 run_all_test 既有案例全部照舊通過） | 自動：`tests/run_all_test.sh` |
| TC-031 | 計畫第 4 項 | 功能 | 修復完成 | 讀 `docs/TESTING.md` 與 `docs/PITFALLS.md` | TESTING 說明測試需要 jq 與 python3、exit 3 的意思、`gates_without_jq_test.sh` 是「缺 jq 不會讓閘門放行」的檢查，並含 WSL 無 jq 一步（TC-013）與變異檢查一步（TC-014）；PITFALLS 有「22 個紅檔是測試不是閘門」一條 | 手動：`docs/TESTING.md` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 第 13 條（缺 jq 時要說出來，不能默默放行） | 功能 | CI（有 jq） | 跑 `confirm_launch_test.sh`、`confirm_cleanup_test.sh`、`confirm_walkthrough_test.sh`、`plugin_intro_test.sh` 的「no jq」段 | 全部照舊通過（本次沒有削弱它們） | 自動：上述四個檔 |
| TC-033 | 憲法「測試套件要能抓到真的失敗」；`run_all.sh` 既有 exit 1 | 例外 | jq 與 python3 正常；暫存的測試根目錄裡放一個一定失敗的測試檔 | 對該暫存根目錄執行 `run_all.sh` | exit 1，結論行有 `failed`，不印 `all green`（新檢查沒有把真的失敗藏起來） | 自動：`tests/run_all_test.sh` |
| TC-034 | 憲法檢查的存在性 | 功能 | 修復完成 | 跑 `tests/constitution_checks_exist_test.sh` | 通過（憲法點名的檢查檔都還在） | 自動：`tests/constitution_checks_exist_test.sh` |
| TC-035 | 安全網（規則與設定不變） | 功能 | 修復完成 | 比對 `main` 與本分支中 `settings`／hook 註冊檔／憲法 | 這些檔案沒有任何改動 | 手動：`docs/TESTING.md`（確認 hooks 與設定沒被改） |
| TC-036 | 第 13 條（CI 仍會真的跑到有 jq 的路徑） | 功能 | 修復完成 | 看 `.github/workflows` | 仍明確安裝 jq，沒有改成略過；完整套件含新檔都會在 CI 跑 | 手動：`docs/TESTING.md` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-037 | 計畫「Out of scope」第 1 條：不改 hook | 不在範圍 | 修復完成 | 比對 `main` 與本分支的 `hooks/` | 沒有任何差異（暫時為變異檢查改過的 hook 已還原、沒提交） | 手動：`docs/TESTING.md` |
| TC-038 | 「Out of scope」第 2 條：不替人安裝 jq | 不在範圍 | PATH 上有會記錄呼叫的假 `apt-get`、`brew` | 在無 jq 下執行 `run_all.sh` | 假的安裝指令一次都沒被呼叫；只印出安裝指令文字讓人自己跑 | 自動：`tests/run_all_test.sh` |
| TC-039 | 「Out of scope」第 3 條：不改寫那 22 個檔 | 不在範圍 | 修復完成 | 比對 `main` 與本分支的 `tests/` | 除了 `run_all.sh`、`run_all_test.sh`、新檔 `gates_without_jq_test.sh` 之外，沒有任何測試檔被改（尤其沒有放寬任何既有斷言） | 手動：`docs/TESTING.md` |
| TC-040 | 「Out of scope」第 4 條：issue #66、#71 | 不在範圍 | 修復完成 | 看本分支改動清單 | 沒有為 #66、#71 而做的修改 | 手動：`docs/TESTING.md` |
