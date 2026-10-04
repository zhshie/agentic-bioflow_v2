#!/bin/bash
# abf_34_worker.sh <payload-file> <ctx> <hook>
# Runs the hook from the baseline tree (A) and from the new tree (B) on the same
# payload in the same context, compares exit code + stdout + stderr (tree paths
# normalised). Prints one line: SAME or DIFF, with the files kept for a DIFF.
P="$1"; CTX="$2"; H="$3"
A=/tmp/abf34_A; B=/tmp/abf34_B
C=/tmp/abf34_ctx
RES=/tmp/abf34_res; mkdir -p "$RES"
base=$(basename "$P")
case "$CTX" in
  c1) TP="$C/tr_plain.jsonl"; SID=s1 ;;
  c2) TP="$C/tr_slash.jsonl"; SID=s1 ;;
  c3) TP="$C/tr_plain.jsonl"; SID=s9 ;;
  c0) TP=""; SID="" ;;
esac
run() { # run <tree> <out-prefix>
  local T="$1" O="$2" inp
  inp=$(mktemp)
  if [ "$CTX" = c0 ]; then
    cat "$P" > "$inp"
  elif [[ $P == *.json ]]; then
    sed -e "s#@CWD@#$C/work#g" -e "s#@TP@#$TP#g" -e "s#@ROOT@#$T#g" -e "s#\"session_id\":\"s1\"#\"session_id\":\"$SID\"#" "$P" > "$inp"
  else
    # captured / raw payload: rewrite the three context fields when it is JSON
    if jq -e . "$P" >/dev/null 2>&1; then
      jq -c --arg sid "$SID" --arg cwd "$C/work" --arg tp "$TP" '(if type=="object" then (.session_id=$sid | .cwd=$cwd | .transcript_path=$tp) else . end)' "$P" > "$inp"
    else
      cat "$P" > "$inp"
    fi
  fi
  ( cd "$C/work" && env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR HOME="$C/home" XDG_CONFIG_HOME="$C/home/.config" \
      AGENTIC_BIOFLOW_STATE_DIR="$C/state" CLAUDE_PLUGIN_ROOT="$T" \
      bash "$T/hooks/$H.sh" < "$inp" > "$O.out" 2> "$O.err"; echo $? > "$O.rc" )
  rm -f "$inp"
  sed -i "s#/tmp/abf34_[AB]#/T#g" "$O.out" "$O.err"
}
k="$RES/$base.$CTX.$H"
run "$A" "$k.A"; run "$B" "$k.B"
if cmp -s "$k.A.rc" "$k.B.rc" && cmp -s "$k.A.out" "$k.B.out" && cmp -s "$k.A.err" "$k.B.err"; then
  echo "SAME $base $CTX $H rc=$(cat $k.A.rc) out=$(wc -c < $k.A.out) err=$(wc -c < $k.A.err) kind=$(jq -r ".hookSpecificOutput.permissionDecision // (if .hookSpecificOutput.additionalContext then \"ctx\" else \"none\" end)" $k.A.out 2>/dev/null | head -1)"; rm -f "$k".A.* "$k".B.*
else
  echo "DIFF $base $CTX $H"
fi
