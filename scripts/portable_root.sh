#!/bin/bash
# T23: build and maintain a portable folder (docs/SETTINGS.md) - the one
# place a person's settings and token can travel between machines without
# rerunning the whole of `setup`. This script builds the structure and moves
# things into it; `scripts/settings.sh --adopt <path>` is the separate,
# read-mostly step that points a (possibly different) machine AT one that
# already exists - see that script's own header for why the two are split.
#
# Nothing existing: no tool here builds a "settings that travel between this
# person's own machines" folder - env.yaml already had the right keys in it
# (docs/SETTINGS.md), they just never had anywhere designed to live once a
# person owns more than one machine.
#
#   portable_root.sh init <path>              build config/ and projects/,
#                                              migrate this machine's portable
#                                              keys into config/env.yaml,
#                                              encrypt the current token into
#                                              config/.seqera_token.enc. Safe
#                                              to re-run: never overwrites a
#                                              file that is already there -
#                                              same idempotency guarantee as
#                                              scripts/init_workspace.sh.
#   portable_root.sh encrypt-token <path>     (re)write config/.seqera_token.enc
#                                              from this machine's current
#                                              plaintext token. Separate from
#                                              `init` because a token can be
#                                              rotated long after the folder
#                                              was built.
#   portable_root.sh decrypt-token [<path>]   decrypt config/.seqera_token.enc
#                                              into this machine's own
#                                              ACL-protected cache - the same
#                                              path scripts/settings.sh's
#                                              token_file() already resolves
#                                              to (dirname(local settings
#                                              file)/.seqera_token), so
#                                              nothing else has to change to
#                                              start using it. <path>
#                                              defaults to the portable
#                                              folder this machine has
#                                              already adopted (the pointer
#                                              settings.sh --adopt wrote).
#
# The passphrase is never a CLI argument - visible to every other user's `ps`
# on a shared login node, which is exactly the class of exposure this
# project's safety net already refuses elsewhere (PRINCIPLES.md). Supply it
# as AGENTIC_BIOFLOW_TOKEN_PASSPHRASE for a scripted call: the user gives
# Claude the password in the conversation and Claude exports it for exactly
# this one call, the same "flows through the chat, written straight to a
# file, never echoed back" path the token itself already takes in
# commands/setup.md step 3. With no controlling terminal and no env var, this
# refuses rather than silently trying an empty passphrase.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

usage() {
    cat >&2 <<'U'
usage:
  portable_root.sh init <path>
  portable_root.sh encrypt-token <path>
  portable_root.sh decrypt-token [<path>]
U
    exit 2
}

# The portable keys, one place (docs/SETTINGS.md has the authoritative
# description; T27 formalises the full portable/machine-derived table there).
# Left OUT deliberately: site_bridge, ssh_control_path, tw_bin, local_root,
# agent_java, agent_jar, relay_port, singularity_cache - each one is either
# literally a path on THIS machine, or (agent_java/agent_jar) a path on the
# site that scripts/install_deps.sh re-derives on demand rather than a value
# worth carrying between machines.
PORTABLE_KEYS="reach seqera_user workspace_id compute_env slurm_account
site_host site_user storage_root email language record_adapter record_ref
agent_connection"

read_passphrase() {
    if [ -n "${AGENTIC_BIOFLOW_TOKEN_PASSPHRASE:-}" ]; then
        printf '%s' "$AGENTIC_BIOFLOW_TOKEN_PASSPHRASE"
        return 0
    fi
    if [ -r /dev/tty ]; then
        local p
        read -r -s -p "Passphrase for the portable token: " p < /dev/tty || return 1
        echo >/dev/tty 2>/dev/null || true
        printf '%s' "$p"
        return 0
    fi
    echo "no passphrase available: set AGENTIC_BIOFLOW_TOKEN_PASSPHRASE (the value" >&2
    echo "the user gave you), or run this at a real terminal so it can be typed." >&2
    return 1
}

# --- age -----------------------------------------------------------------
# age's own -p/--passphrase prompt opens /dev/tty directly rather than
# reading stdin - deliberate on age's part, so stdin stays free to carry the
# file being encrypted. This could not be measured against a real age binary
# (none installed on this machine, no network to fetch one - PRINCIPLES.md
# invariant 8: measure or read the source before claiming), so rather than
# assume a specific behaviour, the passphrase this already acquired
# (read_passphrase, above) is piped to it anyway and clocked - if age reads
# it, this works; if age instead tries /dev/tty and there is none (the
# ordinary case for a script Claude runs), age fails fast and this falls
# back to openssl below rather than hanging.
try_age_encrypt() {   # try_age_encrypt <plaintext> <ciphertext> <passphrase>
    command -v age >/dev/null 2>&1 || return 1
    printf '%s' "$3" | clocked 5 age --passphrase --armor -o "$2" "$1" >/dev/null 2>&1
}
try_age_decrypt() {   # try_age_decrypt <ciphertext> <plaintext-out> <passphrase>
    command -v age >/dev/null 2>&1 || return 1
    printf '%s' "$3" | clocked 5 age --decrypt "$1" >"$2" 2>/dev/null
}

# --- openssl ---------------------------------------------------------------
# The reliably scriptable backend: -pass env:VAR reads the passphrase from
# this process's own environment, never argv (so it never shows up in `ps`),
# and needs no controlling terminal at all. PBKDF2 + a random salt, which
# openssl 1.1.1+/3.x default to needing explicitly (older openssl defaulted
# to a weaker KDF, so this is asked for by name rather than trusting whatever
# a given build's default happens to be).
try_openssl_encrypt() {   # try_openssl_encrypt <plaintext> <ciphertext> <passphrase>
    command -v openssl >/dev/null 2>&1 || return 1
    AGENTIC_BIOFLOW_TOKEN_PASSPHRASE="$3" clocked 10 openssl enc -aes-256-cbc -pbkdf2 -salt \
        -pass env:AGENTIC_BIOFLOW_TOKEN_PASSPHRASE -in "$1" -out "$2" 2>/dev/null
}
try_openssl_decrypt() {   # try_openssl_decrypt <ciphertext> <plaintext-out> <passphrase>
    command -v openssl >/dev/null 2>&1 || return 1
    AGENTIC_BIOFLOW_TOKEN_PASSPHRASE="$3" clocked 10 openssl enc -d -aes-256-cbc -pbkdf2 -salt \
        -pass env:AGENTIC_BIOFLOW_TOKEN_PASSPHRASE -in "$1" -out "$2" 2>/dev/null
}

# encrypt_token/decrypt_token print which backend actually worked, on stdout,
# and nothing else - callers echo that into their own message. A temp file
# means a failed attempt never leaves a half-written ciphertext or plaintext
# where the real path is expected.
encrypt_token() {   # encrypt_token <plaintext-path> <ciphertext-path> <passphrase>
    local pt="$1" ct="$2" pass="$3" tmp
    tmp="$(mktemp)" || return 1
    if try_age_encrypt "$pt" "$tmp" "$pass" && [ -s "$tmp" ]; then
        mv "$tmp" "$ct"; chmod 600 "$ct"; echo age; return 0
    fi
    rm -f "$tmp"
    if try_openssl_encrypt "$pt" "$tmp" "$pass" && [ -s "$tmp" ]; then
        mv "$tmp" "$ct"; chmod 600 "$ct"; echo openssl; return 0
    fi
    rm -f "$tmp"
    return 1
}
decrypt_token() {   # decrypt_token <ciphertext-path> <plaintext-out-path> <passphrase>
    local ct="$1" pt="$2" pass="$3" tmp
    tmp="$(mktemp)" || return 1
    if try_age_decrypt "$ct" "$tmp" "$pass" && [ -s "$tmp" ]; then
        mv "$tmp" "$pt"; chmod 600 "$pt"; echo age; return 0
    fi
    rm -f "$tmp"
    if try_openssl_decrypt "$ct" "$tmp" "$pass" && [ -s "$tmp" ]; then
        mv "$tmp" "$pt"; chmod 600 "$pt"; echo openssl; return 0
    fi
    rm -f "$tmp"
    return 1
}

require_absolute() {
    case "$1" in
        /*) ;;
        *) echo "the portable folder location must be an absolute path, not '$1'." >&2; exit 2 ;;
    esac
}

cmd_init() {
    local path="${1:?usage: portable_root.sh init <path>}"
    require_absolute "$path"
    path="${path%/}"
    mkdir -p "$path/config" "$path/projects" || { echo "could not create $path" >&2; return 1; }

    # Migrate the portable keys from THIS machine's current settings - never
    # guessed, never invented: each value is read with the ordinary `setting`
    # lookup (on a machine that has not adopted anything yet, that is simply
    # the pre-existing local file), and only a key that actually has a value
    # is written.
    if [ -e "$path/config/env.yaml" ]; then
        echo "note: $path/config/env.yaml already exists - leaving it as is." >&2
        echo "      (idempotent by design; edit it directly to change a portable" >&2
        echo "      value, or remove it first to re-migrate from scratch)" >&2
    else
        local tmp key val wrote=0
        tmp="$(mktemp)" || return 1
        for key in $PORTABLE_KEYS; do
            val="$(setting "$key")"
            [ -n "$val" ] || continue
            printf '%s: %s\n' "$key" "$val" >> "$tmp"
            wrote=$((wrote + 1))
        done
        mv "$tmp" "$path/config/env.yaml"
        chmod 600 "$path/config/env.yaml"
        echo "wrote $path/config/env.yaml ($wrote key(s))"
    fi

    if [ -e "$path/config/.seqera_token.enc" ]; then
        echo "note: $path/config/.seqera_token.enc already exists - leaving it as is." >&2
        return 0
    fi
    local tok; tok="$(token_file)"
    if [ ! -r "$tok" ]; then
        echo "no local token found at $tok - nothing to encrypt yet. Run this again" >&2
        echo "once the token exists (docs/SETTINGS.md, setup step 3)." >&2
        return 0
    fi
    if ! command -v age >/dev/null 2>&1 && ! command -v openssl >/dev/null 2>&1; then
        echo "neither age nor openssl is on PATH - the token cannot be encrypted." >&2
        echo "The portable folder was built WITHOUT a token; the settings keys above" >&2
        echo "still work on their own. The next machine that adopts this folder will" >&2
        echo "need to get a token some other way (docs/SETTINGS.md, setup step 3)." >&2
        return 0
    fi
    local pass backend
    pass="$(read_passphrase)" || return 1
    backend="$(encrypt_token "$tok" "$path/config/.seqera_token.enc" "$pass")" \
        && echo "encrypted the token into $path/config/.seqera_token.enc (via $backend)" \
        || { echo "failed to encrypt the token - nothing was written." >&2; return 1; }
}

cmd_encrypt_token() {
    local path="${1:?usage: portable_root.sh encrypt-token <path>}"
    require_absolute "$path"
    path="${path%/}"
    [ -d "$path/config" ] || { echo "$path/config does not exist - run 'init' first." >&2; return 2; }
    local tok; tok="$(token_file)"
    [ -r "$tok" ] || { echo "no local token found at $tok" >&2; return 1; }
    if ! command -v age >/dev/null 2>&1 && ! command -v openssl >/dev/null 2>&1; then
        echo "neither age nor openssl is on PATH - cannot encrypt." >&2
        return 1
    fi
    local pass backend
    pass="$(read_passphrase)" || return 1
    backend="$(encrypt_token "$tok" "$path/config/.seqera_token.enc" "$pass")" \
        && echo "encrypted the token into $path/config/.seqera_token.enc (via $backend)" \
        || { echo "failed to encrypt the token - nothing was written." >&2; return 1; }
}

cmd_decrypt_token() {
    local path="${1:-$PORTABLE_ROOT}"
    if [ -z "$path" ]; then
        echo "no portable folder given, and none adopted (scripts/settings.sh --adopt)" >&2
        echo "- nothing to decrypt from." >&2
        return 2
    fi
    path="${path%/}"
    local ct="$path/config/.seqera_token.enc"
    [ -r "$ct" ] || { echo "$ct does not exist or is not readable." >&2; return 1; }
    local dest; dest="$(token_file)"
    if [ -r "$dest" ]; then
        echo "a local token already exists at $dest - leaving it as is." >&2
        echo "remove it first if you want to re-decrypt (e.g. after a password change)." >&2
        return 0
    fi
    mkdir -p "$(dirname "$dest")" || { echo "could not create $(dirname "$dest")" >&2; return 1; }
    local pass backend
    pass="$(read_passphrase)" || return 1
    backend="$(decrypt_token "$ct" "$dest" "$pass")" \
        && echo "decrypted the token to $dest (via $backend), mode 600" \
        || { echo "could not decrypt - wrong passphrase, or the wrong tool for how it" >&2
             echo "was encrypted (age vs openssl)?" >&2; return 1; }
}

case "${1:-}" in
    init)          shift; cmd_init "$@" ;;
    encrypt-token) shift; cmd_encrypt_token "$@" ;;
    decrypt-token) shift; cmd_decrypt_token "$@" ;;
    *) usage ;;
esac
