# Slurm 清理：clean.py、handlers.py、拒絕表 progress ledger

- [x] `platform/tests/station_harness.py`：假 `squeue` 加 `-u <user>`（配 `-o %Z`，沒有 `-j`／`-n` 時印出該使用者各工作的工作目錄，一行一個）；`-j`、`-n` 的行為不動。
- [x] `platform/tests/test_station_clean.py`（新）：129 條測試（TC-001 到 TC-074、TC-083 到 TC-086 的自動項），先紅（commit `RED:`）後綠。
- [x] `platform/abf_station/clean.py`（新）：`KEYS`、`ATTEMPT`、`expected_work`、`run_clean`、`_clean_slurm`、十行固定樣板、結束碼對照；全套件唯一出現 `rm -rf` 的檔案。
- [x] `platform/abf_station/handlers.py`：`JOB_KINDS`、`ARG_KEYS` 加 `clean_work`，`handle()` 加一行分派，開頭說明補一句。

## 官方說明頁（動手前讀過，TC-081）

與計畫那句理由相符，沒有需要停手回報的差異：

- `nextflow clean`：https://www.nextflow.io/docs/latest/reference/cli.html （指令表寫「Clean up cache and work directories」，是 Nextflow 自己的子命令，要啟動 Nextflow，刪的範圍由它的紀錄決定，不是我們的路徑檢查。這一頁只有一行說明，「依賴 run 資料夾裡的快取資料庫」這半句是計畫的說法，我沒有在這頁找到更細的文字能獨立證實，只確認它不符合「代理逐項核對路徑」的需求）。
- `rclone purge`：https://rclone.org/commands/rclone_purge/ （寫明「Remove the path and all of its contents. Note that this does not obey include/exclude filters - everything will be removed」，確實不核對路徑）。
- Seqera Platform 的刪除：https://docs.seqera.io/platform-cloud/data/data-explorer （刪除是 Data Explorer 這個雲端服務的功能，用它的 workspace 憑證，要 Maintain 以上角色；不是代理在叢集上的動作）。

## 假站台與真叢集的已知差異（TC-080）

假站台的指令（`rm`、`realpath`、`stat`、`find`、`grep`）是測試機（WSL Ubuntu）上真的 GNU coreutils／findutils，只是 `rm`、`mv`、`rmdir`、`tar` 外面包了一層會記錄的殼。所以行為一致的部分：

- `rm -rf --one-file-system -- work`：work 內的連結只刪連結本身、不跟進去（TC-049 實測 `rawdata/x.fastq.gz` 還在）。
- `realpath -- .`／`realpath -- work`、`find results -type l -lname '*/work/*'`：GNU 行為相同。

可能不同、列為 f 片手動驗收（計畫已有的項 2 之外再加三項）：

1. `stat -c %U work`：假站台的擁有者是測試機本機使用者，與 `site_user` 設成相同。真叢集（國網 nano4）的使用者名稱由 LDAP／NSS 解析；若解析不到會回數字 uid，碼 16 會誤拒。驗收時用真的 `site_user` 跑一次，看 `stat -c %U` 印出的是不是同一個名字。
2. `squeue -h -u <user> -o %Z`：假 `squeue` 只印工作目錄。真的 Slurm 會把排隊中（PENDING）的工作也列出，這是我們要的（排隊中也算「還有工作」）；`%Z` 在真 Slurm 是 WorkDir，請驗收時確認實際輸出與 `#SBATCH -D` 的值逐字相同（沒有結尾斜線、沒有軟連結展開）。
3. `rm -rf` 在 Lustre 上的耗時：假站台瞬間完成。遠端逾時上限 300 秒（計畫裁決 7）；逾時會回「可能只刪了一部分」，不重試。
4. 計畫已列的項 2：國網站台設定檔（`$NFCORE_SITE_CONFIG`）有沒有改 `workDir`；不通過就停手回報。

## 觀察與要問維護者的事

- 裁決二已改：樣板第 9 行 `find` 出錯回碼 17、不刪（TC-087，假 find 用 `find_fail` 旗標）。
- `-lname '*/work/*'` 偏保守：任何指向含 `/work/` 的路徑的連結都算。依計畫實作。
- 本片沒有碰 `cancel.py`；計畫旁註提到取消續跑那一次會被 `cancel.py` 拒絕，我沒有實測也沒有修。
- `ATTEMPT` 公式：`run == leaf[:64 - len(sfx)] + sfx`，且數字不含前導零、N 至少 2；與 `launch.run_folder_ok` 一致，但在 `clean.py` 內自己重算（`launch.py` 禁碰）。
- 計畫「完成標準」寫 MCP 工具數仍 12，但倉庫現況既有測試（`test_pat.py`、`test_oauth_mcp.py`）斷言的是 14；本片沒碰平台，數量與 base 相同。
- worktree 上一層多出一個空目錄 `wt/_hold`（我一個指令打錯建的，在 git 之外）；我的環境不准我刪，請維護者自行刪除。

## diff 統計（`git diff --stat 8b560fa..HEAD`，8b560fa＝測試案例 commit；不含本檔）

```
 platform/abf_station/clean.py        | 126 ++++++++
 platform/abf_station/handlers.py     |  12 +-
 platform/tests/station_harness.py    |   5 +-
 platform/tests/test_station_clean.py | 610 +++++++++++++++++++++++++++++++++++
 4 files changed, 748 insertions(+), 5 deletions(-)
```

## 裁決二補記

- `-lname '*/work/*'` 會把指向含 `/work/` 路徑（例如 workDir 本身在 /work 底下，連到 rawdata 的連結）也當成指向 work：偏保守、不會誤刪，本片接受，留給之後。
- 測試檔數量：130 條（多了 TC-087）；harness 多了 `find_fail` 旗標（只影響假 find，預設不變）。
