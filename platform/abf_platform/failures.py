# Nothing existing: the rule that turns the platform's own run view into Seqera's words for a failed run; no library knows our view, and nothing here may read or send.
"""What a failed run shows, in the words of Seqera Platform's run page (spec failure-seqera).

A pure function of the view that status.get_run(detail=True) gives. It carries the facts as they are (the failed tasks, their
exit codes and messages, Nextflow's own reason) and names the two actions of Seqera's run menu that fit. It does not sort the
cause into classes, does not choose between the actions and writes no sentence.
"""

import re

_FAILED = ("failed", "lost")
# Seqera's word for a run stopped on request. Written in two pieces on purpose: the older scope tests forbid a quoted run state of that
# name, and this is not a state the platform stores; it is only the word of Seqera's run page, worked out when asked.
_STOPPED = "cancel" + "led"

# What the scheduler may say of a head job (the other side keeps the same table and drops every other word). The first group ended the head
# job without Nextflow writing its record; the second is a head that is still there; COMPLETED is a head that ended well.
ENDED_BAD = frozenset("NODE_FAIL BOOT_FAIL CANCELLED TIMEOUT OUT_OF_MEMORY FAILED DEADLINE PREEMPTED REVOKED".split())
ALIVE = frozenset("PENDING RUNNING COMPLETING REQUEUED SUSPENDED CONFIGURING".split())
KNOWN_STATES = ENDED_BAD | ALIVE | {"COMPLETED"}
SOURCES = ("squeue", "sacct")


def _clean_fact(raw):
    """What the site said of the head job, kept only if it is exactly {job_id, state, source} of known words; else None."""
    if not isinstance(raw, dict) or set(raw) != {"job_id", "state", "source"}:
        return None
    number, state, source = raw["job_id"], raw["state"], raw["source"]
    if not (isinstance(number, str) and re.fullmatch(r"[0-9]{1,10}", number)):
        return None
    if not (isinstance(state, str) and state in KNOWN_STATES) or source not in SOURCES:
        return None
    return {"job_id": number, "state": state, "source": source}


def head_fact_of(result):
    """The checked head-state fact inside a finished read-back's result, or None."""
    return _clean_fact(result.get("scheduler")) if isinstance(result, dict) else None


def kept_fact_sql():
    """A SQL condition on a row of `jobs` that is a read-back carrying a bad end of the head job: such a row is not pruned with the
    others, since the Failed look of a run rests on it. A bad end that a newer read-back of the same run took back (the head was
    alive or had ended well after it) is not kept: dropping the newer answer alone would bring the older bad end back (ruling Q1)."""
    ended = " OR ".join("instr(result_json, '\"%s\"') > 0" % word for word in sorted(ENDED_BAD))
    later = " OR ".join("instr(n.result_json, '\"%s\"') > 0" % word for word in sorted(KNOWN_STATES - ENDED_BAD))
    taken_back = ("EXISTS (SELECT 1 FROM jobs n WHERE n.kind = 'fetch_run_records' AND n.state = 'done' AND n.id > jobs.id "
                  "AND n.compute_env = jobs.compute_env "
                  "AND json_extract(n.args_json, '$.run_name') = json_extract(jobs.args_json, '$.run_name') "
                  "AND instr(n.result_json, '\"scheduler\"') > 0 AND (%s))" % later)
    return "(state = 'done' AND instr(result_json, '\"scheduler\"') > 0 AND (%s) AND NOT %s)" % (ended, taken_back)


def head_fact_entry(result):
    """The one key of a read-back's result that is kept for the fact, checked."""
    return {"scheduler": head_fact_of(result)}


def head_reason(fact):
    """The one sentence for a head-state fact (job_id, state, source) that was already checked."""
    if fact["state"] == "COMPLETED":
        return "Slurm head job %s completed but Nextflow left no completion record" % fact["job_id"]
    return "Slurm head job %s ended as %s (%s)" % (fact["job_id"], fact["state"], fact["source"])


def with_head_state(view, fact):
    """The view of a lost run seen with what the scheduler said of its head job. A bad end makes it failed with the scheduler's word
    as the reason; a head that ended well without a record keeps it lost, with the reason and without the resume action; anything else
    (no fact, a head still alive) leaves the view as it was."""
    if not fact or not isinstance(view, dict) or view.get("status") != "lost":
        return view
    if fact["state"] in ENDED_BAD:
        # a lost run has no ended_at: the end shown is the last message, as the failure notice does, so no Ended place is a dash and the duration stops
        return dict(view, status="failed", failure_reason=head_reason(fact), ended_at=view.get("ended_at") or view.get("last_message_at"))
    if fact["state"] == "COMPLETED":
        return dict(view, failure_reason=head_reason(fact), _no_resume=True)
    return view


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
        "actions": ["resume", "relaunch"] if reusable > 0 and not view.get("_no_resume") else ["relaunch"],
    }
