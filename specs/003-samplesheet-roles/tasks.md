# Tasks: 樣本表的欄位角色不寫死

**Input**: `spec.md`, `test-case.md` (approved 2026-10-02), `plan.md` (approved 2026-10-02)
Every task is test-first: write the test for its TCs, run it, record RED, implement, record GREEN. Each stage ends with `bash tests/run_all.sh` green in WSL.

## Stage S1 — the role module and the tool (US1)

- [x] T001 Before touching the tool: fixtures `tests/fixtures/schema_input/{rnaseq-3.27.0,ampliseq-2.18.0,mag-5.5.0,bacass-2.6.1,taxprofiler-2.0.1}.json` downloaded verbatim from `https://raw.githubusercontent.com/nf-core/<p>/<tag>/assets/schema_input.json`, plus `tests/fixtures/schema_input/README.md` naming each source URL. Capture main's current output for the rnaseq case (a temp dir with 3 `_R1`/`_R2` pairs, `--columns` = the rnaseq schema's columns) as `tests/fixtures/samplesheet_golden/rnaseq.csv` + `.stderr` (paths made relative or normalised so the golden is machine-independent)
- [x] T002 [TC-001..TC-013, TC-017, TC-019] `tests/generate_samplesheet_test.sh` (new): every TC in US1 and the exit-3 / nothing-written / message checks; RED against the current tool
- [x] T003 [TC-016] `tests/no_per_pipeline_config.sh`: new check 5 — `scripts/generate_samplesheet.py` contains no string constant `sample` / `fastq_1` / `fastq_2` outside its docstring and comments (Python `ast` scan); RED now
- [x] T004 implement `scripts/utils/schema_roles.py` (infer + parse + CLI) and the tool changes (`--schema`, `--roles`, exit 3 with `needs-decision:` line, other file columns named in one warning); header keeps `# Not …` (TC-018)

## Stage S2 — the overview and the command text (US2)

- [x] T005 [TC-014, TC-015] `tests/prepare_launch_test.sh`: roles line for an inferable fixture and `需要你指定` + candidates for mag; RED first
- [x] T006 implement the `roles:` line in `scripts/prepare_launch.sh` via `schema_roles.py`; `commands/launch.md` step 4 wording (`--schema`, exit 3 → ask → `--roles`); `tests/command_layer_is_site_neutral.sh` and `tests/no_per_pipeline_config.sh` stay green

## Close

- [ ] T007 full suite in WSL
- [ ] T008 independent acceptance (read-only verifier) against spec + approved test cases + diff
