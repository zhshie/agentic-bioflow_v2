# cb-D9 ledger

## RED (unchanged code)

```
        from abf_platform import compute_envs as ce
        msg = ce.credential_findings({"description": "https://user:" + PW + "@h.org/a"}, "x")
>       assert msg and PW not in repr(msg)
E       assert ([])

platform/tests/test_url_credential_patterns.py:74: AssertionError
=========================== short test summary info ============================
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[https://user:hunter2@h.org/a.fq.gz]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[cell3]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[cell4]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[https://h.org/a.fq.gz?X-Amz-Signature=0123456789abcdef0123456789abcdef0123456789abcdef]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[http://u:hunter2@h.org:8080/a.fq.gz]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[ftp://:hunter2@h.org/a.fq.gz]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[https://user:p%40ss@h.org/a.fq.gz]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[https://user:p@ss@h.org/a.fq.gz]
FAILED platform/tests/test_url_credential_patterns.py::test_url_with_a_secret_is_a_credential[a sample sheet cell: https://user:hunter2@h.org/a.fq.gz, in the middle of text]
FAILED platform/tests/test_url_credential_patterns.py::test_audit_script_inputs_are_refused_by_the_samplesheet_check[https://user:hunter2@h.org/a.fq.gz]
FAILED platform/tests/test_url_credential_patterns.py::test_audit_script_inputs_are_refused_by_the_samplesheet_check[cell3]
FAILED platform/tests/test_url_credential_patterns.py::test_the_secret_is_not_in_the_refusal
12 failed, 27 passed in 0.12s
```

Note: the AWS audit input is already refused on base (AKIA rule); it passes in RED and stays as a regression case.

## Why a sibling list, not _VALUE_PATTERNS

Appending the two rules to `_VALUE_PATTERNS` (as the brief says) made
`platform/tests/test_model_key_refusal.py::test_tc015_the_six_existing_patterns_are_unchanged_and_the_new_ones_come_after`
fail: "Left contains 2 more items" (`got[6:]` is compared for equality). That file is not in the allowed list and a
pin may not be weakened, so the rules went into `_URL_SECRET_PATTERNS`, checked by `looks_like_credential`.
Both pin files pass unchanged.

## GREEN

`pytest platform/tests/test_url_credential_patterns.py test_model_key_refusal.py test_k8s_paste_rule.py`: 84 passed.

## Old shapes, base (origin/v3 compute_envs.py) vs branch

Corpus: every line and every string constant of every .py/.md/.sh in the worktree plus 17 hand-made shapes (170170 strings).
base refuses 520, branch refuses 552. LOST (base refused, branch accepts): 0.
GAINED: 32, all of them a `scheme://user:pw@host` URL or an `X-Goog-Signature=`/`X-Amz-Signature=` URL (the new test
inputs, their own failure lines, docs lines quoting them, `https://u:p@h/`, `https://user:pw@github.com/x`,
`http://127.0.0.1:%d@evil.example/user-info`, `http://u:p@127.0.0.1:1`). Counter-examples
`https://h/a.fq.gz`, `git@github.com:org/repo.git`, `https://h/x?y=z@w`, `user@host:22`, `a@b.c` stay accepted.

## Full suite (HEAD eb74ebc2, code commit)

NOT green locally: 134/143 passed, 9 failed. The same 6 pytest cases fail on an unmodified origin/v3 checkout (run in the suite venv):
test_station_e2e tc056 and tc082, test_cli_snapshots[cli_help_top], and the three read-only-cache tests (the VM runs as root).
The other failing entries (agent_ctl_connection_id, why_pending, wsl_bridge, platform_upgrade, platform_clock) are shell/environment
tests that failed the same way in the earlier D1/D3/D5/D7 runs on this VM; none touches compute_envs.

```
FAIL       agent          not running - Platform will show no outputs (scripts/on_site.sh --script scripts/agent_ctl.sh start)
FAIL       resources      tar: Child returned status 141
FAIL       compute-env    ce is 'unreachable'>>
missing rsync on MSYS is FAILed by name                    ok
and it says plainly that Git Bash ships none               ok
and gives an install route rather than nothing             ok

-- (i) install_deps.sh: tw on MSYS is named plainly, not folded into 'unknown platform' --
install_deps.sh --cli-only fails cleanly, not silently     ok
it names the gap as unmeasured (R4), a real answer         ok
and gives the Windows asset to fetch by hand               ok
it does not fall back to the generic unknown-platform text ok
shim does not run wsl.exe from the caller's own cwd        ok
and lands in a directory that exists                       ok
only settings.sh decides whether the bridge is in play     ok
and nothing hardcodes the control-path default beside it   ok

3 failed

134/143 passed, 9 failed
```

## Fix round: RED timing test (checker: userinfo regex is quadratic)

Added `test_credential_check_is_linear_on_hostile_input` (`'a.'*100000`, `'x://'+'a:'*50000`, `'http://'+'a:'*50000+' no at sign'`, each < 1 s).
On the current regex (`\b[A-Za-z][A-Za-z0-9+.-]*://[^\s/?#@]*:[^\s/?#@]*@`):

```
E       assert (23463.468378913 - 23439.489433623) < 1.0      (one case took ~24 s)
FAILED platform/tests/test_url_credential_patterns.py::test_credential_check_is_linear_on_hostile_input[text0]
FAILED platform/tests/test_url_credential_patterns.py::test_credential_check_is_linear_on_hostile_input[text1]
FAILED platform/tests/test_url_credential_patterns.py::test_credential_check_is_linear_on_hostile_input[text2]
3 failed, 39 deselected in 82.04s (0:01:22)
```
