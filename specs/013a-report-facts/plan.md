# 013a: report facts template

Source: issue #119 item 'Report without AI' (ADR 0009 point 4: a report made for every run, editable, put into the package at finished) vs the constitution/PRINCIPLES rule that nothing in the package is composed from memory (see the header comment of scripts/build_package.sh: 'nothing here is composed from memory'). B tier: it changes what a user gets in their package.

## Decision (from the issue)
The report is a facts template filled only from files, never from a model: run info, provenance (`scripts/collect_provenance.py`), the MultiQC report link, the methods paragraph (`scripts/methods_text.py`). Interpretation is NOT written by this - it only comes from the chat later (014), and the template leaves a clearly marked empty 'Interpretation' section for the person to edit.

## Build
1. New `scripts/report_facts.py` (python3 stdlib only, like collect_provenance.py): input a project dir (same layout build_package.sh uses); output `report.md` with sections: Runs (for each run: pipeline, version, run name/id, start/end, status - from the provenance JSON collect_provenance.py produces), Inputs (samplesheet path and checksums if input_checksums output exists), Methods (the methods_text.py paragraph, verbatim), Quality control (relative link to each run's MultiQC html if it exists under the run's outputs; if missing write 'MultiQC report not found' - never invent), Interpretation (empty, with a one-line note that it is for the person to write). Every value comes from a file; a missing value is written as 'not recorded', never guessed.
2. `scripts/build_package.sh`: call report_facts.py and put `report.md` into the package next to provenance.json/methods.md; update the header comment list. If report.md already exists in the package from an earlier build, and the person edited it, do NOT overwrite: write the new one as report.facts.md and say so on stderr (editable report rule).
3. Respect existing conventions: portable bash (tests/bash32_arrays_test.sh, bsd_userland_test.sh, no_hardcoded_paths.sh must stay green), require_python.sh for python3.

## Tests (write first)
- `tests/report_facts_test.sh`: with a fixture project (reuse/extend tests/fixtures used by build_package_test.sh / collect_provenance_test.sh): all five headings present; values match the fixture; a run with no MultiQC -> 'MultiQC report not found'; a missing field -> 'not recorded'; the Interpretation section is empty; no line contains text not traceable to the fixture (assert the Runs/Methods text equals what collect_provenance.py / methods_text.py output).
- extend `tests/build_package_test.sh`: package contains report.md; an edited report.md is kept and report.facts.md written.

## Out of scope
No web page (that is 013b/011). No AI call of any kind. Do not touch platform/, docs/PLATFORM.md, CHANGELOG.md.

## Rulings after contract round 1 (developer-agent, 2026-10-18)

- R1 Inputs: no checksums in 013a (input_checksums.sh has no fixed output location; deferred to 013b). Inputs lists, per run, the samplesheet file NAME (basename only, never an absolute path) taken from the `input` parameter recorded in the provenance JSON; absent -> `not recorded`.
- R2 Edited detection: report.md is deterministic (no timestamps, no host names, stable order), so two builds of the same project give byte-identical files. build_package.sh writes the sha256 of the report.md it generated to `submission/.report.md.sha256`. On rebuild: report.md missing -> write it; hash file exists and current report.md matches it -> overwrite in place and refresh the hash; otherwise (hash differs, or report.md exists with no hash file) -> treat as edited: keep report.md untouched, write the new one to report.facts.md (overwrite any earlier report.facts.md), and print one stderr line naming both files.
- R3 Runs: fields come only from the provenance JSON; start/end/status are `not recorded` when the JSON has no such field (accepted as the current reality). "run name" = the basename of the run's `run_dir`; run id = `platform_run_id` if present, else `not recorded`.
- R4 MultiQC: the link is relative to report.md's own folder (`submission/`) and may point outside the package (e.g. `../runs/<run>/results/multiqc/multiqc_report.html`); append ` (outside this package)` after such a link. Copying MultiQC into the package is 013b. Use the path find_quality_report() in collect_provenance.py already finds if the JSON carries it; otherwise look for multiqc_report.html under the run's results; none -> `MultiQC report not found`.
- R5 Interface: `scripts/report_facts.py --provenance <submission/provenance.json> --methods <submission/methods.md> --out <file>`. It reads what build_package.sh already produced; it does NOT re-run collect_provenance.py or methods_text.py. Methods section = methods.md content verbatim.
- R6 Fixtures: build them inline in the test like build_package_test.sh does; no tests/fixtures/ change needed.
- R7 Out-of-scope (no platform/, docs/PLATFORM.md, CHANGELOG.md change) is checked by the verifier reading the diff.
