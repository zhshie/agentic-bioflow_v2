#!/usr/bin/env python3
# Nothing existing: drives the platform's own login page and confirm page in a real Chrome (WCO-3, specs/web-chrome-origin); Playwright is only the browser driver, the page, the user and the pending request are this project's.
"""Manual check WCO-3: a real Chrome logs in (303) and presses send (no 403).

Not part of pytest or CI: CI has neither Playwright nor Chrome. Run it by hand, see docs/TESTING.md
("Chrome login (web-chrome-origin)"). The platform side is Unix-only (its test harness), so run this file in WSL or Linux; the browser Python may be a
Windows one (ABF_PLAYWRIGHT_PYTHON=/mnt/c/.../python.exe) - the driver is passed with -c, no file crosses over.
Needs this repo's test dependencies (pytest, abf_platform) in the
Python that runs this file; the browser is driven by the Python named in ABF_PLAYWRIGHT_PYTHON
(default: this Python, if it has playwright).

Exit 0 = pass, 1 = fail, 77 = no playwright or no Chrome (nothing was checked)."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "platform"))
sys.path.insert(0, str(REPO / "platform" / "tests"))

DRIVER = textwrap.dedent('''
    import sys
    from playwright.sync_api import sync_playwright
    base, name, password, rid = sys.argv[1:5]
    posts = []
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(channel="chrome", headless=True)
        except Exception as e:
            print("NOBROWSER", e)
            sys.exit(77)
        page = b.new_page()
        page.on("response", lambda r: posts.append((r.request.method, r.status)) if r.request.method == "POST" else None)
        page.goto(base + "/login?next=/c/" + rid)
        page.fill("input[name=name]", name)
        page.fill("input[name=password]", password)
        page.click("button[type=submit]")
        page.wait_for_load_state()
        page.click("button[type=submit]")
        page.wait_for_load_state()
        print("POSTS", posts)
        print("BODY", "\u5df2\u9001\u51fa" in page.content())
        b.close()
''')


def playwright_python():
    cand = os.environ.get("ABF_PLAYWRIGHT_PYTHON")
    if cand:
        return cand
    return sys.executable if importlib.util.find_spec("playwright") else None


def main():
    py = playwright_python()
    if not py:
        print("no python with playwright (set ABF_PLAYWRIGHT_PYTHON)")
        return 77
    import pytest
    from helpers import free_port, start_cli, stop_proc, wait_port
    from human_harness import PASSWORD, World
    from test_confirm_page import pending

    mp = pytest.MonkeyPatch()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        w = World(tmp, mp)
        ann = w.user("ann")
        rid = pending(w, ann)
        port = free_port()
        proc = start_cli(["web", "--port", str(port)], w.data.env(), tmp / "web.log")
        try:
            wait_port(port, proc=proc)
            out = subprocess.run([py, "-c", DRIVER, "http://127.0.0.1:%d" % port, "ann", PASSWORD, rid],
                                 capture_output=True, text=True, timeout=120, encoding="utf-8")
        finally:
            stop_proc(proc)
            mp.undo()
    print(out.stdout, out.stderr)
    if out.returncode == 77:
        print("no Chrome: nothing was checked")
        return 77
    if out.returncode != 0 or "403" in out.stdout or "('POST', 303)" not in out.stdout or "BODY True" not in out.stdout:
        print("FAIL: expected a 303 on login, no 403, and the sent page")
        return 1
    print("PASS: WCO-3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
