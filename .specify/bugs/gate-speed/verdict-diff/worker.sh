#!/bin/bash
# worker.sh <payload-file> <ctx> <hook>
# Runs the hook from the baseline tree (A) and from the new tree (B) on the same
# payload in the same context; compares exit code + stdout + stderr (tree paths
# normalised) and records the wall time of each run.
#   SAME <payload> <ctx> <hook> rc= out= err= kind= msA= msB=
#   DIFF ...   (files kept in /tmp/abf34_res)
#   SLOW ...   (identical output, but B took more than 2x A + 300 ms, or over 10 s)
# Contexts:
#   c0 original payload, c1 in use, c2 in use + slash-command marker in the transcript,
#   c3 session not in use, mingw (c1 with a uname that says MINGW64, so D3 and the
#   shared splitter answer run), nojq (c1 with no jq on PATH), badjq (c1 with a jq
#   that always fails).
P="$1"; CTX="$2"; H="$3"
A=/tmp/abf34_A; B=/tmp/abf34_B
C=/tmp/abf34_ctx
RES=/tmp/abf34_res; mkdir -p "$RES"
base=$(basename "$P")
PATHX="$PATH"
case "$CTX" in
  c1) TP="$C/tr_plain.jsonl"; SID=s1 ;;
  c2) TP="$C/tr_slash.jsonl"; SID=s1 ;;
  c3) TP="$C/tr_plain.jsonl"; SID=s9 ;;
  c0) TP=""; SID="" ;;
  mingw) TP="$C/tr_plain.jsonl"; SID=s1; PATHX="$C/bin_mingw:$PATH" ;;
  nojq)  TP="$C/tr_plain.jsonl"; SID=s1; PATHX="$C/bin_nojq" ;;
  badjq) TP="$C/tr_plain.jsonl"; SID=s1; PATHX="$C/bin_badjq:$PATH" ;;
esac
now_ms() { local e=${EPOCHREALTIME/[.,]/}; echo $((e / 1000)); }
run() { # run <tree> <out-prefix>
  local T="$1" O="$2" inp s e
  inp=$(mktemp)
  if [ "$CTX" = c0 ]; then
    cat "$P" > "$inp"
  elif [[ $P == *.json ]]; then
    sed -e "s#@CWD@#$C/work#g" -e "s#@TP@#$TP#g" -e "s#@ROOT@#$T#g" \
        -e "s#\"session_id\": *\"s1\"#\"session_id\":\"$SID\"#" "$P" > "$inp"
  else
    # captured / raw payload: rewrite the three context fields when it is a JSON object
    if /usr/bin/jq -e . "$P" >/dev/null 2>&1; then
      /usr/bin/jq -c --arg sid "$SID" --arg cwd "$C/work" --arg tp "$TP" '(if type=="object" then (.session_id=$sid | .cwd=$cwd | .transcript_path=$tp) else . end)' "$P" > "$inp"
    else
      cat "$P" > "$inp"
    fi
  fi
  s=$(now_ms)
  ( cd "$C/work" && env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR HOME="$C/home" XDG_CONFIG_HOME="$C/home/.config" \
      AGENTIC_BIOFLOW_STATE_DIR="$C/state" CLAUDE_PLUGIN_ROOT="$T" PATH="$PATHX" \
      timeout 60 bash "$T/hooks/$H.sh" < "$inp" > "$O.out" 2> "$O.err"; echo $? > "$O.rc" )
  e=$(now_ms); echo $((e - s)) > "$O.ms"
  rm -f "$inp"
  sed -i -E -e "s#/tmp/abf34_[AB]#/T#g" -e "s/line [0-9]+:/line N:/g" "$O.out" "$O.err"   # script line numbers differ between trees
}
k="$RES/$base.$CTX.$H"
run "$A" "$k.A"; run "$B" "$k.B"
msA=$(cat "$k.A.ms"); msB=$(cat "$k.B.ms")
if cmp -s "$k.A.rc" "$k.B.rc" && cmp -s "$k.A.out" "$k.B.out" && cmp -s "$k.A.err" "$k.B.err"; then
  kind=$(/usr/bin/jq -r '.hookSpecificOutput.permissionDecision // (if .hookSpecificOutput.additionalContext then "ctx" else "none" end)' "$k.A.out" 2>/dev/null | head -1)
  tag=SAME
  if [ "$msB" -gt $((msA * 2 + 300)) ] || [ "$msB" -gt 10000 ]; then tag=SLOW; fi
  echo "$tag $base $CTX $H rc=$(cat $k.A.rc) out=$(wc -c < $k.A.out) err=$(wc -c < $k.A.err) kind=${kind:-none} msA=$msA msB=$msB"
  rm -f "$k".A.* "$k".B.*
else
  echo "DIFF $base $CTX $H rc=$(cat $k.A.rc)/$(cat $k.B.rc) msA=$msA msB=$msB"
fi
