# PRODUCT.md: agentic-bioflow web

**Who**: students and staff in one plant-pathology / microbiology lab, running nf-core pipelines (16S first) on NCHC Taiwania3 or a capped cloud account. Not bioinformaticians; 5–10 analyses at a time. English layout required (product), Chinese available.

**Job**: open the page and know at a glance which analyses are running, at which step, and whether anything needs *me*. Everything the system can handle (debugging, resubmission, memory) it handles; the person only decides what is genuinely theirs (confirm a launch, run downstream or not, supply missing raw data).

**Path**: settings first → create project → upload raw data → guided launch (pipeline previously used or new, workflow diagram, samplesheet, parameters, compute) → confirm → running → results with an editable report → optional downstream in an embedded RStudio/Jupyter (the person writes R, or asks the AI to edit and run the script; figures appear live and the chosen ones are packaged) → finished package.

**Not**: a Seqera clone with many top-level pages (too much to learn); chatty AI text; a web terminal; roles, Data Explorer, Dashboard (later).

**Principles**: every write goes through a human confirmation (ADR 0006); the web works without AI; data stays on the person's site or cloud (ADR 0004); each person sees only their own runs.
