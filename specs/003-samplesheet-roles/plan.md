# Implementation Plan: 樣本表的欄位角色不寫死

**Branch**: `003-samplesheet-roles` | **Date**: 2026-10-02 | **Spec**: `spec.md` | **Test cases**: `test-case.md` (19, approved 2026-10-02)

## 給維護者：複雜度與風險摘要（人工關卡 2）

**做法一句話**：新增一個小模組，讀管線的說明檔判斷「哪欄是樣本名、哪兩欄是 R1／R2」；產生樣本表的工具和送出前的總覽都用它。判斷不出來就用一個專門的結束碼停下來，並列出候選欄位，Claude 據此問你，你指定後再跑一次。

**複雜度**：小到中。一個新模組（約 100 行），改一支工具的填值那幾行，送出前的總覽多兩三行輸出，`launch.md` 第 4 步改一段話。不碰安全網，也不碰叢集。

**分兩段做**，每段結束全部測試綠燈：
1. 判斷模組＋產生樣本表的工具（US1，TC-001～013、016～019）。
2. 送出前的總覽顯示角色＋`launch.md` 文字（US2，TC-014、015）。
之後交給獨立驗收。這次沒有手動步驟：19 條全部自動驗。

**風險（由高到低）**：
1. **把現在的 rnaseq 用法改壞**：這支工具目前完全沒有測試。所以第一件事是在改動前，用真的 rnaseq 說明檔把現在的輸出存成標準答案（TC-001），之後逐字比對。
2. **呼叫方式變了**：以後要多帶說明檔才會自動判斷，沒帶又沒指定就停下來（FR-005，你核可的行為）。`launch.md` 會同步改；其他地方沒有直接呼叫它（已查）。
3. **FASTQ 欄位認錯**：判斷靠說明檔裡的檔名規則。測試用五條管線真實的說明檔（固定版本），包含規則寫在 `anyOf` 裡的 bacass，以及有 `fasta` 欄的 taxprofiler。
4. **mag、bacass 每次都會停一次**：你已接受。

## Technical Context

- Python 3 stdlib (`scripts/generate_samplesheet.py` and the new module), Bash (`scripts/prepare_launch.sh`, tests). No new dependency.
- Fixtures: real `assets/schema_input.json` from rnaseq 3.27.0, ampliseq 2.18.0, mag 5.5.0, bacass 2.6.1, taxprofiler 2.0.1 under `tests/fixtures/schema_input/<pipeline>-<version>.json`, each with its source URL in a sibling README line. Not per-pipeline configuration: nothing in `scripts/` reads them, and `tests/no_per_pipeline_config.sh`'s rules (no `pipelines/` dir, `configs/` = site adapters) still hold.

## Constitution Check (PASS)

| Principle | How |
|---|---|
| 1 | No maintained tool infers column roles from `schema_input.json` (searched 2026-10-02: the nearest, `andrewsgeller/nfcore_pipeline_samplesheet`, hard-codes three pipelines and is unfinished); nf-schema's `meta` tag is the existing signal, used rather than reinvented. Header says so (TC-018). |
| 3 | No path baked in. |
| 6, 7 | The point: any pipeline whose schema names one id column and at most two FASTQ columns needs no configuration and no maintainer. |
| 13 | Every stop says why and what to do next, with a distinct exit code (TC-017). |
| Safety net | Untouched. |

## Design

### `scripts/utils/schema_roles.py` (new)

```
infer_roles(schema: dict, columns: list[str]) -> Roles | NeedsDecision
parse_roles("sample=X,read1=Y,read2=Z", columns) -> Roles   # FR-004; unknown column -> error
```
- Properties from `items.properties` (or top-level `properties`), restricted to the requested columns.
- **Sample column**: the one column whose `meta` (list or string) contains `id` or `sample`. Zero or more than one → `NeedsDecision(role="sample", candidates=...)` (TC-007, TC-008; candidates = all requested non-file columns).
- **FASTQ columns**: a column whose `pattern`, or any `pattern` inside `anyOf`/`oneOf`, mentions a FASTQ ending (`f(ast)?q`, `fastq`, `fq`). `format: file-path` alone does not count (fasta and BAM are file-paths too). In schema order: 1 → read1 only (single-end column, FR-006); 2 → read1, read2; more than 2 → `NeedsDecision(role="reads", candidates=...)` (TC-004/005/006).
- Also callable as a CLI: `schema_roles.py --schema <file|-> --columns a,b,c [--roles ...]` prints `sample=<col> read1=<col> read2=<col>` or a `needs-decision` line. `prepare_launch.sh` uses this, so the rule lives in exactly one place.

### `scripts/generate_samplesheet.py`

- New `--schema <path>` and `--roles sample=…,read1=…,read2=…`. `--columns` stays (and defaults to the schema's own column order when `--schema` is given and `--columns` is not).
- Roles: `--roles` if given (validated, TC-009/010), else inferred from `--schema`; neither → stop (TC-011, FR-005).
- **Exit 3 = needs a decision**: nothing written; stderr carries one human line and one machine line `needs-decision: role=<sample|reads> candidates=<a,b,c>`. Existing codes unchanged (0 ok, 1 nothing found, 2 bad usage).
- `build_rows` fills `values[roles.sample]`, `values[roles.read1]`, `values[roles.read2]`, which removes the hard-coded names (TC-016). Other file columns (FASTQ candidates not chosen, fasta, BAM…) are left empty and named in one warning (TC-013, FR-007). Single-end and unpaired rules are kept as they are (TC-012).

### `scripts/prepare_launch.sh`

The `== samplesheet ==` section gets a `roles:` line, either `樣本名 → sampleID, R1 → forwardReads, R2 → reverseReads` or `需要你指定（R1／R2 候選：…）`. It comes from `schema_roles.py` (TC-014, TC-015). If Python is missing, the existing warning covers it.

### `commands/launch.md` step 4

Pass `--schema <the pipeline's schema_input.json at the pinned revision>` to the tool. On exit 3, show the user the candidates, ask which column is which, then rerun with `--roles`. Never pick for them.

## Stages (each ends with `tests/run_all.sh` green in WSL)

| Stage | Delivers | Test cases |
|---|---|---|
| S1 | golden output from main first; fixtures; `schema_roles.py`; tool changes; TC-016 check in `no_per_pipeline_config.sh` | TC-001–013, 016–019 |
| S2 | `prepare_launch.sh` roles line; `launch.md` wording | TC-014, 015 |
| Close | independent acceptance | all |

## Project Structure

```text
scripts/utils/schema_roles.py                 (new)
scripts/generate_samplesheet.py               (--schema, --roles, exit 3)
scripts/prepare_launch.sh                     (roles line)
commands/launch.md                            (step 4)
tests/generate_samplesheet_test.sh            (new)
tests/fixtures/schema_input/*.json            (new, real, pinned)
tests/prepare_launch_test.sh, tests/no_per_pipeline_config.sh
```
