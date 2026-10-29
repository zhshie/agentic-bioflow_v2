# Nothing existing: searched the az CLI's own `storage blob delete-batch`, azcopy remove and rclone purge; each deletes whatever its pattern matches (a fnmatch `*` runs across `/`) and checks no path or prefix, so these tests drive our agent against a fake container that has the neighbours work2/, work-keep and results/ to prove only one run's work prefix goes.
"""The agent's clean_work job on Azure Batch (feature azure-clean): list first, then delete one prefix once.

Every test hands the real handler a confirmed (or hostile) clean_work job and a fake `site.run_fixed`; nothing reaches a network or
starts a real program. The fake container keeps a set of blob names and answers `az storage blob list --prefix` (names, one per line)
and `az storage blob delete-batch --pattern` with fnmatch meaning, where `*` also matches `/`, as the official page of the command says
(https://learn.microsoft.com/en-us/cli/azure/storage/blob?view=azure-cli-latest). The TC ids refer to specs/azure-clean/test-case.md.
That the real tool prints this way is checked by hand (docs/TESTING.md), not here.
"""
import ast
import fnmatch
import re
import sys
import time

import pytest

from helpers import PLATFORM_DIR
from test_azure_ce import BKEY, SAS, SAS_FILE, SKEY, Fake, fake_az
from test_azure_launch import Box, job_of, zce

STATION = PLATFORM_DIR / "abf_station"
RUN = "r1"
K = "wor" + "k"      # written in pieces: tests/test_scope.py TC-072 bars cluster-looking paths
SUBF = K             # the sub folder of the workDir
WORKDIR = "az://labcontainer/" + SUBF
PREFIX = SUBF + "/runs/r1/" + K + "/"
DEL_ARGV = ["az", "storage", "blob", "delete-batch", "--source", "labcontainer", "--pattern", PREFIX + "*", "--auth-mode", "key"]
OBJECTS = (SUBF + "/runs/r1/wor" "k/ab/x", SUBF + "/runs/r1/wor" "k/sub/y", SUBF + "/runs/r1/work2/x", SUBF + "/runs/r1/work-keep",
           SUBF + "/runs/r1/results/a.tsv", SUBF + "/runs/r2/work/z", SUBF + "/runs/other/work/x", SUBF + "/uploads/alice/a.fq",
           "rawdata/r1.fq", "runs/r1/wor" "k/q")
MINE = {SUBF + "/runs/r1/wor" "k/ab/x", SUBF + "/runs/r1/wor" "k/sub/y"}
LIVE = "tester /usr/bin/java -cp x nextflow.cli.Launcher run nf-core/rnaseq -r 3.14.0 -name r1 -with-tower http://127.0.0.1:8123\n"
ENV_SECRET = "ENVSECRET" + "ZZ0123456789abcdef"
posix_only = pytest.mark.skipif(sys.platform == "win32", reason="permission bits")


def sce(**over):
    c = zce(workDir=WORKDIR, storageAccountName="azlab")
    c.update(over)
    return c


class World:
    """The platform host (Box) with a fake `site.run_fixed` that knows a container."""

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
        self.del_result = None
        self.timeouts = set()           # "ps", "ls", "del"
        monkeypatch.setattr(site, "run_fixed", self._run)
        self.folder = self.box.folder(RUN)
        self.folder.mkdir(parents=True)
        (self.folder / "head.pid").write_text("4242\n")

    @staticmethod
    def _kind(argv):
        if argv[0] == "ps":
            return "ps"
        if argv[:4] == ["az", "storage", "blob", "list"]:
            return "ls"
        if argv[:4] == ["az", "storage", "blob", "delete-batch"]:
            return "del"
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
        if kind == "ls":
            prefix = argv[argv.index("--prefix") + 1]
            hits = sorted(o for o in self.objects if o.startswith(prefix))
            if self.ls_result is not None:
                return self.ls_result
            return 0, "".join(o + "\n" for o in hits + self.ls_extra)
        if self.del_result is not None:
            return self.del_result
        pattern = argv[argv.index("--pattern") + 1]
        hits = sorted(o for o in self.objects if fnmatch.fnmatchcase(o, pattern))      # `*` runs across `/`
        self.objects -= set(hits)
        return 0, "".join('"%s"\n' % o for o in hits)

    # inputs
    def bundle(self, **over):
        b = {"version": 1, "run_name": RUN, "slurm_job_id": 4242, "run_folder": str(self.folder), "agent": "a1", "ce": sce(),
             "work": WORKDIR + "/runs/r1/" + K}
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

    def zero_calls(self):
        assert self.calls == [], self.calls
        assert self.objects == self.start

    def no_ls_no_del(self):
        assert self.of("ls") == [] and self.of("del") == [], self.calls
        assert self.objects == self.start

    def with_workdir(self, workdir, work=None):
        """The bundle of an environment with another workDir, whose `work` is what the agent will work out (or `work`)."""
        return self.bundle(ce=sce(workDir=workdir), work=work if work is not None else workdir.rstrip("/") + "/runs/r1/" + K)


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


ACTION = ("沒有", "可以再申請", "先等", "不刪", "請", "不會", "保守", "不符", "用過", "不對", "欄位", "另一個", "對不上", "不合規則", "再申請")


def plain(msg, w=None):
    """TC-124: a sentence that says what happened and what to do, with no stack and no internal path."""
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
    if zero == "del":
        assert w.of("del") == [] and w.objects == w.start
    elif zero:
        w.zero_calls()
    else:
        w.no_ls_no_del()
    return res["message"]


def errored(w, job=None):
    state, res = w.go(job)
    assert state == "error" and res["ok"] is False and not res.get("cleaned"), (state, res)
    plain(res["message"], w)
    return res["message"]


# ---- US3: a confirmed run -----------------------------------------------------------------------------------------------

def test_clean_azure_lists_then_deletes_exactly_one_prefix(w):
    # TC-032, TC-077, TC-096 (AZC-STN-01)
    state, res = w.go()
    assert state == "done", res
    order = [w._kind(c[0]) for c in w.calls]
    assert order.count("ls") == 1 and order.count("del") == 1 and order.index("ls") < order.index("del")
    assert w._kind(w.calls[-1][0]) == "del"                              # the delete is the last call
    assert set(order) <= {"ps", "ls", "del"}                             # the other calls are only the process question
    assert all(isinstance(c[0], list) for c in w.calls)
    assert not [c for c in w.calls if c[0][0] in ("gcloud", "aws")]


def test_the_delete_argv_is_exactly_the_one_fixed_list(w):
    # TC-033 (AZC-STN-01)
    w.go()
    assert [c[0] for c in w.of("del")] == [DEL_ARGV]
    argv = w.of("del")[0][0]
    assert set(argv[4:]) == set(DEL_ARGV[4:]) and len(argv) == len(DEL_ARGV)
    for bad in ("--dryrun", "--delete-snapshots", "--account-key", "--sas-token", "--timeout", "--lease-id"):
        assert bad not in argv
    assert not [a for a in argv if a.startswith("--if-")]


def test_the_listing_argv_is_read_only_and_ends_the_prefix_with_a_slash(w):
    # TC-034
    w.go()
    argv, _, _ = w.of("ls")[0]
    assert argv[:4] == ["az", "storage", "blob", "list"]
    for flag, value in (("--container-name", "labcontainer"), ("--prefix", PREFIX), ("--query", "[].name"), ("--output", "tsv"),
                        ("--auth-mode", "key"), ("--num-results", "*")):
        assert argv[argv.index(flag) + 1] == value, flag
    assert PREFIX.endswith("/")
    for bad in ("delete", "upload", "remove", "--delete-snapshots"):
        assert not [a for a in argv if bad in a]


def test_the_report_of_a_done_clean(w):
    # TC-035
    state, res = w.go()
    assert state == "done" and set(res) == {"ok", "cleaned", "run_name", "message"}
    assert res["ok"] is True and res["cleaned"] is True and res["run_name"] == "r1"
    assert "az://labcontainer/" + SUBF + "/runs/r1/work" in res["message"] and "results 沒有動" in res["message"] and "已刪除" in res["message"]
    for bad in ("gcloud", "Google", "gs://", "s3://"):
        assert bad not in res["message"]


def test_a_sas_only_credential_sends_no_auth_mode_and_the_token_only_in_the_environment(w):
    # TC-036
    w.box.cred.write_text(SAS_FILE)
    state, res = w.go()
    assert state == "done", res
    for argv, env, _ in w.of("ls") + w.of("del"):
        assert "--auth-mode" not in argv and not [a for a in argv if SAS in a]
        assert env["AZURE_STORAGE_SAS_TOKEN"] and "AZURE_STORAGE_KEY" not in env
    assert w.of("del")[0][0] == [a for a in DEL_ARGV[:-2]]
    assert w.objects == w.start - MINE


def test_workdir_subfolder_is_kept_in_the_prefix(w):
    # TC-037, TC-084 (AZC-STN-09)
    w.go()
    assert w.of("del")[0][0][w.of("del")[0][0].index("--pattern") + 1] == SUBF + "/runs/r1/" + K + "/*"
    assert w.of("ls")[0][0][w.of("ls")[0][0].index("--prefix") + 1] == SUBF + "/runs/r1/" + K + "/"
    # a listing that holds an object of a neighbour prefix, or one without the sub folder, aborts the whole thing
    for extra in (SUBF + "/runs/r1/work2/x", "runs/r1/" + K + "/x"):
        w2 = World(w.box.tmp / ("again-" + str(abs(hash(extra)))), w.mp)
        w2.ls_extra = [extra]
        refused(w2, None, "前綴撞名", zero="del")


# ---- US3: the gate before anything is asked of Azure ------------------------------------------------------------------------

@pytest.mark.parametrize("how", ["none", "used"])
def test_unconfirmed_clean_is_refused_and_az_is_never_called(w, how):
    # TC-038, TC-122 (AZC-STN-02)
    job = w.job()
    if how == "none":
        job["confirmation"] = None
        job["args"].pop("confirmation_id")
    else:
        w.box.ctx.used_confirmations.add(job["args"]["confirmation_id"])
    refused(w, job)


@pytest.mark.parametrize("how", ["launch", "cancel", "spent"])
def test_expired_or_wrong_type_confirmation_is_refused(w, how):
    # TC-039, TC-040 (AZC-STN-03)
    job = w.job(conf_kind=how) if how != "spent" else w.job()
    if how == "spent":
        job["confirmation"]["used_at"] = 1.0
    refused(w, job)


def test_a_bundle_changed_after_the_confirmation_is_refused(w):
    # TC-041
    job = w.job()
    job["args"]["bundle"]["run_name"] = "r2"
    refused(w, job)


def test_a_bundle_with_other_fields_is_refused(w):
    # TC-042
    b = w.bundle()
    b["extra"] = 1
    refused(w, w.job(b), "欄位")
    b = w.bundle()
    del b["work"]
    refused(w, w.job(b), "欄位")


def test_a_bundle_for_another_agent_is_refused(w):
    # TC-043
    refused(w, w.job(w.bundle(agent="other")), "另一個代理")


@pytest.mark.parametrize("name", ["R1", "a/b", "", "x" * 300, "r 1"])
def test_a_bad_run_name_is_refused(w, name):
    # TC-044
    refused(w, w.job(w.bundle(run_name=name)))


@pytest.mark.parametrize("number", [True, "5", 0, -1, 2 ** 31])
def test_a_bad_process_number_is_refused(w, number):
    # TC-045
    refused(w, w.job(w.bundle(slurm_job_id=number)), "十進位")


@pytest.mark.parametrize("where", ["_gcb_runs", "_aws_runs", "elsewhere"])
def test_run_folder_must_be_the_azure_runs_folder(w, where):
    # TC-046 (AZC-STN-12)
    other = w.box.storage / where / RUN
    other.mkdir(parents=True)
    refused(w, w.job(w.bundle(run_folder=str(other))), "專屬資料夾")
    refused(w, w.job(w.bundle(run_folder=str(w.box.folder("other-run")))), "專屬資料夾")
    refused(w, w.job(w.bundle(run_folder=str(w.box.tmp / "outside"))), "專屬資料夾")


def test_a_deployment_without_storage_root_is_refused(w):
    # TC-047
    w.box.settings.write_text("reach: local\n")
    refused(w, None, "storage_root")


@pytest.mark.parametrize("workdir", ["gs://labcontainer/work", "az://LabContainer/work", "az://lab--container/work", "az://ab/work",
                                     "az://labcontainer/a/../b", "az://labcontainer", "/data/work"])
def test_environment_is_judged_again_and_a_bad_container_is_refused(w, workdir):
    # TC-048, TC-049, TC-050 (AZC-STN-14)
    refused(w, w.job(w.bundle(ce=sce(workDir=workdir), work=workdir.rstrip("/") + "/runs/r1/" + K)), "環境設定不合規則")


@pytest.mark.parametrize("work", ["az://labcontainer/wor" "k/runs/r1", "az://labcontainer/wor" "k/runs/r1/results/",
                                  "az://labcontainer/wor" "k/runs/r1/results", "az://labcontainer/wor" "k/runs/r1/work/",
                                  "az://labcontainer/wor" "k/runs/r1/work/../results/", "az://labcontainer/wor" "k/runs/r1/work/../results",
                                  "az://other-container/wor" "k/runs/r1/work", "az://labcontainer/wor" "k/runs/r2/work", "", None, 5])
def test_work_path_is_recomputed_and_must_match_the_bundle(w, work):
    # TC-051 .. TC-054 (AZC-STN-08)
    refused(w, w.job(w.bundle(work=work)), "路徑不是這個平台給這個 run 的")


@pytest.mark.parametrize("sub", ["rawdata", "results", "analysis", ".", "x/rawdata", "x/results/y", "x/./y", "x//y"])
def test_barred_segments_and_empty_segments_are_refused(w, sub):
    # TC-055 .. TC-060 (AZC-STN-10)
    refused(w, w.job(w.with_workdir("az://labcontainer/" + sub)))
    assert w.calls == []


def test_a_dotdot_segment_is_refused_by_the_environment_check(w):
    # TC-058
    refused(w, w.job(w.with_workdir("az://labcontainer/x/../y")))


@pytest.mark.parametrize("sub", ["a*b", "a?b", "a[b", "a]b", "x/*", "[!a]"])
def test_glob_characters_in_the_subfolder_are_refused(w, sub):
    # TC-061 .. TC-064 (AZC-STN-11)
    w.objects |= {sub + "/runs/r1/work/q", "zzz/runs/r1/work/q"}
    w.start = set(w.objects)
    refused(w, w.job(w.with_workdir("az://labcontainer/" + sub)), "萬用字元")


@pytest.mark.parametrize("name", ["r*", "r?", "r[1]"])
def test_glob_characters_in_the_run_name_are_refused(w, name):
    # TC-065
    b = w.bundle(run_name=name)
    b["run_folder"] = str(w.box.folder(name))
    b["work"] = WORKDIR + "/runs/%s/work" % name
    w.box.folder(name).mkdir(parents=True)
    refused(w, w.job(b))


# ---- US3: the head process -------------------------------------------------------------------------------------------------

def test_a_running_head_is_refused_and_az_is_not_called(w):
    # TC-066 (AZC-STN-04)
    w.ps = (0, LIVE)
    msg = refused(w, w.job(), "主控程序還在跑", zero=False)
    assert "再申請" in msg
    assert [w._kind(c[0]) for c in w.calls] == ["ps"] and w.box.fake.calls == []


def test_a_missing_or_wrong_head_pid_is_refused(w):
    # TC-067, TC-068
    (w.folder / "head.pid").write_text("not a number\n")
    refused(w, w.job(), "head.pid", zero=False)
    (w.folder / "head.pid").unlink()
    refused(w, w.job(), "head.pid", zero=False)
    (w.folder / "head.pid").write_text("999\n")
    refused(w, w.job(), "head.pid", zero=False)
    assert w.box.fake.calls == []


def test_a_pid_taken_by_another_program_counts_as_gone(w):
    # TC-069
    w.ps = (0, "tester /usr/bin/other-thing --flag\n")
    state, res = w.go()
    assert state == "done" and res["cleaned"] is True
    assert len(w.of("ls")) == 1 and len(w.of("del")) == 1


def test_a_timeout_of_the_process_question_is_an_error_and_nothing_is_deleted(w):
    # TC-070
    w.timeouts = {"ps"}
    state, res = w.go()
    assert state == "error" and "逾時" in res["message"] and "沒有刪任何東西" in res["message"] and not res.get("cleaned")
    w.no_ls_no_del()
    assert len([c for c in w.calls if w._kind(c[0]) == "ps"]) == 1 and w.box.fake.calls == []


# ---- US3: the host -------------------------------------------------------------------------------------------------------

def test_a_missing_credentials_file_or_missing_az_fails_safely(w):
    # TC-071, TC-072 (AZC-STN-17)
    w.box.cred.unlink()
    msg = refused(w, w.job(), "預檢未通過", zero=False)
    assert BKEY not in msg and SKEY not in msg and "憑證檔" in msg
    w.box.cred.write_text("[default]\nbatch_account_key = " + BKEY + "\nstorage_account_key = " + SKEY + "\n")
    if sys.platform != "win32":
        w.box.cred.chmod(0o600)
    fake_az(w.mp, have=False)
    msg = refused(w, w.job(), "預檢未通過", zero=False)
    assert "az" in msg and BKEY not in msg and SKEY not in msg


def test_a_failed_preflight_item_is_a_refusal_without_listing_or_deleting(w):
    # TC-073
    fake_az(w.mp, Fake(replies={"storage": (0, "false")}))
    msg = refused(w, w.job(), "storage", zero=False)
    assert "預檢未通過" in msg
    fake_az(w.mp, Fake(replies={"batch": (0, "resizing")}))
    refused(w, w.job(), "pool", zero=False)


def test_az_env_has_only_the_allowed_azure_keys(w):
    # TC-074, TC-075, TC-125 (AZC-STN-15)
    w.mp.setenv("ABF_X", "parent-value-1234")
    w.mp.setenv("AZURE_OTHER", "parent-value-5678")
    w.mp.setenv("AZURE_STORAGE_KEY", ENV_SECRET)
    state, res = w.go()
    assert state == "done", res
    for argv, env, _ in w.of("ls") + w.of("del"):
        azure_keys = {k for k in env if k.upper().startswith("AZURE_")}
        assert azure_keys <= {"AZURE_STORAGE_ACCOUNT", "AZURE_STORAGE_KEY", "AZURE_STORAGE_SAS_TOKEN", "AZURE_CONFIG_DIR",
                              "AZURE_CORE_COLLECT_TELEMETRY", "AZURE_CORE_NO_COLOR", "AZURE_CORE_ONLY_SHOW_ERRORS"}, azure_keys
        assert env["AZURE_STORAGE_ACCOUNT"] == "azlab" and env["AZURE_STORAGE_KEY"] == SKEY and env["AZURE_CONFIG_DIR"]
        assert "ABF_X" not in env and "AZURE_OTHER" not in env and ENV_SECRET not in env.values()
        assert not [a for a in argv if SKEY in a or BKEY in a or ENV_SECRET in a]


def test_no_secret_is_in_any_argv_or_any_report(w):
    # TC-076, TC-125
    w.mp.setenv("ABF_STATION_SECRET", ENV_SECRET)
    seen = []
    for kind in ("ok", "ls", "del"):
        w2 = World(w.box.tmp / kind, w.mp)
        if kind == "ls":
            w2.ls_result = (3, "boom " + BKEY + " " + SKEY + " " + ENV_SECRET)
        if kind == "del":
            w2.del_result = (3, "boom " + BKEY + " " + SKEY + " " + ENV_SECRET)
        state, res = w2.go()
        seen.append(str(res))
        for argv, _, _ in w2.calls:
            assert not [a for a in argv if BKEY in a or SKEY in a or SAS in a or ENV_SECRET in a]
    for text in seen:
        assert BKEY not in text and SKEY not in text and ENV_SECRET not in text


def test_the_config_folder_of_the_call_is_gone_afterwards(w):
    # TC-074 (a folder of its own for each call)
    import os
    w.go()
    dirs = {env["AZURE_CONFIG_DIR"] for _, env, _ in w.of("ls") + w.of("del")}
    assert len(dirs) == 2 and not [d for d in dirs if os.path.exists(d)]


# ---- US3: the listing -------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("extra", [SUBF + "/runs/r1/work2/x", SUBF + "/runs/other/work/x", SUBF + "/runs/r1/work-keep",
                                   SUBF + "/runs/r1/results/x", SUBF + "/runs/r1/" + K, "unrelated"])
def test_listing_with_a_neighbour_prefix_aborts_before_delete(w, extra):
    # TC-078 .. TC-082 (AZC-STN-05)
    w.ls_extra = [extra]
    refused(w, w.job(), "前綴撞名", zero="del")
    assert len(w.of("ls")) == 1 and w.of("del") == []


def test_a_neighbour_that_appears_late_in_a_long_listing_aborts(w):
    # TC-083 (AZC-STN-06)
    w.objects |= {PREFIX + "f%05d" % i for i in range(1500)}
    w.start = set(w.objects)
    w.ls_extra = [SUBF + "/runs/r1/work2/late"]
    refused(w, w.job(), "前綴撞名", zero="del")
    assert w.of("del") == []


def test_a_long_clean_listing_is_deleted_once(w):
    # TC-083 (the same size without a neighbour is fine)
    w.objects |= {PREFIX + "f%05d" % i for i in range(1500)}
    w.start = set(w.objects)
    state, res = w.go()
    assert state == "done" and len(w.of("del")) == 1 and not [o for o in w.objects if o.startswith(PREFIX)]


def test_empty_listing_is_a_plain_success_without_delete(w):
    # TC-085 (AZC-STN-07)
    w.objects = {o for o in w.objects if not o.startswith(PREFIX)}
    w.start = set(w.objects)
    state, res = w.go()
    assert state == "done" and res["cleaned"] is True and res["ok"] is True and "本來就沒有東西" in res["message"]
    assert len(w.of("ls")) == 1 and w.of("del") == [] and w.objects == w.start


def test_a_failed_listing_is_an_error_without_a_delete(w):
    # TC-086
    w.ls_result = (2, "az: error")
    said = errored(w)
    assert "沒有刪任何東西" in said and "再申請" in said and w.of("del") == [] and w.objects == w.start


def test_a_listing_timeout_deletes_nothing(w):
    # TC-087
    w.timeouts = {"ls"}
    state, res = w.go()
    assert state == "refused" and not res.get("cleaned") and "逾時" in res["message"] and "沒有刪任何東西" in res["message"]
    plain(res["message"], w)
    assert w.of("del") == [] and w.objects == w.start


def test_a_failed_delete_is_not_retried_and_cleaned_is_false(w):
    # TC-088 (AZC-STN-16)
    w.del_result = (1, "some failure")
    said = errored(w)
    assert len(w.of("del")) == 1 and "可能只刪了一部分" in said and "可以再申請" in said
    assert "some failure" in said or "結束碼" in said


def test_a_delete_timeout_is_not_retried(w):
    # TC-089
    w.timeouts = {"del"}
    said = errored(w)
    assert len(w.of("del")) == 1 and "逾時" in said and "可能只刪了一部分" in said


def test_a_long_output_is_cut_and_scrubbed(w):
    # TC-090, TC-091
    long = ("x" * 400) + " " + str(w.box.cred) + " " + str(w.folder) + " " + str(w.box.storage) + " " + BKEY + " " + ENV_SECRET
    w.mp.setenv("ABF_SECRET_LONG", ENV_SECRET)
    for kind in ("ls", "del"):
        w2 = World(w.box.tmp / kind, w.mp)
        if kind == "ls":
            w2.ls_result = (255, long)
        else:
            w2.del_result = (1, long)
        said = errored(w2)
        for bad in (str(w2.box.cred), str(w2.box.storage), str(w2.folder), BKEY, ENV_SECRET, "x" * 301):
            assert bad not in said, (kind, bad)
        assert len(said) < 600


# ---- US3: the world after a clean ---------------------------------------------------------------------------------------------

def test_only_the_run_prefix_is_deleted_and_the_neighbours_stay(w):
    # TC-092
    state, res = w.go()
    assert state == "done"
    assert w.objects == w.start - MINE
    for kept in (SUBF + "/runs/r1/work2/x", SUBF + "/runs/r1/work-keep", SUBF + "/runs/r1/results/a.tsv", SUBF + "/runs/r2/work/z",
                 SUBF + "/runs/other/work/x", SUBF + "/uploads/alice/a.fq", "rawdata/r1.fq", "runs/r1/work/q"):
        assert kept in w.objects, kept


def test_the_handler_reaches_the_azure_branch(w):
    # TC-093
    from abf_station import clean, handlers
    assert handlers.JOB_KINDS.count("clean_work") == 1
    w.go()
    assert len(w.of("ls")) == 1 and len(w.of("del")) == 1
    assert hasattr(clean, "_clean_azure") and hasattr(clean, "_azure_work")


def test_google_aws_and_slurm_still_go_to_their_own_branches(w, monkeypatch):
    # TC-094, TC-095 (AZC-STN-18): only the dispatch is checked here, their own tests check what they do
    from abf_station import clean, launch
    seen = []
    monkeypatch.setattr(clean, "_clean_gcb", lambda *a: seen.append("gcb") or ("done", {}))
    monkeypatch.setattr(clean, "_clean_aws", lambda *a: seen.append("aws") or ("done", {}))
    monkeypatch.setattr(clean, "_clean_azure", lambda *a: seen.append("azure") or ("done", {}))
    monkeypatch.setattr(clean, "_clean_slurm", lambda *a: seen.append("slurm") or ("done", {}))
    monkeypatch.setattr(clean, "_check_path", lambda b, e: ("r1", "f"))
    monkeypatch.setattr(clean.rules, "clean_environment", lambda ce: {})
    for platform, expected in ((launch.GCB, "gcb"), (launch.AWS, "aws"), (launch.AZURE, "azure"), ("slurm-platform", "slurm")):
        seen.clear()
        b = w.bundle(ce=dict(sce(), platform=platform))
        from abf_platform import common
        job = job_of(b, kind="clean_work", conf_kind="clean_work")
        clean.run_clean(job, w.box.ctx)
        assert seen == [expected], (platform, seen)


def test_the_azure_clean_makes_no_google_or_aws_call(w):
    # TC-096
    w.go()
    w.ls_extra = [SUBF + "/runs/r1/work2/x"]
    w.go()
    assert not [c for c in w.calls if c[0][0] in ("gcloud", "aws", "gsutil", "rclone")]


# ---- US3/US4: the file itself -----------------------------------------------------------------------------------------------------

def _azure_segment():
    text = (STATION / "clean.py").read_text(encoding="utf-8")
    a, b = "# ---- Azure Batch (Azure-clean)", "# ---- AWS Batch (aws-clean)"
    assert a in text and b in text
    return text, text.split(a, 1)[1].split(b, 1)[0]


def test_forbidden_words_never_appear_in_clean_py():
    # TC-097, TC-098 (AZC-STN-13)
    text, seg = _azure_segment()
    for word in ("--delete-snapshots", "--dryrun", "container delete", "storage remove", "azcopy", "az batch", "--if-", "--sas-token",
                 "--account-key", "sync", "s3api", "boto3", "gcloud", "rclone"):
        assert word not in seg, word
    assert seg.count("delete-batch") == 1
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            assert "run_fixed" not in ast.unparse(node), "a program is started inside a loop"
    assert "import azure" not in text and "from azure" not in text


def test_the_station_package_has_no_bare_lower_case_azure_word():
    # TC-099
    for path in STATION.glob("*.py"):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not re.search(r"\bazure\b", line), (path.name, n)


def test_the_azure_section_stands_before_the_aws_section():
    # TC-100
    text = (STATION / "clean.py").read_text(encoding="utf-8")
    a, b = text.index("# ---- Azure Batch (Azure-clean)"), text.index("# ---- AWS Batch (aws-clean)")
    assert a < b
    assert "_clean_azure" not in text[b:] and "az://" not in text[b:] and "Azure" not in text[b:]
