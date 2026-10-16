# Nothing existing: Seqera's launch button and Tower Agent are closed, and no queue library knows a "yes" that is bound to the hash of what was shown; this is the one function that writes one.
"""The user's "yes" to a launch or a cancel, written in the same transaction as the job it allows (feature 007b).

Only the action layer (abf_platform/actions) calls this module, and until the confirmation page (009c) it does so only for
the terminal commands (abf_launch), after the person answered y at the question. No HTTP route, no MCP tool and no other
module imports it (tests/test_actions_layer.py checks the imports). The
confirmation row holds the hash of the canonical content that was shown (common.bundle_sha256); jobs.py refuses to
queue a launch or a cancel for any content whose hash is not in an unspent row of the right kind.
"""
import secrets
import time

from . import common, jobs


def _confirm(state_path, ce_name, kind, job_kind, bundle, clock, deadline_seconds, offline_after, caller_user_id):
    now = clock()
    seconds = jobs._seconds(job_kind, deadline_seconds)
    cid = secrets.token_hex(16)

    def work(con):
        con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, caller_user_id) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (cid, common.bundle_sha256(bundle), kind, now, caller_user_id))
        return cid, jobs.enqueue_confirmed(con, ce_name, job_kind, bundle, cid, now, seconds, offline_after)

    return jobs.transaction(state_path, work)


def confirm_launch(state_path, ce_name, bundle, clock=time.time, deadline_seconds=None, offline_after=None,
                   caller_user_id=None):
    """Write the confirmation and queue the launch, or neither (JobRefused). Returns (confirmation id, job id)."""
    return _confirm(state_path, ce_name, "launch", "launch_nextflow", bundle, clock, deadline_seconds, offline_after,
                    caller_user_id)


def confirm_cancel(state_path, ce_name, bundle, clock=time.time, deadline_seconds=None, offline_after=None,
                   caller_user_id=None):
    return _confirm(state_path, ce_name, "cancel", "cancel_run", bundle, clock, deadline_seconds, offline_after,
                    caller_user_id)
