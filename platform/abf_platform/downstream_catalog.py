# Nothing existing: nf-core and Galaxy publish no allowlist of certified downstream methods; this is our own hand-kept JSON with its schema check.
"""The certified downstream method catalogue: load, check the schema, work out the effective grade, answer list_downstream.

The data is `data/downstream-methods.json` (hand kept; every value comes from a seed file with sources, nothing is guessed: a value that
could not be found is null and the entry's notes say 查不到). Grade A/B/C is set by a person; an entry not reviewed for more than 365
days (calendar days, exactly 365 still counts) is shown one grade lower. Grade C is never listed. Only the standard library; nothing is
written and nothing is fetched.
"""
import json
import re
from datetime import date
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "data" / "downstream-methods.json"
SCHEMA = 1
MAX_AGE_DAYS = 365
KEYS = ("id", "pipeline", "pipeline_version", "method", "link", "doi", "grade", "version_pin", "license", "inputs",
        "non_interactive_plot", "singularity", "reviewed", "notes")
NULLABLE_NEEDS_NOT_FOUND = ("doi", "license", "version_pin", "pipeline_version")
NOT_FOUND = "查不到"
PENDING = "待驗證"
NO_METHODS_NOTE = "no certified downstream methods for this pipeline"
EMPTY_PIPELINE = "pipeline 不能是空的；請給 pipeline 名稱，例如 ampliseq 或 rnaseq (the pipeline name must not be empty; give one such as ampliseq or rnaseq)"
_ID = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*\Z")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_DOWN = {"A": "B", "B": "C", "C": "C"}


def validate(data):
    """Every violation of the schema, as readable lines naming the entry id and the field. An empty list means the data is fine."""
    problems = []
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        return ["schema: the top level must be an object with schema %d" % SCHEMA]
    es = data.get("entries")
    if not isinstance(es, list):
        return ["entries: must be a list"]
    seen = set()
    for i, e in enumerate(es):
        if not isinstance(e, dict):
            problems.append("entry %d: not an object" % i)
            continue
        eid = e.get("id") if isinstance(e.get("id"), str) else "#%d" % i
        for k in KEYS:
            if k not in e:
                problems.append("%s: missing key %s" % (eid, k))
        if "id" in e:
            if not (isinstance(e["id"], str) and _ID.match(e["id"])):
                problems.append("%s: id must be kebab-case" % eid)
            elif e["id"] in seen:
                problems.append("%s: duplicate id" % eid)
            seen.add(e["id"])
        if "pipeline" in e and not (isinstance(e["pipeline"], str) and e["pipeline"]):
            problems.append("%s: pipeline must be a non-empty string" % eid)
        if "grade" in e and e["grade"] not in ("A", "B", "C"):
            problems.append("%s: grade must be A, B or C, not %r" % (eid, e["grade"]))
        if "singularity" in e and e["singularity"] not in ("ok", "untested", "unavailable"):
            problems.append("%s: singularity must be ok, untested or unavailable" % eid)
        if "reviewed" in e:
            r = e["reviewed"]
            ok = isinstance(r, str) and bool(_DATE.match(r))
            if ok:
                try:
                    date.fromisoformat(r)
                except ValueError:
                    ok = False
            if not ok:
                problems.append("%s: reviewed must be a date written YYYY-MM-DD, not %r" % (eid, r))
        notes = e.get("notes")
        if "notes" in e and not isinstance(notes, str):
            problems.append("%s: notes must be a string" % eid)
            notes = ""
        notes = notes or ""
        for k in NULLABLE_NEEDS_NOT_FOUND:
            if k in e and e[k] is None and NOT_FOUND not in notes:
                problems.append("%s: %s is null but notes does not say %s" % (eid, k, NOT_FOUND))
        if "non_interactive_plot" in e:
            v = e["non_interactive_plot"]
            if not (v is True or v is False or v is None or v == "needs_person"):
                problems.append("%s: non_interactive_plot must be true, false, \"needs_person\" or null" % eid)
            elif v is None and PENDING not in notes:
                problems.append("%s: non_interactive_plot is null but notes does not say %s" % (eid, PENDING))
        if "inputs" in e:
            ins = e["inputs"]
            if not isinstance(ins, list):
                problems.append("%s: inputs must be a list" % eid)
            else:
                for x in ins:
                    if not (isinstance(x, dict) and isinstance(x.get("pipeline_output"), str) and x["pipeline_output"]
                            and isinstance(x.get("role"), str) and x["role"]):
                        problems.append("%s: every inputs item needs a pipeline_output and a role" % eid)
                        break
        if e.get("grade") == "A" and not (isinstance(e.get("link"), str) and e["link"].strip()):
            problems.append("%s: link is empty (a grade A entry must not have no link; A 級不得沒有連結)" % eid)
    return problems


def load(path=None):
    """The catalogue as a dict. A broken file raises ValueError naming every violation."""
    data = json.loads(Path(DEFAULT_PATH if path is None else path).read_text(encoding="utf-8"))
    problems = validate(data)
    if problems:
        raise ValueError("downstream catalogue is invalid: " + "; ".join(problems))
    return data


def age_days(entry, today=None):
    """Calendar days from the review date to today (today can be injected)."""
    today = date.today() if today is None else today
    return (today - date.fromisoformat(entry["reviewed"])).days


def effective_grade(entry, today=None):
    """The declared grade, one lower when the review is more than 365 days old. The file is never changed."""
    g = entry["grade"]
    return _DOWN[g] if age_days(entry, today) > MAX_AGE_DAYS else g


def list_downstream(pipeline, today=None, path=None):
    """{pipeline, methods, count, note}: the methods of one pipeline whose effective grade is A or B, A first, then by method name.
    An unknown pipeline is an empty answer, not an error and not a guess; an empty name raises ValueError."""
    if not isinstance(pipeline, str) or not pipeline.strip():
        raise ValueError(EMPTY_PIPELINE)
    name = pipeline.strip()
    today = date.today() if today is None else today
    rows = []
    for e in load(path)["entries"]:
        if e["pipeline"] != name:
            continue
        g = effective_grade(e, today)
        if g == "C":
            continue
        rows.append({"id": e["id"], "method": e["method"], "link": e["link"], "grade": g, "declared_grade": e["grade"],
                     "downgraded": g != e["grade"], "version_pin": e["version_pin"], "license": e["license"], "doi": e["doi"],
                     "inputs": e["inputs"], "non_interactive_plot": e["non_interactive_plot"], "singularity": e["singularity"],
                     "reviewed": e["reviewed"], "notes": e["notes"]})
    rows.sort(key=lambda r: (r["grade"], r["method"]))
    out = {"pipeline": name, "methods": rows, "count": len(rows), "note": ""}
    if not rows:
        out["note"] = NO_METHODS_NOTE
    else:
        out["note"] = ("Certified methods only, A before B; grade C is not listed. non_interactive_plot needs_person means a person "
                       "must operate it; null means not yet verified; singularity untested means not run on nano4. Nothing was run.")
    return out
