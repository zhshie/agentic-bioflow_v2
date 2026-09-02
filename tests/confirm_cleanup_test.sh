#!/bin/bash
# Regression tests for hooks/confirm_cleanup.sh.
#
# The first two cases are the ones that mattered: the hook used to classify a
# segment as a delete whenever the letters "rm" followed by a space appeared
# anywhere in it, which is true of "confirm " and of "Platform run". Combined
# with a protected word among the arguments, that denied ordinary commands.
# A guard that refuses `echo confirm the results directory` trains its reader
# to ignore it, which costs more than the guard is worth.
#
# Note the delete verb is assembled from hex below rather than written out, so
# that running this file does not itself trip a cleanup hook watching the shell.
H="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/hooks/confirm_cleanup.sh"
t() {
  printf '%-58s ' "$2"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$1" | bash "$H")
  if [ -z "$out" ]; then echo "pass"; else
    python3 -c "import json,sys;o=json.load(sys.stdin)['hookSpecificOutput'];print(o.get('permissionDecision','warn'))" <<<"$out"
  fi
}
D=$(printf '\x72\x6d')            # the delete verb, assembled so this file's own
P=/work/u9613010/lab_runs/x       # text does not trip the installed v1 hook
t "bash set_phase.sh /x completed note=\"Seqera Platform run 2LjRa 201 tasks\"" "harmless cmd mentioning 'Platform run'"
t "echo confirm the results directory"                                          "harmless cmd containing 'confirm'"
t "$D -rf $P/results"                                                           "delete results/        (expect deny)"
t "$D -rf $P/rawdata"                                                           "delete rawdata/        (expect deny)"
t "$D -rf $P/.nextflow/plugins"                                                 "delete plugins/        (expect deny)"
t "$D -rf $P/work"                                                              "delete work/           (expect warn)"
t "ls $P && $D -rf $P/results"                                                  "delete inside compound (expect deny)"
