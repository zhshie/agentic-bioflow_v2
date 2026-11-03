# CLI 契約測試（argparse，golden 快照） progress ledger

- [x] test_cli_contract.py（TC-001..012）、test_cli_snapshots.py（TC-013..016）、__golden__/ 6 份快照
- RED be27aa90（快照缺檔 6 條紅）；GREEN：快照產生並逐檔審閱後 187 passed（含 test_cli_usage_doc.py）。
- 快照（各自行數）：cli_tree 36、cli_help_top 37、cli_help_user_add 12、cli_help_ce_create 73、cli_json_ce_show 19、cli_json_dataset_show 14。
  審閱：無 /tmp、使用者名稱、CR；JSON 的時間戳與 id 已正規化為 <TS>/<N>；cli_tree 每個葉子一行（共 36 條）；help 以 COLUMNS=100、`optional arguments:`→`options:`。
  產生方式：ABF_UPDATE_GOLDEN=1 跑 abf-fast-suite（鏡像目錄寫檔），複製回工作樹，再不帶變數重跑。沒有一次蓋掉全部不看的更新。
- 環境：worktree 用 Windows git 建，WSL 內 constitution_scope_test.sh 若紅＝環境問題，以 CI 為準（裁決 4）。
- 已知偏離（見 decisions.tsv）：`ce show`／`dataset show` 找不到時 stderr 不以 `rejected:` 開頭（現況，不能改 cli.py）；中文說明放寬為「任一處有中文」。
- 驗收核對：`git diff --stat v3...HEAD` 應只含兩支測試、__golden__/、specs/cli-contract-tests/。
