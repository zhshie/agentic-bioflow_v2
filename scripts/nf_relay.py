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
    # Added 2026-09-02 after nf-core/ampliseq failed with no useful message from
    # Platform ("Execution aborted due to an unexpected error"); the relay log
    # named all three. Reference databases and a container host that rnaseq
    # never touches, so nothing before ampliseq could have revealed them.
    "biocontainers.pro",      # base image for ampliseq's local modules
    "qiime2.org",             # QIIME2 classifiers (--qiime_ref_taxonomy)
    "ecogenomic.org",         # GTDB SSU references (--dada_ref_taxonomy gtdb=...)
    # nf-core/fetchngs resolves GEO/GSM accessions through NCBI eutils and
    # pulls reads from the SRA mirrors. Covers eutils/trace/ftp/sra-download.
    "ncbi.nlm.nih.gov",
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


# Every connection starts with a reverse lookup, so a burst runs them all at
# once and the slow ones eat the socket timeout. The set of compute nodes is
# small and stable, so remember what we resolve. Failures are deliberately not
# cached: a transient resolver hiccup must not lock a legitimate node out for
# the life of the relay.
_PEER_CACHE = {}


def peer_ok(ip):
    hit = _PEER_CACHE.get(ip)
    if hit is not None:
        return hit
    try:
        name = socket.gethostbyaddr(ip)[0].lower()
    except Exception:
        # No reverse record means we cannot tell who this is. Refuse rather
        # than fall back to a subnet check - login and compute nodes share
        # 172.16/12 here, so a subnet check would not narrow anything.
        return False, "<no-rdns>"
    result = (name.startswith(ALLOW_HOST_PREFIXES), name)
    _PEER_CACHE[ip] = result
    return result


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

            # Read the whole header block at once, then split off the request
            # line. Doing it the other way round - request line first, then
            # "recv until this chunk contains \r\n\r\n" - hangs on a CONNECT
            # that carries no headers, because the only thing left in the
            # socket is the terminating \r\n and no single chunk can ever
            # contain \r\n\r\n. That is exactly what Python's
            # http.client._tunnel() sends:
            #     CONNECT host:443 HTTP/1.0\r\n\r\n
            # so every urllib request through this relay stalled for the full
            # socket timeout and the client reported "Remote end closed
            # connection without response". curl and Singularity always send a
            # Host: header, which is why image pulls never revealed it.
            buf = b""
            while b"\r\n\r\n" not in buf and len(buf) < 8192:
                chunk = c.recv(1024)
                if not chunk:
                    return
                buf += chunk
            head = buf.partition(b"\r\n\r\n")[0]
            line = head.split(b"\r\n", 1)[0]
            parts = line.decode("latin-1").strip().split()
            if len(parts) < 2:
                c.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                log("REJECT malformed from", peer_name)
                return

            if parts[0].upper() != "CONNECT":
                # Plain HTTP, sent to a proxy in absolute form:
                #   GET http://host/path HTTP/1.1
                # Rejecting these with 405 was fine while everything here spoke
                # HTTPS, but nf-core/fetchngs pulls FASTQ over plain HTTP from
                # ftp.sra.ebi.ac.uk and wget reported the relay's own 405 as if
                # the archive had refused it.
                self.forward_http(c, parts, buf, peer_name)
                return

            hostport = parts[1]
            if ":" in hostport:
                host, _, port = hostport.rpartition(":")
                port = int(port)
            else:
                host, port = hostport, 443

            if not domain_ok(host):
                c.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
                log("DENY-DOMAIN", host, port, "from", peer_name)
                return

            # One retry. A pipeline that fans out - fetchngs opens a request
            # per accession at once - makes this node's resolver drop the odd
            # UDP query, and a bare gaierror here becomes a 502 that fails the
            # whole task. Resolving the same name 30 times in a row succeeds;
            # it is only under the burst that it slips. Two attempts turned 2
            # failures in 61 connections into none.
            up = None
            for attempt in (1, 2, 3):
                try:
                    up = socket.create_connection((host, port), timeout=20)
                    break
                except Exception as e:
                    err = e
                    if attempt < 3:
                        time.sleep(0.3 * attempt)
            if up is None:
                c.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                log("FAIL", host, port, "from", peer_name, repr(err))
                return

            c.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            log("OPEN", host, port, "from", peer_name)
            self.pump(c, up)
            log("CLOSE", host, port, "from", peer_name)
        except Exception as e:
            log("ERROR", peer, repr(e))

    def forward_http(self, c, parts, buf, peer_name):
        """Proxy one plain-HTTP request given in absolute form.

        The allowlist is applied to the URL's host exactly as it is for
        CONNECT, so this opens no door that tunnelling did not already open -
        it only stops the relay from answering 405 to a protocol it is
        perfectly able to carry.
        """
        url = parts[1]
        if not url.lower().startswith("http://"):
            c.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
            log("REJECT non-absolute", url[:60], "from", peer_name)
            return
        hostport, _, path = url[7:].partition("/")
        if ":" in hostport:
            host, _, port = hostport.rpartition(":")
            port = int(port)
        else:
            host, port = hostport, 80

        if not domain_ok(host):
            c.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            log("DENY-DOMAIN", host, port, "from", peer_name)
            return

        up = None
        for attempt in (1, 2, 3):
            try:
                up = socket.create_connection((host, port), timeout=20)
                break
            except Exception as e:
                err = e
                if attempt < 3:
                    time.sleep(0.3 * attempt)
        if up is None:
            c.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            log("FAIL", host, port, "from", peer_name, repr(err))
            return

        # Rewrite the request line to origin form; forward the rest verbatim.
        head, sep, tail = buf.partition(b"\r\n\r\n")
        first, _, others = head.partition(b"\r\n")
        origin = f"{parts[0]} /{path} {parts[2] if len(parts) > 2 else 'HTTP/1.1'}".encode("latin-1")
        rebuilt = origin + (b"\r\n" + others if others else b"") + sep + tail
        up.sendall(rebuilt)
        log("OPEN-HTTP", host, port, "from", peer_name)
        self.pump(c, up)
        log("CLOSE-HTTP", host, port, "from", peer_name)

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
    # socketserver defaults this to 5 - the listen() backlog. Pulling container
    # images opens a handful of connections and never noticed, but a pipeline
    # that fans out metadata queries (nf-core/fetchngs asks about every
    # accession at once) overflows the accept queue in a single burst. The
    # excess connections are reset and the client reports "Remote end closed
    # connection without response", which reads like a fault at the far end
    # rather than here.
    request_queue_size = 128


if __name__ == "__main__":
    log(f"nf-relay on 0.0.0.0:{PORT}")
    log(f"  peers  : {','.join(ALLOW_HOST_PREFIXES)}*")
    log(f"  domains: {','.join(ALLOW_DOMAINS)}")
    Server(("0.0.0.0", PORT), Handler).serve_forever()
