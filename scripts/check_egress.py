#!/usr/bin/env python3
"""Which hosts will this pipeline reach for, and would the relay allow them?

The relay's allowlist is the one thing a new pipeline reliably needs added to,
and discovering that by watching a run fail costs a queue slot and a round of
diagnosis. This reads the pipeline's own config and bin/ scripts and reports
any host the relay would refuse.

Heuristic, not a guarantee: URLs assembled at runtime or supplied by the user
in params cannot be seen from here, and a pipeline only fetches the reference
databases its parameters actually select. A clean report means "nothing
obviously missing", never "this will not need the allowlist".

    check_egress.py nf-core/fetchngs 1.12.0 [path/to/nf_relay.py]
"""
import importlib.util, json, os, re, sys, urllib.request

URL = re.compile(r"https?://([A-Za-z0-9._-]+)")
# Citations live in comments all over nf-core sources. Reporting doi.org as a
# missing egress host trains the reader to skim past the real entries.
COMMENT = re.compile(r"^\s*(//|#|\*|/\*)|\s//\s")
# Hosts that appear as citations and homepages rather than as things a task
# fetches. Excluded so the real entries stand out - not because the relay would
# or should allow them.
CITATIONS = {
    "doi.org", "dx.doi.org", "stackoverflow.com", "nf-co.re",
    "www.nextflow.io", "creativecommons.org", "spdx.org",
}


def is_citation(host):
    return host in CITATIONS or host.endswith(".github.io")


def get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "check-egress"})
        return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    except Exception:
        return ""


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    repo, rev = sys.argv[1], sys.argv[2]
    relay_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "nf_relay.py")

    # nf_relay reads sys.argv at import time to choose its port.
    saved, sys.argv = sys.argv, sys.argv[:1]
    spec = importlib.util.spec_from_file_location("relay", relay_path)
    relay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(relay)
    sys.argv = saved

    paths = ["nextflow.config"]
    for d in ("conf", "bin"):
        listing = get(f"https://api.github.com/repos/{repo}/contents/{d}?ref={rev}")
        try:
            paths += [f"{d}/{e['name']}" for e in json.loads(listing) if e["type"] == "file"]
        except Exception:
            pass

    hosts, scanned = set(), 0
    for path in paths:
        text = get(f"https://raw.githubusercontent.com/{repo}/{rev}/{path}")
        if not text:
            continue
        scanned += 1
        for line in text.splitlines():
            if COMMENT.search(line):
                continue
            hosts.update(h for h in URL.findall(line) if "." in h)

    if scanned == 0:
        sys.exit(f"ERROR: fetched nothing for {repo}@{rev} - wrong name or revision?")

    missing = sorted(h for h in hosts
                     if not relay.domain_ok(h) and not is_citation(h))
    print(f"{repo}@{rev}: {scanned} files, {len(hosts)} distinct hosts")
    if missing:
        print(f"  {len(missing)} host(s) not in the allowlist. A pipeline only")
        print( "  fetches what its parameters select, so these may or may not")
        print( "  be needed for your run - add the ones that are:")
        for h in missing:
            print(f"    {h}")
        return 1
    print("  nothing obviously missing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
