# CI 失敗只重跑一次＋隔離名單（重跑才過的要登記） progress ledger

- [x] RED `5a16009`：`tests/run_all_retry_test.sh` 先寫，在未改 `run_all.sh` 的狀態下 96 條斷言紅（旗標不存在，如 `TC-005 --help mentions --retry-failed-once FAIL`、`TC-011 all green + flag: exit 0 FAIL` 等），不帶旗標的 TC-001／003／004／006／007／008 本來就綠。
- [x] GREEN `3ee0c95`：`tests/run_all.sh` 加 `--retry-failed-once`、`--check-quarantine`、名單驗證（純 bash 日數換算）、重跑與結論函式；新增 `tests/quarantine.txt`（只有註解）。`tests/run_all_retry_test.sh` 全綠（自動 TC 全部）。
- [x] `platform_test.sh` 不准進名單（裁決二第 2 點）：驗證時拒絕並說明，TC-053 覆蓋。
- [x] 不改 `.github/`（裁決二第 1 點，留給 developer-agent）、不改 `memory/scripts/abf-fast-suite.sh`、不改任何既有測試。

## 證據

全套（WSL，不帶旗標，`abf-fast-suite`）在 `3ee0c95`：`122/122 passed`、`all green`。

TC-009：同一個假目錄（a_test.sh 通過、b_test.sh 失敗），`47701fb` 的 `run_all.sh` 與新 `run_all.sh` 各不帶旗標跑一次，正規化後 `diff` 為空。輸出：

```
root: X
version: unknown

a_test.sh                                      ok
b_test.sh                                      FAIL  rc=1

== output of what did not pass ==
--- b_test.sh ---
boom

1/2 passed - run with --allow-missing-tools, python3 missing, 1 failed
```

真實 repo `bash tests/run_all.sh --allow-missing-tools --check-quarantine`（假 uname）：`tests/quarantine.txt ok`，退出 0。

`git diff --stat 47701fb..HEAD -- . ':!specs'`：`tests/quarantine.txt`、`tests/run_all.sh`、`tests/run_all_retry_test.sh` 三個檔。

## 備註

- Git Bash 沒有 jq，沙盒測試的摘要行會多出 ` - run with --allow-missing-tools, ... missing`，`run_all_retry_test.sh` 在比對前把這段去掉（TC-056 的 python3 假指令也放行 `print(1)` 探測，因為既有的工具檢查會呼叫它）。
- TC-033（INCOMPLETE 重跑不能補救）沙盒難製造：`retry_and_conclude` 第一行 `[ "$total" = "$expected" ] || exit 1`，閱卷讀碼。
- 沒有跑「真實 repo 帶 `--retry-failed-once` 全套」；全套只跑了不帶旗標那次。

## 審查後修訂（裁決三、裁決四）

- [x] RED `8b3c63e`：`tests/run_all_retry_test.sh` 依修訂合約重寫（相對日期、無 RUN_ALL_TODAY、逾時不重跑、名單檔不見、TC-078～TC-091 新案例）；未改 run_all.sh 時 42 條斷言紅。
- [x] GREEN `1c003e3`：`tests/run_all.sh` 日期只用 `date -u +%F`、逾時不重跑、名單檔不見即失敗、`--check-quarantine` 在參數解析後立刻執行、`platform_clock_test.sh` 也拒收、`--verbose` 印重跑輸出、缺工具提示帶進結論、名單行尾 `# 註解`、stderr 句改為 `Not quarantined (flaky): …`。`run_all_retry_test.sh` 全綠；WSL 全套（不帶旗標）`122/122 passed`、`all green`。
- 沒動 `.github/`（留給 developer-agent）。此 ledger 提交之後 HEAD 多一個只改文件的 commit，測試與程式碼同 `1c003e3`。
