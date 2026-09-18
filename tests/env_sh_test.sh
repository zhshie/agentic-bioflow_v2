#!/bin/bash
# Tests for scripts/env.sh: one `source` sets PATH and TOWER_ACCESS_TOKEN from
# a deployment's settings, so a command file's "Before anything" section does
# not spend a separate round trip deriving either one.
#
# Every case runs env.sh in a fresh `bash -c` subshell rather than sourcing it
# into this test's own shell - PATH and TOWER_ACCESS_TOKEN must not leak
# between cases, and a subshell is the cheap way to guarantee that. Each case
# also gets its OWN settings directory (mktemp -d under $TMP) rather than
# reusing one - token_file() walks up from wherever the settings file lives,
# so a `.seqera_token` left over from an earlier case would be found again
# here and a case meant to prove "no token" would pass by accident.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/env.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
ok() { printf '%-64s ok\n' "$1"; }
no() { printf '%-64s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

# case_dir <name> -> a fresh, empty directory under $TMP, and its settings path
case_dir() { local d="$TMP/$1"; mkdir -p "$d"; printf '%s\n' "$d"; }
settings_in() { local d="$1"; shift; printf '%s\n' "$@" > "$d/env.yaml"; }

# run_env <extra-env-assignments...> -- prints PATH<US>TOKEN<US>rc, US being
# 0x1f (ASCII unit separator). Not a tab: bash's word-splitting treats
# consecutive IFS-*whitespace* characters (space/tab/newline) as ONE
# delimiter and trims them at the ends, so an empty TOKEN field between two
# tabs silently vanishes on the `read` below instead of coming back as "" -
# reproduced in isolation while writing this file. 0x1f is not IFS
# whitespace, so `read` keeps the empty field, and it will never occur inside
# a real PATH or token either.
run_env() {
    env "$@" bash -c '. "'"$S"'" >/dev/null 2>&1
                       printf "%s\x1f%s\x1f%s\n" "$PATH" "${TOWER_ACCESS_TOKEN:-}" "$?"'
}

FAKE_TW_DIR="$TMP/bin"; mkdir -p "$FAKE_TW_DIR"
printf '#!/bin/bash\necho fake-tw\n' > "$FAKE_TW_DIR/tw"; chmod +x "$FAKE_TW_DIR/tw"

# --- both variables set correctly -------------------------------------------
D=$(case_dir both)
settings_in "$D" "tw_bin: $FAKE_TW_DIR/tw"
printf 'tok-abc-123' > "$D/.seqera_token"; chmod 600 "$D/.seqera_token"

out=$(run_env LAB_SETTINGS_FILE="$D/env.yaml")
IFS=$'\x1f' read -r path tok rc <<<"$out"
case ":$path:" in
    *":$FAKE_TW_DIR:"*) ok "PATH gains tw_bin's own directory" ;;
    *) no "PATH gains tw_bin's own directory" "PATH was: $path" ;;
esac
[ "$tok" = "tok-abc-123" ] \
    && ok "TOWER_ACCESS_TOKEN is read from the token file beside settings" \
    || no "TOWER_ACCESS_TOKEN is read from the token file beside settings" "got '$tok'"
[ "$rc" = 0 ] && ok "sourcing it leaves the shell's exit status untouched" \
              || no "sourcing it leaves the shell's exit status untouched" "rc=$rc"

# --- sourcing twice does not grow PATH -------------------------------------
out=$(env LAB_SETTINGS_FILE="$D/env.yaml" bash -c \
      '. "'"$S"'" >/dev/null 2>&1; . "'"$S"'" >/dev/null 2>&1; echo "$PATH"')
n=$(tr ':' '\n' <<<"$out" | grep -cFx "$FAKE_TW_DIR")
[ "$n" = 1 ] && ok "sourcing it twice adds tw's directory only once" \
             || no "sourcing it twice adds tw's directory only once" "appeared $n times"

# --- no settings file at all: degrades quietly, never fatal ----------------
D=$(case_dir nosettings)
out=$(run_env LAB_SETTINGS_FILE="$D/does-not-exist.yaml")
IFS=$'\x1f' read -r path tok rc <<<"$out"
[ -z "$tok" ] && ok "no settings file: no token is exported" \
              || no "no settings file: no token is exported" "got '$tok'"
case ":$path:" in
    *"::"*|"") no "no settings file: PATH is left alone rather than corrupted" "PATH was: '$path'" ;;
    *) ok "no settings file: PATH is left alone rather than corrupted" ;;
esac
[ "$rc" = 0 ] && ok "no settings file: sourcing it does not fail" \
              || no "no settings file: sourcing it does not fail" "rc=$rc"

# --- settings file exists but names no tw_bin -------------------------------
D=$(case_dir notwbin)
settings_in "$D" 'workspace_id: 1'
out=$(run_env LAB_SETTINGS_FILE="$D/env.yaml")
IFS=$'\x1f' read -r path tok rc <<<"$out"
case ":$path:" in
    *":$FAKE_TW_DIR:"*) no "no tw_bin recorded: PATH does not gain a stale directory" "PATH was: $path" ;;
    *) ok "no tw_bin recorded: PATH does not gain a stale directory" ;;
esac

# --- settings file present, token file missing ------------------------------
D=$(case_dir notoken)
settings_in "$D" "tw_bin: $FAKE_TW_DIR/tw"
out=$(run_env LAB_SETTINGS_FILE="$D/env.yaml")
IFS=$'\x1f' read -r path tok rc <<<"$out"
[ -z "$tok" ] && ok "settings present but no token file: nothing is exported" \
              || no "settings present but no token file: nothing is exported" "got '$tok'"
[ "$rc" = 0 ] && ok "a missing token file does not make sourcing it fail" \
              || no "a missing token file does not make sourcing it fail" "rc=$rc"

# --- settings broken: token file unreadable (mode 000) ----------------------
D=$(case_dir unreadable)
settings_in "$D" "tw_bin: $FAKE_TW_DIR/tw"
printf 'tok-should-not-be-read' > "$D/.seqera_token"; chmod 000 "$D/.seqera_token"
if [ "$(id -u)" != 0 ]; then
    out=$(run_env LAB_SETTINGS_FILE="$D/env.yaml")
    IFS=$'\x1f' read -r path tok rc <<<"$out"
    [ -z "$tok" ] && ok "an unreadable token file: nothing is exported, no crash" \
                  || no "an unreadable token file: nothing is exported, no crash" "got '$tok'"
    [ "$rc" = 0 ] && ok "an unreadable token file does not fail the source" \
                  || no "an unreadable token file does not fail the source" "rc=$rc"
else
    echo "an unreadable token file: nothing is exported, no crash    skip (running as root)"
    echo "an unreadable token file does not fail the source           skip (running as root)"
fi
chmod 600 "$D/.seqera_token"

# --- an already-exported token wins over the file ---------------------------
D=$(case_dir alreadyset)
settings_in "$D" "tw_bin: $FAKE_TW_DIR/tw"
printf 'from-the-file' > "$D/.seqera_token"; chmod 600 "$D/.seqera_token"
out=$(run_env LAB_SETTINGS_FILE="$D/env.yaml" TOWER_ACCESS_TOKEN=already-set)
IFS=$'\x1f' read -r path tok rc <<<"$out"
[ "$tok" = "already-set" ] \
    && ok "an already-exported TOWER_ACCESS_TOKEN is never overwritten" \
    || no "an already-exported TOWER_ACCESS_TOKEN is never overwritten" "got '$tok'"

# --- settings file is outright garbage (not key:value at all) --------------
D=$(case_dir garbage)
printf 'this is not yaml at all {{{\nsome junk with no colon at all' > "$D/env.yaml"
out=$(run_env LAB_SETTINGS_FILE="$D/env.yaml")
IFS=$'\x1f' read -r path tok rc <<<"$out"
[ "$rc" = 0 ] && ok "a garbage settings file still leaves sourcing it harmless" \
              || no "a garbage settings file still leaves sourcing it harmless" "rc=$rc"

echo
[ "$fails" = 0 ] && echo "OK: scripts/env.sh" || { echo "$fails failed"; exit 1; }
