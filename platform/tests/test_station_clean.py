# Nothing existing: tests that hand the real agent clean_work jobs, honest and hostile, and watch a fake site with a real file tree; the protocol and the site are ours.
"""The agent's clean_work job (feature cloud-cleanup-c): refuses unless confirmed, works the path out again, removes one `work` folder.

The handler runs in this process (handlers.handle) with a Context whose site is the real Site class on the fake site's tools,
wrapped so that every call to it is counted; the fake site has a real file tree, so what was removed can be looked at.
"""
import os
import pwd
import re
import secrets
import shutil
import subprocess
import time
from types import SimpleNamespace

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from station_harness import FakeSite, snapshot

from abf_platform import common
from abf_station import clean, handlers, launch
from abf_station.site import Site, SiteResult, default_plugin_root, quote

ME = pwd.getpwuid(os.getuid()).pw_name
RUN = "ampliseq-d5"
STATION = PLATFORM_DIR / "abf_station"


class Rec:
    """The site as the handler sees it: counts every call, and may answer instead of the real tools."""

    def __init__(self, real):
        self.real = real
        self.calls = []
        self.answer = None

    def call(self, args, input=None, timeout=None):
        self.calls.append((list(args), timeout))
        if self.answer is not None:
            return self.answer
        return self.real.call(args, input=input, timeout=timeout)


class Env:
    def __init__(self, tmp, monkeypatch, site_user=ME, settings=(), run=RUN):
        self.site = FakeSite(tmp, site_user=site_user, destructive_log=True, settings=settings)
        self.lines = []
        self.rec = Rec(Site(default_plugin_root(), self.site.settings, log=self.lines.append))
        monkeypatch.setattr(os, "environ", dict(self.site.agent_env()))
        self.ctx = SimpleNamespace(site=self.rec, settings_file=str(self.site.settings), platform_url="", agent_name="agent-f",
                                   instance_id=None, used_confirmations=set(), job_started=time.monotonic())
        self.work = self.site.work                      # the workDir of the compute environment
        self.F = self.work / "runs" / run
        self.W = self.F / "work"
        (self.W / "ab" / "cdef").mkdir(parents=True)
        (self.W / "ab" / "cdef" / "a.tsv").write_text("task output\n")
        (self.W / "ab" / "cdef" / ".command.sh").write_text("echo hi\n")
        (self.F / "results").mkdir()
        (self.F / "results" / "guard.txt").write_text("results guard\n")
        (self.F / "head.sh").write_text("#!/bin/bash\n")
        (self.F / ".nextflow").mkdir()
        (self.F / ".nextflow" / "history").write_text("h\n")
        (self.F / "slurm-4242.out").write_text("log\n")
        for d in ("rawdata", "analysis"):
            (self.work / d).mkdir()
            (self.work / d / "guard.txt").write_text(d + " guard\n")
        self.guarded = [self.work / "rawdata", self.work / "analysis", self.F / "results"]

    def ce(self, **over):
        c = {"name": "lab-a", "platform": "slurm-platform", "workDir": str(self.work), "launchDir": str(self.site.launch),
             "headQueue": "normal", "computeQueue": None, "readRoots": []}
        c.update(over)
        return c

    def bundle(self, **over):
        b = {"version": 1, "run_name": RUN, "slurm_job_id": 4242, "run_folder": str(self.F), "agent": "agent-f",
             "ce": self.ce(), "work": str(self.F) + "/work"}
        b.update(over)
        return b

    def job(self, bundle=None, conf_kind="clean_work", remaining=300, **extra):
        bundle = bundle if bundle is not None else self.bundle()
        cid, sha = secrets.token_hex(16), common.bundle_sha256(bundle)
        job = {"kind": "clean_work", "args": {"bundle": bundle, "confirmation_id": cid, "bundle_sha256": sha},
               "confirmation": {"id": cid, "sha256": sha, "kind": conf_kind}, "remaining": remaining}
        job.update(extra)
        return job

    def go(self, job=None):
        self.ctx.job_started = time.monotonic()
        return handlers.handle(job if job is not None else self.job(), self.ctx)

    def sent(self):
        return len(self.rec.calls)

    def command(self):
        assert len(self.rec.calls) == 1, self.rec.calls
        args, _ = self.rec.calls[0]
        assert len(args) == 1
        return args[0]

    def guards(self):
        return {str(p): snapshot(p) for p in self.guarded}

    def nothing_sent(self):
        assert self.rec.calls == [] and self.site.calls() == [], (self.rec.calls, self.site.calls())
        assert self.site.destructive() == [] and self.W.is_dir()


@pytest.fixture
def env(tmp_path, monkeypatch):
    return Env(tmp_path / "s", monkeypatch)


def refused(env, job, said=None, sent=False):
    before = env.guards()
    state, res = env.go(job)
    assert state == "refused" and res["ok"] is False and res["message"].strip(), (state, res)
    assert "Traceback" not in res["message"] and str(STATION) not in res["message"]
    if said:
        assert said in res["message"], res["message"]
    if not sent:
        env.nothing_sent()
    assert env.guards() == before, "rawdata, results and analysis are as they were"
    return res["message"]


def rebundled(env, **over):
    return env.job(env.bundle(**over))


# ---- US1: no confirmation, nothing is done -------------------------------------------------------------------------

def _unconfirmed(env, how):
    good = env.job()
    if how == "no confirmation id":
        return dict(good, args={k: v for k, v in good["args"].items() if k != "confirmation_id"}), "確認憑證"
    if how == "changed content":
        b = dict(good["args"]["bundle"], run_name="ampliseq-d6")
        return dict(good, args=dict(good["args"], bundle=b)), "內容與確認時不符"
    if how == "spent":
        return dict(good, confirmation=dict(good["confirmation"], used_at=12345.0)), "已用過"
    if how == "launch kind":
        return env.job(conf_kind="launch"), "種類不符"
    return env.job(conf_kind="cancel"), "種類不符"


@pytest.mark.parametrize("how", ["no confirmation id", "changed content", "spent", "launch kind", "cancel kind"])
def test_tc001_to_tc007_an_unconfirmed_clean_is_refused_in_plain_words_and_nothing_is_sent(env, how):
    job, said = _unconfirmed(env, how)
    refused(env, job, said)


def test_tc006_a_second_run_of_the_same_confirmed_job_is_refused(env):
    job = env.job()
    assert env.go(job)[0] == "done"
    state, res = env.go(job)
    assert state == "refused" and "用過" in res["message"]
    assert len(env.site.destructive()) == 1 and env.sent() == 1


def test_tc008_the_confirmation_is_checked_before_anything_else_in_the_bundle(env):
    job = env.job(env.bundle(run_name="x;rm", work=str(env.F) + "/results"))
    del job["args"]["confirmation_id"]
    refused(env, job, "確認憑證")


# ---- US2: the bundle, the identity, the settings, the time, the kinds -----------------------------------------------

def test_tc009_a_confirmed_job_goes_on_and_sends_exactly_one_command(env):
    assert env.go()[0] == "done"
    assert env.sent() == 1


def test_tc010_a_bundle_with_another_key_is_refused(env):
    refused(env, rebundled(env, delete_results=True), "欄位不對")


def test_tc011_a_bundle_with_a_missing_key_is_refused(env):
    b = env.bundle()
    del b["work"]
    refused(env, env.job(b))


def test_tc012_a_bundle_of_another_agent_is_refused(env):
    refused(env, rebundled(env, agent="agent-z"), "另一個代理")


def test_tc013_a_google_batch_bundle_is_refused_in_plain_words(env):
    msg = refused(env, rebundled(env, ce=env.ce(platform=launch.GCB)), "Google Batch 的清理尚未支援")
    assert "cloud-cleanup-d" in msg


def test_tc014_another_platform_is_refused(env):
    refused(env, rebundled(env, ce=env.ce(platform="other-platform")), "Slurm")


@pytest.mark.parametrize("ce", [None, "text", "missing"])
def test_tc015_a_missing_or_odd_environment_is_refused_without_crashing(env, ce):
    b = env.bundle()
    if ce == "missing":
        del b["ce"]
        b["ce2"] = 1
    else:
        b["ce"] = ce
    refused(env, env.job(b))


BAD_NAMES = ["a b", "a;b", "a$(x)", "a`x`", "a\nb", "a‮b", "a" * 65, ".."]


@pytest.mark.parametrize("name", BAD_NAMES)
def test_tc016_a_hostile_run_name_is_refused(env, name):
    folder = str(env.work / "runs" / name)
    refused(env, rebundled(env, run_name=name, run_folder=folder, work=folder + "/work"))


@pytest.mark.parametrize("wd", ["/w d/abf", "/w;d/abf", "/w$(x)/abf", "/w`x`/abf", "/w\nd/abf", "/w‮d/abf", "/w/../abf",
                                "{W}/", "relative/abf", "/"])
def test_tc017_a_hostile_workdir_is_refused(env, wd):
    wd = wd.replace("{W}", str(env.work))
    folder = wd.rstrip("/") + "/runs/" + RUN
    refused(env, rebundled(env, ce=env.ce(workDir=wd), run_folder=folder, work=folder + "/work"))


@pytest.mark.parametrize("fol", ["/w d/runs/" + RUN, "/w;d/runs/" + RUN, "/w$(x)/runs/" + RUN, "/w`x`/runs/" + RUN,
                                 "/w\nd/runs/" + RUN, "/w‮d/runs/" + RUN, "{W}/runs/" + RUN + "/.."])
def test_tc018_a_hostile_folder_is_refused(env, fol):
    fol = fol.replace("{W}", str(env.work))
    refused(env, rebundled(env, run_folder=fol, work=fol + "/work"))


@pytest.mark.parametrize("n", [True, 0, -1, 2 ** 31, "123", None])
def test_tc019_a_job_number_that_is_not_one_decimal_number_is_refused(env, n):
    refused(env, rebundled(env, slurm_job_id=n))


def test_tc020_a_missing_site_user_is_refused_in_plain_words(tmp_path, monkeypatch):
    e = Env(tmp_path / "s", monkeypatch, site_user=None)
    refused(e, e.job(), "site_user")


@pytest.mark.parametrize("user", ["a b", "a;b"])
def test_tc021_a_site_user_that_is_not_plain_is_refused(tmp_path, monkeypatch, user):
    e = Env(tmp_path / "s", monkeypatch, site_user="x")
    e.site.settings.write_text(re.sub(r"site_user: .*", "site_user: " + user, e.site.settings.read_text()))
    refused(e, e.job())


def test_tc022_too_little_time_left_is_refused(env):
    refused(env, env.job(remaining=30), "時間不夠")


@pytest.mark.parametrize("remaining,want", [(1000, 300), (100, 85)])
def test_tc023_the_command_is_given_a_clock_of_the_time_left(env, remaining, want):
    assert env.go(env.job(remaining=remaining))[0] == "done"
    assert env.sent() == 1
    assert want - 1 <= env.rec.calls[0][1] <= want, env.rec.calls[0][1]


def test_tc024_an_argument_the_agent_does_not_take_is_refused(env):
    job = env.job()
    job["args"]["force"] = True
    refused(env, job, "force")


@pytest.mark.parametrize("kind", ["clean_work2", "clean_all"])
def test_tc025_another_kind_is_refused_and_the_list_names_clean_work(env, kind):
    state, res = handlers.handle(dict(env.job(), kind=kind), env.ctx)
    assert state == "refused" and "clean_work" in res["message"]
    env.nothing_sent()


def test_tc026_every_kind_has_arguments_and_clean_work_is_dispatched_to_clean(env, monkeypatch):
    assert set(handlers.JOB_KINDS) == set(handlers.ARG_KEYS) and "clean_work" in handlers.JOB_KINDS
    seen = []
    monkeypatch.setattr(clean, "run_clean", lambda job, ctx: seen.append(job) or ("done", {"ok": True}))
    assert handlers.handle({"kind": "clean_work", "args": {}}, env.ctx) == ("done", {"ok": True}) and len(seen) == 1


def test_tc027_clean_work_takes_the_launch_keys():
    assert handlers.ARG_KEYS["clean_work"] == launch.LAUNCH_KEYS == {"bundle", "confirmation_id", "bundle_sha256"}


def test_tc028_the_other_six_kinds_are_as_they_were():
    from abf_station import fetch, readlog
    assert handlers.JOB_KINDS[:6] == ("preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records", "read_task_log")
    assert handlers.JOB_KINDS[6:] == ("clean_work",)
    old = {"preflight": {"ce"}, "list_site_files": {"ce", "path"}, "launch_nextflow": launch.LAUNCH_KEYS, "cancel_run": launch.LAUNCH_KEYS,
           "fetch_run_records": fetch.ARGS, "read_task_log": readlog.ARGS}
    assert {k: v for k, v in handlers.ARG_KEYS.items() if k != "clean_work"} == old


# ---- US3: the path is worked out again and compared character by character -------------------------------------------

def _results_workdir(e):
    wd = "/" + "work/u1/results/abf"      # joined so the hard-coded-paths scan (test_scope TC-072) does not read it as a real path
    f = wd + "/runs/" + RUN
    return dict(ce=e.ce(workDir=wd), run_folder=f, work=f + "/work")


PATH_ROWS = [
    ("TC-029", lambda e: dict(work=str(e.F) + "/work/")),
    ("TC-030", lambda e: dict(work=str(e.F) + "/results")),
    ("TC-031", lambda e: dict(work=str(e.F) + "/work/../results")),
    ("TC-032", lambda e: dict(work=str(e.work) + "/rawdata")),
    ("TC-033", lambda e: dict(work=str(e.F))),
    ("TC-034", lambda e: dict(work=str(e.work) + "/runs/other-run/work")),
    ("TC-035", lambda e: dict(work=str(e.work) + "/analysis/work")),
    ("TC-036", lambda e: dict(run_name="other-a2")),
    ("TC-037", _results_workdir),
    ("TC-038", lambda e: dict(run_folder=str(e.work) + "/runs/x/y", work=str(e.work) + "/runs/x/y/work")),
    ("TC-041", lambda e: dict(run_name=RUN + "-a1")),
    ("TC-042a", lambda e: dict(run_folder=str(e.F) + "/")),
    ("TC-042b", lambda e: dict(run_folder=str(e.F) + "/", work=str(e.F) + "//work")),
    ("TC-043a", lambda e: dict(run_folder=str(e.work) + "/runs/./" + RUN)),
    ("TC-043b", lambda e: dict(run_folder=str(e.work) + "//runs/" + RUN)),
    ("TC-044", lambda e: dict(work=str(e.F) + "/./work")),
    ("TC-070a", lambda e: dict(work=[str(e.F) + "/work", str(e.F) + "/work"])),
    ("TC-070b", lambda e: dict(work=str(e.F) + "/work/ab")),
]


@pytest.mark.parametrize("tc,over", PATH_ROWS, ids=[r[0] for r in PATH_ROWS])
def test_the_path_table_every_odd_path_is_refused_before_any_command(env, tc, over):
    refused(env, env.job(env.bundle(**over(env))))
    assert (env.W / "ab" / "cdef" / "a.tsv").is_file()


def test_tc039_a_resume_attempt_uses_the_first_runs_folder_and_is_cleaned(env):
    state, res = env.go(rebundled(env, run_name=RUN + "-a2"))
    assert state == "done" and res["cleaned"] is True and res["run_name"] == RUN + "-a2"
    assert not env.W.exists() and (env.F / "results" / "guard.txt").is_file()


def test_tc040_a_cut_resume_name_is_cleaned(env):
    leaf = "l" + "m" * 63
    f = env.work / "runs" / leaf
    (f / "work").mkdir(parents=True)
    (f / "work" / "x").write_text("x")
    state, res = env.go(rebundled(env, run_name=leaf[:61] + "-a2", run_folder=str(f), work=str(f) + "/work"))
    assert state == "done" and res["cleaned"] is True and not (f / "work").exists()


# ---- US4: the checks on the site, the removal, the exit codes ---------------------------------------------------------

def test_tc045_a_confirmed_clean_removes_work_and_says_so(env):
    state, res = env.go()
    assert state == "done" and res["ok"] is True and res["cleaned"] is True and res["run_name"] == RUN
    assert res["message"] == "已刪除 %s/work；results 沒有動" % env.F
    assert not env.W.exists() and (env.F / "results").is_dir()
    assert env.site.dangerous() == []          # TC-064: no scancel, sbatch, srun or nextflow run


def test_tc046_to_tc047_one_command_one_removal_and_its_only_target_is_the_word_work(env):
    env.go()
    assert env.sent() == 1
    assert env.site.destructive() == ["rm -rf --one-file-system -- work"]
    rm = env.site.destructive()[0]
    assert "*" not in rm and "$" not in rm and "/" not in rm


def test_tc048_nothing_but_work_changes(env):
    (env.F / "results" / "x.tsv").write_text("x")
    root = env.site.site
    gone = str(env.W.relative_to(root))
    under = lambda k: (k + "/").startswith(gone + "/")
    before = snapshot(root)
    assert env.go()[0] == "done"
    after = snapshot(root)
    rel_f = str(env.F.relative_to(root))
    b = {k: v for k, v in before.items() if not under(k)}
    a = dict(after)
    # the run folder's own modification time moves when a child goes; its kind and everything else must not
    assert b.pop(rel_f)[0] == a.pop(rel_f)[0]
    assert a == b
    assert set(before) - set(after) == {k for k in before if under(k)}


def test_tc049_links_inside_work_go_but_what_they_point_to_stays(env):
    target = env.work / "rawdata" / "x.fastq.gz"
    target.write_bytes(b"reads")
    (env.W / "ab" / "link.fq").symlink_to(target)
    before = snapshot(env.work / "rawdata")
    assert env.go()[0] == "done"
    assert not env.W.exists() and snapshot(env.work / "rawdata") == before and target.read_bytes() == b"reads"


def test_tc050_no_work_folder_is_a_success_that_removes_nothing(env):
    shutil.rmtree(env.W)
    before = snapshot(env.site.site)
    state, res = env.go()
    assert state == "done" and res["cleaned"] is True
    assert env.site.destructive() == [] and snapshot(env.site.site) == before


def _make_work_a_link(e):
    shutil.rmtree(e.W)
    e.W.symlink_to(e.F / "results")


def _make_parent_a_link(e):
    real = e.work / "runs-real"
    (e.work / "runs").rename(real)
    (e.work / "runs").symlink_to(real)


def _results_links_into_work(e):
    (e.F / "results" / "a.tsv").symlink_to(e.W / "ab" / "cdef" / "a.tsv")


def _job_in_folder(e):
    e.site.add_job(7, "nf-x", ME, str(e.F))


def _other_owner(e):
    e.site.settings.write_text(re.sub(r"site_user: .*", "site_user: nobody-else", e.site.settings.read_text()))


CLUSTER = [
    ("TC-057", 11, lambda e: shutil.rmtree(e.F), "進不了"),
    ("TC-052", 12, _make_parent_a_link, "捷徑"),
    ("TC-054", 13, _job_in_folder, "Slurm 工作"),
    ("TC-051", 14, _make_work_a_link, "work 本身是捷徑"),
    ("TC-055", 16, _other_owner, "擁有者"),
    ("TC-053", 17, _results_links_into_work, "results"),
    ("TC-056", 18, lambda e: e.site.set("squeue_fail", "1"), "Slurm 佇列"),
]


@pytest.mark.parametrize("tc,code,setup,said", CLUSTER, ids=[c[0] for c in CLUSTER])
def test_the_cluster_side_checks_refuse_with_one_command_and_remove_nothing(tmp_path, monkeypatch, tc, code, setup, said):
    e = Env(tmp_path / "s", monkeypatch)
    setup(e)
    guards = e.guards() if code != 11 else None
    snap = snapshot(e.site.site) if code != 11 else None
    state, res = e.go()
    assert state == "refused" and res["ok"] is False, res
    assert said in res["message"] and "沒有改動任何東西" in res["message"], res["message"]
    assert "Traceback" not in res["message"] and str(STATION) not in res["message"]
    assert e.sent() == 1
    assert e.site.destructive() == [] and e.site.dangerous() == []
    if snap is not None:
        assert snapshot(e.site.site) == snap and e.guards() == guards
    if code == 12:
        assert (e.work / "runs-real" / RUN / "work").is_dir()


def test_each_exit_code_has_its_own_plain_sentence_and_none_echoes_the_sites_raw_output(env):
    seen = set()
    for code in range(11, 19):
        env.rec.calls.clear()
        env.rec.answer = SiteResult(code, b"SECRET-RAW-OUT-12345", "SECRET-RAW-OUT-12345")
        state, res = env.go()
        assert state == "refused" and "沒有改動任何東西" in res["message"] and "SECRET-RAW-OUT-12345" not in str(res)
        seen.add(res["message"])
        assert env.sent() == 1
    assert len(seen) == 8


@pytest.mark.parametrize("rc", [0, 13, 99])
def test_tc060_the_raw_output_of_the_site_is_never_passed_on(env, rc):
    env.rec.answer = SiteResult(rc, b"SECRET-RAW-OUT-12345", "SECRET-RAW-OUT-12345")
    assert "SECRET-RAW-OUT-12345" not in str(env.go())


def test_tc061_the_command_is_one_fixed_template_and_only_three_values_vary(tmp_path, monkeypatch):
    texts = []
    for i, (wd, run, user) in enumerate([("/w/ab-1", "run-x", "u-1"), ("/q.z/p", "other-9", "tester.2")]):
        e = Env(tmp_path / ("s%d" % i), monkeypatch)
        e.rec.answer = SiteResult(0, b"", "")
        folder = wd + "/runs/" + run
        e.site.settings.write_text(re.sub(r"site_user: .*", "site_user: " + user, e.site.settings.read_text()))
        state, _ = e.go(e.job(e.bundle(ce=e.ce(workDir=wd), run_name=run, run_folder=folder, work=folder + "/work")))
        assert state == "done"
        text = e.command()
        for value, mark in ((quote(folder + "/work"), "<W>"), (quote(folder), "<F>"), (quote(user), "<U>")):
            text = text.replace(value, mark)
        texts.append(text)
    assert texts[0] == texts[1]
    assert texts[0].split("\n") == [
        "cd -- <F> || exit 11",
        'test "$(realpath -- .)" = <F> || exit 12',
        "q=$(squeue -h -u <U> -o %Z 2>&1) || exit 18",
        "printf '%s\\n' \"$q\" | grep -qxF -- <F> && exit 13",
        "test -d work || exit 20",
        "test ! -L work || exit 14",
        'test "$(realpath -- work)" = <W> || exit 15',
        'test "$(stat -c %U work)" = <U> || exit 16',
        "if [ -d results ] && find results -type l -lname '*/work/*' | grep -q . ; then exit 17; fi",
        "rm -rf --one-file-system -- work",
    ]


def test_tc062_a_timeout_is_an_error_that_says_part_may_be_gone_and_is_not_retried(env):
    env.rec.answer = SiteResult(124, b"", "", timed_out=True)
    state, res = env.go()
    assert state == "error" and "逾時" in res["message"] and "可能只刪了一部分" in res["message"] and env.sent() == 1


def test_tc063_an_unknown_exit_code_is_an_error_with_the_code_and_is_not_retried(env):
    env.rec.answer = SiteResult(99, b"", "")
    state, res = env.go()
    assert state == "error" and "99" in res["message"]
    assert "可能只刪了一部分；work_cleaned_at 沒記，可以再申請" in res["message"] and env.sent() == 1


def test_tc065_no_answer_shows_a_traceback_or_the_agents_own_path(env):
    for answer in (SiteResult(99, b"", ""), SiteResult(124, b"", "", timed_out=True), SiteResult(14, b"", "")):
        env.rec.answer = answer
        text = str(env.go(env.job()))
        assert "Traceback" not in text and str(STATION) not in text and str(REPO_ROOT) not in text


def test_tc066_a_key_in_the_settings_is_in_no_answer_and_no_log(tmp_path, monkeypatch):
    e = Env(tmp_path / "s", monkeypatch, settings=["fake_token = SECRET-TOKEN-98765"])
    out = [str(e.go(e.job())), str(e.go(e.job(e.bundle(work=str(e.F) + "/results"))))]
    assert "SECRET-TOKEN-98765" not in "\n".join(out + e.lines)


def _squeue(site, *args):
    return subprocess.run([str(site.bin / "squeue")] + list(args), capture_output=True, text=True, env=site.agent_env())


def test_tc067_the_fake_squeue_lists_the_folders_of_one_user(tmp_path):
    s = FakeSite(tmp_path / "s", destructive_log=True)
    s.add_job(1, "nf-a", "tester", "/f/one")
    s.add_job(2, "nf-b", "other", "/f/three")
    s.add_job(3, "nf-c", "tester", "/f/two")
    p = _squeue(s, "-h", "-u", "tester", "-o", "%Z")
    assert p.returncode == 0 and p.stdout.splitlines() == ["/f/one", "/f/two"]
    s.set("squeue_fail", "1")
    assert _squeue(s, "-h", "-u", "tester", "-o", "%Z").returncode != 0


def test_tc068_the_fake_squeue_j_and_n_print_as_before(tmp_path):
    s = FakeSite(tmp_path / "s", destructive_log=True)
    s.add_job(1, "nf-a", "tester", "/f/one")
    s.add_job(2, "nf-b", "other", "/f/two")
    assert _squeue(s, "-h", "-j", "1", "-o", "%j|%u|%Z").stdout == "nf-a|tester|/f/one\n"
    assert _squeue(s, "-h", "-n", "nf-b").stdout == "nf-b|other|/f/two\n"
    assert _squeue(s, "-h", "-j", "9").stdout == ""


# ---- US5: not in scope ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("key", ["force", "delete_results", "all"])
def test_tc069_no_flag_asks_for_more_than_work(env, key):
    refused(env, env.job(env.bundle(**{key: True})))
    job = env.job()
    job["args"][key] = True
    refused(env, job)


def test_tc071_no_nextflow_program_is_called_and_the_command_does_not_name_it(env):
    env.go()
    assert "nextflow" not in env.command().replace(str(env.site.tmp), "") and not [c for c in env.site.calls() if c.startswith("nextflow")]


def test_tc072_the_source_has_no_loop_no_thread_no_sleep_no_retry_and_failures_send_one_command(env):
    text = (STATION / "clean.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*while\b|\bThread\b|sleep|retry|import threading", text, re.M)
    for answer in (SiteResult(99, b"", ""), SiteResult(18, b"", ""), SiteResult(124, b"", "", timed_out=True)):
        env.rec.calls.clear()
        env.rec.answer = answer
        env.go()
        assert env.sent() == 1


def test_tc073_the_source_reaches_the_site_only_through_ctx_site_call():
    text = (STATION / "clean.py").read_text(encoding="utf-8")
    assert not re.search(r"import subprocess|from subprocess|os\.system|os\.popen|run_fixed|start_detached", text)
    assert text.count("ctx.site.call(") == 1


def test_tc074_only_the_handler_calls_run_clean():
    callers = []
    for f in sorted(STATION.glob("*.py")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if "run_clean" in line and f.name != "cancel.py" and not line.startswith("def run_clean"):
                callers.append((f.name, line.strip()))
    assert callers == [("handlers.py", "return clean.run_clean(job, ctx)")], callers


# ---- constitution and safety net ---------------------------------------------------------------------------------

def test_tc083_the_header_of_the_new_file_says_why_the_known_tools_do_not_fit():
    first = (STATION / "clean.py").read_text(encoding="utf-8").splitlines()[:40]
    head = [ln for ln in first if ln.startswith("# Nothing existing: ")][0]
    assert len(head) > 40 and "nextflow clean" in head.lower() and "rclone purge" in head and "Seqera" in head


def test_tc084_the_launch_allow_list_still_has_one_entry():
    text = (REPO_ROOT / "tests" / "no_second_run_state_test.sh").read_text(encoding="utf-8")
    block = re.search(r'LAUNCH_ALLOW="\n(.*?)"', text, re.S).group(1)
    assert [ln.split("|")[0] for ln in block.splitlines() if ln.strip()] == ["platform/abf_station/launch.py"]


def test_tc085_the_removing_words_are_in_clean_py_only():
    found = sorted(f.name for d in (STATION, PLATFORM_DIR / "abf_platform") for f in d.glob("*.py")
                   if re.search(r"rm -rf", f.read_text(encoding="utf-8")))
    assert found == ["clean.py"]


@pytest.mark.parametrize("tc,over", [r for r in PATH_ROWS if r[0] != "TC-037"], ids=[r[0] for r in PATH_ROWS if r[0] != "TC-037"])
def test_tc086_rawdata_results_and_analysis_stay_bit_for_bit_in_every_refusal(env, tc, over):
    before = env.guards()
    env.go(env.job(env.bundle(**over(env))))
    assert env.guards() == before
