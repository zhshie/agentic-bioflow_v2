#!/bin/bash
# One `source` that sets PATH and TOWER_ACCESS_TOKEN from this deployment's
# own settings, so every command file's "Before anything else" section can
# open with one line instead of each later step re-deriving `tw`'s location
# and the token separately.
#
# Why this matters here specifically (GitHub issue #13): the PreToolUse hooks
# measure at ~0.17s/call, which is not the bottleneck - a `launch` walk costs
# 20-40 tool-call round trips, each one a full model turn. Folding "find tw,
# read the token" into the same line as the call that needs them removes a
# turn every time a command file would otherwise have spent one deriving
# them first.
#
# Not a hook: PreToolUse/SessionStart run in their OWN process and exit -
# nothing they export survives into the Bash tool call that follows. And the
# Bash tool starts a fresh shell for every call, so one source at the top of
# a command does not carry over either: each call that runs `tw` opens with
# `. scripts/env.sh &&` itself. That is still no extra round trip - the
# prefix rides inside the call that needed it.
#
# Nothing existing: `tw`/`nextflow` land on PATH through the site account's
# own ~/.bashrc once `scripts/on_site.sh` runs something there (PITFALLS
# 16c) - but that guard only ever executes on the far side of an ssh call.
# This file is for the shell the agent itself is typing into: the laptop
# under reach:ssh, or the interactive login shell under reach:local/none -
# neither of which reads the site account's ~/.bashrc at all.
#
#   . scripts/env.sh
#
# Sets, best-effort and never fatal:
#   PATH                 the directory holding `tw_bin` (settings.sh), once,
#                         prepended only if it is not on PATH already
#   TOWER_ACCESS_TOKEN    read from the token file beside the settings file
#                         (settings.sh's own token_file()), unless a value is
#                         already exported - an explicit export always wins,
#                         the same order preflight.sh already uses
#
# Deliberately quiet on every failure shape: no settings file yet (setup's own
# first run, before either value exists), no tw_bin recorded, no readable
# token file. Refusing to source over any of those would make this less safe
# to put first in every command file, not more - the calls that actually need
# `tw` or the token already fail on their own, with their own message, and
# this is only a convenience that removes a few of the round trips leading up
# to that point, never a gate.
set -uo pipefail
_ENV_SH_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -r "$_ENV_SH_HERE/settings.sh" ]; then
    . "$_ENV_SH_HERE/settings.sh"
else
    echo "scripts/env.sh: missing $_ENV_SH_HERE/settings.sh - this deployment is incomplete." >&2
fi

# --- PATH: tw's own directory, once -----------------------------------------
if command -v setting >/dev/null 2>&1; then
    _env_tw_bin="$(setting tw_bin 2>/dev/null)"
    if [ -n "$_env_tw_bin" ]; then
        _env_tw_dir="$(dirname "$_env_tw_bin")"
        case ":${PATH:-}:" in
            *":$_env_tw_dir:"*) ;;   # already there - do not grow PATH on every source
            *) PATH="$_env_tw_dir:${PATH:-}" ;;
        esac
    fi
    unset _env_tw_bin _env_tw_dir
    export PATH
fi

# --- TOWER_ACCESS_TOKEN: read once, unless already exported ----------------
# An empty exported value is treated as "not set" - `export TOWER_ACCESS_TOKEN=`
# left over from an earlier, failed attempt must not block this one from
# reading the real token file.
if [ -z "${TOWER_ACCESS_TOKEN:-}" ] && command -v token_file >/dev/null 2>&1; then
    _env_token_file="$(token_file 2>/dev/null)"
    if [ -n "$_env_token_file" ] && [ -r "$_env_token_file" ]; then
        _env_token="$(cat "$_env_token_file" 2>/dev/null)"
        [ -n "$_env_token" ] && export TOWER_ACCESS_TOKEN="$_env_token"
        unset _env_token
    fi
    unset _env_token_file
fi

unset _ENV_SH_HERE
