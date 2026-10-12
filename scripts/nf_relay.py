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


# ---- the one loopback door (specs/007b-launch, FR-005) ---------------------------------------------------------------
# Feature 007b needs a Nextflow head job on a compute node to report to the platform on the user's laptop. The laptop's
# shared ssh connection carries a reverse forward, but this site's sshd binds it to the login node's loopback only, so only a
# process ON the login node can reach it - this relay. The door is as narrow as it can be made:
#   - plain HTTP in absolute form only (never CONNECT), to exactly 127.0.0.1:<the port in the forward file>;
#   - the port is read from the file (NF_RELAY_FORWARD_FILE, else $NF_RELAY_STATE_DIR/forward_port, else
#     $LAB_RUNS_DIR/_relay/forward_port) for EVERY request, and any doubt about the file means no;
#   - only the paths /trace/... and /user-info (the query string is not a path);
#   - one request per connection: the relay closes both ends after the answer;
#   - before a request is passed on, the port is asked (no token) who answers; only the platform whose instance id is on file
#     (forward_instance, beside forward_port) gets it, so a stale port taken by another user never sees a run token.
# Every other spelling of loopback is refused here and never reaches the domain code below.
_LOOPBACKISH = re.compile(r"^(?:[^@/]*@)?(?:127\.|0x7f|0177|2130706433(?:$|:)|localhost|0\.0\.0\.0|\[|::|0:)", re.I)
_FORWARD_TARGET = re.compile(r"^127\.0\.0\.1:([0-9]{1,5})\Z")
_SAFE_PATH = re.compile(r"^[A-Za-z0-9._~/-]+\Z")
LOOPBACK_METHODS = ("GET", "POST", "PUT")
LOOPBACK_BODY_LIMIT = 8 * 1024 * 1024
_DROP_HEADERS = ("connection", "proxy-connection", "keep-alive", "upgrade", "http2-settings", "te", "expect", "trailer")


def pass_answer(up, c):
    """Pass one answer from the platform on: as long as its Content-Length says, else until the platform closes (it was
    told to). A server that ignores 'Connection: close' and keeps its end open does not keep the client's end open."""
    head = b""
    while b"\r\n\r\n" not in head and len(head) < 65536:
        data = up.recv(65536)
        if not data:
            break
        head += data
    c.sendall(head)
    header, sep, rest = head.partition(b"\r\n\r\n")
    length = re.search(rb"(?im)^content-length:[ \t]*([0-9]{1,9})[ \t]*$", header.replace(b"\r", b""))
    if sep and length:
        remaining = int(length.group(1)) - len(rest)
        while remaining > 0:
            data = up.recv(min(65536, remaining))
            if not data:
                break
            c.sendall(data)
            remaining -= len(data)
        return
    while True:
        data = up.recv(65536)
        if not data:
            break
        c.sendall(data)


def forward_instance():
    """The instance id of the platform the forward is for (written next to the port file by the agent), or None."""
    path = forward_file()
    if not path:
        return None
    try:
        with open(os.path.join(os.path.dirname(path), "forward_instance"), "rb") as f:
            raw = f.read(80)
    except OSError:
        return None
    m = re.fullmatch(rb"([A-Za-z0-9._-]{8,64})\n?", raw)
    return m.group(1).decode("ascii") if m else None


def platform_answers_at(port, want):
    """True only if what listens on 127.0.0.1:<port> is the platform the forward was made for.

    When the shared connection ends, its forwarded port is free again and any other user of this login node can listen on it.
    So before a request that carries a run token is passed on, one request with no token asks the port who it is: the answer
    must be a 401 whose X-ABF-Platform header is exactly the instance id on file. Anything else, a silence included, is no.
    """
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=3)
    except OSError:
        return False
    try:
        s.settimeout(3)
        s.sendall(b"GET /user-info HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nConnection: close\r\nX-ABF-Probe: 1\r\n\r\n" % port)
        got = b""
        while b"\r\n\r\n" not in got and len(got) < 16384:
            data = s.recv(4096)
            if not data:
                break
            got += data
    except OSError:
        return False
    finally:
        s.close()
    head = got.partition(b"\r\n\r\n")[0].replace(b"\r", b"")
    lines = head.split(b"\n")
    if not lines or not re.match(rb"HTTP/1\.[01] 401( |$)", lines[0]):
        return False
    marks = [ln.split(b":", 1)[1].strip() for ln in lines[1:] if ln.lower().startswith(b"x-abf-platform:")]
    return len(marks) == 1 and marks[0] == want.encode("ascii")


def forward_file():
    explicit = os.environ.get("NF_RELAY_FORWARD_FILE")
    if explicit:
        return explicit
    state = os.environ.get("NF_RELAY_STATE_DIR")
    if not state and os.environ.get("LAB_RUNS_DIR"):
        state = os.path.join(os.environ["LAB_RUNS_DIR"], "_relay")
    return os.path.join(state, "forward_port") if state else None


def forward_port():
    """The port of the reverse forward, or None when the file is missing, unreadable, malformed or out of range."""
    path = forward_file()
    if not path:
        return None
    try:
        with open(path, "rb") as f:
            raw = f.read(64)
    except OSError:
        return None
    m = re.fullmatch(rb"([1-9][0-9]{3,4})\n?", raw)
    if not m:
        return None
    port = int(m.group(1))
    return port if 1024 <= port <= 65535 and port != PORT else None


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
        if _LOOPBACKISH.match(hostport):
            self.forward_loopback(c, parts, buf, peer_name, hostport, "/" + path)
            return
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

    def forward_loopback(self, c, parts, buf, peer_name, hostport, target):
        """One plain-HTTP request to the reverse forward, if and only if every condition of the door holds."""
        def deny(why, code=b"403 Forbidden"):
            c.sendall(b"HTTP/1.1 " + code + b"\r\n\r\n")
            log("DENY-LOOPBACK", _clean(hostport, 60), why, "from", peer_name)

        m = _FORWARD_TARGET.match(hostport)
        port = forward_port()
        if not m or port is None or m.group(1) != str(port):
            return deny("not the forward port")
        if parts[0].upper() not in LOOPBACK_METHODS:
            return deny("method", b"405 Method Not Allowed")
        path = re.split(r"[?#]", target, 1)[0]
        if not (path == "/user-info" or (path.startswith("/trace/") and len(path) > 7)) or not _SAFE_PATH.match(path) \
                or "//" in path or any(seg in (".", "..") for seg in path.split("/")):
            return deny("path " + _clean(path, 60))
        want = forward_instance()
        if want is None or not platform_answers_at(port, want):
            return deny("the port is not answered by the platform it was made for")
        head, _, tail = buf.partition(b"\r\n\r\n")
        lines = head.split(b"\r\n")[1:]
        kept, length = [], 0
        for ln in lines:
            name, sep, value = ln.partition(b":")
            lname = name.strip().lower().decode("latin-1")
            if not sep or not lname:
                return deny("malformed header", b"400 Bad Request")
            if lname == "transfer-encoding":
                return deny("chunked body", b"411 Length Required")
            if lname == "content-length":
                if not re.fullmatch(rb"[0-9]{1,8}", value.strip()):
                    return deny("content-length", b"400 Bad Request")
                length = int(value.strip())
            if lname in _DROP_HEADERS:
                continue
            kept.append(ln)
        if length > LOOPBACK_BODY_LIMIT:
            return deny("body too large", b"413 Payload Too Large")
        body = tail
        while len(body) < length:
            chunk = c.recv(65536)
            if not chunk:
                return deny("short body", b"400 Bad Request")
            body += chunk
        body = body[:length]          # whatever follows the body is not another request
        try:
            up = socket.create_connection(("127.0.0.1", port), timeout=5)
        except OSError as e:
            c.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            log("FAIL", "127.0.0.1", port, "from", peer_name, repr(e))
            return
        up.settimeout(60)
        request = ("%s %s HTTP/1.1" % (parts[0].upper(), target)).encode("latin-1") + b"\r\n" \
            + b"".join(k + b"\r\n" for k in kept) + b"Connection: close\r\n\r\n" + body
        log("OPEN-HTTP", "127.0.0.1", port, "from", peer_name)
        try:
            up.sendall(request)
            pass_answer(up, c)
        except OSError:
            pass
        finally:
            for sk in (up, c):
                try:
                    sk.close()
                except OSError:
                    pass
        log("CLOSE-HTTP", "127.0.0.1", port, "from", peer_name)

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
