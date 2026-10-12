# Nothing existing: the few functions shared by the receiver and the rebuild (run id, times, secret names, Nextflow's error text) so both paths agree by construction.
"""Shared rules. Both the live receiver and the rebuild call these, so they cannot drift apart."""
import base64
import datetime
import hashlib
import json
import os
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


_ISO = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.\d+)?(Z|[+-]\d\d:\d\d)?\Z")


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


# ---- agents and jobs (feature 007) --------------------------------------------------
# An agent sends a beat every AGENT_HEARTBEAT_SECONDS and holds each poll for AGENT_POLL_SECONDS.
# It is offline when its last contact is older than three beats. docs/PLATFORM.md states the same
# numbers; the environment variables only exist so the tests can shorten them.
AGENT_HEARTBEAT_SECONDS = 20
AGENT_POLL_SECONDS = 25
AGENT_OFFLINE_AFTER_BEATS = 3


def _seconds_from_env(name, default):
    raw = os.environ.get(name)
    try:
        value = float(raw) if raw not in (None, "") else float(default)
    except ValueError:
        value = float(default)
    return value if value > 0 else float(default)


def heartbeat_seconds():
    """ABF_AGENT_HEARTBEAT_SECONDS, else 20."""
    return _seconds_from_env("ABF_AGENT_HEARTBEAT_SECONDS", AGENT_HEARTBEAT_SECONDS)


def poll_seconds():
    """ABF_AGENT_POLL_SECONDS, else 25."""
    return _seconds_from_env("ABF_AGENT_POLL_SECONDS", AGENT_POLL_SECONDS)


def offline_after_seconds():
    return AGENT_OFFLINE_AFTER_BEATS * heartbeat_seconds()


def epoch_iso_ms(epoch):
    """ISO 8601 UTC with milliseconds, the form Seqera uses for its dates."""
    if epoch is None:
        return None
    dt = datetime.datetime.fromtimestamp(float(epoch), datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (dt.microsecond // 1000)


def token_from_header(value):
    """Bearer <token>, or Basic base64('@token:<token>') as Nextflow sends it."""
    if not value:
        return None
    scheme, _, cred = value.strip().partition(" ")
    cred = cred.strip()
    if scheme.lower() == "bearer":
        return cred or None
    if scheme.lower() == "basic":
        try:
            decoded = base64.b64decode(cred, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return None
        user, _, password = decoded.partition(":")
        return password if user == "@token" and password else None
    return None


# ---- launch and cancel (feature 007b) ---------------------------------------------------------------
# The confirmation binds a hash of the exact content the user saw. The terminal command, the platform's queue and the agent all
# compute it with this one function, so they cannot disagree about what "the same content" means.

def canonical_json(obj):
    """The bytes the hash is taken over: keys sorted, no spaces, UTF-8 as is."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def bundle_sha256(bundle):
    return hashlib.sha256(canonical_json(bundle)).hexdigest()


# What an agent may tell the platform about itself in hello: the facts a launch screen has to show and a bundle is built from.
# None of them is a credential; each is bounded, and a value of the wrong type is dropped. The platform stores them with this
# function and the agent builds the same shape with it, so the two sides compare like with like.
FACT_TEXT = {"slurm_account": 64, "reach": 16, "endpoint": 300, "forward_file": 1100, "storage_root": 1100}
FACT_FLAGS = ("platform_local",)


def clean_facts(facts):
    """The facts of a hello, each as text/boolean/None within its bound; None when there were no facts at all."""
    if not isinstance(facts, dict):
        return None
    out = {}
    for key, limit in FACT_TEXT.items():
        v = facts.get(key)
        out[key] = v if isinstance(v, str) and 0 < len(v) <= limit else None
    for key in FACT_FLAGS:
        v = facts.get(key)
        out[key] = v if isinstance(v, bool) else None
    return out
