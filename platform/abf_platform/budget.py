# Nothing like it existed: the platform asked a person for every send; this is the one place that decides whether the person's own earlier SU budget already says yes.
"""BUDGET (constitution 8.0.0): the yes a person gave in advance by setting two SU limits on their own settings page.

`decide` is a pure function of facts that were already looked up; `check` looks them up and fails closed: anything that is missing,
cannot be worked out or raises is "ask the person", never a yes. Only the action layer's `_ask` and `_request_attempt` call `check`,
and only a True answer lets them record the yes as BUDGET. Cloud sends, forget and clean_work never come here."""
import os
import time

from . import compute_envs, store, su

SU_KINDS = ("launch", "cancel")


def is_hosted():
    """A hosted deployment (ABF_HOSTED set) never takes a BUDGET yes."""
    return bool(os.environ.get("ABF_HOSTED"))


def limits(tokens_path, user_id):
    """(single, month): the two SU limits of this user, None for one that is not set."""
    b = store.user_budget(tokens_path, user_id)
    return b["single"], b["month"]


def _n(x):
    return ("%.4f" % x).rstrip("0").rstrip(".")


def decide(*, user_present, hosted, single, month, kind, slurm, site_known, estimate, used):
    """(True, note) when the budget says yes, else (False, reason). `kind` is 'send' (launch, resume, relaunch) or 'cancel'. A cancel needs
    only a person, a non-hosted deployment, both limits above 0 and a Slurm environment; a send also needs a known SU site, an estimate
    not above the single limit, and the month's use plus the estimate not above the monthly limit. None for estimate or used is
    unknown, which is never a yes. A limit of 0 allows nothing."""
    if not user_present:
        return False, "沒有登入的使用者 (no signed-in user)"
    if hosted:
        return False, "這個部署不啟用預算內免確認 (this deployment does not take a budget yes)"
    if single is None or month is None:
        return False, "你還沒有把單次與每月 SU 上限都設好 (the two SU limits are not both set)"
    if not (single > 0 and month > 0):
        return False, "SU 上限是 0，什麼都不自動送出 (a limit of 0 allows nothing)"
    if not slurm:
        return False, "這個環境不是國網 Slurm 站台 (not a Slurm site)"
    if kind == "cancel":
        return True, "cancel; single limit %s, monthly limit %s" % (_n(single), _n(month))
    if not site_known:
        return False, "這個站台沒有 SU 費率 (no SU rates for this site)"
    if estimate is None:
        return False, "這個 pipeline 在這個站台還沒有成功的紀錄可以估 SU (no history to estimate from)"
    if used is None:
        return False, "本月已用的 SU 算不出來 (this month's SU cannot be worked out)"
    if estimate > single:
        return False, "預估 %s SU 超過你的單次上限 %s (the estimate is over the single limit)" % (_n(estimate), _n(single))
    if used + estimate > month:
        return False, "本月已用 %s 加預估 %s 超過每月上限 %s (over the monthly limit)" % (_n(used), _n(estimate), _n(month))
    return True, ("estimate %s SU, single limit %s, used this month %s, monthly limit %s" % (_n(estimate), _n(single), _n(used), _n(month)))


def _pipeline_of(bundle):
    if not isinstance(bundle, dict):
        return None
    p = bundle.get("pipeline")
    if not p:
        p = ((bundle.get("resume") or bundle.get("relaunch") or {}).get("origin") or {}).get("pipeline")
    return p if isinstance(p, str) else None


def check(platform_path, kind, ce_name, bundle, caller, clock=time.time, index_path=None, tokens_path=None, rates=None):
    """(True, note, facts) when this request is inside the caller's own budget, else (False, reason, None); never raises. `kind` is 'launch' or
    'cancel' (the kind of confirmation; resume and relaunch are launches). The note is what the confirmation keeps; facts is
    {estimate, single, used, month} for the sentence told to the AI (cancel: estimate and used are None)."""
    try:
        if caller is None or getattr(caller, "user_id", None) is None:
            return False, "no user", None
        index_path = index_path or store.default_index_path()
        tokens_path = tokens_path or store.default_tokens_path(index_path)
        single, month = limits(tokens_path, caller.user_id)
        if single is None or month is None or is_hosted():
            return False, "not set or hosted", None
        ce = compute_envs.get(platform_path, ce_name) if ce_name else None
        slurm = bool(ce) and ce["platform"] == compute_envs.SUPPORTED
        est = used = None
        site_known = False
        if slurm and kind != "cancel":
            rates = rates if rates is not None else su.load_rates()
            site = ce["config"].get("suSite") or (rates or {}).get("default_site")
            site_known = isinstance(rates, dict) and isinstance(site, str) and site in (rates.get("sites") or {})
            if site_known:
                est = su.estimate_launch(index_path, platform_path, caller.user_id, _pipeline_of(bundle), site, rates)["su"]
                used = su.month_used_at(index_path, platform_path, caller.user_id, site, rates, clock())
        ok, note = decide(user_present=True, hosted=False, single=single, month=month, kind="cancel" if kind == "cancel" else "send",
                          slurm=slurm, site_known=site_known, estimate=est, used=used)
        return (True, note, {"estimate": est, "single": single, "used": used, "month": month}) if ok else (False, note, None)
    except Exception:       # fail closed: whatever went wrong, the person is asked as before; nothing of it is said to anybody
        return False, "could not be worked out", None


def said(facts):
    """The plain sentence an AI is told when a send went through on the budget."""
    if facts["estimate"] is None:
        return "在你設定的 SU 額度內，已直接送出（取消）。你的單次上限 %s、每月上限 %s (inside your SU budget, done without asking)" % (
            _n(facts["single"]), _n(facts["month"]))
    return ("在你設定的 SU 額度內，已直接送出。預估 %s SU，你的單次上限 %s、本月已用 %s／上限 %s "
            "(inside your SU budget: estimate %s SU, single limit %s, used %s of %s this month)" % (
                _n(facts["estimate"]), _n(facts["single"]), _n(facts["used"]), _n(facts["month"]),
                _n(facts["estimate"]), _n(facts["single"]), _n(facts["used"]), _n(facts["month"])))
