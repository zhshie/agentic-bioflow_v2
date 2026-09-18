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

## Where the agent runs, which is not the same question as where the data is

The section above is about moving results. This one is about the agent, and it
decides something the data question does not: whether step 5 of `/downstream`
exists at all.

`scripts/positron_run.py` reaches a console over a named pipe, a Unix domain
socket, or a loopback port, and finds what to connect to by reading local
state — the bridge extension's state file first (ladder rung 1,
`extensions/positron-bridge`), then a kallichore connection file (rung 2, an
older Positron with no bridge installed). There is no network hop anywhere
in either rung, and no host field in the bridge file either — writing one
would invite exactly the "reach a console on a different machine" feature
this section explains does not exist. So the tool works on **one machine —
whichever one the thing it reads local state from is running on** — and
nowhere else. What changed with the bridge is *which* mechanism answers
that question correctly against kallichore 0.1.68+ (PITFALLS 34); it does
not change which machine gets to answer it at all.

That splits this deployment in three, and until 2026-09-10 nothing said so
for the first two, or considered the third:

| | where Claude runs | where the bridge/kallichore file lives | step 5 | everything else |
|---|---|---|---|---|
| **A** | on the desktop, in Positron's own terminal or as its agent extension | the desktop — same machine as Claude | native, either ladder rung | reaches the site with `reach: ssh` and a multiplexed master |
| **B** | on the site itself | **the desktop, if Positron runs there with no remote-editing support** — a different machine from Claude | **structurally impossible**, at either rung: reads directly what's local to it, and the desktop's own state file is not that | `reach: local`; nothing to multiplex, nothing to fetch |
| **C** | on the site itself, same as B | **the site** — Positron on the desktop, but reaching the site through its own Remote-SSH support | **native**, if the bridge is installed | `reach: local`, same as B |

A and B are the two deployments this repo actually runs; C is new with the
bridge and needs its own explanation, because it is the one row where "where
Claude runs" alone no longer decides the answer.

Both A and B are coherent on their own. B is what this deployment has
actually been running in, and it is cheaper for every other command —
`analysis/` and `results/` are already on the site's own filesystem, so
`fetch.sh` has nothing to do. It was only step 5 that could not work there,
because the Plots pane was on the other machine — and installing the bridge
on the desktop in deployment B does not change that: the bridge still runs
wherever Positron's extension host runs, and in B that is still the desktop,
a machine `positron_run.py` on the site has no route to (same limit PITFALLS
20i already named, now also true of the bridge file and not just the
kallichore one).

Neither A nor B is wrong to pick. What was wrong was picking one by accident
and finding out through a message that named the wrong cause (PITFALLS 20i).

**C is what collapses B's limitation, and it is read from the bridge
extension's own manifest, not measured against a live session here.**
`extensions/positron-bridge/package.json` declares `"extensionKind":
["workspace"]` — VS Code's (and so Positron's) own documented mechanism for
telling a Remote-SSH window to run an extension's host on the *remote* side
rather than the client. When Positron is pointed at the site through its own
Remote-SSH support, the bridge's extension host runs on the site, and so does
`activate()` — which means its state file lands in the *site's* own
`$XDG_STATE_HOME/agentic-bioflow/positron-bridge.json`, not the desktop's.
An agent running as deployment B then finds it exactly the way it already
finds anything else local to the site: no glob across machines, no new code,
because ladder rung 1 was never machine-aware to begin with — it only ever
reads whatever is local to wherever it runs, and C is the arrangement where
that happens to be the site.

This is **read in code**, in `docs/CONDITIONS.md`'s own sense of the word:
the mechanism is VS Code's documented remote-extension placement, not
something this repo has run against a live Positron Remote-SSH session to
confirm. `positron_run.py --check` on the site is the whole probe once
someone is in a position to try it — open the project that way, open a
console, install the bridge if it is not there already, and run `--check`.
It answers in one line, and whichever way it answers becomes measured
evidence for this row instead of read-in-code evidence.

One thing still worth weighing before treating C as the default: it puts a
live Positron console on a machine whose job is moving files and asking
about schedules, which is what the A/B tradeoff above argues against for
size reasons: normalised results are usually small (this file's own worked
numbers), but a large enough analysis flips that argument, on the site
exactly as much as anywhere else.
