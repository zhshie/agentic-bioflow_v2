# Nothing existing: the new blocks of the guided launch page (guided-launch-2); they only draw what `actions.pipeline_files` and `actions.latest_release` returned.
"""guided-launch-2: the blocks of the launch page that come from the pipeline's own files, and the one pure function that turns the `p.<name>`
fields of the parameter table into lines of the parameter box.

The platform does not connect out: `web.py` calls the two read actions, which ask the caller's own agent, and hands their answers to the
functions here. Nothing in this file reads a file, a database or the network. Every sentence the agent or the action layer sends back is
`中文 (English)`; the page keeps the half of its own language (`web_board.plain_reason`). Every state is a symbol plus words: ✓ done, ✗ failed,
… reading, ○ not checked yet."""
import re
import urllib.parse

from . import web_board
from .web_board import esc, plain_reason, taipei_time


# ---- the `p.<name>` fields --------------------------------------------------------------------------------------------------------------

def fields_of(pairs):
    """{parameter name: text} of every `p.<name>` field of a form or an address (empty values kept; the caller decides what counts as filled)."""
    out = {}
    for key, value in dict(pairs).items():
        if isinstance(key, str) and key.startswith("p.") and web_board.PARAM_KEY.match(key[2:]):
            out[key[2:]] = str(value)
    return out


def _typed(value, kinds):
    """The value as the parameter's type in the pipeline's own schema asks for it; text when it cannot be (or the type is another one)."""
    if "integer" in kinds and web_board.PARAM_INT.match(value):
        return int(value)
    if "number" in kinds:
        if web_board.PARAM_INT.match(value):
            return int(value)
        if web_board.PARAM_FLOAT.match(value):
            return float(value)
    if "boolean" in kinds and value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


def merge_params(text, fields, types):
    """The parameter box after the filled `p.<name>` fields are added to it. `text` is the box as typed (it wins for a name in both); `fields`
    is {name: text}; `types` is {name: [json types]} from the pipeline's schema. An empty field is ignored. A name the schema does not know is
    written as it was typed, so the parameter box reads it the way it reads anything typed there."""
    text = str(text or "")
    have = {line.partition(":")[0].strip() for line in text.splitlines() if ":" in line and not line[:1].isspace()}
    lines = []
    for name, raw in (fields or {}).items():
        value = " ".join(str(raw).split())
        if not value or name in have:
            continue
        kinds = (types or {}).get(name)
        if kinds:
            lines.append(web_board.params_text({name: _typed(value, kinds)}))
        else:
            lines.append("%s: %s" % (name, value))
    if not lines:
        return text
    return (text.rstrip("\n") + "\n" if text.strip() else "") + "\n".join(lines)


def _params_of(files):
    """The parameters of the read of the schema, in the schema's order; [] when it is not there."""
    schema = (files or {}).get("schema") if (files or {}).get("state") == "ready" else None
    if not isinstance(schema, dict) or schema.get("status") != "ok":
        return []
    return [p for g in schema.get("groups") or [] for p in g.get("params") or []]


def types_of(files):
    """{parameter name: [json types]} from the read of the schema, {} when it is not there."""
    return {p["name"]: p.get("types") or [] for p in _params_of(files)}


def defaults_of(files):
    """{parameter name: default} of the parameters that have one in the pipeline's own schema (guided-launch-2b)."""
    return {p["name"]: p.get("default") for p in _params_of(files) if p.get("has_default")}


def _same(value, default):
    """Whether the typed value is the schema's default (a bool is never equal to a number)."""
    if isinstance(value, bool) or isinstance(default, bool):
        return isinstance(value, bool) and isinstance(default, bool) and value == default
    if isinstance(value, (int, float)) and isinstance(default, (int, float)):
        return value == default
    return type(value) is type(default) and value == default


def changed_fields(fields, files):
    """{name: text} of the filled `p.<name>` fields that are not what the pipeline does by itself. An empty field is not sent; a field whose typed
    value is the schema's default is not sent either (guided-launch-2b). Without the schema (reading or failed) every filled field stays, as typed."""
    types, defaults = types_of(files), defaults_of(files)
    out = {}
    for name, raw in (fields or {}).items():
        value = " ".join(str(raw).split())
        if not value:
            continue
        if name in defaults and (_shown(defaults[name]) == value or _same(_typed(value, types.get(name) or []), defaults[name])):
            continue
        out[name] = raw
    return out


def cell_value(p, cells):
    """What the box of this parameter holds: what was filled in (or the earlier analysis's value) when there is such a value, else the default."""
    if p["name"] in (cells or {}):
        return str(cells[p["name"]])
    return _shown(p.get("default")) if p.get("has_default") else ""


def cell_values(files, cells):
    """{name: text} of every box of the parameter table as the page shows it."""
    return {p["name"]: cell_value(p, cells) for p in _params_of(files)}


def split_prefill(params, files):
    """(cells, rest) of the parameters of an earlier analysis: those the schema knows go to the boxes of the table, the others stay as they were."""
    known = types_of(files)
    cells, rest = {}, {}
    for key, value in (params or {}).items():
        if key in known:
            cells[key] = _shown(value)
        else:
            rest[key] = value
    return cells, rest


def size_text(size):
    """A file size as the page writes it: B under 1 KB, whole KB under 1 MB, else MB with one decimal."""
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        return "—"
    if size < 1024:
        return "%d B" % size
    if size < 1048576:
        return "%d KB" % int(size / 1024.0 + 0.5)
    return "%.1f MB" % (size / 1048576.0)


def star(t):
    return '<span class="req" title="%s">*</span>' % esc(t["g2_req"])


# ---- small pieces -----------------------------------------------------------------------------------------------------------------------

CJK_PAREN = re.compile(r"\(([^()]*[⺀-鿿＀-￯][^()]*)\)")


def why(lang, text):
    """One plain line out of a sentence of the action layer. Most read `中文 (English)`; the refusal of a missing agent reads `English (中文): English
    (中文)`, which web_board.plain_reason would cut at the wrong place, so that shape is split here first."""
    text = str(text or "")
    if CJK_PAREN.search(text) and not web_board.CJK.search(CJK_PAREN.sub("", text)):
        if lang == "en":
            text = re.sub(r"\s+([:;,.])", r"\1", CJK_PAREN.sub("", text))
        else:
            text = "，".join(CJK_PAREN.findall(text))
    return plain_reason(text, lang)


def is_loading(*answers):
    return any(isinstance(a, dict) and a.get("state") == "loading" for a in answers)


def _line(symbol, css, text):
    return '<p class="%s"><span class="csym">%s</span> %s</p>' % (css, symbol, esc(text))


def reading(t, quiet=False):
    """The reading state: a symbol, a word and (unless the page is not going to refresh) the fixed sentence."""
    out = _line("…", "wait", t["g2_reading"])
    return out if quiet else out + '<p class="muted">%s</p>' % esc(t["g2_note"])


def _bad(lang, text):
    return _line("✗", "bad", why(lang, text))


def _failure(lang, files):
    """The ✗ line of a read that failed as a whole (state error)."""
    return _bad(lang, files.get("reason"))


def _part(files, name):
    """(kind, view): kind is 'none' (no read yet), 'loading', 'error' or 'part'."""
    if not isinstance(files, dict):
        return "none", None
    if files.get("state") == "loading":
        return "loading", None
    if files.get("state") != "ready":
        return "error", None
    return "part", files.get(name) if isinstance(files.get(name), dict) else {}


# ---- step 1 -----------------------------------------------------------------------------------------------------------------------------

def params_check(t, lang, revision, files):
    """The row of step 1 for the parameter table: (key, symbol, label, sentence)."""
    label = t["g_c_params"]
    if not revision or files is None:
        return ("params", "○", label, t["g2_params_wait"])
    kind, schema = _part(files, "schema")
    if kind == "loading":
        return ("params", "…", label, t["g2_reading"])
    if kind == "error":
        return ("params", "✗", label, why(lang, files.get("reason")))
    if schema.get("status") == "ok":
        groups = schema.get("groups") or []
        return ("params", "✓", label, t["g2_params_ok"] % (len(groups), sum(len(g.get("params") or []) for g in groups)))
    return ("params", "✗", label, why(lang, schema.get("message")))


def step1_note(t, files, quiet):
    return '<p class="muted">%s</p>' % esc(t["g2_note"]) if is_loading(files) and not quiet else ""


# ---- step 2 -----------------------------------------------------------------------------------------------------------------------------

def latest_block(t, lang, pipeline, latest, quiet=False):
    """Under the two boxes of the new-pipeline tab: the newest release, ready to be used."""
    if not isinstance(latest, dict):
        return ""
    if latest.get("state") == "loading":
        return reading(t, quiet)
    revision = latest.get("revision")
    if latest.get("state") != "ready" or not revision:
        return _bad(lang, latest.get("why"))
    link = esc("/launch?" + urllib.parse.urlencode([("pipeline", pipeline), ("revision", revision)] + ([("lang", "en")] if lang == "en" else []), safe="/"))
    out = ('<p class="ok"><span class="csym">✓</span> %s <a href="%s">%s</a></p>'
           % (esc(t["g2_latest"] % revision), link, esc(t["g2_use_ver"])))
    if latest.get("source") == "stale-cache":
        out += '<p class="muted">%s</p>' % esc(t["g2_stale"] % (taipei_time(latest.get("checked_at")) or "—"))
    return out


# ---- step 3 -----------------------------------------------------------------------------------------------------------------------------

def diagram_block(t, lang, pipeline, revision, files, image, quiet=False):
    """(state of the step, html): the workflow diagram as its file name, its size and a link that opens it in the same tab."""
    if files is None:
        return "later", '<p class="muted">%s</p>' % esc(t["g2_dia_wait"])
    kind, d = _part(files, "diagram")
    if kind == "loading":
        return "later", reading(t, quiet)
    if kind == "error":
        return "later", _failure(lang, files)
    if d.get("status") == "none":
        return "done", '<p class="muted">%s</p>' % esc(t["g2_dia_none"])
    if d.get("status") != "ok":
        return "later", _bad(lang, d.get("message"))
    ikind, im = _part(image, "image")
    if ikind in ("none", "loading"):
        return "later", _line("…", "wait", t["g2_img_wait"]) + ("" if quiet else '<p class="muted">%s</p>' % esc(t["g2_note"]))
    if ikind == "error":
        return "later", _failure(lang, image)
    if im.get("status") != "ok":
        return "later", _bad(lang, im.get("message"))
    href = esc("/launch/diagram?" + urllib.parse.urlencode([("pipeline", pipeline), ("revision", revision)], safe="/"))
    return "done", ('<p>%s</p><p><a class="dlink" href="%s">%s</a></p>'
                    % (esc(t["g2_dia_file"] % (d.get("name") or "—", size_text(d.get("size")))), href, esc(t["g2_dia_open"])))


# ---- step 4 -----------------------------------------------------------------------------------------------------------------------------

def samplesheet_block(t, lang, files, quiet=False):
    """Under the samplesheet chooser: the columns the pipeline's own schema_input asks for, in the file's order."""
    kind, si = _part(files, "schema_input")
    if kind == "none":
        return ""
    if kind == "loading":
        return reading(t, quiet)
    if kind == "error":
        return _failure(lang, files)
    if si.get("status") != "ok":
        return _bad(lang, si.get("message"))
    rows = "".join('<tr class="scol"><td>%s%s</td><td>%s</td></tr>'
                   % (esc(c.get("name")), star(t) if c.get("required") else "", esc(c.get("description") or "")) for c in si.get("columns") or [])
    heads = "".join("<th>%s</th>" % esc(t[k]) for k in ("g2_th_col", "g2_th_desc"))
    return ('<p class="muted">%s</p><table class="tbl scols"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>'
            % (esc(t["g_legend"]), heads, rows))


# ---- step 5 -----------------------------------------------------------------------------------------------------------------------------

def _shown(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def _row(t, p, cells):
    name = p["name"]
    required = star(t) if p.get("required") and not p.get("has_default") else ""
    default = _shown(p.get("default")) if p.get("has_default") else ""
    value = cell_value(p, cells)
    label = ' aria-label="%s"' % esc(name)

    def options(choices):
        shown = list(choices) + ([value] if value and value not in choices else [])
        return "".join('<option value="%s"%s>%s</option>' % (esc(x), " selected" if x == value else "", esc(x)) for x in [""] + shown)
    if p.get("enum"):
        control = '<select name="p.%s"%s>%s</select>' % (esc(name), label, options([str(x) for x in p["enum"]]))
    elif "boolean" in (p.get("types") or []):
        control = '<select name="p.%s"%s>%s</select>' % (esc(name), label, options(["true", "false"]))
    else:
        control = '<input name="p.%s"%s value="%s">' % (esc(name), label, esc(value))
    return ('<tr class="prow"><td>%s%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
            % (esc(name), required, esc(p.get("description") or ""), esc(", ".join(p.get("types") or [])), esc(default) if p.get("has_default") else "—", control))


COLS = ("cname", "cdesc", "ctype", "cdef", "cval")      # the widths are in the style sheet (web_board), one rule for each


def groups_block(t, lang, files, quiet=False, cells=None):
    """The parameter table: the pipeline's own groups, hidden parameters last, each with a box that comes back as `p.<name>` and holds the
    default (or the value of the earlier analysis, or what was filled in before the page was drawn again)."""
    kind, schema = _part(files, "schema")
    if kind == "none":
        return '<p class="muted">%s</p>' % esc(t["g2_groups_wait"])
    if kind == "loading":
        return reading(t, quiet)
    if kind == "error":
        return _failure(lang, files)
    if schema.get("status") != "ok":
        return _bad(lang, schema.get("message"))
    heads = "".join("<th>%s</th>" % esc(t[k]) for k in ("g2_th_name", "g2_th_desc", "g2_th_type", "g2_th_default", "g2_th_value"))
    colgroup = "<colgroup>%s</colgroup>" % "".join('<col class="%s">' % c for c in COLS)

    def table(params):
        return ('<table class="tbl ptbl">%s<thead><tr>%s</tr></thead><tbody>%s</tbody></table>'
                % (colgroup, heads, "".join(_row(t, p, cells) for p in params)))
    out, opened = [], False
    hidden = []
    for g in schema.get("groups") or []:
        shown = [p for p in g.get("params") or [] if not p.get("hidden")]
        hidden += [p for p in g.get("params") or [] if p.get("hidden")]
        if not shown:
            continue
        out.append('<details class="pgroup"%s><summary>%s</summary>%s</details>' % ("" if opened else " open", esc(g.get("title") or g.get("id") or ""), table(shown)))
        opened = True
    if hidden:
        out.append('<details class="pgroup pgroup-adv"><summary>%s</summary>%s</details>' % (esc(t["g2_adv"]), table(hidden)))
    return '<p class="muted">%s</p><div class="pgroups">%s</div>' % (esc(t["g_legend"]), "".join(out))


def fill_hint(t, loading):
    return '<p class="muted">%s</p>' % esc(t["g2_fill"]) if loading else ""
