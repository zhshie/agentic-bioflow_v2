#!/bin/bash
# Read one value from the deployment's settings file.
#
# Not a YAML parser (PyYAML, yq): deliberately reads `key: value` and stops at
# the first `#` - see the note further down about what that rules out.
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
#   settings.sh --summary      what this deployment is configured as and where
#                              that lives. Never the token's value.
#
# Deliberately not a YAML parser: this reads `key: value` and stops at the first
# `#`, which is all the settings file is allowed to be. A settings file that
# needs a real parser has grown into something it should not be.
set -uo pipefail

# How this machine differs from the one these scripts were written on, decided
# in one place (scripts/utils/portable.sh). Sourced here rather than in each
# caller because nearly everything already sources this file.
#
# Fail-closed, and loudly: without it `stat_mode` is simply undefined, so the
# token's permission check would evaluate to nothing and report a
# world-readable token as fine. A missing guard has to be an error, not a
# quieter version of the same output.
_PORTABLE="$(dirname "${BASH_SOURCE[0]}")/utils/portable.sh"
if [ -r "$_PORTABLE" ]; then
    . "$_PORTABLE"
else
    echo "missing $_PORTABLE - this deployment is incomplete." >&2
    return 1 2>/dev/null || exit 1
fi

# --- Where everything is: one root ------------------------------------------
# T30. There used to be seven places a deployment's own files could be, and
# the reason was accretion rather than design: `$LAB_RUNS_DIR/_personal` came
# first (when the only deployment ran ON the site), the XDG location was added
# for `reach: ssh`, and the portable folder was added on top of both as a
# fourth rather than replacing either. A person who wanted to know where their
# own settings were had to be told which of the three applied to them, and the
# honest answer depended on which shell they asked from.
#
# There is now ONE, and the user names it:
#
#   <root>/config/env.yaml                  the settings
#   <root>/config/.seqera_token             the token, mode 600
#   <root>/config/machines/<machine>.yaml   the few keys that cannot travel
#   <root>/projects/<project>/...           analysis, results, staging
#
# The root is meant to travel - a synced folder, an external drive, anywhere
# that follows the person between machines - so nothing written into
# config/env.yaml may be a path only one machine can resolve. That is what
# machines/ is for, and every key in it is discovered automatically; nobody is
# ever asked for one.
#
# One breadcrumb cannot be avoided: a machine has to learn where the root is
# before it can read anything in it. ROOT_POINTER is that, one line, written
# by `settings.sh --use <path>`, and never something the user has to know
# about. A FILE rather than an environment variable on purpose - every way the
# settings file has gone missing between sessions (PITFALLS 16j, 16k, 25) was
# caused by a variable set in one shell's startup file and not another's, and
# $HOME is the one thing every shell on every platform agrees about.
#
# LAB_SETTINGS_FILE still wins outright when set: it names exactly one file,
# which is what this repo's own test fixtures point at, and a value that could
# quietly resolve elsewhere would let `setting` read one file while
# `set_setting` writes another.
ROOT_POINTER="${XDG_CONFIG_HOME:-${HOME:-}/.config}/agentic-bioflow/root"

# This machine's identity, for the machines/ file. Hostname alone is not
# enough: Git Bash and WSL on ONE Windows box are two environments with
# separate homes, separate PATHs and a different `tw` (PITFALLS 25), and they
# report the same hostname. `uname -s` is what tells them apart (MSYS_NT...
# vs Linux). Sanitised because this becomes a filename inside a folder that
# may sync to Windows.
machine_id() {
    # No trailing newline into `tr`: -c would translate it too, leaving every
    # machine id with a stray underscore on the end.
    printf '%s-%s' "$(uname -n 2>/dev/null || echo unknown)" \
                   "$(uname -s 2>/dev/null || echo unknown)" \
        | tr -c 'A-Za-z0-9._-' '_'
    printf '\n'
}

ABF_ROOT=""
SETTINGS_FILE=""
MACHINE_SETTINGS_FILE=""
SETTINGS_FOUND=0

if [ -n "${LAB_SETTINGS_FILE:-}" ]; then
    SETTINGS_FILE="$LAB_SETTINGS_FILE"
    MACHINE_SETTINGS_FILE="$(dirname "$LAB_SETTINGS_FILE")/machines/$(machine_id).yaml"
    # Only call it a root when the path actually has a root's shape. An
    # explicit settings file may be anywhere - a test fixture, a one-off - and
    # inferring a root two directories up from an arbitrary path would invent
    # a projects area nobody asked for, in somebody's $TMP or $HOME.
    case "$(dirname "$LAB_SETTINGS_FILE")" in
        */config) ABF_ROOT="$(dirname "$(dirname "$LAB_SETTINGS_FILE")")" ;;
    esac
    [ -r "$SETTINGS_FILE" ] && SETTINGS_FOUND=1
elif [ -r "$ROOT_POINTER" ]; then
    ABF_ROOT="$(head -1 "$ROOT_POINTER" 2>/dev/null | tr -d '\r\n')"
    ABF_ROOT="${ABF_ROOT%/}"
    if [ -n "$ABF_ROOT" ]; then
        SETTINGS_FILE="$ABF_ROOT/config/env.yaml"
        MACHINE_SETTINGS_FILE="$ABF_ROOT/config/machines/$(machine_id).yaml"
        [ -r "$SETTINGS_FILE" ] && SETTINGS_FOUND=1
    fi
fi

# Where a pre-T30 deployment kept its settings. Deliberately NOT searched -
# T30 cut over rather than carrying two layouts indefinitely (docs/SETTINGS.md,
# "Migration") - but looked at whenever something is missing, so that a person
# who already ran setup is told `--migrate` rather than "run setup again".
legacy_settings_found() {
    local p
    for p in ${LAB_RUNS_DIR:+"${LAB_RUNS_DIR%/}/_personal/env.yaml"} \
             "$(xdg_default)"; do
        if [ -r "$p" ]; then printf '%s\n' "$p"; return 0; fi
    done
    return 1
}

# Why the root cannot be read right now. A root that has been named but is not
# here yet (a synced folder still catching up) is a different failure from one
# never named, and the two must not read alike - the first is "wait", the
# second is "run setup".
root_missing_reason() {
    [ -n "$ABF_ROOT" ] || return 1
    [ "$SETTINGS_FOUND" = 1 ] && return 1
    echo "This machine points at:  $ABF_ROOT" >&2
    echo "  (named in $ROOT_POINTER)" >&2
    if [ ! -e "$ABF_ROOT" ]; then
        echo "  which is not here yet. A common cause: a synced folder that has not" >&2
        echo "  finished syncing to this machine - wait for it, or check the sync" >&2
        echo "  client. Nothing is wrong with the deployment itself." >&2
    else
        echo "  but $SETTINGS_FILE is missing or unreadable." >&2
    fi
    return 0
}

# What the search covered. An error that names one unreadable path tells the
# reader nothing about where to put a file instead - which is the whole
# difference between "not set up" and "set up somewhere I did not look".
settings_missing() {
    echo "No settings file."
    if [ -n "${LAB_SETTINGS_FILE:-}" ]; then
        printf '  LAB_SETTINGS_FILE names %s, so nowhere else was searched.\n' "$LAB_SETTINGS_FILE"
    elif [ -n "$ABF_ROOT" ]; then
        printf '  This machine reads %s\n' "$SETTINGS_FILE"
        echo "  and that file is missing or unreadable."
    else
        echo "  This machine has not been pointed at a root yet -"
        printf '  %s does not exist.\n' "$ROOT_POINTER"
    fi
    # The single most useful thing this message can do is tell somebody who
    # HAS already been through setup that they are one command away, rather
    # than sending them through all ten steps a second time.
    local old
    if old="$(legacy_settings_found)"; then
        echo
        echo "There is a pre-T30 settings file on this machine:"
        printf '  %s\n' "$old"
        echo "That layout is no longer read. Move it into a root of your choosing, once:"
        echo "  scripts/settings.sh --migrate <root>"
        echo "Nothing in it has to be answered again."
        return 0
    fi
    steered_past_a_real_file
    shell_blind_spot
    echo "Run setup to create one. It asks where the root should be; anywhere that"
    echo "follows you between machines is a good answer. There is deliberately no"
    echo "default, because every default worth typing is a path that cannot travel."
    return 0
}

# The conventional place, worked out the same way the candidate list does it.
# The pre-T30 conventional location. Kept because legacy_settings_found()
# still has to look at it to offer `--migrate`, not because anything writes
# there any more.
xdg_default() {
    printf '%s\n' "${XDG_CONFIG_HOME:-${HOME:-}/.config}/agentic-bioflow/env.yaml"
}

# A root worth suggesting when the one in use cannot hold mode 600. Only ever
# printed as advice inside an error - never a fallback anything reads, which
# is the distinction T30 turns on: a default root is a path that cannot
# travel, chosen for somebody who was never asked.
example_root() {
    printf '%s\n' "${HOME:-~}/agentic-bioflow"
}

# A variable can steer the search away from a file that is sitting right there.
# LAB_SETTINGS_FILE wins outright and searches nowhere else, so a member who
# set it once - to a path that has since moved, or that only exists in another
# shell's home - gets a report listing one absent path while their real
# settings file is untouched at the default. That reads exactly like "never set
# up", and it is the one form of this failure a person can fix in one command.
steered_past_a_real_file() {
    # T30: the file that gets steered past is the root's own env.yaml, named
    # by the pointer. The failure is unchanged - LAB_SETTINGS_FILE wins
    # outright, so one stale export hides a perfectly good deployment - but
    # there is one place to check now instead of three, so the condition can
    # be stated directly rather than inferred from "the search got here".
    [ -n "${LAB_SETTINGS_FILE:-}" ] || return 0
    [ -r "$ROOT_POINTER" ] || return 0
    local r; r="$(head -1 "$ROOT_POINTER" 2>/dev/null | tr -d '\r\n')"
    [ -n "$r" ] || return 0
    [ -r "${r%/}/config/env.yaml" ] || return 0
    echo "  BUT a settings file exists at ${r%/}/config/env.yaml"
    echo "  and the search never reached it. Unset LAB_SETTINGS_FILE to use it."
}

# Windows puts two homes on one machine and only one of them is the one setup
# used. Git Bash's $HOME is the Windows profile; a deployment set up in WSL -
# which commands/setup.md requires, because PITFALLS 16b measured that only WSL
# can hold the site connection - sits in a filesystem this shell cannot reach,
# and WSL's ~/.bashrc, where LAB_SETTINGS_FILE is exported, is never read here.
# So the candidate list above is a true answer to the wrong question: every path
# in it is genuinely absent, and the file is genuinely there. Without this note
# "no settings file" is indistinguishable from "never set up", which is exactly
# the confusion the third candidate was added to end - one machine over.
#
# The right move is named here too, because the obvious one is wrong: copying
# the settings file somewhere Git Bash can see it makes --summary green in a
# shell this version still refuses to drive the site from (on_site.sh), and
# where chmod 600 on the Windows filesystem does not hold - trading a loud
# failure for a quiet one and dropping the token's only protection on the way.
#
# uname, not $OSTYPE: bash sets OSTYPE itself at startup, so it cannot be
# substituted from the environment and the branch would be untestable.
shell_blind_spot() {
    case "$(uname -s 2>/dev/null)" in
        MINGW*|MSYS*|CYGWIN*) ;;
        *) return 0 ;;
    esac
    echo "  This shell is Git Bash/MSYS, where HOME is ${HOME:-unset}."
    echo "  A deployment set up in WSL is not visible from here: different home,"
    echo "  different filesystem, and WSL's ~/.bashrc is never read in this shell."
    echo "  'Not found' here does not mean 'not set up'."
    echo "  None of that asks you to move: the project folder you already work"
    echo "  in does not have to move, and neither does this window. The one call"
    echo "  that needs WSL borrows it by itself (PITFALLS 16b, 16g)."
    echo "  Run setup here. It writes a settings file this shell can find, and"
    echo "  refuses outright if the file would not be private to you - settings.sh"
    echo "  reads that back rather than trusting that chmod did anything."
    echo "  The mode this shell prints for a Windows file is manufactured and is"
    echo "  not consulted (PITFALLS 16j): Windows itself is asked who can open the"
    echo "  file, and a refusal here means it named more people than you."
    echo "  A deployment already set up inside WSL stays exactly where it is;"
    echo "  this shell simply cannot read it."
}

# The token file, worked out in one place. preflight.sh, the session hook,
# agent_ctl.sh and ce_apply.sh each used to derive this for themselves, and two
# of them anchored it on the settings file while two anchored it on
# $LAB_RUNS_DIR. With a third place for the settings file to live, those two
# answers start differing for real.
#
# The settings file's directory is the anchor: docs/SETTINGS.md says the pair
# travel together. The other candidate directories are tried after it for the
# one case where they legitimately part - under `reach: ssh` the settings file
# stays on the user's machine and never crosses, but agent_ctl.sh still runs on
# the site and still needs the token left beside the run area there.
# T30: one location, beside the settings it belongs to. There is no search
# any more because there is nowhere else for it to be.
#
# Stored in plaintext, mode 600, deliberately - and the root is expected to be
# a synced folder, so say what that means rather than implying otherwise: the
# sync client uploads this file to a third party like any other, and on
# Windows the mode is advisory (the ACL is what decides). That was weighed
# against keeping it encrypted with a passphrase, which bought secrecy at the
# cost of a second, machine-local location and a password typed on every new
# machine - the exact "設定一次就好" property T30 exists to deliver. A Seqera
# personal access token is revocable from the Platform UI in one click, which
# is what makes this the cheaper side of the trade.
token_file() {
    if [ -n "${SEQERA_TOKEN_FILE:-}" ]; then printf '%s\n' "$SEQERA_TOKEN_FILE"; return 0; fi
    printf '%s\n' "$(dirname "$SETTINGS_FILE")/.seqera_token"
}

# One derivation of "is the WSL bridge in play", for on_site.sh, fetch.sh,
# push.sh, reset_master.sh and detect_conditions.sh. Those five worked it out
# four separate times when the bridge first landed, and two of the copies
# already disagreed: detect_conditions.sh probed `wsl.exe` alone and never
# read `site_bridge`, so a member who had turned the bridge off was told this
# machine was `supported` while on_site.sh refused every call it made. That is
# exactly the failure token_file() above exists to prevent, one subsystem over
# - and reset_master.sh, which never learned about the bridge at all, was
# telling people to close a master at a path nothing had opened.
#
# A function, never run at source time: the probe costs a process spawn and
# nearly everything in this repo sources this file.
bridge_kind() {   # -> wsl | none
    case "$(uname -s 2>/dev/null)" in
        MINGW*|MSYS*|CYGWIN*) ;;
        # WSL is a Windows-only concept, so there is nothing to detect
        # elsewhere - and a stray `wsl.exe` on some other PATH must never
        # change what these scripts do there.
        *) printf 'none\n'; return 0 ;;
    esac
    # Probed from a directory WSL can map, for the reason
    # scripts/utils/wsl_ssh.sh gives at length: a cloud-drive working directory
    # makes wsl.exe complain before it runs anything. Measured to be only a
    # warning there - but this probe reads an exit code, and a probe whose
    # answer depends on a warning staying a warning would turn "the bridge is
    # missing" into a refusal on a machine where WSL is working fine.
    #
    # The setting wins over the probe, in both directions: `site_bridge: none`
    # turns a working bridge off, which is what makes the refusal path
    # reachable on a machine that has WSL. So it is read FIRST, and the probe
    # only runs when there is no setting to answer with. It used to run on
    # every call regardless and then be overruled - and in the 2.15.0 Windows
    # verification one call spent 312 s inside it.
    #
    # </dev/null and a time limit on the probe for the same reason: wsl.exe
    # reads the stdin it inherits, and from a harness whose stdin is a pipe
    # that can hold it indefinitely. A WSL that has not answered in 20 s -
    # a cold start takes a few - is reported as no bridge, which is what the
    # caller would have to act on anyway.
    local _set _default=none
    _set="$(setting site_bridge "")"
    if [ -n "$_set" ]; then printf '%s\n' "$_set"; return 0; fi
    command -v wsl.exe >/dev/null 2>&1 \
        && ( cd "${HOME:-/}" 2>/dev/null || cd / 2>/dev/null || :
             clocked 20 wsl.exe -e true </dev/null >/dev/null 2>&1 ) \
        && _default=wsl
    printf '%s\n' "$_default"
}

# The ssh binary that goes with that answer. PITFALLS 16b/16g: Git Bash's own
# ssh cannot open a session over a master, WSL's can, and scripts/utils/
# wsl_ssh.sh is that one call - a script rather than a function because both
# `$SSH` and rsync's `-e` need something passable as a command string.
site_ssh_bin() {   # site_ssh_bin <bridge-kind> -> path or 'ssh'
    if [ "${1:-none}" = wsl ]; then
        printf '%s\n' "$(dirname "${BASH_SOURCE[0]}")/utils/wsl_ssh.sh"
    else
        printf 'ssh\n'
    fi
}

# The ControlPath default that goes with it. Under the bridge the master lives
# inside WSL, so the path has to be one WSL's OWN shell expands: left as the
# literal '~/...' it crosses wsl.exe unexpanded and resolves against WSL's
# home, rather than a Windows-shaped $HOME this shell would have expanded
# first. Either way it must not contain ':' - illegal in an NTFS filename,
# which is why the usual '%r@%h:%p' form cannot be used here (PITFALLS 16b).
site_control_path_default() {   # site_control_path_default <bridge-kind>
    if [ "${1:-none}" = wsl ]; then
        printf '%s\n' '~/.ssh/cm-%r-%h-%p'
    else
        printf '%s\n' "${HOME:-}/.ssh/cm-%r-%h-%p"
    fi
}

# --- T29: the local side's project layout -----------------------------------
# One place, so scripts/init_workspace.sh (which builds these directories)
# and scripts/where.sh (which answers "where are they" for commands/
# downstream.md and commands/finish.md) compute the SAME path by
# construction, never by a test asserting two independent formulas happen to
# agree.
#
# Two decisions:
#
# 1. Old layout (<local_root>/<seqera_user>/projects/<project>/...) or new
#    (<local_root>/projects/<project>/..., no <seqera_user> layer - matching
#    the portable folder's own shape, T23/docs/SETTINGS.md) - decided PER
#    PROJECT, by whether the old path already exists on this machine.
#    docs/SETTINGS.md: "Migration: none" - a project already living at the
#    old path keeps living there; only a brand new project gets the new one.
# T30 removed what used to be a second branch here: `analysis/` and
# `submission/` were redirected into the portable folder once one was adopted,
# while `rawdata/`/`runs/` stayed behind in a different root. There is only
# one root now, so there is nothing to redirect and nothing to keep in step.

# local_layout_is_old <root> <user> <project> -> 0 (true) if the OLD,
# <user>-layered path already exists for this project.
local_layout_is_old() {
    [ -n "${2:-}" ] && [ -n "${3:-}" ] && [ -d "${1%/}/$2/projects/$3" ]
}

# The base directory for rawdata/runs (and, with no portable folder,
# analysis/submission too): <root>/<user>/projects/<project> for a project
# that already lives there, <root>/projects/<project> for a new one.
local_project_base() {   # local_project_base <root> <user> <project>
    local root="${1%/}" user="${2:-}" project="${3:-}"
    if local_layout_is_old "$root" "$user" "$project"; then
        printf '%s\n' "$root/$user/projects/$project"
    else
        printf '%s\n' "$root/projects/$project"
    fi
}

# Where analysis/ and submission/ live. Kept as its own name rather than
# folded into local_project_base(): every caller that wants analysis/ says so
# by calling this, which is what made the T30 simplification a one-line change
# here instead of an audit of every call site.
local_analysis_base() {   # local_analysis_base <root> <user> <project>
    local_project_base "$1" "$2" "$3"
}

# The one place a `key: value` line is actually pulled out of a file -
# unchanged from before T23, just factored out so `setting()` can try it
# against two files in order instead of duplicating the sed pipeline.
_read_key() {   # _read_key <file> <key>
    [ -r "$1" ] || return 0
    sed -n "s/^[[:space:]]*${2}[[:space:]]*:[[:space:]]*//p" "$1" \
        | sed 's/[[:space:]]*#.*$//; s/[[:space:]]*$//' | head -1
}

# T30: the keys that cannot travel with the root, and must therefore live in
# <root>/config/machines/<machine>.yaml instead of config/env.yaml.
#
# It is a short list on purpose, and everything on it is DISCOVERED - `tw_bin`
# by install_deps.sh, `site_bridge` by probing for wsl.exe, `ssh_control_path`
# by its own default. Nobody is ever asked for one, so the machines/ file is
# never a thing a user has to know exists.
#
# agent_java and agent_jar are deliberately NOT here: under both `reach:
# local` and `reach: ssh` they are paths on the SITE, identical no matter
# which machine is doing the asking. Putting them in the machine file was the
# old layout's mistake - it made a second machine re-run install_deps.sh to
# rediscover values that had not changed.
MACHINE_KEYS=" tw_bin site_bridge ssh_control_path "

is_machine_key() { case "$MACHINE_KEYS" in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

setting() {
    local key="$1" fallback="${2:-}" val=""
    # The machine's own file first, and only for the keys that belong in it:
    # a stale tw_bin copied into env.yaml by an older version must not win
    # over what this machine actually has.
    if [ -n "$MACHINE_SETTINGS_FILE" ] && is_machine_key "$key"; then
        val="$(_read_key "$MACHINE_SETTINGS_FILE" "$key")"
    fi
    [ -n "$val" ] || val="$(_read_key "$SETTINGS_FILE" "$key")"
    if [ -n "$val" ]; then printf '%s\n' "$val"; return 0; fi
    if [ "$fallback" = "--required" ]; then
        if [ "$SETTINGS_FOUND" = 1 ]; then
            echo "missing '$key' in $SETTINGS_FILE." >&2
        else
            echo "missing '$key', and there is no settings file to read it from." >&2
            settings_missing >&2
        fi
        root_missing_reason >&2
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
    local key="$1" val="$2" created=0
    if [ -z "${SETTINGS_FILE:-}" ]; then
        # T30: there is deliberately nowhere to fall back to, so this has to
        # say what to do rather than just what is missing. A default root
        # would be a path that cannot travel, picked for somebody who was
        # never asked - the exact thing T30 removed.
        echo "no root on this machine, so there is nowhere to save '$key'." >&2
        echo "Choose somewhere that follows you between machines, then:" >&2
        echo "  scripts/settings.sh --use <root>" >&2
        if legacy_settings_found >/dev/null 2>&1; then
            echo "Set up before T30? Move it across instead, once:" >&2
            echo "  scripts/settings.sh --migrate <root>" >&2
        fi
        return 1
    fi
    # T30: a machine key goes to this machine's own file inside the same root,
    # so that a second machine adopting the root does not inherit a `tw_bin`
    # that does not exist there. Everything else goes to config/env.yaml and
    # travels. One function, one routing decision, so no caller has to know.
    local SETTINGS_FILE="$SETTINGS_FILE"
    if is_machine_key "$key" && [ -n "${MACHINE_SETTINGS_FILE:-}" ]; then
        SETTINGS_FILE="$MACHINE_SETTINGS_FILE"
    fi
    mkdir -p "$(dirname "$SETTINGS_FILE")"
    if [ ! -e "$SETTINGS_FILE" ]; then
        created=1
        : > "$SETTINGS_FILE"
        chmod 600 "$SETTINGS_FILE"
    fi
    # awk, not python3, and ENVIRON rather than `awk -v`. PITFALLS 20c: Git
    # Bash's python3 is a Microsoft Store stub that sits on PATH, prints
    # nothing, and exits 49 - this was the one place in the whole repo that
    # still needed a real python3 to exist, to rewrite a single `key: value`
    # line. awk is POSIX and Git Bash ships it - tests/portable_userland.sh
    # holds this file to POSIX awk, so no gensub, no GNU-only extension.
    # Still not a real YAML parser, for the same reason `setting()` above
    # is not one (see this file's own header): the settings file is only
    # ever `key: value` plus an optional trailing comment, by design.
    #
    # ENVIRON, not `awk -v key=... val=...`: POSIX has awk interpret
    # backslash escapes inside a `-v` assignment the same way it would
    # inside a string literal, so a value with a bare backslash in it - a
    # Windows path typed without forward slashes - would come out mangled.
    # ENVIRON hands awk the same bytes bash already has, untouched.
    local _tmp
    _tmp="$(mktemp "${SETTINGS_FILE}.XXXXXX" 2>/dev/null)" || {
        echo "could not create a temp file beside $SETTINGS_FILE" >&2
        [ "$created" = 1 ] && rm -f "$SETTINGS_FILE"
        return 1
    }
    if ! AWK_KEY="$key" AWK_VAL="$val" awk '
        BEGIN {
            key = ENVIRON["AWK_KEY"]; val = ENVIRON["AWK_VAL"]
            klen = length(key); found = 0
        }
        {
            rest = $0
            sub(/^[ \t]*/, "", rest)
            if (!found && substr(rest, 1, klen) == key) {
                after = substr(rest, klen + 1)
                sub(/^[ \t]*/, "", after)
                if (substr(after, 1, 1) == ":") {
                    found = 1
                    # Keep any trailing comment: it usually says why the
                    # value matters.
                    comment = ""
                    hashpos = index($0, "#")
                    if (hashpos > 0) comment = "  #" substr($0, hashpos + 1)
                    print key ": " val comment
                    next
                }
            }
            print
        }
        END { if (!found) print key ": " val }
    ' "$SETTINGS_FILE" > "$_tmp"
    then
        rm -f "$_tmp"
        [ "$created" = 1 ] && rm -f "$SETTINGS_FILE"
        echo "awk failed to rewrite $SETTINGS_FILE" >&2
        return 1
    fi
    # Content only, not the file itself: `mv` would swap in the temp file's
    # own inode, and mktemp always creates that at mode 600 regardless of
    # umask - which would make the mode-600 check just below pass by
    # accident, on a file that never actually went through the chmod that
    # check exists to verify. Writing into the existing file instead - the
    # same thing the python block's own `open(path, "w")` did - keeps
    # whatever mode the file already had until the explicit chmod decides it.
    cat "$_tmp" > "$SETTINGS_FILE" || {
        rm -f "$_tmp"
        echo "failed to write $SETTINGS_FILE" >&2
        return 1
    }
    rm -f "$_tmp"
    chmod 600 "$SETTINGS_FILE"

    # B1: the chmod above can be *accepted* and change nothing. Measured shape:
    # /mnt/c under WSL without the `metadata` mount option, and exFAT, both take
    # the syscall and silently keep whatever mode the file already had - no
    # error, nothing to catch, and the token that lives beside this file
    # (docs/SETTINGS.md) ends up readable by anyone with access to that
    # filesystem. Reading the mode back is the only way to see that; the chmod
    # returning success proves nothing on its own.
    #
    # An empty stat_mode is a DIFFERENT case, not this one. token_state() (this
    # file, below) already treats "" as "cannot tell" rather than "unsafe" - its
    # own empty-string branch - and a refusal on a machine whose `stat` simply
    # answers differently would be a worse failure than the silent-token bug
    # this exists to catch. So "" carries on here too.
    local _priv _state; _priv="$(file_privacy "$SETTINGS_FILE")"
    _state="${_priv%% *}"
    case "$_state" in
        private|unknown) return 0 ;;
    esac
    # Only a file THIS call created is ours to remove. One that already held a
    # member's real settings must stay - deleting it over a permission problem
    # would be a second, worse failure stacked on the first.
    if [ "$created" = 1 ]; then rm -f "$SETTINGS_FILE"; fi
    refuse_unwritable_mode "$SETTINGS_FILE" "${_priv#* }"
    return 1
}

# What set_setting() calls when chmod 600 did not hold. Same shape as
# refuse_site_shaped_write() below: name the file, say why, name where it
# works instead.
refuse_unwritable_mode() {
    local file="$1" why="$2"
    echo "refusing to write settings to $file: it would not be private to you." >&2
    echo "" >&2
    # 16k: this used to be one paragraph about chmod, because the mode was the
    # only thing it ever looked at. On Windows the mode is not what decides,
    # and saying "chmod 600 was accepted but..." there would be describing a
    # call whose result was never consulted.
    if [ "$(plat_kind)" = msys ]; then
        echo "$why." >&2
        echo "" >&2
        echo "The permission bits Git Bash prints here are manufactured, and this" >&2
        echo "check did not use them: it asked Windows itself who can open the file," >&2
        echo "and Windows named someone beyond you, SYSTEM and the Administrators" >&2
        echo "group. No chmod in this shell can change that answer." >&2
        echo "" >&2
        echo "A folder in your own user profile is owner-only by default. Point" >&2
        echo "the root at one instead:" >&2
        printf '  scripts/settings.sh --use %s\n' "$(example_root)" >&2
        echo "A drive with no ACLs at all - a USB stick, or a cloud-drive folder -" >&2
        echo "answers this way about every file on it, and is no place for a token." >&2
        return 0
    fi
    echo "chmod 600 was accepted but the file is still $why. /mnt/c under WSL" >&2
    echo "(without the 'metadata' mount option) and exFAT both do this: the chmod" >&2
    echo "call succeeds and silently changes nothing. A token saved there is" >&2
    echo "effectively public to anyone with access to that filesystem." >&2
    echo "" >&2
    echo "Point the root at a filesystem that can hold mode 600, for example" >&2
    printf '  scripts/settings.sh --use %s\n' "$(example_root)" >&2
    echo "Anything under \$HOME on a native Linux or macOS filesystem will do." >&2
}

# T30 deleted three refusals that lived here, and it is worth saying which and
# why, because each was load-bearing under the old layout:
#
# - site_shaped_write_refusal()/refuse_site_shaped_write() (D5) caught a
#   settings file being written into a `$LAB_RUNS_DIR`-shaped directory on the
#   user's own machine. It cannot happen any more: SETTINGS_FILE is derived
#   from the root pointer and never from LAB_RUNS_DIR, so there is no code
#   path left for that variable to steer a write.
# - looks_synced_write_refusal()/refuse_synced_write() refused to write
#   settings into a synced folder at all. Under T30 a synced folder is the
#   INTENDED home for the root - refusing it would refuse the design. What the
#   refusal was protecting (the token) is addressed where the token is
#   defined, in token_file() above, by saying plainly what the trade is.
#
# What survives is the caution below, which warns and never refuses.

# The root is expected to be a synced folder, so this is a note, not a gate.
# Two things still have to be said, because neither is obvious and both cost
# real money or real time when they go wrong.
cloud_sync_caution() {   # cloud_sync_caution <path> <setting-key>
    local path="$1" key="$2"
    looks_cloud_synced "$path" || return 0
    echo "note: '$key' ($path) looks like it is inside a synced folder (OneDrive," >&2
    echo "Dropbox, Google Drive, iCloud's Library/Mobile Documents, Box, Nextcloud," >&2
    echo "...) - not a complete list, any folder that syncs anywhere is the same risk." >&2
    echo "That is the intended home for it. Two things to know:" >&2
    echo "  - large files (rawdata, results, container images) sync slowly and will" >&2
    echo "    eat the sync quota. They do not live here - rawdata and results stay" >&2
    echo "    on the site, and only what an IDE opens is kept in the root." >&2
    echo "  - the Seqera token is in config/.seqera_token, mode 600, in plaintext," >&2
    echo "    so the sync client holds a copy of it. That is a deliberate trade" >&2
    echo "    (scripts/settings.sh, token_file). A token is revocable from the" >&2
    echo "    Seqera UI in one click if the folder is ever shared by mistake." >&2
    return 0
}

# --- T30: settings.sh --use <path> ------------------------------------------
# Point THIS machine at a root, creating the root if it is not there yet.
#
# One command covers both cases on purpose. The old layout split them -
# `portable_root.sh init` built a folder, `settings.sh --adopt` pointed at an
# existing one - and the split was a source of its own errors: a person on
# their second machine had to know which of the two they were, and picking
# wrong either clobbered nothing or reported a folder as "not one we built".
# Here the folder's existence answers it, not the user.
use_root() {   # use_root <path>
    local path="$1" created=0
    case "$path" in
        /*) ;;
        [A-Za-z]:[\\/]*) ;;   # a Windows path handed straight to Git Bash
        *) echo "the root must be an absolute path, not '$path'." >&2
           return 2 ;;
    esac
    path="${path%/}"

    if [ -r "$path/config/env.yaml" ]; then
        : # an existing root: nothing to build, only to point at
    elif [ -e "$path" ] && [ ! -d "$path" ]; then
        echo "refusing to use $path: it exists and is not a directory." >&2
        return 1
    else
        mkdir -p "$path/config/machines" "$path/projects" || {
            echo "could not create $path - check the path and permissions." >&2
            echo "If this is a synced folder that has not appeared on this machine" >&2
            echo "yet, wait for the sync client rather than creating it by hand." >&2
            return 1
        }
        chmod 700 "$path/config" 2>/dev/null || true
        created=1
    fi

    local pointer_dir; pointer_dir="$(dirname "$ROOT_POINTER")"
    mkdir -p "$pointer_dir" || { echo "could not create $pointer_dir" >&2; return 1; }
    printf '%s\n' "$path" > "$ROOT_POINTER" || {
        echo "could not write $ROOT_POINTER" >&2; return 1; }
    chmod 600 "$ROOT_POINTER" 2>/dev/null || true

    cloud_sync_caution "$path" root
    if [ "$created" = 1 ]; then
        echo "created $path"
        printf '  %s\n' "$path/config/     settings, token, and this machine's own file"
        printf '  %s\n' "$path/projects/   analysis and results, one directory per project"
    else
        echo "using the root already at $path"
    fi
    echo "this machine now reads: $path/config/env.yaml"
    echo "(remembered in $ROOT_POINTER - nothing else on this machine holds any of it)"
}

# --- T30: settings.sh --migrate <path> --------------------------------------
# The one-time move off the pre-T30 layout. T30 cut over rather than searching
# both layouts forever, so a deployment that already ran setup needs exactly
# one command - this one - and never has to answer setup's questions again.
#
# Copies, never moves: the old files are left exactly where they are. A
# migration that deletes the only copy of somebody's credentials before the
# new location has been proven is not a migration, it is a gamble. Say where
# they are instead and let the user delete them.
migrate_legacy() {   # migrate_legacy <path>
    local path="${1:-}" old key val n=0 m=0
    if ! old="$(legacy_settings_found)"; then
        echo "nothing to migrate: no settings file at either of the pre-T30 locations." >&2
        echo "Looked for:" >&2
        [ -n "${LAB_RUNS_DIR:-}" ] && printf '  %s\n' "${LAB_RUNS_DIR%/}/_personal/env.yaml" >&2
        printf '  %s\n' "${XDG_CONFIG_HOME:-${HOME:-}/.config}/agentic-bioflow/env.yaml" >&2
        echo "If this machine has never been set up, run setup instead." >&2
        return 1
    fi
    [ -n "$path" ] || { echo "usage: settings.sh --migrate <root>" >&2; return 2; }

    use_root "$path" || return 1
    # use_root wrote the pointer; re-resolve so set_setting writes to the new
    # root rather than wherever this shell resolved at source time.
    ABF_ROOT="${path%/}"
    SETTINGS_FILE="$ABF_ROOT/config/env.yaml"
    MACHINE_SETTINGS_FILE="$ABF_ROOT/config/machines/$(machine_id).yaml"

    echo
    echo "migrating from $old"
    while IFS= read -r line; do
        case "$line" in
            [a-z_]*:*) ;;
            *) continue ;;
        esac
        key="${line%%:*}"
        val="$(_read_key "$old" "$key")"
        [ -n "$val" ] || continue
        # local_root is gone: the root IS the local side now, and this
        # machine's copy of that answer is the pointer file, not a key.
        if [ "$key" = "local_root" ]; then
            echo "  local_root ($val) is superseded by the root itself - not carried over"
            continue
        fi
        set_setting "$key" "$val" >/dev/null || continue
        if is_machine_key "$key"; then m=$((m+1)); else n=$((n+1)); fi
    done < "$old"
    echo "  $n setting(s) into config/env.yaml, $m into config/machines/$(machine_id).yaml"

    local oldtok="$(dirname "$old")/.seqera_token" newtok="$ABF_ROOT/config/.seqera_token"
    if [ -r "$oldtok" ] && [ ! -e "$newtok" ]; then
        cp -p "$oldtok" "$newtok" && chmod 600 "$newtok" 2>/dev/null
        echo "  token copied to $newtok"
    elif [ -e "$newtok" ]; then
        echo "  token already present at $newtok - left alone"
    else
        echo "  no token found beside the old settings - setup step 3 saves one"
    fi

    echo
    echo "Done. The old files are untouched and can be deleted once this is proven:"
    printf '  %s\n' "$old"
    [ -r "$oldtok" ] && printf '  %s\n' "$oldtok"
    echo "Run 'scripts/preflight.sh' first; delete them only after it passes."
}

# --- T23: settings.sh --reconstruct -----------------------------------------
# The fallback for issue #17's actual reported shape: no portable folder, and
# the site's own _personal/env.yaml only ever held agent_java/agent_jar/
# tw_bin/agent_connection - the values scripts/install_deps.sh and
# scripts/agent_ctl.sh discover on their own, never the ones a person has to
# be asked for. Everything Platform can answer is read back here as a
# CANDIDATE only; nothing is written automatically (docs/SETTINGS.md: "must
# be asked for rather than guessed") - confirm each with
# `scripts/settings.sh --set <key> <value>`.
#
# tw's exact table output was not measured against a real `tw` binary on this
# machine (none installed here, no network to fetch one - PRINCIPLES.md
# invariant 8: measure or read the source before claiming). Parsing here
# indexes columns by their header text rather than a fixed position, and
# falls back to printing the raw table when it cannot find what it is looking
# for - a degraded answer, never a silently wrong one.
_reconstruct_tw_bin() {
    local t; t="${TW_BIN:-$(setting tw_bin)}"
    [ -n "$t" ] || t="tw"
    command -v "$t" >/dev/null 2>&1 && printf '%s\n' "$t"
}

# Index-by-header-name table reader for tw's `|`-delimited list output (the
# one shape actually confirmed in this repo: scripts/preflight.sh parses
# `tw compute-envs view` the same way). <label> is what each candidate line
# is printed as.
_table_candidates() {   # _table_candidates <table-text> <label>
    local text="$1" label="$2" header
    header=$(grep -F '|' <<<"$text" | grep -iE '(^| )id( |\|)' | head -1)
    if [ -z "$header" ]; then
        echo "  (could not find an 'Id' column in this table - read it yourself:)"
        sed 's/^/  | /' <<<"$text"
        return 0
    fi
    local idx nidx
    idx=$(awk -F'|' -v h="$header" 'BEGIN{
        n=split(h,a,"|")
        for(i=1;i<=n;i++){g=a[i]; gsub(/^[ \t]+|[ \t]+$/,"",g); if (tolower(g)=="id"){print i; exit}}
    }')
    nidx=$(awk -F'|' -v h="$header" 'BEGIN{
        n=split(h,a,"|")
        for(i=1;i<=n;i++){g=a[i]; gsub(/^[ \t]+|[ \t]+$/,"",g); if (tolower(g)=="name"){print i; exit}}
    }')
    [ -n "$idx" ] || { echo "  (no 'Id' column - read the raw table yourself:)"; sed 's/^/  | /' <<<"$text"; return 0; }
    awk -F'|' -v idx="$idx" -v nidx="${nidx:-0}" -v label="$label" -v hdr="$header" '
        $0 == hdr { next }
        /^[[:space:]|:+=-]+$/ { next }
        NF >= idx {
            id=$idx; gsub(/^[ \t]+|[ \t]+$/,"",id)
            if (id == "" || tolower(id) == "id") next
            name=""
            if (nidx > 0 && NF >= nidx) { name=$nidx; gsub(/^[ \t]+|[ \t]+$/,"",name) }
            print "  candidate " label ": " id (name != "" ? " (" name ")" : "")
        }' <<<"$text"
}

reconstruct_settings() {
    local tw; tw="$(_reconstruct_tw_bin)"
    if [ -z "$tw" ]; then
        echo "no working 'tw' found (the tw_bin setting, or on PATH) - cannot" >&2
        echo "reconstruct anything. Install it first: scripts/install_deps.sh --cli-only." >&2
        return 1
    fi

    local tokf; tokf="$(token_file)"
    if [ -z "${TOWER_ACCESS_TOKEN:-}" ] && [ -r "$tokf" ]; then
        TOWER_ACCESS_TOKEN="$(cat "$tokf")"; export TOWER_ACCESS_TOKEN
    fi
    if [ -z "${TOWER_ACCESS_TOKEN:-}" ]; then
        echo "no Seqera token available (checked $tokf and \$TOWER_ACCESS_TOKEN) -" >&2
        echo "reconstruction needs one to ask Platform anything at all. See" >&2
        echo "docs/SETTINGS.md / commands/setup.md step 3 for how to get one." >&2
        return 1
    fi

    echo "Reconstructing from Seqera Platform - every line below is a CANDIDATE."
    echo "Confirm each one with the user, then save it yourself:"
    echo "  scripts/settings.sh --set <key> <value>"
    echo "Nothing here is written automatically."
    echo

    local info user_line
    info="$("$tw" info 2>&1)"
    user_line=$(grep -iE 'user' <<<"$info" | head -1)
    echo "-- seqera_user, from '$tw info' --"
    if [ -n "$user_line" ]; then
        # The label/value separator was not measured (no real `tw` here to
        # check against - see this function's own header comment): a ':' or
        # '|' on the line is trusted as that separator when present, and
        # otherwise this falls back to the LAST whitespace-separated field,
        # which is right for a two-column "label   value" layout too.
        local cand
        case "$user_line" in
            *:*|*'|'*)
                cand="${user_line}"
                cand="${cand##*:}"
                cand="${cand##*|}" ;;
            *)
                cand="${user_line##* }" ;;
        esac
        cand="$(sed 's/^[[:space:]]*//;s/[[:space:]]*$//' <<<"$cand")"
        echo "  candidate seqera_user: $cand"
        echo "  (from the line: $user_line)"
    else
        echo "  (no line mentioning a user - read the raw output yourself:)"
        sed 's/^/  | /' <<<"$info"
    fi
    echo

    echo "-- workspace_id, from '$tw workspaces list' --"
    _table_candidates "$("$tw" workspaces list 2>&1)" workspace_id
    echo

    echo "-- compute_env --"
    echo "  needs a confirmed workspace_id first, so this is not run automatically:"
    echo "    $tw compute-envs list -w <the workspace_id you just confirmed>"
    echo "  confirm against the Name column, which is what the 'compute_env' setting"
    echo "  actually stores (docs/SETTINGS.md)."
    echo

    echo "-- slurm_account --"
    echo "  cannot be read from Platform at all - it is the site's own allocation,"
    echo "  never Seqera's. On the site, ask the user to check:"
    echo "    sacctmgr show associations user=\$USER format=account"
    echo "    sshare -U -u \$USER"
    echo "  and confirm which one this deployment should bill to. There is"
    echo "  deliberately no default here (docs/SETTINGS.md) - never guess it, and"
    echo "  never copy it from another member."
}

# Which startup file an export has to go into, and the line to put there.
#
# Writing `~/.bashrc` unconditionally is wrong the moment the shell is not
# bash: zsh - the default on macOS since Catalina - never reads it, so the
# export vanishes with no error and the next terminal looks unconfigured. That
# is PITFALLS 25's symptom reached by a different road, on a machine with only
# one home directory and therefore no clue to follow.
#
# $SHELL, not $0 and not the parent process: the question is what a NEW
# terminal will start and therefore what will read a startup file, and this
# script may well be running under a bash the user never chose.
#
# The line is generated rather than left to the caller because the file and the
# syntax have to agree - fish takes `set -gx`, and an `export` written into
# config.fish is a syntax error at every future shell start.
profile_file() {
    case "$(basename "${SHELL:-sh}")" in
        zsh)  printf '%s\n' "${ZDOTDIR:-$HOME}/.zshrc" ;;
        bash) printf '%s\n' "$HOME/.bashrc" ;;
        fish) printf '%s\n' "$HOME/.config/fish/config.fish" ;;
        ksh)  printf '%s\n' "$HOME/.kshrc" ;;
        csh|tcsh) printf '%s\n' "$HOME/.cshrc" ;;
        # sh, dash, ash, mksh and anything unrecognised: ~/.profile with POSIX
        # `export` is the answer that is right for all of them. The two shells
        # it would be wrong for - fish and csh - are the two named above,
        # because a wrong answer here is silent in both directions: the file is
        # never read, or the line is a syntax error at every future shell start.
        *)    printf '%s\n' "$HOME/.profile" ;;
    esac
}

profile_export() {
    local name="${1:?usage: --profile-export <NAME> <VALUE>}" val="${2?}"
    case "$(basename "${SHELL:-sh}")" in
        fish)     printf 'set -gx %s %s\n' "$name" "$val" ;;
        csh|tcsh) printf 'setenv %s "%s"\n' "$name" "$val" ;;
        *)        printf 'export %s="%s"\n' "$name" "$val" ;;
    esac
}

# `settings.sh --summary` - one screen answering "what am I configured as", and
# above all *where that answer lives*. Nothing else in this repo ever names the
# file it just read, which is how a member came to be grepping the filesystem
# for it.
#
# The token's value is never part of this. Setup's own rule for it is "never
# printed, never in git, never in a params file", and a convenience command that
# leaked it would be a worse bug than the one this fixes. Only two things about
# it are anybody's business here: whether it is there, and whether its mode
# still keeps it to one person.
token_state() {
    local f p; f="$(token_file)"
    if [ -r "$f" ]; then
        p="$(file_privacy "$f")"
        case "${p%% *}" in
            private) printf 'present (%s)  %s\n' "${p#* }" "$f" ;;
            unknown) printf 'present  %s\n' "$f" ;;
            *)       printf 'present but %s  %s\n' "${p#* }" "$f" ;;
        esac
    elif [ -e "$f" ]; then
        printf 'present but unreadable  %s\n' "$f"
    else
        printf 'not found - looked beside the settings file\n'
    fi
}

settings_summary() {
    [ "$SETTINGS_FOUND" = 1 ] || { settings_missing >&2; root_missing_reason >&2; return 1; }
    local r='  %-20s %s\n' host
    host="$(setting site_host)"
    echo "This deployment:"
    echo
    # shellcheck disable=SC2059
    printf "$r" "root"                "${ABF_ROOT:-$(dirname "$(dirname "$SETTINGS_FILE")")}"
    printf "$r" "settings file"       "$SETTINGS_FILE"
    printf "$r" "site account"        "$(setting site_user 'not set')"
    printf "$r" "site"                "$(setting reach local)${host:+ - $host}"
    printf "$r" "seqera account"      "$(setting seqera_user 'not set')"
    printf "$r" "workspace"           "$(setting workspace_id 'not set')"
    printf "$r" "run area"            "$(setting storage_root "${LAB_RUNS_DIR:-not set}")"
    printf "$r" "compute environment" "$(setting compute_env 'not set')"
    printf "$r" "agent connection"    "$(setting agent_connection 'not set')"
    printf "$r" "token"               "$(token_state)"
    echo
    # B2: this used to assert "mode 600" outright. token_state() above already
    # reads the mode back and reports what it actually is rather than what it
    # should be - the two halves of one file were inconsistent. Same call,
    # same three-way read here, so a filesystem that cannot hold 600 (B1) is
    # not contradicted two lines later by a sentence that was never checked.
    local _sp; _sp="$(file_privacy "$SETTINGS_FILE")"
    case "${_sp%% *}" in
        private) echo "All of it is saved at $SETTINGS_FILE, ${_sp#* }." ;;
        unknown) echo "All of it is saved at $SETTINGS_FILE; ${_sp#* }." ;;
        *)       echo "All of it is saved at $SETTINGS_FILE, ${_sp#* }." ;;
    esac
    # T30: the whole point of one root is that this sentence is short enough
    # to be true. It used to have to explain which of three files each value
    # came from.
    if [ -r "${MACHINE_SETTINGS_FILE:-/nonexistent}" ]; then
        printf 'Three keys that cannot travel are in %s.\n' "$MACHINE_SETTINGS_FILE"
        echo "They are found automatically on each machine; you are never asked for them."
    fi
    echo "Take the root with you and any other machine needs one command:"
    echo "  scripts/settings.sh --use $ABF_ROOT"
    echo "Nothing here has to be entered again, on this machine or any other."
}

# Allow `settings.sh <key> [default]` and `settings.sh --set <key> <value>` as
# well as sourcing it. The writing form is for the case where the discovery
# happened somewhere else: a script run on the site knows where it put things,
# but its own set_setting can only reach the settings file it can see, which on
# a deployment driven from the user's machine is not the one that counts.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    case "${1:-}" in
        --set)
            _k="${2:?usage: settings.sh --set <key> <value>}"
            _v="${3?usage: settings.sh --set <key> <value>}"
            set_setting "$_k" "$_v" ;;
        --summary)
            settings_summary ;;
        --profile-file)
            profile_file ;;
        --profile-export)
            profile_export "${2:?usage: settings.sh --profile-export <NAME> <VALUE>}" \
                           "${3?usage: settings.sh --profile-export <NAME> <VALUE>}" ;;
        --use)
            use_root "${2:?usage: settings.sh --use <root>}" ;;
        --migrate)
            migrate_legacy "${2:?usage: settings.sh --migrate <root>}" ;;
        --root)
            if [ -n "$ABF_ROOT" ]; then printf '%s\n' "$ABF_ROOT"; else
                echo "no root set on this machine (see $ROOT_POINTER)" >&2; exit 1; fi ;;
        --machine-file)
            printf '%s\n' "${MACHINE_SETTINGS_FILE:-}" ;;
        --reconstruct)
            reconstruct_settings ;;
        *)
            setting "${1:?usage: settings.sh <key> [default|--required] | --summary | --set <key> <value>}" \
                    "${2:-}" ;;
    esac
fi
