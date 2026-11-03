"""PR #280 (platform/abf_station/launch.py:_user_limits/_resource_limits_line): the user's own resourceLimits line is read by a
one-line regex and merged into the single global `process.resourceLimits` the platform appends. Fact the merge relies on:
a line that contains `resourceLimits = [...]` is a GLOBAL process limit. Refute it with scoped uses.
Run: python3 -I docs/reports/audit-2026-11/02_resource_limits_scope_hoist.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "platform"))
from abf_station import launch as L

cases = {
 "global (control)":  "process.resourceLimits = [cpus: 2]",
 "inside withName":   "process {\n  withName: 'BIGJOB' {\n    resourceLimits = [cpus: 2, memory: 4.GB]\n  }\n}",
 "inside a profile":  "profiles {\n  small {\n    process.resourceLimits = [cpus: 2, memory: 4.GB]\n  }\n}",
}
for label, cfg in cases.items():
    ce = {"name": "e", "maxvCpus": 64, "maxMemoryGB": 256, "nextflowConfig": cfg}
    print("%-18s -> %s" % (label, L._resource_limits_line(ce)))
