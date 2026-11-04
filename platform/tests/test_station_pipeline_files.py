# Nothing existing: tests of the agent's pipeline_files job against a stand-in for the internet; no earlier test reads public GitHub files.
"""release-lookup-job, the agent side (S-01 to S-19): the agent reads five kinds of public file (the fifth is nf-core's own pipeline list, test_nfcore_catalogue.py) and nothing else.

The one place that connects is `pipeline_files.OPEN`; every test here replaces it, and an autouse guard makes any test that
forgets to do so fail instead of reaching the real GitHub (TC-043). Test cases are named in the comments (TC-001 ...).
"""
import base64
import http.server
import json
import re
import threading
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from station_harness import FakePlatform, FakeSite
from test_station_fakeplatform import agent_on

from abf_platform import releases
from abf_station import agent, handlers, pipeline_files

STATION = PLATFORM_DIR / "abf_station"
SCHEMA_FILE = PLATFORM_DIR / "tests" / "fixtures" / "schema" / "ampliseq-2.18.0.nextflow_schema.json"
INPUT_FILE = REPO_ROOT / "tests" / "fixtures" / "schema_input" / "ampliseq-2.18.0.json"
RAW = "https://raw.githubusercontent.com/nf-core/ampliseq/2.18.0/"
SCHEMA_URL = RAW + "nextflow_schema.json"
INPUT_URL = RAW + "assets/schema_input.json"
API_URL = "https://api.github.com/repos/nf-core/ampliseq/contents/docs/images?ref=2.18.0"
IMAGE_URL = RAW + "docs/images/ampliseq_workflow.png"
TAGS_URL = "https://github.com/nf-core/ampliseq.git/info/refs?service=git-upload-pack"
ADVERT = "application/x-git-upload-pack-advertisement"
PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 4
EIGHT = ("preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records", "read_task_log", "clean_work", "put_upload")
LISTING = [
    {"name": "ampliseq_workflow.png", "type": "file", "size": 753702},
    {"name": "ampliseq_workflow.svg", "type": "file", "size": 348755},
    {"name": "ampliseq_workflow_multiplesequencingruns.png", "type": "file", "size": 189695},
    {"name": "ampliseq_workflow_multiplesequencingruns.svg", "type": "file", "size": 228700},
]


class Net:
    """The stand-in for pipeline_files.OPEN: answers from a table, records every request, and reads at most limit + 1 bytes."""

    def __init__(self):
        self.routes = {}
        self.calls = []

    def __call__(self, url, headers, timeout, limit):
        self.calls.append({"url": url, "headers": dict(headers), "timeout": timeout, "limit": limit})
        answer = self.routes.get(url)
        if answer is None:
            return 404, {}, b""
        if isinstance(answer, BaseException):
            raise answer
        status, headers_out, body = answer
        return status, dict(headers_out), body[:limit + 1]

    def urls(self):
        return [c["url"] for c in self.calls]

    def ok(self, url, body, headers=None):
        self.routes[url] = (200, headers or {}, body)


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch):
    # TC-043: the default OPEN is replaced by something that fails the test that reaches it
    def forbidden(url, headers, timeout, limit):
        raise AssertionError("a test reached the real network: %s" % url)
    monkeypatch.setattr(pipeline_files, "OPEN", forbidden)


@pytest.fixture
def net(monkeypatch):
    n = Net()
    monkeypatch.setattr(pipeline_files, "OPEN", n)
    return n


@pytest.fixture
def ctx():
    return agent.Context(None, "settings.yaml", "", "a1")


def job(parts, repo="nf-core/ampliseq", revision="2.18.0", **extra):
    args = {"repo": repo, "revision": revision, "parts": parts}
    args.update(extra)
    return {"id": 1, "kind": "pipeline_files", "args": args}


def pkt(text):
    raw = text if isinstance(text, bytes) else text.encode()
    return b"%04x" % (len(raw) + 4) + raw


def advert(refs):
    out = pkt("# service=git-upload-pack\n") + b"0000"
    for i, ref in enumerate(refs):
        line = ("%040x %s" % (i + 1, ref)).encode()
        if i == 0:
            line += b"\0multi_ack thin-pack side-band agent=git/github-x"
        out += pkt(line + b"\n")
    return out + b"0000"


TAG_REFS = ["HEAD", "refs/heads/main", "refs/pull/1/head", "refs/tags/2.18.0", "refs/tags/2.18.0^{}", "refs/tags/3.0.0", "refs/tags/3.0.0dev"]


def all_ok(net):
    net.ok(SCHEMA_URL, SCHEMA_FILE.read_bytes())
    net.ok(INPUT_URL, INPUT_FILE.read_bytes())
    net.ok(API_URL, json.dumps(LISTING).encode())
    net.ok(IMAGE_URL, PNG)
    net.ok(TAGS_URL, advert(TAG_REFS), {"Content-Type": ADVERT})


def run(ctx, j):
    return handlers.handle(j, ctx)


# ---- the kinds and the arguments ----------------------------------------------------------------

def test_tc001_pipeline_files_is_last_and_the_others_keep_their_order():
    # TC-001
    assert handlers.JOB_KINDS.count("pipeline_files") == 1 and handlers.JOB_KINDS[-2:] == ("pipeline_files", "read_run_file")
    assert tuple(k for k in handlers.JOB_KINDS if k != "pipeline_files")[:len(EIGHT)] == EIGHT


def test_tc002_arguments_are_repo_revision_parts():
    # TC-002
    assert handlers.ARG_KEYS["pipeline_files"] == {"repo", "revision", "parts"}
    assert set(handlers.JOB_KINDS) == set(handlers.ARG_KEYS)


def test_tc003_an_unknown_kind_is_refused_and_names_the_supported_ones(ctx):
    # TC-003
    state, out = run(ctx, {"kind": "frobnicate", "args": {}})
    assert state == "refused" and "pipeline_files" in out["message"]


# ---- hosts ----------------------------------------------------------------------------------------

def test_tc004_the_four_hosts_are_allowed():
    # TC-004
    for url in ("https://github.com/nf-core/ampliseq.git/info/refs?service=git-upload-pack", RAW + "nextflow_schema.json", API_URL,
                "https://nf-co.re/pipelines.json"):
        assert pipeline_files.allowed(url) is True


BAD_URLS = ["http://github.com/x", "https://github.com.evil.com/x", "https://evil.com/github.com", "https://raw.githubusercontent.com@evil.com/x",
            "https://raw.githubusercontent.com:8443/x", "ftp://github.com/x", "http://nf-co.re/pipelines.json", "https://nf-co.re.evil.com/pipelines.json",
            "https://www.nf-co.re/pipelines.json", "",
            "https://user:pw@github.com/x", "https://github.com:443/x", " https://github.com/x", None, 5]


def test_tc005_every_other_address_is_not_allowed():
    # TC-005
    assert [u for u in BAD_URLS if pipeline_files.allowed(u)] == []


def test_tc006_a_refused_address_never_reaches_open(net, monkeypatch, ctx):
    # TC-006: even if a checked value somehow built a bad address, the check runs before OPEN
    fetcher = pipeline_files._Fetcher()
    for url in BAD_URLS:
        with pytest.raises(Exception):
            fetcher.get(url, "*/*", 10)
    assert net.calls == []


# ---- the files ------------------------------------------------------------------------------------

def test_tc007_tc008_tc009_the_three_parts_of_ampliseq(net, ctx):
    # TC-007, TC-008, TC-009
    all_ok(net)
    state, out = run(ctx, job(["schema", "schema_input", "diagram"]))
    assert net.urls() == [SCHEMA_URL, INPUT_URL, API_URL]
    assert state == "done" and out["ok"] is True
    assert out["parts"]["schema"]["status"] == "ok" and out["parts"]["schema"]["text"] == SCHEMA_FILE.read_text(encoding="utf-8")
    assert out["parts"]["schema_input"]["text"] == INPUT_FILE.read_text(encoding="utf-8")
    assert set(out["parts"]) == {"schema", "schema_input", "diagram"}
    assert out["parts"]["diagram"] == {"status": "ok", "name": "ampliseq_workflow.png", "type": "image/png", "size": 753702}


def entry(name, size=100, kind="file"):
    e = {"name": name, "type": kind}
    if size is not None:
        e["size"] = size
    return e


@pytest.mark.parametrize("entries,expected", [
    ([entry("ampliseq_workflow.png"), entry("x_metro.svg")], "x_metro.svg"),            # metro first, even as an svg
    ([entry("a_workflow.svg"), entry("a_workflow.png")], "a_workflow.png"),             # png before svg
    ([entry("long_name_workflow.png"), entry("w_workflow.png")], "w_workflow.png"),     # the shorter name
    ([entry("b_workflow.png"), entry("a_workflow.png")], "a_workflow.png"),             # then the alphabet
])
def test_tc010_the_diagram_is_picked_by_rule(net, ctx, entries, expected):
    # TC-010
    net.ok(API_URL, json.dumps(entries).encode())
    state, out = run(ctx, job(["diagram"]))
    assert state == "done" and out["parts"]["diagram"]["name"] == expected


def test_tc011_a_candidate_that_is_too_large_is_skipped_and_an_unknown_size_is_kept(net, ctx):
    # TC-011
    net.ok(API_URL, json.dumps([entry("a_workflow.png", 2000001), entry("b_workflow.png", 100)]).encode())
    assert run(ctx, job(["diagram"]))[1]["parts"]["diagram"]["name"] == "b_workflow.png"
    net.ok(API_URL, json.dumps([entry("a_workflow.png", None)]).encode())
    assert run(ctx, job(["diagram"]))[1]["parts"]["diagram"]["name"] == "a_workflow.png"


def test_tc012_all_candidates_too_large(net, ctx):
    # TC-012
    net.ok(API_URL, json.dumps([entry("a_workflow.png", 2000001), entry("b_workflow.svg", 5000000)]).encode())
    assert run(ctx, job(["diagram"]))[1]["parts"]["diagram"]["status"] == "too_large"


def test_tc013_no_candidate_is_none(net, ctx):
    # TC-013
    net.ok(API_URL, json.dumps([entry("readme.png"), entry("my workflow.png"), entry("..%2Fx_workflow.png"), entry("a_workflow.gif"),
                                entry("a_workflow.png", 5, "dir")]).encode())
    assert run(ctx, job(["diagram"]))[1]["parts"]["diagram"] == {"status": "none"}
    net.routes[API_URL] = (404, {}, b"")
    assert run(ctx, job(["diagram"]))[1]["parts"]["diagram"] == {"status": "none"}
    net.ok(API_URL, json.dumps([entry("../x_workflow.png"), entry("a b_workflow.png")]).encode())
    assert run(ctx, job(["diagram"]))[1]["parts"]["diagram"] == {"status": "none"}


def test_tc014_tc015_the_image(net, ctx):
    # TC-014, TC-015
    all_ok(net)
    state, out = run(ctx, job(["image"]))
    assert net.urls() == [API_URL, IMAGE_URL]
    assert state == "done"
    image = out["parts"]["image"]
    assert image["status"] == "ok" and image["type"] == "image/png" and base64.b64decode(image["data_b64"]) == PNG
    assert out["parts"]["diagram"]["name"] == "ampliseq_workflow.png"


def test_tc016_an_image_that_is_not_what_it_says(net, ctx):
    # TC-016
    net.ok(API_URL, json.dumps(LISTING).encode())
    net.ok(IMAGE_URL, b"<html>not a png</html>")
    assert run(ctx, job(["image"]))[1]["parts"]["image"]["status"] == "bad_response"
    net.ok(API_URL, json.dumps([entry("a_workflow.svg")]).encode())
    svg = RAW + "docs/images/a_workflow.svg"
    net.ok(svg, b"<html>" + b"x" * 5000 + b"<svg")
    assert run(ctx, job(["image"]))[1]["parts"]["image"]["status"] == "bad_response"
    net.ok(svg, b"\xff\xfe<svg")
    assert run(ctx, job(["image"]))[1]["parts"]["image"]["status"] == "bad_response"
    net.ok(svg, b"<?xml version='1.0'?><svg xmlns='http://www.w3.org/2000/svg'></svg>")
    ok = run(ctx, job(["image"]))[1]["parts"]["image"]
    assert ok["status"] == "ok" and ok["type"] == "image/svg+xml"


def test_tc017_an_image_over_the_limit(net, ctx):
    # TC-017
    net.ok(API_URL, json.dumps(LISTING).encode())
    net.ok(IMAGE_URL, PNG + b"0" * 2000000)
    out = run(ctx, job(["image"]))[1]
    assert out["parts"]["image"]["status"] == "too_large" and "data_b64" not in out["parts"]["image"]
    assert max(c["limit"] for c in net.calls if c["url"] == IMAGE_URL) == 2000000


# ---- the tags -----------------------------------------------------------------------------------------

def test_tc018_tc019_the_tag_list(net, ctx):
    # TC-018, TC-019
    net.ok(TAGS_URL, advert(TAG_REFS), {"Content-Type": ADVERT})
    state, out = run(ctx, job(["tags"], revision=None))
    assert net.urls() == [TAGS_URL]
    text = out["parts"]["tags"]["text"]
    sha = lambda n: "%040x" % n
    assert text == "%s\trefs/tags/2.18.0\n%s\trefs/tags/3.0.0\n%s\trefs/tags/3.0.0dev\n" % (sha(4), sha(6), sha(7))
    tags = releases.parse_ls_remote(text)
    assert tags == ["2.18.0", "3.0.0", "3.0.0dev"] and releases.pick_latest(tags) == "3.0.0"


def test_tc020_a_tag_list_that_is_not_one(net, ctx):
    # TC-020
    good = advert(TAG_REFS)
    for headers, body in (({"Content-Type": "text/html"}, good), ({"Content-Type": ADVERT}, b"zzzz" + good[4:]),
                          ({"Content-Type": ADVERT}, good[:len(good) // 2]), ({"Content-Type": ADVERT}, good[:-4])):
        net.routes[TAGS_URL] = (200, headers, body)
        assert run(ctx, job(["tags"], revision=None))[1]["parts"]["tags"]["status"] == "bad_response"


def test_tc021_a_tag_list_over_the_limit(net, ctx):
    # TC-021
    net.routes[TAGS_URL] = (200, {"Content-Type": ADVERT}, b"x" * 4000001)
    assert run(ctx, job(["tags"], revision=None))[1]["parts"]["tags"]["status"] == "too_large"


# ---- trouble ---------------------------------------------------------------------------------------

def test_tc022_one_file_missing_is_a_part_not_a_failure(net, ctx):
    # TC-022
    all_ok(net)
    del net.routes[INPUT_URL]
    state, out = run(ctx, job(["schema", "schema_input"]))
    assert state == "done" and out["ok"] is True
    assert out["parts"]["schema_input"]["status"] == "not_found" and out["parts"]["schema"]["status"] == "ok"


def test_tc023_a_schema_over_the_limit_has_no_text(net, ctx):
    # TC-023
    net.ok(SCHEMA_URL, b"x" * 1000001)
    part = run(ctx, job(["schema"]))[1]["parts"]["schema"]
    assert part["status"] == "too_large" and "text" not in part


def test_tc024_a_limit_from_github(net, ctx):
    # TC-024
    net.routes[API_URL] = (403, {"X-RateLimit-Remaining": "0"}, b"rate limit exceeded")
    assert run(ctx, job(["diagram"]))[1]["parts"]["diagram"]["status"] == "rate_limited"
    net.routes[API_URL] = (429, {}, b"")
    assert run(ctx, job(["diagram"]))[1]["parts"]["diagram"]["status"] == "rate_limited"


def test_tc025_other_answers_are_bad_responses_and_a_redirect_is_not_followed(net, ctx):
    # TC-025
    for status, headers in ((403, {"X-RateLimit-Remaining": "12"}), (500, {}), (301, {"Location": "https://evil.com/x"})):
        net.calls.clear()
        net.routes[API_URL] = (status, headers, b"")
        assert run(ctx, job(["diagram"]))[1]["parts"]["diagram"]["status"] == "bad_response"
        assert net.urls() == [API_URL]


def test_tc026_a_limit_on_the_listing_leaves_the_files_alone(net, ctx):
    # TC-026
    all_ok(net)
    net.routes[API_URL] = (403, {"X-RateLimit-Remaining": "0"}, b"")
    parts = run(ctx, job(["schema", "schema_input", "diagram"]))[1]["parts"]
    assert parts["schema"]["status"] == "ok" and parts["schema_input"]["status"] == "ok" and parts["diagram"]["status"] == "rate_limited"


def test_tc027_tc028_no_credential_and_a_user_agent(net, ctx):
    # TC-027, TC-028
    all_ok(net)
    run(ctx, job(["schema", "schema_input", "diagram", "image", "tags"]))
    assert len(net.calls) == 5
    for call in net.calls:
        names = {k.lower() for k in call["headers"]}
        assert not ({"authorization", "cookie"} & names) and not [n for n in names if n.startswith("x-")]
        assert call["headers"]["User-Agent"].startswith("abf-station/")


class _Local(http.server.BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        _Local.seen.append((self.command, dict(self.headers.items()), self.path))
        if self.path == "/redirect":
            self.send_response(301)
            self.send_header("Location", "/other")
            self.end_headers()
            return
        if self.path == "/missing":
            self.send_response(404)
            self.end_headers()
            return
        body = b"0123456789" * 10
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def test_tc027_the_real_connection_uses_get_sends_no_credential_and_does_not_follow(monkeypatch):
    # TC-027: the real function, against a local server (it is the only thing here that really connects; the address check is above it)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    for var in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY"):
        monkeypatch.delenv(var, raising=False)
    server = http.server.HTTPServer(("127.0.0.1", 0), _Local)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = "http://127.0.0.1:%d" % server.server_address[1]
        headers = {"User-Agent": "abf-station/test", "Accept": "*/*"}
        status, _, body = pipeline_files._fetch_once(base + "/ok", headers, 5, 20)
        assert status == 200 and len(body) == 21                    # limit + 1 bytes
        status, _, body = pipeline_files._fetch_once(base + "/redirect", headers, 5, 20)
        assert status == 301 and body == b""
        assert pipeline_files._fetch_once(base + "/missing", headers, 5, 20)[0] == 404
        with pytest.raises(OSError):
            pipeline_files._fetch_once("http://127.0.0.1:1/x", headers, 2, 20)
    finally:
        server.shutdown()
        server.server_close()
    assert {c for c, _, _ in _Local.seen} == {"GET"}
    assert "/other" not in [p for _, _, p in _Local.seen]
    for _, sent, _ in _Local.seen:
        assert not [k for k in sent if k.lower() in ("authorization", "cookie") or k.lower().startswith("x-")]


# ---- what is refused -------------------------------------------------------------------------------

def refused(ctx, net, j):
    state, out = run(ctx, j)
    assert state == "refused" and out["ok"] is False and isinstance(out["message"], str), j
    assert net.calls == [], j


def test_tc029_bad_repos_are_refused(net, ctx):
    # TC-029
    for repo in ("", "../x", "a/b/c", "./x", "x/.", "nf core/x", "nf-core/ampliseq?x=1", "nf-core/ampliseq#a", "nf-core/ampliseq\n",
                 "%2e%2e/x", "evil.com:80/x", 5, None, ["nf-core/x"], "ampliseq"):
        refused(ctx, net, job(["schema"], repo=repo))


def test_tc030_branch_names_are_refused(net, ctx):
    # TC-030
    for revision in ("master", "main", "dev", "3.0.0dev", "2.18.0/../x", "a" * 39, "A" * 40, "", "2.18.0\n", "latest"):
        refused(ctx, net, job(["schema"], revision=revision))


def test_tc031_revision_and_parts_must_agree(net, ctx):
    # TC-031
    refused(ctx, net, job(["schema"], revision=None))
    refused(ctx, net, job(["tags"], revision="2.18.0"))


def test_tc032_bad_parts_are_refused(net, ctx):
    # TC-032
    for parts in ([], ["x"], ["schema", "schema"], "schema", None, ("schema",), {"schema": 1}, [1], [["schema"]]):
        refused(ctx, net, job(parts))


def test_tc033_exact_versions_are_let_through(net, ctx):
    # TC-033
    for revision in ("v3.0.0", "3.0", "1.2.3.4", "0123456789abcdef0123456789abcdef01234567"):
        net.calls.clear()
        state, out = run(ctx, job(["schema"], revision=revision))
        assert state == "done" and len(net.calls) == 1, revision


# ---- the network fails ---------------------------------------------------------------------------------

@pytest.mark.parametrize("failure", [OSError("down"), TimeoutError("slow"), pytest.param("urlerror", id="urlerror")])
def test_tc034_a_failed_first_request_ends_the_job(net, ctx, failure):
    # TC-034
    import urllib.error
    all_ok(net)
    net.routes[SCHEMA_URL] = urllib.error.URLError("x") if failure == "urlerror" else failure
    state, out = run(ctx, job(["schema", "schema_input", "diagram"]))
    assert state == "error" and out["ok"] is False and out["error"] == "network" and isinstance(out["message"], str)
    assert net.urls() == [SCHEMA_URL]


def test_tc035_a_failure_in_the_middle_ends_the_job(net, ctx):
    # TC-035
    all_ok(net)
    net.routes[INPUT_URL] = OSError("down")
    state, out = run(ctx, job(["schema", "schema_input", "diagram"]))
    assert state == "error" and out["error"] == "network"
    assert net.urls() == [SCHEMA_URL, INPUT_URL]


def test_tc036_the_message_is_short_and_in_two_languages(net, ctx):
    # TC-036
    net.routes[SCHEMA_URL] = OSError("secret detail /home/x Traceback")
    message = run(ctx, job(["schema"]))[1]["message"]
    assert len(message) <= 300 and "Traceback" not in message and "secret" not in message
    assert re.search(r"[一-鿿]", message) and re.search(r"[A-Za-z]{4}", message)


def test_tc037_the_whole_job_has_a_budget(net, ctx, monkeypatch):
    # TC-037
    all_ok(net)
    ticks = iter([0.0, 1.0, 46.0, 47.0, 48.0, 49.0, 50.0])
    monkeypatch.setattr(pipeline_files, "CLOCK", lambda: next(ticks))
    state, out = run(ctx, job(["schema", "schema_input", "diagram"]))
    assert state == "error" and out["error"] == "network"
    assert net.urls() == [SCHEMA_URL]


# ---- what goes back ------------------------------------------------------------------------------------

def test_tc038_the_result_has_only_the_agreed_keys(net, ctx):
    # TC-038
    all_ok(net)
    state, out = run(ctx, job(["schema", "schema_input", "diagram", "image", "tags"]))
    assert set(out) == {"ok", "repo", "revision", "parts", "message"}
    allowed = {"schema": {"status", "text"}, "schema_input": {"status", "text"}, "diagram": {"status", "name", "type", "size"},
               "image": {"status", "name", "type", "size", "data_b64"}, "tags": {"status", "text"}}
    assert set(out["parts"]) == set(allowed)
    for name, part in out["parts"].items():
        assert set(part) == allowed[name], name


def test_tc039_nothing_of_githubs_own_goes_back(net, ctx):
    # TC-039
    net.routes[SCHEMA_URL] = (500, {"Set-Cookie": "SECRET=1", "X-GitHub-Request-Id": "ABC123"}, b"<html>Oops ERRORPAGE</html>")
    net.routes[INPUT_URL] = (404, {"Server": "GitHub.com"}, b"<html>Not Found ERRORPAGE</html>")
    state, out = run(ctx, job(["schema", "schema_input"]))
    text = json.dumps(out)
    assert state == "done" and "ERRORPAGE" not in text and "SECRET" not in text and "ABC123" not in text and "GitHub.com" not in text
    assert all(len(p["message"]) <= 300 for p in out["parts"].values())


def test_tc040_each_request_has_a_timeout_and_a_size_limit(net, ctx):
    # TC-040
    all_ok(net)
    run(ctx, job(["schema", "schema_input", "diagram", "image", "tags"]))
    assert [c["limit"] for c in net.calls] == [1000000, 1000000, 1000000, 2000000, 4000000]
    assert all(0 < c["timeout"] <= 10 for c in net.calls)


# ---- the source ----------------------------------------------------------------------------------------

def test_tc041_only_two_agent_files_connect():
    # TC-041
    using = sorted(p.name for p in STATION.glob("*.py") if "urllib.request" in p.read_text(encoding="utf-8"))
    assert using == ["agent.py", "pipeline_files.py"]


def test_tc042_the_reader_never_writes_or_signs_or_runs_anything():
    # TC-042
    text = (STATION / "pipeline_files.py").read_text(encoding="utf-8")
    for word in ("open(", ".write(", "os.remove", "shutil", "subprocess", "socket", "ctx.site", "site.call", "Authorization", "sbatch", "rm -rf"):
        assert word not in text, word


def test_tc043_a_test_that_forgets_to_stand_in_for_the_internet_fails(ctx):
    # TC-043: only the autouse guard is in place here
    with pytest.raises(AssertionError):
        pipeline_files.run_fetch(job(["schema"]), ctx)
    with pytest.raises(AssertionError):
        handlers.handle(job(["tags"], revision=None), ctx)


def test_tc044_tc045_the_real_agent_refuses_bad_jobs_and_lives(tmp_path):
    # TC-044, TC-045
    site = FakeSite(tmp_path / "s")
    fake = FakePlatform()
    try:
        with agent_on(fake, site, tmp_path, name="agent-f") as a:
            bad_repo = fake.push("pipeline_files", {"repo": "../x", "revision": "2.18.0", "parts": ["schema"]})
            extra = fake.push("pipeline_files", {"repo": "nf-core/x", "revision": "2.18.0", "parts": ["schema"], "extra": 1})
            first, second = fake.wait_result(bad_repo), fake.wait_result(extra)
            assert a.alive()
    finally:
        fake.stop()
    assert first["state"] == "refused" and first["result"]["ok"] is False
    assert second["state"] == "refused" and "does not take" in second["result"]["message"]


def test_tc046_the_agent_does_not_parse_what_it_reads(net, ctx):
    # TC-046
    net.ok(SCHEMA_URL, b"not json")
    state, out = run(ctx, job(["schema"]))
    assert state == "done" and out["parts"]["schema"] == {"status": "ok", "text": "not json"}


def test_tc047_there_is_no_way_to_read_other_files(net, ctx):
    # TC-047
    refused(ctx, net, job(["readme"]))
    refused(ctx, net, job(["catalogue"]))      # catalogue takes no repo／revision (CS-08)
    refused(ctx, net, job(["schema", "catalogue"], repo=None, revision=None))
    refused(ctx, net, job(["schema", "readme"]))


def test_tc048_every_address_is_one_of_the_five_shapes(net, ctx):
    # TC-048
    all_ok(net)
    run(ctx, job(["schema", "schema_input", "diagram", "image", "tags"]))
    shapes = [r"https://raw\.githubusercontent\.com/nf-core/ampliseq/2\.18\.0/nextflow_schema\.json\Z",
              r"https://raw\.githubusercontent\.com/nf-core/ampliseq/2\.18\.0/assets/schema_input\.json\Z",
              r"https://api\.github\.com/repos/nf-core/ampliseq/contents/docs/images\?ref=2\.18\.0\Z",
              r"https://raw\.githubusercontent\.com/nf-core/ampliseq/2\.18\.0/docs/images/[A-Za-z0-9][A-Za-z0-9._-]*\.(png|svg)\Z",
              r"https://github\.com/nf-core/ampliseq\.git/info/refs\?service=git-upload-pack\Z"]
    assert len(net.calls) == 5
    for url in net.urls():
        assert [s for s in shapes if re.match(s, url)], url
        assert pipeline_files.allowed(url)
