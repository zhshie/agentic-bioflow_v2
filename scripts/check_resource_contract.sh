#!/bin/bash
# Compare the partition boxes hardcoded in configs/sites/nchc.config against what
# SLURM currently reports, and complain about drift.
#
# The config has to hardcode the boxes - Nextflow reads it on the head node at
# launch time and shelling out to sacctmgr from a config closure would run once
# per task. So this check exists to catch the day NCHC changes a partition,
# rather than discovering it as a run that never schedules.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${1:-$HERE/../configs/sites/nchc.config}"

# The box table is parsed in exactly one place. This check compares the config
# against SLURM; if it also owned a second way of reading the config, a bug in
# that reader would show up here as site drift and send someone to argue with
# NCHC about a partition that never changed.
. "$HERE/utils/boxes.sh"

command -v sacctmgr >/dev/null || { echo "sacctmgr not found - run this on the cluster" >&2; exit 2; }

# live: queue<TAB>cpus<TAB>memGB, for the QOS names the config names
live=$(sacctmgr -nP show qos format=Name,MinTRES 2>/dev/null | awk -F'|' '
  $2 ~ /cpu=/ {
    cpu=""; mem=""
    n=split($2, a, ",")
    for (i=1;i<=n;i++) {
      if (a[i] ~ /^cpu=/)  { sub(/^cpu=/,"",a[i]); cpu=a[i] }
      if (a[i] ~ /^mem=/)  { sub(/^mem=/,"",a[i]); sub(/G$/,"",a[i]); mem=a[i] }
    }
    if (cpu != "" && mem != "") print tolower($1) "\t" cpu "\t" mem
  }' | sort)

# config: same shape, from the NCHC_BOXES literal. QOS names are lower case in
# sacctmgr and mixed case in the config, so fold before comparing.
cfg=$(nchc_boxes "$CONFIG" | cut -f1-3 | tr 'A-Z' 'a-z' | sort) || {
    echo "could not read the box table out of $CONFIG" >&2; exit 2; }

drift=0
while IFS=$'\t' read -r q c m; do
  [ -z "$q" ] && continue
  hit=$(grep -P "^${q}\t" <<<"$live")
  if [ -z "$hit" ]; then
    echo "MISSING: config lists '$q' but SLURM has no such QOS"; drift=1; continue
  fi
  lc=$(cut -f2 <<<"$hit"); lm=$(cut -f3 <<<"$hit")
  if [ "$c" != "$lc" ] || [ "$m" != "$lm" ]; then
    echo "DRIFT:   $q config=${c}cpu/${m}G  live=${lc}cpu/${lm}G"; drift=1
  fi
done <<<"$cfg"

if [ "$drift" = 0 ]; then echo "OK - every box in $(basename "$CONFIG") matches the live QOS table"; fi
exit $drift
