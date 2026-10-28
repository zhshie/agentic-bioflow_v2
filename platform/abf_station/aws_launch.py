# Nothing existing: searched Nextflow's awsbatch executor, the launch command of the Seqera CLI and nf-core's tower launch tool; they all hand the work to a Seqera service, none lets a local agent start the head process after a person's yes and stop that one process after a second yes.
"""Launch and cancel on AWS Batch, as the station agent on the platform host does them (aws-launch).

The head process of the analysis runs on this host; the compute is done by Batch jobs that the head process asks for. The text of the
head script lives in launch.py, which also builds and checks the bundle; this module does what is done with a confirmed bundle: check
the host, write the run's own folder, start the head process and remember its number, and later send ONE stop signal to exactly that
process after checking that it is still the process that was started (the cancel is the one the Google Batch run uses, gcb_launch).

Order of a launch, and every step that fails stops the job (nothing is retried):
  1. the confirmation (launch.verify_confirmation) already passed when this is called: nothing was written or started before that;
  2. the bundle is built again from this agent's own settings and must be identical to the confirmed one;
  3. the time left, a host with /proc, the credential file again, Java 17+, Nextflow and the aws command, and the read-only preflight
     of the environment. Nothing is written before all of these pass;
  4. the run's own folder is made (never over an existing one) and its files are written, never through a link;
  5. the head process is started in a session of its own, with the credential file named only in its environment; its number is written.

The credential file's path is this agent's own setting. It is not in the bundle, the head script, the arguments of any program, a result
or a message; the program that starts the head process gets it in its environment and nowhere else.
"""
import os

from . import aws_preflight, gcb_launch, launch, rules
from . import site as host
from .gcb_launch import _check_tools, _has_proc, _plain_env, _settle_seconds, _tail, _write_new

KEY_SHOWN = "[credential file]"
CHECKED_AS = "aws-launch"      # the name the re-check of the credential file is given; the platform's own name for it is not in the bundle
CANCEL_REMINDER = "取消請求已送出（主控程序 pid %d）；請到 AWS Console 的 Batch 頁確認 job 都已結束，沒取消乾淨的工作仍會計費"


def _head_env(ce, cred_path):
    """The environment of the head process, built from nothing but what is named here."""
    env = aws_preflight._aws_env(cred_path, ce["region"])      # no ABF_*, no other AWS_* of this agent's own; the file by path only
    env.pop("TOWER_ACCESS_TOKEN", None)      # the head script reads the token from its own file
    for e in ce.get("environment") or []:
        if e.get("head", True):
            env[e["name"]] = e.get("value", "")
    return env


def _check_aws_cli():
    try:
        rc, _out = host.run_fixed(["aws", "--version"], _plain_env(), 60)
    except TimeoutError:
        raise rules.Refusal("aws 沒有在時間內回答，不送出 (aws did not answer in time)")
    if rc != 0:
        raise rules.Refusal("平台主機上找不到 aws 指令：Nextflow 的 AWS Batch 需要 AWS CLI，請先安裝再送出，沒有建立任何東西 (the AWS CLI is not installed)")


def _check_environment(ce, cred_path):
    """The read-only preflight of the environment (the credential file, the key, the job queue, the bucket), again, just before the launch."""
    try:
        env = aws_preflight.clean_environment(dict(ce, credentialsId=CHECKED_AS))
    except rules.Refusal as e:
        raise rules.Refusal("內容不合規則：%s" % e)
    res = aws_preflight.run_preflight(env, cred_path=cred_path)
    failed = [c for c in res["checks"] if c["status"] != "pass" and c["name"] != "credential_name"]      # the name is the platform's business
    if failed:
        shown = "；".join("%s（%s）" % (c["name"], aws_preflight._scrub(c["detail"]).replace(str(cred_path), KEY_SHOWN)) for c in failed)
        raise rules.Refusal("預檢未通過，沒有建立任何東西：" + shown)


def run_launch(job, ctx, bundle):
    """(state, result) of a confirmed launch on AWS Batch. The confirmation was verified by the caller."""
    if bundle.get("agent") != ctx.agent_name:
        raise rules.Refusal("這個內容包是給另一個代理的 (the bundle is for another agent)")
    token = job.get("run_token")
    if not isinstance(token, str) or not token or len(token) > 200:
        raise rules.Refusal("平台沒有給這次執行的 token (no run token was sent)")
    try:
        rebuilt = launch.render_aws_bundle(ce=bundle["ce"], agent=bundle["agent"], facts=launch.own_facts(ctx), roots=[],
                                           run_name=bundle["run_name"], pipeline=bundle["pipeline"], revision=bundle["revision"],
                                           samplesheet=bundle["samplesheet"], params=bundle["params"], path_columns=bundle["path_columns"])
    except (launch.BundleError, KeyError, TypeError) as e:
        raise rules.Refusal("內容不合規則：%s" % e)
    if rebuilt != {k: v for k, v in bundle.items() if k not in launch.RECORDS}:
        raise rules.Refusal("內容與代理依自己的設定重新產生的不一致：不送出 (the bundle is not what this agent builds from its own settings)")
    if "upload_paths" in bundle:
        launch._check_upload_paths(bundle["upload_paths"], ctx)
    if launch._left(ctx, job) < launch._min_remaining():
        raise rules.Refusal("工作期限剩下的時間不足以安全送出 (too little of the deadline is left to start safely)")
    if not _has_proc():
        raise rules.Refusal("這台主機沒有 /proc：AWS Batch 的送出與取消需要 Linux 或 WSL（取消要靠 /proc 核對那個程序），不送出 "
                            "(this needs Linux or WSL)")
    cred_path = aws_preflight.credentials_path(ctx.settings_file)
    _check_tools()
    _check_aws_cli()
    _check_environment(bundle["ce"], cred_path)

    run, folder = bundle["run_name"], bundle["run_folder"]
    runs = os.path.dirname(folder)
    try:
        if os.path.islink(runs):
            raise rules.Refusal("%s 是捷徑，不寫進去 (a link, never written through)" % runs)
        os.makedirs(runs, mode=0o700, exist_ok=True)
        os.mkdir(folder, 0o700)
        os.chmod(folder, 0o700)
    except FileExistsError:
        raise rules.Refusal("專屬資料夾 %s 已存在，不覆蓋；請換一個 run 名稱。沒有改動任何東西 (the run folder exists already)" % folder)
    except OSError as e:
        return "error", {"ok": False, "message": "建不起專屬資料夾 %s（%s），尚未啟動 (could not make the run folder)" % (folder, e.__class__.__name__)}
    files = [(name, bundle["files"][name].encode("utf-8")) for name in launch.AWS_FILE_NAMES] + [("tower.token", token.encode("utf-8"))]
    try:
        for name, data in files:
            _write_new(os.path.join(folder, name), data)
    except OSError as e:
        left = "資料夾 %s 已建立，檔案可能不完整，尚未啟動" % folder
        return "error", {"ok": False, "message": "寫入專屬資料夾時出錯（%s）。%s" % (e.__class__.__name__, left), "left_on_site": left}

    try:
        proc = host.start_detached(["bash", os.path.join(folder, "head.sh")], _head_env(bundle["ce"], cred_path), folder,
                                   os.path.join(folder, "head.out"))
    except OSError as e:
        left = "資料夾 %s 與其中的檔案（未啟動，未刪除）" % folder
        return "error", {"ok": False, "message": "主控程序沒有啟動（%s）。不重試。" % e.__class__.__name__, "left_on_site": left}
    pid = getattr(proc, "pid", proc)
    if isinstance(pid, bool) or not isinstance(pid, int) or pid < 1:
        left = "資料夾 %s；主控程序可能已啟動，請查 -name %s 的程序" % (folder, run)
        return "error", {"ok": False, "message": "主控程序的編號不明：" + left, "left_on_site": left}
    try:
        _write_new(os.path.join(folder, "head.pid"), ("%d\n" % pid).encode("ascii"))
    except OSError as e:
        left = "資料夾 %s；主控程序（pid %d）已啟動但 head.pid 寫不進去，取消時需要它" % (folder, pid)
        return "error", {"ok": False, "message": "寫 head.pid 時出錯（%s）。%s" % (e.__class__.__name__, left), "left_on_site": left}

    code = host.wait_for_exit(proc, _settle_seconds())      # a head process that is gone within a few seconds did not start
    if code is not None:
        tail = aws_preflight._scrub(_tail(os.path.join(folder, "head.out")))
        left = "資料夾 %s（保留供檢查）" % folder
        return "error", {"ok": False, "message": "主控程序一啟動就結束了（結束碼 %s）：%s。%s" % (code, tail or "沒有輸出", left),
                         "left_on_site": left}
    return "done", {"ok": True, "slurm_job_id": pid, "run_name": run, "run_folder": folder,
                    "message": "已啟動：主控程序編號（pid）%d，run 名稱 %s，專屬資料夾 %s；AWS Batch 的工作與費用從現在開始計"
                               % (pid, run, folder)}


def run_cancel(job, ctx, bundle):
    """(state, result) of a confirmed cancel of an AWS Batch run: the one-signal cancel of gcb_launch, in this type's own folder."""
    return gcb_launch._cancel_head(ctx, bundle, launch.AWS_RUNS, CANCEL_REMINDER)
