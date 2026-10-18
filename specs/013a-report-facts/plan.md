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
