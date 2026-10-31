# slurm-url-cells

Tier: B (non-UI; maintainer ordered this fix 2026-10-31). Kind: backend. Branch: fix/slurm-url-cells, base v3.

## Goal
Let a Slurm launch (MCP `launch`, terminal `abf-platform launch`) carry a samplesheet whose path cells are `https://` or `http://`
addresses, so nf-core's own test data (e.g. `https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/.../SRR6357070_1.fastq.gz`)
can be run on nano4 without copying it into /work/u9613010. Nextflow downloads such cells itself.

## Maintainer's words (verbatim)
1. 「修正下面這個問題，我要馬上用MCP跑其他pipline」
2. 「abf 的限制：launch 一定要附樣本表，而且表裡的檔案路徑必須在 /work/u9613010 底下。nf-core 內建的 -profile test 是靠網址取得樣本表 … 所以送不出去。」

## Today's behaviour (the bug)
`platform/abf_station/launch.py::_check_samplesheet` (around line 363) runs every cell returned by `path_cells` through
`rules.path_problem`; a cell `https://…` in a column like `fastq_1` is not an absolute path, so the launch is refused.
A params value that is a scheme address is already NOT judged as a path (`platform/abf_launch/build.py::_param_path`, the
SCHEME rule, 116b ruling). This task gives samplesheet cells of the Slurm launch the same rule.

## Scope
- `platform/abf_station/launch.py`: the Slurm samplesheet check only (`_check_samplesheet`). A cell matching
  `^https?://` (case-insensitive) with a host is accepted as written and not checked against read roots. Every other
  cell keeps today's checks word for word. `file:`, `s3://`, `gs://`, `az://` and any other scheme stay refused as today.
- Whatever else in the Slurm launch path must agree (the platform's `build._confine`, the agent's rebuild/verification of the
  bundle at job time, any staging of path cells on the site) so that a URL cell reaches the samplesheet.csv written on the site
  unchanged. Find these with `git grep -n "path_cells("`.
- Credential check still applies to URL cells (a URL containing something that looks like a credential is refused; reuse the
  existing credential detector).
- New test file `platform/tests/test_slurm_url_cells.py`.
- `PITFALLS.md` or docs: one line in the Slurm launch docs that https cells are passed to Nextflow as-is.

## Not in scope (must stay refused, existing tests must stay green and unchanged)
- Google Batch / AWS launch checks (launch.py around lines 823, 1001, 1183, 1377).
- Datasets and web upload flows: `test_web_upload.py` TC-061, `test_aws_upload.py:635`, `test_cloud_upload.py:262`,
  `test_datasets.py:339` keep refusing URLs.
- No `-profile` option, no change to MCP tool signatures.

## Failing-first tests
1. Slurm launch with header `sample,fastq_1,fastq_2,strandedness` and two https cells → bundle built; samplesheet.csv in the
   bundle holds the URLs byte for byte.
2. Same via the MCP action `request_launch` with `samplesheet_text` → reaches the pending/confirm step (not "未送出").
3. `http://` accepted; `file:///etc/passwd`, `s3://b/x`, `ftp://h/x`, `https:///nohost` → refused (message unchanged from v3 where one exists).
4. A local cell outside read roots in the same sheet → still refused with today's exact sentence.
5. A URL cell carrying a credential-looking token (e.g. `https://h/x?AKIA` + 16 caps) → refused, token never echoed.
6. Mixed sheet (one https cell, one local cell inside read roots) → accepted.
7. Google Batch / AWS launch with an https cell → still refused as on v3.

## Done when
All the above green; `tests/run_all.sh` green (environment-red per README is noted in the ledger); diff only adds a branch for URL cells.

## Rulings
1. Run the full suite with run_in_background and `tests/run_all.sh --timeout 900`.
2. WSL `constitution_scope_test.sh` red from a Windows-created worktree = environment; CI decides.
