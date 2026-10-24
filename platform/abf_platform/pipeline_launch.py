# Nothing existing: nf-core/tools and Seqera Platform start a pipeline on a machine that runs programs; this only makes the text of a project and the choices for a person's yes, and starts nothing.
"""Sending a saved, checked graph to the confirmation page (spec 017d).

`build_project` is a pure function: from a canonical graph, a pipeline name and version, the header of the samplesheet and the module
files it is given (the committed ones, see `module_sources`) it makes the files of the project that is written into the run's own
`pipeline/` folder: `main.nf` (every input the graph left open is joined to the samplesheet), `nextflow.config` (with the platform's
own publish block), `modules.json` and the files of the modules the graph uses. It reads no database, opens no connection and writes
nothing. Nothing a person typed is ever put into the Groovy: it is made of a closed set of forms and column names that are checked.

`prepare` is the part before the question: whose it is, the check of today, the project, and then the same `build.prepare_launch`
every launch uses, so the screen, the hash and the question are those of any launch. Nothing is shown, asked or written here.
"""
import hashlib
import re

from abf_launch import build

from . import catalogue, common, compose, module_sources
from . import validate as checks

MAX_BYTES = 2 * 1024 * 1024
MAX_FILES = 2000
MAX_SHOWN = 5
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\Z")
_NESTED = re.compile(r"^[ \t]*(include[ \t]*\{|workflow\b(?!\.))", re.M)
_ADDED = "// added by the platform at launch"
PUBLISH = (_ADDED + ": every process copies its outputs to <outdir>/<process name in small letters>\n"
           "process.publishDir = [\n"
           "    path: { \"${params.outdir}/${task.process.tokenize(':')[-1].toLowerCase()}\" },\n"
           "    mode: 'copy'\n"
           "]\n")
_FORMS = {"file": "file(row.%s, checkIfExists: true)", "directory": "file(row.%s, checkIfExists: true)", "string": "row.%s",
          "integer": "(row.%s as Integer)", "float": "(row.%s as Double)", "boolean": "row.%s.toBoolean()"}
_PATHS = ("file", "directory")
UNSUPPORTED = "UNSUPPORTED_MODULE"


class ProjectError(Exception):
    """The graph cannot be made into a project; the text says what and what to do, in Chinese and in English. `code` names the kind
    when there is one (UNSUPPORTED_MODULE)."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


def _lines_of(main_nf, line):
    return [i for i, ln in enumerate(main_nf) if ln == line]


def build_project(canonical, name, version, header, *, data=None, sources=None):
    """{"project": {path: text}, "project_sha256", "path_columns", "columns"}. `header` is the first row of the samplesheet. Raises ProjectError."""
    data = catalogue.load() if data is None else data
    try:
        rendered = compose.render(canonical, name, version, data)
    except ValueError:
        raise ProjectError("這個版本的圖現在轉不出專案檔；請到組合頁存一個修正後的新版本 "
                           "(this version of the graph can no longer be turned into a project; save a corrected version)")
    files = dict(rendered["files"])
    nodes = {n["id"]: n for n in canonical["nodes"]}
    paths = sorted({catalogue.describe(n["module"], data)["path"] for n in canonical["nodes"]})
    try:
        have = module_sources.files_for(paths, module_sources.load() if sources is None else sources)
    except ValueError as e:
        raise ProjectError("%s [%s]" % (e, UNSUPPORTED), code=UNSUPPORTED)
    for path in paths:
        if _NESTED.search(have.get("modules/nf-core/%s/main.nf" % path, "")):
            raise ProjectError("模組 %s 含有 include 或 workflow 宣告，目前不支援巢狀子流程；換成別的模組 [%s] (module %s includes another "
                               "file or declares a workflow, which is not supported yet; use another module)" % (path, UNSUPPORTED, path),
                               code=UNSUPPORTED)

    header = list(header)
    kinds, columns, required, shown = {}, [], [], {}
    for item in rendered["open_inputs"]:
        node, number = item["node"], item["input"]
        records = [r for r in catalogue.describe(nodes[node]["module"], data)["inputs"] if r["channel"] == number]
        parts = []
        for r in records:
            kind, rname, optional = r.get("type"), r.get("name"), bool(r.get("optional"))
            if kind == "map":
                col, form = "sample", "[id: row.sample]"
            else:
                if kind not in _FORMS:
                    raise ProjectError("節點 %s 的輸入 %d（%s）：型別 %s 目前不支援；換成別的模組，或先把這個輸入接上線 "
                                       "(node %s input %d, record %s: the type %s is not supported yet; use another module or wire this input)"
                                       % (node, number, rname, kind or "（沒有型別）", node, number, rname, kind or "none"))
                if not isinstance(rname, str) or not _NAME.match(rname):
                    raise ProjectError("節點 %s 的輸入 %d：記錄名 %r 不能當樣本表的欄名；換成別的模組 (node %s input %d: the record name %r cannot be "
                                       "a samplesheet column; use another module)" % (node, number, rname, node, number, rname))
                col, form = rname, _FORMS[kind] % rname
            if col in kinds and kinds[col] != (kind or "map"):
                raise ProjectError("欄 %s 在不同的輸入裡型別不同（%s 與 %s），無法共用一欄；換成別的模組 (the column %s is used with two types, %s and "
                                   "%s)" % (col, kinds[col], kind, col, kinds[col], kind))
            kinds[col] = kind or "map"
            if col not in columns:
                columns.append(col)
            if not optional and col not in required:
                required.append(col)
            if optional and col not in header:
                form = "[]"
            parts.append(form)
        has_meta = any(r.get("type") == "map" for r in records)
        if not parts:
            shown[(node, number)] = "[]"
        elif len(parts) == 1 and not has_meta:
            shown[(node, number)] = parts[0]      # one value and no meta: the value itself
        else:
            shown[(node, number)] = "[ %s ]" % ", ".join(parts)      # meta first, the rest in the catalogue's order
    missing = [c for c in required if c not in header]
    if missing:
        raise ProjectError("樣本表需要這些欄：%s（缺：%s） (the samplesheet needs these columns: %s; missing: %s)"
                           % ("、".join(required), "、".join(missing), ", ".join(required), ", ".join(missing)))

    main_nf = files["main.nf"].split("\n")
    for item in rendered["open_inputs"]:
        node, number = item["node"], item["input"]
        old = "    ch_%s_in%d = Channel.empty()  // OPEN INPUT: %s input %d (%s)" % (node, number, node, number, ", ".join(item["names"]))
        at = _lines_of(main_nf, old)
        if len(at) != 1:
            raise ProjectError("組合渲染出的主程式不是預期的形狀，找不到節點 %s 輸入 %d 的那一行；請回報平台維護者 (the rendered main script has not the "
                               "expected line for node %s input %d)" % (node, number, node, number))
        main_nf[at[0]] = "    ch_%s_in%d = ch_rows.map { row -> %s }" % (node, number, shown[(node, number)])
    if rendered["open_inputs"]:
        start = _lines_of(main_nf, "workflow {")
        if len(start) != 1:
            raise ProjectError("組合渲染出的主程式不是預期的形狀，找不到 workflow 的開頭 (the rendered main script has no workflow line)")
        main_nf.insert(start[0] + 1, "    ch_rows = Channel.fromPath(params.input).splitCsv(header: true)")
    files["main.nf"] = "\n".join(main_nf)
    config = files["nextflow.config"]
    files["nextflow.config"] = (config if config.endswith("\n") else config + "\n") + "\n" + PUBLISH
    files.update(have)

    size = sum(len(text.encode("utf-8")) for text in files.values())
    if size > MAX_BYTES:
        raise ProjectError("專案檔全部共 %d 位元組，超過上限 %d（2 MiB）；請減少節點 (the project files are %d bytes together, more than the "
                           "limit of %d, 2 MiB; use fewer nodes)" % (size, MAX_BYTES, size, MAX_BYTES))
    if len(files) > MAX_FILES:
        raise ProjectError("專案有 %d 個檔案，超過上限 %d；請減少節點 (the project has %d files, more than the limit of %d; use fewer nodes)"
                           % (len(files), MAX_FILES, len(files), MAX_FILES))
    return {"project": files, "project_sha256": hashlib.sha256(common.canonical_json(files)).hexdigest(),
            "path_columns": [c for c in columns if kinds[c] in _PATHS and c in header], "columns": columns}


def _findings_text(result):
    errors = [f["message"] for f in result["findings"] if f["severity"] == "error"]
    lines = ["這個版本的檢查有 %d 個錯誤，所以不能送出 (this version has %d errors, so it cannot be sent):" % (len(errors), len(errors))]
    lines += ["- %s" % m for m in errors[:MAX_SHOWN]]
    if len(errors) > MAX_SHOWN:
        lines.append("另有 %d 條 (and %d more)" % (len(errors) - MAX_SHOWN, len(errors) - MAX_SHOWN))
    lines.append("到組合頁修正後存成新版本再送 (fix them on the pipeline page, save a new version and send that one)")
    return "\n".join(lines)


def prepare(platform_path, *, pipeline_id, version=None, run_name, samplesheet=None, samplesheet_raw=None, ce=None, params=None, caller=None,
            area=None, data=None, sources=None):
    """(environment name, bundle) for the launch of this version of a saved pipeline, or build.Refusal. Nothing is shown, asked or
    written. The pipeline must be the caller's (what is not answers like what does not exist); the check of today must have no error
    (it is made here, not read from what was stored); the project is built from the samplesheet's header."""
    from .actions import pipelines      # read here: this module is imported by the action layer
    got = pipelines.get_pipeline(platform_path, pipeline_id, version, caller=caller)
    if not got["ok"]:
        raise build.Refusal(got["message"])
    result = checks.validate(got["graph"], data)
    if not result["ok"]:
        raise build.Refusal(_findings_text(result))
    try:
        rows = build.parse_samplesheet(samplesheet_raw) if samplesheet_raw is not None else build.read_samplesheet(samplesheet)
    except build.bundle_mod.BundleError as e:
        raise build.Refusal(str(e))
    try:
        built = build_project(got["graph"], got["name"], got["version"], rows[0] if rows else [], data=data, sources=sources)
    except ProjectError as e:
        raise build.Refusal(str(e))
    return build.prepare_launch(platform_path, ce=ce, pipeline="%s/%s" % (build.bundle_mod.COMPOSED, got["name"]), revision="0.%d.0" % got["version"],
                                run_name=run_name, params=params, path_columns=built["path_columns"], check_name=False,
                                owner=caller.user_id if caller is not None else None, area=area, samplesheet_rows=rows,
                                composed={"pipeline_id": got["id"], "version": got["version"], "project": built["project"]})
