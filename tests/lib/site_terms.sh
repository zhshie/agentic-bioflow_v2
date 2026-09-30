#!/bin/bash
# Shared term list for invariant 4 (the command layer is site-neutral),
# sourced by tests/command_layer_is_site_neutral.sh and
# tests/launch_provenance_test.sh so the two lists cannot drift apart
# (bug: false-green-tests, item 1).
#
# grep -E, not -P: -P errors out (exit 2) under some locales - the false-green
# bug this file exists to fix, where that error was read as "no match" - and
# is absent entirely from BSD grep, i.e. the maintainer's Mac
# (tests/portable_userland.sh). The one thing -P bought here, a negative
# lookbehind so the site adapter's own `reach: ssh` contract value did not
# count as the command layer naming ssh, is done as a second pass instead
# (site_terms_allow): collect every line that matches a term, then drop the
# lines whose only reason for matching is a phrase that is not the command
# layer naming site machinery.
# Word boundaries spelled out rather than \b, which BSD grep -E (the Mac)
# does not promise.
SITE_TERMS='slurm|sbatch|squeue|scontrol|sacctmgr|qos|partition|relay|proxy|singularity|module load|(^|[^[:alnum:]_])(ssh|scp|rsync)([^[:alnum:]_]|$)'

# site_terms_grep <path>...
# Case-insensitive (-i): a scheduler name capitalised in prose - "SLURM",
# "Slurm" - is exactly the kind of hit the lowercase-only original list
# missed, silently, on top of the -P bug. A grep error (rc >= 2 - a bad
# locale, a path that does not exist, a typo in this pattern) is printed and
# returned as an error, never swallowed as "found nothing": that silent
# swallow is the root cause this whole bug is about.
site_terms_grep() {
    grep -rinE "$SITE_TERMS" "$@"
}

# site_terms_allow
# Reads matching lines on stdin, drops the ones that do not belong here:
#   - `reach: ssh` / `reach=ssh` - the site adapter's own contract value
#     (docs/SITE_ADAPTER.md); a command that helps a user choose between the
#     three `reach` values must be able to name them.
#   - "Relay what they ..." - the verb, in the five commands/*.md openings
#     that tell Claude to relay a script's output; nothing to do with
#     scripts/nf_relay.py.
#   - "relay column output" - skills/operational/SKILL.md's own name for the
#     fenced-code-block rule tests/column_output_relay_rule.sh checks; same
#     verb, same non-issue.
#   - "Remote-SSH" - Positron's own connection feature (a proper noun the
#     editor uses for itself), named so the user knows which of Positron's
#     own settings to reach for. The command layer is not spelling out an
#     ssh invocation here; nothing forks scripts/on_site.sh.
# Reviewed individually, per the assessment's own caution against bulk-
# whitelisting once -i widens what matches.
site_terms_allow() {
    grep -viE 'reach: ?ssh|reach=ssh|relay what they|relay column output|remote-ssh'
}
