# Not nf-shard: it ships no command line at all; this one starts the receiver, issues tokens, runs the MCP server and rebuilds the index.
"""abf-platform: serve | token new | mcp [--http] | rebuild <launch folder>..."""
import argparse
import sys

from . import rebuild as rebuild_mod
from . import store

LOOPBACK = ("127.0.0.1", "localhost", "::1")


def _say(text):
    print(text, flush=True)


def _risk_line(what, host, port):
    _say("WARNING: %s listens on %s:%s, so it is reachable from other machines on the network. "
         "Anyone who can reach this port can try tokens against it; put it behind a firewall or a TLS proxy." % (what, host, port))


def cmd_serve(args):
    import uvicorn
    from .receiver import create_app

    index = store.default_index_path()
    tokens = store.default_tokens_path(index)
    app = create_app(index, tokens)
    _say("abf-platform receiver on http://%s:%s (index %s, tokens %s)" % (args.host, args.port, index, tokens))
    if args.host not in LOOPBACK:
        _risk_line("the receiver", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def cmd_token_new(args):
    tokens = store.default_tokens_path()
    token = store.create_token(tokens)
    _say("New token (it is shown once and cannot be shown again; only its hash is kept):")
    _say(token)
    _say("Give it to Nextflow as TOWER_ACCESS_TOKEN, with tower.endpoint set to this receiver.")
    return 0


def cmd_mcp(args):
    from . import mcp_server

    index = store.default_index_path()
    if args.http:
        if args.host not in LOOPBACK:
            _risk_line("the MCP server", args.host, args.port)
        mcp_server.run_http(index, args.host, args.port)
    else:
        mcp_server.run_stdio(index)
    return 0


def cmd_rebuild(args):
    index = store.default_index_path()
    result = rebuild_mod.rebuild(args.folders, index, out=_say)
    _say("Rebuilt %d run(s) from %d launch folder(s); skipped %d folder(s)." % (
        result.runs, result.folders, len(result.skipped)))
    return 1 if result.skipped else 0


def build_parser():
    p = argparse.ArgumentParser(prog="abf-platform", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("serve", help="run the receiver for Nextflow's trace messages")
    s.add_argument("--host", default="127.0.0.1", help="address to listen on (default: 127.0.0.1, this machine only)")
    s.add_argument("--port", type=int, default=8787)
    s.set_defaults(func=cmd_serve)

    t = sub.add_parser("token", help="manage access tokens")
    tsub = t.add_subparsers(dest="token_command", required=True)
    tn = tsub.add_parser("new", help="issue a token and show it once")
    tn.set_defaults(func=cmd_token_new)

    m = sub.add_parser("mcp", help="run the read-only MCP server (stdio, or --http)")
    m.add_argument("--http", action="store_true", help="Streamable HTTP instead of stdio")
    m.add_argument("--host", default="127.0.0.1")
    m.add_argument("--port", type=int, default=8788)
    m.set_defaults(func=cmd_mcp)

    r = sub.add_parser("rebuild", help="drop the index and build it again from Nextflow's records")
    r.add_argument("folders", nargs="+", help="launch folders (the ones holding .nextflow/ and .nextflow.log)")
    r.set_defaults(func=cmd_rebuild)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)
