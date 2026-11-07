---
id: gitleaks-classify
title: security workflow 的 gitleaks 全歷史掃描失敗時，另產一份仍遮蔽密鑰的 JSON 報告並上傳成 artifact，讓人能分類那 34 筆
tier: A
kinds: backend
risk: L
lane: L-gitleaks-classify
branch: feat/gitleaks-classify
dir: specs/gitleaks-classify
base: v3
source: 維護者經 chase session 於 2026-11-05 轉述；PR #358（specs/ci-secrets-deps）新增的 security workflow 在 v3 回報「2234 commits scanned, leaks found: 34」，但日誌被 --redact 遮蔽、無法分類
---

# gitleaks-classify

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/gitleaks-classify/plan.md`。**只處理本任務**。risk L（tier A，且範圍含 `.github/`）。

## 目標
`security` workflow 的 `gitleaks` job 在「Scan full history」步驟失敗時，同時留下一份 JSON 報告（密鑰值仍遮蔽），並以 artifact 上傳。人下載後能看到 34 筆各自的檔案路徑、規則 id、commit，**看不到密鑰原文**，才能判斷是測試 fixture 還是真洩漏。本片只做「看得見」，不做分類、不加 allowlist。

## 維護者原話（verifier 出題用）
1. 「需在本機或 CI 加 --report-format json --report-path 上傳 artifact 才能分類，再決定是 .gitleaks.toml allowlist（僅限測試 fixture，每條要附證據）還是真洩漏（若是真金鑰要先通知維護者並輪替）」（11-05，chase session 轉述）
   → 測試案例：(a) 全歷史掃描步驟有 `--report-format json` 與 `--report-path`；(b) 有 upload-artifact 步驟且 `if: always()`；(c) 沒有新增任何 allowlist 條目（`.gitleaks.toml` 不變）；(d) 掃描仍帶 `--redact`；(e) 文件寫明「真金鑰：停、通知維護者、輪替」。
2. ci-secrets-deps 既有裁示（沿用，不得退步）：「真機密 → 停下回報（BLOCKED，屬安全事件，不得自行改寫歷史），不寫進 allowlist」；「一律加 `--redact`，日誌不得出現疑似機密原文」；不是必過檢查（`run_all`／`shard` 不動）。

## 範圍：檔案
- `.github/workflows/security.yml`：**只改 `gitleaks` job 的「Scan full history」步驟**，並在它之後新增一個 upload-artifact 步驟。不動其他步驟、不動 `pip-audit` job、不動 `on:`、頂層 `permissions:`。（此檔受 `.github/` 寫入防護，由 developer-agent 親手寫入；executor 把完整新檔內容寫在 ledger／交接中。）
- `tests/ci_security_workflow_test.sh`：**只新增**檢查函式與把它們加進最後的 `for t in ...` 清單；既有 12 項不刪不放寬。
- `docs/TESTING.md`：只在「## CI security checks」一節（約 1041～1051 行）後面加一小段：報告 artifact 叫什麼、怎麼下載、欄位怎麼看、真金鑰的處置。只加不改。
- `specs/gitleaks-classify/`（ledger 等）。
- **不得改**：`.gitleaks.toml`、`.github/workflows/tests.yml`、`platform/pip-audit-ignore.txt`、任何 ruleset／required check 設定。

## 作法
1. **掃描步驟**：沿用原指令字串並**只在後面附加旗標**，例如
   `gitleaks git --redact --no-banner --config .gitleaks.toml --report-format json --report-path gitleaks-report.json`
   （既有測試用 `grep -F` 找 `gitleaks git --redact --no-banner --config .gitleaks.toml`，附加在後面不會破壞它；`--redact` 必須留在、且每一行 `gitleaks git ` 都要有它）。報告檔放工作目錄、檔名固定 `gitleaks-report.json`。不用 `continue-on-error`、`|| true`、`--no-fail`（既有 TC-011 禁止；步驟失敗仍要讓 job 紅）。
2. **報告內容要確認已遮蔽**：gitleaks 8.30.1 在 `--redact` 下 JSON 的 `Secret` 與 `Match` 欄會被遮蔽（`REDACTED`）。executor 在本機用同版本（或在草稿分支的 CI）對一個假金鑰（`AKIA` 形假值，見 TESTING.md 既有手動案）實跑一次，把報告片段貼進 ledger，證明報告檔裡**找不到假金鑰原文**；若找得到，停下回報、不要上傳。報告含 `File`、`RuleID`、`Commit`、`StartLine`、`Author`、`Email`、`Date`、`Fingerprint`——作者 email 是個資，列入爆炸半徑說明（artifact 只有對 repo 有讀取權的人可下載；repo 若為公開，email 本來就在 git log 公開）。
3. **上傳步驟**（緊接在掃描步驟之後，同一 job）：
   - `uses: actions/upload-artifact@<40 位 commit SHA>  # vX.Y.Z`——格式必須符合既有 TC-009 的正規式（`owner/repo@40位十六進位  # v數字.數字.數字`）。SHA 由 executor 以 `gh api repos/actions/upload-artifact/git/ref/tags/<tag>`（若為 annotated tag 再解一層）查出並在 ledger 記下查證過程；**不得憑記憶填 SHA**、不得用 `@v4` 之類浮動標籤。選目前主版本 v4 的最新穩定版。
   - `if: always()`（掃描失敗時也要上傳）；`name: gitleaks-report`；`path: gitleaks-report.json`；`if-no-files-found: ignore`（掃描根本沒跑到時不要讓上傳步驟另外報錯）；`retention-days: 14`。
   - 不給任何 `secrets.*`、不加 `permissions:` 區塊（既有 TC-005／006：整檔只有頂層一個 `permissions:`，內容只有 `contents: read`；upload-artifact 不需要額外權限）。
4. **PR 掃描步驟（Scan this PR's commits）不動**；本片不替它產報告。
5. **不新增 allowlist、不改 `.gitleaks.toml`**。分類在這之後，每條 allowlist 都要有證據。
6. **爆炸半徑證明（risk L 必附，寫進 ledger）**：
   - workflow 能做什麼：在 GitHub-hosted runner 上 checkout 全歷史、下載並驗 sha256 的 gitleaks、跑掃描、上傳一個檔案；新增的唯一能力是「上傳一個 artifact」。
   - 權限：頂層 `permissions: contents: read` 不變、job 內無 `permissions:`；貼 `git diff` 證明。
   - 對 fork 的暴露：觸發器仍是 `pull_request`（非 `pull_request_target`）；fork 的 PR 拿不到 repo secrets、`GITHUB_TOKEN` 唯讀；workflow 裡沒有任何 `secrets.` 引用（grep 為 0 筆）。fork PR 觸發時 artifact 只含該 PR 可見歷史的遮蔽報告。
   - 報告已遮蔽：第 2 點的假金鑰實驗結果。
   - 不影響必過檢查：job 名 `gitleaks`、`pip-audit` 與 `run_all`／`shard` 無關，`tests.yml` 的 diff 為空。
   - 移除方式：把新增的步驟與附加的兩個旗標刪掉即還原；或還原該 commit。
7. **文件**：TESTING.md 新段說明：artifact 名 `gitleaks-report`（Actions 該次 run 頁面下方 Artifacts）；用 `jq -r '.[] | [.RuleID,.File,.Commit] | @tsv'` 看清單；**判斷是真金鑰就立刻停下、通知維護者、輪替該金鑰，不得自行改寫歷史、不得先寫 allowlist**。

## 失敗先行測試
全部寫在 `tests/ci_security_workflow_test.sh`（grep／awk，不連網、不用 PyYAML），沿用其 `code`／`cg` 輔助函式與 `ok`／`FAIL` 輸出。現在都會紅（security.yml 尚無報告旗標與 upload 步驟）。
- `test_gitleaks_full_scan_writes_json_report`：「Scan full history」那一行含 `--report-format json` 與 `--report-path`，且路徑值非空。
- `test_gitleaks_report_stays_redacted`：每一行 `gitleaks git ` 仍含 `--redact`；整檔沒有 `--no-redact`。
- `test_report_is_uploaded_always_as_artifact`：存在一個 `uses: actions/upload-artifact@<40hex>  # v…` 行；同一步驟區塊內有 `if: always()`，且 `path:` 等於掃描步驟的 `--report-path` 值（兩邊一致）。
- `test_upload_artifact_is_sha_pinned`：該 uses 行符合與 TC-009 相同的完整 SHA 正規式，且不含 `@v[0-9]`、`@main`、`@master`。
- `test_permissions_stay_read_only_after_report`：沿用 TC-005／006 的邏輯再斷言一次：頂層 `permissions:` 只有 `contents: read`；整檔只有一個 `permissions:`；無 `secrets.`、無 `pull_request_target`。
- `test_gitleaks_toml_has_no_new_allowlist`：`.gitleaks.toml` 內 `[[allowlists]]` 條數與 origin/v3 相同（目前為 0 條則斷言仍為 0）。executor 先用 `git show origin/v3:.gitleaks.toml` 確認現況再寫死基準。
- `test_pip_audit_job_unchanged`：`pip-audit` job 內容與 origin/v3 逐字相同（以 `git show "origin/v3:.github/workflows/security.yml"` 取 job 區段比對；鏡像沒有 origin/v3 時印 `skipped` 並視為通過，比照既有 `test_existing_tests_yml_untouched` 的作法）。
- 最後把以上函式加進檔尾 `for t in ...` 清單；檔案的總結輸出格式不變。

## 允許的斷言（既有測試）
下列既有檢查釘住本案會碰的字串，**只准新增、不刪不放寬**。開工前用 `git -C <repo> grep -n "<字串>" origin/v3 -- tests` 對一次行號：
- `tests/ci_security_workflow_test.sh`：
  - `test_gitleaks_scans`（TC-023..026）：`grep -F` 找 `gitleaks git --redact --no-banner --config .gitleaks.toml`（附加旗標在後面可通過）、`--log-opts "origin/${{ github.base_ref }}..HEAD"`、`if: github.event_name == 'pull_request'`、`fetch-depth: 0`。
  - `test_gitleaks_uses_redact`（TC-027）：`gitleaks git ` 行數 ≥ 2 且全含 `--redact`。
  - `test_every_uses_is_pinned_to_full_sha`（TC-009）：每個 `uses:` 行必須是 `owner/repo@40hex  # vN.N.N`；新增的 upload-artifact 行也要符合（版本註解一定要寫三段）。
  - `test_permissions_are_read_only_and_no_pull_request_target`（TC-005..008）：頂層 permissions 內容必須恰為 `  contents: read`；全檔只有一個 `permissions:`；無 `secrets.`。
  - `test_no_way_to_turn_checks_off`（TC-011）：不得出現 `continue-on-error`、`|| true`、`--no-fail`、`if: false`。（`if: always()` 不在禁止內。）
  - `test_gitleaks_download_is_verified`（TC-020..022）：`GITLEAKS_VERSION`、`sha256sum -c`、64 位十六進位、無 `latest`、無 `gitleaks/gitleaks-action`。
  - `test_triggers`、`test_security_workflow_exists_and_is_separate`、`test_job_names_do_not_collide_with_required_check`、`test_pip_audit_targets_both_files`、`test_allowlist_entries_have_reason_and_are_not_blanket`（讀 `.gitleaks.toml`，本案不動它）、`test_existing_tests_yml_untouched`（`tests.yml` 不得有 diff）。
- `tests/charter_v4_workflow_test.sh:61`、`tests/run_all_shard_test.sh:76`：只讀 `tests.yml`；本案不碰 `tests.yml`，不受影響。
- `docs/TESTING.md`：1043 行「Neither is a required check」與 1046 行手動案（假金鑰、日誌遮蔽）原句不改，只在該節後面加新段。

## 完成標準（done when）
- 上面每條失敗先行測試綠；`bash tests/ci_security_workflow_test.sh` 全綠；`tests/run_all.sh` 全綠（環境紅依 README 通例）。
- `git diff --stat` 只含：`.github/workflows/security.yml`、`tests/ci_security_workflow_test.sh`、`docs/TESTING.md`、`specs/gitleaks-classify/`。`.gitleaks.toml`、`tests.yml`、`pip-audit` job 的 diff 為空，貼進 ledger。
- 爆炸半徑證明（作法第 6 點）逐項寫進 ledger；PASS 後依 risk L 再跑一次 Opus 對抗審。
- 假金鑰實驗證據（作法第 2 點）在 ledger。
- 合併後在 v3 實跑一次 `security` workflow（`workflow_dispatch`），確認 artifact `gitleaks-report` 出現且可下載。**此為手動驗收，由 developer-agent 做，不擋合併**。

## 環境事實
- 現行 workflow：`.github/workflows/security.yml`（origin/v3），`gitleaks` job 步驟為 checkout（fetch-depth 0）→ 安裝（固定版本 8.30.1＋sha256）→「Scan full history」（`gitleaks git --redact --no-banner --config .gitleaks.toml`）→「Scan this PR's commits」（僅 pull_request）。
- v3 實測：2234 commits scanned、leaks found: 34；日誌被遮蔽無法分類。
- `.github/` 受寫入防護，executor 無法直接寫；developer-agent 負責寫入該檔（ci-secrets-deps ledger 同樣如此）。
- 在此機器上 `git show origin/v3:<path>` 要先 `export MSYS_NO_PATHCONV=1`，並把 `origin/v3:<path>` 用引號包起來。
- 設計參考：`specs/ci-secrets-deps/plan.md`、`specs/ci-secrets-deps/ledger.md`（原 workflow 的爆炸半徑與測試寫法）。
- PITFALLS 已查：`docs/PITFALLS.md` 沒有 gitleaks／workflow／artifact／`.github` 相關條目（只有無關的 `/workflow/<id>/reports`、`workflows/` 目錄等字樣）；`docs/solutions/` 不存在。PITFALLS 已查，無相符項。

## 不做
- **實際讀報告、分類 34 筆**：是 developer-agent 的後續工作，不在本片。分類結果決定：誤報（僅限測試 fixture）→ 另開任務在 `.gitleaks.toml` 加精準 allowlist，每條附證據；真洩漏 → 見裁決 1。
- 不加任何 allowlist 條目、不改 `.gitleaks.toml`。
- 不改哪個 job 是必過檢查；不動 `pip-audit` job；不動 `tests.yml`、`on:` 觸發器、頂層 `permissions`。
- 不替「Scan this PR's commits」產報告（後續切片，如有需要再議）。
- 不改寫 git 歷史、不輪替任何金鑰（那是維護者的動作）。
- 不用第三方 action 取代手動安裝的 gitleaks；不引入 `gitleaks-action`。

## 裁決
1. **真金鑰處置（常設）**：分類時只要有任何一筆是真的金鑰（不是測試 fixture），developer-agent 立刻停手、通知維護者並請其輪替該金鑰；不得先寫 allowlist、不得自行改寫歷史、不得把原文貼到任何 ledger／issue／對話。
2. 合約規則：計畫未明寫的細節由 verifier 依專長守則與既有慣例自訂預期值，不以「計畫未寫」退回。
3. 本任務碰 `.github/`，risk L，須附爆炸半徑證明；請把 `risk: L` 抄進佇列任務物件。
4. 整套測試一律 `run_in_background`＋等待迴圈跑 `tests/run_all.sh --timeout 900`。
5. **維護者核可（2026-11-07）**：他說好；已從 `awaiting_maintainer` 移到 `backlog.ready`（做法同 ci-secrets-deps）。仍是受保護路徑（`.github/`）：Opus 對抗審通過前不得掛自動合併，worker 走 `done-protected`，由 lead 手動合併。

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
