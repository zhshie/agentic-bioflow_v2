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


class Counting:
    """A server on 127.0.0.1 that answers every request with 'ok', keeps the connection open, and records what it saw."""

    def __init__(self, port=None):
        self.port = port or free_port()
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
                    self.requests.append((n, line))
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")   # and the connection stays open
        except OSError:
            pass
        finally:
            conn.close()

    def stop(self):
        self.stopped = True
        self.sock.close()


class Relay:
    def __init__(self, tmp, forward=None):
        self.port = free_port()
        self.forward_file = Path(tmp) / "forward_port"
        if forward is not None:
            self.forward_file.write_text(str(forward) + "\n")
        self.log = Path(tmp) / "relay.log"
        env = dict(os.environ, NF_RELAY_FORWARD_FILE=str(self.forward_file), NF_RELAY_EXTRA_DOMAINS="abf-golden.example.org",
                   PYTHONDONTWRITEBYTECODE="1")
        env.pop("NF_RELAY_STATE_DIR", None)
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
    others = {n: Counting(n) for n in (F + 1, 80, 22, 1, 65535) if n != relay.port}
    targets = ["http://127.0.0.1:%d/user-info" % n for n in others] + [
        "http://localhost:%d/user-info" % F, "http://[::1]:%d/user-info" % F, "http://127.0.0.2:%d/user-info" % F,
        "http://127.1:%d/user-info" % F, "http://0x7f.0.0.1:%d/user-info" % F, "http://2130706433:%d/user-info" % F,
        "http://0.0.0.0:%d/user-info" % F, "http://127.0.0.1.:%d/user-info" % F, "http://user@127.0.0.1:%d/user-info" % F,
        "http://127.0.0.1:%d@evil.example/user-info" % F, "http://127.0.0.1:" + str(F).translate({ord(c): ord(c) + 0xFEE0 for c in "0123456789"}) + "/user-info",
        "http://127.0.0.1:+%d/user-info" % F,
        "http://127.0.0.1:0%d/user-info" % F, "http://127.0.0.1: %d/user-info" % F, "http://127.0.0.1/user-info",
        "http://127.0.0.1:%d/user-info" % relay.port]
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
