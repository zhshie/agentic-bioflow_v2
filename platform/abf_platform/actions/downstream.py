# Nothing existing: a thin door onto our own abf_platform.downstream_catalog (spec downstream-method-catalog).
"""The certified downstream method catalogue as an action (list_downstream). Thin: the loading, the grade and the listing are
`abf_platform.downstream_catalog`. Not exported by `actions/__init__`, like `actions.catalogue`. The catalogue is public, shared and
read-only: no caller, no owner filter, nothing is written."""
from .. import downstream_catalog


def list_downstream(pipeline):
    """{pipeline, methods, count, note} for one pipeline. An empty name raises ValueError (a plain sentence saying what to give)."""
    return downstream_catalog.list_downstream(pipeline)
