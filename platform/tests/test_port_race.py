# Nothing existing: regression test for the free_port() time-of-check/time-of-use race (test-port-race); no library covers our own helper.
"""test-port-race: two test servers asking for a port at once must never get the same one."""
import http.server
import threading
import urllib.request

import helpers


def _forced_candidates(monkeypatch, first_port, count):
    """The OS hands out first_port `count` times (two shards racing), then real ports again."""
    real = helpers._candidate_port
    seq = [first_port] * count

    def fake():
        return seq.pop(0) if seq else real()

    monkeypatch.setattr(helpers, "_candidate_port", fake)


def _serve(port, name):
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = name.encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_tc001_same_candidate_yields_two_different_ports(monkeypatch):
    # TC-001
    first = helpers._candidate_port()
    _forced_candidates(monkeypatch, first, 2)
    a = helpers.free_port()
    b = helpers.free_port()
    assert a == first
    assert a != b


def test_tc002_each_test_talks_to_its_own_server(monkeypatch):
    # TC-002
    first = helpers._candidate_port()
    _forced_candidates(monkeypatch, first, 2)
    a = helpers.free_port()
    b = helpers.free_port()
    sa, sb = _serve(a, "server-a"), _serve(b, "server-b")
    try:
        assert urllib.request.urlopen("http://127.0.0.1:%d/" % a, timeout=5).read() == b"server-a"
        assert urllib.request.urlopen("http://127.0.0.1:%d/" % b, timeout=5).read() == b"server-b"
    finally:
        sa.shutdown(); sb.shutdown(); sa.server_close(); sb.server_close()
