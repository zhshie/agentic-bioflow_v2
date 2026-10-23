# nano4 站台設定檔、CE 範本與三種費率 progress ledger

- [x] configs/sites/nchc-nano4.config: fallback when the site modules are absent (slurm, resourceLimits, singularity, queue from SLURM_PARTITION, account from SLURM_ACCOUNT; no box table)
- [x] configs/sites/nchc-nano4-ce.json: CE template, passes compute_envs.clean (slurm-platform); no `_comment` key because the schema refuses unknown keys
- [x] configs/sites/su_rates.json: sites.nano4 (twd_per_su nstc 0.1 / academic 0.2 / industry 0.37; partitions `ngs*` 1, `big-mem*` 7); T3 and nchc sections untouched
- [x] platform/abf_platform/su.py: trailing `*` partition keys (exact first, then the longest prefix); a site with twd_per_su also returns `twd`
- [x] platform/tests/test_estimate_su.py: N4-xx tests added; existing assertions unchanged
- [x] specs/estimate-su/ledger.md: sources of the two nano4 factors; docs/TESTING.md: the manual check

## 自裝 Nextflow 時怎麼改 CE (self-installed Nextflow fallback)

If the site's Nextflow module does not work on nano4, copy `nchc-nano4-ce.json` and change two things: set `modules` to `[]`, and add two
`environment` entries (head and compute both true): `PATH=/work/u9613010/nextflow/bin:$PATH` and
`NXF_PLUGINS_DIR=/work/u9613010/.nextflow/plugins`. The `docs/SETTINGS.md` text is written in L3; it copies this section.

## Migration

不需要 migration: only JSON settings files and `su.py` changed; no database table or column was touched.
