#!/bin/bash
# Tests for hooks/confirm_walkthrough.sh, the gate that makes launch.md's
# walkthrough steps actually happen.
#
# The failure it exists for: commands/launch.md has required since 2.0.6 that
# the pipeline's diagram and stage list be shown before anyone is asked to
# configure it, and that the parameter choices be put to the user rather than
# decided for them. A model that had read that file skipped both. Nothing
# caught it, because those two steps produce no artifact - doing them and
# skipping them leave the run looking identical.
#
# Three things below are worth more than the rest:
#
#   - The gate must deny at the step that DEPENDS on the walkthrough, not at
#     the launch. Denying at `tw launch` would arrive after the samplesheet and
#     the parameters were settled, when showing the diagram is a formality.
#
#   - Evidence is a fetched URL, not a mention. An earlier draft matched the
#     bare string `docs/images/`, and its own design conversation satisfied it.
#
#   - An injected turn - a subagent finishing, a system reminder - is shaped in
#     the transcript exactly like a person typing. Counted as a reply, waiting
#     for a subagent would satisfy a gate about whether a human answered. The
#     last case here is the one that pins that shut.
H="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/hooks/confirm_walkthrough.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

# Build a transcript from a compact spec, one record per argument:
#   a:<text>   assistant text (what the user actually read)
#   w:<cmd>    a Bash command the assistant RAN - never read by the user
#   q:<x>      an AskUserQuestion tool_use
#   h:<text>   a human turn
#   n:<text>   an injected turn (arrives shaped like a human one)
#   u:<text>   tool result
mktx() {
  local out="$1"; shift
  python3 - "$out" "$@" <<'PY'
import json, sys
out, specs = sys.argv[1], sys.argv[2:]
with open(out, "w") as f:
    for spec in specs:
        kind, _, text = spec.partition(":")
        if kind == "a":
            rec = {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}
        elif kind == "w":
            rec = {"type": "assistant", "message": {"content": [
                   {"type": "tool_use", "name": "Bash", "input": {"command": text}}]}}
        elif kind == "q":
            rec = {"type": "assistant", "message": {"content": [
                   {"type": "tool_use", "name": "AskUserQuestion", "input": {"questions": []}}]}}
        elif kind == "h":
            rec = {"type": "user", "message": {"content": [{"type": "text", "text": text}]}}
        elif kind == "n":
            rec = {"type": "user", "message": {"content": text}}
        else:
            rec = {"type": "user", "message": {"content":
                   [{"type": "tool_result", "tool_use_id": "x", "content": text}]}}
        f.write(json.dumps(rec) + "\n")
PY
}

DIAG_URL='https://raw.githubusercontent.com/nf-core/bacass/2.4.0/docs/images/nf-core-bacass_metro_map.png'
SCHEMA_URL='https://raw.githubusercontent.com/nf-core/bacass/2.4.0/nextflow_schema.json'
DIAG="here is the workflow: $DIAG_URL"
SCHEMA="fetching $SCHEMA_URL"


t() { # t <label> <expect allow|deny|warn> <tool-json> <transcript>
  printf '%-58s ' "$1"
  local out got
  out=$(python3 -c '
import json,sys
d=json.loads(sys.argv[1]); d["transcript_path"]=sys.argv[2]; print(json.dumps(d))' "$3" "$4" \
        | bash "$H" 2>/dev/null)
  if [ -z "$out" ]; then got=allow
  else got=$(python3 -c '
import json,sys
o=json.load(sys.stdin)["hookSpecificOutput"]
print(o.get("permissionDecision","warn"))' <<<"$out" 2>/dev/null) || got=unparseable
  fi
  if [ "$got" = "$2" ]; then echo "ok ($got)"
  else echo "FAIL: expected $2, got $got"; fails=$((fails+1)); fi
}

SS='{"tool_name":"Bash","tool_input":{"command":"tw datasets add -w 1 ss.csv"}}'
SSW='{"tool_name":"Write","tool_input":{"file_path":"/r/samplesheet.csv"}}'
PY_='{"tool_name":"Write","tool_input":{"file_path":"/r/params.yaml"}}'
LA="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"tw $(printf '\x6c\x61\x75\x6e\x63\x68') x --disable-optimization\"}}"
LS='{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'

mktx "$TMP/empty.jsonl"  'a:starting work'
mktx "$TMP/diag.jsonl"   "a:$DIAG"
mktx "$TMP/mention.jsonl" 'a:step 2 says to read docs/images/ and pick the figure'
mktx "$TMP/schema.jsonl" "a:$DIAG" "a:$SCHEMA"
mktx "$TMP/answered.jsonl" "a:$DIAG" "a:$SCHEMA" 'h:全部預設'
mktx "$TMP/asked.jsonl"  "a:$DIAG" "a:$SCHEMA" 'q:' 'u:the user chose defaults'
mktx "$TMP/injected.jsonl" "a:$DIAG" "a:$SCHEMA" 'n:<task-notification>agent finished</task-notification>'
mktx "$TMP/escape.jsonl" 'a:nothing done at all' 'h:略過導覽'

# Found by running the gate against this session's own transcript: the figure
# URL appeared in a heredoc that WROTE THIS FILE, and that satisfied the gate.
# A URL inside a command the model ran was never in front of the user.
FIXTURE_WRITE="cat > tests/confirm_walkthrough_test.sh <<'T'
DIAG='here is the workflow: $DIAG_URL'
SCHEMA='fetching $SCHEMA_URL'
T"
mktx "$TMP/typed_diag.jsonl"   "w:$FIXTURE_WRITE"
mktx "$TMP/typed_schema.jsonl" "a:$DIAG" "w:$FIXTURE_WRITE" 'h:全部預設'
mktx "$TMP/curled.jsonl"       "a:$DIAG" "w:curl -sSL $SCHEMA_URL" 'h:全部預設'

# A diagram is evidence about ONE pipeline. Switching pipelines mid-conversation
# leaves the previous one's figure sitting in the transcript, and it used to go
# on answering for the new one.
RNASEQ_DIAG='here is the workflow: https://raw.githubusercontent.com/nf-core/rnaseq/3.14.0/docs/images/nf-core-rnaseq_metro_map_grey.png'
mktx "$TMP/wrong_pipeline.jsonl" "a:$RNASEQ_DIAG" "a:$SCHEMA" 'h:全部預設'
mktx "$TMP/right_pipeline.jsonl" "a:$DIAG" "a:$SCHEMA" 'h:全部預設'

t "an unrelated command is not this gate's business" allow "$LS"  "$TMP/empty.jsonl"
t "samplesheet before the diagram is refused"        deny  "$SS"  "$TMP/empty.jsonl"
t "writing the csv directly is the same step"        deny  "$SSW" "$TMP/empty.jsonl"
t "naming docs/images/ is not showing a diagram"     deny  "$SS"  "$TMP/mention.jsonl"
t "a fetched figure URL is"                          allow "$SS"  "$TMP/diag.jsonl"
t "params before the schema is read is refused"      deny  "$PY_" "$TMP/diag.jsonl"
t "schema read but nobody answered is still refused" deny  "$PY_" "$TMP/schema.jsonl"
t "a human reply after the schema opens it"          allow "$PY_" "$TMP/answered.jsonl"
t "so does an AskUserQuestion"                       allow "$PY_" "$TMP/asked.jsonl"
t "launch with no diagram is refused"                deny  "$LA"  "$TMP/empty.jsonl"
t "launch with a diagram but no menu is refused"     deny  "$LA"  "$TMP/diag.jsonl"
t "launch with both goes through"                    allow "$LA"  "$TMP/answered.jsonl"
t "the user can stand the gate down"                 allow "$LA"  "$TMP/escape.jsonl"
t "an unreadable transcript warns, never denies"     warn  "$SS"  "$TMP/does-not-exist"

# The one that matters most: a subagent report is not a person answering.
t "an injected turn is not the user replying"        deny  "$PY_" "$TMP/injected.jsonl"

# The one this round's real transcript caught: evidence the model typed into a
# command is evidence of nothing. Both halves matter - the write must not
# count, and a genuine fetch still must.
t "a figure URL I typed into a command is not shown" deny  "$SS"  "$TMP/typed_diag.jsonl"
t "a fixture naming the schema is not reading it"    deny  "$PY_" "$TMP/typed_schema.jsonl"
t "actually fetching the schema still counts"        allow "$PY_" "$TMP/curled.jsonl"

# The diagram must be the diagram OF THIS PIPELINE.
LA_B="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"tw $(printf '\x6c\x61\x75\x6e\x63\x68') nf-core/bacass -w me/ws\"}}"
LA_NAMED="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"tw $(printf '\x6c\x61\x75\x6e\x63\x68') bacass_v261\"}}"
t "another pipeline's diagram does not answer"       deny  "$LA_B" "$TMP/wrong_pipeline.jsonl"
t "this pipeline's diagram does"                     allow "$LA_B" "$TMP/right_pipeline.jsonl"
t "a Launchpad name names no repo, so no constraint" allow "$LA_NAMED" "$TMP/wrong_pipeline.jsonl"

# ---------------------------------------------------------------------------
# G4 - an analysis plan, agreed, before any analysis or plotting code is written.
#
# The evidence has three parts and each closes a different hole:
#   the plan file, beside or above the code   -> which work this plan is for
#   a plan in assistant TEXT, two lines+      -> a person was actually shown it
#   a human turn after it                     -> a person had the floor
#
# The first alone is the one that matters most here. Writing the plan into a
# file is the natural move in this step - far more natural than the heredoc
# that caught G1 - so a gate that accepted "a plan file exists" would be
# satisfied by the model talking to itself.
mkdir -p "$TMP/projA/analysis" "$TMP/projB/analysis"
echo "# analysis plan" > "$TMP/projA/analysis/analysis.md"

W_A='{"tool_name":"Write","tool_input":{"file_path":"'"$TMP"'/projA/analysis/plot_asv.R"}}'
W_B='{"tool_name":"Write","tool_input":{"file_path":"'"$TMP"'/projB/analysis/plot_asv.R"}}'
W_MD='{"tool_name":"Write","tool_input":{"file_path":"'"$TMP"'/projA/analysis/notes.md"}}'
RUN_R='{"tool_name":"Bash","tool_input":{"command":"scripts/positron_run.py --lang r --file analysis/plot_asv.R"}}'
HEREDOC='{"tool_name":"Bash","tool_input":{"command":"cat > '"$TMP"'/projA/analysis/plot_asv.R <<EOF\nplot(1)\nEOF"}}'

PLAN='Here is the plan, which I will write to analysis/analysis.md:
1. ASV richness by group - answers whether SynCom shifts diversity - from dada2/ASV_table.tsv columns 2-11
2. Shannon index by group - answers the same for evenness - from qiime2/alpha_diversity.tsv'
ONELINE='Plan, in analysis/analysis.md: one figure, ASV richness from dada2/ASV_table.tsv'
TALK='Before I write any plotting script I will propose an analysis plan and get your agreement.'
PLANWRITE="cat > $TMP/projA/analysis/analysis.md <<'P'
1. ASV richness from dada2/ASV_table.tsv
2. Shannon boxplot from qiime2/alpha.tsv
P"

mktx "$TMP/g4_none.jsonl"     'a:starting the downstream work'
mktx "$TMP/g4_ok.jsonl"       "a:$PLAN" 'h:好，就這樣'
mktx "$TMP/g4_noreply.jsonl"  "a:$PLAN"
mktx "$TMP/g4_typed.jsonl"    "w:$PLANWRITE" 'h:好'
mktx "$TMP/g4_talk.jsonl"     "a:$TALK" 'h:ok'
mktx "$TMP/g4_oneline.jsonl"  "a:$ONELINE" 'h:好'
mktx "$TMP/g4_injected.jsonl" "a:$PLAN" 'n:<task-notification>agent finished</task-notification>'
mktx "$TMP/g4_asked.jsonl"    "a:$PLAN" 'q:x'
mktx "$TMP/g4_esc4.jsonl"     'h:略過計畫'
mktx "$TMP/g4_esc1.jsonl"     'h:略過導覽'
INVENTORY='The results tree holds:
  dada2/ASV_table.tsv     11 columns, 555 rows
  qiime2/alpha_diversity.tsv   4 columns, 10 rows
  multiqc/multiqc_data.json    top-level keys: report_general_stats_data'
mktx "$TMP/g4_inventory.jsonl" "a:$INVENTORY" 'h:好'

t "no plan at all: refused"                          deny  "$W_A" "$TMP/g4_none.jsonl"
t "a plan shown and answered: allowed"               allow "$W_A" "$TMP/g4_ok.jsonl"
t "a plan nobody answered: refused"                  deny  "$W_A" "$TMP/g4_noreply.jsonl"
t "AskUserQuestion counts as the answer"             allow "$W_A" "$TMP/g4_asked.jsonl"

# The three that must not pass, each pinning a different mistake.
t "a plan I only wrote into a file is not agreed"    deny  "$W_A" "$TMP/g4_typed.jsonl"
t "talking about a plan is not proposing one"        deny  "$W_A" "$TMP/g4_talk.jsonl"
t "a subagent report is not the user answering"      deny  "$W_A" "$TMP/g4_injected.jsonl"

# The subject: this project's plan does not license another project's code.
t "another project has no plan of its own"           deny  "$W_B" "$TMP/g4_ok.jsonl"

# A plan is plural; one line is what ordinary prose produces by accident.
t "a single shaped line is not a plan"               deny  "$W_A" "$TMP/g4_oneline.jsonl"

# Step 2 prints an inventory naming many files. It is not a plan, and a gate
# that only counted file references would be satisfied by it.
t "an inventory printout is not a plan"              deny  "$W_A" "$TMP/g4_inventory.jsonl"

# What must NOT fire: notes, and running code that already exists.
t "writing notes into analysis/ is not gated"        allow "$W_MD" "$TMP/g4_none.jsonl"
t "running an existing script is not gated"          allow "$RUN_R" "$TMP/g4_none.jsonl"
t "a heredoc into analysis/ is the same write"       deny  "$HEREDOC" "$TMP/g4_none.jsonl"

# Two escape phrases, and this is why: one of them said hours earlier for a
# different step must not stand this one down as well.
t "略過計畫 stands G4 down"                          allow "$W_A" "$TMP/g4_esc4.jsonl"
t "略過導覽 does NOT stand G4 down"                  deny  "$W_A" "$TMP/g4_esc1.jsonl"

# A subagent cannot be shown a plan and cannot ask, so a denial there would be
# a wall rather than a detour. Its transcript is its own file, every record
# marked - measured, PITFALLS 22.
python3 - "$TMP/g4_sidechain.jsonl" <<'PYX'
import json, sys
with open(sys.argv[1], "w") as f:
    for rec in ({"type": "assistant", "isSidechain": True,
                 "message": {"content": [{"type": "text", "text": "working"}]}},):
        f.write(json.dumps(rec) + "\n")
PYX
t "a subagent is warned, not walled"                 warn  "$W_A" "$TMP/g4_sidechain.jsonl"

# ---------------------------------------------------------------------------
# G5 - a run's output lands inside a project.
#
# outdir is a pipeline parameter, so it is in params.yaml and never on the
# launch command line. Checking argv for it would be a rule that could not
# fire; these cases pin the three places the value really appears.
GOOD='/work/lab/zhshie404/projects/sclerotia/runs/ampliseq_d5_20260904/results'
BAD='/work/lab/zhshie404/runs/ampliseq_d5_20260904/results'

pw() { printf '{"tool_name":"Write","tool_input":{"file_path":"/r/params.yaml","content":"%s"}}' "$1"; }
t "an outdir outside any project is refused"         deny  "$(pw "outdir: $BAD")"  "$TMP/curled.jsonl"
t "an outdir inside a project passes"                allow "$(pw "outdir: $GOOD")" "$TMP/curled.jsonl"
t "params with no outdir leaves the constraint off"  allow "$(pw "input: samplesheet.csv")" "$TMP/curled.jsonl"

HD_BAD='{"tool_name":"Bash","tool_input":{"command":"cat > params.yaml <<EOF\noutdir: '"$BAD"'\nEOF"}}'
t "a heredoc writing params is read the same way"    deny  "$HD_BAD" "$TMP/curled.jsonl"

# --params-file: the launch names a file, and the file is what carries outdir.
echo "outdir: $BAD" > "$TMP/bad_params.yaml"
LA_PF="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"tw $(printf '\x6c\x61\x75\x6e\x63\x68') nf-core/bacass --params-file $TMP/bad_params.yaml\"}}"
t "a launch's --params-file is read too"             deny  "$LA_PF" "$TMP/right_pipeline.jsonl"

t "略過導覽 stands the project gate down"            allow "$(pw "outdir: $BAD")" "$TMP/escape.jsonl"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
