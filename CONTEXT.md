# agentic-bioflow

An AI-assisted, no-code way for a lab to run its own bioinformatics analyses — from raw
sequencing data to figures and a methods section — on infrastructure the lab already has.

## Language

### What is being built

**Prototype** (雛形):
The open-source Claude Code plugin in this repository: the fastest way to prove the idea, using
Seqera Platform as its execution backend and interface.
_Avoid_: the product, the plugin (when the long-term thing is meant)

**Product** (產品):
The long-term offering the Prototype leads to: the same workflow driven by a model the lab can
run itself, with no required dependency on any single vendor's platform.
_Avoid_: the plugin, the platform

**Execution backend** (執行後端):
What actually runs a pipeline and holds its run state — today Seqera Platform; later Nextflow
driven directly on an HPC cluster, then rented cloud.
_Avoid_: platform, server, compute environment (that is Seqera's narrower term)

**Brain** (大腦):
The machine the Operator talks to: it runs the model, the conversation, plotting and packaging.
In the Product, a pre-installed box sold to the lab.
_Avoid_: server, workstation, client

**Muscle** (肌肉):
Where pipelines actually compute: an HPC account (for labs with an NSTC project) or a rented
cloud machine. It is an Execution backend seen from the Operator's side.
_Avoid_: cluster (when cloud is also meant)

### Who is involved

**Buyer** (付費者):
The principal investigator who pays, usually from a research grant.
_Avoid_: customer, user

**Operator** (操作者):
The graduate student or research assistant who actually runs analyses with the tool.
_Avoid_: user (ambiguous between Buyer and Operator), member

### What goes in

**Experiment spec** (實驗設計規格):
The Operator-approved record of the study question, sample groups, comparisons, covariates and
wanted figures, drawn out through conversation. Pipeline setup, the figure plan and the methods
text are derived from it; nothing is set up before it is approved.
_Avoid_: experiment design (the lab's own plan, before it is written down), metadata, samplesheet

### What comes out

**Deliverable** (交付成果):
Pipeline outputs organised, plus figures, tables and a methods text with citations traceable to
source files, together with the Python or R scripts that produced them — stopping short of
interpreting the results.
_Avoid_: report, results

**Reproducible** (可再現):
The same data and the same Deliverable's recorded versions give the same results on another
machine or cluster.
_Avoid_: portable (which here means moving between execution backends)

**Data stays local** (資料不離開實驗室):
The Operator's raw data and results never leave the lab's own machine, HPC account or cloud
account.
_Avoid_: private, secure
