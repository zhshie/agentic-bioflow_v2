# 讀 nextflow_schema.json 的解析器（不連網） progress ledger

- [x] RED: test_schema.py + two fixtures (real file sha256 verified)
- [x] GREEN: platform/abf_platform/schema.py (load, parameter_groups, required_without_default, samplesheet_columns)
- BLOCKED: TC-050 contract (fastq_1, control, fastq_2) contradicts the real ampliseq-2.18.0.json (sampleID, forwardReads, reverseReads). Test restored to the contract value (red); verifier must reopen the contract. Plan note "$defs first key asv_post_processing" is the same misreading; TC-003 (position 6) holds.
