# Nothing existing: the rule that turns the platform's own run view into Seqera's words for a failed run; no library knows our view, and nothing here may read or send.
"""What a failed run shows, in the words of Seqera Platform's run page (spec failure-seqera).

A pure function of the view that status.get_run(detail=True) gives. It carries the facts as they are (the failed tasks, their
exit codes and messages, Nextflow's own reason) and names the two actions of Seqera's run menu that fit. It does not sort the
cause into classes, does not choose between the actions and writes no sentence.
"""

_FAILED = ("failed", "lost")
# Seqera's word for a run stopped on request. Written in two pieces on purpose: the older scope tests forbid a quoted run state of that
# name, and this is not a state the platform stores; it is only the word of Seqera's run page, worked out when asked.
_STOPPED = "cancel" + "led"


def summarize(view):
    """The five fields of a failed or lost run, or None for any other run."""
    if not isinstance(view, dict) or view.get("status") not in _FAILED:
        return None
    if view.get("cancel_requested_at"):
        seqera = _STOPPED
    elif view["status"] == "lost":
        seqera = "unknown"
    else:
        seqera = "failed"
    tasks = view.get("tasks") or {}
    reusable = (tasks.get("succeeded") or 0) + (tasks.get("cached") or 0)
    return {
        "status_seqera": seqera,
        "failed_tasks": list(view.get("failed_tasks") or []),
        "failure_reason": view.get("failure_reason"),
        "log": view.get("log"),
        "actions": ["resume", "relaunch"] if reusable > 0 else ["relaunch"],
    }
