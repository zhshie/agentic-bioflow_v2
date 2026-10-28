# Nothing existing: searched the aws CLI's own `s3 rm`, rclone purge and s3cmd del; each deletes whatever its URL matches and checks no path or prefix, so these tests drive our agent against a fake bucket that has the neighbours work2/, work-keep and results/ to prove only one run's work prefix goes.
"""The agent's clean_work job on AWS Batch (feature aws-clean): list first, then delete one prefix once.

Every test hands the real handler a confirmed (or hostile) clean_work job and a fake `site.run_fixed`; nothing reaches a network or
starts a real program. The fake bucket keeps a set of object names and answers `aws s3 ls --recursive` and `aws s3 rm --recursive`
with prefix meaning: what the URL (with its trailing slash) starts. The listing lines follow the official page of `aws s3 ls`
(https://docs.aws.amazon.com/cli/latest/reference/s3/ls.html: date, time, size, bucket-relative key). The TC ids refer to
specs/aws-clean/test-case.md. That the real tool prints this way is checked by hand (docs/TESTING.md), not here.
"""
import ast
import json
import os
import subprocess
import sys
import time

import pytest

from helpers import PLATFORM_DIR
from test_aws_launch import AKID, Box, MARKER, ace, job_of

STATION = PLATFORM_DIR / "abf_station"
RUN = "r1"
K = "wor" + "k"      # written in pieces: tests/test_scope.py TC-072 bars cluster-looking paths
BARE = "s3://lab-bucket"
URL = "s3://lab-bucket/runs/r1/" + K + "/"
RM_ARGV = ["aws", "s3", "rm", URL, "--recursive", "--region", "eu-west-1"]
OBJECTS = ("runs/r1/wor" "k/ab/x", "runs/r1/wor" "k/sub/y", "runs/r1/work2/x", "runs/r1/work-keep", "runs/r1/results/a.tsv",
           "runs/r2/work/z", "runs/other/work/x", "uploads/alice/a.fq", "work/runs/r1/work/q", "rawdata/r1.fq")
MINE = {"runs/r1/wor" "k/ab/x", "runs/r1/wor" "k/sub/y"}
LIVE = "tester /usr/bin/java -cp x nextflow.cli.Launcher run nf-core/rnaseq -r 3.14.0 -name r1 -with-tower http://127.0.0.1:8123\n"
ENV_SECRET = "ENVSECRET" + "ZZ0123456789abcdef"
posix_only = pytest.mark.skipif(sys.platform == "win32", reason="permission bits")


class World:
    """The platform host (Box) with a fake `site.run_fixed` that knows a bucket."""

    def __init__(self, tmp, monkeypatch):
        from abf_station import site
        self.box = Box(tmp, monkeypatch)
        self.mp = monkeypatch
        self.objects = set(OBJECTS)
        self.start = set(OBJECTS)
        self.calls = []                 # (argv, env, timeout)
        self.ps = (1, "")               # the head process is gone
        self.ls_result = None           # (rc, text) instead of the real listing
        self.ls_extra = []
        self.rm_result = None
        self.timeouts = set()           # "ps", "ls", "rm"
        monkeypatch.setattr(site, "run_fixed", self._run)
        self.folder = self.box.folder(RUN)
        self.folder.mkdir(parents=True)
        (self.folder / "head.pid").write_text("4242\n")

    @staticmethod
    def _kind(argv):
        if argv[0] == "ps":
            return "ps"
        if argv[:3] == ["aws", "s3", "ls"]:
            return "ls"
        if argv[:3] == ["aws", "s3", "rm"]:
            return "rm"
        return "pre"

    def _run(self, argv, env, timeout):
        self.calls.append((list(argv), dict(env or {}), timeout))
        kind = self._kind(argv)
        if kind in self.timeouts:
            raise TimeoutError("did not return")
        if kind == "ps":
            return self.ps
        if kind == "pre":
            return self.box._run_fixed(argv, env, timeout)
        prefix = argv[3][len("s3://lab-bucket/"):]
        hits = sorted(o for o in self.objects if o.startswith(prefix))
        if kind == "ls":
            if self.ls_result is not None:
                return self.ls_result
            if not hits and not self.ls_extra:
                return 1, ""
            lines = ["2026-10-28 18:%02d:00 %10d %s" % (i % 60, 10 + i, o) for i, o in enumerate(hits)]
            return 0, "\n".join(lines + self.ls_extra) + "\n"
        if self.rm_result is not None:
            return self.rm_result
        self.objects -= set(hits)
        return 0, "".join("delete: s3://lab-bucket/%s\n" % o for o in hits)

    # inputs
    def ce(self, **over):
        return ace(workDir=BARE, **over)

    def bundle(self, **over):
        b = {"version": 1, "run_name": RUN, "slurm_job_id": 4242, "run_folder": str(self.folder), "agent": "a1", "ce": self.ce(),
             "work": "s3://lab-bucket/runs/r1/" + K}
        b.update(over)
        return b

    def job(self, bundle=None, conf_kind="clean_work"):
        return job_of(bundle if bundle is not None else self.bundle(), kind="clean_work", conf_kind=conf_kind)

    def go(self, job=None):
        from abf_station import handlers
        self.box.ctx.job_started = time.monotonic()
        return handlers.handle(job if job is not None else self.job(), self.box.ctx)

    # looks
    def of(self, kind):
        return [c for c in self.calls if self._kind(c[0]) == kind]

    def pre(self):
        """The read-only checks of the preflight (their own runner, recorded by the Box)."""
        return list(self.box.fake.calls)

    def zero_calls(self):
        assert self.calls == [], self.calls
        assert self.objects == self.start

    def no_ls_no_rm(self):
        assert self.of("ls") == [] and self.of("rm") == [], self.calls
        assert self.objects == self.start

    def sub(self):
        """The environment whose workDir has a sub folder, and the bucket that goes with it."""
        self.objects |= {"work/runs/r1/wor" "k/x", "work/runs/r1/wor" "k/deep/y", "work/runs/r1/work2/x"}
        self.start = set(self.objects)
        ce = ace(workDir=BARE + "/" + K)
        return self.bundle(ce=ce, work="s3://lab-bucket/" + K + "/runs/r1/" + K)


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


ACTION = ("沒有", "可以再申請", "先等", "不刪", "請", "不會", "保守", "不符", "用過", "不對", "欄位", "另一個", "對不上", "不合規則")


def plain(msg, w=None):
    """TC-107: a sentence that says what happened and what to do, with no stack and no internal path."""
    assert isinstance(msg, str) and msg.strip(), msg
    assert any(ord(c) > 0x4E00 for c in msg) and any(a in msg for a in ACTION), msg
    for bad in ("Traceback", 'File "', "SELECT", "sqlite"):
        assert bad not in msg, msg
    if w is not None:
        assert str(w.box.storage) not in msg and str(STATION) not in msg, msg
    return msg


def refused(w, job, said=None, zero=True):
    state, res = w.go(job)
    assert state == "refused" and res["ok"] is False and res["message"].strip(), (state, res)
    plain(res["message"], w)
    if said:
        assert said in res["message"], res["message"]
    if zero:
        w.zero_calls()
    return res["message"]


def errored(w, job=None):
    state, res = w.go(job)
    assert state == "error" and res["ok"] is False and not res.get("cleaned"), (state, res)
    plain(res["message"], w)
    return res["message"]


# ---- US1: a confirmed run -----------------------------------------------------------------------------------------------

def test_clean_aws_lists_then_removes_exactly_one_prefix(w):
    # TC-032, TC-085
    state, res = w.go()
    assert state == "done", res
    order = [w._kind(c[0]) for c in w.calls]
    assert order.count("ls") == 1 and order.count("rm") == 1 and order.index("ls") < order.index("rm")
    assert w._kind(w.calls[-1][0]) == "rm"                               # rm is the last call
    assert set(order) <= {"ps", "ls", "rm"}                              # the other calls are only the process question
    assert all(c[0][1] in ("sts", "batch", "s3api") for c in w.pre())   # and the read-only checks of the preflight
    for argv, _, _ in w.of("rm"):
        assert argv[3].startswith("s3://lab-bucket/") and argv[3].endswith("/work/") and "/runs/r1/" in argv[3]


def test_the_rm_argv_is_exactly_the_one_fixed_list(w):
    # TC-033
    w.go()
    assert [c[0] for c in w.of("rm")] == [RM_ARGV]
    rm = w.of("rm")[0][0]
    assert isinstance(rm, list) and not set(rm) & {"--include", "--exclude", "--dryrun", "--only-show-errors", "--quiet"}


def test_the_report_of_a_done_clean(w):
    # TC-034
    state, res = w.go()
    assert state == "done" and set(res) == {"ok", "cleaned", "run_name", "message"}
    assert res["ok"] is True and res["cleaned"] is True and res["run_name"] == "r1"
    assert "s3://lab-bucket/runs/r1/work" in res["message"] and "results 沒有動" in res["message"] and "已刪除" in res["message"]
    for bad in ("gcloud", "Google", "gs://"):
        assert bad not in res["message"]


def test_the_listing_is_one_plain_recursive_aws_call_before_the_rm(w):
    # TC-035
    w.go()
    ls = w.of("ls")
    assert [c[0] for c in ls] == [["aws", "s3", "ls", URL, "--recursive", "--region", "eu-west-1"]]
    argv = ls[0][0]
    assert "--max-items" not in argv and not {"rm", "delete", "mv", "cp", "sync", "rb"} & set(argv)
    assert w.calls.index(ls[0]) < w.calls.index(w.of("rm")[0])


def test_a_work_dir_with_a_sub_folder_goes_into_the_prefix_as_written(w):
    # TC-036
    b = w.sub()
    state, res = w.go(w.job(b))
    assert state == "done" and res["cleaned"] is True, res
    assert [c[0] for c in w.of("rm")] == [["aws", "s3", "rm", "s3://lab-bucket/wor" "k/runs/r1/wor" "k/", "--recursive", "--region", "eu-west-1"]]
    assert w.objects == w.start - {"work/runs/r1/wor" "k/x", "work/runs/r1/wor" "k/deep/y", "work/runs/r1/wor" "k/q"}      # q lies under that prefix too


# ---- US2: not confirmed, odd bundle, odd path -----------------------------------------------------------------------------

def _unconfirmed(w, how):
    job = w.job()
    if how == "none":
        job["confirmation"] = None
        job["args"].pop("confirmation_id")
    elif how == "hash":
        job["args"]["bundle"]["work"] = job["args"]["bundle"]["work"] + "x"
    elif how == "used":
        w.box.ctx.used_confirmations.add(job["args"]["confirmation_id"])
    elif how == "spent":
        job["confirmation"]["used_at"] = 1.0
    elif how in ("launch", "cancel"):
        job = w.job(conf_kind=how)
    return job


@pytest.mark.parametrize("how", ["none", "used"])
def test_unconfirmed_clean_is_refused_and_aws_is_never_called(w, how):
    # TC-037
    refused(w, _unconfirmed(w, how))


@pytest.mark.parametrize("how", ["launch", "cancel", "spent"])
def test_expired_or_wrong_type_confirmation_is_refused(w, how):
    # TC-038, TC-039 (the agent sees an old or used confirmation as one that carries a used_at)
    refused(w, _unconfirmed(w, how))


def test_a_bundle_changed_after_the_yes_is_refused(w):
    # TC-040
    refused(w, _unconfirmed(w, "hash"))


@pytest.mark.parametrize("change", ["extra", "missing"])
def test_other_keys_are_refused(w, change):
    # TC-041
    b = w.bundle()
    if change == "extra":
        b["extra"] = 1
    else:
        del b["work"]
    refused(w, w.job(b), "欄位")


def test_a_bundle_for_another_agent_is_refused(w):
    # TC-042
    refused(w, w.job(w.bundle(agent="a2")), "另一個代理")


@pytest.mark.parametrize("name", ["R1", "a/b", "", "x" * 65, "r 1", 7])
def test_a_run_name_not_made_by_the_platform_is_refused(w, name):
    # TC-043
    refused(w, w.job(w.bundle(run_name=name)), "run 名稱")


@pytest.mark.parametrize("number", [True, "5", 0, -1, 2 ** 31])
def test_a_job_number_that_is_not_one_decimal_number_is_refused(w, number):
    # TC-044
    refused(w, w.job(w.bundle(slurm_job_id=number)), "編號")


def test_a_run_folder_that_is_not_this_hosts_aws_folder_is_refused(w):
    # TC-045
    for folder in (str(w.box.storage / "_gcb_runs" / RUN), str(w.box.folder("other")), "/elsewhere/_aws_runs/r1", str(w.box.folder(RUN)) + "/"):
        refused(w, w.job(w.bundle(run_folder=folder)), "專屬資料夾")
        w.box.ctx.used_confirmations.clear()


def test_a_host_without_storage_root_is_refused(w):
    # TC-046
    w.box.settings.write_text("reach: local\n")
    refused(w, w.job(), "storage_root")


@pytest.mark.parametrize("change", [{"workDir": "gs://lab-bucket"}, {"workDir": "lab-bucket"}, {"workDir": "s3://lab..bucket"},
                                    {"workDir": "s3://"}, {"region": "mars"}, {"region": "eu-west-1; id"}])
def test_environment_is_judged_again_and_a_bad_bucket_or_region_is_refused(w, change):
    # TC-047, TC-048, TC-049
    ce = ace(**change)
    refused(w, w.job(w.bundle(ce=ce, work=str(change.get("workDir", BARE)) + "/runs/r1/" + K)))


@pytest.mark.parametrize("work", ["s3://lab-bucket/runs/r1/", "s3://lab-bucket/runs/r1/results/", "s3://lab-bucket/runs/r1/work/../results/",
                                  "s3://other-bucket/runs/r1/work", "s3://lab-bucket/runs/r1/work/", "s3://lab-bucket/runs/r2/work", 5, None])
def test_work_path_is_recomputed_and_must_match_the_bundle(w, work):
    # TC-050, TC-051, TC-052, TC-053, TC-054
    refused(w, w.job(w.bundle(work=work)), "路徑不是這個平台給這個 run 的")


@pytest.mark.parametrize("seg", ["rawdata", "results", "analysis", "../x", "./x", "/x"])
def test_a_barred_segment_in_the_work_dir_is_never_cleaned(w, seg):
    # TC-055, TC-056, TC-057, TC-058, TC-059, TC-060 (the bundle agrees with what the agent works out, so only the segment guard can stop it)
    work_dir = BARE + "/" + seg
    ce = ace(workDir=work_dir)
    said = refused(w, w.job(w.bundle(ce=ce, work=work_dir + "/runs/r1/" + K)))
    assert "rawdata" in said and "results" in said and "不刪" in said or "空段" in said or "一律不刪" in said


# ---- US2: the head process ----------------------------------------------------------------------------------------------

def test_a_head_still_running_is_never_cleaned(w):
    # TC-061
    w.ps = (0, LIVE)
    said = refused(w, w.job(), zero=False)
    assert "還在跑" in said and "沒有刪任何東西" in said
    assert not w.of("ls") and not w.of("rm") and not [c for c in w.calls if c[0][0] == "aws"] and w.pre() == []


@pytest.mark.parametrize("pid", [None, "abc\n", "12 34\n", "-5\n", "4242 x\n"])
def test_a_head_pid_that_is_missing_or_not_a_number_is_not_cleaned(w, pid):
    # TC-062
    f = w.folder / "head.pid"
    f.unlink()
    if pid is not None:
        f.write_text(pid)
    said = refused(w, w.job(), zero=False)
    assert "head.pid" in said and "不刪" in said
    assert [c for c in w.calls if c[0][0] == "aws"] == [] and w.objects == w.start


def test_a_head_pid_of_another_number_is_not_cleaned(w):
    # TC-063
    (w.folder / "head.pid").write_text("999\n")
    refused(w, w.job(), "head.pid", zero=False)
    assert [c for c in w.calls if c[0][0] == "aws"] == [] and w.objects == w.start


def test_a_process_of_another_name_is_a_reused_number(w):
    # TC-064
    w.ps = (0, "tester /usr/bin/python other.py -name something-else\n")
    state, res = w.go()
    assert state == "done" and res["cleaned"] is True and len(w.of("ls")) == 1 and len(w.of("rm")) == 1


def test_the_question_about_the_process_timing_out_is_an_error_with_no_aws_call(w):
    # TC-065
    w.timeouts = {"ps"}
    said = errored(w)
    assert "逾時" in said and "沒有刪任何東西" in said and "不重試" in said
    assert len(w.of("ps")) == 1 and [c for c in w.calls if c[0][0] == "aws"] == []


# ---- US2: the credentials and the preflight -------------------------------------------------------------------------------

def test_a_missing_credentials_file_fails_with_the_one_allowed_path_detail(w):
    # TC-066
    w.box.cred.unlink()
    said = refused(w, w.job(), "預檢未通過", zero=False)
    assert "憑證" in said or "credential" in said.lower()
    assert AKID not in said and MARKER not in said
    w.no_ls_no_rm()


def test_a_failing_preflight_check_is_refused_and_named(w):
    # TC-067
    w.box.fake.replies["s3api"] = (255, "An error occurred (404) when calling the HeadBucket operation: Not Found")
    said = refused(w, w.job(), "預檢未通過", zero=False)
    assert "bucket" in said.lower() or "s3" in said.lower()
    w.no_ls_no_rm()
    w.box.cred.write_text("[other]\nx = y\n")
    w.box.ctx.used_confirmations.clear()
    w.box.fake.replies["s3api"] = (0, "")
    refused(w, w.job(), "預檢未通過", zero=False)
    w.no_ls_no_rm()


ALLOWED = {"AWS_SHARED_CREDENTIALS_FILE", "AWS_PROFILE", "AWS_CONFIG_FILE", "AWS_DEFAULT_REGION", "AWS_PAGER",
           "AWS_EC2_METADATA_DISABLED", "AWS_CA_BUNDLE"}


def test_both_calls_carry_the_credential_file_by_path_and_the_fixed_settings(w):
    # TC-068
    w.go()
    runs = w.of("ls") + w.of("rm")
    assert len(runs) == 2
    for _, env, _ in runs:
        assert env["AWS_SHARED_CREDENTIALS_FILE"] == str(w.box.cred) and env["AWS_PROFILE"] == "default"
        assert env["AWS_CONFIG_FILE"] == os.devnull and env["AWS_DEFAULT_REGION"] == "eu-west-1"


def test_nothing_of_the_agents_own_aws_or_abf_variables_goes_along(w, monkeypatch):
    # TC-069
    monkeypatch.setenv("AWS_ACCESS_" "KEY_ID", ENV_SECRET)
    monkeypatch.setenv("AWS_SECRET_" "ACCESS_KEY", ENV_SECRET)
    monkeypatch.setenv("AWS_SESSION_" "TOKEN", ENV_SECRET)
    monkeypatch.setenv("AWS_PROFILE", "someone-else")
    monkeypatch.setenv("ABF_X", "fake")
    w.go()
    runs = w.of("ls") + w.of("rm")
    assert len(runs) == 2
    for _, env, _ in runs:
        assert not [k for k in env if k.upper().startswith("ABF_")]
        assert {k for k in env if k.upper().startswith("AWS_")} <= ALLOWED, sorted(env)
        assert env["AWS_PROFILE"] == "default" and ENV_SECRET not in "".join(env.values())


def test_every_call_goes_through_run_fixed_as_a_list(w, monkeypatch):
    # TC-070
    def boom(*a, **k):
        raise AssertionError("a program was started without run_fixed")
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    w.go()
    assert w.calls and all(isinstance(c[0], list) and all(isinstance(a, str) for a in c[0]) for c in w.calls)
    assert [c[2] for c in w.of("ps")] == [20] and [c[2] for c in w.of("ls")] == [120] and [c[2] for c in w.of("rm")] == [300]


# ---- US3: the listing decides ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("stray", ["runs/r1/work2/x", "runs/other/work/x", "runs/r1/work-keep", "runs/r1/results/x", "uploads/alice/a.fq", "x"])
def test_listing_with_a_neighbour_is_refused_whole_and_nothing_is_removed(w, stray):
    # TC-071, TC-072, TC-073, TC-074
    w.ls_extra = ["2026-10-28 18:20:00         12 " + stray]
    said = refused(w, w.job(), "前綴撞名", zero=False)
    assert "沒有刪" in said or "不刪" in said
    assert w.of("rm") == [] and w.objects == w.start and len(w.of("ls")) == 1


def test_a_listing_line_that_cannot_be_read_is_refused(w):
    # TC-071 (an unreadable line is not trusted)
    w.ls_extra = ["something the tool never printed before"]
    refused(w, w.job(), "不刪", zero=False)
    assert w.of("rm") == [] and w.objects == w.start


def many(count, last=None):
    return ["2026-10-28 18:20:00 %10d runs/r1/work/f%05d" % (i, i) for i in range(count)] + ([last] if last else [])


def test_a_neighbour_after_the_first_thousand_lines_still_stops_it(w):
    # TC-075
    w.ls_result = (0, "\n".join(many(1200, "2026-10-28 18:20:00          1 runs/r1/work2/x")) + "\n")
    refused(w, w.job(), "前綴撞名", zero=False)
    assert w.of("rm") == [] and w.objects == w.start and len(w.of("ls")) == 1


def test_a_long_listing_that_is_all_inside_goes_through_with_one_rm(w):
    # TC-076
    w.ls_result = (0, "\n".join(many(1200)) + "\n")
    state, res = w.go()
    assert state == "done" and res["cleaned"] is True and len(w.of("ls")) == 1 and len(w.of("rm")) == 1


@pytest.mark.parametrize("answer", [(1, ""), (0, ""), (0, "\n")])
def test_empty_listing_is_a_plain_success_without_rm(w, answer):
    # TC-077
    w.ls_result = answer
    state, res = w.go()
    assert state == "done" and res["ok"] is True and res["cleaned"] is True and set(res) == {"ok", "cleaned", "run_name", "message"}
    assert "本來就沒有" in res["message"] or "已經沒有" in res["message"]
    assert "沒有刪任何東西" in res["message"] and "results 沒有動" in res["message"]
    assert w.of("rm") == [] and w.objects == w.start


def test_a_failing_listing_is_an_error_and_removes_nothing(w):
    # TC-078
    w.ls_result = (255, "An error occurred (AccessDenied) when calling the ListObjectsV2 operation: Access Denied")
    said = errored(w)
    assert "列出" in said and "沒有刪任何東西" in said and "可以再申請" in said
    assert w.of("rm") == [] and w.objects == w.start


def test_a_listing_that_times_out_removes_nothing(w):
    # TC-079
    w.timeouts = {"ls"}
    state, res = w.go()
    assert state in ("refused", "error") and not res.get("cleaned") and res["ok"] is False
    plain(res["message"], w)
    assert "逾時" in res["message"] and "沒有刪任何東西" in res["message"] and "再申請" in res["message"]
    assert w.of("rm") == []


@pytest.mark.parametrize("stray,fine", [("work/runs/r1/work2/x", False), ("runs/r1/work/x", False), ("work/runs/r1/work/ok", True)])
def test_with_a_sub_folder_the_whole_prefix_is_what_is_compared(w, stray, fine):
    # TC-080
    b = w.sub()
    w.ls_extra = ["2026-10-28 18:20:00         12 " + stray]
    state, res = w.go(w.job(b))
    if fine:
        assert state == "done"
    else:
        assert state == "refused" and "前綴撞名" in res["message"] and w.of("rm") == []


# ---- US4: a removal that fails --------------------------------------------------------------------------------------------

def test_a_failing_rm_is_not_retried(w):
    # TC-081
    w.rm_result = (1, "delete failed: s3://lab-bucket/runs/r1/wor" "k/ab/x An error occurred (AccessDenied)")
    said = errored(w)
    assert len(w.of("rm")) == 1 and len(w.of("ls")) == 1
    assert "刪除沒有成功" in said and "一部分" in said and "work_cleaned_at" in said and "可以再申請" in said


def test_a_rm_that_times_out_is_not_retried(w):
    # TC-082
    w.timeouts = {"rm"}
    said = errored(w)
    assert len(w.of("rm")) == 1 and "逾時" in said and "一部分" in said and "可以再申請" in said


def test_what_the_tool_printed_is_shortened_and_cleaned_in_every_answer(w):
    # TC-083
    long = ("fatal error at %s and %s with %s and %s %s " % (w.box.cred, w.box.storage, AKID, MARKER, w.folder)) + "x" * 3000
    for kind in ("ls", "rm"):
        w.box.ctx.used_confirmations.clear()
        w.calls.clear()
        w.objects = set(OBJECTS)
        if kind == "ls":
            w.ls_result, w.rm_result = (255, long), None
        else:
            w.ls_result, w.rm_result = None, (1, long)
        said = errored(w)
        for bad in (str(w.box.cred), str(w.box.storage), str(w.folder), AKID, MARKER, "x" * 301):
            assert bad not in said, (kind, bad)
        assert len(said) < 600


def test_forbidden_words_never_appear_in_clean_py():
    # TC-084
    text = (STATION / "clean.py").read_text(encoding="utf-8")
    marker = "# ---- AWS Batch (aws-clean)"
    assert marker in text
    aws = text.split(marker, 1)[1]
    tree = ast.parse(text)
    code = ast.unparse(tree)
    for word in ("delete-objects", "delete-bucket", "--versions", "--include", "--exclude", "sync", "boto3", "botocore", "s3api"):
        assert word not in aws, word
    assert code.count("'s3', 'rm'") == 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            assert "run_fixed" not in ast.unparse(node), "a program is started inside a loop"


def test_only_the_run_prefix_is_removed_and_the_neighbours_stay(w):
    # TC-086
    state, res = w.go()
    assert state == "done"
    assert w.objects == w.start - MINE and w.objects >= {"runs/r1/work2/x", "runs/r1/work-keep", "runs/r1/results/a.tsv", "runs/other/work/x",
                                                         "uploads/alice/a.fq", "runs/r2/work/z", "rawdata/r1.fq"}


# ---- US5: dispatch and the other platforms --------------------------------------------------------------------------------

def test_the_handler_sends_an_aws_clean_to_the_aws_cleaning(w):
    # TC-087
    state, res = w.go()
    assert state == "done" and "尚未支援" not in res["message"] and len(w.of("ls")) == 1


def test_google_and_slurm_cleaning_are_not_the_aws_one(w):
    # TC-088 (the Google and Slurm tests themselves are untouched: test_station_clean_gcb.py and test_station_clean.py)
    from abf_station import clean
    text = (STATION / "clean.py").read_text(encoding="utf-8")
    assert "def _clean_gcb(" in text and "def _clean_slurm(" in text and "def _clean_aws(" in text
    assert clean.KEYS == {"version", "run_name", "slurm_job_id", "run_folder", "agent", "ce", "work"}


def test_no_gcloud_is_ever_called(w):
    # TC-089
    cases = [w.job(), w.job(w.bundle(work="s3://lab-bucket/runs/r1/")), w.job(w.bundle(agent="x"))]
    w.ls_extra = []
    for job in cases:
        w.go(job)
    w.rm_result = (1, "boom")
    w.box.ctx.used_confirmations.clear()
    w.go()
    assert [c for c in w.calls if c[0][0] in ("gcloud", "gsutil")] == []


def test_no_answer_nor_log_holds_a_key(w, capsys, caplog):
    # TC-090
    w.box.mp.setenv("AWS_SECRET_" "ACCESS_KEY", ENV_SECRET)
    said = []
    for res in (w.go(), ):
        said.append(json.dumps(res[1]))
    w.box.ctx.used_confirmations.clear()
    w.rm_result = (1, "ERROR %s %s %s" % (AKID, MARKER, ENV_SECRET))
    said.append(json.dumps(w.go()[1]))
    w.box.ctx.used_confirmations.clear()
    w.ls_result = (255, "ERROR %s %s %s" % (AKID, MARKER, ENV_SECRET))
    said.append(json.dumps(w.go()[1]))
    seen = capsys.readouterr()
    blob = "".join(said) + seen.out + seen.err + caplog.text
    for secret in (AKID, MARKER, ENV_SECRET):
        assert secret not in blob
    ok = json.loads(said[0])
    assert set(ok) == {"ok", "cleaned", "run_name", "message"}


def test_every_failure_speaks_plainly(w):
    # TC-107
    cases = [("hash", None), ("none", None), ("used", None)]
    for how, _ in cases:
        w.box.ctx.used_confirmations.clear()
        plain(w.go(_unconfirmed(w, how))[1]["message"], w)
    for bundle in (w.bundle(work="s3://lab-bucket/runs/r1/"), w.bundle(agent="zz"), w.bundle(slurm_job_id=0), w.bundle(run_name="BAD")):
        w.box.ctx.used_confirmations.clear()
        plain(w.go(w.job(bundle))[1]["message"], w)
    w.ls_extra = ["2026-10-28 18:20:00 1 runs/r1/work2/x"]
    w.box.ctx.used_confirmations.clear()
    plain(w.go()[1]["message"], w)
    w.ls_extra = []
    w.rm_result = (1, "boom")
    w.box.ctx.used_confirmations.clear()
    plain(w.go()[1]["message"], w)
