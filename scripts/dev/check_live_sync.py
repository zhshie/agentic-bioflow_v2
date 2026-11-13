#!/usr/bin/env python3
# Nothing existing: Playwright only drives the browser; what is checked (the browser cases of specs/live-sync/test-case.md) and the pass/fail line are this platform's own (pytest cannot hold it: CI has no Chromium and a skip would hide the gap).
"""Browser checks of live-sync: TC-001, 004, 005, 006, 007, 008, 009, 011, 014, 017, 018, 019, 032, 034, 035 and 040 of specs/live-sync/test-case.md.

A standalone script, not a pytest test: it never skips quietly. It starts a throwaway platform on a data folder under /tmp, seeds it, drives Chromium
against it and stops it. Nothing reaches a site: the answers of the "agent" are rows written into the throwaway database.

  python scripts/dev/check_live_sync.py --platform-python ~/abf-venv/bin/python
  python scripts/dev/check_live_sync.py --only TC-001,TC-004 --chromium-path /usr/bin/chromium

Needs: pip install playwright (and a Chromium: python -m playwright install chromium, or --chromium-path / $CHROME_PATH), and a Python that has abf_platform
installed (--platform-python, default: this one) to run the platform and to seed it. A full run takes about six minutes (it waits 35 s for the page-reload cases,
60 s for the request log, and a minute for the back-off).

Exit 0 = every selected case passed, 1 = at least one failed, 2 = bad arguments, 3 = playwright / Chromium / the platform could not be started (nothing was checked)."""
import argparse
import base64
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ui_check import free_port  # noqa: E402  (one helper, not two copies)

USER, PASSWORD = "alice", "correct horse battery"
CASES = ["TC-001", "TC-004", "TC-005", "TC-006", "TC-007", "TC-008", "TC-009", "TC-011", "TC-014", "TC-017", "TC-018", "TC-019", "TC-032", "TC-034", "TC-035", "TC-040"]
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000000020001e221bc330000000049454e44ae426082")
SCHEMA = json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "t", "type": "object",
                     "$defs": {"opts": {"title": "Options", "type": "object", "properties": {
                         "trunclenf": {"type": "integer", "default": 0, "description": "Truncate forward reads"},
                         "skip_qiime": {"type": "boolean", "default": False, "description": "Skip the QIIME step"}}}},
                     "allOf": [{"$ref": "#/$defs/opts"}]})
TAGS = "0123456789abcdef0123456789abcdef01234567\trefs/tags/2.18.0\n"

SEED = r'''
import asyncio, base64, json, os, sqlite3, time
from pathlib import Path
from abf_platform import actions, agents, jobs, store
db = os.environ["ABF_PLATFORM_DB"]
state = str(Path(db).parent / "platform.db")
tokens = store.default_tokens_path()
store.set_web_password(tokens, "alice", "correct horse battery")
uid = store.user_id_of(tokens, "alice")
con = sqlite3.connect(state)
with con:
    con.execute("UPDATE compute_envs SET status = 'available', checked_ok = 1 WHERE name = 'lab-a'")
con.close()
agents.register(state, "agent-t", "0.1.0", time.time, facts={"slurm_account": "ACCT", "reach": "local", "platform_local": True, "endpoint": "http://127.0.0.1:8787",
                                                            "forward_file": None, "storage_root": "/data/storage"}, owner_user_id=uid)
now = int(time.time())
ix = store.connect_index(db)
with ix:
    for name, final in (("live-run", None), ("live-1", None), ("live-2", None), ("live-3", None), ("live-ok", "succeeded"), ("live-file", "succeeded")):
        ix.execute("INSERT INTO runs (id, session_id, run_name, final_status, started_at, ended_at, last_message_at, n_succeeded, n_running) VALUES (?,?,?,?,?,?,?,?,?)",
                   ("id-" + name, "s-" + name, name, final, now - 3600, (now - 3500) if final else None, now - 3500 if final else now, 4 if final else 1, 0 if final else 2))
ix.close()
st = store.connect_state(state)
with st:
    for name in ("live-run", "live-1", "live-2", "live-3", "live-ok", "live-file"):
        st.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?,?,?,?,?,?)", (name, "/f/" + name, "lab-a", "agent-t", time.time(), uid))
st.close()
for name in ("live-run", "live-1", "live-2", "live-3", "live-ok", "live-file"):      # the listing of every run is answered already: the page that a flip to succeeded makes needs no new ask
    path = "/f/%s/results" % name
    job = jobs.enqueue_listing(state, "lab-a", path, time.time, caller_user_id=uid)
    con = sqlite3.connect(state)
    with con:
        con.execute("UPDATE jobs SET state = 'done', finished_at = ?, result_json = ? WHERE id = ?",
                    (time.time(), json.dumps({"ok": True, "path": path, "entries": [{"name": "a.txt", "type": "file", "size": 3, "modified": "2026-10-20T08:00:00Z"}], "count": 1}), job))
    con.close()
'''

PUBLISH = r'''
import asyncio, base64, os, sys, time
from pathlib import Path
from abf_platform import actions, store
db = os.environ["ABF_PLATFORM_DB"]
state = str(Path(db).parent / "platform.db")
tokens = store.default_tokens_path()
uid = store.user_id_of(tokens, "alice")
caller = actions.Caller(uid, "alice", "lab-x")
figs = [{"filename": n, "content_base64": base64.b64encode(bytes.fromhex(os.environ["PNG"])).decode(), "code": "print(1)\n", "params": "k=1"} for n in sys.argv[1:]]
got = asyncio.run(actions.request_publish_figure(state, run_id="id-live-ok", figures=figs, caller=caller, clock=time.time, index_path=db))
actions.approve(state, got["request_id"], confirmed_by=actions.PAGE, caller=caller, clock=time.time)
'''


def parse(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--platform-python", default=sys.executable, help="a Python that has abf_platform installed (runs and seeds the platform)")
    ap.add_argument("--chromium-path", default=os.environ.get("CHROME_PATH") or None, help="Chrome/Chromium to drive instead of Playwright's own download")
    ap.add_argument("--only", help="comma list of cases, e.g. TC-001,TC-004 (default: all %d)" % len(CASES))
    ap.add_argument("--out", help="folder for screenshots of failed cases (default $TMPDIR/check-live-sync/)")
    a = ap.parse_args(argv)
    a.only = [c.strip().upper() for c in a.only.split(",")] if a.only else list(CASES)
    bad = [c for c in a.only if c not in CASES]
    if bad:
        ap.error("unknown case %s (choose from %s)" % (",".join(bad), ",".join(CASES)))
    return a




class Platform:
    def __init__(self, python, tmp):
        self.python, self.tmp = python, Path(tmp)
        self.db = self.tmp / "data" / "index.db"
        self.state = self.tmp / "data" / "platform.db"
        self.env = dict(os.environ, ABF_PLATFORM_DB=str(self.db), ABF_AGENT_HEARTBEAT_SECONDS="3600", ABF_PLATFORM_DEADLINE_PIPELINE_FILES="3600",
                        ABF_PLATFORM_DEADLINE_READ_RUN_FILE="3600",
                        PYTHONPATH=os.pathsep.join(x for x in (str(Path(__file__).resolve().parents[2] / "platform"), os.environ.get("PYTHONPATH", "")) if x))      # this checkout's platform, not an installed copy
        self.proc = None

    def run(self, *args, code=None):
        cmd = [self.python] + (["-c", code] if code else ["-m", "abf_platform"]) + list(args)
        done = subprocess.run(cmd, env=self.env, capture_output=True, text=True)
        if done.returncode != 0:
            raise RuntimeError("%s failed: %s" % (" ".join(cmd[:4]), (done.stderr or done.stdout)[-600:]))
        return done.stdout

    def start(self):
        (self.tmp / "data").mkdir(parents=True)
        for cmd in (["user", "add", USER, "--lab", "lab-x"],
                    ["ce", "create", "--name", "lab-a", "--platform", "slurm-platform", "--agent", "agent-t", "--work-dir", "/data/w", "--launch-dir", "/data/l",
                     "--head-queue", "normal", "--head-job-options", "-A ACCT -c 4"]):
            self.run(*cmd)
        self.run(code=SEED)
        port = free_port()
        log = open(self.tmp / "web.log", "w")
        self.proc = subprocess.Popen([self.python, "-m", "abf_platform", "web", "--port", str(port)], env=self.env, stdout=log, stderr=subprocess.STDOUT)
        self.base = "http://127.0.0.1:%d" % port
        for _ in range(150):
            try:
                if urllib.request.urlopen(self.base + "/login", timeout=2).status == 200:
                    return
            except Exception:
                time.sleep(0.2)
        raise RuntimeError("the platform did not come up, see %s" % (self.tmp / "web.log"))

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def sql(self, which, stmt, args=()):
        con = sqlite3.connect(str(self.db if which == "index" else self.state if which == "state" else self.tmp / "data" / "tokens.db"), timeout=10)
        try:
            with con:
                return con.execute(stmt, args).fetchall()
        finally:
            con.close()

    def finish_run(self, name):
        self.sql("index", "UPDATE runs SET final_status = 'succeeded', ended_at = ?, last_message_at = ? WHERE run_name = ?", (int(time.time()), int(time.time()), name))

    def keep_alive(self):
        self.sql("index", "UPDATE runs SET last_message_at = ? WHERE final_status IS NULL", (int(time.time()),))

    def answer_pipeline_files(self):
        """The agent answers every waiting pipeline_files job: the schema, and the tags."""
        for jid, args in self.sql("state", "SELECT id, args_json FROM jobs WHERE kind = 'pipeline_files' AND state IN ('queued', 'claimed')"):
            parts = json.loads(args)["parts"]
            if parts == ["tags"]:
                result = {"ok": True, "parts": {"tags": {"status": "ok", "text": TAGS}}}
            else:
                result = {"ok": True, "parts": {p: ({"status": "ok", "text": SCHEMA} if p == "schema" else {"status": "none"}) for p in parts}}
            self.sql("state", "UPDATE jobs SET state = 'done', finished_at = ?, result_json = ? WHERE id = ?", (time.time(), json.dumps(result), jid))

    def answer_file(self, data=b"abc"):
        for jid, in self.sql("state", "SELECT id FROM jobs WHERE kind = 'read_run_file' AND state IN ('queued', 'claimed')"):
            result = {"ok": True, "status": "ok", "name": "a.txt", "size": len(data), "b64": base64.b64encode(data).decode()}
            self.sql("state", "UPDATE jobs SET state = 'done', finished_at = ?, result_json = ? WHERE id = ?", (time.time(), json.dumps(result), jid))

    def publish(self, *names):
        env = dict(self.env, PNG=PNG.hex())
        done = subprocess.run([self.python, "-c", PUBLISH] + list(names), env=env, capture_output=True, text=True)
        if done.returncode != 0:
            raise RuntimeError("publish failed: " + (done.stderr or done.stdout)[-600:])

    def end_sessions(self):
        self.sql("tokens", "DELETE FROM web_sessions")


class Watch:
    """The page loads and the requests of one page, as the browser reports them."""

    def __init__(self, page, base):
        self.loads, self.requests, self.base = 0, [], base
        page.on("load", lambda *_: setattr(self, "loads", self.loads + 1))
        page.on("request", lambda r: self.requests.append((time.monotonic(), r.method, r.url)))

    def live(self, kind="version"):
        return [t for t, m, u in self.requests if "/live/" + kind in u]


def login(browser, plat, js=True):
    ctx = browser.new_context(viewport={"width": 1280, "height": 700}, java_script_enabled=js)
    page = ctx.new_page()
    page.goto(plat.base + "/login")
    page.fill("input[name=name]", USER)
    page.fill("input[name=password]", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_load_state()
    return ctx, page


def nap(page, seconds):
    """Wait `seconds` while Playwright goes on delivering the page's events (a plain sleep would hold them back, and every count would read zero)."""
    page.wait_for_timeout(int(seconds * 1000))


def until(page, expr, arg=None, timeout=6.0):
    """Wait for a page function to say yes. The waiting call of Playwright that takes a string is not used: it evaluates the string, which the policy of these pages (no unsafe-eval) refuses."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if page.evaluate(expr, arg):
            return True
        page.wait_for_timeout(200)
    return False


def hide(page, hidden):
    """Emulate a tab that is in the background: Chromium headless has no tab strip, so the two things the script reads are set by hand."""
    page.evaluate("""(h) => { Object.defineProperty(document, 'hidden', {configurable: true, get: () => h});
                              Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => h ? 'hidden' : 'visible'});
                              document.dispatchEvent(new Event('visibilitychange')); }""", hidden)


# ---- the cases ---------------------------------------------------------------------------------------------------------------------

def tc001_004_006(browser, plat, want):
    out = {}
    if "TC-001" in want:
        ctx, page = login(browser, plat)
        page.goto(plat.base + "/?run=id-live-1")
        page.wait_for_selector("main[data-pane=middle] .badge")
        before = page.inner_text("main[data-pane=middle] .badge")
        plat.finish_run("live-1")
        t0 = time.monotonic()
        try:
            page.wait_for_selector("main[data-pane=middle] .badge.state-succeeded", timeout=3500)
            took = time.monotonic() - t0
            out["TC-001"] = (took <= 3.5, "the badge went from %r to the succeeded one in %.1f s" % (before, took))
        except Exception:
            out["TC-001"] = (False, "the badge did not change within 3.5 s (it said %r)" % page.inner_text("main[data-pane=middle] .badge"))
        ctx.close()
    if "TC-004" in want:
        ctx, page = login(browser, plat)
        page.goto(plat.base + "/?run=id-live-2")
        page.wait_for_selector("aside[data-pane=left] .rows")
        page.evaluate("document.querySelector('aside[data-pane=left] .tools').__keep = 1; document.querySelector('aside[data-pane=left] .foot').__keep = 1; "
                      "document.querySelector('aside[data-pane=left] .rows').__keep = 1")
        plat.finish_run("live-2")
        try:
            page.wait_for_selector("main[data-pane=middle] .badge.state-succeeded", timeout=3500)
        except Exception:
            pass
        kept = page.evaluate("[!!document.querySelector('aside[data-pane=left] .tools').__keep, !!document.querySelector('aside[data-pane=left] .foot').__keep, "
                             "!!document.querySelector('aside[data-pane=left] .rows').__keep]")
        out["TC-004"] = (kept[0] and kept[1] and not kept[2], "marks kept on the unchanged tools row / the unchanged foot / the changed run list: %s" % kept)
        ctx.close()
    if "TC-006" in want:
        ctx, page = login(browser, plat)
        page.set_viewport_size({"width": 1280, "height": 360})
        watch = Watch(page, plat.base)
        page.goto(plat.base + "/?run=id-live-3")
        page.wait_for_selector("main[data-pane=middle] .badge")
        page.evaluate("window.__mark = 7; window.scrollTo(0, 120)")
        y0 = page.evaluate("window.scrollY")
        loads0 = watch.loads
        plat.finish_run("live-3")
        try:
            page.wait_for_selector("main[data-pane=middle] .badge.state-succeeded", timeout=3500)
        except Exception:
            pass
        y1, mark = page.evaluate("window.scrollY"), page.evaluate("window.__mark")
        out["TC-006"] = (y0 > 0 and mark == 7 and watch.loads == loads0 and abs(y1 - y0) <= 2, "scroll %s -> %s, mark %s, page loads %d (was %d)" % (y0, y1, mark, watch.loads, loads0))
        ctx.close()
    return out


def tc005_007_008(browser, plat, want):
    out = {}
    ctx, page = login(browser, plat)
    watch = Watch(page, plat.base)
    page.goto(plat.base + "/?run=id-live-run")
    page.wait_for_selector("main[data-pane=middle] .badge")
    start = time.monotonic()
    nap(page, 22)
    plat.keep_alive()
    versions, contents = watch.live("version"), watch.live("content")
    if "TC-005" in want:
        out["TC-005"] = (len(versions) >= 8 and not contents, "%d version asks and %d content asks in 22 s on a page that did not change" % (len(versions), len(contents)))
    if "TC-007" in want:
        gaps = [b - a for a, b in zip(versions, versions[1:])][:10]
        out["TC-007"] = (len(gaps) >= 9 and all(1.5 <= g <= 3.0 for g in gaps), "gaps between asks: %s" % ", ".join("%.2f" % g for g in gaps))
    if "TC-008" in want:
        hide(page, True)
        nap(page, 0.5)
        n0 = len(watch.live("version"))
        nap(page, 10)
        n1 = len(watch.live("version"))
        hide(page, False)
        t0 = time.monotonic()
        asked = None
        while time.monotonic() - t0 < 2:
            if len(watch.live("version")) > n1:
                asked = time.monotonic() - t0
                break
            nap(page, 0.05)
        out["TC-008"] = (n1 - n0 <= 1 and asked is not None and asked <= 1.0, "asks while hidden: %d; first ask after coming back: %s" % (n1 - n0, "%.2f s" % asked if asked is not None else "none in 2 s"))
    ctx.close()
    return out


def tc009(browser, plat):
    ctx, page = login(browser, plat)
    watch = Watch(page, plat.base)
    page.goto(plat.base + "/?run=id-live-run")
    page.wait_for_selector("main[data-pane=middle] .badge")
    nap(page, 3)
    page.route("**/live/version*", lambda r: r.abort())
    t_fail = time.monotonic()
    nap(page, 62)
    plat.keep_alive()
    stamps = [t for t in watch.live("version") if t >= t_fail]
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    page.unroute("**/live/version*")
    nap(page, 1)
    t_ok = time.monotonic()
    nap(page, 34)
    back = [t for t in watch.live("version") if t >= t_ok]
    fast = [b - a for a, b in zip(back, back[1:])]
    grows = len(gaps) >= 4 and all(b >= a - 0.3 for a, b in zip(gaps, gaps[1:])) and max(gaps) <= 31.5 and gaps[-1] >= 25
    recovered = len(fast) >= 3 and all(g <= 3.0 for g in fast[-3:])
    ctx.close()
    return {"TC-009": (grows and recovered, "gaps while failing: %s; gaps after it came back: %s" % (", ".join("%.1f" % g for g in gaps), ", ".join("%.1f" % g for g in fast[-4:])))}


def tc011(browser, plat):
    ctx, page = login(browser, plat)
    watch = Watch(page, plat.base)
    page.goto(plat.base + "/?run=id-live-run")
    page.wait_for_selector("main[data-pane=middle] .badge")
    loads0 = watch.loads
    plat.end_sessions()
    try:
        page.wait_for_url("**/login*", timeout=6000)
    except Exception:
        pass
    nap(page, 1)
    loads1 = watch.loads
    nap(page, 8)
    ctx.close()
    return {"TC-011": ("/login" in page.url and loads1 == loads0 + 1 and watch.loads == loads1, "ended at %s, page loads %d -> %d -> %d" % (page.url, loads0, loads1, watch.loads))}


def regions_of(page, sel):
    return page.evaluate("(s) => Array.from(document.querySelectorAll(s)).map(e => e.value)", sel)


def tc014(browser, plat):
    plat.publish("fig1.png", "fig2.png")
    ctx, page = login(browser, plat)
    page.goto(plat.base + "/?run=id-live-ok&stage=finished")
    page.wait_for_selector("input[name=fig]")
    boxes = page.query_selector_all("input[name=fig]")
    for b in boxes[:2]:
        b.check()
    ticked = page.evaluate("Array.from(document.querySelectorAll('input[name=fig]')).filter(e => e.checked).map(e => e.value)")
    plat.publish("fig3.png")
    until(page, "() => document.querySelectorAll('input[name=fig]').length === 3")
    now = page.evaluate("Array.from(document.querySelectorAll('input[name=fig]')).map(e => [e.value, e.checked])")
    still = [v for v, c in now if c]
    ctx.close()
    return {"TC-014": (len(now) == 3 and sorted(still) == sorted(ticked) and len(ticked) == 2, "figures %s, ticked before %s, ticked after %s" % ([v for v, _ in now], ticked, still))}


def launch_flow(browser, plat, want):
    out = {}
    ctx, page = login(browser, plat)
    page.set_viewport_size({"width": 1100, "height": 420})
    page.goto(plat.base + "/launch?pipeline=nf-core/ampliseq&revision=2.18.0&src=used")
    page.wait_for_selector("input[name=run_name]")
    page.fill("input[name=run_name]", "typed-by-hand")
    page.focus("input[name=run_name]")
    page.evaluate("window.scrollTo(0, 60)")
    y0 = page.evaluate("window.scrollY")
    step5 = lambda: page.evaluate("document.querySelector(\"details[data-step='5']\").textContent")      # noqa: E731 (the step is closed: its text is there, but not rendered)
    before = step5()
    plat.answer_pipeline_files()
    until(page, "(b) => document.querySelector(\"details[data-step='5']\").textContent !== b", before)
    after = step5()
    typed = page.input_value("input[name=run_name]")
    focus = page.evaluate("document.activeElement && document.activeElement.name")
    y1 = page.evaluate("window.scrollY")
    if "TC-017" in want:
        out["TC-017"] = (typed == "typed-by-hand" and focus == "run_name", "the box holds %r and the focus is on %r" % (typed, focus))
    if "TC-018" in want:
        out["TC-018"] = (after != before and "trunclenf" in after, "the parameter step changed: %s" % (after != before))
    if "TC-019" in want:
        out["TC-019"] = (abs(y1 - y0) <= 2 and focus == "run_name", "scroll %s -> %s, focus on %r" % (y0, y1, focus))
    ctx.close()
    return out


def tc032(browser, plat):
    ctx = browser.new_context(viewport={"width": 1280, "height": 700}, accept_downloads=True)
    page = ctx.new_page()
    page.goto(plat.base + "/login")
    page.fill("input[name=name]", USER)
    page.fill("input[name=password]", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_load_state()
    page.goto(plat.base + "/run/file?run=id-live-file&path=a.txt")
    page.wait_for_selector("main.narrow")
    got = None
    try:
        with page.expect_download(timeout=7000) as info:
            plat.answer_file()
        got = info.value
    except Exception:
        pass
    ok = got is not None and got.suggested_filename == "a.txt"
    ctx.close()
    return {"TC-032": (ok, "download %s" % (got.suggested_filename if got else "did not start"))}


def tc034_035(browser, plat, want):
    out = {}
    if "TC-034" in want:
        ctx, page = login(browser, plat, js=False)
        watch = Watch(page, plat.base)
        page.goto(plat.base + "/?run=id-live-run")
        loads0 = watch.loads
        nap(page, 35)
        plat.keep_alive()
        out["TC-034"] = (watch.loads - loads0 >= 2 and not watch.live("version"), "page loads in 35 s without scripts: %d, live asks: %d" % (watch.loads - loads0, len(watch.live("version"))))
        ctx.close()
    if "TC-035" in want:
        ctx, page = login(browser, plat)
        watch = Watch(page, plat.base)
        page.goto(plat.base + "/?run=id-live-run")
        loads0 = watch.loads
        nap(page, 35)
        plat.keep_alive()
        out["TC-035"] = (watch.loads == loads0, "page loads in 35 s with scripts: %d (the first one counted: %d)" % (watch.loads - loads0 + 1, 1))
        ctx.close()
    return out


def tc040(browser, plat):
    ctx, page = login(browser, plat)
    watch = Watch(page, plat.base)
    page.goto(plat.base + "/?run=id-live-run")
    nap(page, 30)
    plat.keep_alive()
    page.goto(plat.base + "/launch?pipeline=nf-core/ampliseq&revision=2.19.0&src=used")
    nap(page, 30)
    plat.keep_alive()
    others = [(m, u) for _t, m, u in watch.requests if not u.startswith(plat.base + "/") or m != "GET"]
    live = [u for _t, _m, u in watch.requests if "/live/" in u]
    ctx.close()
    return {"TC-040": (not others and len(live) >= 20, "%d requests, %d of them to the live routes; not same-origin GET: %s" % (len(watch.requests), len(live), others[:3]))}


def need_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        print("check_live_sync: playwright is required (pip install playwright): %s" % e)
        sys.exit(3)
    return sync_playwright


def main(argv=None):
    a = parse(argv if argv is not None else sys.argv[1:])
    sync_playwright = need_playwright()
    if a.chromium_path and not os.path.isfile(a.chromium_path):
        print("check_live_sync: --chromium-path / $CHROME_PATH is not a file: %s" % a.chromium_path)
        return 3
    want = set(a.only)
    tmp = tempfile.mkdtemp(prefix="check-live-sync-", dir="/tmp")
    plat = Platform(a.platform_python, tmp)
    try:
        plat.start()
    except Exception as e:
        print("check_live_sync: %s" % e)
        plat.stop()
        return 3
    results = {}
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(**({"executable_path": a.chromium_path} if a.chromium_path else {}))
            except Exception as e:
                print("check_live_sync: Chromium would not start (%s)" % str(e).splitlines()[0])
                return 3
            plan = [(["TC-001", "TC-004", "TC-006"], lambda: tc001_004_006(browser, plat, want)),
                    (["TC-005", "TC-007", "TC-008"], lambda: tc005_007_008(browser, plat, want)),
                    (["TC-009"], lambda: tc009(browser, plat)), (["TC-011"], lambda: tc011(browser, plat)),
                    (["TC-014"], lambda: tc014(browser, plat)), (["TC-017", "TC-018", "TC-019"], lambda: launch_flow(browser, plat, want)),
                    (["TC-032"], lambda: tc032(browser, plat)), (["TC-034", "TC-035"], lambda: tc034_035(browser, plat, want)),
                    (["TC-040"], lambda: tc040(browser, plat))]
            for cases, run in plan:
                if not want & set(cases):
                    continue
                plat.keep_alive()
                try:
                    results.update({k: v for k, v in run().items() if k in want})
                except Exception as e:      # a case that could not be driven is a failure, never a skip
                    for c in cases:
                        if c in want and c not in results:
                            results[c] = (False, "could not be driven: %s" % str(e).splitlines()[0])
            browser.close()
    finally:
        plat.stop()
    lines = ["| case | result | what was seen |", "|---|---|---|"]
    for c in CASES:
        if c in want:
            ok, text = results.get(c, (False, "did not run"))
            lines.append("| %s | %s | %s |" % (c, "pass" if ok else "FAIL", text))
    print("\n".join(lines))
    return 0 if all(results.get(c, (False,))[0] for c in want) else 1


if __name__ == "__main__":
    sys.exit(main())
