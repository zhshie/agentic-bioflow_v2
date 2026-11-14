# Nothing existing: test_publish_figure.py tests the action list_figures, but no MCP tool exposed it, and no test checked that the downstream prompt names the gallery tools.
"""The read tool list_figures (an AI client can see the gallery it published into) and the MCP path of the downstream prompt."""
import pathlib

import pytest

from helpers import tool_json
from human_harness import World
from test_publish_figure import call, fig, press
from test_web_board import seed

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def w(tmp_path, monkeypatch):
    import time
    world = World(tmp_path, monkeypatch)
    world.clock.t = time.time()
    return world


def lf(w, caller, rid, **kw):
    args = {"run_id": rid}
    args.update(kw)
    return tool_json(w.call("list_figures", args, caller=caller))


def test_list_figures_is_a_read_only_tool(w):
    tools, _ = w.mcp([])
    by = {t.name: t for t in tools}
    assert "list_figures" in by and by["list_figures"].annotations.read_only_hint is True
    props = by["list_figures"].input_schema["properties"]
    assert sorted(props) == ["packed_only", "run_id"] and by["list_figures"].input_schema["required"] == ["run_id"]
    d = by["list_figures"].description
    for s in ("gallery", "your own", "packed", "Nothing is written"):
        assert s in d, s


def test_list_figures_shows_what_was_published(w):
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    assert lf(w, ann, run) == {"found": True, "figures": []}
    press(w, "ann", call(w, ann, run, [fig("a.png", caption="first"), fig("b.png")])["request_id"])
    got = lf(w, ann, run)
    assert got["found"] is True and [f["name"] for f in got["figures"]] == ["a.png", "b.png"]
    assert got["figures"][0]["caption"] == "first" and got["figures"][0]["packed"] is False
    assert lf(w, ann, run, packed_only=True)["figures"] == []


def test_list_figures_tool_and_action_agree(w):
    import json
    from abf_platform import actions
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    press(w, "ann", call(w, ann, run, [fig()])["request_id"])
    assert lf(w, ann, run) == json.loads(json.dumps(actions.list_figures(w.ip.index, w.ip.state_db, run, caller=ann)))


def test_list_figures_hides_other_peoples_runs(w):
    ann, bob = w.user("ann"), w.user("bob")
    run = seed(w, "r1", "succeeded", ann)
    press(w, "ann", call(w, ann, run, [fig()])["request_id"])
    theirs, missing = lf(w, bob, run), lf(w, bob, "no-such-run")
    assert theirs["found"] is False and theirs == missing and "a.png" not in str(theirs)


def test_list_figures_writes_nothing(w):
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    before = (w.sql("SELECT COUNT(*) AS n FROM jobs")[0]["n"], w.sql("SELECT COUNT(*) AS n FROM confirmations")[0]["n"])
    lf(w, ann, run)
    assert (w.sql("SELECT COUNT(*) AS n FROM jobs")[0]["n"], w.sql("SELECT COUNT(*) AS n FROM confirmations")[0]["n"]) == before


def test_downstream_prompt_has_the_mcp_path_to_the_gallery():
    text = " ".join((ROOT / "skills" / "downstream" / "SKILL.md").read_text(encoding="utf-8").split())
    for s in ("publish_figure", "list_figures", "pack_figures", "delete_figure", "run_outputs", "read_run_file",
              "do not run `scripts/", "RStudio"):
        assert s in text, s
    # the MCP path comes before the terminal steps, so a chat client meets it first
    assert text.index("publish_figure") < text.index("## Before anything else")


def test_routing_instructions_name_the_gallery_tools():
    from abf_platform import guidance
    text = guidance.routing_instructions()
    assert "list_figures" in text and "publish_figure" in text and len(text.encode("utf-8")) <= guidance.MAX_BYTES
