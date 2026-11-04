# cb-T2 ledger

Base: `origin/v3` @ 62c91293de611d265d8fbf3d0a128bea849be98c. Task: table tests for every public name in `scripts/utils/schema_roles.py`.

## 1. Unchanged code: the new file passes

`bash tests/schema_roles_unit_test.sh` on unchanged `schema_roles.py`: exit 0, last lines:

```

205/205 cases ok
schema_roles unit tests: all passed
```

## 2. Mutation proof (RED substitute, RULES 5.3)

Code is already right, so each mutant below was applied temporarily to `scripts/utils/schema_roles.py` (one exact-text replacement each, applied by a throwaway script outside the repo), the new test file was run, and the file was restored from a saved copy after the whole run. Nothing in `scripts/` is committed: `git diff origin/v3 -- scripts/` is empty. "failing cases" is the number of `FAIL` lines; the first failing case is shown.

Result: 96 mutants, 95 killed (new test exits non-zero), 1 survived (equivalent, see below).

| # | mutant | exit | failing cases | first failing case |
|---|---|---|---|---|
| 1 | schema_properties: prefer top-level over items | 1 | 73 | schema_properties: items.properties |
| 2 | schema_properties: drop dict check on items.properties | 1 | 2 | schema_properties: items.properties not a dict falls back to top-level |
| 3 | schema_properties: top-level returns {} always | 1 | 6 | schema_properties: top-level properties |
| 4 | _patterns: ignore anyOf/oneOf/allOf | 1 | 13 | is_fastq_column: anyOf fastq + empty-string branch (nf-core optional column) -> True |
| 5 | _patterns: drop allOf | 1 | 2 | is_fastq_column: allOf with fastq branch -> True |
| 6 | _patterns: drop oneOf | 1 | 2 | is_fastq_column: oneOf with fastq branch -> True |
| 7 | _patterns: no recursion | 1 | 2 | is_fastq_column: nested anyOf inside anyOf -> True |
| 8 | _patterns: top-level pattern ignored | 1 | 59 | is_fastq_column: plain fastq.gz pattern -> True |
| 9 | _accepts_only_fastq: any->all for fastq names | 1 | 57 | is_fastq_column: plain fastq.gz pattern -> True |
| 10 | _accepts_only_fastq: use match not search | 1 | 6 | is_fastq_column: unanchored fq.gz pattern (search, not match) -> True |
| 11 | _accepts_only_fastq: ignore non-fastq rejection | 1 | 19 | is_fastq_column: catch-all ^\S+$ accepts .txt -> False |
| 12 | _accepts_only_fastq: reject only if all non-fastq match | 1 | 6 | is_fastq_column: fastq + bam in one pattern -> False |
| 13 | _accepts_only_fastq: bad regex counts as fastq | 1 | 2 | is_fastq_column: invalid regex -> False |
| 14 | _NOT_FASTQ_NAMES: drop reads.bam | 1 | 2 | is_fastq_column: fastq + bam in one pattern -> False |
| 15 | _NOT_FASTQ_NAMES: drop reads.fa.gz | 1 | 1 | is_fastq_column: fq.gz or .fa.gz -> False |
| 16 | _FASTQ_NAMES: drop reads.fq.gz | 1 | 3 | is_fastq_column: unanchored fq.gz pattern (search, not match) -> True |
| 17 | is_fastq_column: all->any over patterns | 1 | 5 | is_fastq_column: anyOf fastq branch + bam branch -> False |
| 18 | is_fastq_column: empty pattern list counts | 1 | 31 | is_fastq_column: no pattern at all -> False |
| 19 | is_mixed: drop 'not all' | 1 | 38 | is_mixed_reads_column: fastq only -> False |
| 20 | is_mixed: any->all first clause | 1 | 4 | is_mixed_reads_column: fastq branch + bam branch -> True |
| 21 | _is_file_column: drop format file-path | 1 | 4 | infer_roles: ... candidates are non-file columns only (unknown ones included), --columns order |
| 22 | _is_file_column: drop exists | 1 | 3 | infer_roles: ... candidates are non-file columns only (unknown ones included), --columns order |
| 23 | _is_file_column: drop fastq | 1 | 4 | other_file_columns: file columns that are not sample/R1/R2, in --columns order |
| 24 | _is_file_column: no dict guard | 1 | 0 | - |
| 25 | _meta: bare string ignored | 1 | 2 | infer_roles: meta bare string id marks the sample column |
| 26 | _meta: list ignored | 1 | 50 | infer_roles: paired schema, all columns |
| 27 | _meta: keep non-string list items | 0 | 0 | - |
| 28 | _SAMPLE_META: drop sample | 1 | 2 | infer_roles: meta list [sample] marks the sample column |
| 29 | _SAMPLE_META: drop id | 1 | 14 | infer_roles: paired schema, all columns |
| 30 | _SAMPLE_META: substring match | 1 | 1 | infer_roles: meta exact match, not prefix (samples) does not mark it |
| 31 | infer: sample_cols != 1 -> < 1 | 1 | 0 | - |
| 32 | infer: sample candidates all wanted | 1 | 1 | infer_roles: ... candidates are the marked ones, in --columns order |
| 33 | infer: no-sample candidates include file cols | 1 | 10 | infer_roles: meta list of other keys does not mark it |
| 34 | infer: non_file uses wrong predicate | 1 | 11 | infer_roles: meta list of other keys does not mark it |
| 35 | infer: use columns order for fastq | 1 | 3 | infer_roles: schema order decides R1/R2, not --columns order |
| 36 | infer: ambiguity judged on subset only | 1 | 0 | - |
| 37 | infer: ambiguity threshold >3 | 1 | 1 | infer_roles: ... why counts the columns |
| 38 | infer: ambiguity threshold >1 | 1 | 1 | infer_roles: ... why counts the columns |
| 39 | infer: >2 candidates always all_fastq | 1 | 1 | infer_roles: asking for a subset of >2 fastq columns does not resolve it |
| 40 | infer: >2 no fallback | 1 | 1 | infer_roles: >2 fastq in schema, none requested -> candidates fall back to all of them |
| 41 | infer: mixed check removed | 1 | 0 | - |
| 42 | infer: mixed only among wanted | 1 | 0 | - |
| 43 | infer: mixed cands in wanted order | 1 | 1 | infer_roles: ... candidates in schema order |
| 44 | infer: mixed cands drop fallback | 1 | 1 | infer_roles: ... none requested -> candidates fall back to all fastq-only + mixed columns |
| 45 | infer: mixed cands exclude mixed | 1 | 2 | infer_roles: ... candidates in schema order |
| 46 | infer: single fastq gives read2 same | 1 | 12 | infer_roles: single-end (only fastq_1 requested; schema has two) -> read2 None |
| 47 | infer: pair swapped | 1 | 16 | infer_roles: paired schema, all columns |
| 48 | infer: zero fastq candidates incl. sample | 1 | 1 | infer_roles: ... candidates are the requested columns minus the sample, in --columns order |
| 49 | infer: zero fastq -> Roles | 1 | 0 | - |
| 50 | other_file: include roles | 1 | 5 | other_file_columns: file columns that are not sample/R1/R2, in --columns order |
| 51 | other_file: ignore read2 | 1 | 3 | other_file_columns: file columns that are not sample/R1/R2, in --columns order |
| 52 | other_file: schema order | 1 | 1 | other_file_columns: --columns order, not schema order |
| 53 | other_file: all columns not just file | 1 | 3 | other_file_columns: file columns that are not sample/R1/R2, in --columns order |
| 54 | parse_roles: no trim | 1 | 0 | - |
| 55 | parse_roles: split on last = | 1 | 1 | parse_roles: a value containing '=' keeps the rest and then fails the column check |
| 56 | parse_roles: skip no-= check | 1 | 1 | parse_roles: an item without '=' is refused |
| 57 | parse_roles: unknown role allowed | 1 | 2 | parse_roles: an unknown role is refused |
| 58 | parse_roles: duplicate allowed | 1 | 2 | parse_roles: the same role twice is refused |
| 59 | parse_roles: empty value allowed | 1 | 2 | parse_roles: a role with an empty column is refused |
| 60 | parse_roles: no sample requirement | 1 | 3 | parse_roles: sample missing |
| 61 | parse_roles: no read1 requirement | 1 | 3 | parse_roles: read1 missing |
| 62 | parse_roles: membership check dropped | 1 | 7 | parse_roles: a column that was not requested is refused, naming it and the requested ones |
| 63 | parse_roles: same-column check dropped | 1 | 3 | parse_roles: one column for two roles is refused, naming both roles |
| 64 | parse_roles: read2 not returned | 1 | 6 | parse_roles: sample, read1, read2 |
| 65 | parse_roles: skip empty items off | 1 | 0 | - |
| 66 | explain: swap wording | 1 | 6 | explain: sample role says 'the sample name' |
| 67 | explain: candidates none -> blank | 1 | 1 | explain: empty candidate list reads 'none' |
| 68 | explain: candidates join with , | 1 | 1 | explain: candidates joined with ', ' |
| 69 | explain: drop why | 1 | 2 | explain: sample role says 'the sample name' |
| 70 | machine_line: space join | 1 | 4 | machine_line: role and comma-joined candidates |
| 71 | machine_line: wrong prefix | 1 | 8 | machine_line: role and comma-joined candidates |
| 72 | load_schema: stdin ignored | 1 | 0 | - |
| 73 | load_schema: non-dict accepted | 1 | 5 | load_schema: a JSON array is not a schema |
| 74 | load_schema: OSError escapes | 1 | 4 | load_schema: a missing file -> ValueError naming the path |
| 75 | load_schema: ValueError escapes | 1 | 3 | load_schema: invalid JSON -> ValueError |
| 76 | main: needs-decision exit 0 | 1 | 5 | main: ambiguous reads -> exit 3 |
| 77 | main: needs-decision exit 1 | 1 | 5 | main: ambiguous reads -> exit 3 |
| 78 | main: error exit 1 | 1 | 6 | main: --roles naming a column outside --columns -> exit 2 |
| 79 | main: error to stdout | 1 | 8 | main: ... nothing on stdout |
| 80 | main: machine line to stderr | 1 | 5 | main: ... stdout is exactly the machine line |
| 81 | main: explain to stdout | 1 | 5 | main: ... stdout is exactly the machine line |
| 82 | main: no explain message | 1 | 0 | - |
| 83 | main: --roles ignored | 1 | 8 | main: --roles skips inference (ambiguous schema, exit 0) |
| 84 | main: --roles empty string parsed | 1 | 1 | main: an empty --roles falls back to inference |
| 85 | main: columns default = none | 1 | 15 | main: paired schema -> exit 0 |
| 86 | main: columns not stripped | 1 | 1 | main: --columns tolerates spaces and empty items, schema order decides R1/R2 |
| 87 | main: empty column items kept | 1 | 1 | main: --columns of only commas -> no columns -> needs a decision (exit 3) |
| 88 | main: print read2 even if None | 1 | 3 | main: single-end request -> no read2 field |
| 89 | main: roles separator comma | 1 | 13 | main: ... stdout is 'sample=.. read1=.. read2=..' |
| 90 | main: --schema optional | 1 | 2 | main: no --schema -> argparse exit 2 |
| 91 | _NOT_FASTQ_NAMES: drop reads.txt | 1 | 1 | is_fastq_column: fq.gz or .txt -> False |
| 92 | _NOT_FASTQ_NAMES: drop reads.fasta (first) | 1 | 1 | is_fastq_column: fq.gz or .fasta -> False |
| 93 | _NOT_FASTQ_NAMES: drop reads.fasta.gz | 1 | 1 | is_fastq_column: fq.gz or .fasta.gz -> False |
| 94 | _FASTQ_NAMES: drop reads.fastq.gz | 1 | 1 | is_fastq_column: accepts only .fastq.gz -> True |
| 95 | _FASTQ_NAMES: drop reads.fq | 1 | 1 | is_fastq_column: accepts only .fq -> True |
| 96 | Roles: field rename read1->r1 | 1 | 1 | infer_roles: result is a Roles tuple with the three named fields |

Survivor: `_meta: keep non-string list items` (`[x for x in m if isinstance(x, str)]` -> `[x for x in m]`). Equivalent: `_meta` is only used as `m in _SAMPLE_META` (tuple of strings), and no non-string value compares equal to a string, so the filter is not observable through any public name. Not a test gap.

## 3. Findings

- P3 cleanup (unreachable code): `scripts/utils/schema_roles.py:156-157` (the final `return NeedsDecision("reads", fastq, f"{len(fastq)} requested columns accept FASTQ file names")` in `infer_roles`) cannot run: `fastq` is a subset of `all_fastq`, and `len(all_fastq) > 2` already returned at line 145. Left as is (production code is out of scope); no test can reach it.

