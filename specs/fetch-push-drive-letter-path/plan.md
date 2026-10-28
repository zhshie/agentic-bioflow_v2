---
id: fetch-push-drive-letter-path
title: fetch.sh／push.sh 交給 rsync 的本機路徑若是 Windows 磁碟機寫法（C:/…），要先轉成 rsync 看得懂的本機路徑，不能被當成遠端主機
tier: A
kinds: backend
lane: L15-fetch-drive-path（只動 scripts/fetch.sh、scripts/push.sh 與各自的測試；不與 build_package／finish 任務、platform、web、雲端、hooks、測試切分任何檔相交）
branch: fix/fetch-push-drive-letter-path
base: v3
source: GitHub issue #23（表列第 5 項 `fetch-sh-rsync-remote-remote`，退出碼 2，標 workaround）；#11 的 #6（rsync 缺失）已修，本任務是同一條 rsync 路徑上留下的另一個洞
---

# fetch-push-drive-letter-path

> 本檔由 Explore 子代理草擬（2026-10-28）給 developer-agent 審。A 級（預設行為不變，只修「路徑長得像 `C:/…` 時 rsync 把它當遠端」）。
> **誠實註記**：#23 只留下簽章，沒有診斷（「each line below is a pointer to investigate, not a diagnosis」）。「rsync 把 `C:` 當主機名」是我讀 `scripts/fetch.sh` 後的**推論**：rsync 規定 `host:path` 形式的引數是遠端，`C:/Users/x/` 正好是這個形狀，fetch.sh 的來源 `$HOST:$SRC` 已是遠端，目的地再被判成遠端，就會得到 rsync 的 "The source and destination cannot both be remote"（簽章名 remote-remote 吻合）。**沒有在真的 Windows 機器上重現過**。本任務釘的是不變式（「交給 rsync 的本機端引數絕不以磁碟機代號加冒號開頭」），測試只用假的 rsync 記錄引數，不需要 Windows。

## 目標
`fetch.sh`（本機目的地 `$(dirname "$DEST")/`）與 `push.sh`（本機來源 `$SRC` 或 `$SRC/`）呼叫 rsync 時，若本機路徑是 `X:/…` 或 `X:\…`，先轉成 MSYS 寫法 `/x/…`（有 `cygpath` 就用 `cygpath -u`）再交給 rsync；其他路徑一字不動。對使用者的意義：在 Windows 上指定 `C:\Users\me\out` 當 `fetch.sh` 的本機路徑（或把 `C:` 路徑的資料夾 `push.sh` 上站台）不再因為 rsync 誤判成遠端而以 exit 2 失敗、逼人手動換寫法。

## 維護者原話（verifier 出題用）
- issue #23 本文：「Fields are the report whitelist only; no free text was ever recorded, so each line below is a pointer to investigate, not a diagnosis.」→ 本任務是調查後的最小修補，不得宣稱已證實為唯一原因。
- issue #23 表列第 5 項（逐字）：`| 5 | downstream | `fetch.sh` | `fetch-sh-rsync-remote-remote` (host) | 2 | workaround | `c55ec86c0393` |`
- issue #23 末段：「Each item becomes its own change after the repo moves to spec-driven development; this issue is the backlog pointer.」→ 一項一個變更，不順手改別的。

## 範圍：檔案（只准改這些）
- `scripts/fetch.sh`
- `scripts/push.sh`
- `tests/fetch_test.sh`（只許**新增**斷言段落；既有斷言原樣）
- `tests/push_test.sh`（同上）
- `specs/fetch-push-drive-letter-path/ledger.md`（新，executor 進度帳本）

**禁止碰**：`scripts/utils/*`（不新增共用輔助函式到別的檔；兩支腳本各自內嵌一個小函式，理由見作法 4）、`scripts/on_site.sh`、`scripts/settings.sh`、`hooks/`、`platform/**`、`.github/`、`tests/platform_shard_*`、`tests/platform_test.sh`、`tests/run_all.sh`、`tests/quarantine.txt`、任何 `*aws*`／`*azure*`／`build.py`／`compute_envs.py`。

## 作法
1. 新增函式 `rsync_local_path()`（fetch.sh 與 push.sh 各一份，內容相同）：輸入一個本機路徑字串，輸出要交給 rsync 的字串。
   - 若符合 `^[A-Za-z]:[\\/]`：優先 `cygpath -u -- "$p"`（若 `command -v cygpath` 且成功）；否則手動轉換——磁碟機代號轉小寫、冒號拿掉、反斜線換正斜線，前面補 `/`：`C:\Users\me\out` → `/c/Users/me/out`，`D:/x` → `/d/x`。
   - 結尾斜線保留（rsync 的尾斜線有語意：`dir/` 與 `dir` 不同）。
   - 其他一切路徑（含 `/c/Users/…`、相對路徑、`./C:foo`）原樣輸出。
2. `fetch.sh`：rsync 呼叫的目的地 `"$(dirname "$DEST")/"` 改為 `"$(rsync_local_path "$(dirname "$DEST")")/"`。tar 後備路徑**不動**（tar 吃 `C:/…` 沒問題，且 `-C` 是本機目錄，不經過 rsync 的主機判斷）；`mkdir -p`、`--dry-run` 輸出、最後 `printf '%s\n' "$DEST"` 一律用**原始** `$DEST`（使用者看到的是自己給的路徑）。
3. `push.sh`：rsync 呼叫的 `"$from"` 改為 `"$(rsync_local_path "$from")"`（保留 `$SRC/` 的尾斜線，注意先轉換再看尾斜線不被吃掉）；`$to`（`$HOST:$DST…`）**不動**——那是真正的遠端端。tar 後備路徑不動。
4. 為什麼不放進 `scripts/utils/`：目前只有這兩處需要，而 `scripts/utils/*` 在別的任務可能同時動；兩份小函式的重複由測試鎖住兩邊行為一致（見測試 5），比共用檔多一條跨任務相依便宜。若將來第三處需要，再抽出。
5. 不改任何錯誤訊息、不改 `--dry-run` 輸出格式、不改 exit code。

## 失敗先行測試
全部用假 rsync（`FETCH_RSYNC_BIN`／`PUSH_RSYNC_BIN` 指到記錄引數的小 shell 腳本，每個引數一行寫進 `$TMP/rsync.args`），假 ssh（既有 `mkssh`／`$TMP/ssh`），在 `$TMP` 內 `cd` 後執行，所以相對目錄 `C:/Users/me/...` 在 Linux 是普通資料夾，**不需 Windows、不連網**。現在都會紅（rsync 的最後一個引數仍以 `C:` 開頭）。

在 `tests/fetch_test.sh`：
1. `fetch_drive_letter_destination_is_not_handed_to_rsync_as_is`：`settings 'reach: ssh' 'site_host: me@example.org'`，`mkssh 26000`，執行 `fetch.sh /work/runs/myrun/results 'C:/Users/me/out/results'`；記錄到的 rsync 引數中，**最後一個**必須等於 `/c/Users/me/out/`（無 `cygpath` 的環境；測試先 `PATH` 排除 cygpath，或僅在 `command -v cygpath` 為空時斷言這個字串，有 cygpath 時斷言「不匹配 `^[A-Za-z]:`」）。今天最後一個引數是 `C:/Users/me/out/` → 紅。
2. `fetch_backslash_drive_letter_is_converted_too`：目的地 `'D:\\data\\out\\results'` → 最後引數不匹配 `^[A-Za-z]:`，且等於 `/d/data/out/`。
3. `fetch_posix_and_relative_destinations_are_untouched`（控制組，今天就綠、改後必須仍綠）：目的地 `/tmp/x/results` 與 `rel/results` → 最後引數分別為 `/tmp/x/` 與 `rel/`；既有 `t "a real fetch prints the local path"` 原樣綠。
4. `fetch_still_reports_the_users_own_path`：步驟 1 的情境，stdout 最後一行是使用者給的 `C:/Users/me/out/results`（不是轉換後的），`--dry-run` 輸出也含原始路徑。
5. `fetch_remote_end_is_never_rewritten`：rsync 引數中的 `me@example.org:/work/runs/myrun/results` 原樣存在。

在 `tests/push_test.sh`：
6. `push_drive_letter_source_is_not_handed_to_rsync_as_is`：`$TMP` 內建立相對資料夾 `C:/Users/me/reads`（內含一個小檔），`cd "$TMP"` 後 `push.sh 'C:/Users/me/reads' /work/runs/myrun/rawdata`；rsync 引數中倒數第二個（來源）等於 `/c/Users/me/reads/`（尾斜線保留），最後一個（目的）等於 `me@example.org:/work/runs/myrun/rawdata/`。今天來源引數是 `C:/Users/me/reads/` → 紅。
7. `push_plain_file_with_drive_letter_keeps_no_trailing_slash`：來源是單一檔案 `C:/Users/me/a.fastq.gz` → 來源引數 `/c/Users/me/a.fastq.gz`（無尾斜線）。
8. `push_posix_source_is_untouched`（控制組）：既有 `$TMP/reads` 的行為不變。

雙腳本一致：
9. `both_scripts_convert_the_same_way`：在 `fetch_test.sh` 或 `push_test.sh` 其中一檔（擇一）把兩支腳本的 `rsync_local_path` 函式本體用 `sed -n '/^rsync_local_path()/,/^}/p'` 抽出、`diff` 相同。

## 完成標準（done when）
- 上面新測試全綠；`bash tests/fetch_test.sh`、`bash tests/push_test.sh` 既有斷言全部原樣綠；全套（WSL 內 `bash tests/run_all.sh`）綠。
- `git diff --name-only origin/v3...HEAD` 只出現「範圍」列的檔案。
- `fetch.sh`／`push.sh` 在輸入為非磁碟機寫法時，rsync 引數與修改前逐字相同（測試 3、8）。
- 沒有新增相依、沒有新增 `nohup`／`setsid`、沒有 skills／commands 字樣變動（`tests/command_layer_is_site_neutral.sh` 綠）。

## 環境事實
- `scripts/fetch.sh`（origin/v3）：rsync 呼叫在檔尾的 `if command -v "$RSYNC"` 區塊，`"$RSYNC" -a -e "$SSH -o ControlPath=$CP" "$HOST:$SRC" "$(dirname "$DEST")/"`；`DEST="${2:-$STAGE/${SRC#/}}"`，`STAGE` 來自 `FETCH_ROOT`／`XDG_CACHE_HOME`／`$HOME/.cache`。Git Bash 的 `$HOME` 是 `/c/Users/…` 形式，所以預設不會觸發；觸發條件是使用者／呼叫者給了 `C:\…`／`C:/…` 的第二個引數或 `FETCH_ROOT`。
- `scripts/push.sh`：rsync 呼叫在 `command -v "$RSYNC"` 區塊，`"$RSYNC" -a --partial -e … "$from" "$to"`；`from="$SRC/"`（資料夾）或 `$SRC`（檔案），`to="$HOST:$DST…"`。`[ -e "$SRC" ]` 先檢查來源存在。
- rsync 規則：引數含 `:` 且冒號前沒有 `/` 者視為 `host:path`（遠端）；兩端都遠端 → 錯誤。這是 rsync 的行為（官方 man page 的 "USAGE"），不是推測；「這就是 #23 第 5 項的原因」才是推測。
- `docs/PITFALLS.md` 16 節（約 889–895 行）記載 Git Bash 沒有 rsync、fetch／push 已改用 tar|ssh 後備；本任務只針對**有 rsync** 的路徑。
- 既有測試風格：`tests/fetch_test.sh` 的 `t <label> <rc> <substring> -- <args>` 輔助函式與 `mkssh`；假 rsync 現在是 `exit 0` 的空腳本（`$TMP/rsync`），新測試要另做一支「記錄引數」的版本，不改既有那支。
- repo CLAUDE.md「For the executor and verifier」：一個測試檔用 `bash tests/<name>.sh`；全套須在 WSL／Linux；不得改 `spec.md`、`test-case*.md`、憲法、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`；不得連站台或 HPC。

## 不做
- 不處理 WSL 內 rsync 要 `/mnt/c/…` 的情形（目前專案文件的 Windows 路徑是 Git Bash／MSYS，`/c/…`；WSL 橋接下的磁碟機寫法未量測，列為已知未涵蓋，見裁決 1）。
- 不改 tar|ssh 後備、不改 `--dry-run`、不改錯誤訊息、不改 exit code。
- 不做 UNC 路徑（`\\server\share`）處理。
- 不新增共用輔助檔、不碰 `scripts/utils/`。
- 不處理 #23 其他幾項（它們多數已修，見回報）。

## 待裁決選項（developer-agent 填入下方「裁決」）
1. 轉換目標寫成 MSYS 形式 `/c/…`（Git Bash／MSYS rsync 看得懂）；WSL 橋接下的 `/mnt/c/…` 不做。要不要加：＿＿＿（預設：不加，標為未量測）。
2. 因 #23 沒有診斷，是否要求維護者先在 Windows 上重現一次再派工：＿＿＿（預設：不要求；不變式本身無害，測試不依賴重現）。
3. 兩份函式重複 vs. 抽到 `scripts/utils/`：＿＿＿（預設：重複＋測試 9 鎖一致）。

## 裁決
- **D1（2026-10-28 14:55，developer-agent）**：三項都照預設——①只轉成 MSYS 的 `/c/…`，WSL 的 `/mnt/c/…` 不做，ledger 標「未量測」；②不要求先在 Windows 重現，測試鎖的是「磁碟機寫法不得交給 rsync」這個不變式；③兩支腳本各自一份轉換函式，用測試 9 鎖住兩邊輸出一致，不抽到 `scripts/utils/`。
- **D2**：根因是從程式推論的（#23 只有簽名），PR 說明要照實寫「推論、未在 Windows 重現」。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
