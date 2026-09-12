#!/bin/bash
# D1: inventory both machines, so :setup can tell "brand new site" from
# "someone already set this up" with evidence instead of a guess.
#
# Must be called AFTER reach is known (docs/SITE_ADAPTER.md, contract 6):
# under `local` the site is this machine; under `ssh` the site side goes
# through scripts/on_site.sh, the only sanctioned way to run something there;
# under `none` there is no login node, so the site keys are `unknown` and this
# says why (setup.md used to probe with on_site.sh before reach was even
# asked, which is how a brand-new-site check ended up answering for the
# user's own laptop instead - see the plan this ticket implements).
#
#   inspect_sides.sh              print both sides, one key=value per line
#   inspect_sides.sh --site-probe internal: run ON the site, print only the
#                                  site.* keys. Never called directly by a
#                                  person - scripts/on_site.sh --script ships
#                                  this same file and invokes it this way, so
#                                  every site-side check travels in the ONE
#                                  round trip that costs 31s without a shared
#                                  ssh master (docs/SITE_ADAPTER.md).
#
# Output: `key=value`, one per line, values `yes|no|unknown` or a number.
# Never the token's value - `site.token=yes`/`local.token=yes` mean only that
# the file exists.
#
#   ON_SITE_DRY_RUN=1   forwarded to on_site.sh: no ssh, no network, no site -
#                       see tests/on_site_test.sh for the seam this rides on.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

# Shared by both the probe and the local checks below: on whichever machine
# this runs, is there a `tw` this deployment would actually use? `tw_bin` is
# deliberately not carried across on_site.sh (see its own comment) so a site
# probe reads whatever ITS OWN settings say, falling back to PATH exactly the
# way every other site script already does.
has_tw() {
    local t; t="$(setting tw_bin)"
    if [ -n "$t" ]; then command -v "$t" >/dev/null 2>&1; return $?; fi
    command -v tw >/dev/null 2>&1
}

# --- site-probe mode: runs ON the site (local machine directly under
# reach:local, or shipped over by on_site.sh --script under reach:ssh) -------
if [ "${1:-}" = --site-probe ]; then
    BASE="${LAB_RUNS_DIR:-$(setting storage_root)}"

    if [ "$SETTINGS_FOUND" = 1 ]; then echo "site.settings=yes"; else echo "site.settings=no"; fi

    TOKEN="$(token_file)"
    if [ -r "$TOKEN" ]; then echo "site.token=yes"; else echo "site.token=no"; fi

    if [ -n "$BASE" ] && [ -d "$BASE/_personal" ] && [ -d "$BASE/_system" ]; then
        echo "site.skeleton=yes"
    else
        echo "site.skeleton=no"
    fi

    if has_tw; then echo "site.tw=yes"; else echo "site.tw=no"; fi

    JAVA="${TW_AGENT_JAVA:-$(setting agent_java)}"
    if [ -n "$JAVA" ] && { [ -x "$JAVA" ] || command -v "$JAVA" >/dev/null 2>&1; }; then
        echo "site.java=yes"
    else
        echo "site.java=no"
    fi

    JAR="${TW_AGENT_JAR:-$(setting agent_jar)}"
    if [ -n "$JAR" ] && [ -r "$JAR" ]; then echo "site.jar=yes"; else echo "site.jar=no"; fi

    # Existing run areas: BASE/<user>/projects/<project>/runs/<run> - five
    # levels below BASE. Counted, not listed: this is evidence for a yes/no
    # decision ("has anyone used this site"), not a directory dump.
    if [ -n "$BASE" ] && [ -d "$BASE" ]; then
        n=$(find "$BASE" -mindepth 5 -maxdepth 5 -type d -path '*/projects/*/runs/*' 2>/dev/null | wc -l)
        echo "site.runs=${n// /}"
    else
        echo "site.runs=0"
    fi
    exit 0
fi

# --- top-level: one call for the site side, direct checks for the local one -
REACH="$(setting reach local)"
echo "reach=$REACH"

# Printed on stdout only ever as `key=value` - status.sh and :setup parse
# this. Anything explanatory goes to stderr instead.
emit_site_unknown() {
    local k
    for k in site.settings site.token site.skeleton site.tw site.java site.jar site.runs; do
        echo "$k=unknown"
    done
}

# Pull one key out of the probe's blob, defaulting to unknown rather than
# empty - a key ON_SITE_DRY_RUN's own passthrough line never produced is a
# gap in what was learned, not a "no".
site_kv() {
    local key="$1" blob="$2" v
    v=$(printf '%s\n' "$blob" | sed -n "s/^${key}=//p" | head -1)
    [ -n "$v" ] && printf '%s\n' "$v" || printf 'unknown\n'
}

case "$REACH" in
    none)
        echo "site.reachable=unknown"
        emit_site_unknown
        echo "reach is 'none': a Platform-managed compute environment has no login node," >&2
        echo "so there is nothing on the site side to inspect." >&2
        ;;
    local|ssh)
        # ONE on_site.sh call, whatever REACH is - preflight.sh already does
        # this unconditionally for the same reason: reach:local execs this
        # script directly with no ssh at all, so it costs nothing extra and
        # there is only one code path to keep honouring the contract.
        if OUT=$(bash "$HERE/on_site.sh" --script "$HERE/inspect_sides.sh" --site-probe 2>&1); then
            echo "site.reachable=yes"
            for k in site.settings site.token site.skeleton site.tw site.java site.jar site.runs; do
                echo "$k=$(site_kv "$k" "$OUT")"
            done
        else
            echo "site.reachable=no"
            emit_site_unknown
            printf '%s\n' "$OUT" >&2
        fi
        ;;
    *)
        echo "site.reachable=unknown"
        emit_site_unknown
        echo "unknown reach value '$REACH' - must be none, local or ssh (docs/SITE_ADAPTER.md)." >&2
        ;;
esac

# --- local side: always this machine, checked directly, no round trip -------
if [ "$SETTINGS_FOUND" = 1 ]; then echo "local.settings=yes"; else echo "local.settings=no"; fi

LOCAL_TOKEN="$(token_file)"
if [ -r "$LOCAL_TOKEN" ]; then echo "local.token=yes"; else echo "local.token=no"; fi

# No settings key names this - docs/SETTINGS.md documents the default plainly
# (init_workspace.sh's own `--root`, same default) and nothing here invents a
# second one. $HOME is overridable in tests the same way every other
# settings-file test already overrides it.
LOCAL_ROOT="${HOME:-}/agentic-bioflow"
if [ -d "$LOCAL_ROOT" ]; then echo "local.skeleton=yes"; else echo "local.skeleton=no"; fi

if has_tw; then echo "local.tw=yes"; else echo "local.tw=no"; fi
