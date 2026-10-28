# Nothing existing: searched Nextflow's google-batch executor, the launch command of the Seqera CLI and nf-core's tower launch tool; they all hand the work to a Seqera service, none lets a local agent start the head process after a person's yes and stop that one process after a second yes.
"""Launch and cancel on Google Cloud Batch, as the station agent on the platform host does them (gcb-launch, C-2).

The head process of the analysis runs on this host; the compute is done by Batch virtual machines that the head process asks for. The
text of the head script (and the word that starts it) lives in launch.py, which also builds and checks the bundle; this module does
what is done with a confirmed bundle: check the host, write the run's own folder, start the head process and remember its number, and
later send ONE stop signal to exactly that process after checking that it is still the process that was started.

Order of a launch, and every step that fails stops the job (nothing is retried):
  1. the confirmation (launch.verify_confirmation) already passed when this is called: nothing was written or started before that;
  2. the bundle is built again from this agent's own settings and must be identical to the confirmed one;
  3. the time left, a host with /proc, Java 17+ and Nextflow, and the read-only preflight of the environment (which covers the key
     file: present, private, a service-account key, of the right project). Nothing is written before all of these pass;
  4. the run's own folder is made (never over an existing one) and its files are written, never through a link;
  5. the head process is started in a session of its own, with the key file named only in its environment; its number is written.

The key file's path is this agent's own setting. It is not in the bundle, the head script, the arguments of any program, a result or a
message; the program that starts the head process gets it in its environment and nowhere else.
"""
import os
import re
import signal

from . import gcb_preflight, launch, rules
from . import site as host

PROC = "/proc"
SETTLE_ENV = "ABF_STATION_GCB_SETTLE_SECONDS"
SETTLE_DEFAULT = 5.0
TAIL = 300
JAVA_MIN = 17
KEY_SHOWN = "[key file]"


def _has_proc():
    return os.path.isdir(PROC)


def _current_user():
    try:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_name
    except (ImportError, KeyError, OSError, AttributeError):
        return os.environ.get("USER") or os.environ.get("USERNAME") or ""


def _proc_cwd(pid):
    """The working folder of a process as /proc says, or None."""
    try:
        return os.readlink("%s/%d/cwd" % (PROC, pid))
    except OSError:
        return None


def _write_new(path, data, mode=0o600):
    """Write a file that does not exist yet; an existing file or a link in its place makes this fail, never write through."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, mode)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.chmod(path, mode)


def _read_small(path, limit=64):
    """The first bytes of a plain file (never through a link), or None."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return None
    with os.fdopen(fd, "rb") as f:
        return f.read(limit)


def _plain_env():
    """The environment of a program this agent asks about: no setting of the agent's own, no key, no token."""
    return {k: v for k, v in os.environ.items()
            if not k.upper().startswith("ABF_") and k not in ("GOOGLE_APPLICATION_CREDENTIALS", "TOWER_ACCESS_TOKEN")}


def _head_env(ce, key_path):
    """The environment of the head process, built from nothing but what is named here."""
    env = _plain_env()
    env["GOOGLE_APPLICATION_CREDENTIALS"] = str(key_path)
    env["CLOUDSDK_CORE_DISABLE_PROMPTS"] = "1"
    for e in ce.get("environment") or []:
        if e.get("head", True):
            env[e["name"]] = e.get("value", "")
    return env


def _settle_seconds():
    try:
        return max(0.0, float(os.environ.get(SETTLE_ENV, SETTLE_DEFAULT)))
    except ValueError:
        return SETTLE_DEFAULT


def _check_tools():
    """Java 17 or newer and Nextflow answer on this host; the words say what to install."""
    from . import handlers      # its parsers of the two version lines; it imports this package's modules, so it is read here
    env = _plain_env()
    try:
        rc, out = host.run_fixed(["java", "-version"], env, 60)
    except TimeoutError:
        raise rules.Refusal("Java 沒有在時間內回答，不送出 (java did not answer in time)")
    major = handlers._parse_java(out) if rc == 0 else None
    if rc != 0:
        raise rules.Refusal("平台主機上找不到 Java：Nextflow 需要 Java 17 以上，請先安裝再送出，沒有建立任何東西 (Java 17 or newer is not installed)")
    if major is None:
        raise rules.Refusal("看不懂 Java 的版本；Nextflow 需要 Java 17 以上，沒有建立任何東西 (could not read the Java version)")
    if major < JAVA_MIN:
        raise rules.Refusal("平台主機上的 Java 是 %d 版，太舊了：Nextflow 需要 Java 17 以上，請升級再送出，沒有建立任何東西 "
                            "(Java %d is too old, Java 17 or newer is needed)" % (major, major))
    try:
        rc, out = host.run_fixed(["nextflow", "-version"], env, 120)
    except TimeoutError:
        raise rules.Refusal("Nextflow 沒有在時間內回答，不送出 (nextflow did not answer in time)")
    if rc != 0 or handlers._parse_nextflow(out) is None:
        raise rules.Refusal("平台主機上找不到可用的 Nextflow，請先安裝再送出，沒有建立任何東西 (Nextflow is not installed or does not answer)")


def _check_environment(ce, key_path):
    """The read-only preflight of the environment (the key file and the two gcloud questions), again, just before the launch."""
    try:
        env = gcb_preflight.clean_environment(ce)
    except rules.Refusal as e:
        raise rules.Refusal("內容不合規則：%s" % e)
    res = gcb_preflight.run_preflight(env, cred_path=key_path)
    failed = [c for c in res["checks"] if c["status"] != "pass" and c["name"] != "credential_name"]      # the name is the platform's business
    if failed:
        shown = "；".join("%s（%s）" % (c["name"], gcb_preflight._scrub(c["detail"]).replace(str(key_path), KEY_SHOWN)) for c in failed)
        raise rules.Refusal("預檢未通過，沒有建立任何東西：" + shown)


def _tail(path):
    """The last characters of the head process's output, with anything shaped like a credential hidden."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - TAIL * 4))
            raw = f.read()
    except OSError:
        return ""
    return gcb_preflight._scrub(raw.decode("utf-8", errors="replace")[-TAIL:]).strip()


def run_launch(job, ctx, bundle):
    """(state, result) of a confirmed launch on Google Batch. The confirmation was verified by the caller."""
    if bundle.get("agent") != ctx.agent_name:
        raise rules.Refusal("這個內容包是給另一個代理的 (the bundle is for another agent)")
    token = job.get("run_token")
    if not isinstance(token, str) or not token or len(token) > 200:
        raise rules.Refusal("平台沒有給這次執行的 token (no run token was sent)")
    try:
        rebuilt = launch.render_gcb_bundle(ce=bundle["ce"], agent=bundle["agent"], facts=launch.own_facts(ctx), roots=[],
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
        raise rules.Refusal("這台主機沒有 /proc：Google Batch 的送出與取消需要 Linux 或 WSL（取消要靠 /proc 核對那個程序），不送出 "
                            "(this needs Linux or WSL)")
    key_path = gcb_preflight.credentials_path(ctx.settings_file)
    _check_tools()
    _check_environment(bundle["ce"], key_path)

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
    files = [(name, bundle["files"][name].encode("utf-8")) for name in launch.GCB_FILE_NAMES] + [("tower.token", token.encode("utf-8"))]
    try:
        for name, data in files:
            _write_new(os.path.join(folder, name), data)
    except OSError as e:
        left = "資料夾 %s 已建立，檔案可能不完整，尚未啟動" % folder
        return "error", {"ok": False, "message": "寫入專屬資料夾時出錯（%s）。%s" % (e.__class__.__name__, left), "left_on_site": left}

    try:
        proc = host.start_detached(["bash", os.path.join(folder, "head.sh")], _head_env(bundle["ce"], key_path), folder,
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
        tail = _tail(os.path.join(folder, "head.out"))
        left = "資料夾 %s（保留供檢查）" % folder
        return "error", {"ok": False, "message": "主控程序一啟動就結束了（結束碼 %s）：%s。%s" % (code, tail or "沒有輸出", left),
                         "left_on_site": left}
    return "done", {"ok": True, "slurm_job_id": pid, "run_name": run, "run_folder": folder,
                    "message": "已啟動：主控程序編號（pid）%d，run 名稱 %s，專屬資料夾 %s；Google Batch 的工作與費用從現在開始計"
                               % (pid, run, folder)}


def _same_user(owner):
    me = _current_user()
    return bool(me) and (owner == me or (len(me) > 8 and owner in (me[:8], me[:7] + "+")))


GCB_CANCEL_REMINDER = "取消請求已送出（主控程序 pid %d）；請到 Google Cloud Console 的 Batch 頁確認沒有殘留的工作，沒取消乾淨的虛擬機仍會計費"


def run_cancel(job, ctx, bundle):
    return _cancel_head(ctx, bundle, launch.GCB_RUNS, GCB_CANCEL_REMINDER)


def _cancel_head(ctx, bundle, runs_dir, reminder):
    """(state, result) of a confirmed cancel: ONE stop signal to the one process that is still the head process of this run.
    The Google Batch and the AWS Batch runs share it; they differ in the folder they live in and in the reminder."""
    run, number, folder = bundle["run_name"], bundle["slurm_job_id"], bundle["run_folder"]
    if bundle["agent"] != ctx.agent_name:
        raise rules.Refusal("這個取消是給另一個代理的 (for another agent)")
    if not isinstance(run, str) or not launch.RUN_NAME.match(run):
        raise rules.Refusal("run 名稱不對 (the run name is not one this platform makes)")
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 2 ** 31 - 1:
        raise rules.Refusal("主控程序編號必須是一個十進位數字 (the process number must be one decimal number)")
    storage = launch.own_facts(ctx).get("storage_root")
    if not storage:
        raise rules.Refusal("部署設定沒有 storage_root，無法找到專屬資料夾 (storage_root is not set)")
    if folder != "%s/%s/%s" % (storage, runs_dir, run):
        raise rules.Refusal("專屬資料夾不是這台主機上這個 run 的那一個（資料夾不符），不取消 (the run folder is not the one this host makes)")
    recorded = _read_small(os.path.join(folder, "head.pid"))
    if recorded is None or not re.match(rb"^[0-9]{1,10}\s*\Z", recorded) or int(recorded) != number:
        raise rules.Refusal("專屬資料夾裡的 head.pid 和要取消的編號 %d 不符（或讀不到），不取消 (head.pid does not hold this number)" % number)
    try:
        rc, out = host.run_fixed(["ps", "-o", "user=", "-o", "args=", "-p", str(number)], _plain_env(), 20)
    except TimeoutError:
        return "error", {"ok": False, "message": "查詢主控程序 %d 逾時，沒有取消任何東西，也不重試" % number}
    lines = [ln for ln in str(out).splitlines() if ln.strip()]
    if rc != 0 or not lines:
        raise rules.Refusal("主控程序 %d 已結束（查不到這個程序），不取消 (the process is gone)" % number)
    if len(lines) != 1:
        raise rules.Refusal("查詢主控程序 %d 回了 %d 行，不是剛好一個程序，不取消 (not exactly one process)" % (number, len(lines)))
    owner, _, args = lines[0].strip().partition(" ")
    if not _same_user(owner):
        raise rules.Refusal("程序 %d 不屬於執行這個代理的使用者（不是你的），不取消 (the process is not yours)" % number)
    if not re.search(r"(?:^|\s)-name\s+%s(?:\s|\Z)" % re.escape(run), args.strip()):
        raise rules.Refusal("程序 %d 的命令列沒有 -name %s（名稱不符），不取消 (the name does not match)" % (number, run))
    where = _proc_cwd(number)
    if where is None or os.path.realpath(where) != os.path.realpath(folder):
        raise rules.Refusal("程序 %d 的工作資料夾不是 %s（資料夾不符），不取消 (the working folder does not match)" % (number, folder))
    try:
        os.kill(number, signal.SIGTERM)
    except OSError as e:
        return "error", {"ok": False, "message": "送不出取消的訊號（%s），不重試" % e.__class__.__name__}
    return "done", {"ok": True, "slurm_job_id": number, "run_name": run,
                    "message": reminder % number}
