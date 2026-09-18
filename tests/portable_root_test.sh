#!/bin/bash
# T23 (Fixes #17): a portable folder lets a person carry their settings and
# token to a second machine without rerunning the whole of `setup`. This
# tests the two scripts that make that true: scripts/portable_root.sh (build
# the folder, migrate keys, encrypt/decrypt the token) and
# scripts/settings.sh --adopt/--reconstruct (point a machine at one, or
# rebuild from Platform when there is no portable folder at all).
#
# Real openssl is used throughout (present on every platform this repo
# targets); age is only exercised if actually on PATH, since none is
# installed here and none of this project's other tests assume it either.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/settings.sh"
P="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/portable_root.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

t()      { printf '%-64s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
has()    { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok \
           || { echo "FAIL: nothing matching '$2' <<$3>>"; fails=$((fails+1)); }; }
hasnot() { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" \
           && { echo "FAIL: found '$2'"; fails=$((fails+1)); } || echo ok; }

# Isolates HOME/XDG/LAB_* the same way every other settings-aware test in
# this suite does, so an ambient real deployment on the machine running the
# tests can never leak into a fixture.
clean() { # clean <env assignments...> -- <args...>
    local envs=()
    while [ "$1" != -- ]; do envs+=("$1"); shift; done; shift
    env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE \
        -u AGENTIC_BIOFLOW_STATE_DIR -u AGENTIC_BIOFLOW_REPORTS_DIR \
        "${envs[@]}" "$@"
}

# ---------------------------------------------------------------------------
# --adopt against a path that does not exist: explicit, names the path, and
# the common cause (a cloud folder still syncing) - not a bare "not found".
HOME_A="$TMP/m_missing"; mkdir -p "$HOME_A"
GHOST="$TMP/not_here_yet"
out=$(clean HOME="$HOME_A" XDG_CONFIG_HOME="$HOME_A/.config" -- \
      bash "$S" --adopt "$GHOST" 2>&1); rc=$?
t "adopting a path that does not exist is refused"  "$rc"  "1"
has "...names the exact path"                        "$GHOST" "$out"
has "...names the common cause (a cloud folder still syncing)" "cloud-sync" "$out"
printf '%-64s ' "...and writes no pointer file at all"
[ ! -e "$HOME_A/.config/agentic-bioflow/portable_root" ] && echo ok \
  || { echo "FAIL: a pointer file appeared anyway"; fails=$((fails+1)); }

# A path that exists but was never built by portable_root.sh init (no
# config/env.yaml) is refused the same way, naming what specifically is
# missing.
HALF="$TMP/half_built"; mkdir -p "$HALF"
out=$(clean HOME="$HOME_A" XDG_CONFIG_HOME="$HOME_A/.config" -- \
      bash "$S" --adopt "$HALF" 2>&1); rc=$?
t "adopting a folder with no config/env.yaml is refused"  "$rc"  "1"
has "...names config/env.yaml specifically"  "config/env.yaml" "$out"

# ---------------------------------------------------------------------------
# The whole point: init on machine 1, adopt + decrypt on machine 2, and the
# settings machine 2 reads back are IDENTICAL to what machine 1 had - for
# every portable key, not just one sampled at random.
M1="$TMP/machine1"; mkdir -p "$M1/.config/agentic-bioflow"
cat > "$M1/.config/agentic-bioflow/env.yaml" <<'YAML'
reach: ssh
seqera_user: alice
workspace_id: 424242
compute_env: ce-alice
slurm_account: MST999999
site_host: alice@site.example
site_user: sharedaccount
storage_root: /work/lab_runs
email: alice@example.org
language: en
record_adapter: none
agent_connection: conn-alice
local_root: /home/alice/agentic-bioflow
tw_bin: /home/alice/bin/tw
YAML
chmod 600 "$M1/.config/agentic-bioflow/env.yaml"
echo "the-real-plaintext-token-99887766" > "$M1/.config/agentic-bioflow/.seqera_token"
chmod 600 "$M1/.config/agentic-bioflow/.seqera_token"

m1() { clean HOME="$M1" XDG_CONFIG_HOME="$M1/.config" -- "$@"; }

PORTABLE="$TMP/shared_portable"
out=$(m1 env AGENTIC_BIOFLOW_TOKEN_PASSPHRASE="correct horse battery staple" \
       bash "$P" init "$PORTABLE" 2>&1); rc=$?
t "portable_root.sh init exits clean"  "$rc"  "0"
has "...reports the token was encrypted"  "encrypted the token" "$out"

for d in config projects; do
  printf '%-64s ' "init created $d/"
  [ -d "$PORTABLE/$d" ] && echo ok || { echo "FAIL: $PORTABLE/$d missing"; fails=$((fails+1)); }
done

printf '%-64s ' "every portable key migrated, none dropped"
ok=1
for key in reach seqera_user workspace_id compute_env slurm_account \
           site_host site_user storage_root email language record_adapter \
           agent_connection; do
  grep -q "^${key}: " "$PORTABLE/config/env.yaml" || { ok=0; echo "  missing key: $key"; }
done
[ "$ok" = 1 ] && echo ok || { echo "FAIL: see above"; fails=$((fails+1)); }

printf '%-64s ' "machine-derived keys are NOT migrated (local_root, tw_bin)"
grep -qE '^(local_root|tw_bin):' "$PORTABLE/config/env.yaml" \
  && { echo "FAIL: a machine-derived key leaked into the portable file"; fails=$((fails+1)); } \
  || echo ok

# --- the ciphertext never contains the plaintext token ----------------------
printf '%-64s ' "the portable token file is never plaintext"
grep -qF "the-real-plaintext-token-99887766" "$PORTABLE/config/.seqera_token.enc" \
  && { echo "FAIL: plaintext token leaked into the ciphertext file"; fails=$((fails+1)); } \
  || echo ok
printf '%-64s ' "the portable config/env.yaml never carries the token either"
grep -qF "the-real-plaintext-token-99887766" "$PORTABLE/config/env.yaml" \
  && { echo "FAIL: plaintext token leaked into env.yaml"; fails=$((fails+1)); } \
  || echo ok

# --- machine 2: adopt, then read back every portable key -------------------
M2="$TMP/machine2"; mkdir -p "$M2"
m2() { clean HOME="$M2" XDG_CONFIG_HOME="$M2/.config" -- "$@"; }

out=$(m2 bash "$S" --adopt "$PORTABLE" 2>&1); rc=$?
t "machine 2 adopts the folder machine 1 built"  "$rc"  "0"

printf '%-64s ' "every portable value machine 2 reads back matches machine 1, exactly"
ok=1
for kv in "reach:ssh" "seqera_user:alice" "workspace_id:424242" "compute_env:ce-alice" \
          "slurm_account:MST999999" "site_host:alice@site.example" "site_user:sharedaccount" \
          "storage_root:/work/lab_runs" "email:alice@example.org" "language:en" \
          "record_adapter:none" "agent_connection:conn-alice"; do
  key="${kv%%:*}"; want="${kv#*:}"
  got=$(m2 bash "$S" "$key")
  [ "$got" = "$want" ] || { ok=0; echo "  $key: got '$got' wanted '$want'"; }
done
[ "$ok" = 1 ] && echo ok || { echo "FAIL: see above"; fails=$((fails+1)); }

printf '%-64s ' "machine 2 has NOT inherited machine 1's local_root (machine-derived)"
got=$(m2 bash "$S" local_root "UNSET_DEFAULT")
[ "$got" = "UNSET_DEFAULT" ] && echo ok \
  || { echo "FAIL: got '$got' - a machine-derived key leaked across the adopt"; fails=$((fails+1)); }

# --- token decryption --------------------------------------------------------
printf '%-64s ' "machine 2 has no plaintext token before decrypting"
out=$(m2 bash "$S" --summary 2>&1)
has_local() { grep -qF -- "$1" <<<"$2"; }
has_local "not decrypted yet" "$out" \
  && echo ok || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }

out=$(m2 env AGENTIC_BIOFLOW_TOKEN_PASSPHRASE="wrong password entirely" \
       bash "$P" decrypt-token 2>&1); rc=$?
t "decrypting with the wrong passphrase is refused"  "$rc"  "1"
printf '%-64s ' "...and writes no plaintext token file"
[ ! -e "$M2/.config/agentic-bioflow/.seqera_token" ] && echo ok \
  || { echo "FAIL: a token file appeared despite the wrong passphrase"; fails=$((fails+1)); }

out=$(m2 env AGENTIC_BIOFLOW_TOKEN_PASSPHRASE="correct horse battery staple" \
       bash "$P" decrypt-token 2>&1); rc=$?
t "decrypting with the right passphrase succeeds"  "$rc"  "0"
printf '%-64s ' "and the decrypted token matches machine 1's, exactly"
[ "$(cat "$M2/.config/agentic-bioflow/.seqera_token" 2>/dev/null)" = "the-real-plaintext-token-99887766" ] \
  && echo ok || { echo "FAIL: token content did not round-trip"; fails=$((fails+1)); }
printf '%-64s ' "the decrypted token cache is mode 600"
m=$(stat -c %a "$M2/.config/agentic-bioflow/.seqera_token" 2>/dev/null)
[ "$m" = 600 ] && echo ok || { echo "FAIL: mode $m"; fails=$((fails+1)); }

# Decrypting again when a local token already exists is a no-op, not an
# overwrite - a member who has since rotated their own local copy must not
# have it silently replaced by whatever the portable folder still has.
out=$(m2 env AGENTIC_BIOFLOW_TOKEN_PASSPHRASE="correct horse battery staple" \
       bash "$P" decrypt-token 2>&1); rc=$?
t "decrypting again with a token already present is a no-op"  "$rc"  "0"
has "...says so"  "already exists" "$out"

echo

# ---------------------------------------------------------------------------
# init is idempotent and never re-encrypts an existing ciphertext - a machine
# re-running it should never be prompted for a passphrase it does not need.
out=$(m1 bash "$P" init "$PORTABLE" 2>&1); rc=$?
t "re-running init needs no passphrase at all"  "$rc"  "0"
has "...says the token file already exists"  "already exists" "$out"

# ---------------------------------------------------------------------------
# encrypt-token: no local token at all is refused cleanly, not a crash.
NOTOKHOME="$TMP/no_token_home"; mkdir -p "$NOTOKHOME/.config/agentic-bioflow"
printf 'seqera_user: bob\n' > "$NOTOKHOME/.config/agentic-bioflow/env.yaml"
chmod 600 "$NOTOKHOME/.config/agentic-bioflow/env.yaml"
NOTOK_PORTABLE="$TMP/no_token_portable"; mkdir -p "$NOTOK_PORTABLE/config"
out=$(clean HOME="$NOTOKHOME" XDG_CONFIG_HOME="$NOTOKHOME/.config" -- \
      bash "$P" encrypt-token "$NOTOK_PORTABLE" 2>&1); rc=$?
t "encrypt-token with no local token to encrypt is refused"  "$rc"  "1"
has "...says there is nothing to encrypt"  "no local token found" "$out"

echo

# ---------------------------------------------------------------------------
# --reconstruct: a dry-run fixture `tw` stands in for a real one (none
# installed, no network - the same PRINCIPLES.md invariant 8 this file's own
# header names). Proves --reconstruct prints CANDIDATES only, and writes
# nothing at all.
FIXTW="$TMP/fixture_bin"; mkdir -p "$FIXTW"
cat > "$FIXTW/tw" <<'EOF'
#!/bin/bash
case "$1" in
  info)
    cat <<'OUT'
Nextflow Tower CLI 0.9.4
    API endpoint      https://api.cloud.seqera.io
    Tower user name   dryrun_person
OUT
    exit 0 ;;
  workspaces)
    cat <<'OUT'
  Id      | Name         | Description
  --------|--------------|-------------
  555111  | reconlab-ws  | Recon Lab
OUT
    exit 0 ;;
  *) echo "unhandled tw subcommand: $*" >&2; exit 1 ;;
esac
EOF
chmod +x "$FIXTW/tw"

RECON_HOME="$TMP/recon_home"; mkdir -p "$RECON_HOME/.config/agentic-bioflow"
printf 'this-is-a-fixture-token\n' > "$RECON_HOME/.config/agentic-bioflow/.seqera_token"
chmod 600 "$RECON_HOME/.config/agentic-bioflow/.seqera_token"

recon_before_files=$(find "$RECON_HOME" -type f | sort)
out=$(clean HOME="$RECON_HOME" XDG_CONFIG_HOME="$RECON_HOME/.config" \
      PATH="$FIXTW:$PATH" -- bash "$S" --reconstruct 2>&1); rc=$?
t "--reconstruct exits clean against a dry-run tw fixture"  "$rc"  "0"
has "...surfaces a seqera_user candidate"    "candidate seqera_user: dryrun_person" "$out"
has "...surfaces a workspace_id candidate"   "candidate workspace_id: 555111 (reconlab-ws)" "$out"
has "...tells the user to confirm before saving anything" "CANDIDATE" "$out"
has "...points at settings.sh --set to actually save one" "settings.sh --set" "$out"
has "...names sacctmgr/sshare for slurm_account, never guesses it" "sacctmgr" "$out"
hasnot "...never claims to have set anything" "wrote " "$out"

recon_after_files=$(find "$RECON_HOME" -type f | sort)
t "--reconstruct wrote no new file at all"  "$recon_after_files"  "$recon_before_files"

# --- crypto temp files under a loose umask ------------------------------------
# A backend that writes `-out <path>` creates the file itself, with the
# caller's umask, when the path is missing. The helpers must never leave a
# plaintext token briefly world-readable, nor park it in the shared /tmp.
if command -v openssl >/dev/null 2>&1; then
    CRYPT=$(mktemp -d)
    printf 'secret-token-value' > "$CRYPT/plain"
    # Only the crypto helpers, not the whole script: sourcing it would run its
    # own dispatch and exit on usage. settings.sh supplies `clocked`.
    sed -n '/^try_age_encrypt()/,/^decrypt_token()/p' "$P" > "$CRYPT/funcs.sh"
    # A stand-in openssl that runs the real one, then records the mode and
    # directory of whatever it just wrote - the moment the old code leaked.
    REAL_OPENSSL="$(command -v openssl)"
    mkdir "$CRYPT/bin"
    cat > "$CRYPT/bin/openssl" <<WRAP
#!/bin/bash
"$REAL_OPENSSL" "\$@"; rc=\$?
prev=""; for a in "\$@"; do [ "\$prev" = "-out" ] && echo "\$(stat -c %a "\$a") \$(dirname "\$a")" >> "$CRYPT/written"; prev="\$a"; done
exit \$rc
WRAP
    chmod +x "$CRYPT/bin/openssl"
    ( umask 022
      PATH="$CRYPT/bin:$PATH"
      . "$(dirname "$P")/settings.sh"
      . "$CRYPT/funcs.sh"
      encrypt_token "$CRYPT/plain" "$CRYPT/ct" "pw" >/dev/null
      mkdir "$CRYPT/out"
      decrypt_token "$CRYPT/ct" "$CRYPT/out/plain" "pw" >/dev/null )
    t "decrypted token round-trips under umask 022"  "$(cat "$CRYPT/out/plain" 2>/dev/null)"  "secret-token-value"
    t "decrypted token is mode 600 under umask 022"  "$(stat -c %a "$CRYPT/out/plain" 2>/dev/null)"  "600"
    t "no temp file is left beside the decrypted token"  "$(ls -A "$CRYPT/out")"  "plain"
    t "openssl only ever wrote mode-600 files"  "$(cut -d' ' -f1 "$CRYPT/written" | sort -u)"  "600"
    t "openssl never wrote into the shared temp dir"  "$(grep -c " ${TMPDIR:-/tmp}\$" "$CRYPT/written")"  "0"
    rm -rf "$CRYPT"
fi

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
