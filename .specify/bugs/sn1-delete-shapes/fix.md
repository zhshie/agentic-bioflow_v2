# Fix: sn1-delete-shapes

- **Branch**: `fix/gates-audit2`. RED 210db2a; GREEN **ca7087d** (committed by mistake with the RED message of 210db2a; the message it should have carried is the "What changed" list below); RED 793fa31 / fix 8781ce3 (rclone remote paths, found by the verdict diff).
- **Changed**: `hooks/confirm_cleanup.sh`; `tests/confirm_cleanup_test.sh` (section "SN1: delete shapes the guard did not see", 81 cases with their controls).

## What changed

Each shape is read for the words it really removes; those are judged as an `rm` target would be (`judge_word`: quote characters dropped, backslashes read both as separators and as escapes, a brace word expanded, a relative path also resolved against the working folder). Additive: the rules that were there still run on the same segment.

| shape | judged | verdict on a protected target |
|---|---|---|
| `tar … --remove-files` (also abbreviated, old-style `tar cf A …`) | every source; not the archive (`-f`, `--file`, `f` in an old-style key), not the `-C` folder or another option's value; `-T`/`--files-from`: unknown | deny; work/ ask; `-T` ask |
| `zip -m` / `--move` | every name after the zip file; not `-x`/`-i` patterns; `-@`: unknown | deny |
| `rclone purge/delete/deletefile/rmdir/rmdirs` | every path, with and without a `remote:` prefix, never joined to the working folder | deny |
| `rclone sync` | the destination | deny |
| `rclone move/moveto` | the sources, as an `mv` source (E9) | ask |
| node / ruby / pathlib | `.rm(`, `.rmdir(`, `.unlink(`, node `*Sync(`, Ruby `File/Dir.delete(`, `FileUtils.rm*`/`remove*` (with or without parentheses), bare `rm_rf(`, `remove_dir(` join `RE_CODE_DEL` | ask (as python already did) |
| brace words | expanded as bash does: lists, nesting, `a..z` / `1..9` sequences, at most 64 words (more: unknown, ask); the old flattening is kept | deny |
| a never-delete name in other case (`RESULTS`) | compared ignoring case where the file system does: Git Bash, Cygwin, macOS, or a Windows-shaped path (`C:/`, `/mnt/c/`, `/cygdrive/c/`) from anywhere; elsewhere a different folder that is the same one on such a system | deny there, ask elsewhere |
| `ln -f` with `-n`/`-T` | a link name that IS a guarded folder; without `-n`/`-T` ln writes INTO a folder (staging a link in rawdata/), which stays quiet | deny; work/ ask |
| `install -d` with `-m`/`-o`/`-g` | a protected folder itself | ask (it removes nothing; mode 000 locks everyone out) |
| `: > f`, `> f`, `true > f`, `cat /dev/null > f`, `echo -n > f`, `printf > f` | the redirect targets, as `truncate -s 0` | deny; work/ ask |
| a recursive delete (`rm -r`, `Remove-Item -Recurse`, `rd /s`, `find … -delete`/`-exec rm`) of a folder that holds protected ones | by the deployment's layout (`…/lab_runs/<member>`, `…/projects[/<p>]`, `…/runs[/<r>]`) or, for an absolute path here, by its children | deny |
| `find` from such a folder with a name/path/depth filter | deny when the filter names sequencing files, otherwise ask; a sequencing-file filter from a folder the guard cannot place: ask (`/tmp`, `/var/tmp`, `$TMPDIR` unchanged: warn) | |

Every new trigger joined the large-input filter of #62 (`RE_TRIGGER`, `CW_HANDLED`), and the whole section also passes behind a large here-doc.

## Changes to RED expectations, and why

- `ln -sf /tmp/x <run>/rawdata` was written as deny. Without `-n`/`-T`, GNU ln creates the link INSIDE an existing folder (or a link to one); it replaces nothing. The case became `ln --force --no-dereference -s …` (deny), and the original shape a control (pass: it is how rawdata/ is staged).
- Case folding first covered every rule; on Git Bash that made `C:/Users/me/Documents/Work/x` a Nextflow `work/` delete. It now covers only the never-delete names (protected, shared, plugins); a control pins the Windows `Work` folder.

## Evidence

- RED 210db2a: 48 failures. GREEN: all pass in WSL; native Git Bash probes: `RESULTS` and `Analysis/x` deny there (ask in WSL), `C:/…/Results` deny everywhere.
- **Verdict diff against c018c15** (`.specify/bugs/gate-speed/verdict-diff/` harness, confirm_cleanup only, 1011 payloads: every payload the gate tests feed the hooks plus the harness's harmless and odd shapes; contexts in use / not in use / no jq / failing jq; 4108 runs): 69 different, all in the in-use context. 4 changed text only (the work/ ask now carries the warnings). 60 are the new cases of this record and of nextflow-clean-unconfirmed, as intended. The other 5: in that context the working folder is literally named `work`, so `rm -f a.fastq.gz`, `rm sample.fastq.gz` and `find /tmp/x -name '*.fastq.gz' -delete` (whose pattern word is judged as a relative path, as before) were work/ deletes that only warned; with the SN2 ordering fix of nextflow-clean-unconfirmed they ask. Two rclone remote paths read as under `work/` - a bug, fixed in 8781ce3 with two controls. (One of the new cases, `find . -name '*.fq.gz' -delete`, denies in that context because the harness's folder holds an `analysis/`.) Not in use, no jq, failing jq: identical. (That run predates jq-broken-cleanup; see its fix.md.)
- **Not changed**: `mv`/`rclone move` of a protected folder still asks (E9); `resul*`, `$(…)`, `"$R"` targets still ask; `git clean -fdx <run>` still asks.
- **Not done (maintainer's call)**: `apptainer`/`singularity cache clean -f` and `rm -rf ~/.apptainer/cache` (a personal cache, not the lab's shared library) pass; `gzip` replacing a file by its compressed copy; `chmod`/`chown` on a protected folder; `mv RESULTS x` on a case-insensitive system.
