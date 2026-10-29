# Nothing existing: tests of the agent side of results-files (the read_run_file job); the rules are ours (specs/results-files/test-case.md).
"""results-files, agent side: read_run_file reads ONE regular file of a run's results folder for the platform, within the places the agent may
read, at most 25 MB, through fixed commands with quoted values. A recording site runs the commands on a local folder, so the tests see exactly
which commands the agent sent. Test cases are named in the comments (TC-028 ...)."""
import base64
import re
import shlex
import subprocess
from types import SimpleNamespace

import pytest

from abf_station import handlers, rules
from abf_station.site import SiteResult

RUN = "run-one"
LIMIT = 26214400
NOT_ON_SITE_WORDS = "此環境的結果檔不在站台主機上"


class RecordingSite:
    """Runs each command of the agent on this machine (no ssh) and keeps the text of every command, so a test can say what was sent."""

    def __init__(self):
        self.calls = []

    def call(self, args, input=None, timeout=None):
        text = " ".join(args)
        self.calls.append(text)
        if text == "--check-reach":
            return SiteResult(0, b"", "")
        p = subprocess.run(["bash", "-c", text], capture_output=True)
        return SiteResult(p.returncode, p.stdout, p.stderr.decode("utf-8", errors="replace"))

    def reads(self):
        """The commands that bring file CONTENT to the agent (only base64 does)."""
        return [c for c in self.calls if "base64" in c]


class World:
    def __init__(self, tmp_path, platform="slurm-platform"):
        self.tmp = tmp_path
        self.work = tmp_path / "site" / "work"
        self.folder = self.work / "runs" / RUN
        self.results = self.folder / "results"
        (self.results / "multiqc" / "multiqc_data").mkdir(parents=True)
        self.outside = tmp_path / "site" / "elsewhere"
        self.outside.mkdir(parents=True)
        self.site = RecordingSite()
        self.ctx = SimpleNamespace(site=self.site, settings_file=str(tmp_path / "no-such-settings.yaml"))
        self.ce = {"platform": platform, "workDir": str(self.work), "headQueue": "q", "readRoots": []}

    def job(self, path, run=RUN, **over):
        args = {"ce": self.ce, "run": run, "path": path}
        args.update(over)
        return {"kind": "read_run_file", "args": args}

    def put(self, rel, data=b"x"):
        p = self.results / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def ask(self, path, **kw):
        return handlers.handle(self.job(path, **kw), self.ctx)


@pytest.fixture
def w(tmp_path):
    return World(tmp_path)


def decoded(result):
    return base64.b64decode(result["b64"])


def test_the_kind_is_known_with_exactly_three_arguments():
    # TC-028 (the agent takes this kind), TC-033 (no other argument)
    assert "read_run_file" in handlers.JOB_KINDS and handlers.ARG_KEYS["read_run_file"] == {"ce", "run", "path"}


def test_tc028_a_plain_file_comes_back_as_base64_with_its_size(w):
    # TC-028
    data = bytes(range(256)) * 5 + b"\xff\xfe<script>alert(1)</script>\n"      # not UTF-8 text
    w.put("multiqc/multiqc_report.html", data)
    state, res = w.ask("multiqc/multiqc_report.html")
    assert state == "done" and res["ok"] is True and res["status"] == "ok"
    assert res["name"] == "multiqc_report.html" and res["size"] == len(data)
    assert decoded(res) == data and len(decoded(res)) == res["size"]
    assert len(w.site.reads()) == 1, w.site.calls      # one fixed command brings the content


def test_tc028_an_empty_file_is_read_too(w):
    # TC-028
    w.put("empty.txt", b"")
    state, res = w.ask("empty.txt")
    assert state == "done" and res["ok"] is True and res["size"] == 0 and decoded(res) == b""


def test_tc028_the_folder_of_a_resumed_run_is_the_folder_of_its_first_run(w):
    # TC-028: a resume attempt (<name>-a2) keeps the folder of the run it continues
    w.put("overall_summary.tsv", b"a\tb\n")
    state, res = w.ask("overall_summary.tsv", run=RUN + "-a2")
    assert state == "done" and res["ok"] is True and decoded(res) == b"a\tb\n"


@pytest.mark.parametrize("path", ["..", "a/../b", "../x", "/abs", "/etc/passwd", "", ".hidden", "a/.b", "a/./b", "a//b", "a/", "x" * 513,
                                  "line\nbreak", "nul\x00byte", "tab\tbed"])
def test_tc029_a_path_that_is_not_a_plain_relative_path_is_refused_before_any_command(w, path):
    # TC-029
    state, res = w.ask(path)
    assert state == "refused" and res["ok"] is False
    assert w.site.calls == [], "nothing was sent to the site: %s" % w.site.calls


@pytest.mark.parametrize("value", [None, 5, ["a"], {"a": 1}])
def test_tc029_a_path_that_is_not_text_is_refused(w, value):
    # TC-029
    state, _ = w.ask(value)
    assert state == "refused" and w.site.calls == []


def test_tc029_a_run_name_that_is_not_a_run_name_is_refused(w):
    # TC-029
    for bad in ("../x", "A B", "", "x/y", None, 3):
        state, _ = w.ask("a.txt", run=bad)
        assert state == "refused", bad
    assert w.site.calls == []


def test_tc030_a_link_that_leads_out_of_results_is_refused(w):
    # TC-030 (a): once to a file elsewhere in the work folder, once to a file outside every place the agent may read
    secret_in_work = w.work / "secret.txt"
    secret_in_work.write_text("SECRET INSIDE WORK\n")
    secret_outside = w.outside / "secret.txt"
    secret_outside.write_text("SECRET OUTSIDE\n")
    (w.results / "link1.txt").symlink_to(secret_in_work)
    (w.results / "link2.txt").symlink_to(secret_outside)
    for name in ("link1.txt", "link2.txt"):
        state, res = w.ask(name)
        assert state == "refused" and res["ok"] is False, name
        assert "SECRET" not in repr(res) and not w.site.reads()
        assert re.search(r"捷徑|link|範圍", res["message"]), res["message"]


def test_tc030_a_folder_link_that_leads_out_of_results_is_refused(w):
    # TC-030 (b)
    (w.outside / "x.txt").write_text("SECRET VIA FOLDER LINK\n")
    (w.results / "linkdir").symlink_to(w.outside)
    state, res = w.ask("linkdir/x.txt")
    assert state == "refused" and "SECRET" not in repr(res) and not w.site.reads()


def test_tc030_results_that_lies_outside_the_read_places_is_refused(w):
    # TC-030 (c): results itself is a link to a folder outside the work folder and the read roots
    import shutil
    shutil.rmtree(w.results)
    (w.outside / "multiqc").mkdir()
    (w.outside / "multiqc" / "report.html").write_text("SECRET RESULTS ELSEWHERE\n")
    w.results.symlink_to(w.outside)
    state, res = w.ask("multiqc/report.html")
    assert state == "refused" and "SECRET" not in repr(res) and not w.site.reads()


def test_tc030_a_read_root_that_holds_the_results_is_enough(w):
    # TC-030: the read places of the environment are its work folder, its launch folder and its readRoots; results below one of them is read
    other = w.tmp / "site" / "shared"
    (other / "multiqc").mkdir(parents=True)
    (other / "multiqc" / "report.html").write_bytes(b"shared\n")
    import shutil
    shutil.rmtree(w.results)
    w.results.symlink_to(other)
    w.ce["readRoots"] = [str(other)]
    state, res = w.ask("multiqc/report.html")
    assert state == "done" and decoded(res) == b"shared\n"


def test_tc031_a_folder_is_refused_and_a_missing_file_is_not_found(w):
    # TC-031
    state, res = w.ask("multiqc")
    assert state == "error" and res["ok"] is False and res["error"] == "not_a_file"
    state, res = w.ask("multiqc/no-such-file.html")
    assert state == "error" and res["ok"] is False and res["error"] == "not_found"
    assert not w.site.reads(), w.site.calls


def test_tc032_a_file_over_25_mb_is_not_read_and_one_of_exactly_25_mb_is(w):
    # TC-032
    big = w.results / "big.bin"
    with open(big, "wb") as f:
        f.truncate(LIMIT + 1)
    exact = w.results / "exact.bin"
    with open(exact, "wb") as f:
        f.truncate(LIMIT)
    state, res = w.ask("big.bin")
    assert state == "error" and res["ok"] is False and res["error"] == "too_large" and res["size"] == LIMIT + 1
    assert "b64" not in res and not w.site.reads(), w.site.calls
    before = len(w.site.calls)
    state, res = w.ask("exact.bin")
    assert state == "done" and res["ok"] is True and res["size"] == LIMIT and len(decoded(res)) == LIMIT
    assert len(w.site.calls) > before and len(w.site.reads()) == 1


def test_tc033_special_characters_in_a_file_name_are_quoted_and_never_run(w):
    # TC-033
    name = "a b;touch PWNED$(id)`id`'q\".txt"
    w.put("multiqc/" + name, b"quoted ok\n")
    state, res = w.ask("multiqc/" + name)
    assert state == "done" and decoded(res) == b"quoted ok\n" and res["name"] == name
    assert not list(w.tmp.rglob("PWNED*")), "the name was run as a command"
    real = str(w.results.resolve() / "multiqc" / name)
    assert any(shlex.quote(real) in c for c in w.site.calls), w.site.calls
    for c in w.site.calls:
        assert "PWNED" not in c.replace(shlex.quote(real), ""), c      # the name appears only in its quoted form


def test_tc033_a_job_with_an_extra_argument_is_refused(w):
    # TC-033
    w.put("a.txt")
    state, res = w.ask("a.txt", command="cat /etc/passwd")
    assert state == "refused" and w.site.calls == []
    job = w.job("a.txt")
    del job["args"]["run"]
    state, res = handlers.handle(job, w.ctx)
    assert state == "refused" and w.site.calls == []


def test_tc034_a_cloud_environment_has_no_results_on_the_site_host(tmp_path):
    # TC-034, TC-038: the agent answers in one sentence and sends no command to any site or cloud
    for platform in ("awsbatch-platform", "azbatch-platform", "gcb-platform", "k8s-platform"):
        w = World(tmp_path / platform, platform)
        state, res = w.ask("multiqc/multiqc_report.html")
        assert state == "error" and res["ok"] is False and res["error"] == "not_on_site", platform
        assert NOT_ON_SITE_WORDS in res["message"] and w.site.calls == []


def test_tc041_the_agent_sends_only_reading_commands(w):
    # TC-041: realpath, find (type and size) and base64 of the one file; no write, move or delete
    w.put("multiqc/multiqc_report.html", b"<html></html>")
    w.ask("multiqc/multiqc_report.html")
    w.ask("multiqc")
    w.ask("nothing.txt")
    assert w.site.calls
    for c in w.site.calls:
        assert re.match(r"^(realpath|find) ", c), c
        assert not re.search(r"\b(rm|mv|rmdir|cp|tee|touch|chmod|chown|ln|dd|sed -i|truncate|mkdir)\b|>|\bsh -c\b|\bbash\b", c), c


def test_the_site_not_answering_is_an_error_not_a_crash(w):
    # TC-015 (agent side): a site that cannot be reached answers site_unreachable
    class Down(RecordingSite):
        def call(self, args, input=None, timeout=None):
            self.calls.append(" ".join(args))
            return SiteResult(255, b"", "ssh: connect failed")
    w.ctx.site = Down()
    w.put("a.txt")
    state, res = w.ask("a.txt")
    assert state in ("error", "refused") and res["ok"] is False and "b64" not in res
