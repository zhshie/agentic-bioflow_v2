#!/usr/bin/env python3
"""Evidence driver for web-run-tasks-log TC-036 (not part of the product). Starts the throwaway platform of scripts/dev/ui_check.py,
adds a FAILED run with two failed tasks (one with a recorded workdir, one without) and an online agent, then takes 1440/390 x zh/en
screenshots and runs axe on: the board tasks tab, the board logs tab, the results logs tab, /run/log loading, /run/log ready,
/run/log error (no workdir). Usage: PYTHONPATH=platform python specs/web-run-tasks-log/screenshots/seed_failed_demo.py OUTDIR"""
import os, sqlite3, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "dev"))
import ui_check  # noqa: E402

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
tmp = tempfile.mkdtemp(prefix="ui-check-data-", dir="/tmp")
proc, base = ui_check.start_platform(tmp)
RID = "ui-fail-run"
try:
    from abf_platform import store, jobs
    plat = str(Path(tmp) / "data" / "platform.db")
    uid = store.user_id_of(store.default_tokens_path(), ui_check.DEMO_USER)
    now = int(time.time())
    con = store.connect_index(os.environ["ABF_PLATFORM_DB"])
    with con:
        con.execute("INSERT INTO runs (id, session_id, run_name, final_status, started_at, ended_at, last_message_at, failure_reason, n_succeeded, n_failed)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)", (RID, "s-" + RID, RID, "failed", now - 7200, now - 6900, now - 6900, "FASTQC failed", 3, 2))
        con.execute("INSERT INTO failed_tasks (run_id, task_key, name, exit_code, error_message, workdir) VALUES (?,?,?,?,?,?)",
                    (RID, "t1", "FASTQC", 137, "out of memory", "/data/w/ab/cdef12"))
        con.execute("INSERT INTO failed_tasks (run_id, task_key, name, exit_code, error_message, workdir) VALUES (?,?,?,?,?,?)",
                    (RID, "t2", "TRIM", 1, "bad input", None))
    con.close()
    con = store.connect_state(plat)
    with con:
        con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?,?,?,?,?,?)",
                    (RID, "/f/" + RID, "lab-a", "agent-t", time.time(), uid))
        con.execute("UPDATE compute_envs SET owner_user_id = ? WHERE name = 'lab-a'", (uid,))
        con.execute("INSERT OR REPLACE INTO agents (name, version, first_seen_at, last_seen_at, owner_user_id) VALUES ('agent-t','t',?,?,?)",
                    (time.time(), time.time() + 86400, uid))
    con.close()

    from playwright.sync_api import sync_playwright
    from axe_playwright_python.sync_playwright import Axe
    LOG = "/run/log?run=%s&task=FASTQC&which=%s"
    pages = [("board-tasks", "/?run=%s&tab=tasks" % RID), ("board-logs", "/?run=%s&tab=logs" % RID),
             ("results-logs", "/?run=%s&stage=results&tab=logs" % RID), ("log-loading", LOG % (RID, "err")),
             ("log-ready", LOG % (RID, "err")), ("log-error", "/run/log?run=%s&task=TRIM&which=err" % RID)]
    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": os.environ["CHROME_PATH"]} if os.environ.get("CHROME_PATH") else {}))
        for width, height in ui_check.WIDTHS.items():
            for lang in ui_check.LANGS:
                ctx = b.new_context(viewport={"width": width, "height": height}); pg = ctx.new_page()
                pg.goto(base + "/login?lang=" + lang); pg.fill("input[name=name]", ui_check.DEMO_USER)
                pg.fill("input[name=password]", ui_check.DEMO_PASSWORD); pg.click("button[type=submit]"); pg.wait_for_load_state()
                for name, path in pages:
                    if name == "log-ready":     # the agent's answer arrives (the job queued by the loading visit)
                        con = sqlite3.connect(plat)
                        job = con.execute("SELECT id, agent FROM jobs WHERE kind='read_task_log' ORDER BY id DESC LIMIT 1").fetchone()
                        con.execute("UPDATE jobs SET state='claimed', claimed_at=? WHERE id=?", (time.time(), job[0])); con.commit(); con.close()
                        code, body = jobs.take_result(plat, job[1], job[0], "done", {"ok": True, "file": ".command.err", "lines": 4, "truncated": False,
                                                       "text": "Picked up _JAVA_OPTIONS\nstarted analysis of sample_1.fastq\nKilled\nexit status 137"}, time.time)
                        assert code == 200, (code, body)
                    resp = pg.goto(base + path + "&lang=" + lang); pg.wait_for_load_state()
                    pg.screenshot(path=str(out / ("%s-%d-%s.png" % (name, width, lang))), full_page=True)
                    v = Axe().run(pg).response.get("violations", [])
                    rows.append((name, width, lang, resp.status, [(x["impact"], x["id"]) for x in v],
                                 'http-equiv="refresh"' in pg.content()))
                ctx.close()
                # the next round must queue a fresh job: drop the old ones
                con = sqlite3.connect(plat); con.execute("DELETE FROM jobs WHERE kind='read_task_log'"); con.commit(); con.close()
        b.close()
    for r in rows:
        print(r)
finally:
    proc.terminate(); proc.wait(timeout=10)
