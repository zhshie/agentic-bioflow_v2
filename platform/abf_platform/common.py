# Nothing existing: the few functions shared by the receiver and the rebuild (run id, times, secret names, Nextflow's error text) so both paths agree by construction.
"""Shared rules. Both the live receiver and the rebuild call these, so they cannot drift apart."""
import datetime
import hashlib
import re

# Nextflow 26.04.7 sends one message at least every minute while a run is alive
# (research.md: TowerObserver.groovy:60). A run silent for three of them is lost.
HEARTBEAT_SECONDS = 60
LOST_AFTER_SECONDS = 3 * HEARTBEAT_SECONDS

_SECRET = re.compile(r"token|password|secret|key", re.I)


def run_id(session_id, run_name):
    """First 16 hex characters of sha256(sessionId + '/' + runName)."""
    return hashlib.sha256((session_id + "/" + run_name).encode("utf-8")).hexdigest()[:16]


def is_secret_name(name):
    return bool(_SECRET.search(str(name)))


def scrub_params(value):
    """Keep every parameter name; drop the value of the ones whose name looks like a secret (any depth)."""
    if isinstance(value, dict):
        return {k: (None if is_secret_name(k) else scrub_params(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub_params(v) for v in value]
    return value


_ISO = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.\d+)?(Z|[+-]\d\d:\d\d)?$")


def parse_iso_epoch(text):
    """Whole epoch seconds (rounded down) of an ISO 8601 string, nanoseconds allowed; None if it is not one."""
    if not isinstance(text, str):
        return None
    m = _ISO.match(text.strip())
    if not m:
        return None
    tz = m.group(2) or "+00:00"
    if tz == "Z":
        tz = "+00:00"
    try:
        return int(datetime.datetime.fromisoformat(m.group(1) + tz).timestamp())
    except ValueError:
        return None


def epoch_iso(epoch):
    if epoch is None:
        return None
    return datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_PROCESS_ERROR = re.compile(r"Error executing process > '([^']*)'")


def extract_error(text):
    """(task name, message) from Nextflow's 'Error executing process' text, or None.

    The text is either workflow.errorReport of the complete message or the block in
    .nextflow.log. The message is the 'Command error:' section without its indentation;
    when that section is missing, the line under 'Caused by:'.
    """
    if not isinstance(text, str):
        return None
    m = _PROCESS_ERROR.search(text)
    if not m:
        return None
    rest = text[m.end():]
    nxt = _PROCESS_ERROR.search(rest)
    if nxt:
        rest = rest[:nxt.start()]
    name = m.group(1)
    sec = re.search(r"\nCommand error:\n(.*?)(?:\n[ \t]*\nWork dir:|\nWork dir:|\Z)", rest, re.S)
    if sec:
        lines = [ln[2:] if ln.startswith("  ") else ln for ln in sec.group(1).split("\n")]
        message = "\n".join(lines).strip()
    else:
        cause = re.search(r"\nCaused by:\n\s*(.+)", rest)
        message = cause.group(1).strip() if cause else ""
    return name, message
