# Nothing existing: tests of the two ways in to a resume and a relaunch, the MCP tools and the terminal commands (spec 009e); the words and the rules of the two doors are ours.
"""009e: the MCP tools resume and relaunch, the commands `abf-platform resume` and `relaunch`, the kit's ask rules and the skills text.
Test cases are named in the comments (TC-132 ...), see specs/009e-resume-relaunch/test-case.md."""
import json
import re
import time
from pathlib import Path

import pytest

from helpers import REPO_ROOT, tool_json
from human_harness import form_answer
from launch_harness import Pty, cli_argv
from resume_harness import SESSION, FakePerson, Rig
from test_launch_cli import parts

QUESTION_RESUME = "確定續跑？(y/N)"
QUESTION_RELAUNCH = "確定重跑？(y/N)"
NOT_FOUND = "找不到這個 run (Run not found): %s"
SENTENCE = "does not start anything until the person says yes"
YES_FIELDS = {"yes", "y", "confirm", "confirmed", "confirmation", "confirmation_id", "approve", "approved", "agree", "ok", "force", "送出", "kind",
              "command", "cmd", "script", "args", "shell"}


@pytest.fixture
def rig(tmp_path, monkeypatch):
    return Rig(tmp_path, monkeypatch)


@pytest.fixture
def duo(rig):
    from owner_harness import Duo
    return Duo(rig.w)


# ---- the MCP tools ----------------------------------------------------------------------------------------------------------------------

def tools_of(rig):
    tools, _ = rig.w.mcp([])
    return {t.name: t for t in tools}


def test_tc132_the_tools_are_the_old_ones_and_exactly_resume_and_relaunch(rig):
    # TC-132 (test_mcp.py tc024 is rewritten to the same list)
    assert sorted(tools_of(rig)) == ["cancel", "forget", "get_compute_env", "get_run", "launch", "list_agents", "list_compute_envs",
                                     "list_runs", "list_site_files", "read_task_log", "relaunch", "resume", "run_outputs"]       # keep-submissions (F3): plus forget


@pytest.mark.parametrize("name", ["resume", "relaunch"])
def test_tc133_tc134_tc135_each_new_tool_takes_one_argument_the_run_name_and_none_of_them_can_say_yes(rig, name):
    # TC-133, TC-134, TC-135 (resume-edit-params-b: resume also takes the two optional edits; relaunch still only the name)
    t = tools_of(rig)[name]
    props = t.input_schema.get("properties", {})
    assert set(props) == ({"run_name", "params", "extra_config"} if name == "resume" else {"run_name"})
    assert t.input_schema.get("required") == ["run_name"]
    assert props["run_name"].get("type") == "string"
    assert not (set(props) & YES_FIELDS)
    assert t.annotations.read_only_hint is False and t.annotations.destructive_hint is False


def test_tc136_the_descriptions_and_the_instructions_say_that_nothing_starts_until_the_person_says_yes(rig):
    # TC-136
    from abf_platform import guidance, mcp_server
    tools = tools_of(rig)
    for name in ("resume", "relaunch"):
        assert SENTENCE in tools[name].description, name
    assert SENTENCE in guidance.routing_instructions()
    assert SENTENCE in mcp_server.build_server(rig.index).instructions
    assert len(guidance.routing_instructions().encode("utf-8")) <= 2048


def test_the_descriptions_say_what_resume_and_relaunch_are_and_that_nothing_but_the_name_can_change(rig):
    tools = tools_of(rig)
    assert re.search(r"same folder|同一個資料夾", tools["resume"].description)
    assert re.search(r"new folder|全新的資料夾", tools["relaunch"].description)
    assert "params" in tools["resume"].description and "extra_config" in tools["resume"].description      # resume-edit-params-b
    assert re.search(r"samples|樣本", tools["resume"].description) and re.search(r"launch", tools["resume"].description)
    assert re.search(r"samples|樣本", tools["relaunch"].description) and re.search(r"launch", tools["relaunch"].description)


def test_tc080_tc136_the_tool_shows_the_person_the_form_and_queues_a_job_only_after_it_is_accepted(rig):
    rig.first("x")
    seen = []
    out = tool_json(rig.w.call("resume", {"run_name": "x"}, answer=form_answer(seen=seen)))
    assert out["sent"] is True and out["state"] == "queued" and out["job_id"]
    assert len(seen) == 1 and "這是續跑：同一個資料夾，沿用已完成的 task；樣本和參數不變" in seen[0].message
    assert rig.row_of_job(out["job_id"])["attempt_kind"] == "resume"
    rig.first("y")
    seen = []
    declined = tool_json(rig.w.call("relaunch", {"run_name": "y"}, answer=form_answer(action="decline", seen=seen)))
    assert declined["sent"] is False and len(seen) == 1 and "這是原樣重跑" in seen[0].message
    assert len(rig.jobs()) == 3      # the two first launches and the resume


def test_tc082_tc083_over_http_without_a_form_the_tool_answers_pending_and_the_page_address(rig, duo):
    first = duo.sent(duo.a, run="x")
    rig.hand_over(first["job_id"], "x")
    rig.set_run("x", "failed")
    for name in ("resume", "relaunch"):
        out = tool_json(rig.w.call(name, {"run_name": "x"}, caller=duo.a))
        assert out["sent"] is False and out["state"] == "pending" and "/c/" in out["confirmation_url"], out
    assert len(rig.jobs()) == 1


def test_009e_009i_a_connector_that_is_not_allow_listed_gets_the_page_only_for_resume_and_relaunch(rig, duo):
    # 009e x 009i: resume and relaunch go through the same _ask, so a connector whose client was not vetted is never shown the form
    from abf_platform import actions
    first = duo.sent(duo.a, run="x")
    rig.hand_over(first["job_id"], "x")
    rig.set_run("x", "failed")
    conn = actions.Caller.connector(duo.a.user_id, duo.a.name, duo.a.lab, False)
    for name in ("resume", "relaunch"):
        seen = []
        out = tool_json(rig.w.call(name, {"run_name": "x"}, caller=conn, answer=form_answer(seen=seen)))
        assert out["sent"] is False and out["state"] == "pending" and "/c/" in out["confirmation_url"], out
        assert seen == [], "the form must not be shown to a connector that is not allow-listed"
    assert len(rig.jobs()) == 1


def test_tc100_tc101_over_http_somebody_else_is_told_the_run_is_not_found(rig, duo):
    first = duo.sent(duo.a, run="x")
    rig.hand_over(first["job_id"], "x")
    rig.set_run("x", "failed")
    for name in ("resume", "relaunch"):
        out = tool_json(rig.w.call(name, {"run_name": "x"}, caller=duo.b, answer=form_answer()))
        assert out["sent"] is False and NOT_FOUND % "x" in out["message"], out
    assert len(rig.jobs()) == 1


def test_tc148_an_argument_other_than_the_run_name_changes_nothing(rig):
    # TC-148: either the call is refused, or the extra argument is dropped and the job is the plain resume of the first launch
    first = rig.first("x")
    _, outs = rig.w.mcp([("resume", {"run_name": "x", "revision": "9.9.9", "params": {"primer": "OTHER"}, "samplesheet": "/etc/passwd",
                                      "ce_name": "elsewhere", "session_id": "ffffffff-4f50-4a6b-8c7d-9e0f1a2b3c4d"})],
                         answer=form_answer())
    if outs[0].is_error:
        assert len(rig.jobs()) == 1
        return
    out = tool_json(outs[0])
    if out.get("sent"):
        b = rig.bundle_of_job(out["job_id"])
        # resume-edit-params-b: params is now an edit that is kept, in resume.overrides; the rest is still dropped
        assert b["resume"]["overrides"]["params"] == {"primer": "OTHER"}
        assert b["resume"]["origin"]["revision"] == "2.18.0" and b["resume"]["origin"]["params"] == first["params"]
        assert b["resume"]["session_id"] == SESSION and "samplesheet" not in b
    else:
        assert len(rig.jobs()) == 1


def test_tc137_the_kit_asks_for_the_two_new_tools_as_a_second_layer():
    # TC-137: no test of this file existed (the plan names one); it is new
    settings = json.loads((REPO_ROOT / "extensions" / "claude-code-kit" / "settings.json").read_text(encoding="utf-8"))
    ask = settings["permissions"]["ask"]
    for tool in ("launch", "cancel", "resume", "relaunch", "forget"):
        assert "mcp__abf-platform__%s" % tool in ask
    assert not [k for k in settings["permissions"] if k != "ask"], "the kit allows and denies nothing by itself"
    assert len(ask) == len(set(ask)) == 5


def test_tc138_the_skills_say_in_one_line_that_a_failed_run_can_be_resumed_or_started_over():
    # TC-138
    from abf_platform import guidance
    for name in ("operational", "runs"):
        text = guidance.read_skill(name, REPO_ROOT / "skills")
        lines = [ln for ln in text.splitlines() if re.search(r"\bresume\b", ln) and re.search(r"\brelaunch\b", ln)]
        assert lines, name
    # the generated text is the file's text (nothing is hand-edited)
    assert guidance.routing_instructions(REPO_ROOT / "skills") == guidance.routing_instructions()


# ---- the terminal ---------------------------------------------------------------------------------------------------------------------------

def test_tc140_tc141_tc147_the_commands_take_a_run_name_and_a_user_and_nothing_that_could_answer_or_change_the_analysis():
    # TC-140, TC-141, TC-147
    from abf_platform import cli
    p = cli.build_parser()
    for verb in ("resume", "relaunch"):
        ns = p.parse_args([verb, "x"])
        assert ns.run == "x" and ns.user is None and callable(ns.func)
        assert p.parse_args([verb, "x", "--user", "alice"]).user == "alice"
        for bad in (["--yes"], ["-y"], ["--force"], ["--assume-yes"], ["--no-confirm"], ["--y"], ["--params", "a.yaml"], ["--revision", "2.18.1"],
                    ["--samplesheet", "s.csv"], ["--ce", "other"], ["--pipeline", "nf-core/x"], ["--run-name", "n"],
                    ["--session", SESSION]):
            with pytest.raises(SystemExit):
                p.parse_args([verb, "x"] + bad)
        if verb == "relaunch":      # resume-edit-params-b: only resume takes --param (--params-file and --config-file are tested in the new file)
            with pytest.raises(SystemExit):
                p.parse_args([verb, "x", "--param", "a=b"])
        with pytest.raises(SystemExit):
            p.parse_args([verb])
        with pytest.raises(SystemExit):
            p.parse_args([verb, "x", "y"])


def start(rig, verb, run="x", *extra, **kw):
    return Pty(cli_argv(verb, run, *extra), kw.pop("env", None) or rig.w.data.env(), **kw)


@pytest.mark.parametrize("tc,verb,question,sentence", [
    ("TC-143", "resume", QUESTION_RESUME, "這是續跑：同一個資料夾，沿用已完成的 task；樣本和參數不變"),
    ("TC-143", "relaunch", QUESTION_RELAUNCH, "這是原樣重跑：全新資料夾，樣本與參數不變")])
def test_tc110_tc143_the_screen_with_the_command_comes_before_the_question(rig, tc, verb, question, sentence):
    # TC-110 (no users: a run that nobody owns), TC-143
    rig.first("x", slurm=4711)
    before = rig.counts()
    p = start(rig, verb)
    assert p.wait_for(question, 30), p.text()
    time.sleep(0.3)
    screen = p.text()
    lines, asked = parts(screen, question)
    text = "\n".join(lines)
    assert sentence in text and "4711" in text and "第 2 次" in text
    assert re.search(r"nextflow run .* -name x-a2 ", text)
    assert asked.strip() == question and screen.rstrip("\n").endswith(question)
    assert rig.counts() == before, "nothing is written while the question is open"
    p.send("n\n")
    rc, _ = p.finish(30)
    assert rc != 0


@pytest.mark.parametrize("verb,question", [("resume", QUESTION_RESUME), ("relaunch", QUESTION_RELAUNCH)])
def test_tc144_an_answer_other_than_y_queues_nothing(rig, verb, question):
    rig.first("x")
    before = rig.counts()
    for answer in ("n\n", "\n", "yes\n", "是\n"):
        p = start(rig, verb)
        assert p.wait_for(question, 30), p.text()
        p.send(answer)
        rc, screen = p.finish(30)
        assert rc != 0 and "未送出" in screen, (answer, screen[-200:])
        assert rig.counts() == before


@pytest.mark.parametrize("verb,question,kind", [("resume", QUESTION_RESUME, "resume"), ("relaunch", QUESTION_RELAUNCH, "relaunch")])
def test_tc145_y_queues_the_job_through_the_terminal_channel_and_says_what_became_of_it(rig, verb, question, kind):
    rig.first("x")
    p = start(rig, verb)
    assert p.wait_for(question, 30), p.text()
    p.send("y\n")
    rc, screen = p.finish(60)
    assert "已交給代理 agent-t" in screen, screen[-400:]
    assert len(rig.jobs()) == 2
    conf = rig.confirmations()[-1]
    assert (conf["channel"], conf["state"], conf["kind"]) == ("TERMINAL", "confirmed", "launch")
    row = rig.launches()[-1]
    assert (row["run_name"], row["parent_run"], row["attempt"], row["attempt_kind"]) == ("x-a2", "x", 2, kind)
    # no agent answers in this test: the report is the one of a launch whose agent never took the job
    assert rc != 0 and "代理沒有領走這個工作" in screen


NOT_A_TERMINAL = {
    "echo y piped in": ["bash", "-c", 'echo y | "$@"', "_"],
    "stdin from /dev/null": ["bash", "-c", '"$@" < /dev/null', "_"],
    "stdin closed": ["bash", "-c", '"$@" <&-', "_"],
}


@pytest.mark.parametrize("verb", ["resume", "relaunch"])
@pytest.mark.parametrize("how", sorted(NOT_A_TERMINAL))
def test_tc142_without_a_terminal_for_the_answer_nothing_is_queued(rig, verb, how):
    rig.first("x")
    before = rig.counts()
    p = Pty(NOT_A_TERMINAL[how] + cli_argv(verb, "x"), rig.w.data.env())
    rc, screen = p.finish(60)
    assert rc != 0 and "要在終端機上互動回答 y" in screen and "Traceback" not in screen, screen
    assert rig.counts() == before


@pytest.mark.parametrize("verb", ["resume", "relaunch"])
def test_tc142_a_program_with_no_controlling_terminal_is_refused_even_if_its_input_is_a_tty(rig, verb):
    rig.first("x")
    before = rig.counts()
    p = start(rig, verb, controlling=False)
    p.send("y\n")
    rc, screen = p.finish(60)
    assert rc != 0 and "要在終端機上互動回答 y" in screen and "Traceback" not in screen, screen
    assert rig.counts() == before


@pytest.mark.parametrize("flag", ["--yes", "-y", "--force"])
def test_tc141_no_flag_answers_for_the_person(rig, flag):
    rig.first("x")
    p = start(rig, "resume", "x", flag)
    rc, screen = p.finish(60)
    assert rc != 0 and re.search(r"unrecognized|usage", screen, re.I) and QUESTION_RESUME not in screen
    assert rig.counts()[0] == 1


@pytest.mark.parametrize("name", ["ABF_PLATFORM_ASSUME_YES", "ABF_PLATFORM_YES", "CI", "YES"])
def test_tc141_no_environment_variable_answers_for_the_person(rig, name):
    rig.first("x")
    p = start(rig, "resume", env=rig.w.data.env(**{name: "1" if name != "CI" else "true"}))
    assert p.wait_for(QUESTION_RESUME, 30), p.text()
    time.sleep(1.0)
    assert p.proc.poll() is None and rig.counts()[0] == 1
    p.send("n\n")
    p.finish(30)


@pytest.mark.parametrize("verb", ["resume", "relaunch"])
def test_tc108_once_users_exist_the_terminal_must_say_whose_it_is(rig, duo, verb):
    # TC-108
    out = duo.sent(duo.a, run="x")
    rig.hand_over(out["job_id"], "x")
    rig.set_run("x", "failed")
    rc, text = rig.w.ip.run(verb, "x")
    assert rc != 0 and "--user" in text
    assert len(rig.jobs()) == 1


@pytest.mark.parametrize("verb", ["resume", "relaunch"])
def test_tc109_the_terminal_names_somebody_who_is_not_the_owner_and_the_run_is_not_found(rig, duo, verb):
    # TC-109
    out = duo.sent(duo.a, run="x")
    rig.hand_over(out["job_id"], "x")
    rig.set_run("x", "failed")
    rc, text = rig.w.ip.run(verb, "x", "--user", "bob")
    assert rc != 0 and NOT_FOUND % "x" in text
    # the owner gets as far as the terminal question, which a test process has no terminal for
    rc, text = rig.w.ip.run(verb, "x", "--user", "alice")
    assert rc != 0 and "要在終端機上互動回答 y" in text and NOT_FOUND % "x" not in text
    assert rc != 0 and rig.w.ip.run(verb, "x", "--user", "nobody")[1].count("沒有這個帳號") == 1
    assert len(rig.jobs()) == 1


def test_tc131_launches_lists_the_attempt_number_the_kind_and_what_it_is_of(rig):
    # TC-131
    rig.first("x")
    rig.attempt("resume", "x")
    rig.attempt("relaunch", "x-a2")
    rc, text = rig.w.ip.run("launches")
    assert rc == 0
    assert "attempt 2 (resume of x)" in text and "attempt 3 (relaunch of x-a2)" in text
    lines = text.splitlines()
    heads = [ln for ln in lines if ln.startswith(("x ", "x-a2 ", "x-a3 "))]
    assert len(heads) == 3
    first = lines.index(heads[0])
    assert not any("attempt" in ln for ln in lines[first:first + 2]), "a first launch is not an attempt"
    i2 = lines.index(heads[1])
    assert any("attempt 2 (resume of x)" in ln for ln in lines[i2:i2 + 4])


def test_tc131_a_platform_made_before_the_columns_still_lists(tmp_path, monkeypatch):
    # an old row has no attempt: the list is as it always was
    rig = Rig(tmp_path, monkeypatch)
    rig.first("x")
    rc, text = rig.w.ip.run("launches")
    assert rc == 0 and "attempt" not in text and text.startswith("x ")
