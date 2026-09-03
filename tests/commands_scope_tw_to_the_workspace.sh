#!/bin/bash
# `tw` without --workspace answers from the caller's personal workspace. The
# lab's pipelines, runs and compute environments are not there, so the reply is
# an empty list rather than an error - and an empty list reads as an answer.
# `tw pipelines list` said "nothing registered" during the first cold run for
# exactly this reason, and it happened to be true, which is worse: the same
# reply is what a fully populated workspace looks like from outside it.
#
# The token is not the workspace. Sourcing a shell env file that exports
# TOWER_ACCESS_TOKEN authenticates the call and still leaves it pointed
# somewhere else, which is why "but the token works" is not evidence here.
#
# So: any command file naming a workspace-scoped `tw` subcommand must also say
# where the workspace id comes from. `tw info` and `tw credentials` are not
# scoped and are deliberately not listed.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

SCOPED='tw (launch|pipelines|runs|datasets|compute-envs|actions|labels|secrets|members|teams|participants)'

fail=0
for f in "$ROOT"/commands/*.md; do
    rel="${f#"$ROOT"/}"
    grep -qE "$SCOPED" "$f" || continue
    if ! grep -q 'workspace_id' "$f"; then
        echo "$rel: calls a workspace-scoped tw subcommand but never says which workspace"
        fail=1
    fi
done

if [ "$fail" = 1 ]; then
    echo
    echo "FAIL: these calls will answer from the wrong workspace and look like an answer."
    exit 1
fi
echo "OK: every command calling a scoped tw subcommand resolves the workspace"
