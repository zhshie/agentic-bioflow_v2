#!/usr/bin/env python3
"""Both CONNECT shapes a real client sends. The no-header form is what
Python's http.client._tunnel() emits and what used to hang the relay."""
import socket, sys
HOST, PORT = sys.argv[1], int(sys.argv[2])
CASES = [
    ("no headers (python urllib)", b"CONNECT www.ebi.ac.uk:443 HTTP/1.0\r\n\r\n"),
    ("with Host   (curl/singularity)",
     b"CONNECT www.ebi.ac.uk:443 HTTP/1.1\r\nHost: www.ebi.ac.uk:443\r\n\r\n"),
    ("split across segments", None),
    ("denied domain", b"CONNECT evil.example.com:443 HTTP/1.0\r\n\r\n"),
]
for name, payload in CASES:
    try:
        s = socket.create_connection((HOST, PORT), timeout=25); s.settimeout(25)
        if payload is None:
            s.sendall(b"CONNECT www.ebi.ac.uk:443 HTTP/1.1\r\n"); s.sendall(b"Host: x\r\n"); s.sendall(b"\r\n")
        else:
            s.sendall(payload)
        print(f"  {name:32s} -> {s.recv(60)!r}")
        s.close()
    except Exception as e:
        print(f"  {name:32s} -> FAILED {type(e).__name__}: {e}")
