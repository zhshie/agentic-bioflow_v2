# Bug Assessment: 002 follow-ups (egress allowlist gate, its file, the relay's idea of a "specific domain")

- **Slug**: relay-followups
- **Created**: 2026-10-02
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/45
- **Verdict**: valid, every item reproduced against main (1a049f1 + the stacked fixes) in WSL
- **Severity**: medium (gate obfuscations, direct writes, public-suffix and loopback names, env prefix) and low (the rest). None is HIGH: no ordinary command widens the allowlist without the user's confirmation, and a domain only takes effect when the relay is (re)started, which asks and lists what it carries.

## 給維護者

1. 「新增放行網域」的把關（`egress_allow.sh add/remove` 要問你）可以被改寫法繞過：萬用字元、反斜線、拼接引號、先用變數存名字。另外直接用 `>>`、編輯器、Write/Edit 工具改 `egress_allow.tsv` 完全沒有人把關。
2. 「具體網域」的定義太寬：`co.uk`、`github.io`、`nip.io`、`127.0.0.1.nip.io`、`localhost.localdomain` 都能加；中繼程式不檢查解析出來的 IP，所以名字解析到內網或本機時能碰到任意埠。
3. 修法：把關認得這些寫法並對 `egress_allow.tsv` 的寫入也問你；網域檢查加一份「共用名稱／萬用 DNS／本機名稱」清單（bash 與 Python 共用同一份檔案）；中繼程式對「只靠額外清單放行」的名字，解析到非公開位址就拒絕。
4. 下面「Decisions」裡有幾項要你決定，我都選比較安全的那邊。

## Items and test cases

Tests: `tests/confirm_launch_test.sh` (section #45), `tests/egress_allow_test.sh`, `tests/nf_relay_domains_test.sh`, `tests/settings_test.sh`, `tests/on_site_test.sh`, `tests/egress_ctl_restart_test.sh`. `control:` labels differ from their pair in one fact and already passed.

| # | Item | Today | Wanted |
|---|---|---|---|
| M1 | `bash scripts/egress_allow.* add …`, `egress_allo?.sh`, `egress_allow\.sh`, `egress_allow.s[h]`, `e*_allow.sh`, `egress_""allow.sh`, `a=egress_allow; bash scripts/$a.sh add …`, `$a`/`$b` both variables, an unset `$a`, direct run of `egress_allo?.sh` | quiet | ask |
| M2 | `>>`/`>`/`tee -a`/`cp`/`sed -i`/editor/glob on `egress_allow.tsv`; Write/Edit tool on it | quiet | ask (readers `cat`, `grep`, `ls`, `wc`, `diff` stay quiet) |
| M3 | `NF_RELAY_EXTRA_DOMAINS=x bash scripts/egress_ctl.sh start` (also `env`, `export`) | ask, but the summary shows the file's list | the ask says the command overrides this deployment's list |
| M4 | `add co.uk github.io nip.io 127.0.0.1.nip.io localhost.localdomain printer.local db.internal 10.0.0.5.example.com a.localhost`, a name over 253 characters | accepted | refused (and dropped at the relay); an extra domain resolving to a non-public address is refused at connect |
| M5 | spec US2-1 / TC-023 status half | `settings.sh --summary` and `egress_ctl.sh status` say nothing | summary lists the extra domains with date and reason; relay status shows what the running relay loaded and says when the list did not load |
| L1 | false alarms: `cat`/`less`/`grep -n add`/`bash -n`/`git diff --` on the script, `source "scripts/egress_allow.sh"` | ask | quiet (a bare `bash scripts/egress_allow.sh` still asks, as a test already pins) |
| L2 | validators disagree: > 253 characters (bash accepted), U+212A (Python accepted) | | both refuse |
| L3 | a dropped entry is echoed raw into the relay log (newline forges a log line); the note keeps ESC | | printable, one line |
| L4 | `printf %q` on a note with control characters writes `$'…'`, which a POSIX sh remote shell rejects | | note is printable ASCII |
| L5 | `--reason` keeps VT, FF, 0x1f, 0x85 | | all become spaces |
| L6 | the note sent to the site includes the laptop's settings path | | file name only |

## Root cause (per family)

- M1: `confirm_launch.sh` only looks for the literal `egress_allow.sh`, behind a substring pre-check on the raw command.
- M2: nothing watches the file; the Write/Edit tools are not routed to `confirm_launch.sh` at all (`hooks/hooks.json`).
- M3: the ask builds its summary from the file; a prefix variable is only visible in the raw command text.
- M4: `domain_format_ok` and `_parse_extra` check shape only (labels, final label letters). `connect_upstream` takes whatever the name resolves to.
- L1: the gate treats any segment that names the script as running it; a reader's argument and a bare `source` are not runs.
- L2-L6: independent small defects in the two validators, the note, the `--reason` cleaning and `on_site.sh`.

## Decisions (safer option taken; listed again in fix.md)

1. Public-suffix policy: a small built-in list (`scripts/relay_denied_names.txt`, read by `egress_allow.sh` and `nf_relay.py` alike), not the full Public Suffix List. Two kinds of line: `exact` (refuse that name only, so `bbc.co.uk` is fine) and `tree` (refuse the name and everything under it: wildcard-DNS services, local TLDs). The list cannot be complete; the connect-time check is the backstop.
2. Connect-time check: an extra domain (one matched only by this deployment's list) that resolves to a loopback, private, link-local, unspecified, multicast or otherwise non-global address is refused. This also refuses an internal mirror that legitimately resolves to a site-internal address; there is no opt-out.
3. A name that embeds an IPv4 address in its labels (`10.0.0.5.example.com`) is refused.
4. If the denied-names file cannot be read at the relay, every extra domain is dropped and the startup says so (fail closed, invariant 13).
5. M2 asks for editors and every writer of the file, including from a session whose cwd is the config directory; it does not block, because a person can legitimately edit their own file.
6. The ports are not restricted (the issue only names the resolved address). Listed as not done.

## NOT changed

- The built-in allowlist, the peer restriction, `egress_allow.sh list`/`domains` output formats, the 100-entry limit.
- Performance of the gates (#34).
