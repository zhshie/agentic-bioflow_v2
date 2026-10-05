# Fix: backslash-delete-shapes

- **Branch**: `fix/gates-audit2` (RED 298ac9b, GREEN 1cd7634)
- **Changed**: `hooks/confirm_cleanup.sh`; `tests/confirm_cleanup_test.sh` (end of the SN1 section, 10 cases).

## What changed

- `RE_FIND_DEL`, `RE_RSYNC_DEL`, `RE_RSYNC_RSF`, `RE_NFCLEAN`, `RE_TAR_RM`, `RE_ZIP_MV`, `RE_RCLONE`, `RE_LN_F`, `RE_INSTALL_D` take an optional `\` before the name, as `RE_DELVERB` and `RE_MV` already did.
- `past_word` and the nextflow word search drop a leading `\`, so the words after `\tar`, `\zip`, `\rclone`, `\ln`, `\install`, `\nextflow` are read.
- The large-input filter needed no change: `RE_TRIGGER` is built from the same variables, and the awk command word already drops the `\`. `tests/confirm_cleanup_behind_heredoc_test.sh` reruns the new cases there.

## Evidence (WSL)

| Command | Before | After |
|---|---|---|
| `\nextflow clean -f` | pass | ask |
| `\tar --remove-files -cf a.tar results` | pass | deny |
| `\zip -m a.zip rawdata` | pass | deny |
| `\rclone purge results` | pass | deny |
| `\ln -sfn /tmp/x rawdata` | pass | deny |
| `\find /work/u/lab_runs/p -delete` | pass | deny |
| `\rsync -a --delete e/ results/` | pass | deny |
| `\install -d -m 000 results` | pass | ask |

Controls `\tar -cf` and `\rclone copy` stay pass. RED: 8 of these fail in `confirm_cleanup_test.sh` and again behind the here-doc; GREEN: both all passed.
