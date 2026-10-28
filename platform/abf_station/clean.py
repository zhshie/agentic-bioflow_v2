# Nothing existing: what must go is one directory at one fixed place, and this agent must check every path itself after the owner confirmed; the Nextflow clean command starts Nextflow and trusts its cache, rclone purge checks no path, gcloud storage rm deletes whatever its URL matches and checks no path or prefix (a prefix such as work also matches work2 unless the URL is listed and checked first), and Seqera Platform's delete belongs to its own cloud service, so none of them fit.
"""The clean_work job (features cloud-cleanup-c and cloud-cleanup-d): delete the `work` folder of one finished run, after the owner confirmed it.

Two kinds of run. Google Batch (d): see _clean_gcb; the same confirmation and bundle checks, the path worked out again from the
environment's workDir, the head process of the run must be gone, the key file and the read-only preflight must pass, then the
prefix <workDir>/runs/<run>/work/ is LISTED (read-only) and every line must lie under it, and only then ONE
`gcloud storage rm --recursive <that one URL>` is run: no shell, no second try, no loop. Slurm (c), described next:

Order, each step stops at the first failure and nothing is retried: the confirmation and its hash (launch.verify_confirmation),
the shape of the bundle, the path worked out again by this agent and compared character by character with the bundle, the
site user, the time left, and then ONE command for the site. That command is a fixed template; only the folder, the user and
the work path are put into it (quoted). It checks the real place of the folder, that no link is in the way, that this user has
no job still running in the folder, that work belongs to this user and that no link in results points into work, and only
then removes the folder that is literally named work, relative to the folder it just entered.

This is the one file of the package that holds the removing words. The agent answers in its own short sentences and never
passes on what the site printed.
"""
import os
import re

from . import cancel, gcb_launch, gcb_preflight, launch, rules
from . import site as host
from .site import quote

KEYS = {"version", "run_name", "slurm_job_id", "run_folder", "agent", "ce", "work"}
ATTEMPT = re.compile(r"-a([0-9]{1,4})\Z")
BARRED = ("rawdata", "results", "analysis", "..", ".")
USER = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}\Z")
TAIL = "可能只刪了一部分；work_cleaned_at 沒記，可以再申請，也不會自動重試"

# the lines of the one command; F = the run folder, U = the site user, W = F + the word work (all three quoted when put in)
TEMPLATE = (
    "cd -- {F} || exit 11",
    'test "$(realpath -- .)" = {F} || exit 12',
    "q=$(squeue -h -u {U} -o %Z 2>&1) || exit 18",
    "printf '%s\\n' \"$q\" | grep -qxF -- {F} && exit 13",
    "test -d work || exit 20",
    "test ! -L work || exit 14",
    'test "$(realpath -- work)" = {W} || exit 15',
    'test "$(stat -c %U work)" = {U} || exit 16',
    "if [ -d results ]; then l=$(find results -type l -lname '*/work/*' -print) || exit 17; [ -n \"$l\" ] && exit 17; fi",
    "rm -rf --one-file-system -- work",
)

# exit code -> what did not match (a refusal: nothing was changed)
REFUSED = {
    11: "進不了 run 資料夾",
    12: "run 資料夾本身或它的上層是捷徑（真實位置和預期不同）",
    13: "你在這個資料夾裡還有 Slurm 工作沒結束",
    14: "work 本身是捷徑，不是真的資料夾",
    15: "work 的真實位置不是預期的那一個",
    16: "work 的擁有者不是部署設定裡的 site_user（不是你的）",
    17: "results 裡有指向 work 的捷徑，刪了會讓結果壞掉",
    18: "問不到 Slurm 佇列，無法確認工作已結束",
}


def expected_work(folder):
    """The only path this agent will remove: the run folder and the word work."""
    return folder + "/work"


def _attempt_of(leaf, run):
    """True when `run` is the name of a resume attempt (-a2 or more) of the run whose folder is named `leaf`; same cut as the platform makes."""
    m = ATTEMPT.search(run)
    if not m or m.group(1) != str(int(m.group(1))) or int(m.group(1)) < 2:
        return False
    sfx = m.group(0)
    return run == leaf[:64 - len(sfx)] + sfx


def command(folder, user):
    """The one command for the site."""
    return "\n".join(TEMPLATE).format(F=quote(folder), U=quote(user), W=quote(expected_work(folder)))


def _check_path(bundle, env):
    run, folder = bundle["run_name"], bundle["run_folder"]
    if not isinstance(run, str) or not launch.RUN_NAME.match(run):
        raise rules.Refusal("run 名稱不對 (the run name is not one this platform makes)")
    if isinstance(bundle["slurm_job_id"], bool) or not isinstance(bundle["slurm_job_id"], int) or not 1 <= bundle["slurm_job_id"] <= 2 ** 31 - 1:
        raise rules.Refusal("Slurm 工作編號必須是一個十進位數字 (the job number must be one decimal number)")
    bad = "路徑不是這個平台給這個 run 的，沒有動任何東西 (the path is not the one this platform gives this run)"
    if rules.path_problem(folder) is not None or rules.normalize(folder) != folder:
        raise rules.Refusal(bad)
    if bundle["ce"].get("workDir") != env["workDir"] or os.path.dirname(folder) != env["workDir"] + "/runs":
        raise rules.Refusal(bad)
    leaf = os.path.basename(folder)
    if not launch.RUN_NAME.match(leaf) or not (run == leaf or _attempt_of(leaf, run)):
        raise rules.Refusal("run 名稱和資料夾對不上 (the run name does not belong to this folder)")
    work = bundle["work"]
    if not isinstance(work, str) or work != expected_work(folder):
        raise rules.Refusal(bad)
    parts = work.split("/")
    if any(p in BARRED for p in parts) or parts[-1] != "work":
        raise rules.Refusal("路徑含 rawdata、results、analysis 或 ..，或最後一段不是 work，一律不刪 (never rawdata, results or analysis)")
    return run, folder


def run_clean(job, ctx):
    bundle = launch.verify_confirmation(job, ctx, "clean_work")
    if set(bundle) != KEYS:
        raise rules.Refusal("清理的內容包欄位不對 (the clean bundle has other fields than it should)")
    if bundle["agent"] != ctx.agent_name:
        raise rules.Refusal("這個清理是給另一個代理的 (for another agent)")
    ce = bundle["ce"]
    if isinstance(ce, dict) and ce.get("platform") == launch.GCB:
        return _clean_gcb(job, ctx, bundle)
    if isinstance(ce, dict) and ce.get("platform") == launch.AWS:
        raise rules.Refusal("AWS Batch 的清理尚未支援，之後會在 aws-clean 做；現在不會刪任何東西 (cleaning an AWS Batch run is not built yet; nothing is deleted)")
    env = rules.clean_environment(ce)
    run, folder = _check_path(bundle, env)
    return _clean_slurm(job, ctx, run, folder)


def _clean_slurm(job, ctx, run, folder):
    user = cancel.site_user(ctx.settings_file)
    if not user or not USER.match(user):
        raise rules.Refusal("部署設定沒有 site_user，無法核對 work 的擁有者 (site_user is not set)")
    left = launch._left(ctx, job)
    if left < launch._min_remaining():
        raise rules.Refusal("這個工作剩下的時間不夠，沒有動任何東西 (not enough time left)")
    timeout = max(1, int(min(300, left - 15)))
    res = ctx.site.call([command(folder, user)], timeout=timeout)
    if res.timed_out:
        return "error", {"ok": False, "message": "逾時，%s" % TAIL}
    if res.rc == 0:
        return "done", {"ok": True, "cleaned": True, "run_name": run, "message": "已刪除 %s/work；results 沒有動" % folder}
    if res.rc == 20:
        return "done", {"ok": True, "cleaned": True, "run_name": run, "message": "%s/work 本來就不存在，沒有刪任何東西" % folder}
    if res.rc in REFUSED:
        raise rules.Refusal("%s，沒有改動任何東西 (nothing was changed)" % REFUSED[res.rc])
    return "error", {"ok": False, "message": "清理沒有成功（結束碼 %d），%s" % (res.rc, TAIL)}


# ---- Google Batch (cloud-cleanup-d) ---------------------------------------------------------------------------------------------

NOTHING_MATCHED = re.compile(r"matched no objects|no urls matched", re.I)
SHOWN = 300


def _gcloud_env(key_path):
    """The environment of the listing and the removal: the plain one, the key file named here only, and no prompts."""
    env = dict(gcb_launch._plain_env())
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)  # that one is for libraries; gcloud reads the next
    env["CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE"] = str(key_path)
    env["CLOUDSDK_CORE_DISABLE_PROMPTS"] = "1"
    return env


def _said(text, key_path):
    """What gcloud printed, shortened, with the key file's path and anything shaped like a credential hidden."""
    return gcb_preflight._scrub(str(text).replace(str(key_path), gcb_launch.KEY_SHOWN))[:SHOWN].strip()


def _gcb_work(bundle, run, ce_out, bucket):
    """The only prefix this agent will clear: workDir + /runs/<run>/work, worked out here and equal to the bundle's, character by character."""
    expected = "%s/runs/%s/work" % (ce_out["workDir"], run)
    bad = "路徑不是這個平台給這個 run 的，沒有動任何東西 (the path is not the one this platform gives this run)"
    if not isinstance(bundle["work"], str) or bundle["work"] != expected:
        raise rules.Refusal(bad)
    parts = expected[len("gs://"):].split("/")
    if parts[0] != bucket or any(p == "" or p in BARRED for p in parts) or parts[-1] != "work":
        raise rules.Refusal("路徑含 rawdata、results、analysis、空段或 ..，或最後一段不是 work，一律不刪 (never rawdata, results or analysis)")
    return expected


def _head_gone(folder, run, number):
    """None when the head process of this run is not running; a result tuple when the question timed out; a Refusal when it is
    still running or cannot be told."""
    recorded = gcb_launch._read_small(os.path.join(folder, "head.pid"))
    if recorded is None or not re.match(rb"^[0-9]{1,10}\s*\Z", recorded):
        raise rules.Refusal("找不到 head.pid，無法確認主控程序已結束，保守起見不刪 (head.pid is missing or not a number)")
    if int(recorded) != number:
        raise rules.Refusal("head.pid 記的編號和內容包的不同，無法確認主控程序已結束，不刪 (head.pid holds another number)")
    try:
        rc, out = host.run_fixed(["ps", "-o", "user=", "-o", "args=", "-p", str(number)], gcb_launch._plain_env(), 20)
    except TimeoutError:
        return "error", {"ok": False, "message": "查詢逾時，沒有刪任何東西，也不重試"}
    lines = [ln for ln in str(out).splitlines() if ln.strip()]
    if rc != 0 or not lines:
        return None
    if len(lines) != 1:
        raise rules.Refusal("無法確認主控程序已結束（ps 回了不只一行），保守起見不刪 (not exactly one process)")
    if re.search(r"(?:^|\s)-name\s+%s(?:\s|\Z)" % re.escape(run), lines[0].strip()):
        raise rules.Refusal("這個 run 的主控程序還在跑，先等它結束或取消它，再申請清理；沒有刪任何東西 (the head process is still running)")
    return None         # a number that another program has taken over since


def _clean_gcb(job, ctx, bundle):
    run = bundle["run_name"]
    if bundle["agent"] != ctx.agent_name:
        raise rules.Refusal("這個清理是給另一個代理的 (for another agent)")
    if not isinstance(run, str) or not launch.RUN_NAME.match(run):
        raise rules.Refusal("run 名稱不對 (the run name is not one this platform makes)")
    number = bundle["slurm_job_id"]
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 2 ** 31 - 1:
        raise rules.Refusal("主控程序編號必須是一個十進位數字 (the process number must be one decimal number)")
    storage = launch.own_facts(ctx).get("storage_root")
    if not storage:
        raise rules.Refusal("部署設定沒有 storage_root，無法找到這個 run 的專屬資料夾 (storage_root is not set)")
    folder = bundle["run_folder"]
    if folder != "%s/%s/%s" % (storage, launch.GCB_RUNS, run):
        raise rules.Refusal("專屬資料夾不是這台主機上這個 run 的那一個，沒有動任何東西 (the run folder is not the one this host makes)")
    try:
        ce_out, bucket, _ = launch._check_gcb_ce(bundle["ce"])
    except launch.BundleError as e:
        raise rules.Refusal("環境設定不合規則，沒有動任何東西：%s" % e)
    expected = _gcb_work(bundle, run, ce_out, bucket)
    waiting = _head_gone(folder, run, number)
    if waiting is not None:
        return waiting
    key_path = gcb_preflight.credentials_path(ctx.settings_file)
    gcb_launch._check_environment(bundle["ce"], key_path)
    env, url, project = _gcloud_env(key_path), expected + "/", ce_out["project"]

    try:
        rc, out = host.run_fixed(["gcloud", "storage", "ls", "--recursive", "--project", project, url], env, 120)
    except TimeoutError:
        return "refused", {"ok": False, "cleaned": False, "message": "列出雲端暫存檔逾時，沒有刪任何東西；稍後可以再申請"}
    gone = {"ok": True, "cleaned": True, "run_name": run, "message": "%s 底下已經沒有東西，沒有刪任何東西；results 沒有動" % expected}
    if rc != 0:
        if NOTHING_MATCHED.search(str(out)):
            return "done", gone
        return "error", {"ok": False, "message": "列出雲端暫存檔失敗，沒有刪任何東西，可以再申請（%s）" % _said(out, key_path)}
    objects = 0
    for line in (ln.strip() for ln in str(out).splitlines() if ln.strip()):
        heading = line.endswith(":")
        if not (line[:-1] if heading else line).startswith(url):
            raise rules.Refusal("列出的物件不全在 work 底下（前綴撞名），不刪 (the listing holds objects outside work)")
        objects += 0 if heading else 1
    if objects == 0:
        return "done", gone

    try:
        rc, out = host.run_fixed(["gcloud", "storage", "rm", "--recursive", "--project", project, url], env, 300)
    except TimeoutError:
        return "error", {"ok": False, "message": "刪除逾時，%s" % TAIL}
    if rc != 0:
        return "error", {"ok": False, "message": "刪除沒有成功（結束碼 %s：%s），%s" % (rc, _said(out, key_path), TAIL)}
    return "done", {"ok": True, "cleaned": True, "run_name": run, "message": "已刪除 bucket 裡 %s 底下的物件；results 沒有動" % expected}
