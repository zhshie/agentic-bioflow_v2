# Nothing existing: searched Nextflow's official Kubernetes page (its old run subcommand is obsolete), Seqera's command-line launcher and nf-core's launcher; none is a local agent that, after a person's yes, creates the head Pod in the cluster and can stop that one Pod after a second yes, so this drives the kubectl CLI with fixed argument lists.
"""Launching and cancelling a run on a Kubernetes compute environment (k8s-launch).

After the person's yes the agent, on the platform host, makes ONE Secret (the files of the bundle and the run token) and ONE Pod (the
head process, which runs the Nextflow of the bundle inside the cluster) with kubectl with create and `-f -`: the manifests travel through
stdin, are never written to a file and never put on a command line. Reads are `kubectl get`; the one other write is the delete of the
Secret this launch made when the Pod could not be made, and (in the cancel) the delete of that one Pod. The kubeconfig stays on this
side: its path reaches kubectl only through the environment of each call (see k8s_preflight). Nothing here starts a program of its
own, and the text of the Nextflow command lives only in launch.py.
"""
import base64
import json
import os
import re
import shutil
import tempfile
import threading

from . import gcb_launch, k8s_preflight, launch, rules
from . import site
from .gcb_preflight import _scrub

IMAGE_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,299}\Z")
IMAGE_SETTING = "k8s_head_image"
PLACEHOLDER_ID = 1                     # the result's slurm_job_id: a Pod has no Slurm number, the field only has to be a positive whole number
TAIL_LINES = 50
MESSAGE_LIMIT = 200
CANCEL_REMINDER = "本系統只刪主控 Pod，不刪 task Pod：請到叢集確認這次 run 的 task Pod 是否也清掉了，沒清乾淨的要自己處理；費用從啟動算到它們真的停止為止"
UNREACHABLE = "連不上叢集（%s）：沒有建立也沒有刪除任何東西，也不重試。請確認網路與 kubeconfig 後再試 (could not reach the cluster)"


def _text(value, token=None):
    """Text that may be shown: scrubbed, the run token replaced, cut."""
    out = _scrub(value or "")
    if token:
        out = out.replace(token, "[token]")
    return out.strip()[:MESSAGE_LIMIT]


def _kubectl(cred_path, argv, stdin=None):
    """(return code, output) of one kubectl call, each with an empty cache folder of its own that is deleted afterwards. A call that does
    not return in time is reported as a failure, not raised."""
    folder = tempfile.mkdtemp(prefix="abf-kube-")
    try:
        env = k8s_preflight._kube_env(cred_path, folder)
        if stdin is None:
            return site.run_fixed(argv, env, k8s_preflight.TIMEOUT_SECONDS)
        return site.run_fixed(argv, env, k8s_preflight.TIMEOUT_SECONDS, stdin)
    except TimeoutError:
        return 124, "Unable to connect: timed out"
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def _is_missing(out):
    return "NotFound" in out or "not found" in out


def _where(ce):
    return ["--namespace", ce["namespace"], "--context", ce["context"]]


def _check_tools(cred_path):
    """Refuses, in plain words, when the kubeconfig is not a usable file or kubectl is not installed. Before any call."""
    try:
        st = os.stat(str(cred_path))
    except OSError:
        raise rules.Refusal("找不到 kubeconfig（憑證檔）：%s。請放在那裡並設成只有自己能讀 (no kubeconfig at that place)" % cred_path)
    import stat as stat_mod
    import sys
    if not stat_mod.S_ISREG(st.st_mode):
        raise rules.Refusal("kubeconfig 不是一般檔案：%s (the kubeconfig is not a regular file)" % cred_path)
    if sys.platform != "win32" and st.st_mode & 0o077:
        raise rules.Refusal("kubeconfig 的權限太寬：群組或其他人能讀寫。請執行 chmod 600 %s (the kubeconfig's permissions are too open)" % cred_path)
    if not shutil.which("kubectl"):
        raise rules.Refusal("這台主機沒有 kubectl：送出與取消都靠它，請先安裝 (kubectl is not installed on this computer)")


def _head_image(ctx):
    image = rules.read_setting(ctx.settings_file, IMAGE_SETTING)
    if not image:
        raise rules.Refusal("部署設定檔沒有 %s：主控 Pod 要用哪個映像檔（image）由你指定，請在 config/env.yaml 設 %s: <映像檔>，"
                            "映像檔要含 Nextflow (the settings have no %s)" % (IMAGE_SETTING, IMAGE_SETTING, IMAGE_SETTING))
    if not IMAGE_OK.match(image):
        raise rules.Refusal("設定檔的 %s 不是合法的映像檔名稱 (not a valid image name)" % IMAGE_SETTING)
    return image


def secret_manifest(bundle, token):
    files = dict(bundle["files"])
    files["tower.token"] = token
    return {"apiVersion": "v1", "kind": "Secret",
            "metadata": {"name": launch.k8s_secret_name(bundle["run_name"]), "namespace": bundle["ce"]["namespace"]},
            "type": "Opaque",
            "data": {name: base64.b64encode(files[name].encode("utf-8")).decode("ascii") for name in launch.K8S_SECRET_KEYS}}


def pod_manifest(bundle, image):
    ce = bundle["ce"]
    spec = {"restartPolicy": "Never",
            "volumes": [{"name": "work", "persistentVolumeClaim": {"claimName": ce["storageClaimName"]}},
                        {"name": "bundle", "secret": {"secretName": launch.k8s_secret_name(bundle["run_name"])}}],
            "containers": [{"name": "head", "image": image, "command": ["sh", "-c", launch.k8s_pod_command(bundle)],
                            "volumeMounts": [{"name": "work", "mountPath": ce["storageMountPath"]},
                                             {"name": "bundle", "mountPath": launch.K8S_BUNDLE_MOUNT, "readOnly": True}]}]}
    if ce.get("serviceAccount"):
        spec["serviceAccountName"] = ce["serviceAccount"]
    return {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": bundle["pod_name"], "namespace": ce["namespace"]}, "spec": spec}


def _create(cred_path, ce, manifest):
    return _kubectl(cred_path, ["kubectl", "create", "-f", "-"] + _where(ce), json.dumps(manifest))


def _exists(cred_path, ce, kind, name):
    """True / False when the cluster answered; raises Refusal-free ValueError text when it did not."""
    rc, out = _kubectl(cred_path, ["kubectl", "get", kind, name] + _where(ce) + [k8s_preflight.REQUEST_TIMEOUT])
    if rc == 0:
        return True
    if _is_missing(out):
        return False
    raise ConnectionError(_text(out))


def run_launch(job, ctx, bundle):
    """(state, result) of a confirmed launch on Kubernetes. The confirmation was verified by the caller."""
    if bundle.get("agent") != ctx.agent_name:
        raise rules.Refusal("這個內容包是給另一個代理的 (the bundle is for another agent)")
    token = job.get("run_token")
    if not isinstance(token, str) or not token or len(token) > 200:
        raise rules.Refusal("平台沒有給這次執行的 token (no run token was sent)")
    try:
        rebuilt = launch.render_k8s_bundle(ce=bundle["ce"], agent=bundle["agent"], facts=launch.own_facts(ctx), roots=[],
                                           run_name=bundle["run_name"], pipeline=bundle["pipeline"], revision=bundle["revision"],
                                           samplesheet=bundle["samplesheet"], params=bundle["params"], path_columns=bundle["path_columns"])
    except (launch.BundleError, KeyError, TypeError) as e:
        raise rules.Refusal("內容不合規則：%s" % e)
    if rebuilt != {k: v for k, v in bundle.items() if k not in launch.RECORDS}:
        raise rules.Refusal("內容與代理依自己的設定重新產生的不一致：不送出 (the bundle is not what this agent builds from its own settings)")
    if "upload_paths" in bundle:
        raise rules.Refusal("Kubernetes 還不能上傳檔案：檔案要先放進 PVC，不送出 (uploads are not supported for Kubernetes yet)")
    if launch._left(ctx, job) < launch._min_remaining():
        raise rules.Refusal("工作期限剩下的時間不足以安全送出 (too little of the deadline is left to start safely)")
    cred_path = k8s_preflight.credentials_path(ctx.settings_file)
    _check_tools(cred_path)
    image = _head_image(ctx)

    ce = bundle["ce"]
    env = k8s_preflight.clean_environment(dict(ce, credentialsId="launch-check"))
    result = k8s_preflight.run_preflight(env, cred_path=cred_path)
    bad = [c for c in result["checks"] if c["status"] != "pass" and c["name"] != "credential_name"]
    if bad:
        raise rules.Refusal("叢集的預檢沒過，沒有建立任何東西：%s (the cluster check did not pass)"
                            % "；".join("%s：%s" % (c["name"], _text(c["detail"], token)) for c in bad[:3]))

    pod, secret = bundle["pod_name"], launch.k8s_secret_name(bundle["run_name"])
    try:
        if _exists(cred_path, ce, "pod", pod):
            raise rules.Refusal("叢集的命名空間 %s 裡已經有名為 %s 的 Pod，不覆蓋；請換一個 run 名稱，或先確認並手動處理那個 Pod "
                                "(a Pod of that name exists already)" % (ce["namespace"], pod))
        if _exists(cred_path, ce, "secret", secret):
            raise rules.Refusal("叢集裡已經有名為 %s 的 Secret，不覆蓋；請換一個 run 名稱，或用 k8s-clean／手動刪掉它再試 "
                                "(a Secret of that name exists already)" % secret)
    except ConnectionError as e:
        return "error", {"ok": False, "message": UNREACHABLE % e}

    rc, out = _create(cred_path, ce, secret_manifest(bundle, token))
    if rc != 0:
        return "error", {"ok": False, "message": "建不起 Secret %s，沒有建立 Pod：%s" % (secret, _text(out, token) or "沒有訊息")}
    rc, out = _create(cred_path, ce, pod_manifest(bundle, image))
    if rc != 0:
        why = _text(out, token) or "沒有訊息"
        drc, _dout = _kubectl(cred_path, ["kubectl", "delete", "secret", secret] + _where(ce))
        left = "已刪除這次建立的 Secret %s" % secret if drc == 0 else "Secret %s 沒刪成功，請手動刪掉它（不會重試）" % secret
        return "error", {"ok": False, "message": "建不起 Pod %s：%s。%s" % (pod, why, left)}

    threading.Event().wait(gcb_launch._settle_seconds())          # a head Pod that fails at once is seen below
    rc, out = _kubectl(cred_path, ["kubectl", "get", "pod", pod, "-o", "jsonpath={.status.phase}"] + _where(ce) + [k8s_preflight.REQUEST_TIMEOUT])
    left = "Pod %s 與 Secret %s 已建立（沒有刪除）" % (pod, secret)
    if rc != 0:
        return "error", {"ok": False, "message": "無法取得 Pod 狀態（%s）。%s，請到叢集確認" % (_text(out, token), left), "left_on_site": left}
    if out.strip() == "Failed":
        lrc, tail = _kubectl(cred_path, ["kubectl", "logs", pod, "--tail=%d" % TAIL_LINES] + _where(ce))
        return "error", {"ok": False, "message": "主控 Pod 一啟動就失敗了：%s。%s" % (_text(tail, token) or "沒有輸出", left), "left_on_site": left}
    return "done", {"ok": True, "slurm_job_id": PLACEHOLDER_ID, "run_name": bundle["run_name"], "run_folder": bundle["run_folder"],
                    "pod_name": pod,
                    "message": "已啟動：Pod %s（命名空間 %s）；叢集的運算費用從現在開始計" % (pod, ce["namespace"])}


def run_cancel(job, ctx, bundle):
    """(state, result) of a confirmed cancel of a Kubernetes run: look at the head Pod, then ONE delete of that one Pod."""
    if bundle.get("agent") != ctx.agent_name:
        raise rules.Refusal("這個取消是給另一個代理的 (for another agent)")
    env = k8s_preflight.clean_environment(dict(bundle["ce"], credentialsId="launch-check"))
    run, pod = bundle.get("run_name"), bundle.get("pod_name")
    if not isinstance(run, str) or not launch.RUN_NAME.match(run):
        raise rules.Refusal("run 名稱不對 (the run name is not one this platform makes)")
    if pod != launch.k8s_pod_name(run):
        raise rules.Refusal("Pod 名稱不是這個 run 的主控 Pod，不取消 (the Pod name is not this run's head Pod)")
    if bundle.get("run_folder") != "%s/%s/%s" % (env["storageMountPath"].rstrip("/"), launch.K8S_RUNS, run):
        raise rules.Refusal("run 的專屬資料夾不對，不取消 (the run folder is not the one this platform makes)")
    cred_path = k8s_preflight.credentials_path(ctx.settings_file)
    _check_tools(cred_path)
    ce = {"namespace": env["namespace"], "context": env["context"]}
    try:
        present = _exists(cred_path, ce, "pod", pod)
    except ConnectionError as e:
        return "error", {"ok": False, "message": UNREACHABLE % e}
    if not present:
        return "done", {"ok": True, "slurm_job_id": bundle.get("slurm_job_id"), "run_name": run,
                        "message": "Pod 已不存在，視為已停止（%s）。%s" % (pod, CANCEL_REMINDER)}
    rc, out = _kubectl(cred_path, ["kubectl", "delete", "pod", pod, "--namespace", ce["namespace"], "--context", ce["context"], "--wait=false"])
    if rc != 0:
        return "error", {"ok": False, "message": "刪除 Pod %s 沒有成功：%s。不重試 (the delete did not work, not retried)" % (pod, _text(out) or "沒有訊息")}
    return "done", {"ok": True, "slurm_job_id": bundle.get("slurm_job_id"), "run_name": run,
                    "message": "已要求刪除主控 Pod %s（命名空間 %s）。%s" % (pod, ce["namespace"], CANCEL_REMINDER)}
