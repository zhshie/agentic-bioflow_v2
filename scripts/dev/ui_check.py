#!/usr/bin/env python3
# Nothing existing: Playwright only drives the browser and axe-core only judges the page; which pages, which widths, which languages, and the pass/fail line are this platform's own (pytest cannot hold it: CI has no Chromium and a skip would hide the gap).
"""Screenshots (1440 and 390 wide x zh and en) plus an axe-core accessibility check of the platform's key pages.

For the verifier's web acceptance. A standalone script, not a pytest test: it never skips quietly.

  python scripts/dev/ui_check.py --base-url http://127.0.0.1:18789 --user alice --password-env ABF_UI_PASSWORD
  python scripts/dev/ui_check.py --start          # starts a throwaway platform in /tmp, runs, stops it

Pages: board (/), launch (/launch), settings (/settings), results (a succeeded run, ?stage=results), usage (/usage), upload (/upload).
Default: board,launch,settings,results,usage. `results` needs a finished run: --start seeds one, otherwise pass --run <run id>.
Writes <out>/<page>-<width>-<lang>.png (4 per page) and <out>/summary.md. Screenshots stay out of the repository.

Needs: pip install playwright axe-playwright-python, and a Chromium (python -m playwright install chromium, or
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers with the same Playwright version). On a box that cannot reach the Playwright
download but has Chrome or Chromium installed, point --chromium-path at it (default: $CHROME_PATH when set). --start also
needs abf_platform importable (pip install ./platform).

Exit 0 = no serious/critical violation, 1 = at least one (or a page could not be checked), 2 = bad arguments,
3 = playwright / axe / Chromium missing, or --chromium-path is not a file (nothing was checked)."""
import argparse
import datetime
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

PATHS = {"board": "/", "launch": "/launch", "settings": "/settings", "usage": "/usage", "upload": "/upload"}
DEFAULT_PAGES = ["board", "launch", "settings", "results", "usage"]
ALL_PAGES = DEFAULT_PAGES + ["upload"]
WIDTHS = {1440: 900, 390: 844}
LANGS = ("zh", "en")
IMPACTS = ("critical", "serious", "moderate", "minor")
DEMO_USER, DEMO_PASSWORD, DEMO_RUN = "alice", "correct horse battery", "ui-demo-run"


def parse(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", help="platform web address, e.g. http://127.0.0.1:18789 (not needed with --start)")
    ap.add_argument("--out", help="folder for screenshots and summary.md (default $TMPDIR/ui-check-<date>/)")
    ap.add_argument("--pages", help="comma list of: " + ",".join(ALL_PAGES) + " (default " + ",".join(DEFAULT_PAGES) + ")")
    ap.add_argument("--start", action="store_true", help="start a throwaway platform (data folder under /tmp), check it, stop it")
    ap.add_argument("--user", default=os.environ.get("ABF_UI_USER", DEMO_USER), help="login name (default alice, or $ABF_UI_USER)")
    ap.add_argument("--password-env", default="ABF_UI_PASSWORD", help="environment variable holding the password (not used with --start)")
    ap.add_argument("--run", help="a succeeded run id for the results page (not needed with --start)")
    ap.add_argument("--chromium-path", default=os.environ.get("CHROME_PATH") or None,
                    help="Chrome/Chromium executable to drive instead of Playwright's own download (default $CHROME_PATH if set)")
    a = ap.parse_args(argv)
    if not a.start and not a.base_url:
        ap.error("give --base-url or --start")
    if a.start and a.base_url:
        ap.error("--start and --base-url exclude each other")
    pages = a.pages.split(",") if a.pages else DEFAULT_PAGES
    bad = [p for p in pages if p not in ALL_PAGES]
    if bad:
        ap.error("unknown page %s (choose from %s)" % (",".join(bad), ",".join(ALL_PAGES)))
    if "results" in pages and not a.start and not a.run:
        ap.error("the results page needs --run <run id> (or --start, which seeds one)")
    a.pages = pages
    return a


def need_playwright():
    try:
        from playwright.sync_api import sync_playwright
        from axe_playwright_python.sync_playwright import Axe
    except ImportError as e:
        print("ui_check: playwright and axe-playwright-python are required (pip install playwright axe-playwright-python): %s" % e)
        sys.exit(3)
    return sync_playwright, Axe


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_platform(tmp):
    """The verify-abf recipe: one data folder via ABF_PLATFORM_DB, a user with a web password, one succeeded run, `abf-platform web`."""
    env = dict(os.environ, ABF_PLATFORM_DB=str(Path(tmp) / "data" / "index.db"))
    (Path(tmp) / "data").mkdir(parents=True)
    os.environ.update(ABF_PLATFORM_DB=env["ABF_PLATFORM_DB"])
    from abf_platform import store
    cli = [sys.executable, "-m", "abf_platform"]
    for cmd in (["user", "add", DEMO_USER, "--lab", "lab-x"],
                ["ce", "create", "--name", "lab-a", "--platform", "slurm-platform", "--agent", "agent-t", "--work-dir", "/data/w",
                 "--launch-dir", "/data/l", "--head-queue", "normal", "--head-job-options", "-A ACCT -c 4"]):
        subprocess.run(cli + cmd, env=env, check=True, capture_output=True, text=True)
    store.set_web_password(store.default_tokens_path(), DEMO_USER, DEMO_PASSWORD)
    now = int(time.time())
    con = store.connect_index(os.environ["ABF_PLATFORM_DB"])
    with con:
        con.execute("INSERT INTO runs (id, session_id, run_name, final_status, started_at, ended_at, last_message_at, n_succeeded)"
                    " VALUES (?,?,?,?,?,?,?,?)", (DEMO_RUN, "s-" + DEMO_RUN, DEMO_RUN, "succeeded", now - 3600, now - 3500, now - 3500, 12))
    con.close()
    uid = store.user_id_of(store.default_tokens_path(), DEMO_USER)
    con = store.connect_state(str(Path(tmp) / "data" / "platform.db"))
    with con:
        con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?,?,?,?,?,?)",
                    (DEMO_RUN, "/f/" + DEMO_RUN, "lab-a", "agent-t", time.time(), uid))
    con.close()
    port = free_port()
    log = open(Path(tmp) / "web.log", "w")
    proc = subprocess.Popen(cli + ["web", "--port", str(port)], env=env, stdout=log, stderr=subprocess.STDOUT)
    base = "http://127.0.0.1:%d" % port
    for _ in range(100):
        try:
            if urllib.request.urlopen(base + "/login", timeout=2).status == 200:
                return proc, base
        except Exception:
            time.sleep(0.2)
    proc.terminate()
    print("ui_check: the platform did not come up, see %s" % (Path(tmp) / "web.log"))
    sys.exit(1)


def run_checks(a, base, user, password, run_id, sync_playwright, Axe, out):
    rows, shots = [], []
    if a.chromium_path and not os.path.isfile(a.chromium_path):
        print("ui_check: --chromium-path / $CHROME_PATH is not a file: %s" % a.chromium_path)
        sys.exit(3)
    launch_args = {"executable_path": a.chromium_path} if a.chromium_path else {}
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(**launch_args)
        except Exception as e:
            print("ui_check: Chromium would not start (%s); install it or set PLAYWRIGHT_BROWSERS_PATH" % str(e).splitlines()[0])
            sys.exit(3)
        for width, height in WIDTHS.items():
            for lang in LANGS:
                ctx = browser.new_context(viewport={"width": width, "height": height})
                page = ctx.new_page()
                page.goto(base + "/login?lang=" + lang)
                page.fill("input[name=name]", user)
                page.fill("input[name=password]", password)
                page.click("button[type=submit]")
                page.wait_for_load_state()
                for name in a.pages:
                    url = base + (PATHS[name] if name != "results" else "/?run=%s&stage=results" % run_id)
                    url += ("&" if "?" in url else "?") + "lang=" + lang
                    resp = page.goto(url)
                    page.wait_for_load_state()
                    status = resp.status if resp else 0
                    shot = "%s-%d-%s.png" % (name, width, lang)
                    page.screenshot(path=str(out / shot), full_page=True)
                    shots.append(shot)
                    found = Axe().run(page).response.get("violations", [])
                    rows.append(dict(page=name, width=width, lang=lang, status=status, final=page.url, violations=found))
                ctx.close()
        browser.close()
    return rows, shots


def summarize(rows, shots, base):
    lines = ["# ui_check summary", "", "Base: %s  |  %s" % (base, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")), "",
             "| page | width | lang | HTTP | critical | serious | moderate | minor |", "|---|---|---|---|---|---|---|---|"]
    blocking, broken = [], []
    for r in rows:
        n = {i: sum(1 for v in r["violations"] if v.get("impact") == i) for i in IMPACTS}
        lines.append("| %s | %d | %s | %s | %d | %d | %d | %d |" % (r["page"], r["width"], r["lang"], r["status"], *(n[i] for i in IMPACTS)))
        if r["status"] != 200 or "/login" in r["final"]:
            broken.append(r)
        blocking += [(r, v) for v in r["violations"] if v.get("impact") in ("serious", "critical")]
    lines += ["", "## Serious / critical violations", ""]
    if not blocking:
        lines.append("none")
    for r, v in blocking:
        targets = "; ".join(" ".join(n.get("target", [])) for n in v.get("nodes", [])[:3])
        lines.append("- **%s** %s (%d, %s) - %s - %d node(s), e.g. %s" % (v["impact"], v["id"], r["width"], r["lang"], r["page"],
                                                                         len(v.get("nodes", [])), targets))
    if broken:
        lines += ["", "## Pages that did not load as expected", ""]
        lines += ["- %s (%d, %s): HTTP %s, ended at %s" % (r["page"], r["width"], r["lang"], r["status"], r["final"]) for r in broken]
    lines += ["", "## Screenshots (%d)" % len(shots), ""] + ["- " + s for s in shots]
    return "\n".join(lines) + "\n", bool(blocking or broken)


def main(argv=None):
    a = parse(argv if argv is not None else sys.argv[1:])
    sync_playwright, Axe = need_playwright()
    out = Path(a.out) if a.out else Path(tempfile.gettempdir()) / ("ui-check-" + datetime.date.today().isoformat())
    out.mkdir(parents=True, exist_ok=True)
    proc = tmp = None
    try:
        if a.start:
            tmp = tempfile.mkdtemp(prefix="ui-check-data-", dir="/tmp")
            proc, base = start_platform(tmp)
            user, password, run_id = DEMO_USER, DEMO_PASSWORD, DEMO_RUN
        else:
            base, user, run_id = a.base_url.rstrip("/"), a.user, a.run
            password = os.environ.get(a.password_env)
            if not password:
                print("ui_check: set the password in $%s" % a.password_env)
                return 2
        rows, shots = run_checks(a, base, user, password, run_id, sync_playwright, Axe, out)
    finally:
        if proc:
            proc.terminate()
            proc.wait(timeout=10)
    text, failed = summarize(rows, shots, base)
    (out / "summary.md").write_text(text, encoding="utf-8")
    print(text)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
