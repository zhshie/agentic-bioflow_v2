"""Mechanical helpers for samplesheet generation (file discovery, read pairing).

Migrated from the retired nextflow-development skill. Pipeline-specific knowledge
deliberately did NOT come along: columns come from the pipeline's own
assets/schema_input.json, read by the caller (generate_samplesheet.py's --columns),
never from a per-pipeline file like v1's spec.yaml.
"""
