#!/bin/bash
# Sourced by the site scripts that shell out to python3 - egress_ctl.sh for its
# port search, agent_ctl.sh for its JSON state.
#
# Why this exists rather than letting the failure speak for itself: on this
# cluster `/usr/bin/python3` is a symlink to RHEL's own reserved interpreter,
# mode 750 root:root. It is present, it is on PATH, and every use of it returns
# a bare `Permission denied` - which reads like a broken install of this plugin
# rather than a site that fences its system interpreter (PITFALLS 16d). The
# real one comes from the module system.
require_python() {
    local out rc
    out=$(python3 -c '' 2>&1); rc=$?
    [ "$rc" = 0 ] && return 0

    if [ "$rc" = 126 ] || printf '%s' "$out" | grep -qi 'permission denied'; then
        printf '%s\n' \
          "python3 is on PATH but this account may not run it:" \
          "  $(command -v python3 2>/dev/null || echo python3) -> ${out:-Permission denied}" \
          "" \
          "That is usually the site fencing its own system interpreter rather" \
          "than anything wrong here (PITFALLS 16d). Ask the module system for a" \
          "real one:" \
          "" \
          "    module avail python" \
          "    module load python/<version>" \
          "" \
          "Put that 'module load' line in the site account's ~/.bashrc ABOVE the" \
          "interactive-only guard - a 'ssh host <cmd>' session never reaches the" \
          "far side of it, which is the same trap tw and nextflow fell into" \
          "(PITFALLS 16c)." >&2
    else
        printf '%s\n' \
          "python3 is unusable here: ${out:-exit $rc}" \
          "" \
          "The site provides it; this plugin does not install one. Try" \
          "'module avail python'." >&2
    fi
    return 1
}
