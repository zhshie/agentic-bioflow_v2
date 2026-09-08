# Downstream: worked examples

`commands/downstream.md` reads a results tree through
`scripts/inventory_outputs.py` and knows nothing about any pipeline. This file
is where the pipeline-specific knowledge goes instead — because examples go
stale the moment a pipeline changes its output layout, and the command must
not depend on anything that can go stale. Read this for a sense of what the
inventory turns up; never treat it as a substitute for running the inventory
against the tree actually in front of you.

Measured against a real bacass run —
`/work/u9613010/agentic-bioflow-test/results/TsMC-bacass` — with
`scripts/inventory_outputs.py`, 2026-09.

## What turned up

```
TsMC-bacass/QUAST/report/
  report.tsv                                          538 B  tsv, 2 cols x 22 rows
      Assembly, TsMC-flye-medaka_polished_genome
  transposed_report.tsv                               538 B  tsv, 23 cols x 1 rows
      Assembly, # contigs (>= 0 bp), ... N50, N90, auN, L50, L90, # N's per 100 kbp
```

`report.tsv` and its transpose carry the same numbers shaped two ways — one
assembly per row, or one assembly per column with every metric as its own
column. A script written against one shape silently reads garbage against the
other; the inventory shows which is on disk before any code is written.

```
TsMC-bacass/busco/.../run_burkholderiales_odb10/
  full_table.tsv                                    92.2 KB  tsv, 10 cols x 690 rows (after 3 comment lines)
      Busco id, Status, Sequence, Gene Start, Gene End, Strand, Score, Length, OrthoDB url, Description
  short_summary.json                                 3.2 KB  json object, 5 keys
      parameters, lineage_dataset, versions, results, metrics
```

The `.json` summary and the `.tsv` full table carry different halves of the
same run: the JSON has the rolled-up completeness percentages, the TSV has one
row per BUSCO marker. Both were reported with their real column/key names, not
a name remembered from a previous release.

```
TsMC-bacass/Prokka/TsMC-flye-medaka/
  TsMC-flye-medaka.tsv                             360.6 KB  tsv, 7 cols x 5763 rows
      locus_tag, ftype, length_bp, gene, EC_number, COG, product
```

One row per predicted gene — the table most downstream annotation questions
("how many genes have no COG hit", "what's the length distribution by ftype")
actually start from.

```
TsMC-bacass/pipeline_info/
  execution_trace_2026-09-07_15-45-32.txt            1.4 KB  tsv, 14 cols x 9 rows
      task_id, hash, native_id, name, status, exit, submit, duration,
      realtime, %cpu, peak_rss, peak_vmem, rchar, wchar
```

`peak_rss` and `peak_vmem` per task, in a file named `.txt`. See below.

```
TsMC-bacass/multiqc/multiqc_data/
  multiqc_software_versions.yaml                      324 B  yaml, 9 top-level keys
      BUSCO_BUSCO, FLYE, MEDAKA, NANOPLOT, PORECHOP_PORECHOP, Prokka, QUAST,
      TOULLIGQC, Workflow
  mqc_busco_plot_burkholderiales_odb10_1.yaml         183 B  yaml, 1 top-level keys
      short_summary.specific.burkholderiales_odb10.TsMC-flye-medaka_polished_genome
```

MultiQC's own `*_data/*.yaml` and `*_mqc_versions.yml` files are consistently
one document per plot or per topic, keyed by sample or tool name at the top
level — useful for finding *which* file has the number wanted before opening
any of them.

## Two findings worth generalising

**Every trace file nf-core writes as `.txt` is really a TSV.** The three
`execution_trace_*.txt` files above are tab-delimited with a header row, same
as any `.tsv` — the extension nf-core chooses for them is simply wrong for
what is inside. This is why `inventory_outputs.py` sniffs the delimiter from
the bytes rather than trusting the extension: a reader that keyed off `.txt`
to decide "not a table" would miss the one file in the tree carrying resource
usage per task.

**A headerless table's first data row gets reported as its column names.**
`busco/busco_downloads/lineages/burkholderiales_odb10/links_to_ODB10.txt`
inventories as `tsv, 3 cols x 687 rows` with the "header" line
`100150at80840, "Tetrapyrrole methylase, subdomain 1", https://...` — that is
the first *data* row, not a header; this file has none. The inventory has no
way to know that from outside the file, so it reports what the first line
says and moves on. This is visible in the output (a column name that looks
like a real value is the tell), but it is not something the tool can fix for
you — check the first row of any table before trusting its column names.
