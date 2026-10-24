# Not `scancel -u`, `scancel --name` or Seqera's cancel button: they stop whatever matches; this stops the one head job it was confirmed for, after checking its name, owner and folder, and asks the scheduler once.
"""The cancel_run job (feature 007b, FR-008).

Order: the confirmation and its hash (launch.verify_confirmation), the shape of the bundle, then ONE question to the
scheduler about that job number (`squeue -h -j <id> -o '%j|%u|%Z'`: name, owner, working folder), and only if the single
answer line is exactly this run's head job, ONE stop for that one number. Anything else is a refusal and nothing is
sent. There is no retry, no loop and no other stop anywhere.
"""
import re

from . import launch, rules
from .site import quote

KEYS = {"version", "run_name", "slurm_job_id", "run_folder", "agent", "ce"}


def site_user(settings_file):
    user = rules.read_setting(settings_file, "site_user")
    if not user:
        user = rules.read_setting(settings_file, "site_host").partition("@")[0] if "@" in rules.read_setting(settings_file, "site_host") else ""
    return user


def run_cancel(job, ctx):
    bundle = launch.verify_confirmation(job, ctx, "cancel")
    if set(bundle) != KEYS:
        raise rules.Refusal("取消的內容包欄位不對 (the cancel bundle has other fields than it should)")
    if isinstance(bundle.get("ce"), dict) and bundle["ce"].get("platform") == launch.GCB:
        from . import gcb_launch      # a Google Batch run is stopped by its own module; it imports launch.py, so it is read here
        return gcb_launch.run_cancel(job, ctx, bundle)
    env = rules.clean_environment(bundle["ce"])
    run, number, folder = bundle["run_name"], bundle["slurm_job_id"], bundle["run_folder"]
    if bundle["agent"] != ctx.agent_name:
        raise rules.Refusal("這個取消是給另一個代理的 (for another agent)")
    if not isinstance(run, str) or not launch.RUN_NAME.match(run) or folder != "%s/runs/%s" % (env["workDir"], run):
        raise rules.Refusal("run 名稱或專屬資料夾不對 (the run name or the run folder is not one this platform makes)")
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 2 ** 31 - 1:
        raise rules.Refusal("Slurm 工作編號必須是一個十進位數字 (the job number must be one decimal number)")
    user = site_user(ctx.settings_file)
    if not user or not re.match(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}\Z", user):
        raise rules.Refusal("部署設定沒有 site_user，無法核對工作的擁有者 (site_user is not set)")
    site = ctx.site
    res = site.call(["squeue -h -j %d -o %s" % (number, quote("%j|%u|%Z"))])
    if res.rc != 0:
        return "error", {"ok": False, "message": "查詢 Slurm 工作 %d 失敗（結束碼 %d），沒有取消任何東西，也不重試" % (number, res.rc)}
    lines = [ln for ln in res.out.decode("utf-8", errors="replace").splitlines() if ln.strip()]
    if not lines:
        raise rules.Refusal("Slurm 工作 %d 已不在佇列（已結束），不取消 (the job is not in the queue any more)" % number)
    if len(lines) != 1:
        raise rules.Refusal("查詢 Slurm 工作 %d 回了 %d 行，不是剛好一個工作，不取消 (not exactly one job)" % (number, len(lines)))
    parts = lines[0].split("|")
    if len(parts) != 3:
        raise rules.Refusal("看不懂 Slurm 的回答，不取消 (unreadable answer)")
    name, owner, where = parts
    if name != "nf-" + run:
        raise rules.Refusal("工作 %d 的名稱不是 nf-%s（名稱不符），不取消 (the job name does not match)" % (number, run))
    if owner != user:
        raise rules.Refusal("工作 %d 不屬於 %s（不是你的），不取消 (the job is not yours)" % (number, user))
    if where != folder:
        raise rules.Refusal("工作 %d 的工作目錄不是 %s（目錄不符），不取消 (the working folder does not match)" % (number, folder))
    res = site.call(["scancel %d" % number])
    if res.rc != 0:
        return "error", {"ok": False, "message": "scancel 沒有成功（結束碼 %d），不重試" % res.rc}
    return "done", {"ok": True, "slurm_job_id": number, "run_name": run, "message": "取消請求已送出（Slurm 工作 %d）" % number}
