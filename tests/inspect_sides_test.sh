#!/bin/bash
# D1: scripts/inspect_sides.sh has to give :setup evidence, not a guess, for
# "is this a brand new site or has someone already set it up" - and it has to
# do that within the one round trip this site's ssh costs (31s without a
# shared master, docs/SITE_ADAPTER.md). Two things are asserted mechanically
# rather than trusted: the key list is exactly the one the interface spec
# names, and the site side never costs more than ONE call to on_site.sh.
#
# Every invocation below runs through `clean`, which strips the ambient
# deployment out of the environment first. This machine already has one
# (LAB_RUNS_DIR pointed at a real run area) - without stripping it, "local
# side has no token" tests silently pass by reading a real member's token.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
S="$ROOT/scripts/inspect_sides.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

clean() { # clean <env assignments...> -- <args...>
  local envs=()
  while [ "$1" != -- ]; do envs+=("$1"); shift; done; shift
  env -u LAB_RUNS_DIR -u LAB_SETTINGS_FILE -u SEQERA_TOKEN_FILE \
      -u TW_AGENT_JAVA -u TW_AGENT_JAR -u TW_BIN \
      "${envs[@]}" "$@"
}

val() { # val <blob> <key> -> prints the value, or MISSING
  local blob="$1" key="$2"
  local v; v=$(sed -n "s/^${key}=//p" <<<"$blob" | head -1)
  [ -n "$v" ] && printf '%s\n' "$v" || printf 'MISSING\n'
}

kv() { # kv <label> <blob> <key> <want>
  local label="$1" blob="$2" key="$3" want="$4" got
  got=$(val "$blob" "$key")
  printf '%-64s ' "$label"
  [ "$got" = "$want" ] && echo ok || { echo "FAIL: $key=$got, wanted $want"; fails=$((fails+1)); }
}

# =============================================================================
# --site-probe in isolation: no on_site.sh, no ssh, just a constructed BASE.
HOMEDIR="$TMP/home"; mkdir -p "$HOMEDIR"
probe() { clean HOME="$HOMEDIR" LAB_RUNS_DIR="$1" -- bash "$S" --site-probe 2>&1; }

BASE1="$TMP/site_empty"
out=$(probe "$BASE1")
kv "empty site: settings=no"  "$out" site.settings no
kv "empty site: token=no"     "$out" site.token    no
kv "empty site: skeleton=no"  "$out" site.skeleton no
kv "empty site: java=no"      "$out" site.java     no
kv "empty site: jar=no"       "$out" site.jar      no
kv "empty site: runs=0"       "$out" site.runs     0

# A fully set-up site: settings + token beside it, the skeleton, java/jar, runs.
BASE2="$TMP/site_full"
mkdir -p "$BASE2/_personal" "$BASE2/_system/agent"
mkdir -p "$BASE2/alice/projects/gut/runs/rnaseq_gut_20260901"
mkdir -p "$BASE2/alice/projects/gut/runs/rnaseq_gut_20260905"
mkdir -p "$BASE2/bob/projects/other/runs/bacass_o_20260902"
cat > "$BASE2/_personal/env.yaml" <<YAML
reach: local
storage_root: $BASE2
agent_java: $TMP/fake-java
agent_jar: $TMP/fake.jar
YAML
chmod 600 "$BASE2/_personal/env.yaml"
SECRET_TOKEN='not-a-real-token-9Q7X'
printf '%s\n' "$SECRET_TOKEN" > "$BASE2/_personal/.seqera_token"; chmod 600 "$BASE2/_personal/.seqera_token"
printf '#!/bin/bash\nexit 0\n' > "$TMP/fake-java"; chmod +x "$TMP/fake-java"
: > "$TMP/fake.jar"; chmod 644 "$TMP/fake.jar"

out=$(probe "$BASE2")
kv "full site: settings=yes"  "$out" site.settings yes
kv "full site: token=yes"     "$out" site.token    yes
kv "full site: skeleton=yes"  "$out" site.skeleton yes
kv "full site: java=yes"      "$out" site.java     yes
kv "full site: jar=yes"       "$out" site.jar      yes
kv "full site: runs=3"        "$out" site.runs     3

printf '%-64s ' "full site: the token's value is never printed"
grep -qF "$SECRET_TOKEN" <<<"$out" && { echo "FAIL: leaked"; fails=$((fails+1)); } || echo ok

# =============================================================================
# Top-level dispatch: reach=none.
NONEHOME="$TMP/nonehome"; mkdir -p "$NONEHOME"
run_none() { clean HOME="$NONEHOME" LAB_SETTINGS_FILE="$TMP/none.yaml" -- bash "$S" "$@"; }
printf 'reach: none\n' > "$TMP/none.yaml"
out=$(run_none 2>&1)
kv "reach:none - reach echoed"            "$out" reach            none
kv "reach:none - site.reachable=unknown"  "$out" site.reachable   unknown
for k in site.settings site.token site.skeleton site.tw site.java site.jar site.runs; do
  kv "reach:none - $k=unknown" "$out" "$k" unknown
done
printf '%-64s ' "reach:none - says why, so it is not mistaken for a bug"
run_none 2>&1 1>/dev/null | grep -qiF "no login node" && echo ok \
  || { echo "FAIL: no explanation on stderr"; fails=$((fails+1)); }
printf '%-64s ' "reach:none - the explanation is not on stdout"
run_none 2>/dev/null | grep -qiF "no login node" \
  && { echo "FAIL: prose leaked into the key=value stream"; fails=$((fails+1)); } || echo ok

# =============================================================================
# Real on_site.sh under ON_SITE_DRY_RUN=1: no ssh, no network, no site - the
# same seam tests/on_site_test.sh relies on. This only proves the plumbing
# needs neither; the mechanical "exactly one call" proof is the counter-based
# check below, where the count is actually observable from outside.
SSHHOME="$TMP/sshhome"; mkdir -p "$SSHHOME"
printf 'reach: ssh\nsite_host: me@example.org\n' > "$TMP/ssh.yaml"
out=$(clean HOME="$SSHHOME" LAB_SETTINGS_FILE="$TMP/ssh.yaml" ON_SITE_DRY_RUN=1 \
      ON_SITE_SSH_BIN="$TMP/never-called-ssh" -- bash "$S" 2>&1)
rc_dry=$?
printf '%-64s ' "reach:ssh under ON_SITE_DRY_RUN needs no ssh binary at all"
[ ! -e "$TMP/never-called-ssh" ] && echo ok || { echo "FAIL: something ran it"; fails=$((fails+1)); }
printf '%-64s ' "reach:ssh under ON_SITE_DRY_RUN still exits clean"
[ "$rc_dry" = 0 ] && echo ok || { echo "FAIL: rc $rc_dry <<$out>>"; fails=$((fails+1)); }

# =============================================================================
# Faked on_site.sh: control what the "site" answers with, to exercise the
# reachable=yes / reachable=no branches without a real network hop, and to
# COUNT how many times on_site.sh actually ran - the mechanical proof that
# the site side costs exactly one round trip, no matter how many site.* keys
# there are.
FAKESITE="$TMP/fakesite_scripts"; mkdir -p "$FAKESITE/utils"
cp "$ROOT"/scripts/*.sh "$FAKESITE"/ 2>/dev/null
cp "$ROOT"/scripts/utils/*.sh "$FAKESITE/utils/" 2>/dev/null
COUNTER="$TMP/on_site_calls"

cat > "$FAKESITE/on_site.sh" <<EOF
#!/bin/bash
echo call >> "$COUNTER"
if [ "\${FAKE_SITE_FAIL:-}" = 1 ]; then
  echo "the master connection is down" >&2
  exit 2
fi
cat <<'SITE'
site.settings=yes
site.token=no
site.skeleton=yes
site.tw=yes
site.java=no
site.jar=yes
site.runs=7
SITE
EOF
chmod +x "$FAKESITE/on_site.sh"

FS="$FAKESITE/inspect_sides.sh"
run_fake() { : > "$COUNTER"; clean HOME="$TMP/fakehome" LAB_SETTINGS_FILE="$TMP/fake.yaml" -- bash "$FS" "$@" 2>&1; }
mkdir -p "$TMP/fakehome"

printf 'reach: ssh\nsite_host: me@example.org\n' > "$TMP/fake.yaml"
out=$(run_fake)
kv "faked site (reachable): reachable=yes" "$out" site.reachable yes
kv "faked site (reachable): settings=yes"  "$out" site.settings  yes
kv "faked site (reachable): tw=yes"        "$out" site.tw        yes
kv "faked site (reachable): runs=7"        "$out" site.runs      7
printf '%-64s ' "faked site (reachable): exactly one on_site.sh call"
[ "$(wc -l < "$COUNTER")" = 1 ] && echo ok || { echo "FAIL: $(wc -l < "$COUNTER") calls"; fails=$((fails+1)); }

out=$(FAKE_SITE_FAIL=1 run_fake)
kv "faked site (unreachable): reachable=no" "$out" site.reachable no
for k in site.settings site.token site.skeleton site.tw site.java site.jar site.runs; do
  kv "faked site (unreachable): $k=unknown" "$out" "$k" unknown
done
printf '%-64s ' "faked site (unreachable): still exactly one call"
[ "$(wc -l < "$COUNTER")" = 1 ] && echo ok || { echo "FAIL"; fails=$((fails+1)); }

# =============================================================================
# Local side: checked directly, no site involved at all.
LOCALCHECK="$TMP/localcheck"; mkdir -p "$LOCALCHECK/.config"
printf 'reach: local\n' > "$LOCALCHECK/.config/env.yaml"
run_local() { clean HOME="$LOCALCHECK" LAB_SETTINGS_FILE="$LOCALCHECK/.config/env.yaml" -- bash "$S" "$@" 2>&1; }

out=$(run_local)
kv "local.settings=yes when the file is right there" "$out" local.settings yes
kv "local.token=no when there is no token file"       "$out" local.token   no
kv "local.skeleton=no with no local workspace"         "$out" local.skeleton no

mkdir -p "$LOCALCHECK/agentic-bioflow"
out=$(run_local)
kv "local.skeleton=yes once the local root exists" "$out" local.skeleton yes

: > "$LOCALCHECK/.config/.seqera_token"; chmod 600 "$LOCALCHECK/.config/.seqera_token"
out=$(run_local)
kv "local.token=yes once the token file exists" "$out" local.token yes

printf '%-64s ' "local side: never prints the token's value"
echo 'super-secret-value' > "$LOCALCHECK/.config/.seqera_token"
out=$(run_local)
grep -qF "super-secret-value" <<<"$out" && { echo "FAIL: leaked"; fails=$((fails+1)); } || echo ok

# =============================================================================
# The exact key list and order from the interface spec (the appendix in the
# plan). status.sh and anything else downstream parses this by key, but the
# order is still worth pinning: a stray key or a dropped one is a silent
# contract break otherwise.
WANT_KEYS='reach
site.reachable
site.settings
site.token
site.skeleton
site.tw
site.java
site.jar
site.runs
local.settings
local.token
local.skeleton
local.tw'
GOT_KEYS=$(sed -n 's/=.*//p' <<<"$out")
printf '%-64s ' "emits exactly the 13 contract keys, in order"
[ "$GOT_KEYS" = "$WANT_KEYS" ] && echo ok \
  || { echo "FAIL: got:"; echo "$GOT_KEYS"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
