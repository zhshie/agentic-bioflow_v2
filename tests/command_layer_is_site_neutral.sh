#!/bin/bash
# Invariant 4: one cluster is not the world.
#
# The command layer says what needs to be found out; the site adapter knows how
# to find it out. A command that runs `squeue` or greps a proxy log is a command
# that only works in one building - on a cloud compute environment there is no
# scheduler to ask and no proxy to have refused anything.
#
# This is a vocabulary check, which is crude but catches the thing that actually
# happens: someone pastes a working diagnostic inline because it is right there
# in their terminal. If a term below genuinely belongs in the command layer,
# that is a design decision worth arguing for - see docs/SITE_ADAPTER.md.
#
# hooks/ is deliberately NOT scanned. The safety net is allowed to be broader
# than the abstraction: the launch gate triggers on `sbatch` because a run
# started that way still needs confirming, and the deletion guard names the
# directories this deployment must never lose. Both are correct, and both would
# fail this check.
#
# skills/ IS scanned, alongside commands/: skills/operational/SKILL.md is the
# same operational knowledge reachable without a slash command
# (CLAUDE.md, "Repository layout"), so it is bound by the same neutrality this
# check exists to hold commands/*.md to.
#
# The term list and the `reach: ssh` exemption live in tests/lib/site_terms.sh,
# shared with tests/launch_provenance_test.sh so the two cannot drift apart
# (bug: false-green-tests, item 1).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
. "$HERE/lib/site_terms.sh"

raw=$(site_terms_grep "$ROOT/commands" "$ROOT/skills" 2>&1)
rc=$?
if [ "$rc" -ge 2 ]; then
    printf '%s\n' "$raw"
    echo
    echo "FAIL: the site-term scan itself errored (grep exit $rc) - a broken scan is not a clean pass."
    exit 1
fi

# The exemptions are phrases, not lines (#30 review): a line that holds an
# exempt phrase AND a real term must still be reported. Checked here on
# synthetic lines so the rule cannot quietly go back to line-level.
selftest=$(printf '%s\n' \
    'C:/x/commands/a.md:3:Relay what they say, then sbatch it.' \
    'commands/b.md:7:Use Remote-SSH and run squeue' \
    'commands/c.md:9:reach: ssh, then use rsync' \
    'commands/d.md:1:Relay what they print, verbatim.' \
    'commands/e.md:2:set reach: ssh in the settings' | site_terms_allow)
want='C:/x/commands/a.md:3:Relay what they say, then sbatch it.
commands/b.md:7:Use Remote-SSH and run squeue
commands/c.md:9:reach: ssh, then use rsync'
if [ "$selftest" != "$want" ]; then
    echo "FAIL: site_terms_allow exempts whole lines, not phrases. Got:"
    printf '%s\n' "$selftest"
    exit 1
fi

hits=$(printf '%s\n' "$raw" | site_terms_allow | sed "s|^$ROOT/||" | grep -v '^$')

# Second scan (constitution-checks, item 3): the adapter's IMPLEMENTATION and
# the relay's own parts. Constitution II.4 says the command layer MUST NOT name
# a scheduler, partition, queue or relay, and a site adapter supplies the site
# properties. Two different things were slipping past the vocabulary above:
#
#   - A specific site's name or implementation file: `configs/sites/nchc.config`
#     in commands/downstream.md. A second site has no such file; the adapter
#     contract (docs/SITE_ADAPTER.md, 1) already has a neutral name for it,
#     "the site's resource-floor config".
#   - The relay's own parts: nf_relay.py, its denied-names list, its port
#     setting, a login-node host name.
#
# What is deliberately NOT banned: the contract-noun scripts the commands call
# through `scripts/on_site.sh --script` - egress_ctl.sh, egress_allow.sh,
# check_egress.py (contract 2, egress), why_pending.sh (contract 5),
# agent_ctl.sh (contract 3). They are named for what they are in the adapter
# contract, not for the relay or scheduler behind them, they are reached only
# through the adapter's one sanctioned transport, and the prose around them
# says "the outbound channel". Naming the sanctioned interface is how the
# command layer asks; naming the proxy behind it would be naming a relay.
ADAPTER_IMPL_TERMS='nchc|taiwania|configs/sites|nf_relay|relay_denied|relay_port|(^|[^[:alnum:]_])lgn[0-9]'
impl_hits=$(grep -rinE "$ADAPTER_IMPL_TERMS" "$ROOT/commands" "$ROOT/skills" 2>&1)
irc=$?
if [ "$irc" -ge 2 ]; then
    printf '%s\n' "$impl_hits"
    echo "FAIL: the adapter-implementation scan itself errored (grep exit $irc)"
    exit 1
fi
impl_hits=$(printf '%s\n' "$impl_hits" | sed "s|^$ROOT/||" | grep -v '^$')
if [ -n "$impl_hits" ]; then
    printf '%s\n' "$impl_hits"
    echo
    echo "FAIL: the command layer names a site or the relay's own parts (II.4). Say what the adapter supplies, not which file or host supplies it here."
    exit 1
fi

if [ -n "$hits" ]; then
    printf '%s\n' "$hits"
    echo
    echo "FAIL: the command layer names site machinery. Move it behind the adapter."
    exit 1
fi
echo "OK: commands/ and skills/ name no scheduler, no egress mechanism, no container runtime"
