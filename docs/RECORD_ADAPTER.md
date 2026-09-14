# The record adapter

Some deployments keep a record of a run somewhere else — a lab notebook, an
inventory system, whatever a lab already uses. This plugin does not know which,
if any, and — as of this release — none is implemented against a real one. A
*record adapter* is where that fact lives, behind a small interface, so that
the command layer can be written once and stay correct whether a deployment
has picked one, is still deciding, or never will.

This is the same shape as `docs/SITE_ADAPTER.md`, one contract over. That one
answers "where does this run, and what does the site need"; this one answers
"where does this run's *record* go". Both exist so the command layer never has
to know the answer itself.

**The command layer may not name a record system.** It asks *whether this run
has somewhere to be recorded*; the adapter knows how to find out.
`tests/command_layer_is_record_neutral.sh` enforces this the same way
`tests/command_layer_is_site_neutral.sh` enforces the sibling rule — see that
file's own header for why a vocabulary check, crude as it is, catches the
thing that actually happens: someone names the lab's actual ELN inline because
it is the one they are staring at.

---

## What a record adapter must supply

### 1. `resolve <ref>`

Given a reference the deployment already has — a sample ID, an experiment ID,
whatever the record system calls its own primary key — say what, if anything,
is known about it there. `scripts/record_adapter.sh resolve <ref>` is the
entry point; it answers with one `key=value` line.

### 2. `attach <ref> <path>`

Given a reference and a path to an artefact this plugin produced (a report, a
figure, a package `finish` built), make the record system aware of it, however
that adapter's system does that — upload, link, or nothing at all if the
adapter has no such capability. Answers where the artefact actually ended up
staying, because "attach" is not a promise the artefact moved anywhere.

### 3. `lookup-by-checksum <sha256>` — optional

Given a SHA-256, ask whether the record system already has something
registered under it. Optional because not every record system can answer this,
and one that cannot is still a valid adapter for the other two contracts.

### 4. `reach`

Reuses `docs/SITE_ADAPTER.md` contract 6's meaning exactly: where the record
system lives, *relative to wherever this plugin is running* — `none` (nothing
to reach; the adapter is self-contained, which is what `none` is), `local`
(reachable directly, e.g. a service on the same host or plain HTTPS), or `ssh`
(reachable only through the site, the way `scripts/on_site.sh` reaches the
site itself). This is a property of the *adapter*, not of the site — a record
system and the compute site are two different things that happen to both need
this vocabulary, and `docs/SITE_ADAPTER.md` contract 6 already explains why it
is a contract and not a transport layer glued on afterward. A record adapter
with `reach: none` costs nothing to have, exactly as a site with no egress
restrictions costs nothing to have.

---

## What `none` supplies

The only implementation that exists. `scripts/record_adapter.sh` with no
`record_adapter` configured — or `record_adapter: none` explicitly — behaves
like this:

| Contract | Behaviour | Exit |
|---|---|---|
| `resolve <ref>` | prints `record=none` | 0 |
| `attach <ref> <path>` | does nothing; prints `kept=<path>`, the path unchanged | 0 |
| `lookup-by-checksum <sha256>` | prints `found=no` | 0 |
| `reach` | `none` — there is nothing to reach | — |

No network call anywhere in it (`tests/record_adapter_test.sh` asserts this
statically, the way `tests/command_layer_is_site_neutral.sh` asserts the
command layer names no scheduler). No state kept anywhere: this plugin records
no run state in a file (`PRINCIPLES.md`, invariant 2), and a record adapter
that cached what it resolved would be exactly that file wearing a different
name. Bad usage — a missing `<ref>`, a missing `<path>` — exits 2. An adapter
value the script does not recognise exits 2 naming it: `adapter <x> is not
implemented`, never a silent fall-through to `none`'s behaviour, because a
misconfigured deployment silently behaving as if nothing were configured is
the harder failure to notice.

```console
$ scripts/record_adapter.sh resolve d5-sclerotia-rep3
record=none
$ scripts/record_adapter.sh attach d5-sclerotia-rep3 /work/.../results/report.html
kept=/work/.../results/report.html
$ scripts/record_adapter.sh lookup-by-checksum 3f9a2c...
found=no
```

---

## Why no ELN implementation is written yet

The same reason `docs/SITE_ADAPTER.md`'s closing section gives for not writing
a second site adapter speculatively: **one real implementation is what
validates a contract; a second one written before there is a real second
target is a guess wearing the shape of code** (`PRINCIPLES.md`, invariant 8 —
measure or read the source before claiming, and a contract with no real
implementation behind it is nothing to measure against). CLAUDE.md states the
site-adapter form of this rule outright: "Do not write a second site adapter
speculatively — one implementation is what exists to validate the contract; a
second one is real work when there's a real second site." This document is the
same argument, one layer over: this plugin has exactly one validated
implementation of this contract (`none`), and it stays that way until a lab
using it actually picks a record system.

That choice is explicitly out of scope for this release. The lab architecture
draft this plugin's integration was designed against weighs several
candidates — a school-hosted eLabFTW instance, a self-hosted eLabFTW, RSpace —
and defers picking one to a pilot (`~/.claude/plans/lab-ai-agent-ai-agent-protocol-meeting-proud-pony.md`,
"第二階段"). Writing an adapter for any one of them now would be exactly the
mistake CLAUDE.md's rule exists to prevent: a second implementation built
before the first real target is chosen, validating nothing but this project's
own guess.

## Settings

`record_adapter` (default `none`) and `record_ref` are the two keys this
contract needs from the deployment's settings file. **They are documented
here first and land in `docs/SETTINGS.md` in a later release** — that file is
owned by another track of this same round of changes, so this section is the
source of truth for their meaning until that edit lands.

| Key | What it is | Without it |
|---|---|---|
| `record_adapter` | Which adapter is in use: `none`, or a future adapter's name | Defaults to `none` — every deployment is valid with nothing set |
| `record_ref` | The convention this deployment uses for a reference passed to `resolve`/`attach` — opaque to the command layer, meaningful only to the configured adapter (a sample ID, an experiment ID, later an ELN URL once one exists) | Nothing breaks; there is simply nothing to resolve against, which is `none`'s normal case |

`scripts/record_adapter.sh` reads `record_adapter` by running
`scripts/settings.sh record_adapter` as its own CLI call rather than sourcing
it, so this script's one dependency stays optional and it keeps working
standalone — by a person or another model — even somewhere `settings.sh`
cannot be reached (`PRINCIPLES.md`, invariant 5). `$RECORD_ADAPTER` is the
fallback for exactly that case: it is used whenever `settings.sh` has no
actual value to give (no settings file, no `record_adapter` key in it, or the
script missing entirely), and defaults to `none`. A settings file that
explicitly names an adapter always wins over the environment variable.

**An ELN API key, once an ELN adapter exists, belongs in the deployment's own
settings file, mode 600 — never printed, never in git, never in a params file,
never copied from another member's settings.** This is not a new rule:
`docs/SETTINGS.md` already states it for every credential this plugin
touches, and `CLAUDE.md`'s safety net repeats it in the same words. It is
stated here again because it is the one concrete thing this document can say
about a credential for a system that does not exist here yet.

---

## Adding a record adapter

Do not write one speculatively. The contract above was derived from the one
real question this plugin currently has to answer (*is there a record system
at all* — answer: not yet, for the pilot lab this was designed against), and a
contract with one implementation is a guess about the second
(`PRINCIPLES.md`, invariant 8). Write it when a lab has actually chosen a
record system, and expect the contract to change when you do — that is the
point of having written it down before there was a second implementation to
copy from.
