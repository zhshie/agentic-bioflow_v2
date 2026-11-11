# Not nf-shard: it ships no command line at all; this one starts the receiver, issues tokens, manages compute environments, runs the MCP server and rebuilds the index.
"""abf-platform: serve | web | token new | agent-token new|list|revoke [--id N] | user add|cloud-cap|passwd [--temporary]|welcome | pat new|list|revoke | oauth revoke USER | ce ... | mcp [--http] | runs assign|offer-cleanup | auto-send list [--since ISO] | dataset register|list|show | rebuild [<folder>...]"""
import argparse
import asyncio
import json
import os
import re
import sqlite3
import sys
import time

from . import agents, cliout, common, compute_envs, jobs, rebuild as rebuild_mod, records, store, welcome

LOOPBACK = ("127.0.0.1", "localhost", "::1")
_AGENT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")


def _say(text):
    cliout.say(text)


def _err(text, why=None, next=None):
    """A refusal: the plain mode prints `text` and nothing else; --json tells it as what (text), why and next."""
    cliout.err(text, why, next)


def _say_json(obj):
    text = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)
    cliout.set_data(json.loads(text))        # --json: the object itself is the `data`
    _say(text)


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
    public = (args.public_url or "").rstrip("/")
    if public:
        from urllib.parse import urlparse
        u = urlparse(public)
        if u.scheme not in ("http", "https") or not u.hostname:
            _err("rejected: --public-url must look like https://host (--public-url 要是 https://主機 的形式)", why='--public-url 的格式不對', next='改成像 https://主機 的網址再執行一次')
            return 1
        if u.scheme == "http" and u.hostname not in LOOPBACK:
            _err("rejected: --public-url %s is plain http; the login cookie would travel in clear text. Use an https:// address "
                 "(a TLS proxy in front of this page) (--public-url 必須是 https)" % public, why='http 是明文傳輸，登入 cookie 會以明文走在網路上', next='改用 https:// 開頭的網址（在前面放 TLS 代理）')
            return 1
    if args.host not in LOOPBACK:
        _err("rejected: the confirmation page binds loopback only (127.0.0.1, ::1 or localhost), not %s, whatever --public-url says. It "
             "serves plain http and the login cookie must not cross a network in clear text: put a TLS proxy (for example Tailscale "
             "Funnel) on this machine in front of it and give the proxy's address as --public-url https://<address people open> "
             "(確認頁只綁本機位址；要給別人用，請在本機前面放 TLS 代理，並用 --public-url https://… 告訴大家網址)" % args.host, why='確認頁用明文 http，登入 cookie 不能在網路上明文傳送，所以只綁本機位址', next='--host 用 127.0.0.1；要給別人用，就在本機前面放 TLS 代理，並用 --public-url 告知網址')
        return 1
    base = public or "http://%s:%s" % (args.host, args.port)
    try:
        app = web.create_app(index, tokens, state, public_url=public or None, base_url=base)
    except ValueError as e:
        _err("rejected: %s" % e, why='確認頁的設定沒有通過檢查', next='照上面的原因修正後，再執行一次')
        return 1
    store.set_meta(state, "web_base_url", base)    # the MCP server names this address in its answers
    _say("abf-platform confirmation page on http://%s:%s, named to people as %s (tokens %s, platform %s)" % (
        args.host, args.port, base, tokens, state))
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def cmd_token_new(args):
    tokens = store.default_tokens_path()
    token = store.create_token(tokens)
    _say("New token (it is shown once and cannot be shown again; only its hash is kept):")
    _say(token)
    _say("Give it to Nextflow as TOWER_ACCESS_TOKEN, with tower.endpoint set to this receiver.")
    return 0


def _agent_owner(name):
    """The user id that owns the agent of that name, or None (no such agent yet, or nobody owns it)."""
    con = store.open_readonly(store.default_platform_path())
    if con is None:
        return None
    try:
        row = con.execute("SELECT owner_user_id FROM agents WHERE name = ?", (name,)).fetchone()
        return row["owner_user_id"] if row else None
    except sqlite3.Error:
        return None
    finally:
        con.close()


def cmd_agent_token_new(args):
    if not _AGENT_NAME.match(args.name):
        _err("rejected: an agent name is letters, digits, _ . - (1 to 64 characters)", why='代理名字只能用英數字與 _ . -，長度 1 到 64 個字', next='換一個符合規則的名字')
        return 1
    tokens = store.default_tokens_path()
    uid = None
    if args.user is not None:
        uid = store.user_id_of(tokens, args.user)
        if uid is None:
            _err("rejected: no such user: %s (沒有這個使用者); add one with: abf-platform user add" % args.user, why='資料庫裡沒有這個使用者', next='先用 abf-platform user add 新增這個使用者，或檢查名字有沒有打錯')
            return 1
    if uid is None and store.has_users(tokens):
        _err("rejected: say whose agent this is with --user NAME (請用 --user 名字 指定這個代理是誰的)", why='平台上已經有使用者，每個代理都要屬於某一位', next='加上 --user 名字')
        return 1
    if uid is not None:
        owner = _agent_owner(args.name)
        if owner is not None and owner != uid:
            _err("rejected: this agent belongs to another user, so a token for it cannot be made for this one; "
                 "use --user with the user it belongs to (這個代理屬於另一位使用者)", why='這個代理名字已經屬於另一位使用者', next='用 --user 指定它所屬的那位使用者，或換一個代理名字')
            return 1
    token = store.create_token(tokens, kind="agent", agent_name=args.name, user_id=uid)
    _say("New agent token for %s%s (it is shown once and cannot be shown again; only its hash is kept):" % (
        args.name, " of user %s" % args.user if args.user else ""))
    _say(token)
    _say("Put it in a file that only you can read (chmod 600) and start the agent with --token-file <that file>.")
    return 0


def cmd_user_add(args):
    cap = None
    if args.cloud_cap_usd is not None:
        try:
            cap = store.parse_cloud_cap(args.cloud_cap_usd)       # judged before the account is made, so a bad number leaves no account
        except ValueError as e:
            _err("rejected: %s; no account was made (沒有建立帳號)" % e, why='上限要是 0 到 1,000,000 之間的美元數字', next='改成合法的數字再執行一次；帳號還沒有建立')
            return 1
    try:
        uid = store.create_user(store.default_tokens_path(), args.name, args.lab)
    except ValueError:
        _err("rejected: a user named %s already exists (這個名字已存在)" % args.name, why='資料庫裡已經有同名的使用者', next='換一個名字；或對現有的使用者直接用 pat new 發 token')
        return 1
    if cap is not None:
        store.set_cloud_cap(store.default_tokens_path(), uid, cap)
        _say("monthly cloud cap of %s: US$%.2f (每月雲端費用上限)" % (args.name, cap))
    _say("added user %s (lab %s); issue a token with: abf-platform pat new --user %s" % (args.name, args.lab, args.name))
    return 0


def cmd_user_cloud_cap(args):
    """Set or change the monthly cloud cap (US dollars) of a user. The administrator's terminal is the only door to it."""
    tokens = store.default_tokens_path()
    try:
        cap = store.parse_cloud_cap(args.usd)
    except ValueError as e:
        _err("rejected: %s; the cap was not changed (上限沒有改)" % e, why='上限要是 0 到 1,000,000 之間的美元數字', next='改成合法的數字再執行一次；原本的上限沒有動')
        return 1
    uid = store.user_id_of(tokens, args.name)
    if uid is None:
        _err("rejected: 沒有這個使用者 (no such user): %s; add one with: abf-platform user add" % args.name, why='資料庫裡沒有這個使用者', next='先用 abf-platform user add 新增這個使用者，或檢查名字有沒有打錯')
        return 1
    store.set_cloud_cap(tokens, uid, cap)
    _say("monthly cloud cap of %s is now US$%.2f (每月雲端費用上限)" % (args.name, cap))
    return 0


def cmd_user_welcome(args):
    """Print the welcome letter of a user (name, lab, cloud cap filled in), or save it with --out. Reads only; sends nothing."""
    tokens = store.default_tokens_path()
    url = common.public_url(args.platform_url)
    if url is None:
        _err("rejected: the platform address must be https://host (http only for localhost or 127.0.0.1); nothing was printed "
             "(網址要 https://主機，或 http 只限本機)", why='歡迎信裡要放的平台網址格式不對', next='給 https://主機 的網址（http 只限本機）')
        return 1
    user = store.user_by_name(tokens, args.name)
    if user is None:
        _err("rejected: 沒有這個使用者 (no such user): %s; add one with: abf-platform user add" % args.name, why='資料庫裡沒有這個使用者', next='先用 abf-platform user add 新增這個使用者，或檢查名字有沒有打錯')
        return 1
    text = welcome.welcome_text(user["name"], user["lab"], store.cloud_cap(tokens, user["user_id"]), url, args.operator)
    if not args.out:
        _say(text)
        return 0
    try:
        fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        _err("rejected: %s already exists, so it was not overwritten; choose another name or delete it (檔案已存在，沒有覆蓋)" % args.out, why='為了不蓋掉舊檔，已經存在的檔案不會被覆寫', next='換一個 --out 檔名，或先自己刪掉舊檔')
        return 1
    except OSError:
        _err("rejected: cannot create %s; check that the folder exists and you may write there (無法建立檔案)" % args.out, why='資料夾不存在，或你沒有寫入的權限', next='確認資料夾存在而且你可以寫入')
        return 1
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")
    _say("saved to %s (已存到)" % args.out)
    return 0


def cmd_user_passwd(args):
    """Set a user's web password. The person types it, twice, on a real terminal: no flag can type the person's own password, and no
    file or variable can. `--temporary` makes a one-time one instead: a random password shown once, at a real terminal, for the
    administrator to hand over privately; the person must change it at the first web login."""
    import getpass
    from abf_launch import terminal

    temporary = getattr(args, "temporary", False)
    why = terminal.terminal_problem()
    if why and temporary:
        _err("rejected: 臨時密碼只能顯示在真正的終端機上，這裡不行（%s）(a temporary password is shown only at a real terminal, never to a pipe or a script)" % why, why='臨時密碼只能顯示在真正的終端機，不能送給管線或腳本', next='在真正的終端機裡直接執行這個指令')
        return 1
    if why:
        _err("rejected: 密碼只能在真正的終端機上由本人輸入，這裡不行（%s）(the password is typed at a real terminal, nothing else can give it)" % why, why='密碼只能在真正的終端機由本人輸入', next='在真正的終端機裡直接執行這個指令')
        return 1
    tokens = store.default_tokens_path()
    if store.user_id_of(tokens, args.name) is None:
        _err("rejected: 沒有這個使用者 (no such user): %s; add one with: abf-platform user add" % args.name, why='資料庫裡沒有這個使用者', next='先用 abf-platform user add 新增這個使用者，或檢查名字有沒有打錯')
        return 1
    if temporary:
        try:
            issued = store.issue_temporary_password(tokens, args.name)
        except ValueError as e:
            _err("rejected: %s" % e, why='系統拒絕發出臨時密碼', next='照上面的原因修正後，再執行一次')
            return 1
        hours = int(store.TEMP_PASSWORD_SECONDS // 3600)
        _say("temporary web password of %s (一次性臨時密碼，只顯示這一次):" % args.name)
        _say(issued["password"])
        _say("Send it to %s privately, not in a chat with an AI. It works for %d hours, and %s must change it at the first login "
             "(請私下交給本人；%d 小時內有效，第一次登入必須改掉)." % (args.name, hours, args.name, hours))
        _say("Shown once and kept nowhere: if it is lost, run this command again (只顯示這一次、不留任何紀錄，弄丟就重新執行這個指令).")
        return 0
    try:
        first = getpass.getpass("New web password for %s: " % args.name)
        second = getpass.getpass("Type it again: ")
    except (EOFError, KeyboardInterrupt):
        _err("\nrejected: nothing was entered, nothing was changed (沒有輸入，什麼都沒改)", why='沒有輸入任何密碼', next='重新執行，並輸入兩次密碼')
        return 1
    if first != second:
        _err("rejected: the two entries differ, nothing was changed (兩次輸入不一致，什麼都沒改)", why='兩次輸入的密碼不一樣', next='重新執行，兩次輸入相同的密碼')
        return 1
    try:
        store.set_web_password(tokens, args.name, first)
    except ValueError as e:
        _err("rejected: %s" % e, why='系統拒絕這個密碼', next='換一個符合規則的密碼再執行一次')
        return 1
    _say("web password of %s is set; every browser login of that user has ended (網頁密碼已設定，舊的登入全部結束)" % args.name)
    return 0


def cmd_pat_new(args):
    tokens = store.default_tokens_path()
    uid = store.user_id_of(tokens, args.user)
    if uid is None:
        _err("rejected: no such user: %s (沒有這個使用者); add one with: abf-platform user add" % args.user, why='資料庫裡沒有這個使用者', next='先用 abf-platform user add 新增這個使用者，或檢查名字有沒有打錯')
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
    _err("rejected: no live personal access token with id %s" % args.id, why='沒有這個編號的有效 token（編號打錯，或已經撤銷）', next='用 abf-platform pat list 看編號')
    return 1


def cmd_oauth_revoke(args):
    tokens = store.default_tokens_path()
    if store.user_id_of(tokens, args.user) is None:
        _err("no user named %s (沒有這個使用者)" % args.user, why='資料庫裡沒有這個使用者', next='先用 abf-platform user add 新增這個使用者，或檢查名字有沒有打錯')
        return 1
    n = store.revoke_oauth_tokens(tokens, args.user)
    _say("revoked %d OAuth token(s) of %s; their personal access tokens are untouched (已撤銷 %d 個 OAuth 權杖)" % (n, args.user, n))
    return 0


def cmd_agent_token_list(args):
    rows = store.list_agent_tokens(store.default_tokens_path(), args.name)
    for r in rows:
        _say("id %s  agent %s  user %s  created %s  %s" % (
            r["id"], r["agent_name"], r["user"] or "-", time.strftime("%Y-%m-%d %H:%M", time.localtime(r["created_at"])),
            "revoked" if r["revoked_at"] else "not revoked"))
    if not rows:
        _say("no agent tokens" + (" for %s" % args.name if args.name else ""))
    return 0


def cmd_agent_token_revoke(args):
    if (args.name is None) == (args.id is None):
        _err("rejected: give either an agent name or --id N, not both and not neither (請給代理名字或 --id，二選一)", why='撤銷時要指定是哪一個，代理名字和 --id 必須剛好給一個', next='給代理名字，或給 --id N，擇一')
        return 1
    if args.id is not None:
        got = store.revoke_agent_token(store.default_tokens_path(), args.id)
        if got is None:
            _err("rejected: no live agent token with id %s (沒有這個有效的代理 token); list them with: abf-platform agent-token list" % args.id, why='沒有這個編號的有效代理 token（編號打錯，或已經撤銷）', next='用 abf-platform agent-token list 看編號')
            return 1
        _say("revoked agent token %s (agent %s); it is refused from its next request, other tokens of this agent are untouched"
             % (args.id, got["agent_name"]))
        return 0
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
             "pre_run": "preRunScript", "post_run": "postRunScript", "nextflow_config": "nextflowConfig",
             "project": "project", "location": "location", "batch_account": "batchAccountName",
             "storage_account": "storageAccountName", "pool": "pool", "service_account_email": "serviceAccountEmail",
             "boot_disk_size": "bootDiskSize", "region": "region", "job_queue": "jobQueue",
             "context": "context", "namespace": "namespace", "storage_claim": "storageClaimName",
             "storage_mount_path": "storageMountPath", "service_account": "serviceAccount"}
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
    if args.spot is not None:
        config["spot"] = args.spot
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
    if args.owner is not None or not partial:
        fields["owner_user_id"] = _owner_id(args.owner)
    return fields


def _owner_id(name):
    """The user id an environment belongs to (116): the user named by --owner; without it the only user there is, or nobody when there
    are no users yet. With two or more users the flag is required."""
    tokens = store.default_tokens_path()
    if name is not None:
        user = store.user_by_name(tokens, name)
        if user is None:
            raise compute_envs.CEError("no such user: %s (沒有這個使用者)" % name)
        return user["user_id"]
    users = store.user_names(tokens)
    if len(users) > 1:
        raise compute_envs.CEError("there is more than one user, so say whose environment this is with --owner NAME "
                                   "(有多位使用者，請用 --owner 名字 指定這個環境是誰的)")
    return next(iter(users)) if users else None


def _queue_first_preflight(state, ce):
    """The line to print right after a create or update; the work is compute_envs.queue_first_preflight, which the settings page shares."""
    return compute_envs.queue_first_preflight(state, ce)[1]


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
        _err("rejected: %s" % e, why='運算環境的設定沒有通過檢查', next='照上面的說明修正欄位後，再執行一次')
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
        _err("rejected: %s" % e, why='運算環境的設定沒有通過檢查', next='照上面的說明修正欄位後，再執行一次')
        return 1
    _say("compute environment %s updated" % ce["name"])
    if ce["platform"] in compute_envs.CHECKABLE and ce["status"] != compute_envs.DISABLED:
        _say(_queue_first_preflight(state, ce))
    return 0


def cmd_ce_list(args):
    state = store.default_platform_path()
    owner_of, names = compute_envs.owners(state), store.user_names(store.default_tokens_path())
    for ce in compute_envs.list_all(state):
        _say("%s%s  %s  %s  %s  owner %s" % (ce["name"], " (primary)" if ce["primary"] else "", ce["platform"], ce["status"],
                                              ce["agent"] or "-", names.get(owner_of.get(ce["name"])) or "(none: local only)"))
    return 0


def cmd_ce_show(args):
    ce = compute_envs.get(store.default_platform_path(), args.name)
    if ce is None:
        _err("compute environment %s not found (找不到)" % args.name, why='資料庫裡沒有這個名字的運算環境', next='用 abf-platform ce list 看現有的名字')
        return 1
    _say_json(ce)
    return 0


def _simple(fn):
    def run(args):
        try:
            ce = fn(store.default_platform_path(), args.name)
        except compute_envs.CEError as e:
            _err("rejected: %s" % e, why='這個運算環境的操作沒有通過檢查', next='照上面的原因修正後，再執行一次')
            return 1
        _say("%s is now %s%s" % (ce["name"], ce["status"], " and primary" if ce["primary"] else ""))
        return 0
    return run


def cmd_ce_preflight(args):
    state = store.default_platform_path()
    ce = compute_envs.get(state, args.name)
    if ce is not None and ce["platform"] in compute_envs.PLATFORM_HOST_TYPES + compute_envs.CHECK_ONLY_TYPES:
        try:      # a record made before the type was checked must pass today's rules first, whatever its status
            compute_envs.clean({"name": ce["name"], "description": ce["description"], "platform": ce["platform"],
                                "credentialsId": ce["credentialsId"], "agent": ce["agent"], "config": ce["config"]})
        except compute_envs.CEError as e:
            if "請刪除後重建" in str(e):      # an old record: updating cannot fix it
                _err("rejected: %s" % e, why='這筆運算環境是舊版留下的紀錄，更新沒辦法修好它', next='刪除後重新建立')
            else:
                _err("rejected: %s. Fix it with `abf-platform ce update %s ...` first (請先用 ce update 補齊)" % (e, args.name), why='這筆紀錄沒有通過現在的檢查規則', next='先用 abf-platform ce update 補齊欄位，再做 preflight')
            return 1
    try:
        job_id = jobs.enqueue_preflight(state, args.name)
    except jobs.JobRefused as e:
        _err("refused: %s" % e, why='系統拒絕排入這項檢查', next='照上面的原因修正後，再執行一次')
        return 1
    out = asyncio.run(jobs.wait_for_result(state, job_id))
    if out["state"] == "expired" or out["result"] is None:
        _err("refused: %s" % out["message"], why='沒有收到代理的回覆', next='確認該代理正在運行後，再執行一次')
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
        public = (args.public_url or "").rstrip("/")
        if public:
            from urllib.parse import urlparse
            u = urlparse(public)
            if not u.hostname or u.path not in ("", "/") or not (u.scheme == "https" or (u.scheme == "http" and u.hostname in LOOPBACK)):
                _err("rejected: --public-url must be https://host (or http://127.0.0.1:port on this machine), with no path "
                     "(--public-url 要是 https://主機 的形式)", why='--public-url 的格式不對', next='改成 https://主機（不含路徑）的網址再執行一次')
                return 1
        mcp_server.run_http(index, args.host, args.port, public_url=public or None)
    else:
        mcp_server.run_stdio(index)
    return 0


def cmd_runs_offer_cleanup(args):
    """Offer a clean-up request, for the owner of each run that succeeded, on the platform's own terminal. It only previews unless --apply
    is given, and with --apply it only writes pending requests: the owner still presses send on the confirmation page. All the judging is
    done by actions.offer_cleanups; this prints what it answers."""
    from . import actions
    if bool(args.run_names) == bool(args.all):
        _err("rejected: give run names or --all, one of the two (請給 run 名稱，或加 --all，兩者擇一); nothing was changed", why='要處理哪些 run 沒有指定清楚', next='給 run 名稱，或加 --all，兩者擇一')
        return 1
    user_id = None
    if args.user:
        user = store.user_by_name(store.default_tokens_path(), args.user)
        if user is None:
            _err("rejected: no such user: %s (沒有這個使用者); nothing was changed" % args.user, why='資料庫裡沒有這個使用者', next='先用 abf-platform user add 新增這個使用者，或檢查名字有沒有打錯')
            return 1
        user_id = user["user_id"]
    preview = args.list or not args.apply
    index = store.default_index_path()
    out = actions.offer_cleanups(store.default_platform_path(index), index, run_names=None if args.all else args.run_names,
                                 user_id=user_id, dry_run=preview)
    for r in out["results"]:
        if r["offered"]:
            who = r["owner"] or "?"
            _say("%s: 已提出申請，請 %s 登入網頁在確認頁按送出 (offered; %s presses send on the confirmation page)" % (r["run_name"], who, who))
        elif r.get("would_offer"):
            _say("%s: 會提出申請 (would offer)" % r["run_name"])
        else:
            _say("%s: 略過：%s" % (r["run_name"], r["reason"]))
    if preview:
        would = sum(1 for r in out["results"] if r.get("would_offer"))
        skipped = len(out["results"]) - would
        _say("預覽：會提出 %d 張、略過 %d 個；要真的提出請加 --apply (preview: would offer %d, skip %d; add --apply to offer)"
             % (would, skipped, would, skipped))
    else:
        _say("已提出 %d 張、略過 %d 個 (offered %d, skipped %d)" % (out["offered"], out["skipped"], out["offered"], out["skipped"]))
    return 0


def _dataset_caller(args):
    """(Caller or None, exit code or None) for a dataset command: the account rule of `abf-platform launch` (--user once users exist)."""
    from abf_launch import cli as launch_cli
    caller, problem = launch_cli._account(args.user)
    if problem:
        _err(problem, why='帳號規則沒有通過', next='加上 --user 名字，或照上面的說明處理')
        return None, 1
    return caller, None


def _read_sheet_text(path):
    """(text, None) of a samplesheet file, else (None, a plain sentence). Nothing but this file is read."""
    try:
        with open(path, "rb") as f:
            raw = f.read(1024 * 1024 + 1)
    except OSError:
        return None, "讀不到樣本表檔案，請檢查 --samplesheet 的路徑 (cannot read the samplesheet file; check the --samplesheet path); nothing was registered"
    if len(raw) > 1024 * 1024:
        return None, "樣本表太大，上限 1 MiB (the samplesheet is too large; the limit is 1 MiB); nothing was registered"
    if bytes([0]) in raw:
        return None, "樣本表含有 NUL 字元，不是文字檔 (the samplesheet holds a NUL character); nothing was registered"
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError:
        return None, "樣本表不是 UTF-8 文字 (the samplesheet is not UTF-8 text); nothing was registered"


def cmd_dataset_register(args):
    """Keep a dataset (a name, a version, a samplesheet and the places of its files) for a user. All the judging is done by
    datasets.register_dataset; no file named by --file is read or looked at."""
    from .actions import datasets
    caller, code = _dataset_caller(args)
    if code:
        return code
    text, problem = _read_sheet_text(args.samplesheet)
    if problem:
        _err(problem, why='樣本表檔案不能用', next='檢查 --samplesheet 的路徑與檔案內容')
        return 1
    out = datasets.register_dataset(store.default_platform_path(), name=args.name, version=args.version, samplesheet=text,
                                    files=[{"path": p} for p in args.file], caller=caller, destination=args.destination)
    if not out.get("ok"):
        _err(out["message"], why='資料集沒有通過登記檢查', next='照上面的說明修正後，再執行一次')
        return 1
    _say("已登記資料集 %s 版本 %s（%d 個檔案）(registered)" % (args.name, args.version, len(args.file)))
    return 0


def cmd_dataset_list(args):
    from .actions import datasets
    caller, code = _dataset_caller(args)
    if code:
        return code
    for r in datasets.list_datasets(store.default_platform_path(), caller=caller)["datasets"]:
        _say("%s %s %d %s" % (r["name"], r["version"], r["n_files"], time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["created_at"]))))
    return 0


def cmd_dataset_show(args):
    from .actions import datasets
    caller, code = _dataset_caller(args)
    if code:
        return code
    got = datasets.get_dataset(store.default_platform_path(), args.name, args.version, caller=caller)
    if not got.get("found"):
        _err(got["message"], why='平台裡沒有這個名字（或這個版本）的資料集', next='用 abf-platform dataset list 看現有的資料集')
        return 1
    _say_json(got)
    return 0


def _bundle_run_name(bundle_json):
    try:
        b = json.loads(bundle_json) if bundle_json else {}
        b = b.get("bundle", b) if isinstance(b, dict) else {}
        r = b.get("run_name") or ((b.get("resume") or b.get("relaunch") or {}).get("origin") or {}).get("run_name") or b.get("run")
        return r if isinstance(r, str) else "-"
    except (ValueError, AttributeError):
        return "-"


def cmd_auto_send_list(args):
    """The sends that went through on a person's own SU budget (channel BUDGET), one line each for the daily summary. Read only."""
    import datetime
    since = 0
    if args.since:
        try:
            since = datetime.datetime.fromisoformat(args.since).timestamp()
        except ValueError:
            _err("rejected: --since is not an ISO time: %s (--since 不是 ISO 時間); nothing was listed" % args.since,
                 why="時間格式不對", next="用 2026-11-10 或 2026-11-10T08:00:00 這樣的寫法")
            return 1
    index = store.default_index_path()
    state = store.default_platform_path(index)
    names = store.user_names(store.default_tokens_path(index))
    rows = []
    if os.path.exists(str(state)):
        con = sqlite3.connect("file:%s?mode=ro" % str(state).replace("\\", "/"), uri=True, timeout=30)
        try:
            if "budget_note" in {r[1] for r in con.execute("PRAGMA table_info(confirmations)")}:
                rows = con.execute("SELECT confirmed_at, caller_user_id, kind, bundle_json, id, budget_note FROM confirmations "
                                   "WHERE channel = 'BUDGET' AND confirmed_at IS NOT NULL AND confirmed_at >= ? ORDER BY confirmed_at, id",
                                   (since,)).fetchall()
        finally:
            con.close()
    if not rows:
        _say("no budget-approved sends")
        return 0
    for at, uid, kind, bundle_json, rid, note in rows:
        when = datetime.datetime.fromtimestamp(at, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        _say("\t".join([when, names.get(uid, "?"), kind or "-", _bundle_run_name(bundle_json), rid,
                        (note or "").replace("\t", " ").replace("\n", " ")]))
    return 0


def cmd_runs_assign(args):
    """Give a run that nobody owns to a user (116b). Terminal only: it writes launches.user_id of the newest row of the run and nothing else."""
    user = store.user_by_name(store.default_tokens_path(), args.user)
    if user is None:
        _err("rejected: no such user: %s (沒有這個使用者); nothing was changed" % args.user, why='資料庫裡沒有這個使用者', next='先用 abf-platform user add 新增這個使用者，或檢查名字有沒有打錯')
        return 1
    state = store.default_platform_path(store.default_index_path())
    names = store.user_names(store.default_tokens_path())

    def work(con):
        row = jobs.latest_launch(con, args.run_name)
        if row is None:
            return "no_run", None
        old = row["user_id"]
        if old == user["user_id"]:
            return "same", old
        if old is not None and not args.force:
            return "owned", old
        con.execute("UPDATE launches SET user_id = ? WHERE id = ?", (user["user_id"], row["id"]))
        return "done", old

    what, old = jobs.transaction(state, work)
    if what == "no_run":
        _err("rejected: no launch of a run named %s (沒有這個 run); nothing was changed" % args.run_name, why='發射紀錄裡沒有這個名字的 run', next='確認 run 的名稱有沒有打錯')
        return 1
    if what == "owned":
        _err("rejected: run %s already belongs to %s; to change the owner add --force (這個 run 已經有擁有者，要改請加 --force)" % (      # 116b-owner
            args.run_name, names.get(old, "user #%s" % old)), why='這個 run 已經有擁有者', next='要改擁有者，請看 runs assign --help 裡改擁有者的選項')
        return 1
    if what == "same":
        _say("run %s already belongs to %s; nothing to change (已經是他的)" % (args.run_name, args.user))
        return 0
    if old is None:
        _say("run %s now belongs to %s (已指定給 %s)" % (args.run_name, args.user, args.user))
    else:
        _say("run %s: owner changed from %s to %s (擁有者由 %s 改為 %s)" % (
            args.run_name, names.get(old, "user #%s" % old), args.user, names.get(old, "user #%s" % old), args.user))
    return 0


def cmd_rebuild(args):
    index = store.default_index_path()
    # the logs that `fetch-records` brought here are one more place to read, each in the shape of a launch folder
    folders = list(args.folders) + records.roots(store.default_platform_path(index).parent / "records")
    if not folders:
        _err("rejected: no launch folder given, and no records fetched yet (`abf-platform fetch-records <run>`)", why='沒有指定資料夾，也還沒有抓回來的紀錄', next='給一個或多個資料夾，或先執行 abf-platform fetch-records <run>')
        return 2
    result = rebuild_mod.rebuild(folders, index, out=_say)
    _say("Rebuilt %d run(s) from %d launch folder(s); skipped %d folder(s)." % (
        result.runs, result.folders, len(result.skipped)))
    return 1 if result.skipped else 0


def _add_ce_fields(p):
    p.add_argument("--owner", help="the user this environment belongs to (default: the only user; required when there are several)")
    p.add_argument("--description")
    p.add_argument("--credentials", help="the NAME of a credential (the credential itself stays with the agent)")
    p.add_argument("--agent", help="the agent that serves this environment")
    p.add_argument("--work-dir")
    p.add_argument("--project", help="Google Batch: the GCP project ID")
    p.add_argument("--location", help="Google Batch/Azure Batch: the region, e.g. europe-west2 or westeurope")
    p.add_argument("--batch-account", help="Azure Batch: the Batch account name, e.g. labbatch")
    p.add_argument("--storage-account", help="Azure Batch: the storage account name, e.g. labstore")
    p.add_argument("--pool", help="Azure Batch: the id of a pool that already exists, e.g. lab-pool")
    p.add_argument("--context", help="Kubernetes: the context name in the kubeconfig, e.g. lab-context")
    p.add_argument("--namespace", help="Kubernetes: the namespace, e.g. lab-ns")
    p.add_argument("--storage-claim", help="Kubernetes: the name of a storage claim that already exists, e.g. lab-pvc")
    p.add_argument("--storage-mount-path", help="Kubernetes: where the claim is mounted (default /workspace)")
    p.add_argument("--service-account", help="Kubernetes: the service account the pods run as (default: the namespace's own)")
    p.add_argument("--region", help="AWS Batch: the region, e.g. eu-west-1")
    p.add_argument("--job-queue", help="AWS Batch: the name of the job queue (a name, not an ARN)")
    p.add_argument("--spot", dest="spot", action="store_const", const=True, default=None, help="Google Batch/AWS Batch/Azure Batch: use spot machines (Azure: stored only)")
    p.add_argument("--no-spot", dest="spot", action="store_const", const=False, help="Google Batch/AWS Batch/Azure Batch: do not use spot machines")
    p.add_argument("--service-account-email", help="Google Batch: the service account the jobs run as (an e-mail address, not a key)")
    p.add_argument("--boot-disk-size", help="Google Batch: boot disk size, e.g. '50 GB'")
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


class _Parser(argparse.ArgumentParser):
    """Under --json a wrong command line is told as one what/why/next object on stderr (exit 2), like any other refusal."""

    def error(self, message):
        if cliout.json_mode():
            path = self.prog.split(" ", 1)[1] if " " in self.prog else ""
            cliout.emit_failure(path, message, "命令列參數不符合這個指令的格式",
                                "用 abf-platform %s--help 看正確用法" % (path + " " if path else ""))
            self.exit(2)
        super().error(message)


def build_parser():
    p = _Parser(prog="abf-platform", description=__doc__)
    # The flags sit before the command (a leaf has none of them; `dataset register|show` keep their own --version, the dataset's).
    # Their dests differ from every leaf dest, because a leaf's namespace is copied over the root's.
    p.add_argument("--version", dest="product_version", action="store_true",
                   help="print the product version (from .claude-plugin/plugin.json) and exit")
    p.add_argument("--json", dest="json_mode", action="store_true",
                   help="print one JSON object per command (stable keys; a failure is {error: {what, why, next}} on stderr)")
    p.add_argument("--debug", dest="debug_mode", action="store_true",
                   help="add diagnostic lines (each starts with 'debug: ') on stderr; stdout does not change")
    sub = p.add_subparsers(dest="command")      # not required by argparse, so that --version stands alone; main asks for it

    s = sub.add_parser("serve", help="run the receiver for Nextflow's trace messages and the agents' requests")
    s.add_argument("--host", default="127.0.0.1", help="address to listen on (default: 127.0.0.1, this machine only)")
    s.add_argument("--port", type=int, default=8787)
    s.set_defaults(func=cmd_serve)

    wb = sub.add_parser("web", help="run the confirmation page where a person presses send (own process, this machine only by default)",
                        allow_abbrev=False)
    wb.add_argument("--host", default="127.0.0.1", help="address to listen on: loopback only (127.0.0.1, ::1, localhost); a non-loopback "
                                                       "address is refused (see the docs for the proxy in front)")
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
    an.add_argument("--user", help="the user this agent belongs to (required once the platform has users); the agent then belongs to that user, and nobody else's token can take it")
    an.set_defaults(func=cmd_agent_token_new)
    ar = asub.add_parser("revoke", help="revoke every token of an agent name, or one token by --id (see agent-token list)")
    ar.add_argument("name", nargs="?")
    ar.add_argument("--id", type=int, help="revoke only the agent token with this id")
    ar.set_defaults(func=cmd_agent_token_revoke)
    al = asub.add_parser("list", help="list the agent tokens with their ids (never the token values)")
    al.add_argument("name", nargs="?")
    al.set_defaults(func=cmd_agent_token_list)

    u = sub.add_parser("user", help="the people who may call the MCP server")
    usub = u.add_subparsers(dest="user_command", required=True)
    ua = usub.add_parser("add", help="add a user (name and lab)")
    ua.add_argument("name")
    ua.add_argument("--lab", required=True)
    ua.add_argument("--cloud-cap-usd", help="the most this person may spend on cloud runs in a month, in US dollars (0 to 1,000,000); "
                                           "without it the person cannot send to the cloud until you run: user cloud-cap")
    ua.set_defaults(func=cmd_user_add)
    uc = usub.add_parser("cloud-cap", help="set or change the monthly cloud cap of a user, in US dollars", allow_abbrev=False)
    uc.add_argument("name")
    uc.add_argument("usd")
    uc.set_defaults(func=cmd_user_cloud_cap)
    uw = usub.add_parser("welcome", help="print the welcome letter of a user with name, lab and cloud cap filled in; prints only, sends nothing",
                         allow_abbrev=False)
    uw.add_argument("name")
    uw.add_argument("--platform-url", required=True, help="the address the person opens, https://host (http only for localhost)")
    uw.add_argument("--operator", help="the name to sign the letter with (without it <operator> stays for you to fill in)")
    uw.add_argument("--out", help="save the letter to this new file instead of printing it (an existing file is never overwritten); "
                                  "prints only, sends nothing")
    uw.set_defaults(func=cmd_user_welcome)
    up = usub.add_parser("passwd", help="set the password a person logs into the confirmation page with (typed at a terminal, 8 to 1000 characters)",
                         allow_abbrev=False)
    up.add_argument("name")
    up.add_argument("--temporary", action="store_true",
                    help="instead of asking the person, make a one-time random password, show it once at this terminal (never to a pipe), "
                         "valid for 72 hours; the person must change it at the first web login")
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

    oa = sub.add_parser("oauth", help="the OAuth logins of Claude Desktop connectors")
    osub = oa.add_subparsers(dest="oauth_command", required=True)
    orv = osub.add_parser("revoke", help="end every OAuth login (access and refresh tokens) of one user; their personal access tokens stay")
    orv.add_argument("user")
    orv.set_defaults(func=cmd_oauth_revoke)

    c = sub.add_parser("ce", help="compute environments")
    csub = c.add_subparsers(dest="ce_command", required=True)
    cc = csub.add_parser("create", help="store a compute environment (Slurm, Google Batch and AWS Batch are checked by their agent; the other types are only stored)")
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
    cp = csub.add_parser("preflight", help="ask the environment's agent to check it (the site, or for Google Batch the cloud account), and wait for the answer")
    cp.add_argument("name")
    cp.set_defaults(func=cmd_ce_preflight)

    m = sub.add_parser("mcp", help="run the read-only MCP server (stdio, or --http)")
    m.add_argument("--http", action="store_true", help="Streamable HTTP instead of stdio")
    m.add_argument("--host", default="127.0.0.1")
    m.add_argument("--port", type=int, default=8788)
    m.add_argument("--public-url", help="the address people reach this server at (https://host, no path); with it a 401 tells a Claude "
                                        "Desktop connector where to log in (needs `abf-platform web --public-url` too)")
    m.set_defaults(func=cmd_mcp)

    r = sub.add_parser("rebuild", help="drop the index and build it again from Nextflow's records")
    r.add_argument("folders", nargs="*", help="launch folders (the ones holding .nextflow/ and .nextflow.log); the records "
                                              "brought here by fetch-records are read too")
    r.set_defaults(func=cmd_rebuild)

    rn = sub.add_parser("runs", help="the owner of a run in the hand-off record")
    rsub = rn.add_subparsers(dest="runs_command", required=True)
    ra = rsub.add_parser("assign", help="give a run that nobody owns to a user (changing an owner that exists takes one more flag)", allow_abbrev=False)
    ra.add_argument("run_name")
    ra.add_argument("--user", required=True, help="the user who launched it")
    ra.add_argument("--force", action="store_true", help="change the owner of a run that already has one")      # 116b-owner: not a confirmation switch
    ra.set_defaults(func=cmd_runs_assign)
    ro = rsub.add_parser("offer-cleanup", help="offer a clean-up request to the owner of each run that succeeded (previews unless --apply; the owner still presses send)", allow_abbrev=False)
    ro.add_argument("run_names", nargs="*", metavar="RUN", help="the runs to offer for (or --all)")
    ro.add_argument("--all", action="store_true", help="every run that succeeded")
    ro.add_argument("--user", help="only the runs this user launched")
    ro.add_argument("--list", action="store_true", help="only list what would be offered (the default)")
    ro.add_argument("--apply", action="store_true", help="write the requests; without it nothing is written")
    ro.set_defaults(func=cmd_runs_offer_cleanup)

    asd = sub.add_parser("auto-send", help="the sends that went through on a person's own SU budget (read only)")
    assub = asd.add_subparsers(dest="auto_send_command", required=True)
    asl = assub.add_parser("list", help="list them, one per line (time, user, kind, run, confirmation id, note), oldest first", allow_abbrev=False)
    asl.add_argument("--since", help="only the sends at or after this ISO time")
    asl.set_defaults(func=cmd_auto_send_list)

    da = sub.add_parser("dataset", help="datasets: a name, a version, a samplesheet and the places of its files (the platform keeps names and places only)")
    dsub = da.add_subparsers(dest="dataset_command", required=True)
    dr = dsub.add_parser("register", help="keep a dataset for a user; a local path in their uploads folder, or gs:// locations with --destination", allow_abbrev=False)
    dr.add_argument("--name", required=True)
    dr.add_argument("--version", required=True)
    dr.add_argument("--samplesheet", required=True, help="the CSV file (UTF-8, at most 1 MiB)")
    dr.add_argument("--file", action="append", required=True, help="the place of one file (repeat for each); it is not opened")
    dr.add_argument("--user", help="the user it is for (needed once the platform has users)")
    dr.add_argument("--destination", help="a Google Batch environment: the files are gs:// locations of the user's own prefix of its bucket")
    dr.set_defaults(func=cmd_dataset_register)
    dl = dsub.add_parser("list", help="list the datasets", allow_abbrev=False)
    dl.add_argument("--user")
    dl.set_defaults(func=cmd_dataset_list)
    dw = dsub.add_parser("show", help="show one dataset as JSON (the newest version unless --version)", allow_abbrev=False)
    dw.add_argument("name")
    dw.add_argument("--version")
    dw.add_argument("--user")
    dw.set_defaults(func=cmd_dataset_show)

    from abf_launch import cli as launch_cli
    launch_cli.add_commands(sub)
    return p


ADOPTING = ("serve", "web", "mcp", "ce")


def adopt_orphans():
    """What a start does first (116): with exactly one user, the environments, agents and launches that nobody owns become his."""
    index = store.default_index_path()
    store.assign_orphans(store.default_platform_path(index), store.default_tokens_path(index))


def cmd_version(args):
    version = cliout.read_version()
    if version is None:
        _err("rejected: 找不到產品版本 (the product version was not found)",
             why="版本記在 .claude-plugin/plugin.json，這份安裝裡沒有它",
             next="從 repository 的 checkout 執行，或設 PYTHONPATH=platform")
        return 1
    cliout.set_data({"version": version})
    _say("abf-platform %s" % version)
    return 0


def _command_path(args):
    if args.product_version:
        return "version"
    return " ".join([args.command] + [v for k, v in sorted(vars(args).items()) if k.endswith("_command") and v])


def _option_names(parser):
    names = set()
    for a in parser._actions:
        names.update(a.option_strings)
        if isinstance(getattr(a, "choices", None), dict):
            for child in a.choices.values():
                names |= _option_names(child)
    return names


JSON_REFUSED = {
    "serve": "它會一直執行，不會「結束」，沒辦法只印一個物件",
    "web": "它會一直執行，不會「結束」，沒辦法只印一個物件",
    "mcp": "它會一直執行，不會「結束」，沒辦法只印一個物件",
    "user passwd": "密碼只能顯示、輸入在真正的終端機，而 --json 的輸出會被管線接走",
}


def _json_refusal(args, path):
    """(what, why, next) when this command has no business under --json, else None."""
    if path in JSON_REFUSED:
        return "這個指令不能用 --json", JSON_REFUSED[path], "不加 --json，直接在真正的終端機裡執行"
    if getattr(args.func, "__module__", "").startswith("abf_launch"):
        return ("這個指令還不支援 --json", "它的輸出由 abf_launch 自己的出口產生，尚未接上 JSON 外殼",
                "不加 --json 執行，或等後續版本")
    return None


def _run(args, path):
    if args.product_version:
        return cmd_version(args)
    if cliout.json_mode():
        refusal = _json_refusal(args, path)
        if refusal:
            _err(refusal[0], why=refusal[1], next=refusal[2])
            return 1
    if args.command in ADOPTING:
        adopt_orphans()
    return args.func(args)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cliout.reset(json_mode=cliout.leading_flag(argv, "--json"))
    try:
        parser = build_parser()
        args = parser.parse_args(argv)
        if not args.product_version and args.command is None:
            parser.error("the following arguments are required: command")
        cliout.reset(json_mode=args.json_mode, debug=args.debug_mode)
        path = _command_path(args)
        started = time.monotonic()
        known = _option_names(parser)
        given = []
        for tok in argv:
            name = tok.split("=", 1)[0]
            if tok.startswith("--") and name in known and name not in given:
                given.append(name)
        cliout.debug("command %s" % path)
        if given:
            cliout.debug("options %s" % " ".join(given))      # the names only, never a value
        try:
            rc = _run(args, path)
        except Exception:
            cliout.debug_exception()
            raise
        cliout.finish(path, rc, with_output=not args.product_version)
        cliout.debug("exit %s in %d ms" % (rc, (time.monotonic() - started) * 1000))
        return rc
    finally:
        cliout.reset()
