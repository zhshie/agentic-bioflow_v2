#!/bin/bash
# T11: the run area was never designed - it accreted. A real listing showed
# probe directories from setup rehearsals sitting beside real analyses in one
# run area, and a second run area shaped differently again (rawdata/ results/
# _work/ at the top instead of per-member). scripts/init_workspace.sh is the
# fix: one script, both sides, and the tests below are what "designed" has to
# mean in practice - the skeleton it makes actually agrees with the safety net
# that protects it, nothing it creates can eat existing data, and running it
# twice is a no-op.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/init_workspace.sh"
H="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/hooks/confirm_cleanup.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

t() { # t <label> <expect-rc> <expect-substring|""> -- <args...>
  local label="$1" want_rc="$2" want="$3"; shift 4
  printf '%-64s ' "$label"
  local out rc; out=$("$@" 2>&1); rc=$?
  if [ "$rc" != "$want_rc" ]; then echo "FAIL: rc $rc wanted $want_rc <<$out>>"; fails=$((fails+1)); return; fi
  if [ -n "$want" ] && ! grep -qF -- "$want" <<<"$out"; then echo "FAIL: lacks '$want' <<$out>>"; fails=$((fails+1)); return; fi
  echo ok
}

# The hook denies a delete by matching a literal path component - see
# HIT_PROTECTED / HIT_SHARED in hooks/confirm_cleanup.sh. Feed it exactly what
# the site skeleton just created and check the verdict is "deny", the same way
# tests/confirm_cleanup_test.sh does. This is the check the ticket asks for
# directly: "the skeleton and the safety net agree."
D=$(printf '\x72\x6d')   # the delete verb, kept out of this file's own text
# One place asks the hook, so the "does it deny?" question cannot drift between
# the case that wants a yes and the case that wants a no.
hook_says_deny() { # hook_says_deny <path> -> exit 0 if the hook denies deleting it
  local path="$1" out got
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" \
        "$D -rf $path" | bash "$H")
  if [ -z "$out" ]; then got=pass; else
    got=$(python3 -c "import json,sys;o=json.load(sys.stdin)['hookSpecificOutput'];print(o.get('permissionDecision','warn'))" <<<"$out")
  fi
  [ "$got" = deny ]
}

deny_check() { # deny_check <label> <path>
  local label="$1" path="$2"
  printf '%-64s ' "$label"
  if hook_says_deny "$path"; then echo ok
  else echo "FAIL: expected deny"; fails=$((fails+1)); fi
}

# ---------------------------------------------------------------------------
# Site side
RUNS="$TMP/site_runs"
site() { LAB_RUNS_DIR="$RUNS" bash "$S" site "$@"; }

PROJ=gut_study
out=$(site --user alice --project "$PROJ" 2>&1); rc=$?
t "site: exits clean"                              0 "" -- true
[ "$rc" = 0 ] || { echo "FAIL: site --user alice exited $rc: $out"; fails=$((fails+1)); }

for d in _personal _references _singularity_cache \
         _system/agent _system/relay _system/coldstart \
         alice/projects "alice/projects/$PROJ/rawdata" "alice/projects/$PROJ/runs"; do
  printf '%-64s ' "site created $d"
  if [ -d "$RUNS/$d" ]; then echo ok; else echo "FAIL: $RUNS/$d missing"; fails=$((fails+1)); fi
done

printf '%-64s ' "site: _personal/ is mode 700, per person on a shared account"
m=$(stat -c %a "$RUNS/_personal"); [ "$m" = 700 ] && echo ok || { echo "FAIL: mode $m"; fails=$((fails+1)); }

printf '%-64s ' "site: prints the tree it made"
grep -qF "_singularity_cache/" <<<"$out" && grep -qF "alice/" <<<"$out" && echo ok \
  || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }

# The actual point of the ticket: the names the skeleton just built are the
# same names hooks/confirm_cleanup.sh refuses to delete.
deny_check "hook denies deleting site _references/"          "$RUNS/_references"
deny_check "hook denies deleting site _singularity_cache/"    "$RUNS/_singularity_cache"
deny_check "hook denies deleting a project's rawdata"         "$RUNS/alice/projects/$PROJ/rawdata"

# PITFALLS 17 was a protected name nothing wrote to. It was fixed in the hook,
# and the skeleton went on creating the decoy: the comment justifying that name
# still cited a hook that no longer needs it. So the skeleton is now pinned to
# the config that actually writes images, not only to the hook that guards them.
# A directory named by neither is an empty one, and an empty one is the whole
# failure mode - a guard on a path nothing uses stays quiet until it matters.
printf '%-64s ' "site: the image cache is the one nchc.config resolves to"
CFGF="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/configs/sites/nchc.config"
cfg=$(grep NXF_SINGULARITY_CACHEDIR "$CFGF" | grep -oE '/[A-Za-z0-9_.-]+"' | tr -d '/"' | head -1)
if [ -n "$cfg" ] && [ -d "$RUNS/$cfg" ]; then echo ok
else echo "FAIL: config says '$cfg', skeleton has: $(ls -a "$RUNS" | tr '\n' ' ')"; fails=$((fails+1)); fi

# ...and the config default is only a default. ce_apply.sh pushes the settings
# key `singularity_cache` into the compute environment as
# NXF_SINGULARITY_CACHEDIR, which is the value nchc.config reads BEFORE its own
# fallback. On this deployment that points outside the run area at 27 GB of
# images, so creating the fallback name under $BASE would have built the third
# empty directory in this story rather than the first. Three readers, not two.
CACHE_ELSEWHERE="$TMP/elsewhere/images"
cat > "$TMP/env.yaml" <<YAML
storage_root: $TMP/site_runs2
singularity_cache: $CACHE_ELSEWHERE
YAML
out2=$(LAB_SETTINGS_FILE="$TMP/env.yaml" LAB_RUNS_DIR="$TMP/site_runs2" bash "$S" site --user alice 2>&1)
printf '%-64s ' "site: an overridden cache is not duplicated under the run area"
[ -d "$TMP/site_runs2/_singularity_cache" ] \
  && { echo "FAIL: built the fallback name anyway"; fails=$((fails+1)); } || echo ok
printf '%-64s ' "site: and the tree says where the images really are"
grep -qF "$CACHE_ELSEWHERE" <<<"$out2" && echo ok \
  || { echo "FAIL: <<$out2>>"; fails=$((fails+1)); }
printf '%-64s ' "site: the overridden path exists after the call"
[ -d "$CACHE_ELSEWHERE" ] && echo ok || { echo "FAIL: $CACHE_ELSEWHERE missing"; fails=$((fails+1)); }

# --run additionally scaffolds one run's own subdirectories.
site --user alice --project "$PROJ" --run rnaseq_gutmicrobiome_20260908 >/dev/null
RUN_DIR="$RUNS/alice/projects/$PROJ/runs/rnaseq_gutmicrobiome_20260908"
for d in logs results work; do
  printf '%-64s ' "site --run created $d"
  if [ -d "$RUN_DIR/$d" ]; then echo ok; else echo "FAIL: $RUN_DIR/$d missing"; fails=$((fails+1)); fi
done
deny_check "hook denies deleting that run's results/"   "$RUN_DIR/results"

# analysis/ is not built on the site any more: interactive editing happens
# where the IDE is, and one home beats two that drift.
printf '%-64s ' "site run dir has no analysis/ - its home is where the IDE is"
[ -d "$RUN_DIR/analysis" ] && { echo "FAIL: analysis/ must not exist on the site"; fails=$((fails+1)); } || echo ok

# work/ is the one deletable directory - the hook only WARNs on it, never
# denies, and confirm_cleanup_test.sh already covers that path. Checking here
# too would duplicate that test rather than this one's own concern.

# ---------------------------------------------------------------------------
# Idempotency and non-destruction: the two guarantees the ticket names by name
# ("is idempotent" / "never touches an existing directory's contents").
echo "a lab member's own file, not this script's to move or open" \
  > "$RUNS/alice/projects/$PROJ/rawdata/sample_R1.fastq.gz.placeholder"
before=$(stat -c %Y "$RUNS/alice/projects/$PROJ/rawdata/sample_R1.fastq.gz.placeholder")
before_sum=$(md5sum "$RUNS/alice/projects/$PROJ/rawdata/sample_R1.fastq.gz.placeholder")
site --user alice --project "$PROJ" >/dev/null 2>&1
rc2=$?
printf '%-64s ' "re-running site is a no-op exit"
[ "$rc2" = 0 ] && echo ok || { echo "FAIL: rc $rc2"; fails=$((fails+1)); }
after=$(stat -c %Y "$RUNS/alice/projects/$PROJ/rawdata/sample_R1.fastq.gz.placeholder")
after_sum=$(md5sum "$RUNS/alice/projects/$PROJ/rawdata/sample_R1.fastq.gz.placeholder")
printf '%-64s ' "and never touches a file already inside rawdata/"
[ "$before" = "$after" ] && [ "$before_sum" = "$after_sum" ] && echo ok \
  || { echo "FAIL: mtime or content changed"; fails=$((fails+1)); }

# ---------------------------------------------------------------------------
# Local side
LOCAL="$TMP/local_root"
local_() { bash "$S" local --root "$LOCAL" "$@"; }

out=$(local_ --user alice --project "$PROJ" 2>&1)
LPROJ="$LOCAL/alice/projects/$PROJ"
for d in rawdata runs analysis submission; do
  printf '%-64s ' "local project has $d/"
  if [ -d "$LPROJ/$d" ]; then echo ok; else echo "FAIL: $LPROJ/$d missing"; fails=$((fails+1)); fi
done

# rawdata/ now exists on BOTH sides, which reverses what this file used to
# assert. It is not a second home for the data: the site's copy is the one the
# compute nodes read, and the local one is the staging area push.sh sends from
# - what inbox/ used to be, renamed so the two ends of a transfer read alike.
printf '%-64s ' "local rawdata/ is the staging area, named like the site's"
[ -d "$LPROJ/rawdata" ] && echo ok || { echo "FAIL: missing"; fails=$((fails+1)); }

# submission/ is a sibling of analysis/, not a child, and the reason is the
# deletion guard: everything under analysis/ is undeletable by design, and a
# built package has to be throwable-away. Source and build output.
printf '%-64s ' "submission/ is a sibling of analysis/, not inside it"
[ -d "$LPROJ/analysis/submission" ] && { echo "FAIL: nested under analysis/"; fails=$((fails+1)); } || echo ok
deny_check "hook denies deleting the project's analysis/" "$LPROJ/analysis"
printf '%-64s ' "and the hook does NOT deny deleting submission/"
if hook_says_deny "$LPROJ/submission"; then
  echo "FAIL: submission/ cannot be rebuilt if it cannot be removed"; fails=$((fails+1))
else echo ok; fi

local_ --user alice --project "$PROJ" --run rnaseq_gutmicrobiome_20260908 >/dev/null
LRUN="$LPROJ/runs/rnaseq_gutmicrobiome_20260908"
for d in results; do
  printf '%-64s ' "local --run created $d"
  if [ -d "$LRUN/$d" ]; then echo ok; else echo "FAIL: $LRUN/$d missing"; fails=$((fails+1)); fi
done
printf '%-64s ' "local run dir has no work/ - only the site executes anything"
[ -d "$LRUN/work" ] && { echo "FAIL: work/ must not exist locally"; fails=$((fails+1)); } || echo ok

# The two sides' run/ directories share a name so a person can line them up by
# eye - that is the entire reason results/ exists in both places.
printf '%-64s ' "the two sides name the same run directory identically"
[ "$(basename "$RUN_DIR")" = "$(basename "$LRUN")" ] && echo ok \
  || { echo "FAIL: $RUN_DIR vs $LRUN"; fails=$((fails+1)); }

# ---------------------------------------------------------------------------
# Bad input, refused before anything is created.
t "no side given is refused"                        2 "usage" -- \
  env LAB_RUNS_DIR="$TMP/x1" bash "$S"
t "an unknown side is refused"                       2 "usage" -- \
  env LAB_RUNS_DIR="$TMP/x2" bash "$S" cloud --user alice
t "missing --user on the local side is refused"      2 "--user is required" -- \
  bash "$S" local --root "$TMP/x3"
t "a --user with a slash is refused, not turned into a path" 2 "" -- \
  env LAB_RUNS_DIR="$TMP/x4" bash "$S" site --user "../escape"
t "a --user starting with '_' is refused - it would collide with the shared areas" 2 \
  "reserved" -- env LAB_RUNS_DIR="$TMP/x5" bash "$S" site --user _references
t "site side with no run area known fails clearly, not silently"  2 \
  "no run area known" -- env -u LAB_RUNS_DIR bash "$S" site --user alice
t "--run without --project is refused - a run belongs to one project" 2 \
  "needs --project" -- env LAB_RUNS_DIR="$TMP/x6" bash "$S" site --run some_run_20260908

printf '%-64s ' "none of the refused calls created anything"
[ ! -e "$TMP/x1" ] && [ ! -e "$TMP/x2" ] && [ ! -e "$TMP/x3" ] \
  && [ ! -e "$TMP/x4" ] && [ ! -e "$TMP/x5" ] && [ ! -e "$TMP/x6" ] && echo ok \
  || { echo "FAIL: a rejected call still made a directory"; fails=$((fails+1)); }

# ---------------------------------------------------------------------------
# Step 1 of setup asks for a storage location before Seqera has answered who
# the member is (step 3), so the site side has to be usable with no --user at
# all: the shared areas first, the member's own subtree layered on once it is
# known. This is what makes that split possible.
SHARED_ONLY="$TMP/shared_only_runs"
out=$(LAB_RUNS_DIR="$SHARED_ONLY" bash "$S" site 2>&1); rc=$?
printf '%-64s ' "site with no --user still exits clean"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
for d in _personal _references _singularity_cache \
         _system/agent _system/relay _system/coldstart; do
  printf '%-64s ' "shared-only call still creates $d"
  if [ -d "$SHARED_ONLY/$d" ]; then echo ok; else echo "FAIL: $SHARED_ONLY/$d missing"; fails=$((fails+1)); fi
done
printf '%-64s ' "shared-only call creates no member subtree"
[ -d "$SHARED_ONLY/alice" ] && { echo "FAIL: a member directory appeared with no --user given"; fails=$((fails+1)); } || echo ok

LAB_RUNS_DIR="$SHARED_ONLY" bash "$S" site --user alice >/dev/null 2>&1
printf '%-64s ' "a later call with --user layers the member subtree on top"
[ -d "$SHARED_ONLY/alice/projects" ] && [ -d "$SHARED_ONLY/_references" ] && echo ok \
  || { echo "FAIL: layering did not produce both"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
