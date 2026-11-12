# Nothing existing: no test covers a command on a user's own computer that proposes a figure to the platform's gallery and leaves the yes to the person at a link.
"""cli-fetch-publish-figure, slice 2: the publish-figure command (TC-056 to TC-068, with TC-071 and TC-078 for it). The answers of the tool are fakes
(studio_harness.FakeSite), no network is used; the cases with a real server are in test_studio_remote.py (TC-063, TC-065, TC-066).
Test case numbers are in the comments (specs/cli-fetch-publish-figure/test-case.md)."""
import ast
import base64
import os
import re
import time
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR
from studio_harness import FakeSite, patch_session
from test_web_wording_sweep import CJK_RE, banned_in

PKG = PLATFORM_DIR / "abf_platform"
PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) + b"\x00\x01\xff"
RID = "a1" * 16
PENDING_URL = "https://platform.example/c/" + RID


@pytest.fixture(autouse=True)
def _world(tmp_path, monkeypatch):
    for k in list(os.environ):
        if k.startswith("ABF_"):
            monkeypatch.delenv(k)
    monkeypatch.setenv("LC_ALL", "zh_TW.UTF-8")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.setenv("ABF_STUDIO_CONFIG", str(tmp_path / "cfg" / "studio.json"))
    (tmp_path / "home").mkdir()
    from abf_platform import studio_remote
    monkeypatch.setattr(studio_remote, "RETRY_DELAY", 0.0)
    monkeypatch.setattr(studio_remote, "CALL_TIMEOUT", 5.0)
    return tmp_path


def pending_answer(args=None):
    """What the tool says when it asks the person; the words for the chat channel are in `message`, and the command must not repeat them (P8)."""
    return {"ok": True, "sent": False, "state": "pending", "request_id": RID, "url": PENDING_URL, "count": 1, "summary": "fig.png",
            "message": "還沒存入 (nothing is written yet)。請本人打開這個網址：%s 或在聊天裡用 request_id=%s 與 user_confirmed=true 再呼叫一次" % (PENDING_URL, RID)}


def publish(argv, capsys):
    from abf_platform import cli
    try:
        rc = cli.main(["publish-figure"] + list(argv))
    except SystemExit as e:
        rc = e.code
    out = capsys.readouterr()
    return rc, out.out, out.err


def figure_files(tmp_path, data=PNG, code="plot(x)\r\n圖\n", params='{"a": 1}\n', name="fig.png"):
    d = tmp_path / "work"
    d.mkdir(exist_ok=True)
    (d / name).write_bytes(data)
    (d / "plot.R").write_bytes(code.encode("utf-8"))
    (d / "params.json").write_bytes(params.encode("utf-8"))
    return d


def parser_of_publish():
    from abf_platform import cli
    parser = cli.build_parser()
    return next(a for a in parser._actions if getattr(a, "choices", None) and "publish-figure" in a.choices).choices["publish-figure"]


def test_tc056_publish_figure_sends_one_figure_with_its_code_params_and_caption(tmp_path, capsys, monkeypatch):
    # TC-056
    site = FakeSite(publish=pending_answer)
    patch_session(monkeypatch, site)
    d = figure_files(tmp_path)
    rc, out, err = publish(["run1", str(d / "fig.png"), "--code", str(d / "plot.R"), "--params", str(d / "params.json"), "--caption", "圖說"], capsys)
    assert rc == 0, (out, err)
    assert [n for n, _ in site.calls] == ["publish_figure"]
    args = site.names("publish_figure")[0]
    assert args["run_id"] == "run1" and set(args) == {"run_id", "figures"} and len(args["figures"]) == 1
    fig = args["figures"][0]
    assert fig["filename"] == "fig.png" and base64.b64decode(fig["content_base64"]) == PNG
    assert fig["code"] == "plot(x)\r\n圖\n" and fig["params"] == '{"a": 1}\n' and fig["caption"] == "圖說"
    # what is not given is not sent
    site2 = FakeSite(publish=pending_answer)
    patch_session(monkeypatch, site2)
    rc, out, err = publish(["run1", str(d / "fig.png")], capsys)
    assert rc == 0 and set(site2.names("publish_figure")[0]["figures"][0]) == {"filename", "content_base64"}


def test_tc057_the_command_never_sends_a_yes_or_a_request_id(tmp_path, capsys, monkeypatch):
    # TC-057
    site = FakeSite(publish=pending_answer)
    patch_session(monkeypatch, site)
    d = figure_files(tmp_path)
    rc, out, err = publish(["run1", str(d / "fig.png")], capsys)
    assert rc == 0
    for args in site.names("publish_figure"):
        assert "user_confirmed" not in args and "request_id" not in args
        assert all("user_confirmed" not in f and "request_id" not in f for f in args["figures"])
    for name in ("studio_cli.py", "studio_remote.py"):
        text = (PKG / name).read_text(encoding="utf-8")
        assert "user_confirmed" not in text and "request_id" not in text, name


def test_tc058_a_pending_answer_prints_the_name_the_size_the_link_as_given_and_exits_0(tmp_path, capsys, monkeypatch):
    # TC-058, TC-061
    patch_session(monkeypatch, FakeSite(publish=pending_answer))
    d = figure_files(tmp_path)
    rc, out, err = publish(["run1", str(d / "fig.png")], capsys)
    text = out + err
    assert rc == 0
    assert "fig.png" in text and str(len(PNG)) in text
    assert "尚未存入；請本人在瀏覽器開啟下列連結並按送出" in text
    assert PENDING_URL in out.splitlines()       # the link is alone on its line, exactly as the tool gave it
    assert "不會加入交付包" in text                # TC-061
    assert banned_in(text) == []


def test_tc058_the_english_wording_has_no_cjk(tmp_path, capsys, monkeypatch):
    # TC-058 (English), TC-078
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")
    patch_session(monkeypatch, FakeSite(publish=pending_answer))
    d = figure_files(tmp_path)
    rc, out, err = publish(["run1", str(d / "fig.png")], capsys)
    text = (out + err).lower()
    assert rc == 0 and not CJK_RE.search(out + err) and PENDING_URL in out.splitlines()
    assert "not saved yet" in text and "not be added to the delivery bundle" in text


def test_tc059_one_call_no_waiting_and_never_says_it_was_saved(tmp_path, capsys, monkeypatch):
    # TC-059
    site = FakeSite(publish=pending_answer)
    patch_session(monkeypatch, site)
    d = figure_files(tmp_path)
    t0 = time.monotonic()
    rc, out, err = publish(["run1", str(d / "fig.png")], capsys)
    assert rc == 0 and len(site.names("publish_figure")) == 1 and len(site.calls) == 1
    assert time.monotonic() - t0 < 5 and "已存入" not in out + err


def test_tc060_the_tools_own_message_is_not_printed(tmp_path, capsys, monkeypatch):
    # TC-060
    patch_session(monkeypatch, FakeSite(publish=pending_answer))
    d = figure_files(tmp_path)
    rc, out, err = publish(["run1", str(d / "fig.png")], capsys)
    text = out + err
    assert "user_confirmed" not in text and "request_id=" not in text and "nothing is written yet" not in text and "聊天" not in text


@pytest.mark.parametrize("reason", ["圖庫已滿（最多 30 張）", "第 1 張「fig.png」未送出：檔名不合規定", "找不到 run「x」。請用 list_runs 查自己的 run 編號後再送"])
def test_tc062_a_refusal_prints_the_reason_as_given_and_exits_1(reason, tmp_path, capsys, monkeypatch):
    # TC-062
    site = FakeSite(publish={"ok": False, "sent": False, "state": "refused", "request_id": None, "url": None, "count": 0, "reason": reason, "message": reason + " (m)"})
    patch_session(monkeypatch, site)
    d = figure_files(tmp_path)
    rc, out, err = publish(["run1", str(d / "fig.png")], capsys)
    assert rc == 1 and reason in out + err and "尚未存入" not in out + err and "已存入" not in out + err
    assert "(m)" not in out + err                 # the message is not printed, only the reason


def test_tc062_the_words_of_the_platform_are_cleaned_before_they_are_shown(tmp_path, capsys, monkeypatch):
    # TC-062 with R10
    reason = "bad\x1b[31m name\x9b‮ end"
    patch_session(monkeypatch, FakeSite(publish={"state": "refused", "reason": reason}))
    d = figure_files(tmp_path)
    rc, out, err = publish(["run1", str(d / "fig.png")], capsys)
    assert rc == 1 and "\x1b" not in out + err and "\x9b" not in out + err and "‮" not in out + err and "bad" in out + err


@pytest.mark.parametrize("answer", [{"state": "pending"}, {"state": "pending", "url": 5}, {"state": "weird"}, {}, {"state": "refused"}])
def test_an_answer_that_is_none_of_the_three_is_one_sentence_and_exit_1(answer, tmp_path, capsys, monkeypatch):
    # TC-062 (odd answers); no stack, and never "not saved yet" without a link to give
    patch_session(monkeypatch, FakeSite(publish=answer))
    d = figure_files(tmp_path)
    rc, out, err = publish(["run1", str(d / "fig.png")], capsys)
    assert rc == 1 and "Traceback" not in out + err and "尚未存入" not in out + err and (out + err).strip()


def test_a_state_ok_answer_is_told_as_saved_privately_and_not_in_the_bundle(tmp_path, capsys, monkeypatch):
    # TC-061 (the other state of the tool)
    patch_session(monkeypatch, FakeSite(publish={"state": "ok", "count": 1}))
    d = figure_files(tmp_path)
    rc, out, err = publish(["run1", str(d / "fig.png")], capsys)
    assert rc == 0 and "私有圖庫" in out and "不會加入交付包" in out


def test_tc064_the_limits_are_checked_here_and_said_by_name_without_calling_the_tool(tmp_path, capsys, monkeypatch):
    # TC-064
    from abf_platform.actions import figures
    site = FakeSite(publish=pending_answer)
    patch_session(monkeypatch, site)
    d = figure_files(tmp_path)
    big = d / "big.png"
    big.write_bytes(PNG[:8] + b"\0" * figures.MAX_BUNDLE_BYTES)
    (d / "longcode.R").write_bytes(b"#" * (figures.MAX_CODE_BYTES + 1))
    (d / "longparams.json").write_bytes(b"1" * (figures.MAX_PARAMS_BYTES + 1))
    cases = [
        (["run1", str(d / "nope.png")], "nope.png"),                                                          # (a) not there
        (["run1", str(d)], str(d)),                                                                           # (a) a folder, not a file
        (["run1", str(big)], "big.png"),                                                                      # (b) over the bundle limit
        (["run1", str(d / "fig.png"), "--code", str(d / "fig.png")], "fig.png"),                              # (c) not UTF-8
        (["run1", str(d / "fig.png"), "--code", str(d / "none.R")], "none.R"),                                # (c) missing
        (["run1", str(d / "fig.png"), "--caption", "x" * (figures.MAX_CAPTION_CHARS + 1)], "caption"),        # (d)
        (["run1", str(d / "fig.png"), "--caption", "a\nb"], "caption"),                                       # one line only
        (["run1", str(d / "fig.png"), "--caption", "a\x07b"], "caption"),
        (["run1", str(d / "fig.png"), "--code", str(d / "longcode.R")], "code"),
        (["run1", str(d / "fig.png"), "--params", str(d / "longparams.json")], "params"),
    ]
    for argv, word in cases:
        rc, out, err = publish(argv, capsys)
        assert rc not in (0, None) and word in out + err and "Traceback" not in out + err, (argv, rc, out, err)
    assert site.calls == []
    # the edge: exactly at the limit goes through
    (d / "okcode.R").write_bytes(b"#" * figures.MAX_CODE_BYTES)
    rc, out, err = publish(["run1", str(d / "fig.png"), "--code", str(d / "okcode.R"), "--caption", "c" * figures.MAX_CAPTION_CHARS], capsys)
    assert rc == 0 and len(site.calls) == 1


def test_tc064_the_code_limit_counts_bytes_and_text_that_cannot_be_utf8_is_refused(tmp_path, capsys, monkeypatch):
    # TC-064 with R7: the limit is in bytes (a Chinese character is three), and a lone surrogate is refused here
    from abf_platform.actions import figures
    site = FakeSite(publish=pending_answer)
    patch_session(monkeypatch, site)
    d = figure_files(tmp_path)
    (d / "wide.R").write_bytes("圖".encode("utf-8") * (figures.MAX_CODE_BYTES // 3 + 1))
    rc, out, err = publish(["run1", str(d / "fig.png"), "--code", str(d / "wide.R")], capsys)
    assert rc not in (0, None) and "code" in out + err
    rc, out, err = publish(["run1", str(d / "fig.png"), "--caption", "a\udc80b"], capsys)
    assert rc not in (0, None) and "Traceback" not in out + err and "caption" in out + err
    rc, out, err = publish(["run1", str(d / "fig\udc80.png")], capsys)
    assert rc not in (0, None) and "Traceback" not in out + err
    assert site.calls == []


def test_tc064_the_source_names_the_limits_and_writes_no_number_of_its_own():
    # TC-064
    text = (PKG / "studio_cli.py").read_text(encoding="utf-8")
    for name in ("MAX_BUNDLE_BYTES", "MAX_CODE_BYTES", "MAX_PARAMS_BYTES", "MAX_CAPTION_CHARS"):
        assert re.search(r"from \.actions\.figures import [^\n]*\b%s\b" % name, text), name
    tree = ast.parse(text)
    fns = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and "publish" in n.name]
    assert fns
    for fn in fns:
        numbers = {n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool)}
        assert not numbers & {5, 10, 100, 200, 1024, 10240, 102400, 5242880}, (fn.name, numbers)


def test_tc067_nothing_is_requested_from_the_link_and_no_browser_is_opened(tmp_path, capsys, monkeypatch):
    # TC-067
    import socket
    import webbrowser
    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda *a, **k: opened.append(a))

    def refuse(*a, **k):
        raise AssertionError("a network connection was made")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    site = FakeSite(publish=pending_answer)
    patch_session(monkeypatch, site)
    d = figure_files(tmp_path)
    rc, out, err = publish(["run1", str(d / "fig.png")], capsys)
    assert rc == 0 and opened == [] and [n for n, _ in site.calls] == ["publish_figure"]
    for name in ("studio_cli.py", "studio_remote.py"):
        assert "webbrowser" not in (PKG / name).read_text(encoding="utf-8")


def test_tc068_there_is_nothing_to_pack_or_delete_and_only_publish_figure_is_called(tmp_path, capsys, monkeypatch):
    # TC-068
    sub = parser_of_publish()
    options = {o for a in sub._actions for o in a.option_strings}
    assert options == {"-h", "--help", "--code", "--params", "--caption"}, options
    helptext = sub.format_help().lower()
    for word in ("pack", "delete", "remove", "select", "confirm", "launch", "submit", "cancel"):
        assert word not in helptext, word
    site = FakeSite(publish=pending_answer)
    patch_session(monkeypatch, site)
    d = figure_files(tmp_path)
    publish(["run1", str(d / "fig.png")], capsys)
    assert {n for n, _ in site.calls} == {"publish_figure"}


def test_tc071_publish_figure_is_registered_last_and_help_exits_0(capsys):
    # TC-071 (the registration half)
    from abf_platform import cli
    parser = cli.build_parser()
    top = next(a for a in parser._actions if getattr(a, "choices", None) and "publish-figure" in a.choices)
    assert list(top.choices)[-3:] == ["studio-connect", "fetch-results", "publish-figure"]
    assert parser_of_publish().allow_abbrev is False
    with pytest.raises(SystemExit) as e:
        cli.main(["publish-figure", "--help"])
    assert e.value.code == 0
    assert "--user" not in capsys.readouterr().out


def test_tc078_publish_figure_strings_have_the_same_keys_and_the_zh_is_written_chinese():
    # TC-078
    from abf_platform import studio_cli
    zh, en = studio_cli.STRINGS["zh"], studio_cli.STRINGS["en"]
    assert set(zh) == set(en) and any(k.startswith("pub_") for k in zh)
    assert all(not CJK_RE.search(v) for v in en.values()) and all(banned_in(v) == [] for v in zh.values())


# ---- with a real server: nothing is written before the person says yes (TC-063, TC-065, TC-066, TC-040, TC-079, TC-082) --------------------

from test_studio_remote import SECRET, main as remote_main, server, write_config      # noqa: E402,F401  (the module's own real server, used as a fixture)


def counts(server):
    import sqlite3
    con = sqlite3.connect(str(server["plat"].dir / "platform.db"))
    try:
        return {t: con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0] for t in ("confirmations", "jobs")}
    finally:
        con.close()


def gallery_of(server, caller):
    from abf_platform import actions
    return actions.list_figures(server["plat"].index, server["plat"].dir / "platform.db", server["run"], caller=caller)


def alice(server):
    from abf_platform import actions
    return actions.Caller(server["alice_id"], "alice", "lab-x")


def test_tc065_tc066_a_pending_request_writes_nothing_and_the_persons_yes_at_the_page_puts_it_in_the_private_gallery(server, tmp_path, capsys):
    # TC-065, TC-066
    from abf_platform import actions
    d = figure_files(tmp_path)
    write_config(tmp_path, server["url"], token=server["alice"])
    before = counts(server)
    rc, out, err = remote_main(["publish-figure", server["run"], str(d / "fig.png"), "--code", str(d / "plot.R"), "--params", str(d / "params.json"),
                                "--caption", "圖說"], capsys)
    assert rc == 1 or rc == 0
    assert rc == 0, (out, err)
    link = [ln for ln in out.splitlines() if "/c/" in ln]
    assert len(link) == 1 and link[0].strip().endswith(link[0].strip().split("/c/")[-1])
    rid = link[0].strip().split("/c/")[-1]
    after = counts(server)
    assert after["confirmations"] == before["confirmations"] + 1 and after["jobs"] == before["jobs"]      # a request, no job
    assert gallery_of(server, alice(server))["figures"] == []                                            # nothing written yet (TC-065)
    assert SECRET not in out + err and server["alice"] not in out + err
    # TC-066: the person presses the button of the page as the same user; only then is the figure in the gallery, and not in the bundle
    actions.approve(server["plat"].dir / "platform.db", rid, confirmed_by=actions.PAGE, caller=alice(server))
    got = gallery_of(server, alice(server))["figures"]
    assert [f["name"] for f in got] == ["fig.png"] and got[0]["packed"] is False and got[0]["caption"] == "圖說"
    assert gallery_of(server, alice(server)) and actions.list_figures(server["plat"].index, server["plat"].dir / "platform.db", server["run"],
                                                                      caller=alice(server), packed_only=True)["figures"] == []
    assert counts(server)["jobs"] == before["jobs"]


def test_tc063_somebody_elses_run_and_a_missing_run_get_the_same_sentence_and_nothing_is_asked(server, tmp_path, capsys):
    # TC-063
    d = figure_files(tmp_path)
    write_config(tmp_path, server["url"], token=server["bob"])
    before = counts(server)
    rc1, out1, err1 = remote_main(["publish-figure", server["run"], str(d / "fig.png")], capsys)
    rc2, out2, err2 = remote_main(["publish-figure", "no-such-run-0000", str(d / "fig.png")], capsys)
    # the platform's reason names the run id that was asked, so the two differ by that id only
    assert rc1 == rc2 == 1 and "找不到" in out1 + err1 and "run not found" in (out1 + err1)
    assert (out1 + err1).replace(server["run"], "ID") == (out2 + err2).replace("no-such-run-0000", "ID")
    assert counts(server) == before
    from abf_platform import actions
    assert [f for f in gallery_of(server, alice(server))["figures"] if f["name"] != "fig.png"] == []
    assert server["bob"] not in out1 + err1


def test_tc040_a_wrong_or_revoked_token_gives_the_token_message_for_publish_figure_too(server, tmp_path, capsys):
    # TC-040 (slice 2)
    from abf_platform import studio_remote
    d = figure_files(tmp_path)
    for token in ("abf_pat_" + "x" * 43, server["revoked"]):
        write_config(tmp_path, server["url"], token=token)
        rc, out, err = remote_main(["publish-figure", server["run"], str(d / "fig.png")], capsys)
        assert rc == 3 and studio_remote.tr("token_bad") in err and token not in out + err


def test_tc079_tc082_the_token_is_not_printed_and_no_database_is_opened_by_publish_figure(server, tmp_path, capsys, monkeypatch):
    # TC-079, TC-082 (slice 2)
    import subprocess
    import sys
    from helpers import pkg_env
    empty = tmp_path / "emptydb"
    empty.mkdir()
    d = figure_files(tmp_path)
    patch_session(monkeypatch, FakeSite(publish=pending_answer))
    write_config(tmp_path, "https://platform.example", token=SECRET)
    monkeypatch.setenv("ABF_PLATFORM_DB", str(empty / "index.db"))
    rc, out, err = remote_main(["publish-figure", "run1", str(d / "fig.png")], capsys)
    assert rc == 0 and SECRET not in out + err and list(empty.iterdir()) == []
    env = pkg_env(ABF_PLATFORM_DB=empty / "index.db", ABF_STUDIO_CONFIG=str(tmp_path / "nowhere" / "studio.json"))
    r = subprocess.run([sys.executable, "-m", "abf_platform", "publish-figure", "run1", str(d / "fig.png")], env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 2 and list(empty.iterdir()) == []


def test_tc081_json_for_publish_figure_does_not_crash_and_has_no_token(tmp_path, capsys, monkeypatch):
    # TC-081 (slice 2)
    import json
    d = figure_files(tmp_path)
    patch_session(monkeypatch, FakeSite(publish=pending_answer))
    write_config(tmp_path, "https://platform.example", token=SECRET)
    rc, out, err = remote_main(["--json", "publish-figure", "run1", str(d / "fig.png")], capsys)
    assert rc == 0 and json.loads(out)["ok"] is True and SECRET not in out + err
    rc, out, err = remote_main(["--json", "publish-figure", "run1", str(d / "nope.png")], capsys)
    assert rc not in (0, None) and json.loads(err)["ok"] is False and SECRET not in out + err
