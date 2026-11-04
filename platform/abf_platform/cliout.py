# Nothing existing: cli.py printed straight to stdout and stderr; the output modes of the root flags --json and --debug live here.
"""Output modes of abf-platform: plain (as always), --json (one object per command) and --debug (extra lines on stderr).

The state is per call of cli.main and is reset at its start and end, so in-process callers never see a leftover."""
import json
import sys
import traceback
from pathlib import Path

# The product version is the one in plugin.json (not the 0.1.0 of the Python package). No fallback when it cannot be read.
PLUGIN_JSON = Path(__file__).resolve().parents[2] / ".claude-plugin" / "plugin.json"

_S = {"json": False, "debug": False, "lines": [], "error": None, "data": None}


def reset(json_mode=False, debug=False):
    _S.update(json=json_mode, debug=debug, lines=[], error=None, data=None)


def json_mode():
    return _S["json"]


def leading_flag(argv, flag):
    """True when `flag` is among the options written before the command (the only place the root flags are accepted)."""
    for a in argv:
        if not a.startswith("-"):
            return False
        if a == flag:
            return True
    return False


def say(text):
    if _S["json"]:
        _S["lines"].extend(str(text).split("\n"))
    else:
        print(text, flush=True)


def _clean(text):
    text = str(text).strip()
    return text[len("rejected:"):].strip() if text.startswith("rejected:") else text


def err(text, why=None, next=None):
    if not _S["json"]:
        print(text, file=sys.stderr, flush=True)
    elif _S["error"] is None:        # one object per command: the first failure is the one that is told
        _S["error"] = (_clean(text), why, next)


def set_data(obj):
    _S["data"] = obj


def emit_failure(command, what, why, next):
    obj = {"ok": False, "command": command, "error": {"what": what or "指令沒有成功", "why": why or "沒有給出更具體的原因",
                                                       "next": next or "不加 --json 執行看完整說明"}}
    print(json.dumps(obj, ensure_ascii=False, sort_keys=True), file=sys.stderr, flush=True)


def finish(command, rc, with_output=True):
    """In --json mode: print the one object of this command (stdout on success, stderr on failure)."""
    if not _S["json"]:
        return
    lines, e, data = _S["lines"], _S["error"], _S["data"]
    if rc == 0:
        obj = {"ok": True, "command": command, "data": data if data is not None else {}}
        if with_output:
            obj["output"] = lines
        print(json.dumps(obj, ensure_ascii=False, sort_keys=True), flush=True)
        return
    if e is None:
        e = ("指令沒有成功完成（結束碼 %s）" % rc, "; ".join(l.strip() for l in lines if l.strip())[:500], None)
    emit_failure(command, *e)


def debug(line):
    if _S["debug"]:
        print("debug: " + line, file=sys.stderr, flush=True)


def debug_exception():
    if _S["debug"]:
        for l in traceback.format_exc().splitlines():
            debug(l)


def read_version():
    """The `version` of plugin.json, or None when the file or the key is missing."""
    try:
        v = json.loads(Path(PLUGIN_JSON).read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError, AttributeError):
        return None
    return v if isinstance(v, str) and v.strip() else None
