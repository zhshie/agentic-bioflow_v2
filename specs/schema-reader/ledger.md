# 讀 nextflow_schema.json 的解析器（不連網） progress ledger

- [x] RED: test_schema.py + two fixtures (real file sha256 verified)
- [x] GREEN: platform/abf_platform/schema.py (load, parameter_groups, required_without_default, samplesheet_columns)
- Note: TC-050 and the plan's "$defs first key is asv_post_processing" came from unordered (Python 2) dict order; real file order is asserted instead. TC-003 (position 6) holds.
