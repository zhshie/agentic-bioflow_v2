# Not rsync or `scp -r`: they copy a folder, links and secrets included; this reads back only Nextflow's own logs and trace of one launch folder, never follows a link, never writes on the site.
"""The fetch_run_records job (feature 007b, FR-011): read-only.

It reads, in the run folder of a launch, `.nextflow.log*`, `.nextflow/history` and the trace file that a log names
("Workflow started -- trace file: ..."), which must be a plain file name inside that folder. A symbolic link is refused
(find -P says what each entry is, and a file is read only if it is still a regular file when it is read), each file is cut
at 20 MB and says so, and `tower.token`, `params.yaml` and every other file are never asked for. Nothing is written.
"""
import base64
import re

from . import launch, rules
from .site import quote

LIMIT = 20 * 1024 * 1024
_LOG = re.compile(r"^\.nextflow\.log(\.[0-9]{1,3})?\Z")
_TRACE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}\Z")
_NOT_RECORDS = {"tower.token", "params.yaml", "head.sh", "nextflow.config", "samplesheet.csv", "gcb.config", "aws.config", "az" "ure.config"}
_RESUME_FILE = re.compile(r"^(head|params|extra)-[0-9]+\.(sh|yaml|config)\Z")
ARGS = {"ce", "run_name", "run_folder"}


def _read(site, folder, rel):
    """(bytes, truncated) of one regular file, or (None, why)."""
    path = "%s/%s" % (folder, rel)
    res = site.call(["find -P %s -maxdepth 0 -type f -exec head -c %d {} \\;" % (quote(path), LIMIT + 1)], timeout=120)
    if res.rc != 0:
        return None, "讀不到 (exit %d)" % res.rc
    if not res.out and not _is_empty_file(site, path):
        return None, "不是一般檔案，已拒絕"
    return (res.out[:LIMIT], len(res.out) > LIMIT), None


def _is_empty_file(site, path):
    res = site.call(["find -P %s -maxdepth 0 -type f -empty -print" % quote(path)])
    return res.rc == 0 and bool(res.out.strip())


def run_fetch(job, ctx):
    args = job["args"]
    env = rules.clean_environment(args.get("ce"))
    run, folder = args.get("run_name"), args.get("run_folder")
    if not isinstance(run, str) or not launch.RUN_NAME.match(run) or not launch.run_folder_ok(env["workDir"], run, folder):
        raise rules.Refusal("run 名稱或專屬資料夾不對：只讀平台自己送出的專屬資料夾 (not a folder this platform made)")
    site = ctx.site
    listing = site.call(["cd %s && find -P . -maxdepth 2 \\( -name '.nextflow.log*' -o -path ./.nextflow/history \\) "
                         "-printf %s" % (quote(folder), quote("%y\\t%p\\0"))])
    if listing.rc != 0:
        return "error", {"ok": False, "message": "讀不到專屬資料夾 %s（結束碼 %d）" % (folder, listing.rc)}
    files, refused, logs = [], [], []
    wanted = []
    for rec in listing.out.split(b"\0"):
        if not rec:
            continue
        kind, _, rel = rec.decode("utf-8", errors="replace").partition("\t")
        rel = rel[2:] if rel.startswith("./") else rel
        if not (_LOG.match(rel) or rel == ".nextflow/history"):
            continue
        if kind == "l":
            refused.append("符號連結已拒絕：%s" % rel)
        elif kind == "f":
            wanted.append(rel)
    for rel in sorted(wanted):
        got, why = _read(site, folder, rel)
        if got is None:
            refused.append("%s：%s" % (rel, why))
            continue
        data, cut = got
        files.append({"name": rel, "data": base64.b64encode(data).decode("ascii"), "truncated": cut})
        if rel.startswith(".nextflow.log"):
            logs.append(data.decode("utf-8", errors="replace"))
    traces = []
    for text in logs:
        for m in re.finditer(r"Workflow started -- trace file: (.+)", text):
            name = m.group(1).strip()
            if name.startswith(folder + "/"):
                name = name[len(folder) + 1:]
            if name not in traces:
                traces.append(name)
    for name in traces:
        if not _TRACE.match(name) or name in _NOT_RECORDS or _RESUME_FILE.match(name) or name.startswith((".nextflow", "slurm-")):
            refused.append("trace 檔 %r 不在專屬資料夾內或名稱不合，已拒絕" % name[:80])
            continue
        got, why = _read(site, folder, name)
        if got is None:
            refused.append("%s：%s" % (name, why))
            continue
        data, cut = got
        files.append({"name": name, "data": base64.b64encode(data).decode("ascii"), "truncated": cut})
    note = "；".join(f["name"] + "（已截斷）" for f in files if f["truncated"])
    return "done", {"ok": True, "files": files, "refused": refused,
                    "message": "讀回 %d 個檔%s" % (len(files), "；" + note if note else "")}
