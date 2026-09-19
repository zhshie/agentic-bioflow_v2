#!/bin/bash
# Guardrail 1 (T26): scripts/duplicate_run_check.sh flags when a project and
# samplesheet about to be launched already has an active run behind it.
# Fakes `tw` so this runs with no real workspace and no network.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
P="$ROOT/scripts/duplicate_run_check.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

has()    { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2' <<$3>>"; fails=$((fails+1)); }; }
hasnot() { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && { echo "FAIL: found '$2'"; fails=$((fails+1)); } || echo ok; }

printf '%s\n' 'reach: ssh' 'site_host: me@example.org' 'workspace_id: 1' \
    'seqera_user: alice' "tw_bin: $TMP/tw" 'language: en' > "$TMP/env.yaml"
: > "$TMP/.seqera_token"
mkdir -p "$TMP/params"

cat > "$TMP/tw" <<'EOF'
#!/bin/bash
case "$*" in
    *"runs list"*) cat "$RUNS_LIST_FILE" ;;
    *"--params"*)
        id=""; prev=""
        for a in "$@"; do [ "$prev" = "-i" ] && id="$a"; prev="$a"; done
        f="$PARAMS_DIR/$id.txt"
        [ -r "$f" ] && cat "$f"
        ;;
    *) exit 1 ;;
esac
EOF
chmod +x "$TMP/tw"

cat > "$TMP/runs.json" <<'EOF'
{"workflows":[
  {"workflow":{"id":"r-alpha","runName":"tiny_hedgehog","projectName":"nf-core/rnaseq","status":"RUNNING","userName":"alice"}},
  {"workflow":{"id":"r-gamma","runName":"old_one","projectName":"nf-core/rnaseq","status":"SUCCEEDED","userName":"alice"}},
  {"workflow":{"id":"r-delta","runName":"bobs_run","projectName":"nf-core/rnaseq","status":"RUNNING","userName":"bob"}}
]}
EOF
cat > "$TMP/params/r-alpha.txt" <<'EOF'
outdir: /lab/alice/projects/proj_a/runs/rnaseq_x_20260101/results
input: https://tower.example/datasets/1/n/cohort1_samplesheet
EOF
cat > "$TMP/params/r-delta.txt" <<'EOF'
outdir: /lab/alice/projects/proj_a/runs/rnaseq_y_20260102/results
input: https://tower.example/datasets/9/n/other_samplesheet
EOF

mkdir -p "$TMP/sheets"
touch "$TMP/sheets/cohort1_samplesheet.csv"
touch "$TMP/sheets/unrelated.csv"

run() {
    LAB_SETTINGS_FILE="$TMP/env.yaml" RUNS_LIST_FILE="$TMP/runs.json" PARAMS_DIR="$TMP/params" \
    bash "$P" "$@" 2>&1
}

echo "== same project, same-named samplesheet: flagged =="
out=$(run --project proj_a --samplesheet "$TMP/sheets/cohort1_samplesheet.csv")
rc=$?
printf '%-64s ' "exits 1 (a match was found)"
[ "$rc" = 1 ] && echo ok || { echo "FAIL: rc $rc"; fails=$((fails+1)); }
has "names the matching run"      "r-alpha" "$out"
has "names its status"            "RUNNING" "$out"
has "names the project"           "proj_a"  "$out"

echo
echo "== same project, different samplesheet: not flagged =="
out=$(run --project proj_a --samplesheet "$TMP/sheets/unrelated.csv")
rc=$?
printf '%-64s ' "exits 0 (nothing matched)"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
printf '%-64s ' "prints nothing"
[ -z "$out" ] && echo ok || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }

echo
echo "== a different project entirely: not flagged even with the same sheet name =="
out=$(run --project proj_z --samplesheet "$TMP/sheets/cohort1_samplesheet.csv")
rc=$?
printf '%-64s ' "exits 0"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }

echo
echo "== another member's run is never counted as this member's duplicate =="
out=$(run --project proj_a --samplesheet "$TMP/sheets/unrelated.csv")
hasnot "bob's run never appears" "bobs_run" "$out"

echo
echo "== bilingual output: the same match in zh-TW reads in Chinese =="
printf '%s\n' 'reach: ssh' 'site_host: me@example.org' 'workspace_id: 1' \
    'seqera_user: alice' "tw_bin: $TMP/tw" 'language: zh-TW' > "$TMP/env_zh.yaml"
out=$(LAB_SETTINGS_FILE="$TMP/env_zh.yaml" RUNS_LIST_FILE="$TMP/runs.json" PARAMS_DIR="$TMP/params" \
      bash "$P" --project proj_a --samplesheet "$TMP/sheets/cohort1_samplesheet.csv" 2>&1)
has "carries the run id regardless of language" "r-alpha" "$out"
has "reads in zh-TW"                            "看起來像重複" "$out"

echo
echo "== usage errors =="
printf '%-64s ' "missing --samplesheet exits 2"
LAB_SETTINGS_FILE="$TMP/env.yaml" bash "$P" --project proj_a >/dev/null 2>&1
rc=$?
[ "$rc" = 2 ] && echo ok || { echo "FAIL: rc $rc"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
