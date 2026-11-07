# 測試案例：gitleaks-classify（全歷史掃描失敗時另產遮蔽密鑰的 JSON 報告並上傳 artifact）

**規格**：`specs/gitleaks-classify/plan.md`（本任務沒有獨立 spec.md，以 plan 為規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

名詞：「報告」＝ gitleaks 掃完後另存的 JSON 檔 `gitleaks-report.json`；「artifact」＝ GitHub Actions 某次執行結束後可下載的附件；「遮蔽」＝ gitleaks 的 `--redact`，把密鑰原文換成 `REDACTED`；「workflow 檔」＝ `.github/workflows/security.yml`；「測試檔」＝ `tests/ci_security_workflow_test.sh`。

標「＊」的自動案：計畫第 3 點寫了這項要求，但計畫的「失敗先行測試」清單沒有單獨列它；executor 須在測試檔補一條斷言（只新增，不改既有檢查）。

維護者原話（plan「維護者原話」）：
1.「需在本機或 CI 加 --report-format json --report-path 上傳 artifact 才能分類，再決定是 .gitleaks.toml allowlist（僅限測試 fixture，每條要附證據）還是真洩漏（若是真金鑰要先通知維護者並輪替）」→ 小項 (a)(b)(c)(d)(e) 對應 TC-001、002／006、009／021、022／004／039。
2.「真機密 → 停下回報（BLOCKED，屬安全事件，不得自行改寫歷史），不寫進 allowlist」；「一律加 `--redact`，日誌不得出現疑似機密原文」；不是必過檢查（`run_all`／`shard` 不動）→ TC-004、005、017、024、028、039、040、043。

## User Story 1 — 全歷史掃描失敗時，仍留下遮蔽過的 JSON 報告並上傳（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話 1(a)；作法 1 | 功能 | workflow 檔已修改 | 找出 `gitleaks` job 裡名為「Scan full history」的步驟那一行指令 | 該行含 `--report-format json` | 自動：`tests/ci_security_workflow_test.sh`（`test_gitleaks_full_scan_writes_json_report`） |
| TC-002 | 原話 1(a)；作法 1 | 功能 | 同上 | 讀同一行指令 | 含 `--report-path`，且路徑值非空、為固定檔名 `gitleaks-report.json` | 自動：同上 |
| TC-003 | 作法 1（沿用原指令、只在後面附加） | 功能 | 同上 | 讀同一行指令 | 行首仍是原樣的 `gitleaks git --redact --no-banner --config .gitleaks.toml`，新旗標接在其後 | 自動：既有 `test_gitleaks_scans`（TC-023..026）仍綠 |
| TC-004 | 原話 1(d)、原話 2「一律加 --redact」；作法 1 | 功能 | 同上 | 列出檔內每一行含 `gitleaks git ` 的指令（全歷史與 PR 兩條） | 每一行都含 `--redact`，且至少兩行 | 自動：`test_gitleaks_report_stays_redacted`、既有 `test_gitleaks_uses_redact`（TC-027） |
| TC-005 | 原話 2；作法 2 | 例外 | 同上 | 在整個 workflow 檔搜尋 `--no-redact` | 找不到任何一處 | 自動：`test_gitleaks_report_stays_redacted` |
| TC-006 | 原話 1(b)；作法 3 | 功能 | 同上 | 在 `gitleaks` job 找 upload-artifact 步驟 | 存在一行 `uses: actions/upload-artifact@<40 位十六進位>  # v數字.數字.數字`（兩個空格、三段版本註解） | 自動：`test_report_is_uploaded_always_as_artifact` |
| TC-007 | 作法 3（不得憑記憶、不得浮動標籤） | 例外 | 同上 | 檢查該 uses 行 | 不含 `@v` 加數字、`@main`、`@master`；完整 40 位 SHA 符合與既有 TC-009 相同的正規式 | 自動：`test_upload_artifact_is_sha_pinned` |
| TC-008 | 作法 3（選主版本 v4 最新穩定版） | 功能 | 同上 | 讀該 uses 行的版本註解 | 版本註解以 `v4.` 開頭 | 自動＊ |
| TC-009 | 原話 1(b)；作法 3 | 功能 | 同上 | 讀 upload-artifact 步驟區塊 | 同一步驟內有 `if: always()`（掃描失敗時也會上傳） | 自動：`test_report_is_uploaded_always_as_artifact` |
| TC-010 | 作法 3 | 功能 | 同上 | 比較上傳步驟的 `path:` 與掃描指令的 `--report-path` 值 | 兩者相同，都是 `gitleaks-report.json` | 自動：`test_report_is_uploaded_always_as_artifact` |
| TC-011 | 作法 3；作法 7 | 功能 | 同上 | 讀上傳步驟的 `name:` | 等於 `gitleaks-report` | 自動＊ |
| TC-012 | 作法 3 | 功能 | 同上 | 讀上傳步驟的 `if-no-files-found:` | 等於 `ignore`（掃描根本沒跑到時，上傳步驟不另外報錯） | 自動＊ |
| TC-013 | 作法 3 | 功能 | 同上 | 讀上傳步驟的 `retention-days:` | 等於 `14` | 自動＊ |
| TC-014 | 作法 3（緊接在掃描步驟之後、同一 job） | 功能 | 同上 | 看 `gitleaks` job 步驟順序 | 上傳步驟緊接在「Scan full history」之後、在「Scan this PR's commits」之前，且都在 `gitleaks` job 內 | 自動＊ |
| TC-015 | 作法 1；既有 TC-011 | 例外 | 同上 | 在整個 workflow 檔搜尋 `continue-on-error`、`\|\| true`、`--no-fail`、`if: false` | 一處都沒有（掃描有洩漏時步驟仍讓 job 變紅；`if: always()` 不算違規） | 自動：既有 `test_no_way_to_turn_checks_off`（TC-011） |
| TC-016 | 作法 3（TC-009 格式） | 功能 | 同上 | 檢查檔內全部 `uses:` 行（含新增的） | 每一行都是 `owner/repo@40位十六進位  # vN.N.N` | 自動：既有 `test_every_uses_is_pinned_to_full_sha`（TC-009） |
| TC-017 | 原話 1「看不到密鑰原文」；作法 2 | 功能 | 本機或草稿分支以同版本 gitleaks 8.30.1 對一個 `AKIA` 形假金鑰實跑一次（帶 `--redact --report-format json --report-path`） | 開啟產出的 `gitleaks-report.json`，搜尋假金鑰原文 | 報告裡找不到假金鑰原文（`Secret`、`Match` 欄為 `REDACTED`）；證據片段貼在 ledger；若找得到則停下回報、不得上傳 | 手動：`docs/TESTING.md`「CI security checks」新段的假金鑰實驗步驟 |
| TC-018 | 原話 1「才能分類」；目標 | 功能 | 同 TC-017 的實跑報告 | 讀報告裡的一筆發現 | 看得到該筆的檔案路徑（`File`）、規則 id（`RuleID`）、`Commit`（另有 `StartLine` 等欄位），足以判斷是測試 fixture 還是真洩漏 | 手動：同上 |
| TC-019 | 作法 3（SHA 查證，不得憑記憶） | 功能 | executor 已選定 upload-artifact 版本 | 看 ledger 的 SHA 查證紀錄 | 記有以 `gh api repos/actions/upload-artifact/git/ref/tags/<tag>` 查出 SHA 的過程（annotated tag 有再解一層），且查到的 SHA 與 workflow 檔所用一致 | 手動：閱卷者核對 ledger 與 workflow 檔（步驟寫在 `docs/TESTING.md` 新段） |
| TC-020 | 完成標準末條 | 功能 | 本任務已合併進 v3 | 在 GitHub 對 v3 手動觸發一次 `security` workflow（`workflow_dispatch`） | 該次執行頁面下方 Artifacts 出現 `gitleaks-report`，且可下載、內容是 JSON 清單（此項不擋合併，由 developer-agent 做） | 手動：`docs/TESTING.md` 新段 |

## User Story 2 — 不放寬、不改別處（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | 原話 1(c)；不做「不加任何 allowlist」 | 不在範圍 | `.gitleaks.toml` 在 origin/v3 的 `[[allowlists]]` 條數已先用 `git show` 確認（目前預期 0） | 數目前 `.gitleaks.toml` 的 `[[allowlists]]` 條數 | 與 origin/v3 相同（0 則仍為 0），沒有新增任何 allowlist | 自動：`test_gitleaks_toml_has_no_new_allowlist` |
| TC-022 | 範圍「不得改 `.gitleaks.toml`」 | 不在範圍 | 同上 | 對 `.gitleaks.toml` 做 `git diff` 比 base | diff 為空 | 手動：`docs/TESTING.md` 新段的範圍核對步驟（`git diff --name-only`） |
| TC-023 | 範圍「不動 pip-audit job」 | 不在範圍 | 同上 | 取 workflow 檔的 `pip-audit` job 區段，與 origin/v3 同檔同區段逐字比對 | 完全相同（鏡像沒有 origin/v3 時印 `skipped` 並視為通過） | 自動：`test_pip_audit_job_unchanged` |
| TC-024 | 原話 2「不是必過檢查」；範圍「不得改 `tests.yml`」 | 不在範圍 | 同上 | 對 `.github/workflows/tests.yml` 做 diff | 無差異 | 自動：既有 `test_existing_tests_yml_untouched`（TC-012/013） |
| TC-025 | 作法 4、不做「不替 PR 掃描產報告」 | 不在範圍 | 同上 | 讀「Scan this PR's commits」步驟 | 仍是原樣：含 `if: github.event_name == 'pull_request'` 與 `--log-opts "origin/${{ github.base_ref }}..HEAD"`，且不含 `--report-format`、`--report-path` | 自動：既有 `test_gitleaks_scans` ＋ executor 補一條「PR 步驟無報告旗標」斷言＊ |
| TC-026 | 作法 3；既有 TC-005／006 | 例外 | 同上 | 檢查頂層與各 job 的 `permissions:` | 整檔只有一個 `permissions:`（頂層），內容恰為 `contents: read`；job 內沒有 `permissions:` | 自動：`test_permissions_stay_read_only_after_report`、既有 TC-005..008 檢查 |
| TC-027 | 作法 3、作法 6（fork 暴露）；既有 TC-007／008 | 例外 | 同上 | 在 workflow 檔搜尋 `secrets.` 與 `pull_request_target` | 兩者都 0 筆；觸發器仍是 `pull_request` | 自動：`test_permissions_stay_read_only_after_report` |
| TC-028 | 不做「不改哪個 job 是必過檢查、不動 `on:`」 | 不在範圍 | 同上 | 檢查 job 名稱與觸發器 | job 仍是 `gitleaks`、`pip-audit`，沒有 `run_all`／`shard`；`pull_request`、`push`（v3, main）、`schedule`、`workflow_dispatch` 都還在，無 `merge_group` | 自動：既有 `test_job_names_do_not_collide_with_required_check`（TC-002）、`test_triggers`（TC-003/004） |
| TC-029 | 不做「不用第三方 action 取代手動安裝的 gitleaks」 | 不在範圍 | 同上 | 檢查 gitleaks 安裝步驟 | 仍是固定版本 8.30.1 ＋ `sha256sum -c` 驗證；無 `latest`；無 `gitleaks/gitleaks-action` | 自動：既有 `test_gitleaks_download_is_verified`（TC-020..022） |
| TC-030 | 範圍「既有 12 項不刪不放寬」 | 功能 | 測試檔已修改 | 比對測試檔與 base，並執行該檔 | 原有 12 個檢查函式與其斷言原封不動（diff 只有新增）；原 12 項輸出 `ok` | 自動：`bash tests/ci_security_workflow_test.sh`（閱卷者另讀 diff 核對） |
| TC-031 | 範圍；失敗先行測試末條 | 功能 | 同上 | 執行測試檔 | 計畫列的 7 個新函式都在檔尾 `for t in ...` 清單裡並輸出 `ok`；總結輸出格式不變（`all ci_security_workflow checks passed`，失敗時 `N check(s) failed`） | 自動：`bash tests/ci_security_workflow_test.sh` |
| TC-032 | 完成標準「`git diff --stat` 只含四處」 | 不在範圍 | 任務完成 | 執行 `git diff --name-only <base>...HEAD` | 檔案只在：`.github/workflows/security.yml`、`tests/ci_security_workflow_test.sh`、`docs/TESTING.md`、`specs/gitleaks-classify/` 之下 | 手動：`docs/TESTING.md` 新段的範圍核對步驟 |
| TC-033 | 不做「實際讀報告、分類 34 筆」 | 不在範圍 | 同上 | 讀本次 diff（含 ledger、文件） | 沒有任何對那 34 筆的分類結論（沒有「這筆是 fixture／真洩漏」的判定），也沒有報告原文貼入 | 手動：閱卷者讀 diff |
| TC-034 | 範圍「不得改 `platform/pip-audit-ignore.txt`、任何 ruleset／required check 設定」 | 不在範圍 | 同上 | 對 `platform/pip-audit-ignore.txt` 做 diff；diff 中找 ruleset 或 required check 設定檔 | 皆無差異、皆不在 diff 內 | 手動：同 TC-032 的範圍核對步驟 |

## User Story 3 — 文件讓人知道怎麼下載、怎麼看、真金鑰怎麼辦（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-035 | 範圍 `docs/TESTING.md`「只加不改」 | 功能 | 文件已修改 | 對 `docs/TESTING.md` 做 diff | 只有新增行；原句「Neither is a required check」與其後的假金鑰手動案（確認日誌顯示已遮蔽）原文不變；新段接在「## CI security checks」一節之後（在下一個標題之前） | 手動：閱卷者讀 `docs/TESTING.md` 該節 |
| TC-036 | 作法 7 | 功能 | 同上 | 讀新段 | 寫明 artifact 名為 `gitleaks-report`，並說明在 Actions 該次執行頁面下方的 Artifacts 下載 | 手動：同上 |
| TC-037 | 作法 7 | 功能 | 同上 | 讀新段 | 含看清單的指令 `jq -r '.[] \| [.RuleID,.File,.Commit] \| @tsv'` | 手動：同上 |
| TC-038 | 範圍「欄位怎麼看」 | 功能 | 同上 | 讀新段 | 說明報告的欄位（至少 `File`、`RuleID`、`Commit`、`StartLine`）各代表什麼，以及密鑰欄已遮蔽 | 手動：同上 |
| TC-039 | 原話 1(e)；裁決 1 | 功能 | 同上 | 讀新段關於真金鑰的處置 | 明寫：判斷是真金鑰就立刻停下、通知維護者、輪替該金鑰 | 手動：同上 |
| TC-040 | 原話 2；作法 7；裁決 1 | 功能 | 同上 | 讀新段 | 明寫：不得自行改寫歷史、不得先寫 allowlist | 手動：同上 |
| TC-041 | 裁決 1「不得把原文貼到任何 ledger／issue／對話」 | 例外 | 同上 | 讀新段與 ledger | 沒有任何指示或範例要人把密鑰原文貼出來；文件內也沒有真實密鑰 | 手動：同上 |
| TC-042 | 驗證方式規則（手動案必須寫在 TESTING.md） | 功能 | 同上 | 讀新段 | 含手動案步驟：(1) 假金鑰實驗與報告檢查（TC-017／018）、(2) 合併後在 v3 手動觸發並確認 artifact（TC-020）、(3) SHA 查證與範圍核對（TC-019／022／032） | 手動：同上 |

## 憲法與安全網

涉及：Safety Net 的憑證規則（密鑰不得被印出）、Development Workflow 對受保護路徑（`.github/`）的規定（附「還能影響什麼」的證明，並過第二道對抗審）、個資（報告含作者 email）、專長守則 backend（日誌與回應不含密鑰、資料結構變動需 migration 或說明）。本任務沒有網頁／API／聊天動作、寫入動作、使用者紀錄，故對等性、跨使用者、確認管道三類不適用。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-043 | Safety Net 憑證規則；原話 2「日誌不得出現疑似機密原文」 | 功能 | 草稿分支上提交一個 `AKIA` 形假金鑰（既有手動案，永不進入合併後歷史） | 看 `gitleaks` job 日誌 | job 變紅，日誌裡該值仍是遮蔽的；同次執行的 artifact 報告裡也找不到原文 | 手動：`docs/TESTING.md`「CI security checks」既有手動案 ＋ 新段 |
| TC-044 | Development Workflow（受保護路徑要附證明）；作法 6 | 功能 | 任務完成 | 讀 ledger 的爆炸半徑證明 | 六項逐項都有：workflow 能做什麼（新增的唯一能力是上傳一個 artifact）、權限（附 `git diff` 證明）、對 fork 的暴露（`pull_request` 非 `_target`、`secrets.` grep 為 0 筆）、報告已遮蔽（引用 TC-017 結果）、不影響必過檢查（`tests.yml` diff 為空）、移除方式 | 手動：閱卷者讀 ledger |
| TC-045 | 憑證與個資規則；作法 2 | 功能 | 同上 | 讀 ledger 的爆炸半徑說明 | 寫明報告含作者 `Author`／`Email` 屬個資，artifact 只有對 repo 有讀取權的人可下載，且（repo 若公開）email 本就在 git log 公開 | 手動：閱卷者讀 ledger |
| TC-046 | 專長守則 backend（資料結構變動需 migration 或說明） | 不在範圍 | 同上 | 讀 diff 檔案清單 | 沒有 `platform/`、資料庫、migration 相關檔案被改（本案不涉及資料結構） | 手動：同 TC-032 的範圍核對步驟 |
