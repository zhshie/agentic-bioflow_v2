# Nothing existing: the other harnesses fake a platform or a site agent; none fakes the answers of the MCP tools run_outputs and read_run_file as the user's own computer sees them, nor a bare HTTP stub that records the Authorization header.
"""Fakes for the tests of studio-connect and fetch-results (feature cli-fetch-publish-figure, slice 1).

`FakeSite` answers the two read tools the way the platform does (shapes taken from actions.run_outputs and actions.read_run_file) and keeps every call.
`patch_session` puts it behind `studio_remote.open_session`, so no network is used. `Stub` is a plain HTTP server on loopback that answers every
request with one status (or hangs) and records the Authorization header, for the tests of the connection errors."""
import contextlib
import http.server
import threading
import time

PAGE = 12          # characters per page of the fake read_run_file (the real one gives 200000)


class FakeSite:
    def __init__(self, files=None, sizes=None, page=PAGE, binary=(), errors=None, loading=0, forever_loading=(), outputs=None,
                 found=True, fail_page2=(), envs=None, env_error=False, compute_env="lab-a", publish=None):
        self.files = dict(files or {})            # relative path -> str
        self.sizes = dict(sizes or {})            # relative path -> size to report (default: the length in bytes)
        self.page, self.binary, self.errors = page, set(binary), dict(errors or {})
        self.loading = loading                    # how many times each read answers `loading` before `ready`
        self.forever_loading = set(forever_loading)
        self.outputs = outputs                    # a whole run_outputs answer to give at the root, instead of the tree
        self.found, self.fail_page2 = found, set(fail_page2)
        self.envs, self.env_error, self.compute_env = envs, env_error, compute_env
        self.publish = publish                    # the answer publish_figure gives (a dict, or a function of its arguments); slice 2
        self.calls = []
        self._loaded = {}

    NO_RUN = "Run not found (找不到這個 run)"

    def size_of(self, rel):
        if rel in self.sizes:
            return self.sizes[rel]
        return len(self.files[rel].encode("utf-8", "surrogatepass"))

    def run_outputs(self, args):
        if not self.found:
            return {"found": False, "message": self.NO_RUN}
        if self.outputs is not None:
            return self.outputs
        sub = args.get("path") or ""
        prefix = sub + "/" if sub else ""
        names, rows = [], []
        for rel in sorted(set(self.files) | set(self.sizes)):
            if not rel.startswith(prefix):
                continue
            rest = rel[len(prefix):]
            head = rest.split("/", 1)[0]
            if head in names:
                continue
            names.append(head)
            if "/" in rest:
                rows.append({"name": head, "type": "dir", "size": 0, "modified": "", "enter": prefix + head, "download": None, "too_large": False})
            else:
                size = self.size_of(rel) if rel in self.files or rel in self.sizes else 0
                big = size > 26214400
                rows.append({"name": head, "type": "file", "size": size, "modified": "", "enter": None, "download": None if big else rel, "too_large": big})
        return {"found": True, "state": "ready", "path": "/f/results" + ("/" + sub if sub else ""), "compute_env": self.compute_env, "files": rows,
                "listed_at": 1, "reason": None, "sub": sub, "bad_path": False, "max_bytes": 26214400, "top": []}

    def read_run_file(self, args):
        if not self.found:
            return {"found": False, "message": self.NO_RUN}
        rel, offset = args["path"], args.get("offset") or 0
        if rel in self.forever_loading:
            return {"found": True, "state": "loading", "message": "wait"}
        if self._loaded.get(rel, 0) < self.loading:
            self._loaded[rel] = self._loaded.get(rel, 0) + 1
            return {"found": True, "state": "loading", "message": "wait"}
        if rel in self.errors:
            return self.errors[rel]
        if rel in self.binary:
            return {"found": True, "state": "ready", "kind": "binary", "name": rel.rsplit("/", 1)[-1], "size": 5, "note": "binary", "download_url": "u"}
        if rel in self.fail_page2 and offset > 0:
            return {"found": True, "state": "error", "code": "failed", "reason": "the second page failed"}
        text = self.files[rel]
        page = text[offset:offset + self.page]
        end = offset + len(page)
        return {"found": True, "state": "ready", "kind": "text", "name": rel.rsplit("/", 1)[-1], "size": self.size_of(rel), "total_chars": len(text),
                "offset": offset, "text": page, "next_offset": end if end < len(text) else None}

    def list_compute_envs(self, args):
        if self.env_error:
            raise RuntimeError("list failed")
        return {"compute_envs": self.envs if self.envs is not None else []}

    def publish_figure(self, args):
        answer = self.publish
        return answer(args) if callable(answer) else answer

    def handle(self, name, args):
        self.calls.append((name, dict(args)))
        fn = getattr(self, name, None)
        if fn is None or name.startswith("_") or name in ("handle", "size_of"):
            raise AssertionError("the command called a tool it may not call: " + name)
        return fn(args)

    def names(self, tool):
        return [a for n, a in self.calls if n == tool]


class FakeSession:
    def __init__(self, site):
        self.site = site

    async def call_tool(self, name, args):
        return self.site.handle(name, args)

    async def tool_names(self):
        return ["run_outputs", "read_run_file", "list_compute_envs", "publish_figure"]


def patch_session(monkeypatch, site):
    """Every open_session of studio_remote now gives a FakeSession over `site`. Returns the list of configs it was opened with."""
    from abf_platform import studio_remote
    opened = []

    @contextlib.asynccontextmanager
    async def fake_open(config=None):
        opened.append(config)
        yield FakeSession(site)
    monkeypatch.setattr(studio_remote, "open_session", fake_open)
    return opened


class Stub:
    """A loopback HTTP server that answers every request with `status` after `delay` seconds and records what it was asked."""

    def __init__(self, status=503, delay=0.0):
        outer = self
        self.status, self.delay, self.requests = status, delay, []

        class H(http.server.BaseHTTPRequestHandler):
            def _go(self):
                n = int(self.headers.get("content-length") or 0)
                body = self.rfile.read(n) if n else b""
                outer.requests.append((self.command, self.headers.get("Authorization"), body))
                if outer.delay:
                    time.sleep(outer.delay)
                try:
                    self.send_response(outer.status)
                    self.send_header("content-length", "0")
                    self.end_headers()
                except OSError:
                    pass
            do_POST = do_GET = do_DELETE = _go

            def log_message(self, *a):
                pass
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.server.daemon_threads = True
        self.port = self.server.server_port
        self.url = "http://127.0.0.1:%d" % self.port
        self._t = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._t.start()

    def initialize_posts(self):
        return [r for r in self.requests if r[0] == "POST" and b'"method":"initialize"' in r[2]]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
