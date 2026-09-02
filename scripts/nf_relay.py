#!/usr/bin/env python3
"""HTTPS CONNECT relay for the login node.

Compute nodes here have no outbound network but reach the login node freely
(verified job 2008057, 2026-09-02). Nextflow head and task jobs point at this
via https_proxy so they can reach Seqera, quay.io and friends.

Two independent restrictions, because an open relay on a shared login node
would be a real problem:
  - WHO may connect: the peer's reverse-resolved hostname must be a compute
    node (or this login node itself). Checked by hostname, not subnet, because
    login and compute nodes share 172.16/12 here.
  - WHERE they may connect to: an explicit domain allowlist.

Stdlib only - this login node has no tinyproxy/squid/socat.
"""
import select
import socket
import socketserver
import sys
import threading
import time

# Domains the relay will tunnel to.
ALLOW_DOMAINS = (
    # Seqera Platform + Co-Scientist backend
    "seqera.io",
    # Nextflow itself: plugin registry (nf-validation, nf-tower...) and version check.
    # Missing this makes every run die at plugin resolution with a misleading
    # "Conversion = '4'" - pf4j's error formatter chokes on the 403 body.
    "nextflow.io",
    # Pipeline source and test data
    "github.com",
    "githubusercontent.com",
    # Containers
    "quay.io",
    "docker.io",
    "docker.com",
    "ghcr.io",
    # Reference/test data hosts
    "amazonaws.com",
    "googleapis.com",
    "ebi.ac.uk",
    # nf-core's default Singularity image host, plus common reference/data hosts.
    # Missing depot.galaxyproject.org fails every container pull.
    "galaxyproject.org",
    "zenodo.org",
    "figshare.com",
    "ensembl.org",
    "broadinstitute.org",
    "cloudflare.com",
    "cloudflarestorage.com",
)

# Hostname prefixes permitted to use the relay. From `sinfo -N`: compute nodes
# are cpn*/cpna*/gpn*/gpna*/bgm*; lgn* is this node talking to itself.
ALLOW_HOST_PREFIXES = ("cpn", "gpn", "bgm", "lgn", "localhost")

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 18080
_lock = threading.Lock()


def log(*a):
    with _lock:
        print(time.strftime("%H:%M:%S"), *a, flush=True)


def domain_ok(host):
    h = host.lower().rstrip(".")
    # Match on a label boundary: a bare endswith would also accept
    # "evilquay.io" for the "quay.io" entry.
    return any(h == d or h.endswith("." + d) for d in ALLOW_DOMAINS)


def peer_ok(ip):
    try:
        name = socket.gethostbyaddr(ip)[0].lower()
    except Exception:
        # No reverse record means we cannot tell who this is. Refuse rather
        # than fall back to a subnet check - login and compute nodes share
        # 172.16/12 here, so a subnet check would not narrow anything.
        return False, "<no-rdns>"
    return name.startswith(ALLOW_HOST_PREFIXES), name


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        c = self.request
        c.settimeout(20)
        peer = self.client_address[0]
        try:
            ok, peer_name = peer_ok(peer)
            if not ok:
                c.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
                log("DENY-PEER", peer, peer_name)
                return

            line = b""
            while b"\r\n" not in line and len(line) < 8192:
                b = c.recv(1)
                if not b:
                    return
                line += b
            parts = line.decode("latin-1").strip().split()
            if len(parts) < 2 or parts[0].upper() != "CONNECT":
                c.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
                log("REJECT non-CONNECT from", peer_name, parts[:2])
                return
            host, _, port = parts[1].rpartition(":")
            port = int(port or 443)

            while True:
                chunk = c.recv(4096)
                if not chunk or b"\r\n\r\n" in chunk:
                    break

            if not domain_ok(host):
                c.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
                log("DENY-DOMAIN", host, port, "from", peer_name)
                return

            try:
                up = socket.create_connection((host, port), timeout=20)
            except Exception as e:
                c.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                log("FAIL", host, port, "from", peer_name, repr(e))
                return

            c.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            log("OPEN", host, port, "from", peer_name)
            self.pump(c, up)
            log("CLOSE", host, port, "from", peer_name)
        except Exception as e:
            log("ERROR", peer, repr(e))

    @staticmethod
    def pump(a, b):
        a.settimeout(None)
        b.settimeout(None)
        try:
            while True:
                r, _, x = select.select([a, b], [], [a, b], 3600)
                if x or not r:
                    break
                for s in r:
                    data = s.recv(65536)
                    if not data:
                        return
                    (b if s is a else a).sendall(data)
        except Exception:
            pass
        finally:
            for s in (a, b):
                try:
                    s.close()
                except Exception:
                    pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    log(f"nf-relay on 0.0.0.0:{PORT}")
    log(f"  peers  : {','.join(ALLOW_HOST_PREFIXES)}*")
    log(f"  domains: {','.join(ALLOW_DOMAINS)}")
    Server(("0.0.0.0", PORT), Handler).serve_forever()
