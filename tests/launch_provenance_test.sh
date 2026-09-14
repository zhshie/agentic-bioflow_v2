#!/bin/bash
# commands/launch.md: provenance is on by default for a launch (R1,
# docs/PITFALLS.md 32), and step 2's evidence has to survive the gate that
# reads it (docs/PITFALLS.md 33).
#
# Static, not behavioural, for the same reason tests/no_per_pipeline_config.sh
# and tests/command_layer_is_site_neutral.sh are: commands/*.md is prose
# Claude follows, not code with a return value, so the only thing checkable
# without running a real session is what the text actually says.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
L="$ROOT/commands/launch.md"
fails=0

ok() { printf '%-72s ok\n' "$1"; }
no() { printf '%-72s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

[ -f "$L" ] || { echo "FAIL: $L does not exist"; exit 1; }

# 1. The provenance.config block itself: the plugin coordinate and the wrroc
#    format are both load-bearing - get either wrong and the config being
#    described is not the one PITFALLS 32 actually measured on this site.
grep -qF "nf-prov@1.7.0" "$L" \
  && ok "names the measured nf-prov plugin version" \
  || no "names the measured nf-prov plugin version" "'nf-prov@1.7.0' not found"

grep -qF "wrroc" "$L" \
  && ok "the provenance.config block configures the wrroc format" \
  || no "the provenance.config block configures the wrroc format" "'wrroc' not found"

# 2. The launch command shown to the user actually carries the config - not
#    just a config file sitting on disk nobody passes in.
grep -qE -- '--config[[:space:]]+.*provenance\.config' "$L" \
  && ok "the shown launch command passes --config <run>/provenance.config" \
  || no "the shown launch command passes --config <run>/provenance.config" \
        "no '--config ... provenance.config' found"

# 3. The two facts a user has to be told, not just recorded in this repo's
#    own docs where they would never see them (PITFALLS 32).
grep -qiE 'no checksum' "$L" \
  && ok "states that no checksum is recorded" \
  || no "states that no checksum is recorded" "no mention of 'no checksum'"

grep -qE '25\.10' "$L" \
  && ok "states the Nextflow >= 25.10 requirement" \
  || no "states the Nextflow >= 25.10 requirement" "no mention of 25.10"

# 4. Personal details never go into the crate by default (the safety net,
#    PRINCIPLES.md). Two checks: the file must say not to do this, and it
#    must not itself contain a literal email address anywhere - a hardcoded
#    personal detail in a file meant to be site-neutral and installable by
#    anyone (invariant 3) would be the same mistake this text warns against.
grep -qiE "do not put[^\n]{0,60}(name|email)" "$L" \
  && ok "explicitly says not to put the user's name/email into it by default" \
  || no "explicitly says not to put the user's name/email into it by default" \
        "no 'do not put ... name/email' sentence found"

EMAIL_RE='[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
if grep -qE "$EMAIL_RE" "$L"; then
  no "carries no literal email address" "found something matching an email address"
else
  ok "carries no literal email address"
fi

# 5. docs/PITFALLS.md 33: the diagram/stage list step has to end the turn, or
#    the walkthrough gate (G1) can deny a run whose evidence never reached
#    the transcript it reads.
grep -qiE 'final text' "$L" \
  && ok "step 2 says the diagram/stage list must be the final text of the turn" \
  || no "step 2 says the diagram/stage list must be the final text of the turn" \
        "no 'final text' language found"

# 6. commands/*.md stays site-neutral and pipeline-agnostic even with this
#    addition - the same forbidden-term list tests/command_layer_is_site_neutral.sh
#    enforces, checked here directly so a regression in this file shows up
#    under this test's own name too.
TERMS='slurm|sbatch|squeue|scontrol|sacctmgr|qos|partition|relay|proxy|singularity|module load|\bssh\b|\bscp\b|\brsync\b'
if grep -qP "$TERMS" "$L"; then
  no "stays site-neutral (no scheduler/egress/container vocabulary)" \
     "found a forbidden term - see tests/command_layer_is_site_neutral.sh"
else
  ok "stays site-neutral (no scheduler/egress/container vocabulary)"
fi

echo
[ "$fails" = 0 ] && echo "OK: launch_provenance_test" || { echo "$fails failed"; exit 1; }
