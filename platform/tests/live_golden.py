# Nothing existing: the pages whose bytes live-sync must not change; the scenario is ours (specs/live-sync/ledger.md, TC-063).
"""The pages of TC-063, built the same way by any version of the platform: fixed run names, fixed times, fixed clock. `digests(...)` is the sha256 (first 16 hex
digits) of each page with the per-login form tokens masked.

The golden values in test_web_live_sync.py were made by running this file against the code of origin/v3 BEFORE live-sync (see the ledger for the command), never
by the code of this branch. The test strips the three additions of live-sync from the pages of this branch and compares."""
import hashlib
import re
import time

FIXED = 1_800_000_000
HOUR = 3600


def mask(text):
    return re.sub(r'value="[0-9a-f]{64}"', 'value=""', text)


def digest(text):
    return hashlib.sha256(mask(text).encode("utf-8")).hexdigest()[:16]


def board_digests(w):
    """The board in its stages, and the empty board: {name: digest}."""
    from test_web_board import login, seed
    w.clock.t = FIXED
    ann, zed = w.user("ann"), w.user("zed")
    bad = seed(w, "g-bad", "failed", ann, started=FIXED - 5 * HOUR, ended=FIXED - 4 * HOUR, counts=dict(succeeded=1, failed=1), reason="boom")
    ok = seed(w, "g-ok", "succeeded", ann, started=FIXED - 3 * HOUR, ended=FIXED - 2 * HOUR, counts=dict(succeeded=4))
    import sqlite3
    con = sqlite3.connect(str(w.ip.state_db))
    with con:      # the time the launch was sent is shown on the finished stage: it must not be the time of the run of this scenario
        con.execute("UPDATE launches SET confirmed_at = ?", (FIXED - 6 * HOUR,))
    con.close()
    c, cz = login(w, "ann"), login(w, "zed")
    urls = {"board": "/", "running stage": "/?run=%s&stage=running" % bad, "results stage": "/?run=%s" % ok, "outputs tab": "/?run=%s&stage=results&tab=outputs" % ok,
            "finished stage": "/?run=%s&stage=finished" % ok, "english board": "/?lang=en"}
    out = {name: digest(c.get(url).text) for name, url in urls.items()}
    out["empty board"] = digest(cz.get("/").text)
    return out


def launch_digests(tmp_path, monkeypatch):
    """The launch page while the site is being asked (loading), and the same page with nothing asked: {name: digest}."""
    from test_web_guided_launch import SEL, Rig, ready
    from test_web_guided_launch_2 import Fake, loading_files
    from abf_platform import actions
    f = Fake()
    f.files = loading_files()
    monkeypatch.setattr(actions, "pipeline_files", f.pipeline_files)
    monkeypatch.setattr(actions, "latest_release", f.latest_release)
    rig = Rig(tmp_path, monkeypatch)
    _, c = ready(rig)
    return {"launch loading": digest(c.get(SEL).text), "launch plain": digest(c.get("/launch").text)}
