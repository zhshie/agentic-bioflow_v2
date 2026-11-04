#!/usr/bin/env python3
# Nothing existing: drives the platform's own settings page in a real Chrome (settings-ce-table-mobile); Playwright is only the browser driver.
"""Manual check: the compute-environment table on /settings, at 1440 px and at 390 px (device emulation), in zh and en.

Writes four screenshots to the folder given as argv[1] (default specs/settings-ce-table-mobile/screenshots) and prints
document.documentElement.scrollWidth vs clientWidth for each. Exit 0 = no sideways scroll in all four, 1 = overflow, 77 = no playwright/Chrome.
Not part of pytest or CI. Unix-only platform side: run in WSL. See docs/TESTING.md."""
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
    base, name, password, out = sys.argv[1:5]
    bad = 0
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(channel="chrome", headless=True)
        except Exception as e:
            print("NOBROWSER", e)
            sys.exit(77)
        for width, mobile in ((1440, False), (390, True)):
            ctx = b.new_context(viewport={"width": width, "height": 900}, is_mobile=mobile, device_scale_factor=2 if mobile else 1)
            page = ctx.new_page()
            page.goto(base + "/login?next=/settings")
            page.fill("input[name=name]", name)
            page.fill("input[name=password]", password)
            page.click("button[type=submit]")
            page.wait_for_load_state()
            for lang in ("zh", "en"):
                page.goto(base + "/settings?lang=" + lang)
                sw, cw = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
                print("WIDTH", width, lang, "scrollWidth", sw, "clientWidth", cw)
                bad += sw > cw
                page.screenshot(path="%s/settings-ce-%d-%s.png" % (out, width, lang), full_page=True)
            ctx.close()
        b.close()
    sys.exit(1 if bad else 0)
''')


def main():
    py = os.environ.get("ABF_PLAYWRIGHT_PYTHON") or (sys.executable if importlib.util.find_spec("playwright") else None)
    if not py:
        print("no python with playwright (set ABF_PLAYWRIGHT_PYTHON)")
        return 77
    import pytest
    from helpers import free_port, start_cli, stop_proc, wait_port
    from human_harness import PASSWORD, World
    from test_web_settings import two_envs

    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "specs" / "settings-ce-table-mobile" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    shot_dir = subprocess.run(["wslpath", "-w", str(out_dir)], capture_output=True, text=True).stdout.strip() if py.endswith(".exe") else str(out_dir)
    mp = pytest.MonkeyPatch()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        w = World(tmp, mp)
        from abf_platform import compute_envs
        w.base_env = compute_envs.get(w.ip.state_db, "lab-a")
        ann = w.user("ann")
        two_envs(w, ann)
        port = free_port()
        proc = start_cli(["web", "--port", str(port)], w.data.env(), tmp / "web.log")
        try:
            wait_port(port, proc=proc)
            res = subprocess.run([py, "-c", DRIVER, "http://127.0.0.1:%d" % port, "ann", PASSWORD, shot_dir],
                                 capture_output=True, text=True, timeout=180, encoding="utf-8")
        finally:
            stop_proc(proc)
            mp.undo()
    print(res.stdout, res.stderr)
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
