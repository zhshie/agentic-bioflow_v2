# Nothing existing: tests that drive the real command line through a pseudo-terminal, because the confirmation exists only on a terminal; nothing off the shelf plays "wait for the question, then type".
"""abf-platform launch and cancel: what is shown, what is asked, what is refused before the question (feature 007b)."""
import csv
import json
import os
import re
import sqlite3
import time
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR, pkg_env
from launch_harness import ACCOUNT, QUESTION_CANCEL, QUESTION_LAUNCH, LaunchData, Pty, cli_argv
from station_harness import Inproc, write_exec

PREFIX = "| "


@pytest.fixture
def data(tmp_path, monkeypatch):
    return LaunchData(Inproc(tmp_path / "ip", monkeypatch))


def start(data, tmp_path, *args, env=None, **kw):
    argv = cli_argv(*(args or data.launch_args(tmp_path)))
    return Pty(argv, env or data.env(), **kw)


def ask(data, tmp_path, answer=None, args=None, question=QUESTION_LAUNCH, env=None, **kw):
    """Run to the question; answer it (or not); return (exit code, whole screen)."""
    p = start(data, tmp_path, *(args or data.launch_args(tmp_path)), env=env, **kw)
    assert p.wait_for(question), p.text()
    if answer is not None:
        p.send(answer)
    return p.finish(60)


def parts(screen, question):
    """(the lines before the question, with the prefix taken off, the text of the question line)."""
    idx = screen.rindex(question)
    lines = screen[:idx].split("\n")
    assert lines[-1] == "", "the question starts a line of its own"
    body = lines[:-1]
    for ln in body:
        assert ln.startswith(PREFIX), "a line without the prefix: %r" % ln
    return [ln[len(PREFIX):] for ln in body], screen[idx:]


def section(lines, title):
    start_i = [i for i, ln in enumerate(lines) if ln.startswith("== ") and title in ln]
    assert start_i, "no section %s in %r" % (title, [ln for ln in lines if ln.startswith("== ")])
    out = []
    for ln in lines[start_i[0] + 1:]:
        if ln.startswith("== "):
            break
        out.append(ln)
    return out


def unescape(line):
    return (line.replace("\\t", "\t").replace("\\n", "\n").replace("\\\\", "\\"))


# ---- TC-001: everything is shown before the question ---------------------------------------------------------

def test_tc001_the_whole_launch_is_shown_before_the_question_and_nothing_is_written_until_y(data, tmp_path):
    p = start(data, tmp_path)
    assert p.wait_for(QUESTION_LAUNCH, 30), p.text()
    time.sleep(0.5)
    screen = p.text()
    before = data.snapshot()
    assert before == (0, 0, 0, 0), before
    lines, question = parts(screen, QUESTION_LAUNCH)
    assert screen.rstrip("\n").endswith(QUESTION_LAUNCH) and question.strip() == QUESTION_LAUNCH
    text = "\n".join(lines)
    for needle in ("nf-core/ampliseq", "2.18.0", "lab-a", "/data/w1/runs/run-one", ACCOUNT, "normal",
                   "-A %s -c 4 --mem=26G -t 4-00:00:00" % ACCOUNT):
        assert needle in text, needle
    rows = section(lines, "samplesheet.csv")
    assert len([r for r in rows if re.match(r"s\d\d,", r)]) == 10 and "s01" in text and "s10" in text
    shown_params = "\n".join(section(lines, "params.yaml"))
    for name, value in (("primer", '"AGRG"'), ("pacbio", "true"), ("depth", "3")):
        assert "%s: %s" % (name, value) in shown_params
    config = [unescape(x) for x in section(lines, "nextflow.config")]
    assert config == ["process.executor = 'slurm'"]
    # the head script as shown is the one the function renders for the same input
    from abf_platform import compute_envs
    from abf_station import launch
    shown_head = "\n".join(unescape(x) for x in section(lines, "head.sh"))
    ce = compute_envs.get(data.ip.state_db, "lab-a")
    b = launch.render_bundle(**launch.inputs_from_environment(
        ce, data.agent, data.facts, run_name="run-one", pipeline="nf-core/ampliseq", revision="2.18.0",
        samplesheet=list(csv.reader(open(data.samplesheet(tmp_path)))), params={"primer": "AGRG", "pacbio": True, "depth": 3}))
    assert shown_head.rstrip("\n") == b["files"]["head.sh"].rstrip("\n")
    assert "nextflow run" in shown_head and "-with-tower" in shown_head
    p.send("y\n")
    rc, final = p.finish(60)
    assert data.count("jobs") == 1 and data.count("confirmations") == 1 and data.count("launches") == 1
    job = data.rows("jobs")[0]
    assert job[3] == "launch_nextflow"
    conf = data.rows("confirmations")[0]
    from abf_platform import common
    assert conf[1] == common.bundle_sha256(b) and conf[2] == "launch" and conf[4] is None
    args = json.loads(job[4])
    assert common.bundle_sha256(args["bundle"]) == args["bundle_sha256"] == conf[1]
    assert args["confirmation_id"] == conf[0] == job[-1]
    assert data.run_tokens() == 0, "no token before an agent claims the job"
    blob = open(data.ip.state_db, "rb").read()
    assert b"abf_" not in blob.replace(b"abf_platform", b"")


@pytest.mark.parametrize("answer", ["y\n", "Y\n"])
def test_tc002_a_small_y_and_a_capital_Y_both_send(data, tmp_path, answer):
    run = "run-" + ("small" if answer == "y\n" else "capital")
    ask(data, tmp_path, answer, args=data.launch_args(tmp_path, run=run))
    assert (data.count("jobs"), data.count("confirmations"), data.count("launches")) == (1, 1, 1)
    assert data.rows("launches")[0][1] == run


ANSWERS = ["n\n", "N\n", "\n", "yes\n", "YES\n", "yy\n", "是\n", "y x\n", "ok\n", "1\n", "  \n"]


@pytest.mark.parametrize("answer", ANSWERS)
def test_tc003_anything_but_y_sends_nothing(data, tmp_path, answer):
    rc, screen = ask(data, tmp_path, answer)
    assert rc != 0 and "未送出" in screen
    assert data.snapshot() == (0, 0, 0, 0)


NOT_A_TERMINAL = {
    "echo y piped in": ["bash", "-c", 'echo y | "$@"', "_"],
    "yes piped in": ["bash", "-c", 'yes | "$@"', "_"],
    "stdin from /dev/null": ["bash", "-c", '"$@" < /dev/null', "_"],
    "stdin closed": ["bash", "-c", '"$@" <&-', "_"],
}


@pytest.mark.parametrize("how", sorted(NOT_A_TERMINAL))
def test_tc004_without_a_terminal_for_the_answer_nothing_is_sent(data, tmp_path, how):
    argv = NOT_A_TERMINAL[how] + cli_argv(*data.launch_args(tmp_path))
    p = Pty(argv, data.env())
    rc, screen = p.finish(60)
    assert rc != 0 and re.search(r"終端機|terminal", screen), screen
    assert QUESTION_LAUNCH not in screen or "未送出" in screen
    assert data.snapshot() == (0, 0, 0, 0)


def test_tc004_a_program_with_no_controlling_terminal_is_refused_even_if_its_input_is_a_tty(data, tmp_path):
    p = start(data, tmp_path, controlling=False)
    p.send("y\n")
    rc, screen = p.finish(60)
    assert rc != 0 and re.search(r"終端機|terminal", screen), screen
    assert data.snapshot() == (0, 0, 0, 0)


@pytest.mark.parametrize("flag", ["--yes", "-y", "--force", "--assume-yes", "--no-confirm"])
def test_tc004_no_flag_skips_the_question(data, tmp_path, flag):
    p = start(data, tmp_path, *(data.launch_args(tmp_path) + [flag]))
    rc, screen = p.finish(60)
    assert rc != 0 and re.search(r"unrecognized|invalid|usage", screen, re.I), screen
    assert QUESTION_LAUNCH not in screen
    assert data.snapshot() == (0, 0, 0, 0)


@pytest.mark.parametrize("name", ["ABF_PLATFORM_ASSUME_YES", "ABF_PLATFORM_YES", "CI", "ABF_ASSUME_YES", "YES"])
def test_tc004_no_environment_variable_answers_for_the_user(data, tmp_path, name):
    p = start(data, tmp_path, env=data.env(**{name: "1" if name != "CI" else "true"}))
    assert p.wait_for(QUESTION_LAUNCH, 30), p.text()
    time.sleep(1.0)
    assert p.proc.poll() is None, "still waiting for the person"
    assert data.snapshot() == (0, 0, 0, 0)
    p.send("n\n")
    rc, screen = p.finish(30)
    assert rc != 0 and data.snapshot() == (0, 0, 0, 0)


def test_tc004_there_is_no_bypass_in_the_source_or_the_help_text():
    pkg = PLATFORM_DIR / "abf_launch"
    text = "".join(f.read_text(encoding="utf-8") for f in sorted(pkg.rglob("*.py")))
    assert not re.search(r"--yes|assume.yes|ASSUME_YES|--force|\"-y\"|--no-confirm|environ\.get\(.(CI|YES)", text, re.I)
    from abf_platform import cli
    helps = cli.build_parser().format_help()
    for act in cli.build_parser()._actions:
        if isinstance(getattr(act, "choices", None), dict):
            for name, sub in act.choices.items():
                helps += sub.format_help()
    assert not re.search(r"--yes|assume-yes|--force|skip the (question|confirmation)|no-confirm", helps, re.I)


@pytest.mark.parametrize("how", ["ctrl-c", "ctrl-d", "hangup", "kill"])
def test_tc005_an_interrupted_question_leaves_nothing_behind(data, tmp_path, how):
    p = start(data, tmp_path)
    assert p.wait_for(QUESTION_LAUNCH, 30)
    if how == "ctrl-c":
        p.send(b"\x03")
    elif how == "ctrl-d":
        p.send(b"\x04")
    elif how == "hangup":
        p.hangup()
    else:
        p.proc.kill()
    rc, screen = p.finish(30)
    assert p.proc.poll() is not None, "no program left behind"
    assert data.snapshot() == (0, 0, 0, 0)
    if how in ("ctrl-c", "ctrl-d"):
        assert rc != 0


# ---- TC-006: what is shown is true -------------------------------------------------------------------------------

@pytest.mark.parametrize("ch,where", [("\x00", "sheet"), ("\r", "sheet"), ("\x1b[2J", "sheet"), ("\x1b[8m", "sheet"),
                                      ("‮", "sheet"), ("⁦", "sheet"), ("⁩", "sheet"),
                                      ("\x1b[2J", "param"), ("‮", "param"), ("\r", "param")])
def test_tc006_characters_that_could_rewrite_the_screen_are_refused_before_any_question(data, tmp_path, ch, where):
    rows = [("s01", "/data/storage/rawdata/a.fq"), ("x%sy" % ch if where == "sheet" else "ok", "/data/storage/rawdata/b.fq")]
    params = ("depth=3", "note=a%sb" % ch) if where == "param" else ("depth=3",)
    p = start(data, tmp_path, *data.launch_args(tmp_path, rows=rows, params=params))
    rc, screen = p.finish(60)
    assert rc != 0 and QUESTION_LAUNCH not in screen
    assert ("samplesheet" in screen) if where == "sheet" else ("note" in screen), screen
    assert b"\x1b" not in p.raw() and b"\r" not in p.raw() and b"\x00" not in p.raw()
    assert data.snapshot() == (0, 0, 0, 0)


def test_tc006_other_control_characters_are_shown_as_escapes_and_every_line_has_the_prefix(data, tmp_path):
    rows = [("tab\there", "/data/storage/rawdata/a.fq"), ("bell\x07del\x7f", "/data/storage/rawdata/b.fq"),
            ("two\nlines", "/data/storage/rawdata/c.fq"), ("back\\slash", "/data/storage/rawdata/d.fq"),
            ("long" + "x" * 3000, "/data/storage/rawdata/e.fq")]
    p = start(data, tmp_path, *data.launch_args(tmp_path, rows=rows, params=("note=a\tb",)))
    assert p.wait_for(QUESTION_LAUNCH, 30), p.text()
    screen = p.text()
    p.send("n\n")
    p.finish(30)
    raw = p.raw()
    assert b"\x1b" not in raw and b"\r" not in raw and b"\x00" not in raw and b"\x07" not in raw and b"\x7f" not in raw
    assert not re.search("[‪-‮⁦-⁩‎‏؜]", screen)
    lines, _ = parts(screen, QUESTION_LAUNCH)  # raises on a line without the prefix
    text = "\n".join(lines)
    for esc in ("tab\\there", "bell\\x07del\\x7f", "two\\nlines", "back\\\\slash"):
        assert esc in text, esc
    assert "x" * 3000 in text, "a long value is shown whole, on its own prefixed line"
    assert all(ln.startswith(PREFIX) for ln in screen[:screen.rindex(QUESTION_LAUNCH)].split("\n")[:-1])


# ---- TC-011, TC-021, TC-024, TC-025, TC-063: refused before the question ---------------------------------------------

def refuse(data, tmp_path, match, args=None, env=None):
    p = start(data, tmp_path, *(args or data.launch_args(tmp_path)), env=env)
    rc, screen = p.finish(60)
    assert rc != 0, screen
    assert QUESTION_LAUNCH not in screen, "the question must not appear"
    assert re.search(match, screen), screen
    assert data.snapshot() == (0, 0, 0, 0)
    return screen


@pytest.mark.parametrize("extra,match", [
    (["--run-name", "Bad"], r"run"), (["--run-name", "a/b"], r"run"), (["--run-name", "-x"], r"run"),
    (["--revision", "main"], r"revision|版本"), (["--revision", "abc1234"], r"revision|版本"),
    (["--pipeline", "-hub/x"], r"pipeline|管線"), (["--pipeline", "nf-core/ampliseq --foo"], r"pipeline|管線"),
    (["--pipeline", "ampliseq"], r"pipeline|管線")])
def test_tc011_a_bad_name_version_or_pipeline_is_refused_with_the_field_named(data, tmp_path, extra, match):
    args = data.launch_args(tmp_path)
    for flag, val in zip(extra[::2], extra[1::2]):
        args[args.index(flag) + 1] = val
    refuse(data, tmp_path, match, args=args)


@pytest.mark.parametrize("path", ["/etc/passwd", "relative/a.fq", "/data/storage/rawdata/a b.fq", "/data/storage/../x.fq",
                                  "/data/elsewhere/a.fq", "/data/storage/rawdata/$(id).fq"])
def test_tc011_a_sample_file_outside_the_read_roots_is_refused(data, tmp_path, path):
    refuse(data, tmp_path, r"samplesheet|fastq_1", args=data.launch_args(tmp_path, rows=[("s1", path)]))


def test_tc011_an_environment_that_cannot_run_a_launch_is_refused_in_its_own_words(tmp_path, monkeypatch):
    # disabled, not yet available, unknown, agent offline
    ip = Inproc(tmp_path / "ip", monkeypatch)
    d = LaunchData(ip)
    rc, _ = ip.run("ce", "disable", "lab-a")
    assert rc == 0
    refuse(d, tmp_path, r"已停用|disabled")
    ip.run("ce", "enable", "lab-a")
    ip.run("ce", "create", "--name", "bare", "--platform", "slurm-platform", "--work-dir=/data/w2", "--head-queue=normal")
    args = d.launch_args(tmp_path)
    args[args.index("--ce") + 1] = "bare"
    refuse(d, tmp_path, r"preflight|available|可用|狀態|status", args=args)  # created, never checked
    args[args.index("--ce") + 1] = "nope"
    refuse(d, tmp_path, r"not found|找不到", args=args)
    # an agent that was last seen long ago
    from abf_platform import agents
    agents.register(ip.state_db, d.agent, "0.1.0", lambda: time.time() - 100000, facts=d.facts)
    refuse(d, tmp_path, r"offline|離線", env=d.env(ABF_AGENT_HEARTBEAT_SECONDS=20))


def test_tc063_an_environment_of_another_type_is_refused_and_no_cloud_program_is_called(tmp_path, monkeypatch):
    ip = Inproc(tmp_path / "ip", monkeypatch)
    d = LaunchData(ip)
    log = tmp_path / "cloud.log"
    bindir = tmp_path / "cloudbin"
    for t in ("aws", "kubectl", "gcloud", "az", "ssh"):
        write_exec(bindir / t, "#!/bin/bash\necho \"$0 $*\" >> '%s'\n" % log)
    rc, out = ip.run("ce", "create", "--name", "cloud", "--platform", "awsbatch-platform",
                     "--config-json", json.dumps({"workDir": "s3://bucket/work", "region": "eu-west-1"}))
    assert rc == 0, out
    args = d.launch_args(tmp_path)
    args[args.index("--ce") + 1] = "cloud"
    env = d.env(PATH=str(bindir) + os.pathsep + os.environ["PATH"])
    refuse(d, tmp_path, r"尚未支援|not supported", args=args, env=env)
    assert not log.exists() or log.read_text() == ""


def test_tc021_an_unset_account_and_a_disagreeing_account_are_refused_before_the_question(tmp_path, monkeypatch):
    ip = Inproc(tmp_path / "ip", monkeypatch)
    d = LaunchData(ip, facts={"slurm_account": None})
    screen = refuse(d, tmp_path, r"帳號未設定")
    assert "slurm_account" in screen
    d.register(dict(d.facts, slurm_account="ACCT-OTHER-9"))
    screen = refuse(d, tmp_path, r"帳號與環境選項不一致")
    assert "ACCT-OTHER-9" in screen and ACCOUNT in screen


def test_tc024_a_reverse_forward_needs_the_platform_on_the_same_machine(tmp_path, monkeypatch):
    ip = Inproc(tmp_path / "ip", monkeypatch)
    d = LaunchData(ip, facts={"reach": "ssh", "platform_local": False, "endpoint": None,
                              "forward_file": "/data/storage/_relay/forward_port"})
    refuse(d, tmp_path, r"同一台機器|same machine")


def test_tc025_pre_and_post_run_scripts_and_a_user_outdir_are_refused_out_loud(tmp_path, monkeypatch):
    ip = Inproc(tmp_path / "ip", monkeypatch)
    d = LaunchData(ip, pre_run="echo hi")
    refuse(d, tmp_path, r"不支援：這一片不執行事前／事後腳本")
    ip.run("ce", "update", "lab-a", "--pre-run=")
    ip.run("ce", "update", "lab-a", "--post-run=echo bye")
    refuse(d, tmp_path, r"不支援：這一片不執行事前／事後腳本")
    ip.run("ce", "update", "lab-a", "--post-run=")
    screen = refuse(d, tmp_path, r"outdir", args=d.launch_args(tmp_path, params=("outdir=/elsewhere",)))
    assert "results" in screen


# ---- cancel ----------------------------------------------------------------------------------------------------------

def hand_over(data, run="run-one", slurm=4242, agent=None):
    """A row of the hand-off record as the platform writes it when an agent has answered a launch."""
    con = sqlite3.connect(str(data.ip.state_db))
    con.execute("INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at) "
                "VALUES (?, ?, ?, 'lab-a', ?, ?, ?)",
                (run, slurm, "%s/runs/%s" % (data.WORK, run), agent or data.agent, time.time(), time.time() if slurm else None))
    con.commit()
    con.close()


def test_tc040_a_cancel_shows_the_run_the_job_number_and_the_folder_and_asks(data, tmp_path):
    hand_over(data)
    p = start(data, tmp_path, "cancel", "run-one")
    assert p.wait_for(QUESTION_CANCEL, 30), p.text()
    assert (data.count("jobs"), data.count("confirmations")) == (0, 0)
    lines, _ = parts(p.text(), QUESTION_CANCEL)
    text = "\n".join(lines)
    assert "run-one" in text and "4242" in text and "/data/w1/runs/run-one" in text
    assert p.text().rstrip("\n").endswith(QUESTION_CANCEL)
    p.send("Y\n")
    p.finish(30)
    assert (data.count("jobs"), data.count("confirmations")) == (1, 1)
    job = data.rows("jobs")[0]
    assert job[3] == "cancel_run"
    args = json.loads(job[4])
    assert {k: args["bundle"][k] for k in ("run_name", "slurm_job_id", "run_folder", "agent")} == {
        "run_name": "run-one", "slurm_job_id": 4242, "run_folder": "/data/w1/runs/run-one", "agent": data.agent}
    assert data.rows("confirmations")[0][2] == "cancel"
    assert data.rows("launches")[0][-1] is None, "the request is recorded when the agent has sent it, not before"


@pytest.mark.parametrize("answer", ["n\n", "\n", "yes\n", "是\n"])
def test_tc041_a_cancel_not_confirmed_sends_nothing(data, tmp_path, answer):
    hand_over(data)
    p = start(data, tmp_path, "cancel", "run-one")
    assert p.wait_for(QUESTION_CANCEL, 30)
    p.send(answer)
    rc, screen = p.finish(30)
    assert rc != 0 and (data.count("jobs"), data.count("confirmations")) == (0, 0)


def test_tc041_a_cancel_without_a_terminal_sends_nothing(data, tmp_path):
    hand_over(data)
    p = Pty(["bash", "-c", 'echo y | "$@"', "_"] + cli_argv("cancel", "run-one"), data.env())
    rc, screen = p.finish(30)
    assert rc != 0 and re.search(r"終端機|terminal", screen)
    assert (data.count("jobs"), data.count("confirmations")) == (0, 0)


def test_tc042_a_cancel_of_something_the_platform_did_not_launch_is_refused_before_the_question(data, tmp_path):
    p = start(data, tmp_path, "cancel", "never-launched")
    rc, screen = p.finish(30)
    assert rc != 0 and QUESTION_CANCEL not in screen and re.search(r"不是平台|not launched|launches", screen)
    hand_over(data, run="not-submitted", slurm=None)
    p = start(data, tmp_path, "cancel", "not-submitted")
    rc, screen = p.finish(30)
    assert rc != 0 and QUESTION_CANCEL not in screen and re.search(r"Slurm|尚未送出", screen)
    assert (data.count("jobs"), data.count("confirmations")) == (0, 0)


def test_tc042_a_cancel_of_a_launch_of_another_agent_is_refused_before_the_question(data, tmp_path):
    hand_over(data, run="theirs", agent="agent-other")
    p = start(data, tmp_path, "cancel", "theirs")
    rc, screen = p.finish(30)
    assert rc != 0 and QUESTION_CANCEL not in screen and re.search(r"agent|代理", screen)
    assert (data.count("jobs"), data.count("confirmations")) == (0, 0)
