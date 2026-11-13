# Nothing existing: no other module marks the regions of a page or serves a script; the one script the web pages carry is the maintainer's named exception (2026-11-13).
"""live-sync: the pages that reloaded themselves every 15 seconds now carry one static script (data/live.js) that asks this site every 2 seconds whether the
page changed and replaces only the regions that differ. This module is the server's half: the script file, the Content-Security-Policy addition, the
regions of a page and their versions, and the two read-only answers (version, content).

A region is an element that is a direct child of a *container* of the page (the body, the three columns, a form that holds many controls, the figure list of
the gallery). Nothing is marked in the page itself except the body: its `data-live` attribute lists every container (name, where it is) and the version of each
of its regions, so no existing element changes by one byte. A container's own children never nest into each other, and every form control of a page lies in
exactly one region. The names are `<container>-<n>`: fixed words and a number, never anything a person wrote.

A look (the version or the content of a page) runs the page's own handler with LOOK set: the handler then reads and never queues, registers or writes; where the
real page would queue something, the look says so (`note("queue")`) and the answer is one reload, never more often than every RELOAD_SECONDS."""
import contextvars
import hashlib
import html
import json
from html.parser import HTMLParser
from pathlib import Path

SCRIPT_URL = "/static/live.js"
SCRIPT_TAG = '<script src="%s"></script>' % SCRIPT_URL
CSP_ADD = "script-src 'self'; connect-src 'self'"
RELOAD_SECONDS = 15.0       # the pace of today's meta refresh: a page that must ask the site again is loaded whole at most this often
LOOK = contextvars.ContextVar("abf_live_look", default=None)
_SCRIPT = Path(__file__).resolve().parent / "data" / "live.js"
VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())


def looking():
    """True while a look (a version or content request) runs the handler of a page."""
    return LOOK.get() is not None


def note(what):
    """The look says what the real page would have done here (`queue`: asked the site, or registered something; `go`: answered with something that is not the page)."""
    state = LOOK.get()
    if state is not None:
        state[what] = True


def script_bytes():
    return _SCRIPT.read_bytes()


def with_script(headers):
    """The headers of a page that carries the script: the policy gains script-src and connect-src, nothing else changes."""
    out = dict(headers)
    out["Content-Security-Policy"] = headers["Content-Security-Policy"] + "; " + CSP_ADD
    return out


# ---- a small tree of the page: where every element starts and ends -------------------------------------------------------------------

class Node:
    __slots__ = ("tag", "attrs", "start", "head_end", "end", "kids", "parent")

    def __init__(self, tag, attrs, start, head_end, parent):
        self.tag, self.attrs, self.start, self.head_end, self.end, self.kids, self.parent = tag, attrs, start, head_end, head_end, [], parent


class _Tree(HTMLParser):
    def __init__(self, doc):
        super().__init__(convert_charrefs=False)
        self.doc = doc
        self.lines = [0] + [i + 1 for i, ch in enumerate(doc) if ch == "\n"]
        self.root = Node("#root", {}, 0, 0, None)
        self.stack = [self.root]

    def _at(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def _open(self, tag, attrs):
        start = self._at()
        node = Node(tag, dict((k, v or "") for k, v in attrs), start, start + len(self.get_starttag_text()), self.stack[-1])
        self.stack[-1].kids.append(node)
        return node

    def handle_starttag(self, tag, attrs):
        node = self._open(tag, attrs)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs)

    def handle_endtag(self, tag):
        start = self._at()
        end = self.doc.index(">", start) + 1
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                for node in self.stack[i + 1:]:
                    node.end = start
                self.stack[i].end = end
                del self.stack[i:]
                return


def _tree(doc):
    tree = _Tree(doc)
    tree.feed(doc)
    tree.close()
    for node in tree.stack[1:]:
        node.end = len(doc)
    return tree.root


def _find(node, tag):
    if node.tag == tag:
        return node
    for kid in node.kids:
        got = _find(kid, tag)
        if got is not None:
            return got
    return None


def _container(node):
    """The name of the container an element is, or None. The names are the places of the board and the forms that hold many controls."""
    tag, attrs = node.tag, node.attrs
    cls = attrs.get("class", "").split()
    pane = attrs.get("data-pane")
    parent = node.parent
    if tag == "body":
        return "page"
    if tag == "div" and "wb" in cls:
        return "grid"
    if tag == "aside" and pane == "left":
        return "left"
    if tag == "main" and pane == "middle":
        return "mid"
    if tag == "aside" and pane == "right":
        return "right"
    if tag == "main" and "narrow" in cls:
        return "narrow"
    if tag == "form" and "lform" in cls:
        return "form"
    if tag == "div" and "gsteps" in cls:
        return "steps"
    if tag == "form" and attrs.get("action") == "/run/figures/pack":
        return "pack"
    if tag == "ul" and "pack" in cls and parent is not None and parent.tag == "form" and parent.attrs.get("action") == "/run/figures/pack":
        return "figs"
    if tag == "section" and any(k.tag == "form" and k.attrs.get("action") == "/run/figures/pack" for k in node.kids):
        return "gal"
    return None


def _digest(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def layout(doc):
    """[{n: container name, p: its place (the index of each ancestor among the element children, from the body), regions: [{name, html, start, end, hash}]}], in page
    order. A page with no body has none."""
    body = _find(_tree(doc), "body")
    out = []
    if body is None:
        return out

    def walk(node, path):
        name = _container(node)
        if name is not None:
            regions = []
            for kid in node.kids:
                if kid.tag == "script" or _container(kid) is not None:
                    continue
                text = doc[kid.start:kid.end]
                regions.append({"name": "%s-%d" % (name, len(regions)), "html": text, "start": kid.start, "end": kid.end, "hash": _digest(text)})
            out.append({"n": name, "p": path, "regions": regions})
        for i, kid in enumerate(node.kids):
            walk(kid, path + [i])
    walk(body, [])
    return out


def info_of(lay, headers):
    """The part of a page the script keeps: where the containers are, the version of every region, and the class of the headers the page came with (a page that
    gets a different policy, say the first picture of a gallery, is loaded whole)."""
    return {"h": _digest(headers.get("Content-Security-Policy", "")),
            "c": [{"n": c["n"], "p": c["p"], "v": [r["hash"] for r in c["regions"]]} for c in lay]}


def decorate(doc, headers):
    """(page, headers) of a page that carries the script: the body gets the `data-live` attribute, the policy the two sources. Any other page is returned as it is."""
    if SCRIPT_TAG not in doc:
        return doc, headers
    given = with_script(headers)
    attr = ' data-live="%s"' % html.escape(json.dumps(info_of(layout(doc), given), separators=(",", ":")), quote=True)
    return doc.replace("<body", "<body" + attr, 1), given


class Answers:
    """A pure ASGI middleware that answers a few fixed paths itself and hands every other request on. The paths are not routes of the app: the routes of the web app
    are listed exactly by tests that predate this feature, and the list stays what it was."""

    def __init__(self, app, table):
        self.app, self.table = app, table

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] in self.table:
            from starlette.requests import Request
            response = await self.table[scope["path"]](Request(scope, receive))
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
