#!/bin/bash
# The WSL bridge's ssh, made to look exactly like ssh to everything that
# calls it.
#
# Not a shell function: scripts/on_site.sh's $SSH and rsync's `-e` both need
# something passable as a command STRING, not an entry in this shell's own
# function table - a function answers the first and vanishes the moment rsync
# forks its own process for the second. A tiny standalone script is callable
# from both, unmodified.
#
# Not "teach Git Bash's own ssh to multiplex": PITFALLS 16b measured that it
# cannot - the control plane answers, so a master looks alive, and the session
# request then fails, because MSYS emulates Unix sockets and does not
# implement the descriptor passing a session needs. No ssh option changes that.
#
# What does work, measured (PITFALLS 16g): calling WSL's OWN ssh from Git Bash.
# `wsl.exe -e ssh` over a master opened in WSL answered in 0.55 s with no
# one-time code, and carried binary stdin and exit codes intact. The ssh
# client and the master are both inside WSL, so the fd-passing 16b found
# missing happens on a real Linux kernel; this script only spawns wsl.exe and
# lets bytes cross it.
#
# `exec`, not a subshell call: this replaces the current process rather than
# wrapping it, so the exit code wsl.exe returns is exactly what the caller
# (on_site.sh, or rsync's `-e` child) sees - nothing here is left to smooth
# over a nonzero status into something else.
#
# Every argument is handed to `wsl.exe -e ssh` verbatim - no reparsing, no
# extra quoting layer added here. Whether an argument that already crossed one
# quoting boundary (rsync building this file's own `-e "wsl_ssh.sh -o
# ControlPath=..."` string) survives a SECOND hop through wsl.exe is
# unmeasured - risk R1 in the plan. tests/wsl_bridge_test.sh pins the literal
# argv a fake wsl.exe receives so a regression here cannot pass silently.
# Measured on the member's own machine, 2026-09-16: with the working directory
# set to a cloud-drive path WSL cannot map (`G:\...`, and non-ASCII besides),
# `wsl.exe` prints a path-translation warning on stderr and starts in a default
# directory instead. It carried on rather than failing - the exit code that came
# back was the inner command's own - so this was a warning, not a fault. That is
# luck, not design: it would put a line of Windows-shaped noise on stderr in
# front of every single call to the site, and nothing here should depend on a
# warning staying a warning.
#
# The working directory means nothing to this call - ControlPath is absolute or
# WSL-side, and rsync hands file paths to itself, never to the ssh it spawns -
# so the cheapest fix is to not offer wsl.exe an untranslatable one. $HOME under
# Git Bash is the Windows profile, always a real path on a fixed drive; `/` is
# the Git installation directory and is the fallback for the case where it is
# not. Deliberately not `wsl.exe --cd`, which would do the same thing: that flag
# is not in every wsl.exe old enough to be in use, and an unrecognised flag
# fails the whole call rather than one warning line.
cd "${HOME:-/}" 2>/dev/null || cd / 2>/dev/null || :
exec wsl.exe -e ssh "$@"
