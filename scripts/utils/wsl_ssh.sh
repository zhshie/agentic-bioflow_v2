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
exec wsl.exe -e ssh "$@"
