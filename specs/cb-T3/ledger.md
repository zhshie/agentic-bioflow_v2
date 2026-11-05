# cb-T3 ledger

Base: origin/v3 62c91293de611d265d8fbf3d0a128bea849be98c

## Caller search (git grep at base)
docs/reports/sweep-2026-11.md:100:- `scripts/utils/file_discovery.py:133` `find_index_file`、`:172` `detect_input_type`：全 repo 只有定義；同檔的 `discover_files` 才被 `scripts/generate_samplesheet.py:46` 使用。
docs/reports/sweep-2026-11.md:119:- `scripts/utils/file_discovery.py`：檔名未被測試提及（但 `tests/generate_samplesheet_test.sh` 會間接走 `discover_files`）；其中 `find_index_file`、`detect_input_type` 同時是第 5 類的死碼，`count_files_by_type` 無測試名稱命中。
scripts/utils/file_discovery.py:133:def find_index_file(alignment_file: str) -> Optional[str]:
scripts/utils/file_discovery.py:172:def detect_input_type(directory: str) -> str:

## RED (unchanged code): tests/file_discovery_test.sh
```
discover fastq: all four spellings, recursive, sorted by full path           ok
discover default type is fastq                                               ok
discover bam ignores .bai index and other files                              ok
discover cram                                                                ok
FileInfo: stem strips the matched extension, case kept                       ok
FileInfo: size and file_type                                                 ok
discover: symlink to an already-seen file is not listed twice                ok
discover: follow_symlinks=False does not descend into a linked directory     ok
discover: empty directory gives an empty list                                ok
discover: unknown type raises ValueError naming the type                     ok
discover: not a directory raises ValueError                                  ok
count: one entry per supported type                                          ok
count: empty directory is all zeros                                          ok
count: a missing directory is zeros, not an exception                        ok
find_index_file is not defined (no caller)                                   FAIL: got 'True', wanted 'False'
detect_input_type is not defined (no caller)                                 FAIL: got 'True', wanted 'False'
2 failed
```

## Mutation proof (behaviour tests pass on unchanged code; each mutant restored with git checkout, never committed)

Mutant 1: discover_files case-sensitive endswith(ext) -> FAIL lines:
```
discover fastq: all four spellings, recursive, sorted by full path           FAIL: got 's1_R1.fastq.gz,s1_R2.fq.gz,s3.fq', wanted 's2.FASTQ,s1_R1.fastq.gz,s1_R2.fq.gz,s3.fq'
discover default type is fastq                                               FAIL: got '3', wanted '4'
FileInfo: stem strips the matched extension, case kept                       FAIL: got 's1_R1 s1_R2 s3 .fastq.gz .fq.gz', wanted 's2 s1_R1 s1_R2 .fastq .fastq.gz'
FileInfo: size and file_type                                                 FAIL: got '0 fastq', wanted '4 fastq'
discover: symlink to an already-seen file is not listed twice                FAIL: got '3', wanted '4'
discover: follow_symlinks=False does not descend into a linked directory     FAIL: got '3 4', wanted '4 5'
count: one entry per supported type                                          FAIL: got '{'fastq': 3, 'bam': 2, 'cram': 1}', wanted '{'fastq': 4, 'bam': 2, 'cram': 1}'
find_index_file is not defined (no caller)                                   FAIL: got 'True', wanted 'False'
detect_input_type is not defined (no caller)                                 FAIL: got 'True', wanted 'False'
```
Mutant 2: count_files_by_type len(files)+1 -> FAIL lines:
```
count: one entry per supported type                                          FAIL: got '{'fastq': 5, 'bam': 3, 'cram': 2}', wanted '{'fastq': 4, 'bam': 2, 'cram': 1}'
count: empty directory is all zeros                                          FAIL: got '{'fastq': 1, 'bam': 1, 'cram': 1}', wanted '{'fastq': 0, 'bam': 0, 'cram': 0}'
find_index_file is not defined (no caller)                                   FAIL: got 'True', wanted 'False'
detect_input_type is not defined (no caller)                                 FAIL: got 'True', wanted 'False'
```
Mutant 3: symlink dedupe disabled -> FAIL lines:
```
discover: symlink to an already-seen file is not listed twice                FAIL: got '5', wanted '4'
discover: follow_symlinks=False does not descend into a linked directory     FAIL: got '5 6', wanted '4 5'
find_index_file is not defined (no caller)                                   FAIL: got 'True', wanted 'False'
detect_input_type is not defined (no caller)                                 FAIL: got 'True', wanted 'False'
```

## Full suite at eb644ae4 (code HEAD before this ledger update)
NOT GREEN: 134/142 passed, 8 failed. All 8 are environment failures unrelated to this change; file_discovery_test.sh and generate_samplesheet_test.sh pass.
Shell tests agent_ctl_connection_id_test, why_pending_test, wsl_bridge_test also fail identically on an untouched origin/v3 worktree (USER unset, no scheduler, MSYS probe). Platform shards (clock, 4, 5, 6, 7) fail on _winapi import, root-readable cache, nf2 wrapper fixtures, CLI help snapshot - none touch scripts/utils.
```
FAIL       agent          not running - Platform will show no outputs (scripts/on_site.sh --script scripts/agent_ctl.sh start)
FAIL       resources      tar: Child returned status 141
FAIL       compute-env    ce is 'unreachable'>>
missing rsync on MSYS is FAILed by name                    ok
and it says plainly that Git Bash ships none               ok
and gives an install route rather than nothing             ok

-- (i) install_deps.sh: tw on MSYS is named plainly, not folded into 'unknown platform' --
install_deps.sh --cli-only fails cleanly, not silently     ok
it names the gap as unmeasured (R4), a real answer         ok
and gives the Windows asset to fetch by hand               ok
it does not fall back to the generic unknown-platform text ok
shim does not run wsl.exe from the caller's own cwd        ok
and lands in a directory that exists                       ok
only settings.sh decides whether the bridge is in play     ok
and nothing hardcodes the control-path default beside it   ok

3 failed

134/142 passed, 8 failed
```
