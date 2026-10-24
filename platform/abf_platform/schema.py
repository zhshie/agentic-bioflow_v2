# Nothing existing: prepare_launch.sh prints a text summary from inline shell Python, schema_roles.py only judges column roles; the platform has no structured data, and nf-core's CLI needs a full install.
"""Pure readers for a pipeline's nextflow_schema.json and assets/schema_input.json (feature schema-reader).

Input is text or an already parsed dict; nothing is fetched, stored or remembered.
Sample-column roles are NOT decided here (that rule lives only in scripts/utils/schema_roles.py).
"""
import json

MAX_CHARS = 2000000
_REF_PREFIXES = ("#/$defs/", "#/definitions/")


def load(text):
    """Parse schema text into a dict, or raise ValueError (bilingual message)."""
    if not isinstance(text, str) or len(text) > MAX_CHARS:
        raise ValueError("文字過長（上限 2,000,000 字元）/ Schema text is too long (limit 2,000,000 characters).")
    try:
        data = json.loads(text)
    except ValueError:
        raise ValueError("內容不是合法的 JSON / The text is not valid JSON.") from None
    if not isinstance(data, dict):
        raise ValueError("JSON 頂層必須是物件 / The top level of the JSON must be an object.")
    return data


def _str_or_none(v):
    return v if isinstance(v, str) else None


def _types(v):
    t = v.get("type")
    if isinstance(t, str):
        return [t]
    if isinstance(t, list):
        return [x for x in t if isinstance(x, str)]
    return []


def _param(name, p, required):
    desc = p.get("description")
    enum = p.get("enum")
    return {
        "name": name,
        "types": _types(p),
        "description": desc if isinstance(desc, str) else "",
        "help_text": _str_or_none(p.get("help_text")),
        "has_default": "default" in p,
        "default": p.get("default"),
        "required": name in required,
        "hidden": p.get("hidden") is True,
        "enum": enum if isinstance(enum, list) else None,
        "format": _str_or_none(p.get("format")),
        "pattern": _str_or_none(p.get("pattern")),
    }


def _group(gid, g):
    req = g.get("required")
    required = {x for x in req if isinstance(x, str)} if isinstance(req, list) else set()
    props = g.get("properties")
    params = []
    if isinstance(props, dict):
        for name, p in props.items():
            if isinstance(p, dict):
                params.append(_param(name, p, required))
    title = g.get("title")
    desc = g.get("description")
    return {
        "id": gid,
        "title": title if isinstance(title, str) else gid,
        "description": desc if isinstance(desc, str) else "",
        "hidden_count": sum(1 for p in params if p["hidden"]),
        "params": params,
    }


def parameter_groups(schema):
    """Parameter groups in nf-core display order (the top-level allOf order)."""
    if not isinstance(schema, dict):
        return []
    merged = {}
    for key in ("$defs", "definitions"):
        block = schema.get(key)
        if isinstance(block, dict):
            for gid, g in block.items():
                if gid not in merged:
                    merged[gid] = g
    order = []
    allof = schema.get("allOf")
    if isinstance(allof, list):
        for item in allof:
            ref = item.get("$ref") if isinstance(item, dict) else None
            if not isinstance(ref, str):
                continue
            for prefix in _REF_PREFIXES:
                if ref.startswith(prefix):
                    gid = ref[len(prefix):]
                    if gid in merged and gid not in order:
                        order.append(gid)
                    break
    order += [gid for gid in merged if gid not in order]
    groups = [_group(gid, merged[gid]) for gid in order if isinstance(merged[gid], dict)]
    top = schema.get("properties")
    if isinstance(top, dict) and top:
        g = _group("", {"title": "Parameters", "properties": top, "required": schema.get("required")})
        groups.append(g)
    return groups


def required_without_default(groups):
    """Names that are required and have no default, in group order then file order."""
    return [p["name"] for g in groups for p in g["params"] if p["required"] and not p["has_default"]]


def _meta(v):
    m = v.get("meta")
    if isinstance(m, str):
        return [m]
    if isinstance(m, list):
        return [x for x in m if isinstance(x, str)]
    return []


def samplesheet_columns(schema_input):
    """Raw column attributes of a schema_input.json, in file order."""
    if not isinstance(schema_input, dict):
        return []
    items = schema_input.get("items")
    props = items.get("properties") if isinstance(items, dict) else None
    if not isinstance(props, dict) or not props:
        props = schema_input.get("properties")
    if not isinstance(props, dict):
        return []
    req = items.get("required") if isinstance(items, dict) else None
    required = {x for x in req if isinstance(x, str)} if isinstance(req, list) else set()
    cols = []
    for name, c in props.items():
        if not isinstance(c, dict):
            continue
        desc = c.get("description")
        cols.append({
            "name": name,
            "types": _types(c),
            "required": name in required,
            "format": _str_or_none(c.get("format")),
            "pattern": _str_or_none(c.get("pattern")),
            "exists": c.get("exists") is True,
            "meta": _meta(c),
            "description": desc if isinstance(desc, str) else "",
        })
    return cols
