# Nothing existing: tests of scripts/nf_relay.py, the login-node relay, with a real relay process and servers that count their connections; the repository's own relay tests check domains, not the one loopback door added by feature 007b.
"""The relay's loopback rule (feature 007b, FR-005): one narrow door, fail-closed, one request per connection."""
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from helpers import REPO_ROOT, free_port, wait_port

RELAY = REPO_ROOT / "scripts" / "nf_relay.py"
GOLDEN = Path(__file__).resolve().parent / "fixtures" / "relay_golden.json"


INSTANCE = "inst-0123456789abcdef"


class Counting:
    """A server on 127.0.0.1 that answers every request with 'ok', keeps the connection open, and records what it saw.

    Like the platform it answers the relay's question (a GET /user-info with the header X-ABF-Probe) with a 401 that names
    its instance id. `mode` makes it an impostor instead: "noheader" answers 401 with no id, "wrongid" another id, "ok200"
    a 200, "silent" nothing at all. `requests` holds the requests that were not that question; `raw` everything it received."""

    def __init__(self, port=None, mode="platform", instance=INSTANCE):
        self.port = port or free_port()
        self.mode = mode
        self.instance = instance
        self.raw = b""
        self.probes = 0
        self.connections = 0
        self.requests = []          # (connection number, request line)
        self.lock = threading.Lock()
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", self.port))
        self.sock.listen(32)
        self.stopped = False
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while not self.stopped:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with self.lock:
                self.connections += 1
                n = self.connections
            threading.Thread(target=self._serve, args=(conn, n), daemon=True).start()

    def _serve(self, conn, n):
        conn.settimeout(5)
        buf = b""
        try:
            while True:
                while b"\r\n\r\n" not in buf:
                    chunk = conn.recv(4096)
                    if not chunk:
                        return
                    buf += chunk
                head, _, buf = buf.partition(b"\r\n\r\n")
                line = head.split(b"\r\n", 1)[0].decode("latin-1")
                m = re.search(rb"(?i)content-length:\s*(\d+)", head)
                need = int(m.group(1)) if m else 0
                while len(buf) < need:
                    buf += conn.recv(4096)
                buf = buf[need:]
                with self.lock:
                    self.raw += head + b"\r\n\r\n"
                    if b"x-abf-probe" in head.lower():
                        self.probes += 1
                    else:
                        self.requests.append((n, line))
                if b"x-abf-probe" in head.lower():
                    answer = {"platform": b"HTTP/1.1 401 Unauthorized\r\nX-ABF-Platform: " + self.instance.encode() + b"\r\nContent-Length: 0\r\n\r\n",
                              "noheader": b"HTTP/1.1 401 Unauthorized\r\nContent-Length: 0\r\n\r\n",
                              "wrongid": b"HTTP/1.1 401 Unauthorized\r\nX-ABF-Platform: someone-else-0000\r\nContent-Length: 0\r\n\r\n",
                              "ok200": b"HTTP/1.1 200 OK\r\nX-ABF-Platform: " + self.instance.encode() + b"\r\nContent-Length: 0\r\n\r\n",
                              "silent": b""}[self.mode]
                    if answer:
                        conn.sendall(answer)
                    continue
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")   # and the connection stays open
        except OSError:
            pass
        finally:
            conn.close()

    def stop(self):
        self.stopped = True
        self.sock.close()


class Relay:
    def __init__(self, tmp, forward=None, instance=INSTANCE, extra_env=None):
        self.port = free_port()
        self.forward_file = Path(tmp) / "forward_port"
        self.instance_file = Path(tmp) / "forward_instance"
        if forward is not None:
            self.forward_file.write_text(str(forward) + "\n")
            if instance:
                self.instance_file.write_text(instance + "\n")
        self.log = Path(tmp) / "relay.log"
        env = dict(os.environ, NF_RELAY_FORWARD_FILE=str(self.forward_file), NF_RELAY_EXTRA_DOMAINS="abf-golden.example.org",
                   PYTHONDONTWRITEBYTECODE="1")
        env.pop("NF_RELAY_STATE_DIR", None)
        env.update(extra_env or {})
        self.proc = subprocess.Popen([sys.executable, str(RELAY), str(self.port)], env=env, stdout=open(self.log, "w"),
                                     stderr=subprocess.STDOUT)
        wait_port(self.port, proc=self.proc)

    def send(self, raw, source="127.0.0.1", read_timeout=6.0):
        """The whole answer the relay gives to these bytes (empty if it closes without one)."""
        s = socket.socket()
        s.bind((source, 0))
        s.settimeout(read_timeout)
        s.connect(("127.0.0.1", self.port))
        s.sendall(raw)
        out = b""
        try:
            while True:
                d = s.recv(65536)
                if not d:
                    break
                out += d
        except socket.timeout:
            pass
        s.close()
        return out

    def lines(self):
        time.sleep(0.3)
        return self.log.read_text().splitlines()

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def get(target, host=None, method="GET", body=b"", extra=b""):
    h = host or re.sub(r"^http://", "", target).split("/", 1)[0]
    head = ("%s %s HTTP/1.1\r\nHost: %s\r\n" % (method, target, h)).encode()
    if body:
        head += b"Content-Length: %d\r\n" % len(body)
    return head + extra + b"\r\n" + body


def status(answer):
    m = re.match(rb"HTTP/1\.[01] (\d{3})", answer)
    return int(m.group(1)) if m else None


@pytest.fixture
def world(tmp_path):
    srv = Counting()
    relay = Relay(tmp_path, forward=srv.port)
    yield relay, srv
    relay.stop()
    srv.stop()


def test_tc030_the_one_forward_port_is_reached_by_plain_http_and_the_file_is_read_for_every_request(tmp_path, world):
    relay, srv = world
    F = srv.port
    for method, path, body in (("GET", "/user-info", b""), ("POST", "/trace/create", b'{"a":1}'), ("PUT", "/trace/abc/progress", b"{}")):
        answer = relay.send(get("http://127.0.0.1:%d%s" % (F, path), method=method, body=body))
        assert status(answer) == 200 and answer.endswith(b"ok"), (method, answer)
    assert [r[1].split()[0] for r in srv.requests] == ["GET", "POST", "PUT"]
    assert [r[1].split()[1] for r in srv.requests] == ["/user-info", "/trace/create", "/trace/abc/progress"], "origin form on the way"
    assert sum("OPEN-HTTP 127.0.0.1 %d" % F in ln for ln in relay.lines()) == 3
    other = Counting()
    try:
        relay.forward_file.write_text("%d\n" % other.port)          # the file changes; the relay is not restarted
        assert status(relay.send(get("http://127.0.0.1:%d/user-info" % F))) in (400, 403, 405, 502)
        assert len(srv.requests) == 3
        assert status(relay.send(get("http://127.0.0.1:%d/user-info" % other.port))) == 200
        assert len(other.requests) == 1
    finally:
        other.stop()


def test_tc031_every_other_door_to_loopback_stays_shut_and_a_broken_forward_file_shuts_all(tmp_path, world):
    relay, srv = world
    F = srv.port
    others = {}
    for n in (F + 1, 65535, 80, 22, 1):      # a server is only put where an ordinary user may listen; the others are still asked for
        try:
            others[n] = Counting(n)
        except OSError:
            pass
    targets = ["http://127.0.0.1:%d/user-info" % n for n in (F + 1, 65535, 80, 22, 1, relay.port)] + [
        "http://localhost:%d/user-info" % F, "http://[::1]:%d/user-info" % F, "http://127.0.0.2:%d/user-info" % F,
        "http://127.1:%d/user-info" % F, "http://0x7f.0.0.1:%d/user-info" % F, "http://2130706433:%d/user-info" % F,
        "http://0.0.0.0:%d/user-info" % F, "http://127.0.0.1.:%d/user-info" % F, "http://user@127.0.0.1:%d/user-info" % F,
        "http://127.0.0.1:%d@evil.example/user-info" % F, "http://127.0.0.1:" + str(F).translate({ord(c): ord(c) + 0xFEE0 for c in "0123456789"}) + "/user-info",
        "http://127.0.0.1:+%d/user-info" % F,
        "http://127.0.0.1:0%d/user-info" % F, "http://127.0.0.1: %d/user-info" % F, "http://127.0.0.1/user-info",
]
    for t in targets:
        answer = relay.send(get(t))
        assert status(answer) in (None, 400, 403, 405, 502), (t, answer[:80])
    assert srv.connections == 0 and all(o.connections == 0 for o in others.values())
    connect = relay.send(("CONNECT 127.0.0.1:%d HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n" % (F, F)).encode())
    assert status(connect) in (400, 403, 405) and srv.connections == 0
    raw_form = relay.send(b"GET /user-info HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n" % F)
    assert status(raw_form) in (400, 403, 405) and srv.connections == 0
    # a peer that is not a compute node is turned away before anything else
    denied = relay.send(get("http://127.0.0.1:%d/user-info" % F), source="127.0.0.2")
    assert status(denied) == 403 and srv.connections == 0
    assert any("DENY-PEER" in ln for ln in relay.lines())
    assert any("DENY" in ln for ln in relay.lines())
    for o in others.values():
        o.stop()
    # a forward file that cannot be trusted opens nothing, however the request is spelled
    for content in (None, b"", b"   \n", b"abc\n", b"-5\n", b"0\n", b"70000\n", ("%d\n" % relay.port).encode(), b"\xff\x00\x01\x02",
                    ("0%d\n" % F).encode(), ("+%d\n" % F).encode(), ("%d\n%d\n" % (F, F)).encode(), b"1023\n"):
        if content is None:
            relay.forward_file.unlink()
        else:
            relay.forward_file.write_bytes(content)
        answer = relay.send(get("http://127.0.0.1:%d/user-info" % F))
        assert status(answer) in (None, 400, 403, 405, 502), (content, answer[:80])
    assert srv.connections == 0
    relay.forward_file.write_text("%d\n" % F)
    assert status(relay.send(get("http://127.0.0.1:%d/user-info" % F))) == 200


@pytest.mark.parametrize("path,allowed", [
    ("/agent/poll", False), ("/agent/hello", False), ("/mcp", False), ("/", False), ("/trace", False), ("/user-info/x", False),
    ("/user-infox", False), ("//agent/poll", False), ("/trace/../agent/poll", False), ("/trace/%2e%2e/agent/poll", False),
    ("/trace/%2E%2E/agent/poll", False), ("/agent/poll?x=/trace/", False), ("/trace/x/../../agent/poll", False),
    ("/trace/a b", False), ("/trace/a\\b", False), ("/user-info", True), ("/user-info?x=1", True), ("/trace/create", True),
    ("/trace/abc/begin", True), ("/trace/abc/complete?workspaceId=1", True)])
@pytest.mark.parametrize("method", ["GET", "POST", "PUT"])
def test_tc032_only_the_trace_paths_and_user_info_are_forwarded_and_the_query_does_not_count(tmp_path, world, path, allowed, method):
    relay, srv = world
    target = "http://127.0.0.1:%d%s" % (srv.port, path.replace(" ", "%20") if "a b" in path else path)
    answer = relay.send(get(target, method=method, body=b"{}" if method != "GET" else b""))
    if allowed:
        assert status(answer) == 200 and len(srv.requests) == 1
    else:
        assert status(answer) in (None, 400, 403, 404, 405) and srv.connections == 0, (path, answer[:80])


def test_tc032_one_request_per_connection_the_second_never_reaches_the_platform(tmp_path, world):
    relay, srv = world
    F = srv.port
    first = get("http://127.0.0.1:%d/user-info" % F)
    second = get("http://127.0.0.1:%d/agent/poll" % F, method="POST", body=b"{}")
    answer = relay.send(first + second)
    assert status(answer) == 200
    assert len(srv.requests) == 1 and srv.requests[0][1].split()[1] == "/user-info"
    # and sent one after the other on the same connection
    s = socket.socket()
    s.settimeout(6)
    s.connect(("127.0.0.1", relay.port))
    s.sendall(first)
    got = b""
    while True:
        d = s.recv(4096)
        if not d:
            break
        got += d
    assert status(got) == 200, "the relay closed the connection after the answer"
    try:
        s.sendall(second)
    except OSError:
        pass
    s.close()
    time.sleep(0.5)
    assert len(srv.requests) == 2 and all(r[1].split()[1] == "/user-info" for r in srv.requests)


def test_tc032_a_body_longer_than_it_says_is_not_a_second_request(tmp_path, world):
    relay, srv = world
    F = srv.port
    smuggle = get("http://127.0.0.1:%d/trace/create" % F, method="POST", body=b"{}" + get("http://127.0.0.1:%d/agent/poll" % F))
    smuggle = smuggle.replace(b"Content-Length: %d" % (len(smuggle.split(b"\r\n\r\n", 1)[1])), b"Content-Length: 2")
    relay.send(smuggle)
    assert [r[1].split()[1] for r in srv.requests] == ["/trace/create"]


def _golden_requests(relay_port):
    big = b"GET http://abf-golden.example.org/x HTTP/1.1\r\nHost: abf-golden.example.org\r\n\r\n"
    items = [
        ("allowed domain, plain http", big, "127.0.0.1"),
        ("allowed domain, subdomain", b"GET http://a.b.abf-golden.example.org/x HTTP/1.1\r\nHost: a\r\n\r\n", "127.0.0.1"),
        ("connect allowed domain", b"CONNECT abf-golden.example.org:443 HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("denied domain plain", b"GET http://evil.example.net/x HTTP/1.1\r\nHost: evil\r\n\r\n", "127.0.0.1"),
        ("denied domain connect", b"CONNECT evil.example.net:443 HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("suffix trick", b"CONNECT evilabf-golden.example.org:443 HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("ip literal connect", b"CONNECT 93.184.216.34:443 HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("ip literal plain", b"GET http://93.184.216.34/ HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("loopback connect", b"CONNECT 127.0.0.1:22 HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("loopback plain without a forward file", b"GET http://127.0.0.1:9/user-info HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("localhost plain", b"GET http://localhost:9/x HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("private ip connect", b"CONNECT 10.0.0.1:443 HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("non-absolute request", b"GET /x HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("https scheme in plain request", b"GET https://abf-golden.example.org/x HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("malformed line", b"GARBAGE\r\n\r\n", "127.0.0.1"),
        ("empty line", b"\r\n\r\n", "127.0.0.1"),
        ("delete plain allowed", b"DELETE http://abf-golden.example.org/x HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("head plain allowed", b"HEAD http://abf-golden.example.org/x HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("connect without port", b"CONNECT abf-golden.example.org HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("connect uppercase domain", b"CONNECT ABF-GOLDEN.EXAMPLE.ORG:443 HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("connect trailing dot", b"CONNECT abf-golden.example.org.:443 HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("denied wildcard-dns name", b"CONNECT 1.2.3.4.nip.io:443 HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("userinfo trick", b"GET http://abf-golden.example.org@evil.example.net/x HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("non-compute peer plain", big, "127.0.0.2"),
        ("non-compute peer connect", b"CONNECT abf-golden.example.org:443 HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.2"),
        ("non-compute peer loopback", b"GET http://127.0.0.1:9/user-info HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.2"),
        ("allowed domain, port 8080", b"GET http://abf-golden.example.org:8080/x HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("denied github look-alike", b"CONNECT github.com.evil.example.net:443 HTTP/1.1\r\nHost: x\r\n\r\n", "127.0.0.1"),
        ("tab in request line", b"GET\thttp://evil.example.net/ HTTP/1.1\r\n\r\n", "127.0.0.1"),
        ("http/1.0 connect denied", b"CONNECT evil.example.net:443 HTTP/1.0\r\n\r\n", "127.0.0.1"),
    ]
    assert len(items) == 30
    return items


def _first_line(answer):
    return answer.split(b"\r\n", 1)[0].decode("latin-1") if answer else ""


def test_tc075_with_no_forward_file_the_relay_answers_exactly_as_it_did_before_feature_007b(tmp_path):
    # TC-075: GOLDEN was recorded from scripts/nf_relay.py of main (bd9d42b) with the same 30 requests
    relay = Relay(tmp_path)  # no forward file at all
    try:
        got = {name: _first_line(relay.send(raw, source=src, read_timeout=8)) for name, raw, src in _golden_requests(relay.port)}
    finally:
        relay.stop()
    golden = json.loads(GOLDEN.read_text())
    assert golden["recorded_from"].startswith("bd9d42b")
    assert got == golden["answers"]


@pytest.mark.parametrize("mode", ["noheader", "wrongid", "ok200", "silent"])
def test_tc080_a_listener_that_took_over_the_forward_port_never_sees_a_run_token(tmp_path, mode):
    # security F1: when the shared connection ends, its port is free and another user of the login node can listen on it
    impostor = Counting(mode=mode)
    relay = Relay(tmp_path, forward=impostor.port)
    token = "abf_" + os.urandom(16).hex()      # made at run time: a fixed token-shaped value would fail the credentials check
    try:
        for method, path in (("PUT", "/trace/abc/progress"), ("POST", "/trace/create"), ("GET", "/user-info")):
            answer = relay.send(get("http://127.0.0.1:%d%s" % (impostor.port, path), method=method, body=b"{}" if method != "GET" else b"",
                                    extra=("Authorization: Bearer %s\r\n" % token).encode()))
            assert status(answer) in (None, 403), (mode, answer[:80])
        assert impostor.requests == [], "nothing but the question reached it"
        assert token.encode() not in impostor.raw
        assert any("DENY-LOOPBACK" in ln for ln in relay.lines())
    finally:
        relay.stop()
        impostor.stop()


def test_tc080_without_an_instance_file_or_with_a_broken_one_the_door_stays_shut(tmp_path, world):
    relay, srv = world
    F = srv.port
    for content in (None, b"", b"short\n", b"has space in it\n", b"x" * 100, b"\xff\x00\x01 not text"):
        if content is None:
            relay.instance_file.unlink()
        else:
            relay.instance_file.write_bytes(content)
        assert status(relay.send(get("http://127.0.0.1:%d/trace/create" % F, method="POST", body=b"{}"))) in (None, 403), content
    assert srv.requests == []
    relay.instance_file.write_text(INSTANCE + "\n")
    assert status(relay.send(get("http://127.0.0.1:%d/trace/create" % F, method="POST", body=b"{}"))) == 200
    relay.instance_file.write_text("another-platform-id\n")      # the file names another platform than the one that answers
    assert status(relay.send(get("http://127.0.0.1:%d/trace/create" % F, method="POST", body=b"{}"))) in (None, 403)
    assert len(srv.requests) == 1


# ---------------------------------------------------------------------------
# relay-prefix-nano4: the peer prefixes come from NF_RELAY_PEER_PREFIXES
# ---------------------------------------------------------------------------
import importlib.util

NANO4 = "25a-cpn,25a-hgpn,25a-lgn"
DEFAULT_PEERS = ("cpn", "gpn", "bgm", "lgn", "localhost")
UNSET = object()


def load_relay(monkeypatch, peers=UNSET, extra_domains=None):
    """A fresh module instance of scripts/nf_relay.py (its _PEER_CACHE is module-global)."""
    monkeypatch.delenv("NF_RELAY_PEER_PREFIXES", raising=False)
    monkeypatch.delenv("NF_RELAY_EXTRA_DOMAINS", raising=False)
    monkeypatch.delenv("NF_RELAY_EXTRA_NOTE", raising=False)
    if peers is not UNSET:
        monkeypatch.setenv("NF_RELAY_PEER_PREFIXES", peers)
    if extra_domains is not None:
        monkeypatch.setenv("NF_RELAY_EXTRA_DOMAINS", extra_domains)
    monkeypatch.setattr(sys, "argv", ["nf_relay.py"])
    spec = importlib.util.spec_from_file_location("nf_relay_under_test_%d" % time.monotonic_ns(), RELAY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def peer_of(relay, monkeypatch, name):
    """peer_ok() with the reverse lookup faked to return `name` (None = the lookup fails)."""
    def fake(ip):
        if name is None:
            raise socket.herror("no reverse record")
        return (name, [], [ip])
    monkeypatch.setattr(relay.socket, "gethostbyaddr", fake)
    relay._PEER_CACHE.clear()
    return relay.peer_ok("172.16.0.9")


def test_tc001_tc002_default_peer_prefixes_when_nothing_is_set(monkeypatch):
    # TC-001, TC-002
    relay = load_relay(monkeypatch)
    assert relay.ALLOW_HOST_PREFIXES == DEFAULT_PEERS
    assert isinstance(relay.ALLOW_HOST_PREFIXES, tuple)
    assert relay.DEFAULT_HOST_PREFIXES == DEFAULT_PEERS


@pytest.mark.parametrize("raw,loud", [("", False), ("  ", True), (",", True), ("a,b", True), ("*", True), (".", True)])
def test_tc003_to_tc008_default_when_empty_blank_or_all_invalid(monkeypatch, raw, loud):
    # TC-003 (""), TC-004 ("  "), TC-005 (","), TC-006 ("a,b"), TC-007 ("*"), TC-008 (".")
    relay = load_relay(monkeypatch, raw)
    assert relay.ALLOW_HOST_PREFIXES == DEFAULT_PEERS
    text = "\n".join(relay.startup_lines())
    if loud:
        assert "had no usable entry" in text


def test_tc009_to_tc012_startup_lines_unchanged_when_unset(monkeypatch):
    # TC-009, TC-010, TC-011, TC-012
    relay = load_relay(monkeypatch)
    lines = relay.startup_lines()
    assert lines[1] == "  peers  : cpn,gpn,bgm,lgn,localhost*"
    text = "\n".join(lines)
    assert "peers (this deployment)" not in text and "peers: dropped" not in text
    assert "had no usable entry" not in text
    assert lines[0] == "nf-relay on 0.0.0.0:18080"
    assert lines[2].startswith("  domains (built in): ")
    assert lines[3:] == ["  domains (this deployment): (none)"]


@pytest.mark.parametrize("name,expect", [
    ("cpn3857.nchc.org.tw", True), ("gpn0101", True), ("bgm01", True), ("lgn304", True), ("localhost", True),  # TC-013..017
    ("25a-cpn03", False), ("25a-hgpn170", False), ("25a-lgn01", False), ("25a-xyz1", False),                   # TC-018
    ("laptop.example", False), ("evilcpn3857.example", False), ("xcpn1", False),                               # TC-019..021
    ("CPN3001.Example", True), (None, False),                                                                    # TC-022, TC-023
])
def test_tc013_to_tc023_default_allows_t3_nodes_and_refuses_others(monkeypatch, name, expect):
    relay = load_relay(monkeypatch)
    ok, shown = peer_of(relay, monkeypatch, name)
    assert ok is expect
    if name is None:
        assert shown == "<no-rdns>"


def test_tc029_and_tc072_an_extra_domain_does_not_become_a_peer(monkeypatch):
    # TC-029 (default) and TC-072 (with a setting)
    for peers in (UNSET, "25a-cpn"):
        relay = load_relay(monkeypatch, peers, extra_domains="download.example.org")
        assert peer_of(relay, monkeypatch, "download.example.org")[0] is False


def test_tc030_setting_replaces_the_list_and_localhost_is_kept(monkeypatch):
    # TC-030
    relay = load_relay(monkeypatch, NANO4)
    assert relay.ALLOW_HOST_PREFIXES == ("25a-cpn", "25a-hgpn", "25a-lgn", "localhost")


@pytest.mark.parametrize("name,expect", [
    ("25a-cpn03", True), ("25a-hgpn170", True), ("25a-lgn01", True),   # TC-031..033
    ("localhost", True),                                                 # TC-034
    ("cpn3857.nchc.org.tw", False), ("lgn304", False),                   # TC-035, TC-036
    ("25a-gpu1", False), ("25a-xyz1", False),                            # TC-037
    ("CPN3001.Example", False), ("laptop.example", False), (None, False),  # TC-038, TC-039
    ("evilcpn3857", False),                                              # TC-040
])
def test_tc031_to_tc040_nano4_setting(monkeypatch, name, expect):
    relay = load_relay(monkeypatch, NANO4)
    assert peer_of(relay, monkeypatch, name)[0] is expect


def test_tc041_embedded_newline_is_one_dropped_line(monkeypatch):
    # TC-041
    base = load_relay(monkeypatch, "25a-cpn").startup_lines()
    relay = load_relay(monkeypatch, "25a-cpn,cp\nn")
    lines = relay.startup_lines()
    assert len(lines) == len(base) + 1
    assert sum(1 for ln in lines if "peers: dropped" in ln) == 1
    assert relay.ALLOW_HOST_PREFIXES == ("25a-cpn", "localhost")
    assert all("\n" not in ln for ln in lines)


def test_tc042_no_raw_control_characters_in_the_output(monkeypatch):
    # TC-042
    relay = load_relay(monkeypatch, "25a-cpn,\x1b[31m")
    lines = relay.startup_lines()
    assert not any(ord(c) < 32 or ord(c) == 127 for ln in lines for c in ln)
    assert any("peers: dropped" in ln for ln in lines)
    assert relay.ALLOW_HOST_PREFIXES == ("25a-cpn", "localhost")


def test_tc043_tc044_nano4_startup_lines(monkeypatch):
    # TC-043, TC-044
    lines = load_relay(monkeypatch, NANO4).startup_lines()
    assert "  peers  : 25a-cpn,25a-hgpn,25a-lgn,localhost*" in lines
    assert "  peers (this deployment): set by relay_peer_prefixes" in lines


def test_tc045_tc046_match_is_on_the_start_and_case_is_folded(monkeypatch):
    # TC-045, TC-046
    relay = load_relay(monkeypatch, "CPN, GPN")
    assert relay.ALLOW_HOST_PREFIXES == ("cpn", "gpn", "localhost")
    assert peer_of(relay, monkeypatch, "CPN3001.Example")[0] is True
    assert peer_of(relay, monkeypatch, "mycpn3001")[0] is False


@pytest.mark.parametrize("raw,expect", [("cpn,,lgn", ("cpn", "lgn", "localhost")), (",cpn", ("cpn", "localhost")),
                                        ("cpn,", ("cpn", "localhost"))])
def test_tc047_to_tc050_an_empty_string_never_becomes_a_prefix(monkeypatch, raw, expect):
    # TC-047, TC-048, TC-049, TC-050
    relay = load_relay(monkeypatch, raw)
    assert relay.ALLOW_HOST_PREFIXES == expect
    assert "" not in relay.ALLOW_HOST_PREFIXES
    assert not any("dropped" in ln for ln in relay.startup_lines())
    assert peer_of(relay, monkeypatch, "laptop.example")[0] is False


def test_tc051_tc052_tc053_invalid_entries_dropped_and_named(monkeypatch):
    # TC-051, TC-052, TC-053
    relay = load_relay(monkeypatch, "25a-cpn, a.b, ab, UPPER_CASE, ça-cpn, ok-x")
    assert relay.ALLOW_HOST_PREFIXES == ("25a-cpn", "ok-x", "localhost")
    dropped = [ln for ln in relay.startup_lines() if "peers: dropped" in ln]
    assert len(dropped) == 4
    for item in ("a.b", "ab", "UPPER_CASE"):
        assert any("dropped '%s' - " % item in ln and len(ln.split(" - ", 1)[1]) > 3 for ln in dropped), item
    assert any("a-cpn" in ln for ln in dropped)   # the non-ASCII one, shown through _clean() (TC-053)


def test_tc069_more_than_twenty_entries_are_cut(monkeypatch):
    # TC-069
    names = ["host-%02d" % i for i in range(21)]
    relay = load_relay(monkeypatch, ",".join(names))
    assert relay.ALLOW_HOST_PREFIXES == tuple(names[:20]) + ("localhost",)
    assert any("dropped 'host-20'" in ln and "limit of 20" in ln for ln in relay.startup_lines())


@pytest.mark.parametrize("raw,expect", [("localhost,cpn", ("localhost", "cpn")),     # TC-070
                                        ("cpn,lgn,cpn", ("cpn", "lgn", "localhost"))])  # TC-071
def test_tc070_tc071_localhost_is_not_added_twice_and_duplicates_go(monkeypatch, raw, expect):
    assert load_relay(monkeypatch, raw).ALLOW_HOST_PREFIXES == expect


def test_tc073_tc074_tc075_length_and_first_character(monkeypatch):
    # TC-073 (32 ok), TC-074 (33 dropped), TC-075 ("-abc" dropped)
    ok32, bad33 = "a" * 32, "b" * 33
    relay = load_relay(monkeypatch, "%s,%s,-abc,good" % (ok32, bad33))
    assert relay.ALLOW_HOST_PREFIXES == (ok32, "good", "localhost")
    text = "\n".join(relay.startup_lines())
    assert "dropped '%s'" % ok32 not in text
    assert "dropped '-abc'" in text
    assert "peers: dropped 'bbbbbbbb" in text


def test_tc088_no_wildcards_and_no_dots(monkeypatch):
    # TC-088
    relay = load_relay(monkeypatch, "cpn*,cpn.nchc,fine")
    assert relay.ALLOW_HOST_PREFIXES == ("fine", "localhost")
    text = "\n".join(relay.startup_lines())
    assert "dropped 'cpn*'" in text and "dropped 'cpn.nchc'" in text


def test_tc061_tc062_tc063_a_real_relay_with_a_prefix_setting(tmp_path):
    # TC-061, TC-062, TC-063
    srv = Counting()
    relay = Relay(tmp_path, forward=srv.port, extra_env={"NF_RELAY_PEER_PREFIXES": "zzz-nomatch"})
    try:
        target = "http://127.0.0.1:%d/user-info" % srv.port
        assert status(relay.send(get(target), source="127.0.0.1")) != 403
        assert status(relay.send(get(target), source="127.0.0.2")) == 403
        lines = relay.lines()
        assert any("DENY-PEER" in ln for ln in lines)
        assert any(ln.strip() == "peers  : zzz-nomatch,localhost*" for ln in lines)
        assert any("set by relay_peer_prefixes" in ln for ln in lines)
    finally:
        relay.stop()
        srv.stop()


def test_tc076_a_real_relay_with_no_usable_entry_says_so_and_behaves_as_unset(tmp_path):
    # TC-076
    srv = Counting()
    relay = Relay(tmp_path, forward=srv.port, extra_env={"NF_RELAY_PEER_PREFIXES": "ab"})
    try:
        target = "http://127.0.0.1:%d/user-info" % srv.port
        lines = relay.lines()
        assert any("had no usable entry" in ln for ln in lines)
        assert any(ln.strip() == "peers  : cpn,gpn,bgm,lgn,localhost*" for ln in lines)
        assert status(relay.send(get(target), source="127.0.0.1")) != 403
        assert status(relay.send(get(target), source="127.0.0.2")) == 403
    finally:
        relay.stop()
        srv.stop()


def test_tc077_a_real_relay_names_what_it_dropped(tmp_path):
    # TC-077
    relay = Relay(tmp_path, extra_env={"NF_RELAY_PEER_PREFIXES": "25a-cpn, a.b"})
    try:
        lines = relay.lines()
        assert any(ln.strip() == "peers  : 25a-cpn,localhost*" for ln in lines)
        assert any("dropped 'a.b'" in ln for ln in lines)
    finally:
        relay.stop()


def test_tc064_tc065_tc068_setting_is_documented():
    # TC-064, TC-065, TC-068
    settings = (REPO_ROOT / "docs" / "SETTINGS.md").read_text(encoding="utf-8")
    adapter = (REPO_ROOT / "docs" / "SITE_ADAPTER.md").read_text(encoding="utf-8")
    travels = next(ln for ln in settings.splitlines() if ln.startswith("| **Travels**"))
    assert "relay_peer_prefixes" in travels
    for needle in ("relay_peer_prefixes", "25a-cpn", "replaces", "egress_ctl.sh restart"):
        assert needle in settings, needle
    nano4_row = next(ln for ln in adapter.splitlines() if ln.startswith("| nano4 |"))
    assert "no relay" in nano4_row
    assert "never been run on nano4" in adapter
