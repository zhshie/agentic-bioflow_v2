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
#   a:<text>   assistant       h:<text>   a human turn
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

DIAG='here is the workflow: https://raw.githubusercontent.com/nf-core/bacass/2.4.0/docs/images/nf-core-bacass_metro_map.png'
SCHEMA='fetching https://raw.githubusercontent.com/nf-core/bacass/2.4.0/nextflow_schema.json'
ASK='{"type":"tool_use","name":"AskUserQuestion","input":{"questions":[]}}'

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
mktx "$TMP/asked.jsonl"  "a:$DIAG" "a:$SCHEMA" "a:$ASK" 'u:the user chose defaults'
mktx "$TMP/injected.jsonl" "a:$DIAG" "a:$SCHEMA" 'n:<task-notification>agent finished</task-notification>'
mktx "$TMP/escape.jsonl" 'a:nothing done at all' 'h:略過導覽'

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

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
