# 測試案例總覽：憲法 4.0.0 修訂（唯一的提交路徑，綁在使用者確認之後）

狀態：合約已確認（2026-10-11，verifier；依計畫 Revision 2）

**計畫**：`.specify/amendments/4.0.0-launch-path/plan.md`（含 Revision 2，覆蓋下文）　**明細**：`test-case.md`

## 這份合約怎麼來的

第一輪審查（2026-10-11）找出四項 must-fix：
- 「exactly one」與檢查不一致；
- `handlers.py` 有兩處誤報；
- 版本釘字漏列；
- 確認測試綁定太弱。

計畫 Revision 2 四項都答覆，複核後成立，沒有新的 must-fix。

案例已對齊 Revision 2：
- 「至多一條」；
- 第二筆條目的失敗訊息；
- 路徑限定的失敗訊息；
- `LAUNCH_ALLOW_EXTRA` 只在暫存樹生效。

## 一眼看完

| 組別 | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 憲法 3.0.0 → 4.0.0 | 11 | 1 | 0 | 12 |
| US2 — 檢查加強 | 16 | 3 | 0 | 19 |
| US3 — 引用原則 2 的文件 | 6 | 1 | 0 | 7 |
| US4 — 他的話 | 2 | 0 | 0 | 2 |
| 憲法與安全網 | 0 | 8 | 0 | 8 |
| US5 — 不在範圍 | 0 | 0 | 6 | 6 |
| **合計** | 35 | 13 | 6 | 54 |

自動驗證 26 條、手動驗證 28 條（同時有自動與手動部分的算手動）。
- 自動項目是 TC-001、004、005、006、007、008、013、014、015、016、017、018、019、025、026、027、028、029、030、031、032、033、041、043、047、052。
- 手動項目是 TC-002、003、009、010、011、012、020、021、022、023、024、034、035、036、037、038、039、040、042、044、045、046、048、049、050、051、053、054。
- 自動項目由下列測試承擔：
  - `tests/no_second_run_state_test.sh` 的自測區（新增案例）
  - `tests/platform_direction_docs_test.sh`
  - `tests/constitution_scope_test.sh`
  - `tests/constitution_checks_exist_test.sh`
  - `tests/platform_test.sh`
  - CI 的 `tests/run_all.sh`
- 手動項目由驗收者讀 diff、跑兩個分支比對、或在副本做突變，不另加 `docs/TESTING.md` 步驟。

## 覆蓋檢查

- 計畫「What changes」各項全部有案例：
  - 1 原則 2 新文字 → TC-004..008、012
  - 1 理由句 → TC-009
  - 2 檢查（掃描一涵蓋 `platform/`、`platform/tests/` 排除、掃描二至四不變、`LAUNCH_ALLOW`、新自測、檔頭）→ TC-013..021、029、030
  - 3 文件（TC-004 釘字、README、hook 不動、PRINCIPLES／CLAUDE、ROADMAP）→ TC-032..038
  - 4 修訂紀錄與版本 → TC-001..003、010
  - 4 Safety Net 不變 → TC-041、045
- Revision 2 全部有案例：
  - 第 1 項 → TC-005、011、026
  - 第 2 項 → TC-022、023、031
  - 第 3 項 → TC-033、035
  - 第 4 項 → TC-025、027、028、029
  - should-fix：
    - ROADMAP 階段 1 句 → TC-036
    - 007b 需修的兩條平台測試記入紀錄 → TC-002、046
    - 檔頭「a net, not a proof」 → TC-021
- 計畫「Not in this PR」四項全部有不在範圍案例：
  - 啟動 job → TC-049
  - 確認步驟形式 → TC-050
  - 閘門移進工具層 → TC-051
  - 其他等待中的原則 → TC-052
  - 另有 release → TC-053、007b／009 spec → TC-054
- 計畫 Verification 的突變與 `run_all` 不比 main 差 → TC-024、TC-047。
- 他的話三句（給方向，不是輸入）→ TC-003、039、040。

## 已知缺口（給 executor，不擋合約）

- `handlers.py` 的改寫範例若用 `"sbatch squeue sinfo".split()`，字串以 `sbatch` 開頭，仍會中掃描一的引號規則。
  - 字串開頭須是別的字，例如 `"connect work_dir sbatch ..."`。
  - TC-022 以「對真實 repo 跑檢查結束碼 0」把關。
- 計畫 Revision 2 以下的正文仍留舊句「exactly one」與舊釘句。
  - 以 Revision 2 和本合約為準：4.0.0 的條文與釘字一律用 `There MAY be at most one submission path of our own`。
- `platform/tests/test_scope.py` TC-071 與 `platform/tests/test_station_static.py` TC-084 在本 PR 不動（TC-046 要求零差異）。
  - 它們是 007b 的待辦，須記入 4.0.0 修訂紀錄（TC-002）。
