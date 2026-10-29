# Nothing existing: searched Nextflow's azurebatch executor, the launch command of the Seqera CLI and nf-core's tower launch tool; they all hand the work to a Seqera service, none lets a local agent start the head process with azurebatch after a person's yes and stop that one process after a second yes.
"""Launch and cancel on Azure Batch, as the station agent on the platform host does them (the azure_launch slice).

The head process of the analysis runs on this host; the compute is done by Batch tasks in a pool that already exists. The text of the
head script lives in launch.py, which also builds and checks the bundle; this module does what is done with a confirmed bundle: check
the host, write the run's own folder, start the head process and remember its number, and later send ONE stop signal to exactly that
process after checking that it is still the process that was started (the cancel is the one the Google Batch run uses, gcb_launch).

Order of a launch, and every step that fails stops the job (nothing is retried):
  1. the confirmation (launch.verify_confirmation) already passed when this is called: nothing was written or started before that;
  2. the bundle is built again from this agent's own settings and must be identical to the confirmed one;
  3. the time left, a host with /proc, Java 17+, Nextflow and the Azure command line, the credential file again, and the read-only
     preflight of the environment. Nothing is written before all of these pass;
  4. the run's own folder is made (never over an existing one) and its files are written, never through a link;
  5. the head process is started in a session of its own, with the Batch and storage keys in its environment only; its number is written.

The keys come from this agent's own credential file. They are not in the bundle, the head script, the config file, the arguments of any
program, a result or a message; the program that starts the head process gets them in its environment and nowhere else.
"""
import os

from . import azure_preflight, gcb_launch, launch, rules
from . import site as host
from .gcb_launch import _check_tools, _has_proc, _plain_env, _settle_seconds, _tail, _write_new

KEY_SHOWN = "[credential file]"
CHECKED_AS = "launch-check"      # the name the re-check of the credential file is given; the platform's own name for it is not in the bundle
CANCEL_REMINDER = ("取消請求已送出（主控程序 pid %d）：已對它送出一次終止信號（SIGTERM）。請到 Azure Portal 的 Batch 帳號頁確認工作與 pool 的狀態，"
                   "沒停下來的要自己處理；費用從工作開始算到它真的停止為止")
CRED_HINT = "（憑證檔的位置可用環境變數 %s 指定 (where the credential file is looked for)）" % azure_preflight.CREDENTIALS_ENV


def _plain_az_env():
    """The environment of a program this agent asks about: none of its own ABF_ or Azure variables, no token."""
    return {k: v for k, v in _plain_env().items() if not k.upper().startswith("AZURE_")}


def _head_env(ce, cred_path):
    """The environment of the head process, built from nothing but what is named here: the two keys Nextflow reads, and the environment's own."""
    creds, problem = azure_preflight._read_shape(cred_path)
    if not creds:
        raise rules.Refusal("憑證檔不能用，沒有啟動任何東西：%s" % str(problem or "?").replace(str(cred_path), KEY_SHOWN) + CRED_HINT)
    env = _plain_az_env()      # no ABF_*, no other AZURE_* of this agent's own
    env.pop("TOWER_ACCESS_TOKEN", None)      # the head script reads the token from its own file
    env["AZURE_BATCH_ACCOUNT_KEY"] = creds["batch_account_key"]
    if creds.get("storage_account_key"):
        env["AZURE_STORAGE_ACCOUNT_KEY"] = creds["storage_account_key"]
    else:
        env["AZURE_STORAGE_SAS_TOKEN"] = creds["storage_sas_token"].lstrip("?")
    for e in ce.get("environment") or []:
        if e.get("head", True):
            env[e["name"]] = e.get("value", "")
    return env


def _check_az_cli():
    try:
        rc, _out = host.run_fixed(["az", "--version"], _plain_az_env(), 60)
    except TimeoutError:
        raise rules.Refusal("az 沒有在時間內回答，不送出 (az did not answer in time)")
    if rc != 0:
        raise rules.Refusal("平台主機上找不到 az 指令：預檢需要 Azure CLI，請先安裝再送出，沒有建立任何東西 (the Azure CLI is not installed)")


def _check_environment(ce, cred_path):
    """The read-only preflight of the environment (the credential file, the keys, the pool, the container), again, just before the launch."""
    try:
        env = azure_preflight.clean_environment(dict(ce, credentialsId=CHECKED_AS))
    except rules.Refusal as e:
        raise rules.Refusal("內容不合規則：%s" % e)
    try:
        res = azure_preflight.run_preflight(env, cred_path=cred_path)
    except Exception:      # a credential file the preflight cannot read at all; its content is never named
        raise rules.Refusal("憑證檔讀不了或格式不對，沒有建立任何東西" + CRED_HINT)
    failed = [c for c in res["checks"] if c["status"] != "pass" and c["name"] != "credential_name"]      # the name is the platform's business
    if failed:
        shown = "；".join("%s（%s）" % (c["name"], azure_preflight._scrub(c["detail"]).replace(str(cred_path), KEY_SHOWN)) for c in failed)
        hint = CRED_HINT if any(c["name"].startswith("credential") for c in failed) else ""
        raise rules.Refusal("預檢未通過，沒有建立任何東西：" + shown + hint)


def run_launch(job, ctx, bundle):
    """(state, result) of a confirmed launch on Azure Batch. The confirmation was verified by the caller."""
    if bundle.get("agent") != ctx.agent_name:
        raise rules.Refusal("這個內容包是給另一個代理的 (the bundle is for another agent)")
    token = job.get("run_token")
    if not isinstance(token, str) or not token or len(token) > 200:
        raise rules.Refusal("平台沒有給這次執行的 token (no run token was sent)")
    try:
        rebuilt = launch.render_azure_bundle(ce=bundle["ce"], agent=bundle["agent"], facts=launch.own_facts(ctx), roots=[],
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
        raise rules.Refusal("這台主機沒有 /proc：Azure Batch 的送出與取消需要 Linux 或 WSL（取消要靠 /proc 核對那個程序），不送出 "
                            "(this needs Linux or WSL)")
    cred_path = azure_preflight.credentials_path(ctx.settings_file)
    _check_tools()
    _check_az_cli()
    _check_environment(bundle["ce"], cred_path)
    head_env = _head_env(bundle["ce"], cred_path)      # judged before the folder is made: a bad file leaves nothing behind

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
    files = [(name, bundle["files"][name].encode("utf-8")) for name in launch.AZURE_FILE_NAMES] + [("tower.token", token.encode("utf-8"))]
    try:
        for name, data in files:
            _write_new(os.path.join(folder, name), data)
    except OSError as e:
        left = "資料夾 %s 已建立，檔案可能不完整，尚未啟動" % folder
        return "error", {"ok": False, "message": "寫入專屬資料夾時出錯（%s）。%s" % (e.__class__.__name__, left), "left_on_site": left}

    try:
        proc = host.start_detached(["bash", os.path.join(folder, "head.sh")], head_env, folder, os.path.join(folder, "head.out"))
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
        tail = azure_preflight._scrub(_tail(os.path.join(folder, "head.out")))
        left = "資料夾 %s（保留供檢查）" % folder
        return "error", {"ok": False, "message": "主控程序一啟動就結束了（結束碼 %s）：%s。%s" % (code, tail or "沒有輸出", left),
                         "left_on_site": left}
    return "done", {"ok": True, "slurm_job_id": pid, "run_name": run, "run_folder": folder,
                    "message": "已啟動：主控程序編號（pid）%d，run 名稱 %s，專屬資料夾 %s；Azure Batch 的工作與費用從現在開始計。"
                               "由 Azure 向實驗室的 Azure 帳號收費；本系統目前沒有費用預估與上限" % (pid, run, folder)}


def run_cancel(job, ctx, bundle):
    """(state, result) of a confirmed cancel of an Azure Batch run: the one-signal cancel of gcb_launch, in this type's own folder."""
    return gcb_launch._cancel_head(ctx, bundle, launch.AZURE_RUNS, CANCEL_REMINDER)
