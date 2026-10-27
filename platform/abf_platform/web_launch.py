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


def types_of(files):
    """{parameter name: [json types]} from the read of the schema, {} when it is not there."""
    schema = (files or {}).get("schema") if (files or {}).get("state") == "ready" else None
    if not isinstance(schema, dict) or schema.get("status") != "ok":
        return {}
    return {p["name"]: p.get("types") or [] for g in schema.get("groups") or [] for p in g.get("params") or []}


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
                    % (esc(t["g2_dia_file"] % (d.get("name") or "—", d.get("size") if isinstance(d.get("size"), int) else "—")), href, esc(t["g2_dia_open"])))


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
    rows = "".join('<tr class="scol"><td>%s</td><td>%s</td><td>%s</td></tr>'
                   % (esc(c.get("name")), "✓" if c.get("required") else "—", esc(c.get("description") or "")) for c in si.get("columns") or [])
    heads = "".join("<th>%s</th>" % esc(t[k]) for k in ("g2_th_col", "g2_th_req", "g2_th_desc"))
    return '<table class="tbl scols"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (heads, rows)


# ---- step 5 -----------------------------------------------------------------------------------------------------------------------------

def _shown(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def _row(t, p):
    name = p["name"]
    required = ' <span class="req">%s</span>' % esc(t["g2_req"]) if p.get("required") and not p.get("has_default") else ""
    default = _shown(p.get("default")) if p.get("has_default") else ""
    label = ' aria-label="%s"' % esc(name)
    if p.get("enum"):
        opts = '<option value=""></option>' + "".join('<option value="%s">%s</option>' % (esc(x), esc(x)) for x in p["enum"])
        control = '<select name="p.%s"%s>%s</select>' % (esc(name), label, opts)
    elif "boolean" in (p.get("types") or []):
        control = ('<select name="p.%s"%s><option value=""></option><option value="true">true</option><option value="false">false</option></select>'
                   % (esc(name), label))
    else:
        control = '<input name="p.%s"%s placeholder="%s">' % (esc(name), label, esc(default))
    return ('<tr class="prow"><td>%s%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
            % (esc(name), required, esc(p.get("description") or ""), esc(", ".join(p.get("types") or [])), esc(default) if p.get("has_default") else "—", control))


def groups_block(t, lang, files, quiet=False):
    """The parameter table of route ③: the pipeline's own groups, hidden parameters last, each with a box that comes back as `p.<name>`."""
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

    def table(params):
        return '<table class="tbl ptbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (heads, "".join(_row(t, p) for p in params))
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
    return '<div class="pgroups">%s</div>' % "".join(out)


def fill_hint(t, loading):
    return '<p class="muted">%s</p>' % esc(t["g2_fill"]) if loading else ""
