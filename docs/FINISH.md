# Finishing: worked examples

`commands/finish.md` carries no pipeline-specific knowledge, on purpose. This
file is where that knowledge goes instead — because a pipeline's output layout
changes on its own schedule, and the command must not depend on anything that
can go stale. Everything below is measured, with the date it was measured.

## What the runs actually held (2026-09-10)

Three real runs on one cluster, and they disagreed about almost every name.

### The versions file has three names

| run | file |
|---|---|
| nf-core/ampliseq 2.18.0 | `nf_core_ampliseq_software_mqc_versions.yml` |
| nf-core/rnaseq 3.14.0 | `software_versions.yml` |
| nf-core/differentialabundance 2.0.0 | both `collated_versions.yml` and `nf_core_differentialabundance_software_versions.yml` |

This is why `scripts/collect_provenance.py` looks for a `.yml` in
`pipeline_info/` whose top level looks like process names carrying tool
versions, rather than for a filename. A fourth name costs nothing.

### The quality report moves

- ampliseq: `results/multiqc/multiqc_report.html`, data in `multiqc_data/`
- rnaseq: `results/multiqc/star_salmon/multiqc_report.html` — nested under the
  aligner — with data in `multiqc_report_data/`
- differentialabundance: `results/report/rnaseq/<name>_report.html`

### A retried run leaves its corpse in place

`ampliseq_sclerotia_d5_20260904/results/pipeline_info/` holds two of everything:

```
execution_report_2026-09-04_11-25-59.html   2.9 MB   the attempt that died
execution_report_2026-09-04_11-35-35.html   3.4 MB   the one that finished
execution_trace_2026-09-04_11-25-59.txt      154 B   header only
execution_trace_2026-09-04_11-35-35.txt       27 KB  104 tasks
```

Sorted by name the dead one comes first. The collector takes the newest by
modification time and reports how many it passed over, because silence there
reads as "there was one attempt".

## The empty citation slot (2026-09-10)

This is the defect `/finish` exists to repair. Both runs rendered their methods
paragraph with `${tool_citations}` and `${tool_bibliography}` **empty**:

```html
<p>The pipeline was executed with Nextflow v25.10.4 (...) with the following command:</p>
<pre><code>nextflow run 'https://github.com/nf-core/ampliseq' ... </code></pre>
<p></p>                                <!-- every per-tool citation, missing -->
```

So DADA2, QIIME2, Cutadapt, STAR and Salmon are uncited in a paragraph that
otherwise reads as complete. The template's own footnote says what to do:

> You should also cite all software used within this run.

`scripts/methods_text.py` re-renders the template from
`~/.nextflow/assets/nf-core/<pipeline>/assets/methods_description_template.yml`
with that slot filled from `CITATIONS.md`.

**The recorded command is also not reproducible.** Launching through the
Platform records an ephemeral parameters URL:

```
-params-file 'https://api.cloud.seqera.io/ephemeral/voSKdQ-tvoQptZ2DaEac5A.yaml'
```

which expires. The methods text is rebuilt against the run's own `params.yaml`
and says it was rebuilt.

## How well the citation matching does

Measured against the real citation files, 2026-09-10:

| run | citable tools | matched | left as gaps |
|---|---|---|---|
| ampliseq | 8 | 7 | `ShortRead` |
| rnaseq | 19 | 15 | `cutadapt`, `getchromsizes`, `stringtie`, and one more |

Two different kinds of gap, and they must not be confused:

- **`ShortRead`** is a real Bioconductor package with a real paper, used by
  one of the quality steps, and ampliseq's `CITATIONS.md` simply does not list
  it. Nothing here can fix that; it becomes `[CITATION NEEDED]` and a person
  decides.
- **`stringtie`** is listed — as `StringTie2`. The matcher reports it as a
  **candidate** rather than resolving it, because a rule that strips trailing
  digits would just as happily cite Bowtie's paper for Bowtie 2. A wrong
  citation is worse than a missing one: the gap is visible and the error is not.

## Why the parameters, not just what

The richest methods material on the whole filesystem is the `params.yaml` the
person wrote when they launched the run. From
`ampliseq_sclerotia_d5_20260904/params.yaml`:

```yaml
# Exact primers from the Karst et al. PacBio CCS pair - not the generic
# non-degenerate 27F/1492R.
FW_primer: AGRGTTYGATYMTGGCTCAG
# minBoot=80, "recommended over the 50% default for sequences longer than
# 250 bases" - full-length 16S is ~1450 bp. The pipeline defaults to 50.
dada_min_boot: 80
```

The generated paragraph says what ran. Only this says **why**, and it is the
half a reader needs to judge the work. `methods_text.py` lifts these comments
with their keys. Note the mixed languages: the rnaseq run's are in Traditional
Chinese and need translating for an English manuscript.

## What is not installed here

Measured on the login node, 2026-09-10:

| | |
|---|---|
| `quarto` | absent — no binary, no module |
| `pandoc` | absent |
| `R` | 4.2.1, plus modules 4.3.3 / 4.4.1 / 4.5.2 — **base packages only** |
| R user library | none; `.libPaths()` is root-owned and cannot be added to |
| Python | 3.12.2, standard library only |
| `node` | v25.9.0 |

So nothing renders here. Positron bundles Quarto, which is why the manuscript
is authored with **no executable chunks** — the figures are already files, so
rendering needs Quarto and nothing else. `build_package.sh` does everything
except render, and says where the last step runs.

Render each format separately. Asking for several at once has a known failure
when an image needs converting between them, and vector images do not embed in
word-processor output — so figures written for the package are raster at
publication resolution, and vector copies travel as extras.
