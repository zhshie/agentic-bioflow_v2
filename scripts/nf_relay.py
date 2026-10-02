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
# Not tinyproxy/squid/socat: none is installed here, and swapping one in would
# still mean rebuilding the two checks above by hand - reverse-DNS-is-a-
# compute-node and the domain allowlist - since neither is a stock feature.
import ipaddress
import os
import re
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
    # nf-core/funcscan reference databases, found by scripts/check_egress.py
    # before the first launch rather than by watching a task fail. CARD is
    # hardcoded in the pipeline's own subworkflow, the two AMP databases are
    # selected by --amp_ampcombi_db_id. dbCAN and the DeepARG Zenodo archive
    # need nothing new: they sit on amazonaws.com and zenodo.org.
    "card.mcmaster.ca",           # RGI / CARD, fetched unconditionally by arg.nf
    "aps.unmc.edu",               # APD3, what -profile test selects
    "dramp.cpu-bioinfor.org",     # DRAMP, the default outside the test profile
    # BUSCO downloads its lineage datasets from a host that appears nowhere in
    # nf-core/bacass - the URL lives inside the BUSCO tool. No static scan can
    # find this one; the relay's own DENY log named it on the first run, which
    # is what that log is for.
    "ezlab.org",                  # busco-data.ezlab.org, busco-data2.ezlab.org
    # 2026-09-19, nf-core/ampliseq with its default --dada_ref_taxonomy
    # (sbdi-gtdb): the URL is on ndownloader.figshare.com, already allowed,
    # but figshare answers with a redirect to a presigned URL on KTH's S3.
    # The target exists only at run time, so check_egress.py cannot see it;
    # the relay log showed 8 DENY-DOMAIN for it as every RENAME_RAW_DATA_FILES
    # task aborted. The one host only, not kth.se.
    "presigned.s3.cloud.kth.se",
)

# This deployment's own additions (specs/002-relay-allowlist). The list above
# is plugin code, so before this a new pipeline's new host needed the
# maintainer. A member adds one with scripts/egress_allow.sh, which keeps it in
# their own settings root; scripts/on_site.sh carries the comma list here as
# NF_RELAY_EXTRA_DOMAINS, and NF_RELAY_EXTRA_NOTE when the list could not be
# read in full.
#
# Validated again here rather than trusted: this is an environment variable,
# and anything that can set one can set it to anything. A bare "com" or "*"
# would open the relay to everything below it. Same rule as egress_allow.sh -
# at least two labels, each 1-63 characters, no leading/trailing hyphen, and a
# final label of letters only, which is what rules out every IPv4 literal.
_DOMAIN_RE = re.compile(r"^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_EMBEDDED_IP_RE = re.compile(r"(^|\.)[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(\.|$)")
EXTRA_LIMIT = 100


def _clean(text, limit=120):
    """Printable ASCII on one line, for anything an environment variable can put
    in the log: a newline would start a log line of its own and an escape
    character would colour or rewrite the terminal reading it (#45)."""
    out = "".join(c if (c.isascii() and c.isprintable()) else "?" for c in str(text))
    return out if len(out) <= limit else out[: limit - 3] + "..."


# scripts/relay_denied_names.txt, the same file scripts/egress_allow.sh reads, so
# the two cannot disagree about what is not "a specific domain" (#45). None
# means it could not be read: then no extra domain is loaded at all (a list that
# cannot be checked is not a list that refuses nothing).
def _load_denied_names():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relay_denied_names.txt")
    exact, tree = set(), []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[0] == "exact":
                    exact.add(parts[1].lower())
                elif len(parts) >= 2 and parts[0] == "tree":
                    tree.append(parts[1].lower())
    except OSError:
        return None
    return exact, tuple(tree)


_DENIED = _load_denied_names()


def _policy_refusal(d):
    """-> a reason when d is well formed but not one host you can name, else ''."""
    if _EMBEDDED_IP_RE.search(d):
        return "it spells an IP address in its labels"
    exact, tree = _DENIED
    if d in exact:
        return f"it is a shared or local-only name ({d}), not one host"
    for name in tree:
        if d == name or d.endswith("." + name):
            return f"it is under {name}, a wildcard-DNS, tunnel or local-only name"
    return ""


def _parse_extra(raw):
    """-> (accepted domains, [why each other entry was dropped])"""
    good, dropped = [], []
    if _DENIED is None and raw.strip():
        return (), ["dropped every entry - relay_denied_names.txt cannot be read, so none can be checked"]
    for item in raw.split(","):
        shown = _clean(item.strip(), 80)
        if not item.strip().isascii():
            # str.lower() folds U+212A (Kelvin sign) to an ASCII k, which the
            # bash validator does not: anything not ASCII is not a domain here.
            dropped.append(f"dropped '{shown}' - not a specific domain name")
            continue
        d = item.strip().lower()
        if d.endswith("."):
            d = d[:-1]
        if not d:
            continue
        if not _DOMAIN_RE.match(d) or len(d) > 253:
            dropped.append(f"dropped '{shown}' - not a specific domain name")
            continue
        why = _policy_refusal(d)
        if why:
            dropped.append(f"dropped '{shown}' - {why}")
        elif d in good:
            continue
        elif len(good) >= EXTRA_LIMIT:
            dropped.append(f"dropped '{d}' - over the limit of {EXTRA_LIMIT} entries")
        else:
            good.append(d)
    return tuple(good), dropped


EXTRA_DOMAINS, EXTRA_DROPPED = _parse_extra(os.environ.get("NF_RELAY_EXTRA_DOMAINS", ""))
EXTRA_NOTE = _clean(" ".join(os.environ.get("NF_RELAY_EXTRA_NOTE", "").split()), 500)
_ALL_DOMAINS = ALLOW_DOMAINS + EXTRA_DOMAINS


def _in(h, names):
    return any(h == d or h.endswith("." + d) for d in names)


def _extra_only(host):
    """True when this host is allowed only by this deployment's own list."""
    h = host.lower().rstrip(".")
    return _in(h, EXTRA_DOMAINS) and not _in(h, ALLOW_DOMAINS)


def _addr_global(ip):
    """Is this resolved address a public one? Loopback, private, link-local,
    unspecified, multicast and the shared 100.64/10 range are not."""
    try:
        a = ipaddress.ip_address(str(ip).split("%")[0])
        if getattr(a, "ipv4_mapped", None) is not None:
            a = a.ipv4_mapped
        return a.is_global
    except ValueError:
        return False

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
    return any(h == d or h.endswith("." + d) for d in _ALL_DOMAINS)


def startup_lines():
    """What the relay says about itself when it starts - and, for this
    deployment's list, what it did NOT load and why. A list that failed to load
    must be said out loud (constitution invariant 13): the alternative is a
    run that fails later on a DENY the member believes they already fixed."""
    lines = [
        f"nf-relay on 0.0.0.0:{PORT}",
        f"  peers  : {','.join(ALLOW_HOST_PREFIXES)}*",
        f"  domains (built in): {','.join(ALLOW_DOMAINS)}",
    ]
    if EXTRA_DOMAINS:
        lines.append(f"  domains (this deployment): {','.join(EXTRA_DOMAINS)}")
        if EXTRA_NOTE:
            lines.append(f"  this deployment's list only partly loaded: {EXTRA_NOTE}")
    elif EXTRA_NOTE:
        lines.append(f"  this deployment's list not loaded: {EXTRA_NOTE}")
    else:
        lines.append("  domains (this deployment): (none)")
    lines.extend(f"  this deployment's list: {why}" for why in EXTRA_DROPPED)
    return lines


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


# Resolution is cached because a fan-out pipeline asks about the same few hosts
# from every task at once, and this node's resolver drops the odd UDP query
# under that load: resolving eutils.ncbi.nlm.nih.gov thirty times in a row
# succeeds, but during nf-core/fetchngs two of sixty-one connections failed
# with gaierror and became 502s. Retrying helped and did not eliminate it;
# asking once per host does.
_DNS_CACHE = {}
_DNS_TTL = 300


def resolve(host, port):
    key = (host, port)
    hit = _DNS_CACHE.get(key)
    if hit and time.time() - hit[0] < _DNS_TTL:
        return hit[1]
    infos = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
    _DNS_CACHE[key] = (time.time(), infos)
    return infos


def connect_upstream(host, port):
    """Connect, trying every address the name resolves to.

    Keeps create_connection's fallback behaviour, which matters here: several
    NCBI names return an IPv6 address first and this cluster has no IPv6 route,
    so pinning the first address would break them.
    """
    err = None
    # A name this deployment added itself (not one of the built-in list) is
    # connected to only when it resolves to a public address: the relay checked
    # neither the resolved address nor the port, so an approved name that
    # resolves to loopback or an internal address reached any port there (#45).
    extra_only = _extra_only(host)
    for attempt in (1, 2, 3):
        try:
            infos = resolve(host, port)
            blocked = 0
            for family, socktype, proto, _, sockaddr in infos:
                if extra_only and not _addr_global(sockaddr[0]):
                    blocked += 1
                    err = PermissionError(
                        f"{host} resolves to {sockaddr[0]}, not a public address; "
                        "this deployment's extra domains may only reach public ones")
                    continue
                try:
                    s = socket.socket(family, socktype, proto)
                    s.settimeout(20)
                    s.connect(sockaddr)
                    return s, None
                except Exception as e:
                    err = e
                    try:
                        s.close()
                    except Exception:
                        pass
            if infos and blocked == len(infos):
                # Every address it resolves to was refused: no point retrying.
                log("DENY-PRIVATE", host, port, repr(str(err)))
                return None, err
        except Exception as e:      # resolution itself failed
            err = e
            _DNS_CACHE.pop((host, port), None)
        if attempt < 3:
            time.sleep(0.3 * attempt)
    return None, err


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
            up, err = connect_upstream(host, port)
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

        up, err = connect_upstream(host, port)
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
    for line in startup_lines():
        log(line)
    Server(("0.0.0.0", PORT), Handler).serve_forever()
