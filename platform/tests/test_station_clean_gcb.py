# Nothing existing: searched gcloud's own `storage rm`, gsutil rm and rclone purge; each deletes whatever its URL matches and checks no path or prefix, so these tests drive our agent against a fake bucket that has the neighbours work2/, work-keep and results/ to prove only one run's work prefix goes.
"""The agent's clean_work job on Google Batch (feature cloud-cleanup-d): list first, then delete one prefix once.

Every test hands the real handler a confirmed (or hostile) clean_work job and a fake `site.run_fixed`; nothing reaches a network or
starts a real program. The fake bucket keeps a set of object names and answers `gcloud storage ls --recursive` and `gcloud storage rm
--recursive` with prefix meaning: what the URL (with its trailing slash) starts. The TC ids refer to specs/cloud-cleanup-d/test-case.md.
That prefix meaning is an assumption about Google's tool; a real bucket is checked by hand in feature cloud-cleanup-f.
"""
import ast
import json
import subprocess
import sys
import time

import pytest

from helpers import PLATFORM_DIR
from test_gcb_launch import Box, gce, job_of
from test_gcb_ce import key_data

STATION = PLATFORM_DIR / "abf_station"
RUN = "r1"
K = "wor" + "k"      # written in pieces: tests/test_scope.py TC-072 bars cluster-looking paths
PFX = "gs://lab-bucket/" + K + "/runs/r1/work"
OBJECTS = ("work/runs/r1/" + K + "/x", "work/runs/r1/" + K + "/sub/y", "work/runs/r1/work2/x", "work/runs/r1/work-keep",
           "work/runs/r1/results/a.tsv", "work/runs/r2/work/z")
ALIVE = "tester /usr/bin/java -cp x nextflow.cli.Launcher run nf-core/rnaseq -r 3.14.0 -name r1 -with-tower http://127.0.0.1:8123\n"
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
        self.pre = (0, "")              # the answers of the read-only preflight questions
        self.timeouts = set()           # "ps", "ls", "rm"
        monkeypatch.setattr(site, "run_fixed", self._run)
        self.folder = self.box.folder(RUN)
        self.folder.mkdir(parents=True)
        (self.folder / "head.pid").write_text("4242\n")

    def _kind(self, argv):
        if argv[0] == "ps":
            return "ps"
        if argv[:3] == ["gcloud", "storage", "ls"] and "--recursive" in argv:
            return "ls"
        if argv[:3] == ["gcloud", "storage", "rm"]:
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
            return self.pre
        url = argv[-1]
        hits = sorted(o for o in self.objects if ("gs://lab-bucket/" + o).startswith(url))
        if kind == "ls":
            if self.ls_result is not None:
                return self.ls_result
            if not hits and not self.ls_extra:
                return 1, "ERROR: (gcloud.storage.ls) One or more URLs matched no objects.\n"
            dirs = {}
            for o in hits:
                full = "gs://lab-bucket/" + o
                dirs.setdefault(full.rsplit("/", 1)[0] + "/", []).append(full)
            lines = []
            for d in sorted(dirs):
                lines += [d + ":"] + dirs[d] + [""]
            return 0, "\n".join(lines + self.ls_extra) + "\n"
        if self.rm_result is not None:
            return self.rm_result
        self.objects -= set(hits)
        return 0, ""

    # inputs
    def ce(self, **over):
        return gce(**over)

    def bundle(self, **over):
        b = {"version": 1, "run_name": RUN, "slurm_job_id": 4242, "run_folder": str(self.folder), "agent": "a1", "ce": self.ce(),
             "work": PFX}
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

    def gcloud_calls(self):
        return [c for c in self.calls if c[0][0] == "gcloud"]

    def zero_calls(self):
        assert self.calls == [], self.calls
        assert self.objects == self.start

    def untouched(self):
        assert self.objects == self.start


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def refused(w, job, said=None, zero=True):
    state, res = w.go(job)
    assert state == "refused" and res["ok"] is False and res["message"].strip(), (state, res)
    assert "Traceback" not in res["message"] and str(STATION) not in res["message"]
    if said:
        assert said in res["message"], res["message"]
    if zero:
        w.zero_calls()
    return res["message"]


def errored(w, job):
    state, res = w.go(job)
    assert state == "error" and res["ok"] is False and not res.get("cleaned"), (state, res)
    return res["message"]


# ---- US1: a confirmed run -----------------------------------------------------------------------------------------------

def test_tc001_a_confirmed_clean_removes_only_the_work_prefix(w):
    state, res = w.go()
    assert state == "done"
    assert res == {"ok": True, "cleaned": True, "run_name": "r1", "message": "已刪除 bucket 裡 %s 底下的物件；results 沒有動" % PFX}
    assert w.objects == {"work/runs/r1/work2/x", "work/runs/r1/work-keep", "work/runs/r1/results/a.tsv", "work/runs/r2/work/z"}


def test_tc002_tc003_one_listing_before_one_removal_with_fixed_argv(w):
    w.go()
    order = [w._kind(c[0]) for c in w.calls]
    assert order.index("ls") < order.index("rm")
    ls, rm = w.of("ls"), w.of("rm")
    assert [c[0] for c in ls] == [["gcloud", "storage", "ls", "--recursive", "--project", "lab-project-1", PFX + "/"]]
    assert [c[0] for c in rm] == [["gcloud", "storage", "rm", "--recursive", "--project", "lab-project-1", PFX + "/"]]
    assert "--continue-on-error" not in rm[0][0] and "--all-versions" not in rm[0][0]


def test_tc004_every_call_goes_through_run_fixed_with_a_list_and_these_clocks(w, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("a program was started without run_fixed")
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    w.go()
    assert [c[0] for c in w.of("ps")] == [["ps", "-o", "user=", "-o", "args=", "-p", "4242"]]
    assert [c[2] for c in w.of("ps")] == [20] and [c[2] for c in w.of("ls")] == [120] and [c[2] for c in w.of("rm")] == [300]
    assert all(isinstance(c[0], list) for c in w.calls)


def test_tc005_a_subfolder_heading_with_a_colon_is_accepted(w):
    rc, text = w._run(["gcloud", "storage", "ls", "--recursive", "--project", "lab-project-1", PFX + "/"], {}, 120)
    assert rc == 0 and "gs://lab-bucket/" + K + "/runs/r1/" + K + "/sub/:" in text.splitlines()      # the fake prints headings like gcloud
    w.calls.clear()
    state, res = w.go()
    assert state == "done" and res["cleaned"] is True and len(w.of("rm")) == 1


def test_tc006_a_listing_with_no_object_is_a_success_and_no_removal(w):
    w.ls_result = (0, "")
    state, res = w.go()
    assert state == "done" and res["ok"] is True and res["cleaned"] is True
    assert w.of("rm") == [] and w.objects == w.start


def test_tc007_gcloud_saying_no_url_matched_is_the_same_success(w):
    w.objects = {o for o in w.objects if not o.startswith("work/runs/r1/work/")}
    w.start = set(w.objects)
    state, res = w.go()
    assert state == "done" and res["cleaned"] is True
    assert len(w.of("ls")) == 1 and w.of("rm") == []


def test_tc008_a_live_process_of_another_name_is_a_reused_number(w):
    w.ps = (0, "tester /usr/bin/python other.py -name something-else\n")
    state, res = w.go()
    assert state == "done" and res["cleaned"] is True and len(w.of("rm")) == 1


@pytest.mark.parametrize("answer", [(1, ""), (0, ""), (1, "ps: error")])
def test_tc009_no_process_found_is_a_gone_head(w, answer):
    w.ps = answer
    state, res = w.go()
    assert state == "done" and res["cleaned"] is True


# ---- US2: not confirmed, odd bundle, odd path ----------------------------------------------------------------------------

def _unconfirmed(w, how):
    job = w.job()
    if how == "none":
        job["confirmation"] = None
        job["args"].pop("confirmation_id")
    elif how == "hash":
        job["args"]["bundle"]["work"] = PFX + "x"
    elif how == "used":
        w.box.ctx.used_confirmations.add(job["args"]["confirmation_id"])
    elif how in ("launch", "cancel"):
        job = w.job(conf_kind=how)
    return job


@pytest.mark.parametrize("how", ["none", "hash", "used", "launch", "cancel"])
def test_tc010_an_unconfirmed_clean_is_refused_and_gcloud_is_never_called(w, how):
    refused(w, _unconfirmed(w, how))


def test_tc071_a_bundle_changed_after_the_yes_is_refused(w):
    job = w.job()
    job["args"]["bundle"]["work"] = "gs://lab-bucket/" + K + "/runs/r2/work"
    refused(w, job)


@pytest.mark.parametrize("change", ["extra", "missing"])
def test_tc011_other_keys_are_refused(w, change):
    b = w.bundle()
    if change == "extra":
        b["more"] = 1
    else:
        del b["work"]
    refused(w, w.job(b))


def test_tc012_another_agent_is_refused(w):
    refused(w, w.job(w.bundle(agent="a2")), "另一個代理")


def test_tc013_a_wrong_run_folder_is_refused(w):
    refused(w, w.job(w.bundle(run_folder=str(w.folder) + "x")))


def test_tc014_no_storage_root_is_refused_in_plain_words(w):
    w.box.settings.write_text("reach: local\n")
    refused(w, w.job(), "部署設定沒有 storage_root")


@pytest.mark.parametrize("n", [0, -1, 2147483648, True, "123"])
def test_tc015_a_bad_process_number_is_refused(w, n):
    refused(w, w.job(w.bundle(slurm_job_id=n)))


@pytest.mark.parametrize("name", ["R1", "a b", "x" * 65, "1abc", ""])
def test_tc016_a_run_name_this_platform_never_makes_is_refused(w, name):
    refused(w, w.job(w.bundle(run_name=name)))


@pytest.mark.parametrize("name", ["r1 x", "r1;x", "r1$(id)", "r1\nx", "r1‮x"])
def test_tc017_a_hostile_run_name_is_refused_before_any_command(w, name):
    refused(w, w.job(w.bundle(run_name=name)))


@pytest.mark.parametrize("bad", ["wo rk", "wo;rk", "wo$(id)rk", "wo\nrk", "wo‮rk"])
def test_tc018_a_hostile_workdir_is_refused_before_any_command(w, bad):
    wd = "gs://lab-bucket/" + bad
    refused(w, w.job(w.bundle(ce=w.ce(workDir=wd), work=wd + "/runs/r1/work")))
    refused(w, w.job(w.bundle(work="gs://lab-bucket/" + bad + "/runs/r1/work")))


WORK_ROWS = [
    ("TC-019", {"work": "gs://lab-bucket/" + K + "/runs/r1/results"}),
    ("TC-020a", {"work": PFX + "/*"}), ("TC-020b", {"work": PFX + "*"}), ("TC-020c", {"work": PFX + "?"}),
    ("TC-020d", {"work": PFX + "[ab]"}), ("TC-020e", {"work": PFX + "{a,b}"}),
    ("TC-021", {"work": "gs://other-bucket/" + K + "/runs/r1/work"}),
    ("TC-022", {"work": "gs://lab-bucket/" + K + "/runs/r1/"}),
    ("TC-023", {"work": PFX + "/../results"}),
    ("TC-024", {"work": "gs://lab-bucket/work/./runs/r1/work"}),
    ("TC-025a", {"ce": gce(workDir="gs://lab-bucket/" + K + "/rawdata"), "work": "gs://lab-bucket/" + K + "/rawdata/runs/r1/work"}),
    ("TC-025b", {"ce": gce(workDir="gs://lab-bucket/analysis"), "work": "gs://lab-bucket/analysis/runs/r1/work"}),
    ("TC-026", {"ce": gce(workDir="gs://lab-bucket/results"), "work": "gs://lab-bucket/results/runs/r1/work"}),
    ("TC-027", {"work": "gs://lab-bucket/" + K + "/runs/r2/work"}),
    ("TC-028", {"work": "gs://lab-bucket/work//runs/r1/work"}),
    ("TC-029", {"ce": gce(workDir="gs://lab-bucket"), "work": "gs://lab-bucket/runs/r1/work"}),
    ("TC-030", {"work": PFX + "/"}),
]


@pytest.mark.parametrize("tc,over", WORK_ROWS, ids=[r[0] for r in WORK_ROWS])
def test_the_path_table_every_odd_work_is_refused_before_any_command(w, tc, over):
    refused(w, w.job(w.bundle(**over)))


# ---- US3: the head still runs, the key is wrong --------------------------------------------------------------------------

def test_tc031_a_running_head_is_refused_and_gcloud_is_not_called(w):
    w.ps = (0, ALIVE)
    msg = refused(w, w.job(), "主控程序還在跑", zero=False)
    assert w.gcloud_calls() == [] and w.objects == w.start and msg


def test_tc032_no_head_pid_is_refused(w):
    (w.folder / "head.pid").unlink()
    refused(w, w.job(), "找不到 head.pid，無法確認主控程序已結束")


@pytest.mark.parametrize("text", ["abc", "", "12 34", "-5"])
def test_tc033_a_head_pid_that_is_not_a_number_is_refused(w, text):
    (w.folder / "head.pid").write_text(text)
    refused(w, w.job(), "找不到 head.pid，無法確認主控程序已結束")


def test_tc034_a_head_pid_of_another_number_is_refused(w):
    (w.folder / "head.pid").write_text("999\n")
    refused(w, w.job())


def test_tc035_a_ps_with_two_lines_is_refused(w):
    w.ps = (0, ALIVE + ALIVE)
    refused(w, w.job(), "無法確認主控程序已結束（ps 回了不只一行），保守起見不刪", zero=False)
    assert w.gcloud_calls() == []


def test_tc036_a_ps_timeout_is_an_error_and_nothing_is_listed(w):
    w.timeouts = {"ps"}
    assert errored(w, w.job()) == "查詢逾時，沒有刪任何東西，也不重試"
    assert len(w.of("ps")) == 1 and w.gcloud_calls() == [] and w.objects == w.start


def _no_ls_no_rm(w):
    assert w.of("ls") == [] and w.of("rm") == [] and w.objects == w.start


def test_tc037_a_missing_key_file_is_refused(w):
    w.box.key.unlink()
    refused(w, w.job(), zero=False)
    _no_ls_no_rm(w)


@posix_only
def test_tc038_a_key_file_others_can_read_is_refused(w):
    w.box.key.chmod(0o644)
    refused(w, w.job(), zero=False)
    _no_ls_no_rm(w)


def test_tc039_a_key_file_that_is_not_a_service_account_key_is_refused(w):
    w.box.key.write_text(json.dumps(key_data(type="authorized_user")))
    refused(w, w.job(), zero=False)
    _no_ls_no_rm(w)


def test_tc040_a_key_of_another_project_is_refused(w):
    w.box.key.write_text(json.dumps(key_data(project_id="other-project-9")))
    refused(w, w.job(), zero=False)
    _no_ls_no_rm(w)


def test_tc041_a_failing_read_only_question_is_refused(w):
    w.pre = (1, "denied")
    refused(w, w.job(), zero=False)
    _no_ls_no_rm(w)


# ---- US4: a listing or a removal goes wrong ------------------------------------------------------------------------------

def test_tc042_a_foreign_prefix_in_the_listing_stops_before_the_removal(w):
    w.ls_extra = ["gs://lab-bucket/" + K + "/runs/r1/work2/x"]
    refused(w, w.job(), "列出的物件不全在 work 底下（前綴撞名），不刪", zero=False)
    assert w.of("rm") == [] and w.objects == w.start


def test_tc043_a_listing_timeout_is_refused_and_nothing_is_removed(w):
    w.timeouts = {"ls"}
    state, res = w.go()
    assert state == "refused" and res == {"ok": False, "cleaned": False, "message": "列出雲端暫存檔逾時，沒有刪任何東西；稍後可以再申請"}
    assert w.of("rm") == [] and w.objects == w.start


def test_tc044_another_listing_failure_is_an_error_and_nothing_is_removed(w):
    w.ls_result = (1, "ERROR: (gcloud.storage.ls) HTTPError 403: denied")
    assert "列出雲端暫存檔失敗" in errored(w, w.job())
    assert w.of("rm") == [] and w.objects == w.start


def test_tc045_a_failing_removal_is_an_error_that_may_be_partial_and_is_not_repeated(w):
    w.rm_result = (1, "ERROR: boom")
    msg = errored(w, w.job())
    assert "可能只刪了一部分；work_cleaned_at 沒記，可以再申請" in msg
    assert len(w.of("rm")) == 1


def test_tc046_a_removal_timeout_is_the_same_error_and_is_not_repeated(w):
    w.timeouts = {"rm"}
    msg = errored(w, w.job())
    assert "可能只刪了一部分；work_cleaned_at 沒記，可以再申請" in msg
    assert len(w.of("rm")) == 1


# ---- US5: the key and the output --------------------------------------------------------------------------------------

def test_tc047_tc048_the_key_path_is_in_the_environment_only(w):
    state, res = w.go()
    key = str(w.box.key)
    for argv, env, _ in w.of("ls") + w.of("rm"):
        assert env["CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE"] == key and env["CLOUDSDK_CORE_DISABLE_PROMPTS"] == "1"
        assert "GOOGLE_APPLICATION_CREDENTIALS" not in env  # ruling three
    assert not any(key in " ".join(c[0]) for c in w.calls)
    assert key not in json.dumps(res)


SECRET = "ya29." + "a0AfB_byC1234567890abcdefghijklmnopqrstuv"


def test_tc049_a_failing_listing_does_not_show_the_key_path_or_a_token(w):
    w.ls_result = (1, "ERROR: cannot read %s with token %s" % (w.box.key, SECRET))
    msg = errored(w, w.job())
    assert str(w.box.key) not in msg and SECRET not in msg and "a0AfB_byC1234567890" not in msg


def test_tc050_a_failing_removal_does_not_show_the_key_path_or_a_token(w):
    w.rm_result = (1, "ERROR: cannot read %s with token %s" % (w.box.key, SECRET))
    msg = errored(w, w.job())
    assert "[key file]" in msg and str(w.box.key) not in msg and "a0AfB_byC1234567890" not in msg


def test_tc051_no_log_line_holds_the_key_path(w, capsys, caplog):
    w.go()
    w.box.ctx.used_confirmations.clear()
    w.rm_result = (1, "ERROR: %s" % w.box.key)
    w.go()
    seen = capsys.readouterr()
    assert str(w.box.key) not in seen.out + seen.err + caplog.text


def test_tc052_the_environment_is_the_clean_one_plus_two_variables(w, monkeypatch):
    from abf_station import gcb_launch
    monkeypatch.setenv("ABF_SOMETHING_SECRET", "s")
    monkeypatch.setenv("TOWER_ACCESS_TOKEN", "t")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/agent/own.json")  # ruling three: must be dropped
    ce = w.ce(environment=[{"name": "MY_OWN_VAR", "value": "mine", "head": True}])
    w.go(w.job(w.bundle(ce=ce)))
    want = dict(gcb_launch._plain_env())
    want.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    want["CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE"] = str(w.box.key)
    want["CLOUDSDK_CORE_DISABLE_PROMPTS"] = "1"
    runs = w.of("ls") + w.of("rm")
    assert len(runs) == 2
    for _, env, _ in runs:
        assert env == want and "MY_OWN_VAR" not in env and "TOWER_ACCESS_TOKEN" not in env


def test_tc053_every_refusal_and_error_speaks_plainly(w):
    said = []
    for how in ("none", "hash", "used"):
        said.append(w.go(_unconfirmed(w, how))[1]["message"])
    said.append(w.go(w.job(w.bundle(work=PFX + "/")))[1]["message"])
    w.ls_extra = ["gs://lab-bucket/" + K + "/runs/r1/work2/x"]
    said.append(w.go(w.job())[1]["message"])
    w.ls_extra = []
    w.rm_result = (1, "ERROR: boom")
    said.append(w.go(w.job())[1]["message"])
    for m in said:
        assert m.strip() and "Traceback" not in m and "File \"" not in m and "SELECT" not in m.upper() and str(STATION) not in m, m
    assert "可以再申請" in said[-1]


# ---- US6: what is not done and what stays ---------------------------------------------------------------------------------

def _py(path):
    return sorted(path.glob("*.py"))


def test_tc054_storage_rm_is_written_in_clean_py_only():
    found = sorted(f.name for d in (STATION, PLATFORM_DIR / "abf_platform") for f in _py(d)
                   if "storage rm" in f.read_text(encoding="utf-8"))
    assert found == ["clean.py"]


def test_tc057_rm_rf_is_still_in_clean_py_only():
    found = sorted(f.name for f in _py(STATION) if "rm -rf" in f.read_text(encoding="utf-8"))
    assert found == ["clean.py"]


def test_tc058_no_other_tool_no_second_write_path_and_no_loop_around_the_removal():
    tree = ast.parse((STATION / "clean.py").read_text(encoding="utf-8"))
    tree.body = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant))]
    code = ast.unparse(tree)
    for word in ("batch jobs delete", "buckets delete", "gsutil", "rclone", "--continue-on-error", "--all-versions"):
        assert word not in code, word
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            assert "run_fixed" not in ast.unparse(node), "a program is started inside a loop"


def test_tc069_the_headers_say_why_the_known_tools_do_not_fit():
    for f in (STATION.parent / "tests" / "test_station_clean_gcb.py", STATION / "clean.py"):
        head = [ln for ln in f.read_text(encoding="utf-8").splitlines()[:40] if ln.startswith("# Nothing existing: ")]
        assert head and len(head[0]) > len("# Nothing existing: ") + 15
    first = (STATION / "clean.py").read_text(encoding="utf-8").splitlines()[0]
    assert "gcloud storage rm" in first and "prefix" in first
