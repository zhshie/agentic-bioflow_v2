# studio-embed: ledger

Written by the executor (2026-11-13). What was built, the L-grade proof the plan asks for, what is not verified, and the results of the runs. The manual
checks TC-036 to TC-040 are not done here: the lead tries them on the maintainer's desktop and writes the results in the last section.

## CSP of the downstream page, before and after

Before (and every other page, with or without the setting; `web._HEADERS`):

```
default-src 'none'; style-src 'sha256-FfC1YK8kGEBly+aw5sxs1lF8rL8fd0bvd3C1C3uWpGw='; form-action 'self'; frame-ancestors 'none'; base-uri 'none'
```

After, for `GET /?run=<id>&stage=downstream` of a succeeded run of the caller, only when `ABF_STUDIO_URL=http://127.0.0.1:8790` is set:

```
default-src 'none'; style-src 'sha256-FfC1YK8kGEBly+aw5sxs1lF8rL8fd0bvd3C1C3uWpGw='; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; frame-src http://127.0.0.1:8790
```

`X-Frame-Options: DENY` and the other headers are unchanged. No `script-src`, no `'unsafe-inline'`, no `*`. `test_tc019` removes `; frame-src <address>` and compares the rest
with `_HEADERS` character by character; `test_tc020` compares the whole header set of fifteen other pages and seven board states with and without the setting;
`test_tc021` checks that a frame in the body and `frame-src` in the header come together. The style hash is unchanged (`STYLE_SHA256` of `test_results_files.py`); the frame is sized with `width` and `height` attributes.

## Refused shapes of ABF_STUDIO_URL (exit code 1, nothing listens; `create_app` also raises `ValueError`)

Accepted: exactly `http://127.0.0.1:<port>` or `http://localhost:<port>`, port 1 to 65535 without a leading zero. Empty or unset: no setting. Refused (each is a case of
`test_tc002_tc003_tc004`): `https://127.0.0.1:8790`, `http://example.com:8790`, `http://127.0.0.1.evil.com:8790`, `http://localhost.evil.com:8790`,
`http://127.0.0.1:8790@evil.com`, `http://0.0.0.0:8790`, `http://[::1]:8790`, `http://127.1:8790`, `http://2130706433:8790`, `ftp://127.0.0.1:8790`,
`javascript:alert(1)`, `//127.0.0.1:8790`, `*`, `http://127.0.0.1` (no port), `:0`, `:99999`, `:abc`, `:08790`, `http://127.0.0.1:8790/x`, `?a=1`, `#f`,
`http://u:p@127.0.0.1:8790`, `http://127.0.0.1:8790; script-src *`, `http://127.0.0.1:8790 'unsafe-inline'`, a value with a leading or trailing blank or a line break (also
`http://127.0.0.1:8790\nhttp://evil.example`), `http://127.0.0.1: 8790`, and the trailing slash `http://127.0.0.1:8790/` (refused, not normalised: ruling 4).
The message names `ABF_STUDIO_URL`, gives the reason in one line, shows an example, is in English and Chinese, and never echoes the value (it could hold a password).

## Existing tests rewritten (only these, as the task named them)

- `tests/hosted_deploy_test.sh` TC-069: the file list under `deploy/` gains `deploy/systemd/abf-rstudio.service.in` (ten files became eleven, label changed). TC-083: `deploy/systemd/` holds five `.service.in`
  instead of four (the count and two labels). Reason: the feature adds one unit template, and these two assertions count the files. Four lines of the file changed; no other assertion.
- `tests/desktop_systemd_test.sh` line 198 (TC-044): it greps the hosted test for `four .service.in` and `-eq 4`; now `five` and `-eq 5`.
- `platform/tests/__golden__/cli_tree.txt` line 17 and `cli_help_top.txt` line 8: the `fetch-results` row gains `--r` (flag, `no`/`False` columns, one help sentence), and the one-line usage gains `[--r]`.
  `test_cli_contract.py` does not list flags per command and is unchanged.
- `platform/tests/test_web_downstream.py` and `test_web_result_viewer.py` are not changed (`test_tc023` compares them with the merge base).

## Not verified (the lead tries these on the real desktop and corrects the unit)

The unit is written from the option names found in the package's `rserver` binary. Nothing of RStudio was installed or run by the executor.

1. Whether a start without root needs `--server-data-dir`, `--secure-cookie-key-file` and `--database-config-file` at all, and the contents they want. The unit makes `%t/abf-rstudio/` (mode 700, under `$XDG_RUNTIME_DIR`), writes a uuid from `/proc/sys/kernel/random/uuid` to `cookie-key`, and a two-line `database.conf` (`provider=sqlite`, `directory=<dir>/db`); this follows what is commonly done to run `rserver` unprivileged, not a test. The data folder is in the runtime folder, so it is gone at logout or reboot (user settings live in the person's own `~/.config/rstudio`).
2. Whether `--auth-none=1` takes effect for a non-root `--server-user`, and whether RStudio still sets a session cookie in a cross-site frame.
3. The value form of `--www-frame-origin` (`${ABF_PUBLIC_URL}` is an origin with a scheme and no trailing slash as the platform's `--public-url` is given; RStudio may want `same`, `none` or another form), and whether `--www-same-site` (`none`) is needed for a page on another site to frame `http://127.0.0.1:<port>`; it is not set.
4. The default of `--www-address` (the package's strings contain `0.0.0.0`), which is why the unit always sets `127.0.0.1`; and that `--www-port` accepts the value cut from the URL by the shell (`${ABF_STUDIO_URL##*:}`).
5. The path `/usr/lib/rstudio-server/bin/rserver` (the usual place of the Ubuntu package) and `--server-daemonize=0` as the way to stay in the foreground under systemd.
6. Systemd quoting: `$$` for the shell's own variables, `%t` and `%u` specifiers, `${ABF_PUBLIC_URL}` expanded by systemd inside the quoted script. `NoNewPrivileges` is left out because it may stop `rsession` from starting; add it if the desktop test shows it is harmless.
7. The `allow` word: the iframe has `allow="local-network-access"` (the Chromium permission policy name for a page that reaches a local address); Firefox and Edge may need another word or none, and a browser that blocks the frame still leaves the new-tab link.
8. Whether an https page may frame `http://127.0.0.1:<port>` in each browser (127.0.0.1 is treated as a secure context by Chromium and Firefox; not tried here).
9. Whether `system2("abf-platform", ...)` finds the command from inside RStudio (its `PATH`), and whether `dev.copy(png, filename = f)` copies the plot in the `RStudioGD` device; the second line is only checked by shape (basic R, temporary png, `publish-figure <id> <file>`, no confirm flag).

## Deliberate differences from ADR 0010, Decided 3

The page does not probe the address (a probe would be a connection by the platform, and the platform never connects to it; the page says what to do when the frame is blank), and the agent does not report the address in its heartbeat (`platform/abf_station/` is not touched).

## Local results (WSL Ubuntu, 2026-11-13)

- `platform/tests/test_studio_embed.py`: 101 passed. Together with `test_web_downstream.py`, `test_web_result_viewer.py`, `test_studio_*.py`, `test_cli_contract.py`, `test_cli_snapshots.py`, `test_cli_flags.py`, `test_results_files.py`, `test_web_wording_sweep.py`, `test_confirm_page.py`, `test_web_board.py`: 834 passed, 2 xfailed.
- `tests/studio_embed_deploy_test.sh`, `hosted_deploy_test.sh`, `desktop_systemd_test.sh`, `credentials_stay_in_settings_test.sh`, `operations_doc_test.sh`, `no_pipefail_grep_q_test.sh`, `constitution_scope_test.sh`: all pass.
- `bash tests/run_all.sh` as one run: 147/155. The three failures were not the feature's: `no_pipefail_grep_q_test.sh` (three `| grep -q` in the new deploy test; fixed), `constitution_scope_test.sh` (the worktree's git record had been pruned during the run; passes after the record was rebuilt), `jev_test.sh` (22 s under load; passes on rerun, not touched by this change). Five `platform_shard_2..6` timed out at the 300 s limit of `run_all.sh` on this machine; each was then run alone with `--timeout 0` and passed (1/1 each). There is no single full run that was green at the final commit: CI is the judge.
- Not run: the manual checks TC-036 to TC-040, and any real RStudio or browser.

## Section for the lead: results on the desktop (TC-036 to TC-040)

Trial by the lead (2026-11-13): RStudio Server 2025.09.2+418, R 4.1.2, headless Chromium 156, parent page on another https site, iframe to `http://127.0.0.1:8790/`.

1. The options of the unit start `rserver` without root: `--server-daemonize=0 --server-user --www-address --www-port --www-frame-origin --auth-none=1 --server-data-dir --server-pid-file --secure-cookie-key-file --database-config-file` were all accepted; the response carried `Content-Security-Policy: frame-ancestors <origin>`. The cookie-key file was made `chmod 600` (the unit now does it).
2. With only those options the frame failed: no `SameSite` on the cookie, so `/` and `/auth-sign-in` redirected to each other until `ERR_TOO_MANY_REDIRECTS`.
3. Adding `--www-same-site=none` still failed: the cookie was `SameSite=None` without `Secure`, which Chromium refuses; the same redirect loop.
4. Adding `--auth-cookies-force-secure=1` worked: `SameSite=None; Secure` accepted, RStudio fully shown in the frame (Console, Environment, Files, Plots). Both options are now in the unit and pinned by `tests/studio_embed_deploy_test.sh`.
5. Without the browser's local network access permission the frame request failed with `net::ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS`; after it was granted it worked. A real Chrome asks once and the person presses Allow; `allow="local-network-access"` on the iframe is needed. The page, OPERATIONS step 12, TESTING and PLATFORM now say so.
6. Without `USER` in the environment the no-login start of `rserver` failed; the unit now does `export USER=%u`.

Not tried: Firefox, Safari, the permission prompt in a real Chrome window, the second R line run in a Console.

Status of the nine points above ("Not verified"):

| # | Point | Status |
|---|---|---|
| 1 | options a start without root needs, data folder, cookie key, database config | verified (accepted and working); cookie key needs mode 600 (added) |
| 2 | `--auth-none=1` for a non-root user, session cookie in a cross-site frame | verified, with `USER` set and with the two cookie options (items 2 to 4, 6) |
| 3 | `--www-frame-origin` value form, `--www-same-site` | verified: the origin form is accepted; `--www-same-site=none` plus `--auth-cookies-force-secure=1` are required |
| 4 | `--www-address` default, `--www-port` from the URL | verified as accepted; not tried separately from the trial's `127.0.0.1:8790` |
| 5 | path of `rserver`, `--server-daemonize=0` | verified (the options were accepted when run) |
| 6 | systemd quoting (`$$`, `%t`, `%u`), `NoNewPrivileges` | still unverified: not reported as run under the systemd unit |
| 7 | the `allow` word | verified for Chromium (required); Firefox and Edge still unverified |
| 8 | https page framing `http://127.0.0.1:<port>` | verified in Chromium 156 only |
| 9 | `system2("abf-platform", ...)` from RStudio, `dev.copy(png, ...)` | still unverified |

Not done: item D of the lead's message (the reconnect steps of the WSL section). `tests/desktop_systemd_test.sh` D6 asserts that the section does NOT contain `LAB_SETTINGS_FILE` ("must not be the example"), so adding it would break that existing test; the section is left as it was and the question goes back to the lead.

## Second desktop trial and the adversarial review (round 2)

Lead's trial, same environment: with `--www-enable-origin-check=1` the frame still works (RStudio fully shown). A POST to `/rpc/client_init` with `Origin: https://evil.example` gave 400, with the frame origin (`https://example.com`) gave 400, with `http://127.0.0.1:8790` gave 200.

| # | Finding of the review | Handling |
|---|---|---|
| S1 | no origin check on the RStudio port | `--www-enable-origin-check=1` added to the unit, pinned by `studio_embed_deploy_test.sh`, whitelist updated |
| S2 | what "anyone can use it" means on the computer that runs the platform | stated in the unit header, `docs/OPERATIONS.md` step 12 and `docs/PLATFORM.md`: a shell of the platform's owner (every user's analyses, databases, token files, signing key, agent token, sending analyses to the site and spending the compute allowance); other Windows users reach it too (WSL forwards loopback); pinned by the deploy test |
| S3 | `ABF_STUDIO_URL` is one value for the deployment and reaches every user's page | stated in `docs/PLATFORM.md`, `docs/OPERATIONS.md` and `deploy/env.example`: only for a deployment with one user; the local network permission is given to the platform's address and is safe only because the platform page runs no script (N4); pinned by the deploy test |
| S4 | `ABF_PUBLIC_URL` unset or not https; the value was pasted into the command text by systemd | the unit stops with exit 2 and a message (as for `ABF_STUDIO_URL`); the frame origin is read and quoted by the shell; pinned by the deploy test |
| S5 | `system2` builds one shell command, so the id and the file path must be quoted | `_r_lines` wraps both in `shQuote()` and returns no R line for an id that is not 16 lowercase hex characters (the rest of the page is as usual); the wrong docstring sentence is replaced; `test_tc011`, `tc012`, `tc028` updated (the embed tests now use a 16-hex run id) |

## git diff --stat origin/v3...HEAD

```
 CHANGELOG.md                                       |   1 +
 deploy/env.example                                 |   9 +
 deploy/systemd/abf-rstudio.service.in              |  26 +
 docs/OPERATIONS.md                                 |  25 +
 docs/PLATFORM.md                                   |  20 +-
 docs/TESTING.md                                    |  14 +
 platform/abf_platform/cli.py                       |  22 +-
 platform/abf_platform/studio_cli.py                |  38 +-
 platform/abf_platform/web.py                       |  18 +-
 platform/abf_platform/web_board.py                 |  12 +-
 platform/abf_platform/web_downstream.py            | 111 +++-
 platform/tests/__golden__/cli_help_top.txt         |   2 +-
 platform/tests/__golden__/cli_tree.txt             |   2 +-
 .../studio_embed_today/read_en_nostudio.txt        |  11 +
 .../studio_embed_today/read_en_studio.txt          |  11 +
 .../studio_embed_today/read_zh_nostudio.txt        |  11 +
 .../studio_embed_today/read_zh_studio.txt          |  11 +
 .../studio_embed_today/unread_en_nostudio.txt      |  11 +
 .../studio_embed_today/unread_en_studio.txt        |  11 +
 .../studio_embed_today/unread_zh_nostudio.txt      |  11 +
 .../studio_embed_today/unread_zh_studio.txt        |  11 +
 platform/tests/test_studio_embed.py                | 600 +++++++++++++++++++++
 specs/studio-embed/ledger.md                       | 142 +++++
 specs/studio-embed/plan.md                         |  57 ++
 specs/studio-embed/test-case-overview.md           |  50 ++
 specs/studio-embed/test-case.md                    |  94 ++++
 tests/desktop_systemd_test.sh                      |   2 +-
 tests/hosted_deploy_test.sh                        |   8 +-
 tests/studio_embed_deploy_test.sh                  | 128 +++++
 29 files changed, 1431 insertions(+), 38 deletions(-)
```

## Checks against the base (lead, 2026-11-13, at d343a3c9 against `origin/v3`)

CI showed that three tests compared the branch with its base and skipped where there is none; nothing may be skipped on CI, and after the merge
such a comparison is empty. They are therefore done once here, with git, and the tests are removed (TC-023, TC-027) or made base-free (TC-026,
the `platform/abf_station/` line of TC-018).

- `git diff --name-only origin/v3...HEAD` names no file under `platform/abf_station/`, `.github/`, `hooks/`, no `plugin.json`, no constitution,
  and none of `confirm.py`, `store.py`, `test_studio_publish.py`, `test_web_downstream.py`, `test_web_result_viewer.py` (grep found nothing).
- The acceptance verifier checked the same at dee653ca, and that the two golden files differ from the base in the `fetch-results` row only;
  the commits after dee653ca touch neither golden file.
- Under the real user service manager (systemd 249) the unit started: `rserver` owned by the user, listening on `127.0.0.1:8790` only, answering
  with `frame-ancestors <ABF_PUBLIC_URL>`; the system `rstudio-server` service is disabled and inactive. This closes point 6 (systemd quoting).
