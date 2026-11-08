# Nothing existing: tests of the site_link fact an agent reports about the shared connection to the site (mcp-site-connection-status).
"""own_facts site_link / site_link_at. TC numbers are in the comments, see the task's test case list."""
import datetime
import threading
from types import SimpleNamespace

from abf_station import agent as agent_mod, launch
from abf_station.site import SiteResult


class FakeSite:
    def __init__(self, rc=0, timed_out=False, raises=None):
        self.rc, self.timed_out, self.raises = rc, timed_out, raises
        self.calls = []

    def call(self, args, input=None, timeout=None):
        self.calls.append((list(args), timeout))
        if self.raises:
            raise self.raises
        return SiteResult(self.rc, b"", "", self.timed_out)


def ctx(tmp_path, reach, site):
    f = tmp_path / "env.yaml"
    f.write_text("reach: %s\n" % reach)
    return SimpleNamespace(site=site, settings_file=str(f), platform_url="https://p.example")


def used(site):
    return [c[0][0] for c in site.calls]


def test_ssh_check_master_1_is_closed_0_is_open_never_check_reach(tmp_path):
    # TC-015, TC-016, TC-019, TC-025
    for rc, want in ((1, "closed"), (0, "open")):
        s = FakeSite(rc=rc)
        assert launch.own_facts(ctx(tmp_path, "ssh", s))["site_link"] == want
        assert used(s) == ["--check-master"] and s.calls[0][1] == 3


def test_ssh_timeout_and_errors_are_unknown(tmp_path):
    # TC-017, TC-018, TC-019
    for s in (FakeSite(rc=124, timed_out=True), FakeSite(rc=2), FakeSite(rc=127), FakeSite(raises=OSError("boom")),
              FakeSite(raises=RuntimeError("x"))):
        assert launch.own_facts(ctx(tmp_path, "ssh", s))["site_link"] == "unknown"
        assert "--check-reach" not in used(s)


def test_local_is_open_and_none_is_unknown_without_any_call(tmp_path):
    # TC-020, TC-021
    s = FakeSite()
    assert launch.own_facts(ctx(tmp_path, "local", s))["site_link"] == "open"
    assert launch.own_facts(ctx(tmp_path, "none", s))["site_link"] == "unknown"
    assert s.calls == []


def test_site_link_at_is_iso(tmp_path):
    # TC-022
    for reach in ("ssh", "local", "none"):
        at = launch.own_facts(ctx(tmp_path, reach, FakeSite()))["site_link_at"]
        datetime.datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ")


class FakeClient:
    name = "a1"

    def __init__(self):
        self.posts = []

    def post(self, path, body, timeout):
        self.posts.append(body)
        return 200, {"agent": "a1"}


def test_failing_check_does_not_stop_hello(tmp_path):
    # TC-023
    c = ctx(tmp_path, "ssh", FakeSite(raises=RuntimeError("x")))
    a = agent_mod.Agent("https://p.example", "t", "a1", c)
    a.client = FakeClient()
    assert a.hello() == "a1"
    assert a.client.posts[0]["facts"]["site_link"] == "unknown"


def test_beat_recomputes_facts_each_time(tmp_path):
    # TC-024
    site = FakeSite(rc=0)
    c = ctx(tmp_path, "ssh", site)
    client = FakeClient()
    done = threading.Event()
    real_post = client.post

    def post(path, body, timeout):
        out = real_post(path, body, timeout)
        site.rc = 1       # after the first beat the connection is gone
        if len(client.posts) >= 2:
            done.set()
        return out
    client.post = post
    beat = agent_mod.Beat(client, 0.01, lambda: launch.own_facts(c))
    beat.start()
    assert done.wait(5)
    beat.finish()
    assert [p["facts"]["site_link"] for p in client.posts[:2]] == ["open", "closed"]


def test_idle_agent_says_facts_again_after_an_empty_poll(tmp_path):
    # TC-024 (idle side, plan amendment 2026-11-08): refresh_facts sends hello with the facts computed now, every time
    site = FakeSite(rc=0)
    c = ctx(tmp_path, "ssh", site)
    c.agent_name = "a1"
    a = agent_mod.Agent("https://p.example", "t", "a1", c)
    a.client = FakeClient()
    a.refresh_facts("a1")
    site.rc = 1
    a.refresh_facts("a1")
    assert [p["facts"]["site_link"] for p in a.client.posts] == ["open", "closed"]
    assert all(p["name"] == "a1" for p in a.client.posts)


def test_idle_refresh_failure_is_ignored(tmp_path):
    # TC-024 (idle side): a failing post or a failing check never stops the poll loop
    c = ctx(tmp_path, "ssh", FakeSite(rc=0))
    a = agent_mod.Agent("https://p.example", "t", "a1", c)

    class Down:
        name = "a1"

        def post(self, path, body, timeout):
            raise OSError("network down")
    a.client = Down()
    a.refresh_facts("a1")       # must not raise
    a.client = FakeClient()
    a.context = ctx(tmp_path, "ssh", FakeSite(raises=RuntimeError("x")))
    a.refresh_facts("a1")
    assert a.client.posts[0]["facts"]["site_link"] == "unknown"


def test_idle_refresh_is_rate_limited(tmp_path):
    # TC-024 (ruling 2026-11-08 no.5): the idle refresh runs at most once per facts_every seconds, whatever the poll rate
    a = agent_mod.Agent("https://p.example", "t", "a1", ctx(tmp_path, "ssh", FakeSite(rc=0)))
    a.client = FakeClient()
    assert a.facts_every == agent_mod.FACTS_EVERY == 25
    t = [100.0]
    a.clock = lambda: t[0]
    a.refresh_facts_if_due("a1")
    t[0] += 24
    a.refresh_facts_if_due("a1")
    assert len(a.client.posts) == 1
    t[0] += 1
    a.refresh_facts_if_due("a1")
    assert len(a.client.posts) == 2


def test_beat_facts_are_rate_limited(tmp_path):
    # TC-024 (job side, ruling 2026-11-08 no.5): the heartbeat of a running job asks the shared connection at most once per facts_every seconds
    s = FakeSite(rc=0)
    a = agent_mod.Agent("https://p.example", "t", "a1", ctx(tmp_path, "ssh", s))
    t = [100.0]
    a.clock = lambda: t[0]
    first = a.beat_facts()
    for _ in range(5):
        t[0] += 4
        assert a.beat_facts() == first
    assert len(s.calls) == 1
    t[0] += 10          # 30 s since the first look
    a.beat_facts()
    assert len(s.calls) == 2


def test_site_link_check_is_silent(tmp_path):
    # TC-024 (adversary): the read-only look prints nothing to the agent's terminal
    root = tmp_path / "plug"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "on_site.sh").write_text("exit 0\n")
    lines = []
    f = tmp_path / "env.yaml"
    f.write_text("reach: ssh\n")
    from abf_station.site import Site
    c = SimpleNamespace(site=Site(root, f, log=lines.append), settings_file=str(f), platform_url="https://p.example")
    assert launch.own_facts(c)["site_link"] == "open"
    assert lines == []
