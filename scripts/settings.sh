#!/bin/bash
# Read one value from the deployment's settings file.
#
# Everything that identifies a person or a site - the account compute time is
# billed to, the workspace, where the agent's Java lives - belongs in one file
# outside the repository, mode 600. Baking any of it into a script makes the
# script one person's (PRINCIPLES.md, invariant 3), and on a cluster where home
# directories are mode 700 it also makes it unreadable to everyone else.
#
#   setting <key>              value, or empty
#   setting <key> <default>    value, or the default
#   setting <key> --required   value, or exit 1 saying which key is missing
#
# Deliberately not a YAML parser: this reads `key: value` and stops at the first
# `#`, which is all the settings file is allowed to be. A settings file that
# needs a real parser has grown into something it should not be.
set -uo pipefail

SETTINGS_FILE="${LAB_SETTINGS_FILE:-${LAB_RUNS_DIR:-}/_personal/env.yaml}"

setting() {
    local key="$1" fallback="${2:-}" val=""
    if [ -r "$SETTINGS_FILE" ]; then
        val=$(sed -n "s/^[[:space:]]*${key}[[:space:]]*:[[:space:]]*//p" "$SETTINGS_FILE" \
              | sed 's/[[:space:]]*#.*$//; s/[[:space:]]*$//' | head -1)
    fi
    if [ -n "$val" ]; then printf '%s\n' "$val"; return 0; fi
    if [ "$fallback" = "--required" ]; then
        echo "missing '$key' in ${SETTINGS_FILE:-<no settings file>}." >&2
        echo "Ask the user for it - never guess it, and never copy it from another member." >&2
        return 1
    fi
    printf '%s\n' "$fallback"
}

# Write one value back. Onboarding discovers things - a free port, where the
# agent's Java ended up - and the member should not have to transcribe them.
# Rewrites the key in place if present so comments and order survive; appends
# otherwise. Creates the file mode 600, because everything in it is either
# personal or an access path.
set_setting() {
    local key="$1" val="$2"
    [ -n "${SETTINGS_FILE:-}" ] || { echo "no settings file location known" >&2; return 1; }
    mkdir -p "$(dirname "$SETTINGS_FILE")"
    [ -e "$SETTINGS_FILE" ] || { : > "$SETTINGS_FILE"; chmod 600 "$SETTINGS_FILE"; }
    python3 - "$SETTINGS_FILE" "$key" "$val" <<'PY'
import re, sys
path, key, val = sys.argv[1:4]
lines = open(path).read().splitlines(keepends=True)
pat = re.compile(rf"^(\s*){re.escape(key)}\s*:")
for i, line in enumerate(lines):
    if pat.match(line):
        # Keep any trailing comment: it usually says why the value matters.
        comment = ""
        body = line.split("#", 1)
        if len(body) == 2:
            comment = "  #" + body[1].rstrip("\n")
        lines[i] = f"{key}: {val}{comment}\n"
        break
else:
    if lines and not lines[-1].endswith("\n"):
        lines.append("\n")
    lines.append(f"{key}: {val}\n")
open(path, "w").writelines(lines)
PY
    chmod 600 "$SETTINGS_FILE"
}

# Allow `settings.sh <key> [default]` as well as sourcing it.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    setting "${1:?usage: settings.sh <key> [default|--required]}" "${2:-}"
fi
