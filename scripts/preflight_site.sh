#!/bin/bash
# The three questions preflight.sh asks only the site, answered in ONE call.
# Nothing existing: Seqera and nf-core have no notion of this site's relay, outputs reader or resource contract, so only the three scripts this plugin ships can answer; this just frames their answers so one ssh session carries all three.
#
# Under reach: ssh every on_site.sh --script is one ssh session, and a site that
# has run out of sessions hangs rather than fails (docs/PITFALLS.md 16e), so
# preflight.sh ships this script once instead of shipping egress_ctl.sh,
# agent_ctl.sh and check_resource_contract.sh one by one (issue #13, item 3).
#
# It decides nothing and changes nothing. It runs the three in order, each one
# regardless of how the one before it ended, and frames each answer:
#
#   @@preflight-begin <name>
#   <the script's stdout and stderr, as written>
#   @@preflight-end <name> rc=<its exit code>
#
# so preflight.sh can apply exactly the judgements it always applied. A content
# line that itself begins with "@@" is written with one more "@" in front, and
# preflight.sh takes it off again: a marker line therefore always starts "@@"
# followed by "p", and nothing a script prints can pass for one.
#
# Exit 0 always - a failing check is reported in its rc, not here.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

section() {
  local name="$1" out rc; shift
  out=$("$@" 2>&1); rc=$?
  printf '@@preflight-begin %s\n' "$name"
  [ -n "$out" ] && printf '%s\n' "$out" | sed 's/^@@/@@@/'
  printf '@@preflight-end %s rc=%s\n' "$name" "$rc"
}

section egress    bash "$HERE/egress_ctl.sh" status
section agent     bash "$HERE/agent_ctl.sh" status
section resources bash "$HERE/check_resource_contract.sh"
exit 0
