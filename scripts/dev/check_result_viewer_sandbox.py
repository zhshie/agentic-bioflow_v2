#!/usr/bin/env python3
# Nothing existing: drives the platform's own report preview (/run/preview, /run/report) in a real Chromium (web-result-viewer); Playwright is only the browser driver.
"""Purpose: the browser half of TC-053 to TC-057 of web-result-viewer. A logged-in Chromium opens the preview page of a report whose own script
attacks the site (reads document.cookie, reads window.parent.document, submits a form to /settings, fetches /settings and /run/file), and the
check reads back what the script got and what the site received. The sample is ATTACK of platform/tests/test_web_result_viewer.py, the same one
the browser-free pytest assertions use.

How to run: from the repo root, in WSL or Linux (the platform side is Unix-only), with the platform's Python:
`cd platform && python ../scripts/dev/check_result_viewer_sandbox.py`. It takes no options and writes nothing outside a temporary folder.
Needs playwright + Chromium (or Chrome) in the Python named by ABF_PLAYWRIGHT_PYTHON (default: this Python if it has playwright, else the
python3 on PATH if that one has it). See docs/TESTING.md, "web-result-viewer".
Exit 0 = all five cases hold; 1 = a case failed; 77 = no playwright or no browser: nothing was checked, the result is UNVERIFIED, never a pass.
One-off: no. It is the re-runnable manual check of the report sandbox; it is not part of pytest or CI, because CI has no browser and may skip
nothing (plan, lead ruling 2026-11-11). platform/tests/test_web_result_viewer.py pins that it exists, uses ATTACK and says so without playwright."""
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

DRIVER = r'''
import json, sys
from playwright.sync_api import sync_playwright
base, name, value, rid = sys.argv[1:5]
with sync_playwright() as p:
    b = None
    for kw in ({}, {"channel": "chrome"}):
        try:
            b = p.chromium.launch(**kw)
            break
        except Exception as e:
            why = e
    if b is None:
        print("NOBROWSER", why)
        sys.exit(77)
    ctx = b.new_context()
    ctx.add_cookies([{"name": name, "value": value, "url": base}])
    page = ctx.new_page()
    page.goto(base + "/run/preview?run=" + rid + "&path=multiqc_report.html")
    frame = [f for f in page.frames if f != page.main_frame][0]
    frame.wait_for_function("document.getElementById('out') && document.getElementById('out').getAttribute('data-done') === '1'", timeout=15000)
    page.wait_for_timeout(1500)
    print(json.dumps({"out": frame.inner_text("#out"), "url": page.url, "top_has_iframe": page.locator("iframe").count()}))
    b.close()
'''


def has_playwright(py):
    try:
        return subprocess.run([py, "-c", "import playwright"], capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def playwright_python():
    named = os.environ.get("ABF_PLAYWRIGHT_PYTHON")
    if named:
        return named if has_playwright(named) else None
    if importlib.util.find_spec("playwright"):
        return sys.executable
    other = shutil.which("python3")
    return other if other and has_playwright(other) else None


def main():
    py = playwright_python()
    if not py:
        print("UNVERIFIED: no Python with playwright (set ABF_PLAYWRIGHT_PYTHON); nothing was checked")
        return 77
    sys.path.insert(0, str(REPO / "platform"))
    sys.path.insert(0, str(REPO / "platform" / "tests"))
    import pytest
    import uvicorn
    from abf_platform import web
    from human_harness import World
    from test_web_finished import world
    from test_web_result_viewer import ATTACK, answered

    mp = pytest.MonkeyPatch()
    seen = []
    with tempfile.TemporaryDirectory() as td:
        try:
            w = World(Path(td), mp)
            ann, c, rid = world(w)
            answered(w, c, rid, "multiqc_report.html", ATTACK.replace(b"RID", rid.encode()))
            answered(w, c, rid, "a.txt", b"secret file text")
            app = web.create_app(w.ip.index, w.ip.tokens, w.ip.state_db, clock=w.clock, public_url=None)

            async def logged(scope, receive, send):
                if scope["type"] == "http":
                    seen.append((scope["method"], scope["path"] + ("?" + scope["query_string"].decode() if scope["query_string"] else "")))
                await app(scope, receive, send)

            s = socket.socket()
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
            s.close()
            server = uvicorn.Server(uvicorn.Config(logged, host="127.0.0.1", port=port, log_level="warning", lifespan="off"))
            t = threading.Thread(target=server.run, daemon=True)
            t.start()
            for _ in range(100):
                if server.started:
                    break
                time.sleep(0.1)
            if not server.started:
                print("FAIL the throwaway platform did not start")
                return 1
            try:
                name, value = next(iter(c.cookies.items()))
                done = subprocess.run([py, "-c", DRIVER, "http://127.0.0.1:%d" % port, name, value, rid],
                                      capture_output=True, text=True, timeout=120, encoding="utf-8")
            finally:
                server.should_exit = True
                t.join(10)
        finally:
            mp.undo()
    if done.returncode == 77:
        print("UNVERIFIED: playwright found no Chromium and no Chrome; nothing was checked\n" + done.stdout[-2000:])
        return 77
    if done.returncode != 0:
        print("FAIL the browser driver ended with %d\n%s" % (done.returncode, (done.stdout + done.stderr)[-2000:]))
        return 1
    got = json.loads(done.stdout.strip().splitlines()[-1])
    res = json.loads(got["out"])
    print("the report's script wrote:", got["out"].replace(value, "<THE LOGIN COOKIE>"))
    print("the site received:", seen)
    reached = [x for x in seen if x[1] == "/settings" or x[1].startswith("/run/file")]
    checks = [
        ("TC-053 the report cannot read the login cookie", value not in got["out"] and (res["cookie"] == "READ:" or res["cookie"].startswith("ERR:"))),
        ("TC-054 fetch of /settings is blocked and never reaches the site", res["settings"].startswith("ERR:") and not [x for x in reached if x[1] == "/settings"]),
        ("TC-055 fetch of /run/file is blocked and never reaches the site", res["file"].startswith("ERR:") and not [x for x in reached if x[1].startswith("/run/file")]),
        ("TC-056 window.parent.document throws", res["parent"].startswith("ERR:")),
        ("TC-057 the form sends nothing and the outer page stays",
         reached == [] and [x for x in seen if x[0] != "GET"] == [] and got["url"].endswith("path=multiqc_report.html") and got["top_has_iframe"] == 1),
    ]
    bad = 0
    for label, good in checks:
        print(("ok   " if good else "FAIL ") + label)
        bad += not good
    print("check_result_viewer_sandbox: " + ("FAIL" if bad else "PASS"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
