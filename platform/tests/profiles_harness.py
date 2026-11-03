# Nothing existing: glue for test_launch_profiles.py (a World whose environment has the eight nano4 pipelines installed and a pre-use check that read their Config profile names); no library plays that site.
"""Helpers for the launch-test-profile tests: the eight pipelines, the profile names the site read, one MCP launch, and a count of everything written."""
import json
import time

EIGHT = [("nf-core/ampliseq", "2.18.0"), ("nf-core/rnaseq", "3.26.0"), ("nf-core/sarek", "3.9.0"), ("nf-core/scrnaseq", "4.2.0"),
         ("nf-core/atacseq", "2.1.2"), ("nf-core/crisprseq", "2.3.0"), ("nf-core/nanoseq", "3.1.0"), ("nf-core/proteinfold", "2.0.0")]
NAMES = ["test", "test_full", "docker", "singularity", "conda", "test_custom"]


def entries():
    return [{"pipeline": p, "revision": r, "module": "biology/%s/%s" % (p.replace("nf-core/", "nf-core-"), r),
             "home": "NFCORE_%s_HOME" % p.split("/")[1].upper()} for p, r in EIGHT]


def profiles_map(names=None):
    return {"%s %s" % (p, r): list(NAMES if names is None else names) for p, r in EIGHT}


def install_eight(w, ce="lab-a"):
    """The environment names the eight pipelines as installed (the settings page's own storage)."""
    cfg = json.loads(w.sql("SELECT config_json FROM compute_envs WHERE name = ?", (ce,))[0][0])
    cfg["sitePipelines"] = entries()
    cfg["siteConfigVars"] = ["NFCORE_SITE_CONFIG"]      # the site's own config file, which a profile must only be added to
    import sqlite3
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET config_json = ? WHERE name = ?", (json.dumps(cfg, sort_keys=True), ce))
    con.close()


def feed(w, site_profiles, ce="lab-a", inventory=None):
    """A pre-use check answered by the agent, through the platform's own claim and take_result (so the result is cleaned as it really is)."""
    from abf_platform import jobs
    agent = w.sql("SELECT agent FROM compute_envs WHERE name = ?", (ce,))[0][0]
    w._tick = getattr(w, "_tick", 0) + 3
    t = time.time() + w._tick
    jid = jobs.enqueue_preflight(w.ip.state_db, ce, lambda: t)
    got = jobs.claim(w.ip.state_db, agent, lambda: t)
    assert got and got["id"] == jid
    result = {"ok": True, "checks": [{"name": "connect", "status": "pass", "detail": "the site answers"}]}
    if site_profiles is not None:
        result["site_profiles"] = site_profiles
    if inventory is not None:
        result["site_inventory"] = inventory
    status, body = jobs.take_result(w.ip.state_db, agent, jid, "done", result, lambda: t + 1)
    assert status == 200 and body["accepted"] is True
    return jid


def tables(w):
    """Row counts of every table, the file names and sizes under the data folder: what a refusal must leave exactly as it was."""
    import sqlite3
    from pathlib import Path
    con = sqlite3.connect(str(w.ip.state_db))
    try:
        names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
        counts = {n: con.execute('SELECT COUNT(*) FROM "%s"' % n).fetchone()[0] for n in names}
    finally:
        con.close()
    root = Path(w.ip.state_db).parent
    tree = sorted((str(p.relative_to(root)), p.stat().st_size) for p in root.rglob("*") if p.is_file() and not p.name.endswith(("-wal", "-shm", "-journal")))
    return counts, tree


def args_of(profiles=None, sheet=None, pipeline="nf-core/ampliseq", revision="2.18.0", run="run-one", **over):
    a = {"pipeline": pipeline, "revision": revision, "run_name": run, "ce_name": "lab-a", "params": {}}
    if profiles is not None:
        a["profiles"] = profiles
    if sheet is not None:
        a["samplesheet"] = str(sheet)
    a.update(over)
    return a


def ask(w, caller, profiles=None, sheet=None, answer=None, **over):
    from helpers import tool_json
    return tool_json(w.call("launch", args_of(profiles, sheet, **over), caller=caller, answer=answer))
