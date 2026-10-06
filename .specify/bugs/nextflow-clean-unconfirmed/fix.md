# Fix: nextflow-clean-unconfirmed

- **Branch**: `fix/gates-audit2` (RED 1293314, GREEN in the commit after it)
- **Changed**: `hooks/confirm_cleanup.sh`; `tests/confirm_cleanup_test.sh` (21 cases, section "SN2: work/ deletes that ran without the confirmation").
- **Approach**:
  - A segment whose command is `nextflow` (as the command word, or behind a wrapper such as `srun`) is read word by word: past `nextflow`, past its global options and their values (`-log x`, `-c x`, `-C x`, `-config x`, `-syslog x`, `-trace x`), the first other word is the subcommand. If it is `clean` and `-f`/`-force`/`--force` follows, and the segment is not a dry run (`-n`/`-dry-run`/`--dry-run`, read by the existing `is_dry_run` after the word `clean`), it is recorded as a work/ delete, so it gets the same ask as `rm -rf work/`. Its remaining words are run names and are not judged as paths. `nextflow` is in the large-input filter's command words and `RE_NFCLEAN` in its triggers (#62).
  - The two warnings that used to end the hook before the work/ ask (an overwrite under rawdata/ or results/, a sequencing-file name) are now notes: appended under "Also:" to the work/ ask when there is one, printed as the warning otherwise.
- **Red -> green**: 13 of the new cases failed on 935328a (9 `nextflow clean -f` shapes passed; 3 work/ deletes only warned; the ask text check). All pass after the fix, and again behind a large here-doc (`tests/confirm_cleanup_behind_heredoc_test.sh`).
- **Behaviour change beyond the two bugs**: when an overwrite and a sequencing-file name occur in the same command with no work/ delete, the warning now carries both texts (before: the first only).
- **Not changed**: `nextflow clean` without `-f`, or with `-n`, stays silent; `nextflow drop` is not judged (it removes a downloaded pipeline, not a protected folder).
