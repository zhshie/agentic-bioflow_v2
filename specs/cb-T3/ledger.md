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
