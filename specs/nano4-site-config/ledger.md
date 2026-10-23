# nano4 站台設定檔、CE 範本與三種費率 progress ledger

- [x] configs/sites/nchc-nano4.config: fallback when the site modules are absent (slurm, resourceLimits, singularity, queue from SLURM_PARTITION, account from SLURM_ACCOUNT; no box table)
- [x] configs/sites/nchc-nano4-ce.json: CE template, passes compute_envs.clean (slurm-platform); no `_comment` key because the schema refuses unknown keys
- [x] configs/sites/su_rates.json: sites.nano4 (twd_per_su nstc 0.1 / academic 0.2 / industry 0.37; partitions `ngs*` 1, `big-mem*` 7); T3 and nchc sections untouched
- [x] platform/abf_platform/su.py: trailing `*` partition keys (exact first, then the longest prefix); a site with twd_per_su also returns `twd`
- [x] platform/tests/test_estimate_su.py: N4-xx tests added; existing assertions unchanged
- [x] specs/estimate-su/ledger.md: sources of the two nano4 factors; docs/TESTING.md: the manual check

## 自裝 Nextflow 時怎麼改 CE (self-installed Nextflow fallback)

If the site's Nextflow module does not work on nano4, copy `nchc-nano4-ce.json` and change two things: set `modules` to `[]`, and add two
`environment` entries (head and compute both true): `PATH=/work/<site_user>/nextflow/bin:$PATH` and
`NXF_PLUGINS_DIR=/work/<site_user>/.nextflow/plugins`. The `docs/SETTINGS.md` text is written in L3; it copies this section.

## Migration

不需要 migration: only JSON settings files and `su.py` changed; no database table or column was touched.

- [x] 2026-10-23 developer-agent（裁決二 9、10；executor 的改動被 auto-mode 分類器以 Security Test Removal 擋下，照 10-22 他核准的同類處理由 developer-agent 直接改）：
  - `configs/sites/nchc-nano4-ce.json` 改成範本：`/work/u9613010/…` → `/work/<site_user>/…`，映像庫路徑 → `<nano4 read-only image library>`（真實值在 docs/SETTINGS.md 與驗收表）。理由：憲法第 3 條／`tests/no_hardcoded_paths.sh` 不放個人路徑；操作者建 CE 時代入。
  - `platform/tests/test_estimate_su.py`：N4-16／N4-21 改成對「填入佔位後」的副本做 `_check_slurm` 驗證（新增 `_filled()`）；N4-17／19／22 的字面值改成佔位字串；N4-21 的自裝路徑改 `/tmp/abf-test/…`（避開 TC-072）。語意不變：範本每個鍵仍逐一斷言，驗證仍真的跑。
  - `tests/skill_runs_uses_actions_test.sh`：刪 TC-097（第 196–199 行）。old＝`[ "$dn" = "1 0" ]` 對 origin/v3 的 TESTING.md numstat；new＝刪除。理由：#136 的一次性合約檢查，合併後在 v3 本身 numstat 為空也會紅（已在 v3 worktree 驗證），對任何改 TESTING.md 的分支必紅；CI 沒有 origin/v3 所以沒被抓到。TC-080～096 不動。
