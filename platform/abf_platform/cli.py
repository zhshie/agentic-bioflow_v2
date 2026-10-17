# Not nf-shard: it ships no command line at all; this one starts the receiver, issues tokens, manages compute environments, runs the MCP server and rebuilds the index.
"""abf-platform: serve | web | token new | agent-token new|revoke | user add|passwd | pat new|list|revoke | ce ... | mcp [--http] | rebuild [<launch folder>...] | the four commands of the hand-off record (see their own --help)"""
import argparse
import asyncio
import json
import re
import sys
import time

from . import agents, common, compute_envs, jobs, rebuild as rebuild_mod, records, store

LOOPBACK = ("127.0.0.1", "localhost", "::1")
_AGENT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")


def _say(text):
    print(text, flush=True)


def _err(text):
    print(text, file=sys.stderr, flush=True)


def _risk_line(what, host, port):
    _say("WARNING: %s listens on %s:%s, so it is reachable from other machines on the network. "
         "Anyone who can reach this port can try tokens against it; put it behind a firewall or a TLS proxy." % (what, host, port))


def cmd_serve(args):
    import uvicorn
    from .receiver import create_app

    index = store.default_index_path()
    tokens = store.default_tokens_path(index)
    state = store.default_platform_path(index)
    app = create_app(index, tokens, platform_path=state)
    _say("abf-platform receiver on http://%s:%s (index %s, tokens %s, platform %s)" % (
        args.host, args.port, index, tokens, state))
    if args.host not in LOOPBACK:
        _risk_line("the receiver", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def cmd_web(args):
    """The confirmation page, a process of its own (spec 009c): loopback by default, plain http, no bearer check (a browser has none)."""
    import uvicorn
    from . import web

    index = store.default_index_path()
    tokens = store.default_tokens_path(index)
    state = store.default_platform_path(index)
    shown = args.host if args.host not in ("0.0.0.0", "::") else "127.0.0.1"
    base = (args.public_url or "http://%s:%s" % (shown, args.port)).rstrip("/")
    store.set_meta(state, "web_base_url", base)    # the MCP server names this address in its answers
    app = web.create_app(index, tokens, state, public_url=args.public_url)
    _say("abf-platform confirmation page on http://%s:%s, named to people as %s (tokens %s, platform %s)" % (
        args.host, args.port, base, tokens, state))
    if args.host not in LOOPBACK:
        _risk_line("the confirmation page", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def cmd_token_new(args):
    tokens = store.default_tokens_path()
    token = store.create_token(tokens)
    _say("New token (it is shown once and cannot be shown again; only its hash is kept):")
    _say(token)
    _say("Give it to Nextflow as TOWER_ACCESS_TOKEN, with tower.endpoint set to this receiver.")
    return 0


def cmd_agent_token_new(args):
    if not _AGENT_NAME.match(args.name):
        _err("rejected: an agent name is letters, digits, _ . - (1 to 64 characters)")
        return 1
    token = store.create_token(store.default_tokens_path(), kind="agent", agent_name=args.name)
    _say("New agent token for %s (it is shown once and cannot be shown again; only its hash is kept):" % args.name)
    _say(token)
    _say("Put it in a file that only you can read (chmod 600) and start the agent with --token-file <that file>.")
    return 0


def cmd_user_add(args):
    try:
        store.create_user(store.default_tokens_path(), args.name, args.lab)
    except ValueError:
        _err("rejected: a user named %s already exists (這個名字已存在)" % args.name)
        return 1
    _say("added user %s (lab %s); issue a token with: abf-platform pat new --user %s" % (args.name, args.lab, args.name))
    return 0


def cmd_user_passwd(args):
    """Set a user's web password. The person types it, twice, on a real terminal: there is no flag, no file and no variable for it."""
    import getpass
    from abf_launch import terminal

    why = terminal.terminal_problem()
    if why:
        _err("rejected: 密碼只能在真正的終端機上由本人輸入，這裡不行（%s）(the password is typed at a real terminal, nothing else can give it)" % why)
        return 1
    tokens = store.default_tokens_path()
    if store.user_id_of(tokens, args.name) is None:
        _err("rejected: 沒有這個使用者 (no such user): %s; add one with: abf-platform user add" % args.name)
        return 1
    try:
        first = getpass.getpass("New web password for %s: " % args.name)
        second = getpass.getpass("Type it again: ")
    except (EOFError, KeyboardInterrupt):
        _err("\nrejected: nothing was entered, nothing was changed (沒有輸入，什麼都沒改)")
        return 1
    if first != second:
        _err("rejected: the two entries differ, nothing was changed (兩次輸入不一致，什麼都沒改)")
        return 1
    try:
        store.set_web_password(tokens, args.name, first)
    except ValueError as e:
        _err("rejected: %s" % e)
        return 1
    _say("web password of %s is set; every browser login of that user has ended (網頁密碼已設定，舊的登入全部結束)" % args.name)
    return 0


def cmd_pat_new(args):
    tokens = store.default_tokens_path()
    uid = store.user_id_of(tokens, args.user)
    if uid is None:
        _err("rejected: no such user: %s (沒有這個使用者); add one with: abf-platform user add" % args.user)
        return 1
    token = store.create_token(tokens, kind="pat", user_id=uid, label=args.label)
    _say("New personal access token for %s (it is shown once and cannot be shown again; only its hash is kept):" % args.user)
    _say(token)
    _say("Give it to the MCP client as the header Authorization: Bearer <token> when it connects to `abf-platform mcp --http`.")
    return 0


def cmd_pat_list(args):
    rows = store.list_pats(store.default_tokens_path())
    for r in rows:
        _say("id %s  user %s  label %s  created %s  %s" % (
            r["id"], r["user"], r["label"] or "-", time.strftime("%Y-%m-%d %H:%M", time.localtime(r["created_at"])),
            "revoked" if r["revoked_at"] else "not revoked"))
    if not rows:
        _say("no personal access tokens")
    return 0


def cmd_pat_revoke(args):
    n = store.revoke_pat(store.default_tokens_path(), args.id)
    if n:
        _say("revoked token %s; it is refused from its next request" % args.id)
        return 0
    _err("rejected: no live personal access token with id %s" % args.id)
    return 1


def cmd_agent_token_revoke(args):
    n = store.revoke_agent_tokens(store.default_tokens_path(), args.name)
    _say("revoked %d token(s) of agent %s; the agent is refused from its next request" % (n, args.name))
    return 0 if n else 1


# ---- compute environments ----------------------------------------------------------------------

def _parse_env(items):
    """--env [head:|compute:|both:]NAME=VALUE, the way Seqera's own command line writes it (head only is the default)."""
    out = []
    for item in items or []:
        where = "head"
        for prefix in ("head:", "compute:", "both:"):
            if item.startswith(prefix):
                where, item = prefix[:-1], item[len(prefix):]
                break
        name, eq, value = item.partition("=")
        if not eq:
            raise compute_envs.CEError("--env wants NAME=VALUE")
        out.append({"name": name, "value": value, "head": where in ("head", "both"), "compute": where in ("compute", "both")})
    return out


def _config_from_args(args):
    config = {}
    if args.config_json:
        text = args.config_json
        if text.startswith("@"):
            with open(text[1:], encoding="utf-8") as f:
                text = f.read()
        try:
            config = json.loads(text)
        except ValueError:
            raise compute_envs.CEError("--config-json is not valid JSON")
        if not isinstance(config, dict):
            raise compute_envs.CEError("--config-json must be a JSON object")
    flags = {"work_dir": "workDir", "launch_dir": "launchDir", "head_queue": "headQueue", "compute_queue": "computeQueue",
             "head_job_options": "headJobOptions", "host_name": "hostName", "user_name": "userName",
             "pre_run": "preRunScript", "post_run": "postRunScript", "nextflow_config": "nextflowConfig"}
    for attr, key in flags.items():
        if getattr(args, attr) is not None:
            config[key] = getattr(args, attr)
    for attr, key in (("max_queue_size", "maxQueueSize"), ("port", "port")):
        v = getattr(args, attr)
        if v is not None:
            try:
                config[key] = int(v)
            except ValueError:
                raise compute_envs.CEError("%s must be a whole number" % key)
    if args.env:
        config["environment"] = _parse_env(args.env)
    if args.read_root:
        config["readRoots"] = list(args.read_root)
    return config


def _fields_from_args(args, partial):
    fields = {}
    if not partial:
        fields["name"] = args.name
        fields["platform"] = args.platform
    for attr, key in (("description", "description"), ("credentials", "credentialsId"), ("agent", "agent")):
        if getattr(args, attr, None) is not None:
            fields[key] = getattr(args, attr)
    fields["config"] = _config_from_args(args)
    return fields


def _queue_first_preflight(state, ce):
    """Right after a create or update: queue a preflight when the environment's agent is online, else say why not."""
    if ce["platform"] != compute_envs.SUPPORTED:
        return ce["message"]
    try:
        jobs.enqueue_preflight(state, ce["name"])
        note = "preflight queued (預檢已排入); the status changes when the agent has answered"
    except jobs.JobRefused as e:
        if "offline" in str(e) or "no agent" in str(e) or "has no agent" in str(e):
            note = "沒有代理在線，尚未預檢 (no agent online, not checked yet): %s" % e
        else:
            note = str(e)
    compute_envs.set_message(state, ce["name"], note, only_status=compute_envs.CREATING)
    return note


def _default_agent(fields):
    """With no --agent, an environment goes to the only agent that has a live token."""
    if fields.get("agent"):
        return
    names = store.live_agent_names(store.default_tokens_path())
    if len(names) == 1:
        fields["agent"] = names[0]


def cmd_ce_create(args):
    state = store.default_platform_path()
    try:
        fields = _fields_from_args(args, partial=False)
        if fields.get("platform") == compute_envs.SUPPORTED:
            _default_agent(fields)
        ce = compute_envs.create(state, fields)
    except compute_envs.CEError as e:
        _err("rejected: %s" % e)
        return 1
    note = _queue_first_preflight(state, ce)
    _say("compute environment %s created (status %s)" % (ce["name"], ce["status"]))
    _say(note)
    return 0


def cmd_ce_update(args):
    state = store.default_platform_path()
    try:
        ce = compute_envs.update(state, args.name, _fields_from_args(args, partial=True))
    except compute_envs.CEError as e:
        _err("rejected: %s" % e)
        return 1
    _say("compute environment %s updated" % ce["name"])
    if ce["platform"] == compute_envs.SUPPORTED and ce["status"] != compute_envs.DISABLED:
        _say(_queue_first_preflight(state, ce))
    return 0


def cmd_ce_list(args):
    for ce in compute_envs.list_all(store.default_platform_path()):
        _say("%s%s  %s  %s  %s" % (ce["name"], " (primary)" if ce["primary"] else "", ce["platform"], ce["status"],
                                    ce["agent"] or "-"))
    return 0


def cmd_ce_show(args):
    ce = compute_envs.get(store.default_platform_path(), args.name)
    if ce is None:
        _err("compute environment %s not found (找不到)" % args.name)
        return 1
    _say(json.dumps(ce, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def _simple(fn):
    def run(args):
        try:
            ce = fn(store.default_platform_path(), args.name)
        except compute_envs.CEError as e:
            _err("rejected: %s" % e)
            return 1
        _say("%s is now %s%s" % (ce["name"], ce["status"], " and primary" if ce["primary"] else ""))
        return 0
    return run


def cmd_ce_preflight(args):
    state = store.default_platform_path()
    try:
        job_id = jobs.enqueue_preflight(state, args.name)
    except jobs.JobRefused as e:
        _err("refused: %s" % e)
        return 1
    out = asyncio.run(jobs.wait_for_result(state, job_id))
    if out["state"] == "expired" or out["result"] is None:
        _err("refused: %s" % out["message"])
        return 1
    for c in out["result"].get("checks", []):
        _say("  %s: %s - %s" % (c["name"], c["status"], c["detail"]))
    ce = compute_envs.get(state, args.name)
    _say("status: %s" % (ce["status"] if ce else "?"))
    return 0 if out["ok"] else 1


def cmd_mcp(args):
    from . import mcp_server

    index = store.default_index_path()
    if args.http:
        if args.host not in LOOPBACK:
            _risk_line("the MCP server", args.host, args.port)
            _say("A token is required: every request needs Authorization: Bearer <personal access token>.")
        if not store.has_users(store.default_tokens_path(index)):
            _say("There are no users yet, so every request will get 401 until you run: abf-platform user add <name> --lab <lab>, "
                 "then abf-platform pat new --user <name>.")
        mcp_server.run_http(index, args.host, args.port)
    else:
        mcp_server.run_stdio(index)
    return 0


def cmd_rebuild(args):
    index = store.default_index_path()
    # the logs that `fetch-records` brought here are one more place to read, each in the shape of a launch folder
    folders = list(args.folders) + records.roots(store.default_platform_path(index).parent / "records")
    if not folders:
        _err("rejected: no launch folder given, and no records fetched yet (`abf-platform fetch-records <run>`)")
        return 2
    result = rebuild_mod.rebuild(folders, index, out=_say)
    _say("Rebuilt %d run(s) from %d launch folder(s); skipped %d folder(s)." % (
        result.runs, result.folders, len(result.skipped)))
    return 1 if result.skipped else 0


def _add_ce_fields(p):
    p.add_argument("--description")
    p.add_argument("--credentials", help="the NAME of a credential (the credential itself stays with the agent)")
    p.add_argument("--agent", help="the agent that serves this environment")
    p.add_argument("--work-dir")
    p.add_argument("--launch-dir")
    p.add_argument("--head-queue")
    p.add_argument("--compute-queue")
    p.add_argument("--max-queue-size")
    p.add_argument("--head-job-options")
    p.add_argument("--host-name")
    p.add_argument("--user-name")
    p.add_argument("--port")
    p.add_argument("--pre-run")
    p.add_argument("--post-run")
    p.add_argument("--nextflow-config")
    p.add_argument("--env", action="append", help="[head:|compute:|both:]NAME=VALUE, repeatable")
    p.add_argument("--read-root", action="append", help="one more absolute path the agent may list, repeatable")
    p.add_argument("--config-json", help="settings as JSON text, or @file; the flags above win over it")


def build_parser():
    p = argparse.ArgumentParser(prog="abf-platform", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("serve", help="run the receiver for Nextflow's trace messages and the agents' requests")
    s.add_argument("--host", default="127.0.0.1", help="address to listen on (default: 127.0.0.1, this machine only)")
    s.add_argument("--port", type=int, default=8787)
    s.set_defaults(func=cmd_serve)

    wb = sub.add_parser("web", help="run the confirmation page where a person presses send (own process, this machine only by default)",
                        allow_abbrev=False)
    wb.add_argument("--host", default="127.0.0.1", help="address to listen on (default: 127.0.0.1, this machine only)")
    wb.add_argument("--port", type=int, default=8789)
    wb.add_argument("--public-url", help="the address people reach this page at; the MCP answers name it, and a https one "
                                         "makes the cookie Secure")
    wb.set_defaults(func=cmd_web)

    t = sub.add_parser("token", help="manage access tokens")
    tsub = t.add_subparsers(dest="token_command", required=True)
    tn = tsub.add_parser("new", help="issue a token and show it once")
    tn.set_defaults(func=cmd_token_new)

    a = sub.add_parser("agent-token", help="manage the tokens of agents")
    asub = a.add_subparsers(dest="agent_token_command", required=True)
    an = asub.add_parser("new", help="issue a token for one agent name and show it once")
    an.add_argument("name")
    an.set_defaults(func=cmd_agent_token_new)
    ar = asub.add_parser("revoke", help="revoke every token of an agent name")
    ar.add_argument("name")
    ar.set_defaults(func=cmd_agent_token_revoke)

    u = sub.add_parser("user", help="the people who may call the MCP server")
    usub = u.add_subparsers(dest="user_command", required=True)
    ua = usub.add_parser("add", help="add a user (name and lab)")
    ua.add_argument("name")
    ua.add_argument("--lab", required=True)
    ua.set_defaults(func=cmd_user_add)
    up = usub.add_parser("passwd", help="set the password a person logs into the confirmation page with (typed at a terminal)",
                         allow_abbrev=False)
    up.add_argument("name")
    up.set_defaults(func=cmd_user_passwd)

    pt = sub.add_parser("pat", help="personal access tokens for the MCP server over HTTP")
    psub = pt.add_subparsers(dest="pat_command", required=True)
    pn = psub.add_parser("new", help="issue a token for a user and show it once")
    pn.add_argument("--user", required=True)
    pn.add_argument("--label")
    pn.set_defaults(func=cmd_pat_new)
    pl = psub.add_parser("list", help="list the tokens (never their values)")
    pl.set_defaults(func=cmd_pat_list)
    pr = psub.add_parser("revoke", help="revoke one token by its id")
    pr.add_argument("id", type=int)
    pr.set_defaults(func=cmd_pat_revoke)

    c = sub.add_parser("ce", help="compute environments")
    csub = c.add_subparsers(dest="ce_command", required=True)
    cc = csub.add_parser("create", help="store a compute environment (Slurm is checked; the other types are only stored)")
    cc.add_argument("--name")
    cc.add_argument("--platform", help="the type, e.g. slurm-platform (see docs/PLATFORM.md)")
    _add_ce_fields(cc)
    cc.set_defaults(func=cmd_ce_create)
    cu = csub.add_parser("update", help="change settings of an environment; the rules of create apply")
    cu.add_argument("name")
    _add_ce_fields(cu)
    cu.set_defaults(func=cmd_ce_update)
    cl = csub.add_parser("list", help="list the environments")
    cl.set_defaults(func=cmd_ce_list)
    cs = csub.add_parser("show", help="show one environment as JSON")
    cs.add_argument("name")
    cs.set_defaults(func=cmd_ce_show)
    for word, fn, text in (("primary", compute_envs.set_primary, "make this the primary environment"),
                           ("disable", compute_envs.disable, "disable it: no new job, and it stops being primary"),
                           ("enable", compute_envs.enable, "enable a disabled environment again")):
        sp = csub.add_parser(word, help=text)
        sp.add_argument("name")
        sp.set_defaults(func=_simple(fn))
    cp = csub.add_parser("preflight", help="ask the environment's agent to check the site, and wait for the answer")
    cp.add_argument("name")
    cp.set_defaults(func=cmd_ce_preflight)

    m = sub.add_parser("mcp", help="run the read-only MCP server (stdio, or --http)")
    m.add_argument("--http", action="store_true", help="Streamable HTTP instead of stdio")
    m.add_argument("--host", default="127.0.0.1")
    m.add_argument("--port", type=int, default=8788)
    m.set_defaults(func=cmd_mcp)

    r = sub.add_parser("rebuild", help="drop the index and build it again from Nextflow's records")
    r.add_argument("folders", nargs="*", help="launch folders (the ones holding .nextflow/ and .nextflow.log); the records "
                                              "brought here by fetch-records are read too")
    r.set_defaults(func=cmd_rebuild)

    from abf_launch import cli as launch_cli
    launch_cli.add_commands(sub)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)
